"""Put a reference image and a render next to each other at the same height.

Usage: python tools/side_by_side.py reference.png render.png out.png [label_left label_right]
"""
import sys

from PIL import Image, ImageDraw


def side_by_side(reference, render, out, labels=("REFERENCE", "OURS"), height=1080, gap=16):
    images = [Image.open(p).convert("RGB") for p in (reference, render)]
    scaled = [im.resize((round(im.width * height / im.height), height), Image.LANCZOS) for im in images]
    band = 44
    sheet = Image.new("RGB", (scaled[0].width + gap + scaled[1].width, height + band), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    x = 0
    for im, label in zip(scaled, labels):
        sheet.paste(im, (x, band))
        draw.text((x + 12, 12), label, fill=(235, 235, 235))
        x += im.width + gap
    sheet.save(out)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    labels = tuple(args[3:5]) if len(args) >= 5 else ("REFERENCE", "OURS")
    print(side_by_side(args[0], args[1], args[2], labels))
