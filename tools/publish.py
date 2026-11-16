"""
Выкладывает собранную книгу на сайт: только то, что нужно плееру, и только это.

    python3 tools/publish.py books/<slug>              # -> web/<slug>/ + web/index.html (gitignore)
    python3 tools/publish.py examples/<slug>           # -> docs/books/<slug>/ + docs/index.html (GitHub Pages)
    python3 tools/publish.py examples/<slug> --to web  # пример тоже в web/

Копирует index.html, mp3, уменьшенные иллюстрации (illustrations/web/) и
pdf/*.pdf. Не копирует build/ (data.json уже встроен в index.html, кеш TTS
и куски аудио сайту не нужны), исходные PNG, тексты, библию.

Два сайта с одинаковым устройством:
- web/  -- личный, в .gitignore. Папку web/ целиком заливать на свой
  хостинг (или открыть web/index.html прямо с диска).
- docs/ -- публичный GitHub Pages репозитория. Только книги, на которые есть
  права: свои тексты, общественное достояние, открытые лицензии. Книги из
  books/ туда не публикуются.

В корне сайта -- catalog.json (карточки книг) и index.html со списком книг
(шаблон player/catalog.html, каталог вписан в страницу). Обложка карточки --
поле "cover" в book.json (путь к картинке в папке книги), иначе первая
иллюстрация.
"""
import argparse
import glob
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookcfg import REPO, Book  # noqa: E402

SITES = {
    "web": {"root": os.path.join(REPO, "web"), "books": ""},
    "pages": {"root": os.path.join(REPO, "docs"), "books": "books/"},
}
ICONS = [os.path.join(REPO, "player", "favicon.svg"), os.path.join(REPO, "player", "apple-touch-icon.png")]


def copy_book(book, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    out_dir = os.path.dirname(book.path("out"))

    def put(src):
        rel = os.path.relpath(src, out_dir)
        os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dst, rel))
        else:
            shutil.copy2(src, os.path.join(dst, rel))

    shutil.copy2(book.path("out"), os.path.join(dst, "index.html"))
    put(book.path("audio"))
    web = book.path("illustrations", "web")
    if os.path.isdir(web):
        put(web)
    pdfs = sorted(glob.glob(os.path.join(book.path("pdf"), "*.pdf")))
    for p in pdfs:
        put(p)

    cover = book.get("cover")
    if cover:
        src = book.path(cover)
        ill = book.path("illustrations")
        if src.startswith(ill + os.sep):  # картинка книги -> её уменьшенная копия из web/
            src_web = os.path.join(ill, "web", os.path.splitext(os.path.relpath(src, ill))[0] + ".jpg")
            if os.path.exists(src_web):
                src = src_web
        cover_rel = "cover" + os.path.splitext(src)[1]
        shutil.copy2(src, os.path.join(dst, cover_rel))
        return cover_rel, len(pdfs)
    first = sorted(glob.glob(os.path.join(web, "**", "*.jpg"), recursive=True))
    return (os.path.relpath(first[0], out_dir).replace(os.sep, "/") if first else None), len(pdfs)


def write_catalog(root, card):
    cat_path = os.path.join(root, "catalog.json")
    catalog = []
    if os.path.exists(cat_path):
        with open(cat_path, encoding="utf-8") as f:
            catalog = json.load(f)
    catalog = [c for c in catalog if c["slug"] != card["slug"]] + [card]
    # книги, чьи папки удалили руками, из каталога убираем
    catalog = [c for c in catalog if os.path.exists(os.path.join(root, c["href"], "index.html"))]
    with open(cat_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(REPO, "player", "catalog.html"), encoding="utf-8") as f:
        page = f.read()
    page = page.replace("__CATALOG_JSON__", json.dumps(catalog, ensure_ascii=False).replace("</", "<\\/"))
    with open(os.path.join(root, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    for icon in ICONS:
        shutil.copy2(icon, root)
    return len(catalog)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book")
    ap.add_argument("--to", choices=SITES, help="web (по умолчанию для books/) или pages (по умолчанию для examples/)")
    args = ap.parse_args()
    book = Book(args.book)
    private = os.path.relpath(book.dir, REPO).startswith("books" + os.sep)
    to = args.to or ("web" if private else "pages")
    if to == "pages" and private:
        raise SystemExit("books/ -- личные книги: на GitHub Pages не публикуются, только --to web (см. docstring)")

    site = SITES[to]
    slug = book["slug"]
    href = f"{site['books']}{slug}/"
    dst = os.path.join(site["root"], href)
    cover_rel, n_pdf = copy_book(book, dst)

    with open(book.path("data"), encoding="utf-8") as f:
        data = json.load(f)
    card = {
        "slug": slug,
        "href": href,
        "title": book["title"],
        "subtitle": book.get("subtitle", ""),
        "langs": f"{book['origShort']} / {book['transShort']}",
        "chapters": len(data["chapters"]),
        "minutes": round(data["duration"] / 60),
        "cover": f"{href}{cover_rel}" if cover_rel else None,
        "about": book.get("about", ""),
    }
    n = write_catalog(site["root"], card)
    size = sum(os.path.getsize(p) for p in glob.glob(os.path.join(dst, "**"), recursive=True) if os.path.isfile(p))
    rel_root = os.path.relpath(site["root"], REPO)
    print(f"{rel_root}/{href}: {size / 1e6:.1f} МБ (PDF: {n_pdf}); {rel_root}/index.html: {n} книг")


if __name__ == "__main__":
    main()
