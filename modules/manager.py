import os
import sys
import json
import enum
import shutil
from datetime import datetime, UTC
from sqlalchemy import desc, text, event
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import create_engine, Integer, String, Column, DateTime, ForeignKey, Text, Enum

def get_base_path():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


DATABASE_TABLE_NAME = "book_table"

class ManageSetting:

    def __init__(self):
        self.path = os.path.join(get_base_path(), "..", "settings.json")

        self.defaults = {
            "theme": 0,
            "system_role": "You are a RAG-based AI assistant. Answer the user's questions strictly and exclusively using the provided context. Do not use your internal knowledge, make assumptions, or generate information that is not explicitly supported by the retrieved data. If the answer cannot be found in the provided context, simply state that the available information is insufficient to answer the question. Never hallucinate or fabricate information.",
            "database_path": self._default_storage_path(),
            "max_input_tokens": 4096,
            "max_output_tokens": 1024,
        }

        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump(self.defaults, file, indent=4)

        try:
            with open(self.path, "r", encoding="utf-8") as file:
                self.settings = json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            self.settings = self.defaults.copy()
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump(self.settings, file, indent=4)

    @staticmethod
    def _default_storage_path():
        return os.path.join(os.path.expanduser("~"), "Sifflet", "Databases")

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(self.settings, file, indent=4)

    def set_item(self, key: str, value):
        self.settings[key] = value
        self._save()

    def reset_defaults(self):
        self.settings = self.defaults
        self._save()

base = get_base_path()
os.makedirs(base, exist_ok=True)
db_path = os.path.join(base, "data.db")
ENGINE = create_engine(f"sqlite:///{db_path.replace(chr(92), '/')}")
Base = declarative_base()


@event.listens_for(ENGINE, "connect")
def _set_sqlite_pragma(dbapi_connection, _):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def utc_now() -> datetime:
    return datetime.now(UTC)

class Lang(enum.IntEnum):
    PERSIAN = 0
    ENGLISH = 1
    ARABIC = 2
    OTHER = 3


class Role(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"

class Database(Base):
    __tablename__ = "database"

    pk = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True, unique=False)
    book_title = Column(String, nullable=True)
    writer = Column(String, nullable=True, default="نامشخص")
    lang = Column(Integer, nullable=True, default=Lang.PERSIAN)
    folder_path = Column(String, nullable=True)
    sqlite_path = Column(String, nullable=True)
    faiss_path = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    chatrooms = relationship(
        "ChatRoom",
        back_populates="database",
        cascade="all, delete-orphan",
    )


class ChatRoom(Base):
    __tablename__ = "chatroom"

    pk = Column(Integer, primary_key=True, autoincrement=True)
    database_id = Column(
        Integer,
        ForeignKey("database.pk", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    database = relationship("Database", back_populates="chatrooms")
    messages = relationship(
        "Message",
        back_populates="chatroom",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "message"

    pk = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(Enum(Role), nullable=False, default=Role.USER)
    text = Column(Text, nullable=False)
    chatroom_id = Column(
        Integer,
        ForeignKey("chatroom.pk", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    chatroom = relationship("ChatRoom", back_populates="messages")


class Models(Base):
    __tablename__ = "models"
    pk = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

def _migrate_ensure_autoincrement(engine):
    tables_to_check = ["patient", "schedules", "report"]

    with engine.begin() as conn:
        for table_name in tables_to_check:
            row = conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:name"),
                {"name": table_name}
            ).fetchone()

            if row is None or row[0] is None:
                continue

            create_sql = row[0]

            if "AUTOINCREMENT" not in create_sql.upper():
                temp_name = f"{table_name}__no_autoincrement"
                conn.execute(text(f"ALTER TABLE {table_name} RENAME TO {temp_name}"))
                table_obj = Base.metadata.tables[table_name]
                table_obj.create(bind=conn)
                columns = [c.name for c in table_obj.columns]
                columns_sql = ", ".join(columns)
                conn.execute(text(
                    f"INSERT INTO {table_name} ({columns_sql}) "
                    f"SELECT {columns_sql} FROM {temp_name}"
                ))

                conn.execute(text(f"DROP TABLE {temp_name}"))
            max_pk = conn.execute(
                text(f"SELECT MAX(pk) FROM {table_name}")
            ).scalar() or 0

            existing_seq = conn.execute(
                text("SELECT seq FROM sqlite_sequence WHERE name=:name"),
                {"name": table_name}
            ).fetchone()

            if existing_seq is None:
                conn.execute(
                    text("INSERT INTO sqlite_sequence (name, seq) VALUES (:name, :seq)"),
                    {"name": table_name, "seq": max_pk}
                )
            elif existing_seq[0] < max_pk:
                conn.execute(
                    text("UPDATE sqlite_sequence SET seq=:seq WHERE name=:name"),
                    {"name": table_name, "seq": max_pk}
                )

def _migrate_add_chatroom_title(engine):
    with engine.begin() as conn:
        columns = [row[1] for row in conn.execute(text("PRAGMA table_info(chatroom)"))]
        if "title" not in columns:
            conn.execute(text("ALTER TABLE chatroom ADD COLUMN title VARCHAR"))


Base.metadata.create_all(bind=ENGINE)
_migrate_ensure_autoincrement(ENGINE)
_migrate_add_chatroom_title(ENGINE)

class DataManager:

    def __init__(self):
        self.engine = ENGINE
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()


    def _safe_commit(self):
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def new_database(self, **kwargs):
        new_database = Database(**kwargs)

        self.session.add(new_database)
        self._safe_commit()
        self.session.refresh(new_database)

        return new_database

    def delete_database(self, pk):
        database = self.session.get(Database, pk)
        if database is not None:
            if os.path.exists(os.path.join(database.folder_path)):
                shutil.rmtree(os.path.join(database.folder_path))
            self.session.delete(database)
            self._safe_commit()

    def all_database(self):
        return (
            self.session.query(Database)
            .execution_options(populate_existing=True)
            .all()
        )

    def get_chatrooms(self, database_id):
        return (
            self.session.query(ChatRoom)
            .filter(ChatRoom.database_id == database_id)
            .order_by(desc(ChatRoom.pk))
            .all()
        )

    def new_chatroom(self, database_id, title):
        room = ChatRoom(database_id=database_id, title=title)
        self.session.add(room)
        self._safe_commit()
        self.session.refresh(room)
        return room

    def add_message(self, chatroom_id, role, message_text):
        message = Message(chatroom_id=chatroom_id, role=Role(role), text=message_text)
        self.session.add(message)
        self.session.query(ChatRoom).filter(ChatRoom.pk == chatroom_id).update(
            {"updated_at": utc_now()}
        )
        self._safe_commit()
        self.session.refresh(message)
        return message

    def delete_chatroom(self, chatroom_id):
        room = self.session.get(ChatRoom, chatroom_id)
        if room is not None:
            self.session.delete(room)
            self._safe_commit()

    def new_model(self, file_path):
        new_model = Models(path=file_path)
        self.session.add(new_model)
        self._safe_commit()
        self.session.refresh(new_model)

        return new_model

    def get_models(self):
        return (
            self.session.query(Models)
            .execution_options(populate_existing=True)
            .order_by(Models.pk)
            .all()
        )

    def delete_model(self, pk):
        model = self.session.get(Models, pk)
        if model is not None:
            self.session.delete(model)
            self._safe_commit()
