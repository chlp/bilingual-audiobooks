"""
Собирает страницу плеера книги: player/template.html + data.json + иллюстрации.

    python3 tools/build_html.py books/<slug>

Читает books/<slug>/book.json (пути, заголовки, подписи колонок), data.json и
illustrations/scenes.json (или images.json). Пишет books/<slug>/index.html, рядом -- уменьшенные
копии картинок в illustrations/web/ (JPEG 1200px: исходники 1.5-3 МБ PNG для
iPad слишком тяжёлые). Страница ссылается на mp3 относительным путём.

scenes.json / images.json -- список {"chapter": N, "file": "ch09/01.png",
"anchor": "...", "pos": "before"|"after", ...}; anchor -- уникальный фрагмент строки перевода
(или "anchorOrig" -- фрагмент строки оригинала). Неуникальный или ненайденный
якорь роняет сборку. Картинки, которых ещё нет на диске, пропускаются с
предупреждением.
"""
import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookcfg import REPO, Book, load_data  # noqa: E402

TEMPLATE = os.path.join(REPO, "player", "template.html")
WEB_WIDTH = 1200


def web_copy(book, src):
    """illustrations/chNN/X.png -> illustrations/web/chNN/X.jpg; -> (rel, w, h)."""
    from PIL import Image
    ill = book.path("illustrations")
    rel_in_ill = os.path.relpath(src, ill)
    dst = os.path.join(ill, "web", os.path.splitext(rel_in_ill)[0] + ".jpg")
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im = Image.open(src).convert("RGB")
        if im.width > WEB_WIDTH:
            im = im.resize((WEB_WIDTH, round(im.height * WEB_WIDTH / im.width)), Image.LANCZOS)
        im.save(dst, "JPEG", quality=82, optimize=True, progressive=True)
    with Image.open(dst) as im:
        w, h = im.size
    out_dir = os.path.dirname(book.path("out"))
    return os.path.relpath(dst, out_dir).replace(os.sep, "/"), w, h


def resolve_images(book, data):
    """-> {chapterIdx: [{tr, orig, pos, src, t, w, h}]}; tr -- индекс строки
    перевода внутри главы, orig -- глобальный индекс реплики оригинала."""
    # scenes.json -- основной формат (сцены с референсами и промптами, guide/ILLUSTRATIONS.md);
    # images.json -- упрощённый: только файл + якорь
    path = book.path("illustrations", "scenes.json")
    if not os.path.exists(path):
        path = book.path("illustrations", "images.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        items = json.load(f)
    cues = data["cues"]
    by_num = {ch["ruNum"]: (i, ch) for i, ch in enumerate(data["chapters"])}
    out, missing = {}, 0
    for it in items:
        if it["chapter"] not in by_num:
            raise SystemExit(f"images.json: нет главы {it['chapter']}")
        idx, ch = by_num[it["chapter"]]
        pos = it.get("pos", "before")
        if pos not in ("before", "after"):
            raise SystemExit(f"images.json: pos={pos!r}, нужно before/after")
        if "anchorOrig" in it:
            hits = [c for c in range(ch["cueStart"], ch["cueEnd"]) if it["anchorOrig"] in cues[c]["text"]]
            anchor = it["anchorOrig"]
        else:
            hits = [i for i, rl in enumerate(ch["ruLines"]) if it["anchor"] in rl["text"]]
            anchor = it["anchor"]
        if len(hits) != 1:
            raise SystemExit(f"anchor {anchor!r} (глава {it['chapter']}): совпадений {len(hits)}, нужно ровно 1")
        if "anchorOrig" in it:
            orig = hits[0]
            tr_cands = [i for i, rl in enumerate(ch["ruLines"]) if rl["svStart"] <= orig <= rl["svEnd"]]
            tr = (tr_cands[0] if pos == "before" else tr_cands[-1]) if tr_cands else 0
            t = cues[orig]["start"]
        else:
            tr = hits[0]
            rl = ch["ruLines"][tr]
            orig = rl["svStart"] if pos == "before" else rl["svEnd"]
            t = rl["start"]
        src = book.path("illustrations", it["file"])
        if not os.path.exists(src):
            missing += 1
            continue
        rel, w, h = web_copy(book, src)
        out.setdefault(idx, []).append({"tr": tr, "orig": orig, "pos": pos, "src": rel, "t": t, "w": w, "h": h})
    total = len(items)
    print(f"иллюстрации: {total - missing}/{total}" + (f" (нет файлов: {missing})" if missing else ""))
    return out


def script_json(obj):
    # "</script>" внутри текста книги не должен закрыть тег
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book", help="папка книги с book.json")
    args = ap.parse_args()
    book = Book(args.book)

    data = load_data(book)
    images = resolve_images(book, data)
    out = book.path("out")
    audio_rel = os.path.relpath(book.path("audio"), os.path.dirname(out)).replace(os.sep, "/")

    cfg = {"slug": book["slug"], "title": book["title"]}
    e = html.escape
    with open(TEMPLATE, encoding="utf-8") as f:
        page = f.read()
    repl = {
        "__UI_LANG__": book["transLang"],
        "__PAGE_TITLE__": e(book["title"]),
        "__HEADER_TITLE__": e(book["title"]),
        "__AUDIO_SRC__": e(audio_rel),
        "__ORIG_LABEL__": e(book["origLabel"]),
        "__TRANS_LABEL__": e(book["transLabel"]),
        "__ORIG_SHORT__": e(book["origShort"]),
        "__TRANS_SHORT__": e(book["transShort"]),
        "__FOOTER_HINT__": e(book["footerHint"]),
        "__CONFIG_JSON__": script_json(cfg),
        "__IMAGES_JSON__": script_json(images),
        "__DATA_JSON__": script_json(data),  # последним: в тексте книги могут встретиться плейсхолдеры
    }
    for k, v in repl.items():
        page = page.replace(k, v)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Wrote {out} ({len(page) // 1024} КБ), аудио: {audio_rel}")


if __name__ == "__main__":
    main()
