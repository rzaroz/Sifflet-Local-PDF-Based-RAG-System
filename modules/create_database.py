import os
import time
from PySide6.QtCore import Qt, QFileInfo, QTimer, Signal, QThread
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QMessageBox
)

from modules.common import (
    PAGE_MARGINS,
    PAGE_SPACING,
    BookDatabase,
    SectionCard,
    create_label,
    create_page_header,
    set_widget_role,
    to_persian_digits,
)
import uuid
from utils.safefolder import safe_folder_name
from utils.database import PDFToSqlite, FaissCreator
from modules.manager import DataManager, ManageSetting, DATABASE_TABLE_NAME


SETTING = ManageSetting()
session = DataManager()

class DatabaseThread(QThread):
    step = Signal(int)

    def __init__(self):
        super().__init__()
        self.lang = None
        self.name = None
        self.title = None
        self.writer = None
        self.file_path = None
        self.folder_path = None
        self.pdf_to_database = None
        self.sqlite_path = None
        self.faiss_path = None
        self.pk = None
        self.embedder = FaissCreator(table_name=DATABASE_TABLE_NAME, field_name="data")

    def set_parameters(self, file_path, name, title, writer, lang):
        self.lang, self.name, self.title = lang, name, title
        self.writer, self.file_path = writer, file_path
        safe_name = safe_folder_name(name) or str(uuid.uuid4())
        self.folder_path = os.path.join(SETTING.settings["database_path"], safe_name)

    def safe_release(self):
        self._release_parameters()

    def _release_parameters(self):
        self.lang = None
        self.name = None
        self.title = None
        self.writer = None
        self.file_path = None
        self.pdf_to_database = None
        self.folder_path = None
        self.sqlite_path = None
        self.faiss_path = None
        self.pk = None

    def run(self):
        os.makedirs(self.folder_path, exist_ok=True)
        self.pdf_to_database = PDFToSqlite(
            doc_path=self.file_path,
            output_folder=self.folder_path,
            name=DATABASE_TABLE_NAME,
        )
        self.sqlite_path = self.pdf_to_database.create()
        self.step.emit(0)
        self.step.emit(1)
        self.faiss_path = self.embedder.create(self.folder_path, self.sqlite_path)
        self.step.emit(2)
        new_db = session.new_database(
            name=self.name,
            book_title = self.title,
            writer = self.writer,
            lang = self.lang,
            folder_path = self.folder_path,
            sqlite_path = self.sqlite_path,
            faiss_path = self.faiss_path,
        )
        self.pk = new_db.pk
        self.step.emit(3)


