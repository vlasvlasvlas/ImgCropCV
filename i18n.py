import json
from pathlib import Path

_translations = {}
_lang = "en"

def load_translations(path: Path):
    global _translations
    if path.exists():
        with open(path, encoding="utf-8") as f:
            _translations = json.load(f)

def set_language(lang: str):
    global _lang
    _lang = lang

def get_language() -> str:
    return _lang

def t(key: str, *args) -> str:
    """Get translated string for key, optionally formatting with args."""
    val = _translations.get(_lang, {}).get(key, key)
    # Fallback to English if key missing in current lang
    if val == key and _lang != 'en':
        val = _translations.get('en', {}).get(key, key)
    
    if args:
        try:
            return val.format(*args)
        except IndexError:
            return val
    return val
