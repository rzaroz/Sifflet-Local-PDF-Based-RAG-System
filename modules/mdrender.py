import re
import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

CODE_STYLE = "monokai"
CODE_BACKGROUND = "#272822"
CODE_FOREGROUND = "#f8f8f2"
INLINE_CODE_STYLE = (
    "background-color:#3b3f4c; color:#f8f8f2; "
    "font-family:Consolas,'Courier New',monospace;"
)

_FENCE = re.compile(r"```[ \t]*([\w+#.-]*)[^\n]*\n(.*?)(?:```|\Z)", re.DOTALL)
_FORMATTER = HtmlFormatter(style=CODE_STYLE, noclasses=True, nowrap=True)


def _render_code(code, language):
    try:
        lexer = get_lexer_by_name(language) if language else TextLexer()
    except ClassNotFound:
        lexer = TextLexer()
    body = highlight(code.rstrip("\n"), lexer, _FORMATTER).rstrip("\n")
    return (
        '<table width="100%" cellspacing="0" cellpadding="10" '
        'style="margin-top:6px; margin-bottom:6px;"><tr>'
        f'<td bgcolor="{CODE_BACKGROUND}">'
        f'<pre dir="ltr" style="margin:0; color:{CODE_FOREGROUND}; '
        "font-family:Consolas,'Courier New',monospace; "
        f'white-space:pre-wrap;">{body}</pre>'
        "</td></tr></table>"
    )


def _render_text(segment):
    if not segment.strip():
        return ""
    html = markdown.markdown(segment, extensions=["tables", "sane_lists", "nl2br"])
    html = html.replace("<code>", f'<code style="{INLINE_CODE_STYLE}">')
    html = html.replace("<table>", '<table border="1" cellspacing="0" cellpadding="5">')
    return html


def render_markdown(text):
    parts = []
    position = 0
    for match in _FENCE.finditer(text):
        parts.append(_render_text(text[position:match.start()]))
        parts.append(_render_code(match.group(2), match.group(1)))
        position = match.end()
    parts.append(_render_text(text[position:]))
    return "".join(parts)