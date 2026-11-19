from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from modules.common import PageIndex, create_label, load_scaled_pixmap


class Sidebar(QFrame):
    page_requested = Signal(int)

    SIDEBAR_WIDTH = 240
    NAVIGATION_ITEMS = (
        ("داشبورد", PageIndex.DASHBOARD),
        ("ایجاد دیتابیس جدید", PageIndex.CREATE_DATABASE),
        ("انتخاب مدل", PageIndex.MODEL_SELECTION),
        ("دیتابیس‌های من", PageIndex.DATABASE_LIST),
        ("تنظیمات", PageIndex.SETTINGS),
    )

    HIGHLIGHT_OVERRIDES = {
        PageIndex.CHAT: PageIndex.DATABASE_LIST,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sideMenu")
        self.setFixedWidth(self.SIDEBAR_WIDTH)
        self._build_interface()

    def _build_interface(self):
        sidebar_layout = QVBoxLayout(self)
        sidebar_layout.setContentsMargins(16, 24, 16, 16)
        sidebar_layout.setSpacing(16)

        logo_label = create_label(alignment=Qt.AlignmentFlag.AlignCenter)
        logo_label.setPixmap(load_scaled_pixmap("logo.png", 150))
        sidebar_layout.addWidget(logo_label)

        self.navigation_list = QListWidget()
        self.navigation_list.setObjectName("NavigationList")
        self.navigation_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.navigation_list.setCursor(Qt.CursorShape.PointingHandCursor)

        for item_text, page_index in self.NAVIGATION_ITEMS:
            navigation_item = QListWidgetItem(item_text)
            navigation_item.setData(Qt.ItemDataRole.UserRole, int(page_index))
            navigation_item.setSizeHint(QSize(0, 42))
            self.navigation_list.addItem(navigation_item)

        self.navigation_list.itemClicked.connect(self._handle_item_clicked)
        sidebar_layout.addWidget(self.navigation_list, 1)

        version_label = create_label(
            "Sifflet · نسخهٔ ۰٫۱",
            role="muted",
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        sidebar_layout.addWidget(version_label)

    def highlight_page(self, page_index):
        target_page = self.HIGHLIGHT_OVERRIDES.get(PageIndex(page_index), PageIndex(page_index))

        for row in range(self.navigation_list.count()):
            navigation_item = self.navigation_list.item(row)
            item_page = navigation_item.data(Qt.ItemDataRole.UserRole)
            if item_page == int(target_page):
                self.navigation_list.setCurrentItem(navigation_item)
                return

    def _handle_item_clicked(self, navigation_item):
        page_index = navigation_item.data(Qt.ItemDataRole.UserRole)
        self.page_requested.emit(page_index)
