from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from modules.common import (
    PAGE_MARGINS,
    PAGE_SPACING,
    ClickableCard,
    PageIndex,
    create_label,
    create_page_header,
    to_persian_digits,
)


class DashboardPage(QWidget):
    section_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_interface()

    def _build_interface(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(*PAGE_MARGINS)
        page_layout.setSpacing(PAGE_SPACING)

        page_layout.addWidget(
            create_page_header(
                "به Sifflet خوش آمدید",
                "با کتاب‌های خود گفت‌وگو کنید؛ ابتدا یک دیتابیس بسازید یا یکی از دیتابیس‌های موجود را انتخاب کنید.",
            )
        )

        cards_layout = QGridLayout()
        cards_layout.setSpacing(PAGE_SPACING)

        create_card, create_summary_label = self._create_section_card(
            index_text="۰۱",
            title="ایجاد دیتابیس جدید",
            description="کتاب را انتخاب کنید تا دیتابیس اختصاصی آن ساخته شود.",
            page_index=PageIndex.CREATE_DATABASE,
        )
        create_summary_label.setText("فرمت‌های PDF، EPUB، DOCX و TXT")

        model_card, self.model_summary_label = self._create_section_card(
            index_text="۰۲",
            title="انتخاب مدل",
            description="فایل مدل را از سیستم خود اضافه کنید و مدل فعال را مشخص کنید.",
            page_index=PageIndex.MODEL_SELECTION,
        )

        database_card, self.database_summary_label = self._create_section_card(
            index_text="۰۳",
            title="دیتابیس‌های من",
            description="دیتابیس‌های ساخته‌شده را مرور کنید و وارد گفت‌وگو با کتاب شوید.",
            page_index=PageIndex.DATABASE_LIST,
        )

        settings_card, settings_summary_label = self._create_section_card(
            index_text="۰۴",
            title="تنظیمات",
            description="تم و گزینه‌های عمومی نرم‌افزار را مدیریت کنید.",
            page_index=PageIndex.SETTINGS,
        )
        settings_summary_label.setText("ظاهر، زبان و ذخیره‌سازی")

        cards_layout.addWidget(create_card, 0, 0)
        cards_layout.addWidget(model_card, 0, 1)
        cards_layout.addWidget(database_card, 1, 0)
        cards_layout.addWidget(settings_card, 1, 1)
        cards_layout.setColumnStretch(0, 1)
        cards_layout.setColumnStretch(1, 1)

        page_layout.addLayout(cards_layout)
        page_layout.addStretch(1)

    def _create_section_card(self, index_text, title, description, page_index):
        card = ClickableCard()
        card.setMinimumHeight(180)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 20)
        card_layout.setSpacing(8)

        card_layout.addWidget(create_label(index_text, role="index"))
        card_layout.addWidget(create_label(title, role="cardTitle"))
        card_layout.addWidget(create_label(description, role="muted", word_wrap=True))
        card_layout.addStretch(1)

        footer_layout = QHBoxLayout()
        summary_label = create_label("", role="muted")
        footer_layout.addWidget(summary_label)
        footer_layout.addStretch(1)
        footer_layout.addWidget(create_label("باز کردن ←", role="accent"))
        card_layout.addLayout(footer_layout)

        card.clicked.connect(lambda: self.section_requested.emit(int(page_index)))
        return card, summary_label

    def set_database_count(self, database_count):
        self.database_summary_label.setText(f"{to_persian_digits(database_count)} دیتابیس")

    def set_model_status(self, active_model_name, is_loaded):
        if not active_model_name:
            self.model_summary_label.setText("مدلی انتخاب نشده است")
        elif is_loaded:
            self.model_summary_label.setText(f"{active_model_name} · آمادهٔ گفت‌وگو")
        else:
            self.model_summary_label.setText(f"{active_model_name} · لود نشده")
