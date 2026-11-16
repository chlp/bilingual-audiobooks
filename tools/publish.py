"""
Публикует собранную книгу на GitHub Pages сайта репозитория (папка docs/).

    python3 tools/publish.py examples/<slug>

Копирует index.html, mp3 и уменьшенные иллюстрации (illustrations/web/) в
docs/books/<slug>/ и добавляет/обновляет карточку книги в docs/catalog.json,
по которому docs/index.html рисует список книг. Обложка карточки -- поле
"cover" в book.json (путь к картинке в папке книги), иначе первая иллюстрация.

Публикуйте только то, на что есть права: свои тексты, общественное
достояние, открытые лицензии. Личные книги остаются в books/ (gitignore).
"""
import argparse
import glob
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookcfg import REPO, Book  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book")
    args = ap.parse_args()
    book = Book(args.book)
    if os.path.relpath(book.dir, REPO).startswith("books" + os.sep):
        raise SystemExit("books/ -- личные книги, публиковать из examples/ (см. docstring)")

    slug = book["slug"]
    dst = os.path.join(REPO, "docs", "books", slug)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)

    out_dir = os.path.dirname(book.path("out"))
    shutil.copy2(book.path("out"), os.path.join(dst, "index.html"))
    audio = book.path("audio")
    shutil.copy2(audio, os.path.join(dst, os.path.relpath(audio, out_dir)))
    web = book.path("illustrations", "web")
    if os.path.isdir(web):
        shutil.copytree(web, os.path.join(dst, os.path.relpath(web, out_dir)))

    cover = book.get("cover")
    cover_rel = None
    if cover:
        src = book.path(cover)
        ill = book.path("illustrations")
        if src.startswith(ill + os.sep):  # картинка книги -> её уменьшенная копия из web/
            src_web = os.path.join(ill, "web", os.path.splitext(os.path.relpath(src, ill))[0] + ".jpg")
            if os.path.exists(src_web):
                src = src_web
        cover_rel = "cover" + os.path.splitext(src)[1]
        shutil.copy2(src, os.path.join(dst, cover_rel))
    else:
        first = sorted(glob.glob(os.path.join(web, "**", "*.jpg"), recursive=True))
        if first:
            cover_rel = os.path.relpath(first[0], out_dir).replace(os.sep, "/")

    with open(book.path("data"), encoding="utf-8") as f:
        data = json.load(f)
    card = {
        "slug": slug,
        "title": book["title"],
        "subtitle": book.get("subtitle", ""),
        "langs": f"{book['origShort']} / {book['transShort']}",
        "chapters": len(data["chapters"]),
        "minutes": round(data["duration"] / 60),
        "cover": f"books/{slug}/{cover_rel}" if cover_rel else None,
        "about": book.get("about", ""),
    }
    cat_path = os.path.join(REPO, "docs", "catalog.json")
    catalog = []
    if os.path.exists(cat_path):
        with open(cat_path, encoding="utf-8") as f:
            catalog = json.load(f)
    catalog = [c for c in catalog if c["slug"] != slug] + [card]
    with open(cat_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")
    size = sum(os.path.getsize(p) for p in glob.glob(os.path.join(dst, "**"), recursive=True) if os.path.isfile(p))
    print(f"docs/books/{slug}/: {size / 1e6:.1f} МБ; docs/catalog.json: {len(catalog)} книг")


if __name__ == "__main__":
    main()
