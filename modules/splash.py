from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMessageBox,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class StartupSplash(QWidget):
    finished = Signal()

    def __init__(self, embedder, parent=None):
        super().__init__(parent)
        self._embedder = embedder
        self._is_finished = False
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedSize(600, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        title_label = QLabel("در حال آماده‌سازی برنامه…")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 0)
        progress_bar.setTextVisible(False)
        layout.addWidget(progress_bar)

        hint_label = QLabel("بارگذاری مدل embedder؛ بار اول ممکن است کمی طول بکشد.")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        # وسط صفحه
        screen = QApplication.primaryScreen()
        if screen is not None:
            geometry = screen.availableGeometry()
            self.move(
                geometry.center().x() - self.width() // 2,
                geometry.center().y() - self.height() // 2,
            )
        embedder.loaded.connect(self._on_loaded)
        embedder.load_failed.connect(self._on_failed)
        if embedder.is_ready():
            self._finish()

    @Slot()
    def _on_loaded(self):
        self._finish()

    @Slot(str)
    def _on_failed(self, message):
        if self._is_finished:
            return
        QMessageBox.warning(
            None,
            "خطا در لود embedder",
            f"مدل embedder لود نشد؛ جستجو در کتاب‌ها کار نخواهد کرد.\n\n{message}",
        )
        self._finish()

    def _finish(self):
        if self._is_finished:
            return
        self._is_finished = True
        self.finished.emit()
