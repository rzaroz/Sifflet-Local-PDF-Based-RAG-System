from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from modules.retriever import BookRetriever
from modules.manager import ManageSetting
from modules.mdrender import render_markdown
from modules.model import LLMService
from modules.common import (
    PAGE_MARGINS,
    PAGE_SPACING,
    ROLE_ASSISTANT,
    ROLE_USER,
    ChatMessage,
    Conversation,
    SectionCard,
    create_label,
    create_scroll_area,
    load_conversations,
    session,
)

SETTING = ManageSetting()

class MessageBubble(QFrame):
    MAXIMUM_BUBBLE_WIDTH = 640

    def __init__(self, chat_message, parent=None):
        super().__init__(parent)

        self._is_user_message = chat_message.role == ROLE_USER
        self.setObjectName("UserBubble" if self._is_user_message else "AssistantBubble")
        self.setMaximumWidth(self.MAXIMUM_BUBBLE_WIDTH)

        bubble_layout = QVBoxLayout(self)
        bubble_layout.setContentsMargins(16, 12, 16, 12)
        bubble_layout.setSpacing(6)

        self.text_label = create_label("", word_wrap=True)
        self.text_label.setTextFormat(
            Qt.TextFormat.PlainText if self._is_user_message else Qt.TextFormat.RichText
        )
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble_layout.addWidget(self.text_label)
        self.set_text(chat_message.text)

        if chat_message.source_note:
            bubble_layout.addWidget(create_label(chat_message.source_note, role="muted"))

    def set_text(self, text):
        self.text_label.setText(text if self._is_user_message else render_markdown(text))

