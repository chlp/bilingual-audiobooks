"""Общий загрузчик book.json: все пути в нём относительны папке книги.

Поля и значения по умолчанию описаны в guide/FORMATS.md.
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULTS = {
    "origLang": "sv",
    "transLang": "ru",
    "origLabel": "Svenska",
    "transLabel": "Русский",
    "origShort": "SV",
    "transShort": "RU",
    "audio": "audio.mp3",
    "data": "build/data.json",
    "text": "text",
    "illustrations": "illustrations",
    "out": "index.html",
    "footerHint": "Клик по строке — переход к этому месту в аудио. "
                  "«Ссылка на место» копирует ссылку, которая откроет книгу здесь же.",
    "tts": {},
}


class Book:
    def __init__(self, book_dir):
        self.dir = os.path.abspath(book_dir)
        path = os.path.join(self.dir, "book.json")
        if not os.path.exists(path):
            raise SystemExit(f"нет {path} -- см. guide/FORMATS.md, раздел book.json")
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        self.cfg = {**DEFAULTS, **raw}
        self.cfg.setdefault("slug", os.path.basename(self.dir))
        self.cfg.setdefault("title", self.cfg["slug"])

    def __getitem__(self, key):
        return self.cfg[key]

    def get(self, key, default=None):
        return self.cfg.get(key, default)

    def path(self, key_or_rel, *more):
        """Абсолютный путь: book.path('data') или book.path('build', 'x.json')."""
        rel = self.cfg.get(key_or_rel, key_or_rel) if not more else key_or_rel
        if isinstance(rel, str) and os.path.isabs(rel):
            return os.path.join(rel, *more)
        return os.path.normpath(os.path.join(self.dir, rel, *more))

    def tts(self, key, default=None):
        return self.cfg.get("tts", {}).get(key, default)


def load_data(book):
    """data.json + ручные названия глав оригинала из book.json
    ("origChapterTitles": {"1": "Vilse i centrum", ...}) -- для маршрутов A/D,
    где распознанный заголовок бывает кривым ("Kapitel two", "- Kapitel 8 -")."""
    with open(book.path("data"), encoding="utf-8") as f:
        data = json.load(f)
    titles = book.get("origChapterTitles") or {}
    for ch in data["chapters"]:
        t = titles.get(str(ch["ruNum"]))
        if t:
            ch["svTitle"] = t
    return data
