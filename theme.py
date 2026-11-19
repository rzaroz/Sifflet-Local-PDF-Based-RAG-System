import os
import sys
import tempfile
from pathlib import Path
from PySide6.QtCore import Qt, QLocale
from PySide6.QtGui import QFont, QFontDatabase, QColor, QPalette


def get_base_path():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


LIGHT = dict(
    bg="#ffffff", base="#ffffff", alt="#fafafa", text="#171717",
    muted="#6f6f6f", border="#eaeaea", button="#ffffff", accent="#0070f3",
)
DARK = dict(
    bg="#000000", base="#0a0a0a", alt="#111111", text="#ededed",
    muted="#a1a1a1", border="#2e2e2e", button="#0a0a0a", accent="#3291ff",
)

MODE = "auto"

RTL = True 
PERSIAN_DIGITS = False
FONT_SIZE = 10.5

FONT_FAMILIES = ["Vazir", "Vazirmatn", "Segoe UI", "Tahoma", "Noto Sans Arabic", "Arial"]

_ARROW_DIR = Path(tempfile.mkdtemp(prefix="qt_arrows_"))


def _rgba(hex_color: str, alpha: float) -> str:
    c = QColor(hex_color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {int(alpha * 255)})"


def _arrow_files(color: str):
    key = color.lstrip("#")
    paths = {}
    for name, d in (("down", "M2.5 4.5 L6 8 L9.5 4.5"), ("up", "M2.5 7.5 L6 4 L9.5 7.5")):
        p = _ARROW_DIR / f"{name}_{key}.svg"
        if not p.exists():
            p.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" '
                f'viewBox="0 0 12 12"><path d="{d}" fill="none" stroke="#{key}" '
                'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            )
        paths[name] = p.as_posix()
    return paths["down"], paths["up"]


def _derive(c: dict) -> dict:
    d = dict(c)
    d["sel"] = _rgba(c["accent"], 0.16)
    d["hover"] = _rgba(c["text"], 0.06)
    d["handle"] = _rgba(c["muted"], 0.45)
    d["handle_hover"] = _rgba(c["muted"], 0.75)
    d["p_bg"], d["p_fg"] = c["text"], c["base"]
    d["p_hover"] = _rgba(c["text"], 0.85)
    d["arrow_down"], d["arrow_up"] = _arrow_files(c["muted"])
    d["pad_end"] = "padding-left" if RTL else "padding-right"
    d["menu_pad"] = "4px 12px 4px 22px" if RTL else "4px 22px 4px 12px"
    d["bd_menu_a"] = "border-left" if RTL else "border-right"
    d["bd_menu_b"] = "border-right" if RTL else "border-left"
    return d


QSS = """
QPushButton {
    background: @button@; color: @text@;
    border: 1px solid @border@; border-radius: 6px; padding: 4px 14px;
}
QPushButton:hover { background: @alt@; border-color: @muted@; }
QPushButton:pressed { background: @border@; }
QPushButton:checked { background: @alt@; border: 1px solid @text@; }
QPushButton:disabled { color: @muted@; background: @bg@; border-color: @border@; }
QPushButton[primary="true"] {
    background: @p_bg@; color: @p_fg@; border: 1px solid @p_bg@; font-weight: 600;
}
QPushButton[primary="true"]:hover { background: @p_hover@; }
QPushButton[primary="true"]:disabled { background: @border@; color: @muted@; border-color: @border@; }

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: @base@; color: @text@;
    border: 1px solid @border@; border-radius: 6px; padding: 3px 10px;
    selection-background-color: @accent@; selection-color: #ffffff;
}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover,
QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover { border: 1px solid @muted@; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border: 1px solid @text@; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    color: @muted@; background: @bg@;
}

QComboBox { @pad_end@: 28px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: center right; width: 26px; border: none; }
QComboBox::down-arrow { image: url(@arrow_down@); width: 12px; height: 12px; }
QComboBox QAbstractItemView {
    background: @base@; color: @text@; border: 1px solid @border@; border-radius: 6px;
    padding: 4px; outline: 0; selection-background-color: @sel@; selection-color: @text@;
}

QSpinBox, QDoubleSpinBox { @pad_end@: 24px; }
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border; subcontrol-position: top right; width: 20px; border: none; background: transparent;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border; subcontrol-position: bottom right; width: 20px; border: none; background: transparent;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url(@arrow_up@); width: 10px; height: 10px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url(@arrow_down@); width: 10px; height: 10px; }

QGroupBox {
    background: transparent; border: 1px solid @border@; border-radius: 8px;
    margin-top: 12px; padding: 14px 8px 8px 8px;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; color: @muted@; }

QTabWidget::pane { border: none; border-top: 1px solid @border@; }
QTabBar::tab {
    background: transparent; color: @muted@; padding: 6px 14px; margin-right: 2px;
    border: none; border-bottom: 2px solid transparent;
}
QTabBar::tab:hover:!selected { color: @text@; }
QTabBar::tab:selected { color: @text@; border-bottom: 2px solid @text@; }

QListWidget, QTableWidget, QTreeWidget {
    background: @base@; color: @text@; border: 1px solid @border@; border-radius: 6px;
    outline: 0; gridline-color: @border@; alternate-background-color: @alt@;
    selection-background-color: @sel@; selection-color: @text@;
}
QListWidget::item { padding: 6px 8px; margin: 1px 4px; border-radius: 4px; }
QListWidget::item:hover:!selected { background: @hover@; }
QListWidget::item:selected { background: @sel@; color: @text@; }
QTableWidget::item { padding: 4px 8px; }
QHeaderView::section {
    background: @bg@; color: @muted@; border: none; border-bottom: 1px solid @border@;
    padding: 6px 8px; font-weight: 600;
}
QTableCornerButton::section { background: @bg@; border: none; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: @handle@; border-radius: 3px; min-height: 28px; }
QScrollBar::handle:horizontal { background: @handle@; border-radius: 3px; min-width: 28px; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: @handle_hover@; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

QSlider::groove:horizontal { height: 4px; background: @border@; border-radius: 2px; }
QSlider::sub-page:horizontal { background: @text@; border-radius: 2px; }
QSlider::handle:horizontal {
    background: @base@; border: 2px solid @text@; width: 12px; height: 12px;
    margin: -7px 0; border-radius: 8px;
}
QProgressBar { background: @border@; border: none; border-radius: 3px; min-height: 6px; max-height: 6px; }
QProgressBar::chunk { background: @text@; border-radius: 3px; }

QMenuBar { background: @bg@; color: @text@; }
QMenuBar::item { padding: 4px 10px; border-radius: 4px; background: transparent; }
QMenuBar::item:selected { background: @hover@; }
QMenu { background: @base@; color: @text@; border: 1px solid @border@; padding: 4px; }
QMenu::item { padding: @menu_pad@; border-radius: 4px; }
QMenu::item:selected { background: @hover@; }
QMenu::separator { height: 1px; background: @border@; margin: 4px 6px; }

QToolBar { background: @bg@; border: none; border-bottom: 1px solid @border@; spacing: 4px; padding: 4px; }
QToolButton { background: transparent; color: @text@; border: none; border-radius: 4px; padding: 5px 10px; }
QToolButton:hover { background: @hover@; }
QToolButton:pressed { background: @sel@; }

QStatusBar { background: @bg@; color: @muted@; }
QToolTip { background: @base@; color: @text@; border: 1px solid @border@; padding: 4px 8px; border-radius: 4px; }
QWidget#sideMenu { @bd_menu_a@: 1px solid @border@; }
QWidget#sideMenuLeft { @bd_menu_b@: 1px solid @border@; }
QWidget#IfNullDashboard { border: 1px solid @border@; border-radius: 20px; }
QPushButton#SubmitButton { background: #007aff; color: white; font-weight: bold; }
QPushButton#CancelButton { background: #e52b50; color: white; font-weight: bold; }
QLabel#Title { font-size: 20px; font-weight: bold; }
"""


