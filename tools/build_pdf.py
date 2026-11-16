"""
PDF книги из того же data.json, что и плеер, с иллюстрациями.

    python3 tools/build_pdf.py books/<slug>                    # параллельный текст, A4
    python3 tools/build_pdf.py books/<slug> --mode orig        # только оригинал, A5-книжка
    python3 tools/build_pdf.py books/<slug> --mode trans       # только перевод, A5

Вёрстка -- HTML, печать через headless Google Chrome (нужен Chrome; путь
можно задать --chrome). Параллельный режим: строки «абзац оригинала --
абзац перевода», у каждого абзаца мелкий таймкод аудио, чтобы по бумажной
книге легко найти место в записи. Результат: pdf/<slug>-<mode>.pdf (рядом с
плеером: build_html.py сам добавит в шапку плеера ссылки на все pdf/*.pdf).
"""
import argparse
import html
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookcfg import Book, load_data  # noqa: E402
from build_html import resolve_images  # noqa: E402

CHROMES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "chromium",
]

CSS_COMMON = """
html { font-family: Charter, Georgia, serif; color: #111; hyphens: auto; }
body { margin: 0; }
.front { break-after: page; text-align: center; padding-top: 40mm; }
.front h1 { font-weight: normal; font-size: 24pt; margin: 0 0 4mm; }
.front .sub { font-size: 12pt; color: #555; }
figure { margin: 4mm 0; text-align: center; break-inside: avoid; }
figure img { max-width: 100%; max-height: 85mm; border-radius: 2mm; }
.tc { font-size: 7pt; color: #aaa; font-variant-numeric: tabular-nums; margin-right: 1.5mm;
  font-family: Helvetica, Arial, sans-serif; }
.num { display: block; font-size: 8.5pt; letter-spacing: .15em; text-transform: uppercase;
  color: #777; margin-bottom: 2mm; }
.name { display: block; font-size: 15pt; font-weight: bold; }
"""

CSS_PARALLEL = """
@page { size: A4; margin: 18mm 15mm 16mm;
  @bottom-center { content: counter(page); font: 9pt Georgia, serif; color: #888; } }
html { font-size: 10pt; line-height: 1.5; }
/* div + flex, не таблица: pagedjs плохо режет таблицы между страницами
   (теряет строки с картинками) */
.row { display: flex; break-inside: avoid; margin: 0 0 3mm; }
.row > div { flex: 1 1 50%; min-width: 0; text-align: justify; }
.row > .o { padding-right: 4mm; border-right: .5pt solid #ddd; }
.row > .t { padding-left: 4mm; }
.row.head { margin: 8mm 0 5mm; }
.row.head > div { text-align: left; }
.row.head.next { break-before: page; }
"""

CSS_SINGLE = """
@page { size: A5; margin: 18mm 16mm 20mm;
  @bottom-center { content: counter(page); font: 9pt Georgia, serif; color: #555; } }
html { font-size: 10.5pt; line-height: 1.45; }
section { break-before: page; }
section h2 { font-weight: normal; text-align: center; margin: 14mm 0 10mm; }
p { margin: 0 0 .9em; text-align: justify; orphans: 2; widows: 2; }
"""


# Только для --engine pagedjs: в шапке страницы -- название главы и таймкод
# ПЕРВОГО абзаца этой страницы (string() = первое значение на странице).
# Chrome не поддерживает string-set, поэтому там таймкод только у абзацев.
CSS_PAGEDJS = """
@page { @top-center { content: string(chapter) "  \\00b7  " string(page-time);
  font: 8.3pt Georgia, serif; letter-spacing: .03em; color: #666; } }
@page :first { @top-center { content: none; } }
.chap { string-set: chapter content(); }
.tc, .ptc { string-set: page-time content(); }
.ptc { display: inline-block; width: 0; overflow: hidden; color: transparent; }
"""


MAX_ROW_CHARS = 700


