"""Check the character loader against the data it reads. No rendering needed.

Usage: python experiments/verify_human.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from recipes import human  # noqa: E402

results = {}

# H1 -----------------------------------------------------------------------------------
# Claim (format docs): a fitted item's vertex = weighted base vertices + offset x scale,
# with offsets in MakeHuman axis order (x, y up, z front).
#
# Test: every item ships an .obj holding its shape as modelled. Fit the item to the
# unmorphed base under five possible axis conventions and compare with that shape after
# removing any wholesale shift. Items whose scale references equal the base mesh exactly
# were modelled on the unmorphed base, so the right convention must reproduce them exactly.
#
# Two earlier attempts are kept here as a record:
#  1. Comparing fit and .obj directly failed by 3 to 80 cm: most items were modelled on a
#     morphed, shifted character, so their .obj is not on the base mesh.
#  2. Measuring distance to the skin could not separate conventions for tight clothes,
#     whose offsets are only about 3 mm.
import glob  # noqa: E402

base = human.base_mesh()[0]
CONVENTIONS = {"x y z (as written)": ([0, 1, 2], [1, 1, 1]), "x z y": ([0, 2, 1], [1, 1, 1]),
               "x -z y": ([0, 2, 1], [1, -1, 1]), "x z -y": ([0, 2, 1], [1, 1, -1]),
               "x y -z": ([0, 1, 2], [1, 1, -1])}
paths = sorted(glob.glob(os.path.join(human.PACK, "clothes", "*", "*.mhclo"))
               + glob.glob(os.path.join(human.PACK, "hair", "*", "*.mhclo")))
exact, wins, exceptions = {}, 0, []
for path in paths:
    item = human.read_mhclo(path)
    authored = human.read_obj(os.path.join(item["dir"], item["obj_file"]))[0]
    ratios = [abs(base[b, i] - base[a, i]) / rec
              for i, (a, b, rec) in enumerate(item["scale"][k] for k in "xyz")]
    residual = {}
    for label, (perm, sign) in CONVENTIONS.items():
        trial = dict(item, offset=item["offset"][:, perm] * np.array(sign))
        d = human.fit(trial, base) - authored
        d -= d.mean(axis=0)
        residual[label] = float(np.sqrt((d ** 2).sum(axis=1).mean()) * 100)  # mm
    if min(residual, key=residual.get) == "x y z (as written)":
        wins += 1
    else:  # only expected for tight items modelled on a morphed character
        exceptions.append({os.path.basename(path): {k: round(v, 1) for k, v in residual.items()}})
    if all(abs(r - 1.0) < 1e-3 for r in ratios):
        exact[os.path.basename(path)] = {k: round(v, 2) for k, v in residual.items()}
results["H1"] = {
    "claim": "Clothes fitting: weighted base vertices + offset x scale, offsets in file axis order",
    "values": {"items_tested": len(paths), "items_where_file_order_fits_best": wins,
               "items_modelled_on_unmorphed_base_residual_mm": exact,
               "exceptions": exceptions},
    # Decisive evidence is the exactly-modelled items; the rest only need to agree broadly.
    "confirmed": bool(exact and all(v["x y z (as written)"] < 0.1 for v in exact.values())
                      and wins >= 0.9 * len(paths)),
}

faces_all = human.base_mesh()[2]
body_faces = [f for f in faces_all if all(v < human.BODY_VERTS for v in f)]

# H2 -----------------------------------------------------------------------------------
# Claim (macro.json): sliders pick targets whose weights multiply; body height should
# respond to the height and age sliders in the obvious direction.
def height_m(**s):
    v = human.morphed_base(**s)
    return round(float(v[:human.BODY_VERTS, 1].max()) * human.SCALE, 3)

heights = {
    "default": height_m(),
    "male": height_m(gender=1.0),
    "female": height_m(gender=0.0),
    "tall": height_m(height=1.0),
    "short": height_m(height=0.0),
    "child": height_m(age=0.19),
}
results["H2"] = {
    "claim": "Height responds sensibly to the gender, height and age sliders",
    "values_m": heights,
    "targets_used_by_default": len(human.macro_targets()),
    "confirmed": bool(heights["short"] < heights["default"] < heights["tall"]
                      and heights["child"] < heights["female"] < heights["male"]
                      and 1.4 < heights["default"] < 2.0),
}

# H3 -----------------------------------------------------------------------------------
# Claim (format docs): delete_verts lists body vertices an item covers.
item = human.read_mhclo(human.find_asset("clothes", "female_casualsuit01"))
hidden = sum(1 for f in body_faces if all(v in item["delete"] for v in f))
results["H3"] = {
    "claim": "An outfit lists covered body vertices, so skin under it can be removed",
    "values": {"covered_vertices": len(item["delete"]), "body_faces": len(body_faces),
               "faces_removed": hidden},
    "confirmed": bool(0 < hidden < len(body_faces)),
}

with open(os.path.join(HERE, "results_human.json"), "w") as fh:
    json.dump(results, fh, indent=2)
print("RESULTS " + json.dumps(results, indent=2))
