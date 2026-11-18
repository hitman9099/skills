"""Audit named Blender objects in the source scenes actually used by a course."""

import argparse
import json
from pathlib import Path
import sys

import bpy


def sources(base, overlays):
    selected = {}
    for folder in (base, *overlays):
        folder = folder.resolve()
        if not folder.is_dir():
            raise ValueError(f"Scene directory does not exist: {folder}")
        scenes = sorted(folder.glob("*.blend"))
        if not scenes:
            raise ValueError(f"No .blend files found in {folder}")
        for path in scenes:
            selected[path.name.casefold()] = path
    return sorted(selected.values(), key=lambda path: path.name.casefold())


def enabled_collection_pointers(layer_collection):
    """Yield collections enabled for rendering along this view-layer path."""
    if layer_collection.exclude or layer_collection.collection.hide_render:
        return
    yield layer_collection.collection.as_pointer()
    for child in layer_collection.children:
        yield from enabled_collection_pointers(child)


def matches(scene, prefixes, object_type, visible_only):
    render_layers = {}
    for layer in scene.view_layers:
        if layer.use:
            render_layers[layer.name] = set(enabled_collection_pointers(layer.layer_collection))
    result = []
    for obj in sorted(scene.objects, key=lambda obj: obj.name.casefold()):
        if not obj.name.casefold().startswith(prefixes) or (object_type and obj.type != object_type):
            continue
        linked_collections = {coll.as_pointer() for coll in obj.users_collection}
        enabled = [] if obj.hide_render else [
            layer_name for layer_name, collections in render_layers.items()
            if linked_collections & collections
        ]
        if visible_only and not enabled:
            continue
        result.append({
            "name": obj.name,
            "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "hide_render": obj.hide_render,
            "eligible_render_layers": enabled,
        })
    return result


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-dir", required=True, type=Path, help="Directory with original .blend shots")
    parser.add_argument("--overlay-dir", action="append", type=Path, default=[],
                        help="Override same-named shots, in the order provided")
    parser.add_argument("--prefix", action="append", required=True,
                        help="Case-insensitive object name prefix. May be repeated")
    parser.add_argument("--type", type=str.upper, choices=sorted(
        item.identifier for item in bpy.types.Object.bl_rna.properties["type"].enum_items
    ), help="Only report this Blender object type")
    parser.add_argument("--visible-only", action="store_true",
                        help="Limit matches to objects eligible in an enabled render layer at the saved frame")
    parser.add_argument("--json", type=Path, help="Optional JSON report path")
    parser.add_argument("--fail-on-match", action="store_true", help="Fail the audit when any matching object is found")
    args = parser.parse_args(argv)
    if any(not prefix.strip() for prefix in args.prefix):
        parser.error("--prefix must not be empty")
    prefixes = tuple(prefix.casefold() for prefix in args.prefix)
    found = []
    match_count = 0
    for path in sources(args.scene_dir, args.overlay_dir):
        if "use_scripts" not in bpy.ops.wm.open_mainfile.get_rna_type().properties:
            raise RuntimeError("This Blender version cannot disable scripts while loading the scene")
        bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
        scenes = []
        for scene in sorted(bpy.data.scenes, key=lambda scene: scene.name):
            objects = matches(scene, prefixes, args.type, args.visible_only)
            match_count += len(objects)
            for obj in objects:
                print(f"{path.name} / {scene.name}: {obj['name']} ({obj['type']})", flush=True)
            scenes.append({"scene": scene.name, "saved_frame": scene.frame_current, "objects": objects})
        found.append({"file": str(path), "scenes": scenes})
    report = {"files_scanned": len(found), "matches": match_count, "files": found}
    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Audited {len(found)} files, found {match_count} matching objects.", flush=True)
    if args.fail_on_match and match_count:
        raise RuntimeError(f"{match_count} matching objects remain")


if __name__ == "__main__":
    if "--" not in sys.argv:
        raise SystemExit("Pass audit arguments after Blender's -- separator.")
    main(sys.argv[sys.argv.index("--") + 1:])
