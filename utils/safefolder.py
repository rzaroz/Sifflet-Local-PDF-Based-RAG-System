import re
import unicodedata

_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
    "COM¹", "COM²", "COM³", "LPT¹", "LPT²", "LPT³",
}

def safe_folder_name(text: str, replacement: str = "_", max_length: int = 100) -> str:
    if text is None:
        text = ""
    text = unicodedata.normalize("NFC", str(text))
    text = re.sub(r"[\x00-\x1f\x7f]", "", text)
    text = re.sub(r'[<>:"/\\|?*]', replacement, text)
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]", "", text)
    text = re.sub(r"\s+", " ", text)
    if replacement:
        text = re.sub(f"{re.escape(replacement)}{{2,}}", replacement, text)
    text = text.strip(" .")
    text = text[:max_length].rstrip(" .")
    if text.split(".")[0].upper() in _RESERVED_NAMES:
        text = f"{replacement}{text}"
    return text or None