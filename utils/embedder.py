import gc
import os
import sys
import threading

import numpy as np
from PySide6.QtCore import QObject, Signal


def get_app_dir():
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


EMBEDDER_DIR = os.path.join(get_app_dir(), "embedder")

MODEL_FILE = "model.onnx"
MAX_SEQ_LENGTH = 128


class EmbedderService(QObject):
    _instance = None

    loaded = Signal()
    load_failed = Signal(str)

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._session = None
        self._tokenizer = None
        self._input_names = set()
        self._dim = 0
        self._error = ""
        self._started = False
        self._done = threading.Event()
        self._start_lock = threading.Lock()
        self._encode_lock = threading.Lock()

    def start(self):
        with self._start_lock:
            if self._started:
                return
            self._started = True
            self._done.clear()
        threading.Thread(target=self._load, name="EmbedderLoader", daemon=True).start()

    def _load(self):
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer

            tok = Tokenizer.from_file(os.path.join(EMBEDDER_DIR, "tokenizer.json"))
            pad_id = tok.token_to_id("<pad>")
            if pad_id is None:
                pad_id = 0
            tok.enable_padding(pad_id=pad_id, pad_token="<pad>")
            tok.enable_truncation(max_length=MAX_SEQ_LENGTH)

            sess = ort.InferenceSession(
                os.path.join(EMBEDDER_DIR, MODEL_FILE),
                providers=["CPUExecutionProvider"],
            )

            self._tokenizer = tok
            self._session = sess
            self._input_names = {i.name for i in sess.get_inputs()}
            self._dim = int(self._run(["test"]).shape[1])

            self._error = ""
            self._done.set()
            self.loaded.emit()
        except Exception as e:
            print(e)
            self._session = None
            self._tokenizer = None
            self._error = str(e)
            self._started = False
            self._done.set()
            self.load_failed.emit(str(e))

    def is_ready(self) -> bool:
        return self._session is not None

    def error(self) -> str:
        return self._error

    def wait_until_ready(self, timeout=None) -> bool:
        self._done.wait(timeout)
        return self._session is not None

    @property
    def dimension(self) -> int:
        self._require_model()
        return self._dim

    def _run(self, texts) -> np.ndarray:
        enc = self._tokenizer.encode_batch(texts)
        ids = np.array([e.ids for e in enc], dtype=np.int64)
        mask = np.array([e.attention_mask for e in enc], dtype=np.int64)

        inputs = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self._input_names:
            inputs["token_type_ids"] = np.zeros_like(ids)

        out = self._session.run(None, inputs)[0]
        m = mask[..., None].astype(np.float32)
        emb = (out * m).sum(axis=1) / np.clip(m.sum(axis=1), 1e-9, None)
        norm = np.linalg.norm(emb, axis=1, keepdims=True)
        emb = emb / np.clip(norm, 1e-12, None)
        return emb.astype("float32")

    def encode(self, texts, batch_size: int = 32) -> np.ndarray:
        self._require_model()
        if isinstance(texts, str):
            texts = [texts]
        texts = list(texts)
        if not texts:
            return np.zeros((0, self._dim), dtype="float32")

        with self._encode_lock:
            parts = [
                self._run(texts[i:i + batch_size])
                for i in range(0, len(texts), batch_size)
            ]
        return np.concatenate(parts, axis=0).astype("float32")

    def _require_model(self):
        if self._session is None:
            raise RuntimeError(
                "مدل embedder هنوز لود نشده است."
                + (f"\n{self._error}" if self._error else "")
            )
        return self._session

    def shutdown(self):
        with self._encode_lock:
            self._session = None
            self._tokenizer = None
        self._started = False
        self._done.clear()
        gc.collect()