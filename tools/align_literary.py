"""
Маршрут D: есть аудио с точными субтитрами оригинала (.srt) и ГОТОВЫЙ
литературный перевод сплошным текстом без таймкодов. Выравнивает их по главам
статистически (в духе Гейл-Черч, 1993) и пишет data.json.

    python3 tools/align_literary.py --srt build/sv.srt --text source/ru.txt --out build/data.json

Формат --text: заголовки глав строкой "Глава N. Название" (regex --chapter-trans),
абзацы через пустую строку. Начала глав в .srt -- реплики, совпадающие с
--chapter-orig (match, не search: служебное "kapitel" в середине текста не
считается). Число глав в обоих файлах должно совпадать.

Каждому предложению перевода назначается время, интерполированное внутри
сопоставленного диапазона реплик оригинала. Это ОЦЕНКА: возможен дрейф на
несколько секунд там, где перевод переставляет или объединяет фразы. Если
перевод ещё не сделан -- лучше маршрут A (перевод сегмент-в-сегмент), он точный.
"""
import argparse
import json
import re


def ts_to_sec(ts):
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(path):
    with open(path, encoding="utf-8") as f:
        blocks = re.split(r"\n\s*\n", f.read().strip())
    cues = []
    for b in blocks:
        lines = b.strip().split("\n")
        if len(lines) < 2:
            continue
        m = re.match(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", lines[1].strip())
        if not m:
            continue
        text = " ".join(x.strip() for x in lines[2:]).strip()
        cues.append({"start": ts_to_sec(m.group(1)), "end": ts_to_sec(m.group(2)), "text": text})
    return cues


def parse_text(path, chapter_re):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    starts = []
    for i, l in enumerate(lines):
        m = chapter_re.match(l.strip())
        if m:
            starts.append((i, int(m.group(1)), m.group(2).strip()))
    chapters = []
    for k, (li, num, title) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        body = "\n".join(lines[li + 1:end]).strip()
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        chapters.append({"num": num, "title": title, "paragraphs": paras})
    return chapters


# Под русский перевод; для другого языка перевода поправить класс заглавных букв.
SENT_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[А-ЯЁ0-9—–\"«])")


def split_sentences(paragraph):
    parts = [p.strip() for p in SENT_SPLIT_RE.split(paragraph) if p.strip()]
    return parts or [paragraph.strip()]


def align_chapter(sv_cues, ru_sentences):
    """Монотонное выравнивание по длине: ходы 1-1, 1-2, 2-1, 2-2 и пропуски.
    -> [{text, start, end, svStart, svEnd}] (svStart/svEnd локальные для главы)."""
    n, m = len(sv_cues), len(ru_sentences)
    sv_lens = [max(1, len(c["text"])) for c in sv_cues]
    ru_lens = [max(1, len(s)) for s in ru_sentences]
    r = sum(ru_lens) / sum(sv_lens) if sv_lens else 1.0

    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    choice = [[None] * (m + 1) for _ in range(n + 1)]

    def cost(ls, lt, ds, dt):
        if ds == 0 or dt == 0:
            return 6.0 + 2.0 * (ds + dt)
        expected = ls * r
        var = max(expected, 3.0) * 0.65
        penalty = 0.0 if (ds == 1 and dt == 1) else 1.6 + 0.7 * (ds + dt - 2)
        return (lt - expected) ** 2 / var + penalty

    moves = [(1, 1), (1, 2), (2, 1), (1, 0), (0, 1), (2, 2)]
    for i in range(n + 1):
        for j in range(m + 1):
            cur = dp[i][j]
            if cur == INF:
                continue
            for ds, dt in moves:
                ni, nj = i + ds, j + dt
                if ni > n or nj > m:
                    continue
                c = cur + cost(sum(sv_lens[i:ni]), sum(ru_lens[j:nj]), ds, dt)
                if c < dp[ni][nj]:
                    dp[ni][nj] = c
                    choice[ni][nj] = (i, j)

    groups = []
    i, j = n, m
    while (i, j) != (0, 0):
        step = choice[i][j] or ((i - 1, j) if i > 0 else (i, j - 1))
        groups.append((step[0], i, step[1], j))
        i, j = step
    groups.reverse()

    results = [None] * m
    prev_end = sv_cues[0]["start"] if sv_cues else 0.0
    prev_range = (0, 0)
    for i0, i1, j0, j1 in groups:
        if i1 > i0:
            span_start, span_end = sv_cues[i0]["start"], sv_cues[i1 - 1]["end"]
            prev_end, prev_range = span_end, (i0, i1 - 1)
        else:
            span_start = span_end = prev_end
        if j1 > j0:
            sub = ru_lens[j0:j1]
            total, acc, dur = sum(sub) or 1, 0.0, max(span_end - span_start, 0.0)
            for k, idx in enumerate(range(j0, j1)):
                s = span_start + acc / total * dur
                acc += sub[k]
                e = span_start + acc / total * dur
                results[idx] = {"text": ru_sentences[idx], "start": s, "end": max(e, s),
                                "svStart": prev_range[0], "svEnd": prev_range[1]}
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--srt", required=True, help="субтитры оригинала с точными таймкодами")
    ap.add_argument("--text", required=True, help="перевод сплошным текстом, главы + абзацы")
    ap.add_argument("--out", required=True, help="куда писать data.json")
    ap.add_argument("--chapter-orig", default=r"^[-–\s]*(kapitel|chapter)\b", help="regex начала главы в .srt")
    ap.add_argument("--chapter-trans", default=r"^Глава\s+(\d+)\.\s*(.*)$", help="regex заголовка главы в переводе (2 группы: номер, название)")
    args = ap.parse_args()

    cues = parse_srt(args.srt)
    orig_re = re.compile(args.chapter_orig, re.IGNORECASE)
    starts = [i for i, c in enumerate(cues) if orig_re.match(c["text"])]
    trans = parse_text(args.text, re.compile(args.chapter_trans))
    if len(starts) != len(trans):
        raise SystemExit(f"глав в .srt: {len(starts)}, в переводе: {len(trans)} -- должно совпадать")

    chapters = []
    for ci, cue_start in enumerate(starts):
        cue_end = starts[ci + 1] if ci + 1 < len(starts) else len(cues)
        ch = trans[ci]
        sents, para_of = [], []
        for pi, para in enumerate(ch["paragraphs"]):
            for s in split_sentences(para):
                sents.append(s)
                para_of.append(pi)
        aligned = align_chapter(cues[cue_start:cue_end], sents)
        last_t, last_sv = cues[cue_start]["start"], 0
        lines = []
        for idx, res in enumerate(aligned):
            if res is None:
                res = {"text": sents[idx], "start": last_t, "end": last_t, "svStart": last_sv, "svEnd": last_sv}
            last_t, last_sv = res["end"], res["svEnd"]
            lines.append({
                "text": res["text"], "start": round(res["start"], 2), "end": round(max(res["end"], res["start"]), 2),
                "para": para_of[idx],
                "svStart": cue_start + res["svStart"], "svEnd": cue_start + res["svEnd"],  # глобальные
            })
        chapters.append({
            "index": ci, "svRawTitle": cues[cue_start]["text"], "ruTitle": ch["title"], "ruNum": ch["num"],
            "timeStart": cues[cue_start]["start"],
            "timeEnd": cues[cue_end]["start"] if cue_end < len(cues) else cues[-1]["end"],
            "cueStart": cue_start, "cueEnd": cue_end, "ruLines": lines, "ruParaCount": len(ch["paragraphs"]),
        })

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"cues": cues, "chapters": chapters, "duration": cues[-1]["end"] if cues else 0},
                  f, ensure_ascii=False)
    print(f"Wrote {args.out}: {len(chapters)} глав, {len(cues)} реплик")


if __name__ == "__main__":
    main()
