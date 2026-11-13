"""Turn a label seen on screen in a tutorial into the Python name that controls it.

Blender builds its UI from the same property and operator definitions that Python uses,
so the text on a button ("Roughness", "Add Monkey", "Depth of Field") can be looked up
and resolved to an operator or property. This is the join between a video analyzer's
output (what was clicked) and a script (what to call).

Usage:
  python tools/label_index.py "Add Monkey" "Roughness" "F-Stop"
  python tools/label_index.py --dump labels.json     # full index for this Blender version
"""
import json
import sys
from collections import defaultdict

import bpy


def build():
    index = defaultdict(list)
    for module_name in dir(bpy.ops):
        module = getattr(bpy.ops, module_name)
        for op_name in dir(module):
            try:
                rna = getattr(module, op_name).get_rna_type()
            except Exception:
                continue
            index[rna.name.lower()].append(
                {"kind": "operator", "call": f"bpy.ops.{module_name}.{op_name}()",
                 "help": rna.description})
    for type_name in dir(bpy.types):
        rna = getattr(getattr(bpy.types, type_name), "bl_rna", None)
        if rna is None:
            continue
        inherited = set(rna.base.properties.keys()) if rna.base else set()
        for prop in rna.properties:
            if prop.identifier == "rna_type" or not prop.name or prop.identifier in inherited:
                continue  # inherited properties are listed once, on the type that defines them
            index[prop.name.lower()].append(
                {"kind": "property", "path": f"{type_name}.{prop.identifier}",
                 "help": prop.description})
            if prop.type == "ENUM":  # dropdown entries, e.g. modifier or light types
                for item in prop.enum_items:
                    if item.name:
                        index[item.name.lower()].append(
                            {"kind": "choice",
                             "path": f"{type_name}.{prop.identifier} = {item.identifier!r}",
                             "help": item.description})
    return index


def lookup(index, label):
    """Exact match first; otherwise labels that contain the text or share its identifier."""
    key = label.lower()
    if key in index:
        return index[key]
    ident = key.replace(" ", "_").replace("-", "_")
    loose = []
    for name, hits in index.items():
        for hit in hits:
            target = (hit.get("call") or hit.get("path")).lower()
            if key in name or ident in target:
                loose.append(hit)
    return loose


if __name__ == "__main__":
    idx = build()
    if len(sys.argv) > 2 and sys.argv[1] == "--dump":
        with open(sys.argv[2], "w") as fh:
            json.dump({"blender": bpy.app.version_string, "labels": idx}, fh)
        print(f"{len(idx)} labels written for Blender {bpy.app.version_string}")
    else:
        for label in sys.argv[1:]:
            hits = lookup(idx, label)
            print(f"{label!r}: {len(hits)} match(es)")
            for hit in hits[:8]:
                print("   ", hit.get("call") or hit.get("path"), "-", hit["help"][:80])
