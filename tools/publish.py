"""
Собирает из папки книги то, что нужно выложить на сайт, и только это.

    python3 tools/publish.py examples/<slug>                # -> docs/books/<slug>/ + docs/catalog.json
    python3 tools/publish.py books/<slug> --out ~/site/<slug>   # свой хостинг, каталог не трогается

Копирует index.html, mp3, уменьшенные иллюстрации (illustrations/web/) и
pdf/*.pdf. Не копирует build/ (data.json уже встроен в index.html, кеш TTS
и куски аудио сайту не нужны), исходные PNG, тексты, библию.

Без --out книга публикуется на GitHub Pages репозитория: копия в
docs/books/<slug>/ и карточка в docs/catalog.json, по которому
docs/index.html рисует список книг. Обложка карточки -- поле "cover" в
book.json (путь к картинке в папке книги), иначе первая иллюстрация.
На Pages -- только то, на что есть права: свои тексты, общественное
достояние, открытые лицензии. Книги из books/ туда не публикуются, для них
есть --out (свой сервер; это ваша ответственность, куда вы их кладёте).
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
    ap.add_argument("--out", help="папка для своего хостинга (будет перезаписана); без неё -- docs/ для GitHub Pages")
    args = ap.parse_args()
    book = Book(args.book)
    if not args.out and os.path.relpath(book.dir, REPO).startswith("books" + os.sep):
        raise SystemExit("books/ -- личные книги: на GitHub Pages не публикуются, используйте --out (см. docstring)")

    slug = book["slug"]
    dst = os.path.abspath(os.path.expanduser(args.out)) if args.out else os.path.join(REPO, "docs", "books", slug)
    if os.path.exists(dst):
        if os.listdir(dst) and not os.path.exists(os.path.join(dst, "index.html")):
            raise SystemExit(f"{dst} не пустая и не похожа на прошлую публикацию (нет index.html) -- не трогаю")
        shutil.rmtree(dst)
    os.makedirs(dst)

    out_dir = os.path.dirname(book.path("out"))
    shutil.copy2(book.path("out"), os.path.join(dst, "index.html"))
    audio = book.path("audio")
    shutil.copy2(audio, os.path.join(dst, os.path.relpath(audio, out_dir)))
    web = book.path("illustrations", "web")
    if os.path.isdir(web):
        shutil.copytree(web, os.path.join(dst, os.path.relpath(web, out_dir)))
    pdfs = glob.glob(os.path.join(book.path("pdf"), "*.pdf"))
    for p in pdfs:
        rel = os.path.relpath(p, out_dir)
        os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
        shutil.copy2(p, os.path.join(dst, rel))

    def total_size():
        return sum(os.path.getsize(p) for p in glob.glob(os.path.join(dst, "**"), recursive=True) if os.path.isfile(p))

    if args.out:
        print(f"{dst}: {total_size() / 1e6:.1f} МБ (PDF: {len(pdfs)})")
        return

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
    print(f"docs/books/{slug}/: {total_size() / 1e6:.1f} МБ (PDF: {len(pdfs)}); docs/catalog.json: {len(catalog)} книг")


if __name__ == "__main__":
    main()