def _build_palette(c: dict) -> QPalette:
    p = QPalette()
    Q = QColor
    p.setColor(QPalette.Window, Q(c["bg"]))
    p.setColor(QPalette.WindowText, Q(c["text"]))
    p.setColor(QPalette.Base, Q(c["base"]))
    p.setColor(QPalette.AlternateBase, Q(c["alt"]))
    p.setColor(QPalette.Text, Q(c["text"]))
    p.setColor(QPalette.Button, Q(c["button"]))
    p.setColor(QPalette.ButtonText, Q(c["text"]))
    p.setColor(QPalette.ToolTipBase, Q(c["base"]))
    p.setColor(QPalette.ToolTipText, Q(c["text"]))
    p.setColor(QPalette.PlaceholderText, Q(c["muted"]))
    p.setColor(QPalette.Highlight, Q(c["accent"]))
    p.setColor(QPalette.HighlightedText, Q("#ffffff"))
    p.setColor(QPalette.Link, Q(c["accent"]))
    p.setColor(QPalette.Light, Q(c["base"]))
    p.setColor(QPalette.Midlight, Q(c["border"]))
    p.setColor(QPalette.Mid, Q(c["border"]))
    p.setColor(QPalette.Dark, Q(c["border"]))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, Q(c["muted"]))
    return p


def apply_theme(app):
    if MODE == "light":
        dark = False
    elif MODE == "dark":
        dark = True
    else:
        dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark

    c = _derive(DARK if dark else LIGHT)
    app.setPalette(_build_palette(c))

    qss = QSS
    for k, v in c.items():
        qss = qss.replace(f"@{k}@", v)
    app.setStyleSheet(qss)


def setup_theme(app):
    app.setStyle("Fusion")

    base = get_base_path()
    loaded = []
    for name in ("Vazir-Regular", "Vazir-Medium", "Vazir-Bold"):
        path = os.path.join(base, "assets", "fonts", f"{name}.ttf")
        if os.path.exists(path):
            fid = QFontDatabase.addApplicationFont(path)
            if fid != -1:
                loaded += QFontDatabase.applicationFontFamilies(fid)

    font = app.font()
    font.setFamilies(list(dict.fromkeys(loaded)) + FONT_FAMILIES)
    font.setPointSizeF(FONT_SIZE)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    if RTL:
        app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    if PERSIAN_DIGITS:
        QLocale.setDefault(QLocale(QLocale.Language.Persian, QLocale.Country.Iran))

    apply_theme(app)
    app.styleHints().colorSchemeChanged.connect(
        lambda _s: apply_theme(app) if MODE == "auto" else None
    )


def set_mode(app, mode: str):
    global MODE
    MODE = mode
    apply_theme(app)