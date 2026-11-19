from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from modules.manager import DataManager
from modules.common import (
    PAGE_MARGINS,
    PAGE_SPACING,
    ClickableCard,
    create_label,
    create_page_header,
    create_scroll_area,
)

session = DataManager()

class DatabaseCard(ClickableCard):
    open_requested = Signal(object)
    delete_requested = Signal(object)

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self._database = database
        self.setMinimumHeight(128)
        self._build_interface()
        self.clicked.connect(self._emit_open_requested)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _build_interface(self):
        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(22, 20, 22, 18)
        card_layout.setSpacing(4)

        title_layout = QHBoxLayout()
        title_layout.addWidget(create_label(self._database.book_title, role="cardTitle"))
        title_layout.addStretch(1)

        delete_button = QToolButton()
        delete_button.setText("حذف")
        delete_button.setCursor(Qt.CursorShape.ArrowCursor)
        delete_button.clicked.connect(self._emit_delete_requested)
        title_layout.addWidget(delete_button)
        card_layout.addLayout(title_layout)
        card_layout.addWidget(create_label(self._database.author, role="muted"))
        card_layout.addStretch(1)

        footer_layout = QHBoxLayout()
        footer_layout.addWidget(
            create_label(
                f"{self._database.created_date}  ·  {self._database.language}",
                role="muted",
            )
        )
        footer_layout.addStretch(1)
        footer_layout.addWidget(create_label("ورود ←", role="accent"))
        card_layout.addLayout(footer_layout)

    def _emit_open_requested(self):
        self.open_requested.emit(self._database)

    def _emit_delete_requested(self):
        session.delete_database(self._database.pk)
        self.delete_requested.emit(self._database)

    def _show_context_menu(self, position):
        context_menu = QMenu(self)
        open_action = context_menu.addAction("ورود به گفت‌وگو")
        delete_action = context_menu.addAction("حذف دیتابیس")
        chosen_action = context_menu.exec(self.mapToGlobal(position))

        if chosen_action is open_action:
            self._emit_open_requested()
        elif chosen_action is delete_action:
            self._emit_delete_requested()


class DatabaseListPage(QWidget):
    database_selected = Signal(object)
    database_deleted = Signal(object)
    create_requested = Signal()

    COLUMN_COUNT = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._databases = []
        self._build_interface()

    def _build_interface(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(*PAGE_MARGINS)
        page_layout.setSpacing(PAGE_SPACING)

        header_layout = QHBoxLayout()
        header_layout.addWidget(
            create_page_header(
                "دیتابیس‌های من",
                "یک دیتابیس را انتخاب کنید و با محتوای همان کتاب گفت‌وگو کنید.",
            ),
            1,
        )

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجوی دیتابیس یا کتاب...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(280)
        self.search_input.textChanged.connect(self._refresh_cards)
        header_layout.addWidget(self.search_input, 0, Qt.AlignmentFlag.AlignVCenter)
        page_layout.addLayout(header_layout)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(PAGE_SPACING)

        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(PAGE_SPACING)
        for column in range(self.COLUMN_COUNT):
            self.cards_layout.setColumnStretch(column, 1)

        content_layout.addWidget(self.cards_container)
        content_layout.addWidget(self._build_empty_state())
        content_layout.addStretch(1)

        page_layout.addWidget(create_scroll_area(content_widget), 1)

    def _build_empty_state(self):
        self.empty_state_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setContentsMargins(0, 60, 0, 0)
        empty_layout.setSpacing(12)

        self.empty_message_label = create_label(
            "",
            role="muted",
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        empty_layout.addWidget(self.empty_message_label)

        self.empty_create_button = QPushButton("ایجاد دیتابیس جدید")
        self.empty_create_button.setProperty("primary", True)
        self.empty_create_button.clicked.connect(self.create_requested.emit)
        empty_layout.addWidget(self.empty_create_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.empty_state_widget.setVisible(False)
        return self.empty_state_widget

    def set_databases(self, databases):
        self._databases = list(databases)
        self._refresh_cards()

    def add_database(self, database):
        self._databases.insert(0, database)
        self._refresh_cards()

    def database_count(self):
        return len(self._databases)

    def _refresh_cards(self):
        self._clear_cards()

        search_text = self.search_input.text().strip().lower()
        visible_databases = [
            database
            for database in self._databases
            if self._matches_search(database, search_text)
        ]

        for position, database in enumerate(visible_databases):
            card = DatabaseCard(database)
            card.open_requested.connect(self.database_selected.emit)
            card.delete_requested.connect(self._confirm_and_delete_database)
            row, column = divmod(position, self.COLUMN_COUNT)
            self.cards_layout.addWidget(card, row, column)

        self._update_empty_state(has_results=bool(visible_databases), search_text=search_text)

    def _confirm_and_delete_database(self, database):
        confirmation_box = QMessageBox(self)
        confirmation_box.setIcon(QMessageBox.Icon.Warning)
        confirmation_box.setWindowTitle("حذف دیتابیس")
        confirmation_box.setText(f"دیتابیس «{database.database_name}» حذف شود؟")
        confirmation_box.setInformativeText("این کار قابل بازگشت نیست.")

        delete_button = confirmation_box.addButton("حذف", QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = confirmation_box.addButton("انصراف", QMessageBox.ButtonRole.RejectRole)
        confirmation_box.setDefaultButton(cancel_button)
        confirmation_box.exec()
        if confirmation_box.clickedButton() is not delete_button:
            return

        self._databases = [item for item in self._databases if item is not database]
        self._refresh_cards()
        self.database_deleted.emit(database)

    def _clear_cards(self):
        while self.cards_layout.count():
            layout_item = self.cards_layout.takeAt(0)
            card_widget = layout_item.widget()
            if card_widget is not None:
                card_widget.deleteLater()

    @staticmethod
    def _matches_search(database, search_text):
        if not search_text:
            return True
        searchable_text = f"{database.database_name} {database.book_title} {database.author}".lower()
        return search_text in searchable_text

    def _update_empty_state(self, has_results, search_text):
        self.empty_state_widget.setVisible(not has_results)
        if has_results:
            return

        if search_text:
            self.empty_message_label.setText("موردی با این جستجو پیدا نشد.")
            self.empty_create_button.setVisible(False)
        else:
            self.empty_message_label.setText("هنوز دیتابیسی ساخته نشده است.")
            self.empty_create_button.setVisible(True)