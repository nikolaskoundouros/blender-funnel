"""Render several variants of one setting as fast clay previews and tile them next to a
reference crop, so shapes can be compared side by side in one image.

Usage: python tools/variants.py SCRIPT VIEW REFERENCE_CROP OUT.png "label=settings" ...
Each settings string is passed to SCRIPT in the COLLAR environment variable.
"""
import os
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageDraw

script, view, reference, out = sys.argv[1:5]
variants = [a.split("=", 1) for a in sys.argv[5:]]
tiles = [("REFERENCE", Image.open(reference).convert("RGB").resize((360, 360)))]
with tempfile.TemporaryDirectory() as tmp:
    for label, settings in variants:
        path = os.path.join(tmp, f"{len(tiles)}.png")
        started = time.time()
        env = dict(os.environ, CLAY="1", COLLAR=settings.replace(";", ","), OUT=path)
        subprocess.run([sys.executable, script, view], env=env, check=True,
                       stdout=subprocess.DEVNULL)
        tiles.append((f"{label} ({time.time() - started:.0f}s)", Image.open(path).convert("RGB")))
sheet = Image.new("RGB", (len(tiles) * 370, 400), (20, 20, 20))
draw = ImageDraw.Draw(sheet)
for i, (label, im) in enumerate(tiles):
    sheet.paste(im, (i * 370, 36))
    draw.text((i * 370 + 8, 10), label, fill=(235, 235, 235))
sheet.save(out)
print(out)
