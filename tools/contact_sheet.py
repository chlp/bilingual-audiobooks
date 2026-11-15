"""
Контакт-лист: все картинки сеткой с подписями -- чтобы одним взглядом
проверить единообразие персонажей и выбрать вариант листа персонажей.

    python3 tools/contact_sheet.py books/<slug>/illustrations/characters/*.png -o /tmp/variants.png
    python3 tools/contact_sheet.py books/<slug>/illustrations/ch*/*.png -o /tmp/scenes.png --cols 4

Подпись под картинкой -- путь относительно общей папки (например ch09/03.png),
именно его удобно назвать Codex при просьбе перегенерировать.
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--width", type=int, default=480, help="ширина миниатюры")
    args = ap.parse_args()

    paths = sorted(p for p in args.images if os.path.isfile(p))
    if not paths:
        raise SystemExit("нет картинок")
    base = os.path.commonpath([os.path.dirname(os.path.abspath(p)) for p in paths])
    thumbs = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        im.thumbnail((args.width, args.width * 2))
        thumbs.append((os.path.relpath(os.path.abspath(p), base), im))
    cell_h = max(im.height for _, im in thumbs) + 34
    rows = (len(thumbs) + args.cols - 1) // args.cols
    sheet = Image.new("RGB", (args.cols * (args.width + 12) + 12, rows * cell_h + 12), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except OSError:
        font = ImageFont.load_default()
    for k, (label, im) in enumerate(thumbs):
        x = 12 + (k % args.cols) * (args.width + 12)
        y = 12 + (k // args.cols) * cell_h
        sheet.paste(im, (x, y))
        draw.text((x, y + im.height + 6), label, fill="black", font=font)
    sheet.save(args.out)
    print(f"Wrote {args.out}: {len(thumbs)} картинок")


if __name__ == "__main__":
    main()