class CreateDatabasePage(QWidget):
    database_created = Signal(object)
    view_databases_requested = Signal()

    PREPARATION_STEPS = (
        "استخراج متن کتاب",
        "تقسیم متن به بخش‌های کوچک",
        "ساخت نمایهٔ معنایی",
        "ذخیرهٔ دیتابیس",
    )
    STEP_INTERVAL_MILLISECONDS = 900

    STATUS_PENDING = "در انتظار"
    STATUS_RUNNING = "در حال انجام"
    STATUS_DONE = "انجام شد"

    NO_FILE_TITLE = "فایلی انتخاب نشده است"
    NO_FILE_HINT = "تنها فرمت PDF پیشتیبانی می شود."
    IDLE_MESSAGE = "پس از انتخاب فایل و تعیین نام دیتابیس، می‌توانید ساخت را آغاز کنید."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_file_path = ""
        self._completed_step_count = 0
        self._is_preparing = False
        self._step_status_labels = []
        self.pure_file_path = None
        self._build_interface()
        self._update_start_button_state()
        self.action_thread = DatabaseThread()
        self.action_thread.step.connect(self._advance_preparation)


    def _build_interface(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(*PAGE_MARGINS)
        page_layout.setSpacing(PAGE_SPACING)

        page_layout.addWidget(
            create_page_header(
                "ایجاد دیتابیس جدید",
                "لطفاً توجه داشته باشید که جزوات دست‌نویس یا اسکن‌شده به‌صورت تصویر قابل پردازش و استفاده در نرم‌افزار نیستند.",
            )
        )

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(PAGE_SPACING)
        columns_layout.addLayout(self._build_book_column(), 3)
        columns_layout.addLayout(self._build_status_column(), 2)
        page_layout.addLayout(columns_layout, 1)

    def _build_book_column(self):
        column_layout = QVBoxLayout()
        column_layout.setSpacing(PAGE_SPACING)
        column_layout.addWidget(self._build_file_card())
        column_layout.addWidget(self._build_book_info_card())
        column_layout.addStretch(1)
        return column_layout

    def _build_file_card(self):
        file_card = SectionCard("فایل کتاب")

        file_panel = QFrame()
        file_panel.setObjectName("FilePanel")

        panel_layout = QVBoxLayout(file_panel)
        panel_layout.setContentsMargins(20, 24, 20, 24)
        panel_layout.setSpacing(8)

        self.file_name_label = create_label(
            self.NO_FILE_TITLE,
            role="cardTitle",
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        self.file_detail_label = create_label(
            self.NO_FILE_HINT,
            role="muted",
            word_wrap=True,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

        self.select_file_button = QPushButton("انتخاب فایل کتاب")
        self.select_file_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_file_button.clicked.connect(self._select_book_file)

        panel_layout.addWidget(self.file_name_label)
        panel_layout.addWidget(self.file_detail_label)
        panel_layout.addSpacing(8)
        panel_layout.addWidget(self.select_file_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        file_card.body_layout.addWidget(file_panel)
        return file_card

    def _build_book_info_card(self):
        info_card = SectionCard("مشخصات کتاب")

        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(12)
        form_layout.setHorizontalSpacing(16)

        self.database_name_input = QLineEdit()
        self.database_name_input.setPlaceholderText("مثلاً: هنر جنگ")
        self.database_name_input.textChanged.connect(self._update_start_button_state)

        self.book_title_input = QLineEdit()
        self.book_title_input.setPlaceholderText("عنوان کتاب")

        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("نام نویسنده")

        self.language_combo = QComboBox()
        self.language_combo.addItems(["فارسی", "انگلیسی", "عربی", "سایر"])

        form_layout.addRow("نام دیتابیس", self.database_name_input)
        form_layout.addRow("عنوان کتاب", self.book_title_input)
        form_layout.addRow("نویسنده", self.author_input)
        form_layout.addRow("زبان کتاب", self.language_combo)

        info_card.body_layout.addLayout(form_layout)
        return info_card

    def _build_status_column(self):
        column_layout = QVBoxLayout()
        column_layout.setSpacing(PAGE_SPACING)

        status_card = SectionCard("وضعیت آماده‌سازی")

        for step_title in self.PREPARATION_STEPS:
            status_card.body_layout.addLayout(self._build_step_row(step_title))

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        status_card.body_layout.addSpacing(4)
        status_card.body_layout.addWidget(self.progress_bar)

        self.status_message_label = create_label(
            self.IDLE_MESSAGE,
            role="muted",
            word_wrap=True,
        )
        status_card.body_layout.addWidget(self.status_message_label)
        status_card.body_layout.addStretch(1)

        self.view_databases_button = QPushButton("مشاهده در دیتابیس‌های من")
        self.view_databases_button.setVisible(False)
        self.view_databases_button.clicked.connect(self.view_databases_requested.emit)

        self.start_button = QPushButton("شروع ساخت دیتابیس")
        self.start_button.setProperty("primary", True)
        self.start_button.setMinimumHeight(40)
        self.start_button.clicked.connect(self._start_preparation)

        self.reset_button = QPushButton("پاک کردن فرم")
        self.reset_button.clicked.connect(self._reset_form)

        status_card.body_layout.addWidget(self.view_databases_button)
        status_card.body_layout.addWidget(self.start_button)
        status_card.body_layout.addWidget(self.reset_button)

        column_layout.addWidget(status_card, 1)
        return column_layout

    def _build_step_row(self, step_title):
        row_layout = QHBoxLayout()
        row_layout.addWidget(create_label(step_title))
        row_layout.addStretch(1)

        status_label = create_label(self.STATUS_PENDING, role="muted")
        row_layout.addWidget(status_label)
        self._step_status_labels.append(status_label)
        return row_layout

    def _select_book_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب فایل کتاب",
            "",
            "فایل‌های کتاب (*.pdf *.epub *.docx *.txt);;همهٔ فایل‌ها (*)",
        )
        if not file_path:
            return

        self.pure_file_path = file_path
        self._selected_file_path = file_path
        file_info = QFileInfo(file_path)

        self.file_name_label.setText(file_info.fileName())
        self.file_detail_label.setText(
            f"{self._format_file_size(file_info.size())}  ·  {file_info.suffix().upper()}"
        )

        if not self.database_name_input.text().strip():
            self.database_name_input.setText(file_info.completeBaseName())
        if not self.book_title_input.text().strip():
            self.book_title_input.setText(file_info.completeBaseName())

        self._update_start_button_state()

    @staticmethod
    def _format_file_size(size_in_bytes):
        size_in_megabytes = size_in_bytes / (1024 * 1024)
        formatted_size = to_persian_digits(f"{size_in_megabytes:.1f}").replace(".", "٫")
        return f"{formatted_size} مگابایت"

    def _start_preparation(self):

        if self.action_thread.isRunning():
            return

        book_name = self.database_name_input.text()
        book_title = self.book_title_input.text()
        writer = self.author_input.text()
        lang = self.language_combo.currentIndex()


        self.action_thread.set_parameters(
            file_path=self.pure_file_path,
            name=book_name,
            title=book_title,
            writer=writer,
            lang=lang
        )

        if os.path.exists(os.path.join(self.action_thread.folder_path, "book.db")):
            reply = QMessageBox.question(
                self,
                "Confirm",
                "برای این کتاب قبلاً دیتابیس ایجاد شده است. آیا مایل به ایجاد مجدد آن هستید؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.No:
                return

        self._is_preparing = True
        self._completed_step_count = 0
        self.progress_bar.setValue(0)
        self.view_databases_button.setVisible(False)
        self.status_message_label.setText("در حال آماده‌سازی دیتابیس...")

        self.action_thread.start()
        self._set_controls_enabled(False)
        self._set_step_state(0, self.STATUS_RUNNING)

    def _advance_preparation(self, step):
        self._set_step_state(step, self.STATUS_DONE)
        self._completed_step_count = step + 1

        total_step_count = len(self.PREPARATION_STEPS)
        self.progress_bar.setValue(int(self._completed_step_count * 100 / total_step_count))

        if self._completed_step_count < total_step_count:
            self._set_step_state(self._completed_step_count, self.STATUS_RUNNING)
        else:
            self._finish_preparation()

    def _finish_preparation(self):
        self._is_preparing = False
        self.status_message_label.setText("دیتابیس با موفقیت ساخته شد.")
        self.view_databases_button.setVisible(True)
        self.reset_button.setEnabled(True)
        self.select_file_button.setEnabled(True)
        self.database_created.emit(self._build_database_from_form(self.action_thread.pk, self.action_thread.sqlite_path, self.action_thread.faiss_path))
        self.action_thread.safe_release()

    def _build_database_from_form(self, pk, sqlite_path, faiss_path):
        book_title = self.book_title_input.text().strip() or self.database_name_input.text().strip()
        author = self.author_input.text().strip() or "نامشخص"

        return BookDatabase(
            pk=pk,
            database_name=self.database_name_input.text().strip(),
            book_title=book_title,
            author=author,
            created_date="امروز",
            page_count=0,
            chunk_count=0,
            language=self.language_combo.currentText(),
            sqlite_path=sqlite_path,
            faiss_path=faiss_path
        )

    def _set_step_state(self, step_index, status_text):
        status_label = self._step_status_labels[step_index]
        status_label.setText(status_text)

        if status_text == self.STATUS_PENDING:
            set_widget_role(status_label, "muted")
        else:
            set_widget_role(status_label, "accent")

    def _set_controls_enabled(self, is_enabled):
        self.select_file_button.setEnabled(is_enabled)
        self.reset_button.setEnabled(is_enabled)
        self.database_name_input.setEnabled(is_enabled)
        self.book_title_input.setEnabled(is_enabled)
        self.author_input.setEnabled(is_enabled)
        self.language_combo.setEnabled(is_enabled)
        self._update_start_button_state()

    def _update_start_button_state(self):
        has_file = bool(self._selected_file_path)
        has_database_name = bool(self.database_name_input.text().strip())
        is_idle = not self._is_preparing and self._completed_step_count == 0
        self.start_button.setEnabled(has_file and has_database_name and is_idle)

    def _reset_form(self):
        if self.action_thread.isRunning():
            return
        self.action_thread.safe_release()
        self._is_preparing = False
        self._completed_step_count = 0
        self._selected_file_path = ""

        self.file_name_label.setText(self.NO_FILE_TITLE)
        self.file_detail_label.setText(self.NO_FILE_HINT)
        self.database_name_input.clear()
        self.book_title_input.clear()
        self.author_input.clear()
        self.language_combo.setCurrentIndex(0)

        for step_index in range(len(self.PREPARATION_STEPS)):
            self._set_step_state(step_index, self.STATUS_PENDING)

        self.progress_bar.setValue(0)
        self.status_message_label.setText(self.IDLE_MESSAGE)
        self.view_databases_button.setVisible(False)
        self._set_controls_enabled(True)
