"""
Режет аудио книги на mp3 по главам (для Yoto «Make Your Own», плеера в
машине и т.п.).

    python3 tools/split_chapters.py books/<slug> [--outdir books/<slug>/build/tracks]

Граница главы -- не таймкод первой реплики главы (у распознанной речи он
иногда стоит в начале паузы, а не на заголовке), а реальная пауза в аудио
(ffmpeg silencedetect) рядом с ним. Разрез -- за --lead-in сек до конца паузы,
чтобы трек начинался почти сразу с заголовка. Сегменты вырезаются `-c copy`
без перекодирования. Имя трека: "NN - Глава N. Название.mp3".
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookcfg import Book  # noqa: E402


def silences(src, noise_db, min_len):
    log = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", src,
         "-af", f"silencedetect=noise={noise_db}dB:d={min_len}", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    return [(float(e) - float(d), float(e)) for e, d in
            re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", log)]


def safe(name):
    return re.sub(r'[\\/:*?"<>|]', "", name).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book")
    ap.add_argument("--outdir", help="по умолчанию build/tracks в папке книги")
    ap.add_argument("--lead-in", type=float, default=0.6)
    ap.add_argument("--noise-db", type=float, default=-40)
    ap.add_argument("--min-silence", type=float, default=0.8)
    args = ap.parse_args()
    book = Book(args.book)

    src = book.path("audio")
    with open(book.path("data"), encoding="utf-8") as f:
        chapters = json.load(f)["chapters"]
    sil = silences(src, args.noise_db, args.min_silence)

    cuts = [0.0]
    for ch in chapters[1:]:
        t = ch["timeStart"]
        near = [s for s in sil if s[0] < t + 1.5 and s[1] > t - 15]
        if near:
            start, end = max(near, key=lambda s: s[1] - s[0])
            cuts.append(max(start, end - args.lead_in))
        else:
            cuts.append(max(0.0, t - args.lead_in))
    cuts.append(None)

    out = args.outdir or book.path("build", "tracks")
    os.makedirs(out, exist_ok=True)
    for ch, a, b in zip(chapters, cuts, cuts[1:]):
        n = ch["ruNum"]
        title = f"Глава {n}. {ch['ruTitle']}"
        dst = os.path.join(out, safe(f"{n:02d} - {title}") + ".mp3")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{a:.3f}"]
        if b is not None:
            cmd += ["-to", f"{b:.3f}"]
        cmd += ["-i", src, "-map", "0:a", "-c", "copy", "-map_metadata", "-1",
                "-metadata", f"title={title}", "-metadata", f"album={book['title']}",
                "-metadata", f"track={n}/{len(chapters)}", dst]
        subprocess.run(cmd, check=True)
        print(f"{os.path.basename(dst)}  {a:9.2f} -> {b if b is not None else 'конец'}")


if __name__ == "__main__":
    main()
