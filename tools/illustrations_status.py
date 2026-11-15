"""
Состояние иллюстраций книги: что уже есть, чего не хватает, где ошибки.

    python3 tools/illustrations_status.py books/<slug>

Проверяет scenes.json: якорь каждой сцены находится ровно в одной строке
главы, все референсы из "refs" зафиксированы (есть refs/<id>.png), файлы
сцен на месте. Печатает списки «нужно сгенерировать» -- их удобно отдать
Codex (prompts/codex-scenes.md).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookcfg import Book, load_data  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book")
    args = ap.parse_args()
    book = Book(args.book)
    ill = book.path("illustrations")
    path = os.path.join(ill, "scenes.json")
    if not os.path.exists(path):
        raise SystemExit(f"нет {path}")
    with open(path, encoding="utf-8") as f:
        scenes = json.load(f)
    data = load_data(book)
    by_num = {ch["ruNum"]: ch for ch in data["chapters"]}

    errors, missing_refs, todo, done = [], set(), [], []
    ids = set()
    for s in scenes:
        sid = s.get("id", s.get("file"))
        if sid in ids:
            errors.append(f"{sid}: повторяющийся id")
        ids.add(sid)
        ch = by_num.get(s["chapter"])
        if not ch:
            errors.append(f"{sid}: нет главы {s['chapter']}")
            continue
        if "anchorOrig" in s:
            n = sum(s["anchorOrig"] in data["cues"][c]["text"] for c in range(ch["cueStart"], ch["cueEnd"]))
        else:
            n = sum(s["anchor"] in rl["text"] for rl in ch["ruLines"])
        if n != 1:
            errors.append(f"{sid}: якорь {s.get('anchor', s.get('anchorOrig'))!r} найден {n} раз, нужно 1")
        for r in s.get("refs", []):
            if not os.path.exists(os.path.join(ill, "refs", r + ".png")):
                missing_refs.add(r)
        (done if os.path.exists(os.path.join(ill, s["file"])) else todo).append(sid)

    print(f"сцен: {len(scenes)}, готово: {len(done)}, нужно сгенерировать: {len(todo)}")
    if missing_refs:
        print("незафиксированные референсы (refs/<id>.png):", ", ".join(sorted(missing_refs)))
    if todo:
        print("сцены без картинки:", ", ".join(todo))
    for e in errors:
        print("ОШИБКА:", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
