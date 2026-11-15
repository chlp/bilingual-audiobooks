"""
Шаг 2: прогоняет каждый кусок из split_audio.py через mlx-whisper и сшивает
результат в единый список сегментов с ГЛОБАЛЬНЫМИ таймкодами (локальное время
куска + его offset).

Нужен venv с mlx-whisper (см. guide/PROCESS.md, «Окружение»):
    source .venv-whisper/bin/activate
    # если venv ещё нет:
    python3 -m venv .venv-whisper && source .venv-whisper/bin/activate && pip install mlx-whisper

Использование:
    python3 tools/transcribe.py --chunks-dir book_chunks --lang sv --out sv.json

Результат: sv.json -- список [{"start": .., "end": .., "text": ..}, ...],
отсортированный по времени, плюс sv.srt в том же порядке для наглядности.
"""
import argparse
import json
import os


def ts_srt(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n{ts_srt(seg['start'])} --> {ts_srt(seg['end'])}\n{seg['text']}\n\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chunks-dir", required=True, help="папка с chunk_*.mp3 и chunks.json из split_audio.py")
    ap.add_argument("--lang", required=True, help="язык оригинала, код ISO (sv, en, ...)")
    ap.add_argument("--model", default="mlx-community/whisper-large-v3-mlx", help="модель mlx-whisper")
    ap.add_argument("--out", required=True, help="путь к выходному sv.json")
    ap.add_argument("--out-srt", default=None, help="путь к выходному .srt (по умолчанию out с расширением .srt)")
    args = ap.parse_args()

    try:
        import mlx_whisper
    except ImportError:
        raise SystemExit(
            "mlx_whisper не установлен. Активируй venv: source .venv-whisper/bin/activate\n"
            "(или создай: python3 -m venv .venv-whisper && source .venv-whisper/bin/activate && pip install mlx-whisper)"
        )

    with open(os.path.join(args.chunks_dir, "chunks.json"), encoding="utf-8") as f:
        chunks = json.load(f)

    all_segments = []
    for i, chunk in enumerate(chunks, 1):
        path = os.path.join(args.chunks_dir, chunk["file"])
        print(f"[{i}/{len(chunks)}] {chunk['file']} ...")
        result = mlx_whisper.transcribe(path, path_or_hf_repo=args.model, language=args.lang)
        offset = chunk["offset"]
        for seg in result["segments"]:
            text = seg["text"].strip()
            if not text:
                continue
            all_segments.append({
                "start": round(seg["start"] + offset, 3),
                "end": round(seg["end"] + offset, 3),
                "text": text,
            })

    all_segments.sort(key=lambda s: s["start"])

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(all_segments, f, ensure_ascii=False, indent=1)

    out_srt = args.out_srt or os.path.splitext(args.out)[0] + ".srt"
    write_srt(all_segments, out_srt)

    print(f"Готово: {len(all_segments)} сегментов -> {args.out}, {out_srt}")


if __name__ == "__main__":
    main()
