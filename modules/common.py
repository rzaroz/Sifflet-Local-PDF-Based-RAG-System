import os
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from modules.manager import DataManager
from PySide6.QtCore import Qt, Signal, QFileInfo
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,

)

session = DataManager()

PAGE_MARGINS = (32, 28, 32, 24)
PAGE_SPACING = 20

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"

PERSIAN_DIGIT_TABLE = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


class PageIndex(IntEnum):
    DASHBOARD = 0
    CREATE_DATABASE = 1
    MODEL_SELECTION = 2
    DATABASE_LIST = 3
    SETTINGS = 4
    CHAT = 5

@dataclass
class BookDatabase:
    pk: int
    database_name: str
    book_title: str
    author: str
    created_date: str
    page_count: int
    chunk_count: int
    language: str
    sqlite_path: str
    faiss_path: str
    status: str = "آماده"
    database_id: int = 0


@dataclass
class LocalModel:
    pk: int
    file_path: str
    model_name: str
    file_format: str
    file_size_text: str


@dataclass
class ChatMessage:
    role: str
    text: str
    source_note: str = ""


@dataclass
class Conversation:
    title: str
    messages: list = field(default_factory=list)
    chatroom_id: int = 0


def get_asset_path(*relative_parts):
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        modules_directory = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(modules_directory)
    return os.path.join(base_path, "assets", *relative_parts)


def load_scaled_pixmap(file_name, target_width):
    pixmap = QPixmap(get_asset_path(file_name))
    if pixmap.isNull():
        return pixmap

    device_pixel_ratio = QGuiApplication.primaryScreen().devicePixelRatio()
    scaled_pixmap = pixmap.scaledToWidth(
        int(target_width * device_pixel_ratio),
        Qt.TransformationMode.SmoothTransformation,
    )
    scaled_pixmap.setDevicePixelRatio(device_pixel_ratio)
    return scaled_pixmap


def to_persian_digits(value):
    return str(value).translate(PERSIAN_DIGIT_TABLE)


def format_count(value):
    if not value:
        return "—"
    return to_persian_digits(f"{value:,}").replace(",", "٬")


def refresh_widget_style(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def set_widget_role(widget, role):
    widget.setProperty("role", role)
    refresh_widget_style(widget)


def create_label(text="", role=None, word_wrap=False, alignment=None):
    label = QLabel(text)
    if role:
        label.setProperty("role", role)
    label.setWordWrap(word_wrap)
    if alignment is not None:
        label.setAlignment(alignment)
    return label


def create_page_header(title, subtitle):
    header_widget = QWidget()
    header_layout = QVBoxLayout(header_widget)
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(4)
    header_layout.addWidget(create_label(title, role="pageTitle"))
    header_layout.addWidget(create_label(subtitle, role="muted", word_wrap=True))
    return header_widget


def create_scroll_area(content_widget):
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll_area.setWidget(content_widget)
    return scroll_area


class SectionCard(QFrame):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")

        self.body_layout = QVBoxLayout(self)
        self.body_layout.setContentsMargins(20, 18, 20, 20)
        self.body_layout.setSpacing(12)

        if title:
            self.body_layout.addWidget(create_label(title, role="sectionTitle"))


class ClickableCard(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("clickable", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        is_left_click = event.button() == Qt.MouseButton.LeftButton
        if is_left_click and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)



def build_sample_databases():
    databases = session.all_database()
    results = []

    for db in databases:
        item = BookDatabase(
            pk= db.pk,
            database_name=db.name,
            book_title=db.book_title,
            author=db.writer,
            created_date=db.created_at,
            page_count=0,
            chunk_count=0,
            sqlite_path=db.sqlite_path,
            faiss_path=db.faiss_path,
            language="فارسی",
            database_id=db.pk,
        )

        results.append(item)

    return results

def _format_file_size(size_in_bytes):
    gigabyte = 1024 ** 3
    megabyte = 1024 ** 2
    if size_in_bytes >= gigabyte:
        value_text = f"{size_in_bytes / gigabyte:.1f}"
        unit_text = "گیگابایت"
    else:
        value_text = f"{size_in_bytes / megabyte:.1f}"
        unit_text = "مگابایت"
    return f"{to_persian_digits(value_text).replace('.', '٫')} {unit_text}"

def load_models():
    models = session.get_models()

    results = []

    for db in models:
        file_info = QFileInfo(db.path)
        item = LocalModel(
            pk=db.pk,
            file_path=db.path,
            model_name=file_info.completeBaseName(),
            file_format=file_info.suffix().upper() or "نامشخص",
            file_size_text=_format_file_size(file_info.size()),
        )

        results.append(item)

    return results


def load_conversations(database):
    if not database.database_id:
        return []

    conversations = []
    for chatroom in session.get_chatrooms(database.database_id):
        conversations.append(
            Conversation(
                title=chatroom.title or "گفت‌وگو",
                messages=[
                    ChatMessage(message.role.value, message.text)
                    for message in chatroom.messages
                ],
                chatroom_id=chatroom.pk,
            )
        )
    return conversations