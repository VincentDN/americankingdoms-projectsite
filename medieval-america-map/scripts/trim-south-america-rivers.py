#!/usr/bin/env python3
"""Repair, 11 September 2026 (revised same day; see trim-south-america-land.py).

Clips the same refined removal region (the deep South America interior,
minus a kept margin around Roman Colonies/Muslim Settlements/neighbours)
out of data/rivers.geojson, so no river segments are left dangling over
open water once the land under them is gone.

Run from the repository root, after trim-south-america-land.py (which
writes /tmp/sa-remove-region.geojson):
  git show 9ba73e4:medieval-america-map/data/rivers.geojson > /tmp/rivers-pretrim.geojson
  python medieval-america-map/scripts/trim-south-america-rivers.py
Requires shapely>=2.1.
"""
import json
from pathlib import Path

from shapely.geometry import shape, mapping, MultiLineString

ROOT = Path(__file__).resolve().parent.parent
RIVERS = ROOT / "data" / "rivers.geojson"
PRE_RIVERS = Path("/tmp/rivers-pretrim.geojson")
REMOVE_REGION = Path("/tmp/sa-remove-region.geojson")


def main():
    remove_region = shape(json.loads(REMOVE_REGION.read_text()))
    cut = remove_region.buffer(0.01)

    data = json.loads(PRE_RIVERS.read_text())
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