def fmt_tc(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), int(t % 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def paragraphs(ch, cues):
    """Абзацы главы: [{orig, trans, time, tr: [индексы строк перевода]}].
    Диапазоны оригинала соседних абзацев могут пересекаться (выравнивание
    литературного перевода) -- оригинал печатается один раз."""
    skip = ch.get("titleLines", 0)   # строки-заголовки (вступление + "Глава N") печатаются отдельно
    groups, order = {}, []
    for i, rl in enumerate(ch["ruLines"]):
        if i < skip:
            continue
        if rl["para"] not in groups:
            groups[rl["para"]] = []
            order.append(rl["para"])
        groups[rl["para"]].append(i)
    rows, last_hi = [], ch["cueStart"] - 1
    if skip:
        last_hi = max(r["svEnd"] for r in ch["ruLines"][:skip])
    # Длинный абзац режется на куски: строка таблицы выше страницы ломает
    # pagedjs (молча обрезает документ) и плохо читается в Chrome.
    chunks = []
    for p in order:
        cur, size = [], 0
        for i in groups[p]:
            n = len(ch["ruLines"][i]["text"])
            if cur and size + n > MAX_ROW_CHARS:
                chunks.append(cur)
                cur, size = [], 0
            cur.append(i)
            size += n
        if cur:
            chunks.append(cur)
    for idx in chunks:
        lines = [ch["ruLines"][i] for i in idx]
        lo, hi = min(r["svStart"] for r in lines), max(r["svEnd"] for r in lines)
        trans = " ".join(r["text"] for r in lines)
        lo = max(lo, last_hi + 1)
        if lo > hi and rows:
            rows[-1]["trans"] += " " + trans
            rows[-1]["tr"] += idx
            continue
        orig = " ".join(cues[c]["text"].strip(" –-\t") if c == lo else cues[c]["text"] for c in range(lo, hi + 1))
        rows.append({"orig": orig, "trans": trans, "tr": idx,
                     "time": cues[lo]["start"] if lo <= hi else lines[0]["start"]})
        last_hi = max(last_hi, hi)
    return rows


def book_paragraphs(ch, cues, mode):
    """Абзацы для режима книги (orig/trans): по строкам, а не по склеенному тексту.
    Новый абзац -- на границе абзаца исходника, на реплике с тире и после неё
    (так диалоги идут каждый с новой строки, как в бумажной книге).
    -> [(text, [индексы строк перевода])] или None, если у реплик нет разметки
    абзацев (маршрут D) -- тогда берутся абзацы перевода целиком."""
    skip = ch.get("titleLines", 0)
    if mode == "orig":
        if any("para" not in cues[c] for c in range(ch["cueStart"], ch["cueEnd"])):
            return None
        first = max((r["svEnd"] for r in ch["ruLines"][:skip]), default=ch["cueStart"] - 1) + 1
        tr_of = {}
        for i, rl in enumerate(ch["ruLines"]):
            for c in range(rl["svStart"], rl["svEnd"] + 1):
                tr_of.setdefault(c, []).append(i)
        items = [(cues[c]["text"], cues[c]["para"], tr_of.get(c, [])) for c in range(first, ch["cueEnd"])]
    else:
        items = [(rl["text"], rl["para"], [i]) for i, rl in enumerate(ch["ruLines"]) if i >= skip]
    out, prev_para, prev_dash = [], None, False
    for text, para, tr in items:
        dash = text.lstrip()[:1] in "–—-"
        if not out or para != prev_para or dash or prev_dash:
            out.append([text, list(tr)])
        else:
            out[-1][0] += " " + text
            out[-1][1] += tr
        prev_para, prev_dash = para, dash
    return [tuple(x) for x in out]


def find_chrome(explicit):
    for c in ([explicit] if explicit else CHROMES):
        if os.path.isabs(c) and os.path.exists(c):
            return c
        if not os.path.isabs(c) and subprocess.run(["which", c], capture_output=True).returncode == 0:
            return c
    raise SystemExit("не найден Google Chrome / Chromium, укажите --chrome")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book")
    ap.add_argument("--mode", choices=["parallel", "orig", "trans"], default="parallel")
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--chrome")
    ap.add_argument("--engine", choices=["chrome", "pagedjs"], default="chrome",
                    help="pagedjs -- таймкод страницы в шапке (нужен node/npx, pagedjs-cli скачается сам)")
    ap.add_argument("--keep-html")
    args = ap.parse_args()
    book = Book(args.book)

    data = load_data(book)
    cues = data["cues"]
    images = {} if args.no_images else resolve_images(book, data)
    out_dir = os.path.dirname(book.path("out"))
    e = html.escape

    def figs(ch_idx, tr_idx, pos):
        res = []
        for im in images.get(ch_idx, []):
            if im["tr"] in tr_idx and im["pos"] == pos:
                src = "file://" + os.path.abspath(os.path.join(out_dir, im["src"]))
                res.append(f"<figure><img src='{e(src)}'></figure>")
        return "".join(res)

    lang = book["origLang"] if args.mode == "orig" else book["transLang"]
    parts = [f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><title>{e(book['title'])}</title>"
             f"<style>{CSS_COMMON}{CSS_PARALLEL if args.mode == 'parallel' else CSS_SINGLE}"
             f"{CSS_PAGEDJS if args.engine == 'pagedjs' else ''}</style></head><body>"]
    parts.append(f"<div class='front'><h1>{e(book['title'])}</h1>"
                 f"<div class='sub'>{e(book.get('subtitle', ''))}</div></div>")

    for ci, ch in enumerate(data["chapters"]):
        sv_title = ch.get("svTitle") or ch.get("svRawTitle", "").strip(" –-")
        rows = paragraphs(ch, cues)
        if args.mode == "parallel":
            nxt = " next" if ci else ""
            parts.append(f"<div class='row head{nxt}'><div class='o'><span class='num'>{ch['ruNum']}</span>"
                         f"<span class='name'>{e(sv_title)}</span></div>"
                         f"<div class='t'><span class='num'>{ch['ruNum']}</span>"
                         f"<span class='name chap'>{e(ch['ruTitle'])}</span></div></div>")
            for r in rows:
                before, after = figs(ci, r["tr"], "before"), figs(ci, r["tr"], "after")
                parts.append(before)
                parts.append(f"<div class='row'><div class='o'><span class='tc'>{fmt_tc(r['time'])}</span>{e(r['orig'])}</div>"
                             f"<div class='t'>{e(r['trans'])}</div></div>")
                parts.append(after)
        else:
            title = sv_title if args.mode == "orig" else ch["ruTitle"]
            parts.append(f"<section><h2><span class='num'>{ch['ruNum']}</span>"
                         f"<span class='name chap'>{e(title)}</span></h2>")
            paras = book_paragraphs(ch, cues, args.mode) or [(r["orig"], r["tr"]) for r in rows]
            for text, tr in paras:
                parts.append(figs(ci, tr, "before"))
                t0 = ch["ruLines"][tr[0]]["start"] if tr else ch["timeStart"]
                tc = f"<span class='ptc'>{fmt_tc(t0)}</span>" if args.engine == "pagedjs" else ""
                parts.append(f"<p>{tc}{e(text)}</p>")
                parts.append(figs(ci, tr, "after"))
            parts.append("</section>")
    parts.append("</body></html>")

    out = os.path.abspath(args.out or book.path("pdf", f"{book['slug']}-{args.mode}.pdf"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        hp = args.keep_html or os.path.join(td, "book.html")
        with open(hp, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))
        if args.engine == "pagedjs":
            # тайм-аут по умолчанию мал: книга с картинками молча обрезается на середине
            subprocess.run(["npx", "-y", "pagedjs-cli@0.4.3", "-t", "1800000",
                            "-i", os.path.abspath(hp), "-o", out], check=True)
        else:
            subprocess.run([find_chrome(args.chrome), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                            "--allow-file-access-from-files", f"--print-to-pdf={out}", "file://" + os.path.abspath(hp)],
                           check=True, capture_output=True)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
