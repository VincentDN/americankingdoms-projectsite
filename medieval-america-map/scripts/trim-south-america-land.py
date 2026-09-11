#!/usr/bin/env python3
"""One-off repair, 11 September 2026 (companion to fix-south-america-and-mayan.py).

The "Uncharted Northern South America" territory Vincent asked to remove
was only the pale political overlay; the physical land itself
(data/land.geojson) is a separate base layer and still filled that whole
blank interior wedge with ordinary tan land. This subtracts the exact same
wedge polygon (recovered from the pre-edit territories.geojson via git)
from the single continental land ring, leaving North/Central America and
the Roman Colonies coastal strip untouched and removing the empty interior
south/east of it.

Run from the repository root, after fix-south-america-and-mayan.py:
  git show HEAD:medieval-america-map/data/territories.geojson > /tmp/territories-orig.geojson
  python medieval-america-map/scripts/trim-south-america-land.py
Requires shapely>=2.1.
"""
import json
from pathlib import Path

from shapely.geometry import shape, mapping, MultiPolygon
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent.parent
LAND = ROOT / "data" / "land.geojson"
ORIG_TERRITORIES = Path("/tmp/territories-orig.geojson")


def main():
    orig = json.loads(ORIG_TERRITORIES.read_text())
    sa_feature = next(f for f in orig["features"] if f["properties"]["id"] == "northern-south-america-interior")
    sa_geom = shape(sa_feature["geometry"])
    wedge = max(sa_geom.geoms, key=lambda p: p.area)
    print(f"wedge area {wedge.area:.1f}, bounds {tuple(round(x,2) for x in wedge.bounds)}")

    land_data = json.loads(LAND.read_text())
    land_feature = land_data["features"][0]
    land_geom = shape(land_feature["geometry"])
    assert land_geom.geom_type == "MultiPolygon"

    before_area = land_geom.area
    # Buffer the cut slightly outward so no sliver rim of land survives
    # along the wedge's old straight clip edges.
    cut = wedge.buffer(0.01)
    trimmed = land_geom.difference(cut)
    trimmed = make_valid(trimmed)
    if trimmed.geom_type == "Polygon":
        trimmed = MultiPolygon([trimmed])
    after_area = trimmed.area
    print(f"land area {before_area:.1f} -> {after_area:.1f} sq deg "
          f"(removed {before_area - after_area:.1f}), valid={trimmed.is_valid}, "
          f"parts={len(trimmed.geoms)}")

    land_feature["geometry"] = mapping(trimmed)
    LAND.write_text(json.dumps(land_data, separators=(",", ":")))
    print(f"Wrote {LAND} ({LAND.stat().st_size:,} bytes).")


if __name__ == "__main__":
    main()
