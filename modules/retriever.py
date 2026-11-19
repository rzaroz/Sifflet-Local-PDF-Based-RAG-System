import sqlite3
import faiss
from utils.embedder import EmbedderService


class BookRetriever:
    _indexes = {}

    @classmethod
    def _get_index(cls, faiss_path):
        if faiss_path not in cls._indexes:
            cls._indexes[faiss_path] = faiss.read_index(faiss_path)
        return cls._indexes[faiss_path]

    @classmethod
    def search(cls, database, question, top_k=3):
        embedder = EmbedderService.instance()
        if not embedder.is_ready() or not database.faiss_path:
            print("Nope!")
            return []

        index = cls._get_index(database.faiss_path)
        _, ids = index.search(embedder.encode(question), top_k)
        ids = [int(i) for i in ids[0] if i != -1]
        if not ids:
            return []

        conn = sqlite3.connect(database.sqlite_path)
        try:
            table = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
            ).fetchone()[0]
            marks = ",".join("?" * len(ids))
            rows = conn.execute(
                f'SELECT pk, data FROM "{table}" WHERE pk IN ({marks})', ids
            ).fetchall()
        finally:
            conn.close()

        by_pk = dict(rows)
        return [by_pk[i] for i in ids if i in by_pk]