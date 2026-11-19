import os
import sys
import os.path
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
    QMessageBox,
)
import struct
import theme
from modules.chat import ChatPage
from modules.common import (
    PageIndex,
    build_sample_databases,
    get_asset_path,
)
from modules.splash import StartupSplash
from modules.create_database import CreateDatabasePage
from modules.dashboard import DashboardPage
from modules.database_list import DatabaseListPage
from modules.model_selection import ModelSelectionPage
from modules.settings import SettingsPage
from modules.sidebar import Sidebar
from modules.styles import EXTRA_QSS
from utils.embedder import EmbedderService
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_public_key

BRAND_ACCENT_LIGHT = "#c42a5b"
BRAND_ACCENT_DARK = "#e2467d"


def configure_theme():
    theme.LIGHT["accent"] = BRAND_ACCENT_LIGHT
    theme.DARK["accent"] = BRAND_ACCENT_DARK
    theme.PERSIAN_DIGITS = True
    theme.QSS += EXTRA_QSS

def get_base_path():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

class MainWindow(QMainWindow):
    ROOT_WORKSPACE_INDEX = 1

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sifflet")
        self.setWindowIcon(QIcon(get_asset_path("logoicon.png")))
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)

        self._build_interface()
        self._connect_signals()
        self._load_sample_data()

    def _build_interface(self):
        self.root_stack = QStackedWidget()
        self.setCentralWidget(self.root_stack)

        self.root_stack.addWidget(self._build_workspace())
        self.root_stack.setCurrentIndex(self.ROOT_WORKSPACE_INDEX)

    def _build_workspace(self):
        workspace_widget = QWidget()
        workspace_layout = QHBoxLayout(workspace_widget)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        self.sidebar = Sidebar()
        workspace_layout.addWidget(self.sidebar)

        self.dashboard_page = DashboardPage()
        self.create_database_page = CreateDatabasePage()
        self.model_selection_page = ModelSelectionPage()
        self.database_list_page = DatabaseListPage()
        self.settings_page = SettingsPage()
        self.chat_page = ChatPage()

        self.content_stack = QStackedWidget()
        ordered_pages = (
            (PageIndex.DASHBOARD, self.dashboard_page),
            (PageIndex.CREATE_DATABASE, self.create_database_page),
            (PageIndex.MODEL_SELECTION, self.model_selection_page),
            (PageIndex.DATABASE_LIST, self.database_list_page),
            (PageIndex.SETTINGS, self.settings_page),
            (PageIndex.CHAT, self.chat_page),
        )
        for expected_index, page_widget in ordered_pages:
            actual_index = self.content_stack.addWidget(page_widget)
            assert actual_index == int(expected_index)

        workspace_layout.addWidget(self.content_stack, 1)
        return workspace_widget

    def _connect_signals(self):
        self.sidebar.page_requested.connect(self.show_page)
        self.dashboard_page.section_requested.connect(self.show_page)

        self.create_database_page.database_created.connect(self._handle_database_created)
        self.create_database_page.view_databases_requested.connect(
            lambda: self.show_page(PageIndex.DATABASE_LIST)
        )

        self.model_selection_page.model_state_changed.connect(self._refresh_summaries)
        self.chat_page.model_selection_requested.connect(
            lambda: self.show_page(PageIndex.MODEL_SELECTION)
        )

        self.database_list_page.database_selected.connect(self._open_chat)
        self.database_list_page.database_deleted.connect(
            lambda database: self._refresh_summaries()
        )
        self.database_list_page.create_requested.connect(
            lambda: self.show_page(PageIndex.CREATE_DATABASE)
        )

        self.chat_page.back_requested.connect(
            lambda: self.show_page(PageIndex.DATABASE_LIST)
        )
        self.settings_page.theme_mode_changed.connect(self._apply_theme_mode)

    def _load_sample_data(self):
        self.database_list_page.set_databases(build_sample_databases())
        self._refresh_summaries()

    def _show_workspace(self):
        self.root_stack.setCurrentIndex(self.ROOT_WORKSPACE_INDEX)
        self.show_page(PageIndex.DASHBOARD)

    def show_page(self, page_index):
        self.content_stack.setCurrentIndex(int(page_index))
        self.sidebar.highlight_page(page_index)

    def _open_chat(self, database):
        self.chat_page.load_database(database)
        self.show_page(PageIndex.CHAT)

    def _handle_database_created(self, database):
        self.database_list_page.add_database(database)
        self._refresh_summaries()

    def _refresh_summaries(self):
        active_model_name = self.model_selection_page.active_model_name()
        loaded_model_name = self.model_selection_page.loaded_model_name()
        self.dashboard_page.set_database_count(self.database_list_page.database_count())
        self.dashboard_page.set_model_status(active_model_name, bool(loaded_model_name))

        self.chat_page.set_active_model_name(loaded_model_name)

    @staticmethod
    def _apply_theme_mode(mode_value):
        theme.set_mode(QApplication.instance(), mode_value)


def fatal(message):
    box = QMessageBox()
    box.setWindowTitle("Sifflet")
    box.setIcon(QMessageBox.Icon.Critical)
    box.setText(message)
    box.exec()
    sys.exit(1)


def main():
    application = QApplication(sys.argv)
    application.setApplicationName("Sifflet")
    application.setWindowIcon(QIcon(get_asset_path("logoicon.png")))
    configure_theme()
    theme.setup_theme(application)

    PUBLIC_KEY_PEM = """\
    -----BEGIN PUBLIC KEY-----
    MCowBQYDK2VwAyEAxL4adsD6qDwCe3Ft8xprukaeKfKI8taqVjwj/AVzuYU=
    -----END PUBLIC KEY-----
    """

    base = get_base_path()
    license_path = os.path.join(base, "license.licence")

    if not os.path.exists(license_path):
        fatal("فایل لایسنس یافت نشد. امکان استفاده از برنامه وجود ندارد.")
    data = Path(license_path).read_bytes()

    public_key = load_pem_public_key(PUBLIC_KEY_PEM.encode())

    if data[:4] != b"ELIC":
        fatal("فرمت فایل لایسنس معتبر نیست.")

    version, payload_length = struct.unpack(">BI", data[4:9])

    if version != 1 or len(data) != 9 + payload_length + 64:
        fatal("ساختار فایل لایسنس معتبر نیست یا نسخه آن پشتیبانی نمی‌شود.")

    payload = data[9:9 + payload_length]
    signature = data[9 + payload_length:]

    try:
        public_key.verify(signature, payload)
    except InvalidSignature:
        fatal("اعتبار امضای دیجیتال لایسنس تأیید نشد. فایل ممکن است دستکاری شده باشد.")

    embedder_path = os.path.join(base, "embedder")
    llama_path = os.path.join(base, "llama")

    if not os.path.exists(llama_path):
        fatal("فولدر llama در پوشه نرم افزار یافت نشد. لطفا llama.cpp مورد نظر خود را دانلود و در پوشه نرم افزار در فولدر llama قرار دهید.")

    if not os.path.exists(embedder_path):
        fatal("فولدر embedder در پوشه نرم افزار یافت نشد. لطفا Embedder مورد نظر خود را دانلود و در پوشه نرم افزار در فولدر embedder قرار دهید.")

    embedder = EmbedderService.instance()
    application.aboutToQuit.connect(embedder.shutdown)

    windows = {}
    splash = StartupSplash(embedder)

    def open_main_window():
        windows["main"] = MainWindow()
        windows["main"].show()
        splash.close()

    splash.finished.connect(open_main_window)
    splash.show()
    embedder.start()

    sys.exit(application.exec())


if __name__ == "__main__":
    main()