class ChatPage(QWidget):
    back_requested = Signal()
    model_selection_requested = Signal()

    HISTORY_PANEL_WIDTH = 260
    GENERATING_PLACEHOLDER_TEXT = "…"
    EMPTY_ANSWER_TEXT = "(پاسخی تولید نشد)"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_database = None
        self._active_model_name = ""
        self._conversations = []
        self._current_conversation = None
        self._message_rows = []
        self._suggestion_buttons = []

        self._is_generating = False
        self._pending_conversation = None
        self._streaming_bubble = None
        self._streaming_text = ""


        self._llm = LLMService.instance()
        self._llm.token.connect(self._on_token_received)
        self._llm.finished.connect(self._on_generation_finished)
        self._llm.error.connect(self._on_generation_error)

        self._build_interface()
        self._update_chat_availability()

    def _build_interface(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(*PAGE_MARGINS)
        page_layout.setSpacing(PAGE_SPACING)

        page_layout.addLayout(self._build_top_bar())

        body_layout = QHBoxLayout()
        body_layout.setSpacing(PAGE_SPACING)
        body_layout.addLayout(self._build_conversation_column(), 1)
        body_layout.addWidget(self._build_history_panel())
        page_layout.addLayout(body_layout, 1)

    def _build_top_bar(self):
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setSpacing(16)

        back_button = QPushButton("→ بازگشت به دیتابیس‌ها")
        back_button.clicked.connect(self.back_requested.emit)
        top_bar_layout.addWidget(back_button)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        self.book_title_label = create_label("", role="pageTitle")
        self.database_info_label = create_label("", role="muted")
        title_layout.addWidget(self.book_title_label)
        title_layout.addWidget(self.database_info_label)
        top_bar_layout.addLayout(title_layout, 1)

        new_conversation_button = QPushButton("گفت‌وگوی جدید")
        new_conversation_button.clicked.connect(self._start_new_conversation)
        top_bar_layout.addWidget(new_conversation_button)
        return top_bar_layout

    def _build_conversation_column(self):
        column_layout = QVBoxLayout()
        column_layout.setSpacing(12)

        messages_container = QWidget()
        self.messages_layout = QVBoxLayout(messages_container)
        self.messages_layout.setContentsMargins(4, 4, 4, 4)
        self.messages_layout.setSpacing(14)

        self.welcome_widget = self._build_welcome_widget()
        self.messages_layout.addWidget(self.welcome_widget)
        self.messages_layout.addStretch(1)

        self.messages_scroll_area = create_scroll_area(messages_container)
        column_layout.addWidget(self.messages_scroll_area, 1)

        self.scope_note_label = create_label("", role="muted")
        column_layout.addWidget(self.scope_note_label)
        column_layout.addWidget(self._build_model_notice())
        column_layout.addLayout(self._build_input_row())
        return column_layout

    def _build_welcome_widget(self):
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.setContentsMargins(0, 40, 0, 0)
        welcome_layout.setSpacing(10)

        welcome_layout.addWidget(
            create_label(
                "دربارهٔ این کتاب بپرسید",
                role="cardTitle",
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
        )
        welcome_layout.addWidget(
            create_label(
                "پاسخ‌ها فقط از محتوای کتاب انتخاب‌شده استخراج می‌شوند.",
                role="muted",
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
        )
        welcome_layout.addSpacing(8)

        return welcome_widget

    def _build_model_notice(self):
        self.model_notice_frame = QFrame()
        self.model_notice_frame.setObjectName("Card")

        notice_layout = QHBoxLayout(self.model_notice_frame)
        notice_layout.setContentsMargins(16, 10, 16, 10)
        notice_layout.addWidget(
            create_label("برای گفت‌وگو ابتدا باید یک مدل را انتخاب و لود کنید.", role="accent")
        )
        notice_layout.addStretch(1)

        select_model_button = QPushButton("رفتن به صفحهٔ مدل‌ها")
        select_model_button.clicked.connect(self.model_selection_requested.emit)
        notice_layout.addWidget(select_model_button)
        return self.model_notice_frame

    def _build_input_row(self):
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("سؤال خود را دربارهٔ این کتاب بنویسید...")
        self.question_input.setMinimumHeight(42)
        self.question_input.returnPressed.connect(self._send_question)
        input_layout.addWidget(self.question_input, 1)

        self.send_button = QPushButton("ارسال")
        self.send_button.setProperty("primary", True)
        self.send_button.setMinimumSize(100, 42)
        self.send_button.clicked.connect(self._handle_send_button_clicked)
        input_layout.addWidget(self.send_button)
        return input_layout

    def _build_history_panel(self):
        history_card = SectionCard("تاریخچهٔ گفت‌وگوها")
        history_card.setFixedWidth(self.HISTORY_PANEL_WIDTH)

        self.history_list = QListWidget()
        self.history_list.setObjectName("HistoryList")
        self.history_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.history_list.itemClicked.connect(self._open_conversation)
        self.history_list.itemSelectionChanged.connect(self._update_delete_button_state)
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self._show_history_menu)
        history_card.body_layout.addWidget(self.history_list, 1)

        self.delete_conversation_button = QPushButton("حذف گفت‌وگوی انتخاب‌شده")
        self.delete_conversation_button.clicked.connect(self._delete_selected_conversation)
        history_card.body_layout.addWidget(self.delete_conversation_button)
        self._update_delete_button_state()
        return history_card

    def set_active_model_name(self, model_name):
        self._active_model_name = model_name
        self._refresh_database_info()
        self._update_chat_availability()
        if not model_name and self._is_generating:
            self._llm.stop()

    def _update_chat_availability(self):
        """بدون مدل فعال، ارسال سؤال و پیشنهادها غیرفعال می‌شوند."""
        is_chat_available = bool(self._active_model_name)

        self.question_input.setEnabled(is_chat_available)
        self.send_button.setEnabled(is_chat_available)
        for suggestion_button in self._suggestion_buttons:
            suggestion_button.setEnabled(is_chat_available)
        self.model_notice_frame.setVisible(not is_chat_available)

        if is_chat_available:
            self.question_input.setPlaceholderText("سؤال خود را دربارهٔ این کتاب بنویسید...")
        else:
            self.question_input.setPlaceholderText("ابتدا یک مدل را لود کنید")

    def load_database(self, database):
        self._cancel_generation()

        self._active_database = database
        self.book_title_label.setText(database.book_title)
        self.scope_note_label.setText(
            f"پاسخ‌ها فقط بر اساس محتوای «{database.book_title}» تولید می‌شوند."
        )
        self._refresh_database_info()

        self._conversations = load_conversations(database)
        self._current_conversation = None
        self._populate_history_list()
        self._clear_messages()

    def _refresh_database_info(self):
        if self._active_database is None:
            return

        info_text = f"دیتابیس فعال: {self._active_database.database_name}"
        if self._active_model_name:
            info_text += f"  ·  مدل: {self._active_model_name}"
        self.database_info_label.setText(info_text)

    def _populate_history_list(self):
        self.history_list.clear()
        for conversation in self._conversations:
            history_item = QListWidgetItem(conversation.title)
            history_item.setSizeHint(QSize(0, 38))
            self.history_list.addItem(history_item)
        self._update_delete_button_state()

    def _update_delete_button_state(self):
        has_selection = self.history_list.currentRow() >= 0
        self.delete_conversation_button.setEnabled(has_selection)

    def _show_history_menu(self, position):
        history_item = self.history_list.itemAt(position)
        if history_item is None:
            return

        conversation_row = self.history_list.row(history_item)
        history_menu = QMenu(self)
        delete_action = history_menu.addAction("حذف گفت‌وگو")
        chosen_action = history_menu.exec(self.history_list.viewport().mapToGlobal(position))
        if chosen_action is delete_action:
            self._delete_conversation(conversation_row)

    def _delete_selected_conversation(self):
        self._delete_conversation(self.history_list.currentRow())

    def _delete_conversation(self, conversation_row):
        if not 0 <= conversation_row < len(self._conversations):
            return

        conversation = self._conversations[conversation_row]
        if not self._confirm_deletion(conversation.title):
            return

        if conversation is self._pending_conversation:
            self._cancel_generation()

        self._conversations.pop(conversation_row)
        self._delete_conversation_from_storage(conversation)
        was_open = conversation is self._current_conversation
        if was_open:
            self._current_conversation = None
            self._clear_messages()

        self._populate_history_list()
        if self._current_conversation is not None:
            self.history_list.setCurrentRow(self._conversations.index(self._current_conversation))

    def _confirm_deletion(self, conversation_title):
        confirmation_box = QMessageBox(self)
        confirmation_box.setIcon(QMessageBox.Icon.Question)
        confirmation_box.setWindowTitle("حذف گفت‌وگو")
        confirmation_box.setText(f"گفت‌وگوی «{conversation_title}» حذف شود؟")
        confirmation_box.setInformativeText("این کار قابل بازگشت نیست.")

        delete_button = confirmation_box.addButton("حذف", QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = confirmation_box.addButton("انصراف", QMessageBox.ButtonRole.RejectRole)
        confirmation_box.setDefaultButton(cancel_button)
        confirmation_box.exec()
        return confirmation_box.clickedButton() is delete_button

    def _start_new_conversation(self):
        self.history_list.clearSelection()
        self.history_list.setCurrentRow(-1)
        self._current_conversation = None
        self._clear_messages()

    def _open_conversation(self, history_item):
        conversation = self._conversations[self.history_list.row(history_item)]
        self._current_conversation = conversation
        self._clear_messages()
        for chat_message in conversation.messages:
            self._append_message(chat_message)

        if conversation is self._pending_conversation:
            self._streaming_bubble = self._append_message(
                ChatMessage(
                    ROLE_ASSISTANT,
                    self._streaming_text or self.GENERATING_PLACEHOLDER_TEXT,
                )
            )

    def _clear_messages(self):
        for message_row in self._message_rows:
            message_row.deleteLater()
        self._message_rows.clear()
        self._streaming_bubble = None
        self.welcome_widget.setVisible(True)

    def _use_suggested_question(self, question_text):
        self.question_input.setText(question_text)
        self.question_input.setFocus()

    def _handle_send_button_clicked(self):
        if self._is_generating:
            self._llm.stop()
        else:
            self._send_question()

    def _send_question(self):
        question_text = self.question_input.text().strip()
        if (
            not question_text
            or self._active_database is None
            or not self._active_model_name
            or self._is_generating
        ):
            return

        self.question_input.clear()

        conversation = self._ensure_current_conversation(question_text)
        user_message = ChatMessage(ROLE_USER, question_text)
        conversation.messages.append(user_message)
        self._save_message(conversation, user_message)  # جدید
        self._append_message(user_message)

        self._pending_conversation = conversation
        self._streaming_text = ""
        self._streaming_bubble = self._append_message(
            ChatMessage(ROLE_ASSISTANT, self.GENERATING_PLACEHOLDER_TEXT)
        )
        self._set_generating(True)
        self._llm.ask(self._build_prompt(conversation, self._active_database))

    @staticmethod
    def _build_prompt(conversation, database):
        question = conversation.messages[-1].text
        passages = BookRetriever.search(database, question)

        context = "\n\n".join(
            f"[بخش {number}]\n{text[:1500]}" for number, text in enumerate(passages, start=1)
        )

        prompt_lines = [
            SETTING.settings.get("system_role") or SETTING.defaults["system_role"],
            "",
            "RAG SYSTEM CONTEXT:",
            context or "No context found",
            "",
        ]
        for chat_message in conversation.messages:
            speaker = "کاربر" if chat_message.role == ROLE_USER else "دستیار"
            prompt_lines.append(f"{speaker}: {chat_message.text}")
        prompt_lines.append("دستیار:")
        return "\n".join(prompt_lines)

    def _on_token_received(self, token_text):
        if self._pending_conversation is None:
            return
        self._streaming_text += token_text
        if self._streaming_bubble is not None:
            self._streaming_bubble.set_text(self._streaming_text)
            QTimer.singleShot(0, self._scroll_to_latest_message)

    def _on_generation_finished(self, full_text):
        self._finish_generation(full_text or self._streaming_text)

    def _on_generation_error(self, message):
        if self._pending_conversation is None:
            return
        self._finish_generation(self._streaming_text)
        QMessageBox.warning(self, "خطا در تولید پاسخ", message)

    def _finish_generation(self, answer_text):
        conversation = self._pending_conversation
        if conversation is None:
            return

        answer_text = answer_text.strip()
        streaming_bubble = self._streaming_bubble
        self._pending_conversation = None
        self._streaming_bubble = None
        self._streaming_text = ""

        if answer_text:
            assistant_message = ChatMessage(ROLE_ASSISTANT, answer_text)
            conversation.messages.append(assistant_message)
            self._save_message(conversation, assistant_message)
            if streaming_bubble is not None:
                streaming_bubble.set_text(answer_text)
        elif streaming_bubble is not None:
            streaming_bubble.set_text(self.EMPTY_ANSWER_TEXT)

        self._set_generating(False)

    def _cancel_generation(self):
        if self._is_generating:
            self._llm.stop()
        self._pending_conversation = None
        self._streaming_bubble = None
        self._streaming_text = ""
        self._set_generating(False)

    def _set_generating(self, is_generating):
        self._is_generating = is_generating
        self.send_button.setText("توقف" if is_generating else "ارسال")
        self.send_button.setEnabled(bool(self._active_model_name))

    def _save_conversation(self, conversation):
        database_id = getattr(self._active_database, "database_id", 0)
        if not database_id:
            return
        try:
            chatroom = session.new_chatroom(database_id, conversation.title)
            conversation.chatroom_id = chatroom.pk
        except Exception as error:
            print(error)

    def _save_message(self, conversation, chat_message):
        if not conversation.chatroom_id:
            return
        try:
            session.add_message(conversation.chatroom_id, chat_message.role, chat_message.text)
        except Exception as error:
            print(error)

    def _delete_conversation_from_storage(self, conversation):
        if not conversation.chatroom_id:
            return
        try:
            session.delete_chatroom(conversation.chatroom_id)
        except Exception as error:
            print(error)

    def _ensure_current_conversation(self, first_question):
        """اگر گفت‌وگوی بازی نیست، یکی می‌سازد و بلافاصله به تاریخچه اضافه می‌کند."""
        if self._current_conversation is not None:
            return self._current_conversation

        maximum_title_length = 36
        title = first_question
        if len(title) > maximum_title_length:
            title = title[:maximum_title_length] + "…"

        conversation = Conversation(title=title)
        self._conversations.insert(0, conversation)
        self._current_conversation = conversation
        self._save_conversation(conversation)

        self._populate_history_list()
        self.history_list.setCurrentRow(0)
        return conversation

    def _append_message(self, chat_message):
        self.welcome_widget.setVisible(False)
        message_row, message_bubble = self._create_message_row(chat_message)
        insert_position = self.messages_layout.count() - 1
        self.messages_layout.insertWidget(insert_position, message_row)
        self._message_rows.append(message_row)

        QTimer.singleShot(30, self._scroll_to_latest_message)
        return message_bubble

    @staticmethod
    def _create_message_row(chat_message):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        message_bubble = MessageBubble(chat_message)
        if chat_message.role == ROLE_USER:
            row_layout.addWidget(message_bubble)
            row_layout.addStretch(1)
        else:
            row_layout.addStretch(1)
            row_layout.addWidget(message_bubble)
        return row_widget, message_bubble

    def _scroll_to_latest_message(self):
        scroll_bar = self.messages_scroll_area.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())