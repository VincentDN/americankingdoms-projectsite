#!/usr/bin/env python3
"""One-off repair, 11 September 2026 (companion to trim-south-america-land.py).

River lines in the removed South America interior wedge would otherwise be
left dangling over open water once the land under them is gone. Clips them
out with the same wedge polygon used to trim data/land.geojson.

Run from the repository root, after trim-south-america-land.py (which
leaves /tmp/territories-orig.geojson in place):
  python medieval-america-map/scripts/trim-south-america-rivers.py
Requires shapely>=2.1.
"""
import json
from pathlib import Path

from shapely.geometry import shape, mapping, MultiLineString

ROOT = Path(__file__).resolve().parent.parent
RIVERS = ROOT / "data" / "rivers.geojson"
ORIG_TERRITORIES = Path("/tmp/territories-orig.geojson")


def main():
    orig = json.loads(ORIG_TERRITORIES.read_text())
    sa_feature = next(f for f in orig["features"] if f["properties"]["id"] == "northern-south-america-interior")
    sa_geom = shape(sa_feature["geometry"])
    wedge = max(sa_geom.geoms, key=lambda p: p.area)
    cut = wedge.buffer(0.01)

    data = json.loads(RIVERS.read_text())
    feature = data["features"][0]
    geom = shape(feature["geometry"])
    before = geom.length

    trimmed = geom.difference(cut)
    lines = list(trimmed.geoms) if trimmed.geom_type == "MultiLineString" else [trimmed]
    trimmed = MultiLineString(lines)
    after = trimmed.length
    print(f"river length {before:.1f} -> {after:.1f} deg (removed {before-after:.1f}), "
          f"parts {len(lines)}")

    feature["geometry"] = mapping(trimmed)
    RIVERS.write_text(json.dumps(data, separators=(",", ":")))
    print(f"Wrote {RIVERS} ({RIVERS.stat().st_size:,} bytes).")


if __name__ == "__main__":
    main()
