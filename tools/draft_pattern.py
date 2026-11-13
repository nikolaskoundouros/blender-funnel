"""Draft a sewing pattern with GarmentCode (ETH Zurich, MIT licence) and save its pattern file.

GarmentCode turns body measurements plus design choices into flat panels and stitches.
This script only drafts; sewing and draping happen in Blender (recipes/patterns.py and
recipes/cloth.py). It runs in its own Python environment because GarmentCode's
dependencies are separate from Blender's.

Usage:
  python tools/draft_pattern.py GARMENTCODE_DIR BODY.yaml OUT.json key=value [key=value ...]
Example design keys: meta.upper=Shirt sleeve.sleeveless=false sleeve.length=1.0
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import yaml


def main():
    gc_dir, body_file, out_file = (os.path.abspath(a) for a in sys.argv[1:4])
    settings = [a.split("=", 1) for a in sys.argv[4:]]
    os.chdir(gc_dir)                 # the library loads its assets by relative path
    sys.path.insert(0, gc_dir)
    from assets.bodies.body_params import BodyParameters
    from assets.garment_programs.meta_garment import MetaGarment

    with open("assets/design_params/default.yaml") as fh:
        design = yaml.safe_load(fh)["design"]
    for key, value in settings:
        node = design
        parts = key.split(".")
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]]["v"] = yaml.safe_load(value)

    garment = MetaGarment("garment", BodyParameters(body_file), design)
    pattern = garment.assembly()
    with tempfile.TemporaryDirectory() as tmp:
        folder = pattern.serialize(Path(tmp), tag="", to_subfolder=True, with_3d=False,
                                   with_text=False, view_ids=False, with_printable=False)
        spec = next(Path(folder).glob("*specification.json"))
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        shutil.copy(spec, out_file)
    with open(out_file) as fh:
        panels = json.load(fh)["pattern"]["panels"]
    print("DRAFTED " + json.dumps({"panels": list(panels), "self_intersecting": bool(garment.is_self_intersecting()),
                                   "settings": dict(settings)}))


if __name__ == "__main__":
    main()
