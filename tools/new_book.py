"""
Заготовка папки новой книги.

    python3 tools/new_book.py my-book --title "Название" [--route tts|asr|literary]

Создаёт books/<slug>/ (папка в .gitignore) с book.json, text/, source/,
build/, illustrations/ и пустыми рабочими файлами для шагов процесса
(guide/PROCESS.md). Для примера, который пойдёт в репозиторий, передайте
--root examples.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookcfg import REPO  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--title", required=True)
    ap.add_argument("--route", choices=["tts", "asr", "literary"], default="tts",
                    help="tts -- озвучиваем сами (B/C), asr -- есть аудио оригинала (A), literary -- аудио + готовый перевод (D)")
    ap.add_argument("--root", default="books")
    args = ap.parse_args()

    d = os.path.join(REPO, args.root, args.slug)
    if os.path.exists(os.path.join(d, "book.json")):
        raise SystemExit(f"{d}/book.json уже есть")
    for sub in ("source", "text", "build", "illustrations/refs"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    cfg = {
        "slug": args.slug,
        "title": args.title,
        "route": args.route,
        "origLang": "sv", "transLang": "ru",
        "origLabel": "Svenska", "transLabel": "Русский",
        "origShort": "SV", "transShort": "RU",
        "audio": "audio.mp3",
        "data": "build/data.json",
    }
    if args.route == "tts":
        cfg["tts"] = {"voice": "voices/sv_SE-nst-medium.onnx", "lengthScale": 1.08}
    with open(os.path.join(d, "book.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    ill = os.path.join(d, "illustrations")
    with open(os.path.join(ill, "scenes.json"), "w", encoding="utf-8") as f:
        f.write("[]\n")
    print(f"Создано: {d}\nДальше: guide/PROCESS.md")


if __name__ == "__main__":
    main()
