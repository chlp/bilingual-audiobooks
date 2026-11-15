"""
Озвучивает оригинал (Piper TTS) по text/chNN.txt и собирает data.json.

    source .venv-tts/bin/activate
    python3 tools/tts_build.py books/<slug>

Вход: text/chNN.txt (формат -- guide/FORMATS.md): строка "оригинал ||| перевод",
первая строка файла -- заголовок главы ("Kapitel 1. Namn ||| Глава 1. Название"),
строка с "@" перед заголовком -- вступление (название книги), абзацы через
пустую строку. Каждое предложение озвучивается отдельно, таймкоды берутся из
фактической длины аудио -- оригинал и перевод синхронны 1:1, без оценок.

Голос и скорость -- в book.json, раздел "tts":
    {"voice": "voices/sv_SE-lisa-medium.onnx", "lengthScale": 1.08}
Путь к голосу ищется относительно папки книги, затем корня репозитория.
Аудио каждого предложения кешируется (build/tts_cache, ключ -- голос+скорость+
текст), поэтому после правки пары строк пересборка занимает секунды.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookcfg import REPO, Book  # noqa: E402

PAUSE_SENT = 0.45
PAUSE_PARA = 1.0
PAUSE_TITLE = 1.8
PAUSE_CHAPTER = 2.5


def synth(voice, cfg, text, cache_dir, key_prefix):
    import numpy as np
    key = hashlib.sha1((key_prefix + "|" + text).encode()).hexdigest()
    path = os.path.join(cache_dir, key + ".npy")
    if os.path.exists(path):
        return np.load(path)
    parts = [c.audio_int16_array for c in voice.synthesize(text, syn_config=cfg)]
    audio = np.concatenate(parts) if parts else np.zeros(0, dtype=np.int16)
    np.save(path, audio)
    return audio


def load_chapter(path):
    """-> {num, intro, sv, ru, paras: [[{sv, ru}]]}; ошибки формата -- с номером строки."""
    m = re.search(r"ch(\d+)", os.path.basename(path))
    num = int(m.group(1)) if m else 0
    intro, title, paras = None, None, [[]]
    for ln, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            if not line and paras[-1]:
                paras.append([])
            continue
        if line.count("|||") != 1:
            raise SystemExit(f"{path}:{ln}: нужен ровно один разделитель '|||': {line[:80]}")
        sv, ru = (x.strip() for x in line.lstrip("@").split("|||"))
        if not sv or not ru:
            raise SystemExit(f"{path}:{ln}: пустая половина строки")
        if line.startswith("@"):
            intro = {"sv": sv, "ru": ru}
        elif title is None:
            title = {"sv": sv, "ru": ru}
        else:
            paras[-1].append({"sv": sv, "ru": ru})
    if not paras[-1]:
        paras.pop()
    if title is None:
        raise SystemExit(f"{path}: нет строки-заголовка главы")
    return {"num": num, "intro": intro, "sv": title["sv"], "ru": title["ru"], "paras": paras}


def strip_num(title):
    # "Kapitel 1. Sanna påhitt" -> "Sanna påhitt"; "Глава 3: Х" -> "Х"
    m = re.match(r"^\s*\S+\s+\d+\s*[.:–—-]\s*(.+)$", title)
    return m.group(1).strip() if m else title.strip()


def find_voice(book, voice):
    for base in (book.dir, REPO):
        p = os.path.join(base, voice)
        if os.path.exists(p):
            return p
    raise SystemExit(f"голос {voice!r} не найден (ни в папке книги, ни в репозитории); "
                     "скачать: tools/get_voice.sh <имя>")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book", help="папка книги с book.json")
    ap.add_argument("--voice", help="переопределить tts.voice")
    ap.add_argument("--length-scale", type=float, help="переопределить tts.lengthScale (>1 -- медленнее)")
    args = ap.parse_args()
    book = Book(args.book)

    try:
        import numpy as np
        from piper import PiperVoice
        from piper.config import SynthesisConfig
    except ImportError:
        raise SystemExit("нет piper-tts: python3 -m venv .venv-tts && source .venv-tts/bin/activate "
                         "&& pip install piper-tts")

    voice_path = find_voice(book, args.voice or book.tts("voice", "voices/sv_SE-lisa-medium.onnx"))
    length_scale = args.length_scale or book.tts("lengthScale", 1.08)
    cache_dir = book.path(book.tts("cache", "build/tts_cache"))
    out_audio, out_data = book.path("audio"), book.path("data")
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(os.path.dirname(out_data), exist_ok=True)

    voice = PiperVoice.load(voice_path)
    sr = voice.config.sample_rate
    cfg = SynthesisConfig(length_scale=length_scale)
    key_prefix = f"{os.path.basename(voice_path)}|{length_scale}"

    files = sorted(glob.glob(os.path.join(book.path("text"), "ch*.txt")))
    if not files:
        raise SystemExit(f"нет {book.path('text')}/ch*.txt")
    pieces, cues, chapters = [], [], []
    pos = 0  # в сэмплах

    def add_silence(sec):
        nonlocal pos
        n = int(sec * sr)
        pieces.append(np.zeros(n, dtype=np.int16))
        pos += n

    def add_line(sv_text):
        nonlocal pos
        audio = synth(voice, cfg, sv_text, cache_dir, key_prefix)
        start = pos / sr
        pieces.append(audio)
        pos += len(audio)
        return round(start, 3), round(pos / sr, 3)

    def add_pair(pair, para):
        s, e = add_line(pair["sv"])
        cue = {"start": s, "end": e, "text": pair["sv"], "para": para}
        cues.append(cue)
        return {"text": pair["ru"], "start": s, "end": e, "para": para,
                "svStart": len(cues) - 1, "svEnd": len(cues) - 1}

    for fi, path in enumerate(files):
        ch = load_chapter(path)
        if fi > 0:
            add_silence(PAUSE_CHAPTER)
        cue_start = len(cues)
        ru_lines = []
        if ch["intro"]:
            ru_lines.append(add_pair(ch["intro"], 0))
            add_silence(PAUSE_CHAPTER)
        ru_lines.append(add_pair({"sv": ch["sv"], "ru": ch["ru"]}, 0))
        add_silence(PAUSE_TITLE)
        for pi, para in enumerate(ch["paras"]):
            if pi > 0:
                add_silence(PAUSE_PARA)
            for si, pair in enumerate(para):
                if si > 0:
                    add_silence(PAUSE_SENT)
                ru_lines.append(add_pair(pair, pi + 1))
        chapters.append({
            "index": fi,
            "svRawTitle": ch["sv"],
            "svTitle": strip_num(ch["sv"]),
            "ruTitle": strip_num(ch["ru"]),
            "ruNum": ch["num"] or fi + 1,
            "timeStart": cues[cue_start]["start"],
            "timeEnd": None,
            "cueStart": cue_start,
            "cueEnd": len(cues),
            "ruLines": ru_lines,
            "ruParaCount": len(ch["paras"]) + 1,
            "titleLines": 2 if ch["intro"] else 1,
        })
        print(f"  {ch['num']}. {strip_num(ch['sv'])} / {strip_num(ch['ru'])}: "
              f"{len(ru_lines)} реплик, до {pos / sr / 60:.1f} мин")

    add_silence(1.0)
    duration = round(pos / sr, 3)
    for i, ch in enumerate(chapters):
        ch["timeEnd"] = chapters[i + 1]["timeStart"] if i + 1 < len(chapters) else duration

    wav_path = os.path.splitext(out_audio)[0] + ".tmp.wav"
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(np.concatenate(pieces).tobytes())
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", wav_path,
                    "-c:a", "libmp3lame", "-b:a", "64k", out_audio], check=True)
    os.remove(wav_path)

    with open(out_data, "w", encoding="utf-8") as f:
        json.dump({"cues": cues, "chapters": chapters, "duration": duration}, f, ensure_ascii=False)
    print(f"Готово: {out_audio} ({duration / 60:.1f} мин), {out_data}: {len(chapters)} глав, {len(cues)} реплик")


if __name__ == "__main__":
    main()
