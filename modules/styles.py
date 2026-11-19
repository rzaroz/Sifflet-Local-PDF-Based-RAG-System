EXTRA_QSS = """
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }

QFrame#Card {
    background: @base@; border: 1px solid @border@; border-radius: 12px;
}
QFrame#Card[clickable="true"]:hover { border: 1px solid @accent@; background: @alt@; }
QFrame#Card[selected="true"] { border: 1px solid @accent@; }

QFrame#FilePanel {
    background: @alt@; border: 1px dashed @muted@; border-radius: 12px;
}

QListWidget#NavigationList { background: transparent; border: none; }
QListWidget#NavigationList::item { padding: 10px 12px; margin: 2px 0px; }
QListWidget#HistoryList { background: transparent; border: none; }

QFrame#UserBubble { background: @sel@; border: none; border-radius: 12px; }
QFrame#AssistantBubble {
    background: @alt@; border: 1px solid @border@; border-radius: 12px;
}

QLabel[role="pageTitle"] { font-size: 22px; font-weight: 700; }
QLabel[role="sectionTitle"] { font-size: 14px; font-weight: 600; }
QLabel[role="cardTitle"] { font-size: 16px; font-weight: 700; }
QLabel[role="muted"] { color: @muted@; }
QLabel[role="accent"] { color: @accent@; font-weight: 600; }
QLabel[role="index"] { color: @accent@; font-size: 13px; font-weight: 700; }
"""
