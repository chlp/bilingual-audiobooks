"""
Шаг 1: режет входной mp3 на куски по паузам (тишине), чтобы потом каждый
кусок отдельно скормить Whisper. Наивная транскрипция целого файла (или
файла, порезанного вслепую по фиксированной длине) на длинных записях иногда
теряет или зацикливает куски речи на границах внутренних 30-секундных окон
модели -- резка по реальным паузам с целевой длиной ~20 сек снимает эту
проблему (см. guide/PROCESS.md, маршрут A).

Использование:
    python3 tools/split_audio.py --input book.mp3 --outdir book_chunks

Результат: book_chunks/chunk_0001.mp3, chunk_0002.mp3, ... и
book_chunks/chunks.json со списком {"file", "offset", "duration"} --
offset нужен на следующем шаге, чтобы пересчитать локальное время Whisper
в глобальное время всей книги.
"""
import argparse
import json
import os
import re
import subprocess


def ffprobe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def detect_silences(path, noise_db, min_silence_len):
    proc = subprocess.run(
        ["ffmpeg", "-i", path, "-af",
         f"silencedetect=noise={noise_db}dB:d={min_silence_len}",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    log = proc.stderr
    starts = [float(x) for x in re.findall(r"silence_start:\s*([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", log)]
    silences = list(zip(starts, ends[:len(starts)]))
    return silences


def pick_split_points(silences, duration, min_chunk, max_chunk):
    midpoints = sorted((s + e) / 2 for s, e in silences)
    points = []
    pos = 0.0
    while duration - pos > max_chunk:
        window = [m for m in midpoints if pos + min_chunk <= m <= pos + max_chunk]
        if window:
            cut = max(window)
        else:
            cut = pos + max_chunk
        points.append(cut)
        pos = cut
    return points


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="исходный mp3")
    ap.add_argument("--outdir", required=True, help="куда положить куски")
    ap.add_argument("--min-chunk", type=float, default=12.0, help="минимальная длина куска, сек")
    ap.add_argument("--max-chunk", type=float, default=20.0, help="целевая максимальная длина куска, сек")
    ap.add_argument("--noise-db", type=float, default=-30.0, help="порог тишины, дБ (silencedetect noise=)")
    ap.add_argument("--min-silence-len", type=float, default=0.35, help="минимальная длина паузы, сек (silencedetect d=)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    duration = ffprobe_duration(args.input)
    silences = detect_silences(args.input, args.noise_db, args.min_silence_len)
    print(f"Длительность: {duration:.1f} сек, найдено пауз: {len(silences)}")

    split_points = pick_split_points(silences, duration, args.min_chunk, args.max_chunk)
    bounds = [0.0] + split_points + [duration]

    chunks = []
    for i in range(len(bounds) - 1):
        start, end = bounds[i], bounds[i + 1]
        fname = f"chunk_{i + 1:04d}.mp3"
        fpath = os.path.join(args.outdir, fname)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", args.input,
             "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
             "-c", "copy", "-avoid_negative_ts", "make_zero", fpath],
            check=True,
        )
        chunks.append({"file": fname, "offset": round(start, 3), "duration": round(end - start, 3)})

    chunks_json_path = os.path.join(args.outdir, "chunks.json")
    with open(chunks_json_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=1)

    print(f"Нарезано {len(chunks)} кусков в {args.outdir}/, метаданные -> {chunks_json_path}")


if __name__ == "__main__":
    main()
