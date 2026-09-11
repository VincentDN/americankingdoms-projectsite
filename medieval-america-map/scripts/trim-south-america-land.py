#!/usr/bin/env python3
"""Repair, 11 September 2026 (revised same day after review).

The "Uncharted Northern South America" territory Vincent asked to remove
was only the pale political overlay; the physical land itself
(data/land.geojson) is a separate base layer. A first pass subtracted the
*entire* wedge polygon from the continental land ring, which also stripped
the ordinary coastal margin around Roman Colonies and Muslim Settlements --
with no plain unclaimed land left beside them, both read as a stark,
uniform-width ribbon floating over open water ("stretched looking") instead
of sitting within a believable coastline, the way unclaimed land reads
everywhere else on the map.

This revised cut keeps a buffer of ordinary land around every territory
that actually touches the wedge (Roman Colonies, Muslim Settlements, the
Aotearoan Settlements sliver and provisional-realm-46/Panama), removing
only the deep interior that's genuinely far from any of them. A first
attempt at this used only a 0.4 degree margin, which technically restored
some backing land but left it exactly as narrow as the territories
themselves -- so Roman Colonies still read as a stretched, uniform-width
ribbon, just with a thin cream outline. 2.5 degrees (roughly 275 km) gives
those coastal territories a believable landmass to sit inside, matching
how the map looked before the wedge existed, while still removing about
80% of the original wedge (roughly 245 of 308 sq-degrees) -- the genuinely
deep, coastline-less interior and the straight clip-box artifact edges.

Run from the repository root:
  git show 9ba73e4:medieval-america-map/data/territories.geojson > /tmp/territories-pre-wedge.geojson
  git show 9ba73e4:medieval-america-map/data/land.geojson > /tmp/land-pretrim.geojson
  python medieval-america-map/scripts/trim-south-america-land.py
Requires shapely>=2.1. 9ba73e4 is the commit before any of this South
America/Mayan work started; re-run against the current pre-edit commit if
this script is reused later.
"""
import json
from pathlib import Path

from shapely.geometry import shape, mapping, MultiPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent.parent
LAND = ROOT / "data" / "land.geojson"
PRE_TERRITORIES = Path("/tmp/territories-pre-wedge.geojson")
PRE_LAND = Path("/tmp/land-pretrim.geojson")

KEEP_MARGIN_DEGREES = 2.5
NEARBY_IDS = [
    "reference-muslim-settlements",
    "reference-roman-colonies",
    "reference-aotearoan-settlements-polynesian",
    "provisional-realm-46",
]


def main():
    orig = json.loads(PRE_TERRITORIES.read_text())
    by_id = {f["properties"]["id"]: f for f in orig["features"]}
    sa_geom = shape(by_id["northern-south-america-interior"]["geometry"])
    wedge = max(sa_geom.geoms, key=lambda p: p.area)
    print(f"wedge area {wedge.area:.1f}, bounds {tuple(round(x,2) for x in wedge.bounds)}")

    nearby = unary_union([shape(by_id[i]["geometry"]) for i in NEARBY_IDS])
    keep_margin = nearby.buffer(KEEP_MARGIN_DEGREES)
    remove_region = wedge.difference(keep_margin)
    print(f"removing {remove_region.area:.1f} of {wedge.area:.1f} sq deg "
          f"(keeping a {KEEP_MARGIN_DEGREES} deg margin around Roman Colonies, "
          f"Muslim Settlements and neighbours)")

    land_data = json.loads(PRE_LAND.read_text())
    land_feature = land_data["features"][0]
    land_geom = shape(land_feature["geometry"])
    assert land_geom.geom_type == "MultiPolygon"

    before_area = land_geom.area
    cut = remove_region.buffer(0.01)
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

    # Save the refined removal region for trim-south-america-rivers.py to reuse.
    Path("/tmp/sa-remove-region.geojson").write_text(json.dumps(mapping(remove_region)))


if __name__ == "__main__":
    main()
