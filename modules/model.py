import atexit           
import gc
import http.client     
import json          
import os            
import socket      
import subprocess  
import sys          
import tempfile 
import time
from pathlib import Path 
from modules.manager import ManageSetting
from PySide6.QtCore import QObject, QThread, Signal, Slot
_SERVER_EXE_NAME = "llama-server.exe" if sys.platform == "win32" else "llama-server"


_THIS_DIR = Path(__file__).resolve().parent
_LLAMA_DIR_CANDIDATES = [
    _THIS_DIR / "llama",
    _THIS_DIR.parent / "llama",
]

SETTING = ManageSetting()

LOAD_TIMEOUT_SECONDS = 600
DEFAULT_N_CTX = 4096
DEFAULT_MAX_TOKENS = 1024
DEFAULT_N_GPU_LAYERS = 99


def _get_n_ctx() -> int:
    return int(SETTING.settings.get("max_input_tokens", DEFAULT_N_CTX))


def _get_max_tokens() -> int:
    return int(SETTING.settings.get("max_output_tokens", DEFAULT_MAX_TOKENS))


def _find_server_exe() -> Path:
    for llama_dir in _LLAMA_DIR_CANDIDATES:
        if not llama_dir.is_dir():
            continue
        direct = llama_dir / _SERVER_EXE_NAME
        if direct.is_file():
            return direct
        for found in llama_dir.rglob(_SERVER_EXE_NAME):
            if found.is_file():
                return found
    searched = "\n".join(str(p) for p in _LLAMA_DIR_CANDIDATES)
    raise FileNotFoundError(
        f"فایل {_SERVER_EXE_NAME} پیدا نشد. این مسیرها بررسی شدند:\n{searched}"
    )


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _LLMWorker(QObject):
    loaded = Signal(str)  
    load_failed = Signal(str, str)
    unloaded = Signal(str)
    token = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._process = None
        self._port = 0
        self._log_path = ""
        self._conn = None   
        self._path = ""
        self._stop = False

    @Slot(str)
    def load(self, model_path: str):
        try:
            self._release()
            exe = _find_server_exe()
            self._port = _find_free_port()

            log_file = tempfile.NamedTemporaryFile(
                prefix="llama_server_", suffix=".log", delete=False
            )
            self._log_path = log_file.name

            command = [
                str(exe),
                "-m", model_path,
                "-c", str(_get_n_ctx()),
                "-ngl", str(DEFAULT_N_GPU_LAYERS),
                "--host", "127.0.0.1",
                "--port", str(self._port),
            ]
            popen_kwargs = {}
            if sys.platform == "win32":
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            self._process = subprocess.Popen(
                command,
                cwd=str(exe.parent),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                **popen_kwargs,
            )
            log_file.close()

            self._wait_until_ready()
            self._path = model_path
            self.loaded.emit(model_path)
        except Exception as e:
            print(e)
            self._release()
            self.load_failed.emit(model_path, str(e))

    def _wait_until_ready(self):
        deadline = time.monotonic() + LOAD_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                raise RuntimeError(
                    "llama-server بسته شد (لود مدل ناموفق بود).\n\n" + self._read_log_tail()
                )
            try:
                conn = http.client.HTTPConnection("127.0.0.1", self._port, timeout=2)
                conn.request("GET", "/health")
                status = conn.getresponse().status
                conn.close()
                if status == 200:
                    return
            except OSError:
                pass
            time.sleep(0.3)
        raise TimeoutError("زمان انتظار برای لود شدن مدل تمام شد.")

    def _read_log_tail(self, max_lines: int = 15) -> str:
        try:
            with open(self._log_path, "r", encoding="utf-8", errors="replace") as f:
                return "".join(f.readlines()[-max_lines:]).strip()
        except Exception:
            return ""

    @Slot()
    def unload(self):
        path = self._path
        self._release()
        self.unloaded.emit(path)

    def _release(self):
        process = self._process
        if process is not None:
            try:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            except Exception:
                pass
        self._process = None
        self._port = 0
        self._path = ""
        if self._log_path:
            try:
                os.remove(self._log_path)
            except OSError:
                pass
            self._log_path = ""
        gc.collect()

    @Slot(str)
    def generate(self, prompt: str):
        if self._process is None or self._process.poll() is not None:
            self.error.emit("هیچ مدلی لود نشده است.")
            return
        self._stop = False
        parts = []
        try:
            body = json.dumps({
                "prompt": prompt + "\n<think>\n\n</think>\n\n",
                "n_predict": _get_max_tokens(),
                "stream": True,
            })
            conn = http.client.HTTPConnection("127.0.0.1", self._port, timeout=None)
            self._conn = conn
            conn.request("POST", "/completion", body, {"Content-Type": "application/json"})
            response = conn.getresponse()
            if response.status != 200:
                raise RuntimeError(f"خطای سرور ({response.status}): {response.read().decode('utf-8', 'replace')}")
            while not self._stop:
                line = response.readline()
                if not line:
                    break 
                line = line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                chunk = json.loads(line[5:].strip())
                text = chunk.get("content", "")
                if text:
                    parts.append(text)
                    self.token.emit(text)
                if chunk.get("stop"):
                    break
            self.finished.emit("".join(parts))
        except Exception as e:
            if self._stop:
                self.finished.emit("".join(parts))
            else:
                print(e)
                self.error.emit(str(e))
        finally:
            self._conn = None
            try:
                conn.close()
            except Exception:
                pass

    def stop(self):
        self._stop = True
        conn = self._conn
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


class LLMService(QObject):
    _instance = None

    _loadRequested = Signal(str)
    _unloadRequested = Signal()
    _generateRequested = Signal(str)

    loaded = Signal(str)
    load_failed = Signal(str, str)
    unloaded = Signal(str)
    token = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._thread = QThread()
        self._worker = _LLMWorker()
        self._worker.moveToThread(self._thread)

        self._loadRequested.connect(self._worker.load)
        self._unloadRequested.connect(self._worker.unload)
        self._generateRequested.connect(self._worker.generate)

        self._worker.loaded.connect(self.loaded)
        self._worker.load_failed.connect(self.load_failed)
        self._worker.unloaded.connect(self.unloaded)
        self._worker.token.connect(self.token)
        self._worker.finished.connect(self.finished)
        self._worker.error.connect(self.error)

        self._thread.start()
        atexit.register(self._worker._release)

    def load_model(self, model_path: str):
        self._loadRequested.emit(model_path)

    def unload_model(self):
        self._unloadRequested.emit()

    def ask(self, prompt: str):
        self._generateRequested.emit(prompt)

    def stop(self):
        self._worker.stop()

    def shutdown(self):
        self.stop()
        self._unloadRequested.emit()
        self._thread.quit()
        self._thread.wait()
        self._worker._release()