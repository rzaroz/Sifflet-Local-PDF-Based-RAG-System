from PySide6.QtCore import QFileInfo, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from modules.manager import DataManager
from modules.model import LLMService
from modules.common import (
    PAGE_MARGINS,
    PAGE_SPACING,
    LocalModel,
    create_label,
    create_page_header,
    create_scroll_area,
    refresh_widget_style,
    to_persian_digits,
    load_models
)

session = DataManager()

class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setToolTip(text)
        self._apply_elision()

    def setText(self, text):
        self._full_text = text
        self.setToolTip(text)
        self._apply_elision()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_elision()

    def _apply_elision(self):
        available_width = max(self.width(), 10)
        elided_text = self.fontMetrics().elidedText(
            self._full_text,
            Qt.TextElideMode.ElideMiddle,
            available_width,
        )
        super().setText(elided_text)


LOAD_STATE_UNLOADED = "unloaded"
LOAD_STATE_LOADING = "loading"
LOAD_STATE_LOADED = "loaded"

class ModelCard(QFrame):
    activate_requested = Signal(str)
    load_requested = Signal(str)
    unload_requested = Signal(str)
    remove_requested = Signal(str)

    ACTIVATE_BUTTON_TEXT = "انتخاب به‌عنوان مدل فعال"
    ACTIVE_BUTTON_TEXT = "مدل فعال"

    def __init__(self, local_model, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.pk = local_model.pk
        self.file_path = local_model.file_path
        self._load_state = LOAD_STATE_UNLOADED
        self._build_interface(local_model)

    def _build_interface(self, local_model):
        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(22, 18, 22, 18)
        card_layout.setSpacing(10)

        title_layout = QHBoxLayout()
        title_layout.setSpacing(10)
        title_layout.addWidget(create_label(local_model.model_name, role="cardTitle"))

        self.state_badge_label = create_label("", role="accent")
        title_layout.addWidget(self.state_badge_label)
        title_layout.addStretch(1)

        self.load_button = QPushButton("لود مدل")
        self.load_button.setMinimumWidth(130)
        self.load_button.clicked.connect(self._handle_load_clicked)
        title_layout.addWidget(self.load_button)

        self.activate_button = QPushButton(self.ACTIVATE_BUTTON_TEXT)
        self.activate_button.setMinimumWidth(160)
        self.activate_button.clicked.connect(
            lambda: self.activate_requested.emit(self.file_path)
        )
        title_layout.addWidget(self.activate_button)

        remove_button = QPushButton("حذف")
        remove_button.clicked.connect(lambda: self.remove_requested.emit(self.file_path))
        title_layout.addWidget(remove_button)
        card_layout.addLayout(title_layout)

        path_label = ElidedLabel(local_model.file_path)
        path_label.setProperty("role", "muted")
        path_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        card_layout.addWidget(path_label)

        specifications_layout = QHBoxLayout()
        specifications_layout.setSpacing(32)
        specification_items = (
            ("قالب فایل", local_model.file_format),
            ("حجم فایل", local_model.file_size_text),
        )
        for label_text, value_text in specification_items:
            specifications_layout.addWidget(
                self._create_specification_widget(label_text, value_text)
            )
        specifications_layout.addStretch(1)
        card_layout.addLayout(specifications_layout)

        self.loading_progress_bar = QProgressBar()
        self.loading_progress_bar.setRange(0, 0)
        self.loading_progress_bar.setTextVisible(False)
        card_layout.addWidget(self.loading_progress_bar)

        self.set_state(False, LOAD_STATE_UNLOADED)

    @staticmethod
    def _create_specification_widget(label_text, value_text):
        specification_widget = QWidget()
        specification_layout = QHBoxLayout(specification_widget)
        specification_layout.setContentsMargins(0, 0, 0, 0)
        specification_layout.setSpacing(6)
        specification_layout.addWidget(create_label(f"{label_text}:", role="muted"))
        specification_layout.addWidget(create_label(value_text))
        return specification_widget

    def _handle_load_clicked(self):
        if self._load_state == LOAD_STATE_LOADED:
            self.unload_requested.emit(self.file_path)
        else:
            self.load_requested.emit(self.file_path)

    def set_state(self, is_active, load_state):
        self._load_state = load_state

        badge_texts = {
            LOAD_STATE_UNLOADED: "فعال",
            LOAD_STATE_LOADING: "در حال بارگذاری",
            LOAD_STATE_LOADED: "لود شده",
        }
        self.state_badge_label.setText(badge_texts[load_state])
        self.state_badge_label.setVisible(is_active)

        self.activate_button.setEnabled(not is_active)
        self.activate_button.setText(
            self.ACTIVE_BUTTON_TEXT if is_active else self.ACTIVATE_BUTTON_TEXT
        )
        self.activate_button.setProperty("primary", not is_active)
        refresh_widget_style(self.activate_button)

        load_button_texts = {
            LOAD_STATE_UNLOADED: "لود مدل",
            LOAD_STATE_LOADING: "در حال بارگذاری...",
            LOAD_STATE_LOADED: "آزادسازی مدل",
        }
        self.load_button.setVisible(is_active)
        self.load_button.setText(load_button_texts[load_state])
        self.load_button.setEnabled(load_state != LOAD_STATE_LOADING)
        self.load_button.setProperty("primary", load_state == LOAD_STATE_UNLOADED)
        refresh_widget_style(self.load_button)

        self.loading_progress_bar.setVisible(load_state == LOAD_STATE_LOADING)

        self.setProperty("selected", is_active)
        refresh_widget_style(self)


class ModelSelectionPage(QWidget):
    model_state_changed = Signal()

    MODEL_FILE_FILTER = (
        "فایل‌ مدل (*.gguf);;همهٔ فایل‌ها (*)"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._local_models = load_models()
        self._model_cards = {}
        self._active_file_path = ""
        self._loading_file_path = ""
        self._loaded_file_path = ""

        self._llm = LLMService.instance()
        self._llm.loaded.connect(self._on_model_loaded)
        self._llm.load_failed.connect(self._on_load_failed)

        self._build_interface()
        for local_model in self._local_models:
            self._add_card(local_model)
        self._refresh_state()

    def _build_interface(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(*PAGE_MARGINS)
        page_layout.setSpacing(PAGE_SPACING)

        header_layout = QHBoxLayout()
        header_layout.addWidget(
            create_page_header(
                "انتخاب مدل",
                "فایل مدل را از سیستم خود اضافه کنید و یکی را به‌عنوان مدل فعال برگزینید.",
            ),
            1,
        )
        self.add_model_button = QPushButton("افزودن مدل")
        self.add_model_button.setProperty("primary", True)
        self.add_model_button.setMinimumHeight(38)
        self.add_model_button.clicked.connect(self._add_model_from_file)
        header_layout.addWidget(self.add_model_button, 0, Qt.AlignmentFlag.AlignVCenter)
        page_layout.addLayout(header_layout)

        self.inactive_notice_label = create_label("", role="accent")
        page_layout.addWidget(self.inactive_notice_label)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        self.cards_layout = QVBoxLayout()
        self.cards_layout.setSpacing(14)
        content_layout.addLayout(self.cards_layout)
        content_layout.addWidget(self._build_empty_state())
        content_layout.addStretch(1)

        page_layout.addWidget(create_scroll_area(content_widget), 1)

    def _build_empty_state(self):
        self.empty_state_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setContentsMargins(0, 60, 0, 0)
        empty_layout.setSpacing(10)

        empty_layout.addWidget(
            create_label(
                "هنوز مدلی اضافه نشده است.",
                role="cardTitle",
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
        )
        empty_layout.addWidget(
            create_label(
                "برای گفت‌وگو با کتاب‌ها، یک فایل مدل را از سیستم خود انتخاب کنید.",
                role="muted",
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
        )
        return self.empty_state_widget

    def active_model_name(self):
        return self._model_name_for_path(self._active_file_path)

    def loaded_model_name(self):
        return self._model_name_for_path(self._loaded_file_path)

    def _model_name_for_path(self, file_path):
        if not file_path:
            return ""
        for local_model in self._local_models:
            if local_model.file_path == file_path:
                return local_model.model_name
        return ""

    def _add_model_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب فایل مدل",
            "",
            self.MODEL_FILE_FILTER,
        )
        if not file_path:
            return

        already_added = any(model.file_path == file_path for model in self._local_models)
        if not already_added:
            local_model = self._build_local_model(file_path)
            self._local_models.append(local_model)
            self._add_card(local_model)

        if not self._active_file_path:
            self._activate_model(file_path)
        else:
            self._refresh_state()

    @staticmethod
    def _build_local_model(file_path):
        new_model = session.new_model(file_path)
        file_info = QFileInfo(file_path)
        return LocalModel(
            pk=new_model.pk,
            file_path=file_path,
            model_name=file_info.completeBaseName(),
            file_format=file_info.suffix().upper() or "نامشخص",
            file_size_text=ModelSelectionPage._format_file_size(file_info.size()),
        )

    @staticmethod
    def _format_file_size(size_in_bytes):
        gigabyte = 1024 ** 3
        megabyte = 1024 ** 2
        if size_in_bytes >= gigabyte:
            value_text = f"{size_in_bytes / gigabyte:.1f}"
            unit_text = "گیگابایت"
        else:
            value_text = f"{size_in_bytes / megabyte:.1f}"
            unit_text = "مگابایت"
        return f"{to_persian_digits(value_text).replace('.', '٫')} {unit_text}"

    def _add_card(self, local_model):
        model_card = ModelCard(local_model)
        model_card.activate_requested.connect(self._activate_model)
        model_card.load_requested.connect(self._start_loading)
        model_card.unload_requested.connect(self._unload_model)
        model_card.remove_requested.connect(self._remove_model)
        self.cards_layout.addWidget(model_card)
        self._model_cards[local_model.file_path] = model_card

    def _activate_model(self, file_path):
        if file_path != self._active_file_path:
            self._reset_load_state()
        self._active_file_path = file_path
        self._refresh_state()
        self.model_state_changed.emit()

    def _start_loading(self, file_path):
        if file_path != self._active_file_path:
            return
        self._loaded_file_path = ""
        self._loading_file_path = file_path
        self._llm.load_model(file_path)
        self._refresh_state()
        self.model_state_changed.emit()

    def _on_model_loaded(self, file_path):
        if file_path != self._loading_file_path:
            return
        self._loaded_file_path = file_path
        self._loading_file_path = ""
        self._refresh_state()
        self.model_state_changed.emit()

    def _on_load_failed(self, file_path, message):
        if file_path != self._loading_file_path:
            return
        self._loading_file_path = ""
        self._refresh_state()
        self.model_state_changed.emit()
        QMessageBox.critical(self, "خطا در لود مدل", message)

    def _unload_model(self, file_path):
        if file_path == self._loaded_file_path:
            self._llm.unload_model()
            self._loaded_file_path = ""
        self._refresh_state()
        self.model_state_changed.emit()

    def _reset_load_state(self):
        if self._loading_file_path or self._loaded_file_path:
            self._llm.unload_model()
        self._loading_file_path = ""
        self._loaded_file_path = ""

    def _remove_model(self, file_path):
        self._local_models = [
            model for model in self._local_models if model.file_path != file_path
        ]
        removed_card = self._model_cards.pop(file_path, None)

        if removed_card is not None:
            session.delete_model(removed_card.pk)
            removed_card.deleteLater()

        if file_path == self._active_file_path:
            self._reset_load_state()
            self._active_file_path = ""


        self._refresh_state()
        self.model_state_changed.emit()

    def _refresh_state(self):
        for file_path, model_card in self._model_cards.items():
            is_active = file_path == self._active_file_path
            if file_path == self._loaded_file_path:
                load_state = LOAD_STATE_LOADED
            elif file_path == self._loading_file_path:
                load_state = LOAD_STATE_LOADING
            else:
                load_state = LOAD_STATE_UNLOADED
            model_card.set_state(is_active, load_state)

        has_models = bool(self._local_models)
        self.empty_state_widget.setVisible(not has_models)
        self._update_notice(has_models)

    def _update_notice(self, has_models):
        if not has_models or self._loaded_file_path:
            self.inactive_notice_label.setVisible(False)
            return

        if self._loading_file_path:
            notice_text = "در حال بارگذاری مدل؛ لطفاً کمی صبر کنید."
        elif self._active_file_path:
            notice_text = "مدل انتخاب شده است؛ برای شروع گفت‌وگو، آن را لود کنید."
        else:
            notice_text = "هیچ مدلی فعال نیست؛ ابتدا یک مدل را انتخاب و سپس لود کنید."

        self.inactive_notice_label.setText(notice_text)
        self.inactive_notice_label.setVisible(True)