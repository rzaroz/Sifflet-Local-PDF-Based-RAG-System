import os
import theme
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QTextEdit
)
from modules.manager import ManageSetting
from modules.common import (
    PAGE_MARGINS,
    PAGE_SPACING,
    SectionCard,
    create_label,
    create_page_header,
    create_scroll_area,
)


SETTING = ManageSetting()

class SettingsPage(QWidget):
    theme_mode_changed = Signal(str)

    THEME_MODES = (
        ("خودکار (مطابق سیستم)", "auto"),
        ("روشن", "light"),
        ("تاریک", "dark"),
    )
    DEFAULT_FONT_SIZE = 10
    STATUS_MESSAGE_DURATION_MILLISECONDS = 2500

    DEFAULT_MAX_INPUT_TOKENS = 4096
    DEFAULT_MAX_OUTPUT_TOKENS = 1024
    MIN_INPUT_TOKENS = 512
    MAX_INPUT_TOKENS_LIMIT = 32768
    INPUT_TOKENS_STEP = 256
    MIN_OUTPUT_TOKENS = 128
    MAX_OUTPUT_TOKENS_LIMIT = 8192
    OUTPUT_TOKENS_STEP = 128

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_interface()

    def _build_interface(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(*PAGE_MARGINS)
        page_layout.setSpacing(PAGE_SPACING)

        page_layout.addWidget(
            create_page_header(
                "تنظیمات",
                "ظاهر، زبان و گزینه‌های عمومی نرم‌افزار را مدیریت کنید.",
            )
        )

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(PAGE_SPACING)
        content_layout.addWidget(self._build_appearance_card())
        content_layout.addWidget(self._build_system_role())
        content_layout.addWidget(self._build_token_card())
        content_layout.addWidget(self._build_storage_card())
        content_layout.addStretch(1)

        page_layout.addWidget(create_scroll_area(content_widget), 1)
        page_layout.addLayout(self._build_action_row())

    def _build_appearance_card(self):
        appearance_card = SectionCard("ظاهر")

        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(12)
        form_layout.setHorizontalSpacing(16)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)

        self.theme_combo = QComboBox()
        for display_text, mode_value in self.THEME_MODES:
            self.theme_combo.addItem(display_text, mode_value)

        self.theme_combo.setMinimumWidth(240)
        self.theme_combo.currentIndexChanged.connect(self._handle_theme_changed)
        self.theme_combo.setCurrentIndex(SETTING.settings["theme"])
        theme.set_mode(QApplication.instance(), self.THEME_MODES[SETTING.settings["theme"]][1])

        form_layout.addRow("تم برنامه", self.theme_combo)
        appearance_card.body_layout.addLayout(form_layout)

        return appearance_card

    def _build_system_role(self):
        role_card = SectionCard("پرامپت سیستم")

        role_card.body_layout.addWidget(
            create_label("پرامپت برای نقش سیستم", role="muted")
        )

        prompt_layout = QHBoxLayout()
        prompt_layout.setSpacing(10)

        self.prompt = QTextEdit()
        self.prompt.setText(SETTING.settings["system_role"])
        self.prompt.textChanged.connect(self._system_role_handler)
        self.prompt.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        prompt_layout.addWidget(self.prompt, 1)

        role_card.body_layout.addLayout(prompt_layout)
        return role_card

    def _system_role_handler(self):
        text = self.prompt.toPlainText()
        SETTING.set_item("system_role", text)

    def _create_token_slider(self, minimum, maximum, step, value, handler):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setSingleStep(step)
        slider.setPageStep(step * 4)
        slider.setTickPosition(QSlider.TickPosition.NoTicks)
        slider.setMinimumWidth(240)
        slider.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        value = self._snap(value, minimum, maximum, step)
        slider.setValue(value)

        value_label = QLabel(str(value))
        value_label.setMinimumWidth(56)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def on_value_changed(raw_value):
            snapped = self._snap(raw_value, minimum, maximum, step)
            if snapped != raw_value:
                slider.blockSignals(True)
                slider.setValue(snapped)
                slider.blockSignals(False)
            value_label.setText(str(snapped))
            handler(snapped)

        slider.valueChanged.connect(on_value_changed)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(12)
        row_layout.addWidget(slider, 1)
        row_layout.addWidget(value_label)

        container = QWidget()
        container.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        container.setLayout(row_layout)
        row_layout.setContentsMargins(0, 0, 0, 0)

        return slider, value_label, container

    @staticmethod
    def _snap(value, minimum, maximum, step):
        value = max(minimum, min(maximum, int(value)))
        snapped = minimum + round((value - minimum) / step) * step
        return max(minimum, min(maximum, snapped))

    def _build_token_card(self):
        token_card = SectionCard("توکن‌ها")

        token_card.body_layout.addWidget(
            create_label(
                "حداکثر تعداد توکن ورودی و خروجی مدل را با کشیدن اسلایدر تعیین کنید.",
                role="muted",
            )
        )

        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(12)
        form_layout.setHorizontalSpacing(16)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        (
            self.input_tokens_slider,
            self.input_tokens_label,
            input_container,
        ) = self._create_token_slider(
            self.MIN_INPUT_TOKENS,
            self.MAX_INPUT_TOKENS_LIMIT,
            self.INPUT_TOKENS_STEP,
            SETTING.settings.get("max_input_tokens", self.DEFAULT_MAX_INPUT_TOKENS),
            self._input_tokens_handler,
        )

        (
            self.output_tokens_slider,
            self.output_tokens_label,
            output_container,
        ) = self._create_token_slider(
            self.MIN_OUTPUT_TOKENS,
            self.MAX_OUTPUT_TOKENS_LIMIT,
            self.OUTPUT_TOKENS_STEP,
            SETTING.settings.get("max_output_tokens", self.DEFAULT_MAX_OUTPUT_TOKENS),
            self._output_tokens_handler,
        )

        form_layout.addRow("حداکثر توکن ورودی", input_container)
        form_layout.addRow("حداکثر توکن خروجی", output_container)
        token_card.body_layout.addLayout(form_layout)

        return token_card

    def _input_tokens_handler(self, value):
        SETTING.set_item("max_input_tokens", value)

    def _output_tokens_handler(self, value):
        SETTING.set_item("max_output_tokens", value)

    def _build_storage_card(self):
        storage_card = SectionCard("ذخیره‌سازی")

        storage_card.body_layout.addWidget(
            create_label("پوشهٔ ذخیرهٔ دیتابیس‌ها", role="muted")
        )

        path_layout = QHBoxLayout()
        path_layout.setSpacing(10)

        self.storage_path_input = QLineEdit(SETTING.settings["database_path"])
        self.storage_path_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        path_layout.addWidget(self.storage_path_input, 1)

        browse_button = QPushButton("انتخاب پوشه")
        browse_button.clicked.connect(self._choose_storage_directory)
        path_layout.addWidget(browse_button)

        storage_card.body_layout.addLayout(path_layout)
        return storage_card

    def _build_action_row(self):
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        self.reset_button = QPushButton("بازنشانی به پیش‌فرض")
        self.reset_button.setProperty("primary", True)
        self.reset_button.setMinimumWidth(140)
        self.reset_button.clicked.connect(self._reset_settings)

        self.status_label = create_label("", role="accent")

        action_layout.addWidget(self.reset_button)
        action_layout.addWidget(self.status_label)
        action_layout.addStretch(1)
        return action_layout

    @staticmethod
    def _default_storage_path():
        return os.path.join(os.path.expanduser("~"), "Sifflet", "Databases")

    def _handle_theme_changed(self):
        SETTING.set_item("theme", self.theme_combo.currentIndex())
        self.theme_mode_changed.emit(self.theme_combo.currentData())

    def _choose_storage_directory(self):
        selected_directory = QFileDialog.getExistingDirectory(
            self,
            "انتخاب پوشهٔ ذخیره‌سازی",
            self.storage_path_input.text(),
        )
        if selected_directory:
            self.storage_path_input.setText(selected_directory)
            SETTING.set_item("database_path", selected_directory)

    def _save_settings(self):
        self._show_status_message("تنظیمات ذخیره شد.")

    def _reset_settings(self):
        self.theme_combo.setCurrentIndex(0)
        self.storage_path_input.setText(self._default_storage_path())
        SETTING.reset_defaults()
        self.prompt.setText(SETTING.settings["system_role"])
        self.input_tokens_slider.setValue(
            self._snap(
                SETTING.settings.get("max_input_tokens", self.DEFAULT_MAX_INPUT_TOKENS),
                self.MIN_INPUT_TOKENS,
                self.MAX_INPUT_TOKENS_LIMIT,
                self.INPUT_TOKENS_STEP,
            )
        )
        self.output_tokens_slider.setValue(
            self._snap(
                SETTING.settings.get("max_output_tokens", self.DEFAULT_MAX_OUTPUT_TOKENS),
                self.MIN_OUTPUT_TOKENS,
                self.MAX_OUTPUT_TOKENS_LIMIT,
                self.OUTPUT_TOKENS_STEP,
            )
        )
        self._show_status_message("تنظیمات به حالت پیش‌فرض بازگشت.")

    def _show_status_message(self, message_text):
        self.status_label.setText(message_text)
        QTimer.singleShot(
            self.STATUS_MESSAGE_DURATION_MILLISECONDS,
            lambda: self.status_label.setText(""),
        )