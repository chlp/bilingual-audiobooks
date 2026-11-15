"""
Шаг 4: собирает data.json для шаблона плеера (template.html) из пары
sv.json / ru.json -- сегментов оригинала и перевода с ОДИНАКОВЫМИ
таймкодами (перевод сделан по той же сегментации, что и распознавание,
см. guide/PROCESS.md, маршрут A). В отличие от tools/align_literary.py,
здесь НЕ нужно статистическое выравнивание Гейл-Черч -- оба языка
уже построчно синхронизированы 1:1.

Использование:
    python3 tools/build_data.py --sv sv.json --ru ru.json --title "Книга" --out data.json

Главы определяются по регэкспу на тексте оригинала (по умолчанию ловит
строки вида "Kapitel 3", "Chapter 3", "Глава 3" в начале реплики). Если
в тексте таких меток нет, всё считается одной главой.
"""
import argparse
import json
import re


DEFAULT_CHAPTER_RE = r"^[-–\s]*(kapitel|chapter|глава)\s*(\d+)?\b[:.,\s]*(.*)$"


def strip_num(title):
    # "Глава 3. Название" -> "Название"
    m = re.match(r"^\s*\S+\s+\d+\s*[.:–—-]\s*(.+)$", title)
    return m.group(1).strip() if m else title.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sv", required=True, help="sv.json из transcribe.py")
    ap.add_argument("--ru", required=True, help="ru.json -- перевод с той же сегментацией/таймкодами")
    ap.add_argument("--out", required=True, help="куда писать data.json")
    ap.add_argument("--title", default="Глава 1", help="заголовок единственной главы, если разметки глав нет")
    ap.add_argument("--chapter-regex", default=DEFAULT_CHAPTER_RE, help="regex для определения начала главы (match, не search)")
    ap.add_argument("--pause-gap", type=float, default=1.2, help="пауза между репликами (сек), которая считается границей абзаца")
    args = ap.parse_args()

    with open(args.sv, encoding="utf-8") as f:
        sv = json.load(f)
    with open(args.ru, encoding="utf-8") as f:
        ru = json.load(f)

    if len(sv) != len(ru):
        raise SystemExit(
            f"sv.json и ru.json разной длины ({len(sv)} vs {len(ru)}) -- "
            "перевод должен сохранять ту же сегментацию 1:1, см. guide/PROCESS.md, маршрут A"
        )

    chapter_re = re.compile(args.chapter_regex, re.IGNORECASE)
    m_title = chapter_re.match
    chapter_starts = []
    for i, seg in enumerate(sv):
        m = chapter_re.match(seg["text"].strip())
        if m:
            num = m.group(2)
            title = (m.group(3) or "").strip() or None
            chapter_starts.append((i, num, title))

    if not chapter_starts:
        chapter_starts = [(0, "1", args.title)]

    chapters_out = []
    for ci, (cue_start, num, sv_title) in enumerate(chapter_starts):
        cue_end = chapter_starts[ci + 1][0] if ci + 1 < len(chapter_starts) else len(sv)
        time_start = sv[cue_start]["start"]
        time_end = sv[cue_end]["start"] if cue_end < len(sv) else sv[-1]["end"]

        ru_title = (ru[cue_start]["text"].strip() if cue_start < len(ru) else None)
        ru_lines = []
        para = 0
        for i in range(cue_start, cue_end):
            if i > cue_start and sv[i]["start"] - sv[i - 1]["end"] > args.pause_gap:
                para += 1
            sv[i]["para"] = para
            ru_lines.append({
                "text": ru[i]["text"],
                "start": round(ru[i]["start"], 2),
                "end": round(ru[i]["end"], 2),
                "para": para,
                "svStart": i,
                "svEnd": i,
            })

        chapters_out.append({
            "index": ci,
            "svRawTitle": sv[cue_start]["text"],
            "svTitle": sv_title or "",
            "ruTitle": strip_num(ru_title) if ru_title else (sv_title or f"Глава {num or ci + 1}"),
            "ruNum": int(num) if num and num.isdigit() else ci + 1,
            "timeStart": time_start,
            "timeEnd": time_end,
            "cueStart": cue_start,
            "cueEnd": cue_end,
            "ruLines": ru_lines,
            "ruParaCount": para + 1,
            "titleLines": 1 if m_title(sv[cue_start]["text"]) else 0,
        })

    data = {
        "cues": sv,
        "chapters": chapters_out,
        "duration": sv[-1]["end"] if sv else 0,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"Wrote {args.out}: {len(chapters_out)} глав(а), {len(sv)} реплик")
    for ch in chapters_out:
        print(f"  {ch['ruNum']}. {ch['ruTitle']} -- реплик: {ch['cueEnd'] - ch['cueStart']}")


if __name__ == "__main__":
    main()
