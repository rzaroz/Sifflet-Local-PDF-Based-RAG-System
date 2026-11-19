import os
import sys
import pymupdf
import sqlite3
import numpy as np
from utils.embedder import EmbedderService

def get_base_path():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

class PDFToSqlite:
    def __init__(self, doc_path, output_folder, name):
        self.name = name
        self.pdf_path = doc_path
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok=True)

    @staticmethod
    def _table_query(table_name):
        return f"""CREATE TABLE "{table_name}" (pk INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL)"""

    @staticmethod
    def _insert_query(table_name):
        return f"""INSERT INTO "{table_name}" (data) VALUES (?)"""

    def create(self):
        sqlite_path = os.path.join(self.output_folder, "book.db")

        if os.path.exists(sqlite_path):
            os.remove(sqlite_path)

        table_name = self.name.replace('"', '""')
        sqlite_conn = sqlite3.connect(sqlite_path)

        try:
            cursor = sqlite_conn.cursor()

            cursor.execute(self._table_query(table_name))

            with pymupdf.open(self.pdf_path) as pdf:
                for page in pdf:
                    text = page.get_text("text").strip()

                    if text:
                        cursor.execute(self._insert_query(table_name),(text,))

            sqlite_conn.commit()

        except Exception:
            sqlite_conn.rollback()
            raise
        finally:
            sqlite_conn.close()

        return sqlite_path

class FaissCreator:
    def __init__(self, table_name, field_name):
        self.table_name = table_name
        self.field_name = field_name

    def create(self, output_path, db_path):
        import faiss
        embedder = EmbedderService.instance()
        if not embedder.wait_until_ready(timeout=300):
            raise RuntimeError(embedder.error() or "مدل embedder لود نشد.")

        sq_conn = sqlite3.connect(db_path)
        try:
            cursor = sq_conn.cursor()
            index = faiss.IndexIDMap2(faiss.IndexFlatIP(embedder.dimension))
            cursor.execute(f"SELECT pk, {self.field_name} FROM {self.table_name}")

            while rows := cursor.fetchmany(32):
                chunk_ids = np.array([row[0] for row in rows], dtype="int64")
                texts = [row[1] for row in rows]
                vectors = embedder.encode(texts)
                index.add_with_ids(vectors, chunk_ids)

            faiss.write_index(index, os.path.join(output_path, "books.faiss"))
        finally:
            sq_conn.close()
            return os.path.join(output_path, "books.faiss")

