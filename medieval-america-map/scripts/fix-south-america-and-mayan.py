#!/usr/bin/env python3
"""One-off repair, 11 September 2026.

Two independent edits to data/territories.geojson, run together since both
touch the Central America / Caribbean region:

1. "Uncharted Northern South America" (id northern-south-america-interior)
   is a leftover-land MultiPolygon with thousands of parts worldwide (mostly
   sub-pixel Aleutian island slivers). One part -- index 5397 in the source
   file, bounds roughly lon -81..-58, lat -5..11 -- is the large blank
   interior wedge south of Roman Colonies that Vincent marked for removal
   (no coastline of its own, just an inland clip artifact from the original
   Natural Earth import). This drops only that one part; every other sliver
   is untouched.

2. Mayan Civilizations already covered the Yucatan peninsula; it's expanded
   south and west to absorb the neighbouring unclaimed provisional realms
   43 (Chiapas/Guatemala/Belize) and 45 (El Salvador/Honduras/Nicaragua
   Pacific coast), matching Vincent's traced extent and the real historical
   reach of Maya civilization. Renamed Mayan Civilizations -> Mayan States.

Run from the repository root: python medieval-america-map/scripts/fix-south-america-and-mayan.py
Requires shapely>=2.1.
"""
import json
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
TERRITORIES = ROOT / "data" / "territories.geojson"

WEDGE_BOUNDS_HINT = (-81.34, -5.0, -58.0, 11.32)  # for a sanity check only


def main():
    data = json.loads(TERRITORIES.read_text())
    features = data["features"]
    by_id = {f["properties"]["id"]: f for f in features}

    # --- 1. Drop the South America interior wedge -----------------------
    sa = by_id["northern-south-america-interior"]
    sa_geom = shape(sa["geometry"])
    assert sa_geom.geom_type == "MultiPolygon"
    parts = list(sa_geom.geoms)
    parts_sorted = sorted(range(len(parts)), key=lambda i: -parts[i].area)
    wedge_idx = parts_sorted[0]
    wedge = parts[wedge_idx]
    b = tuple(round(x, 1) for x in wedge.bounds)
    hint = tuple(round(x, 1) for x in WEDGE_BOUNDS_HINT)
    assert b == hint, f"largest part bounds {b} != expected {hint}; re-check before removing"
    remaining = [p for i, p in enumerate(parts) if i != wedge_idx]
    from shapely.geometry import MultiPolygon
    sa["geometry"] = mapping(MultiPolygon(remaining))
    print(f"Removed South America wedge (area {wedge.area:.1f} sq deg) from "
          f"{sa['properties']['id']}; {len(remaining)} parts remain.")

    # --- 2. Expand Mayan Civilizations into Mayan States -----------------
    mayan = by_id["reference-mayan-civilizations"]
    realm_43 = by_id["provisional-realm-43"]
    realm_45 = by_id["provisional-realm-45"]

    mayan_geom = shape(mayan["geometry"])
    g43 = shape(realm_43["geometry"])
    g45 = shape(realm_45["geometry"])

    merged = unary_union([mayan_geom, g43, g45])
    from shapely.geometry import MultiPolygon
    if merged.geom_type == "Polygon":
        merged = MultiPolygon([merged])

    # realm-43's canon-provisional seam is imprecise around the Isthmus of
    # Tehuantepec: unioning produces a disconnected Oaxaca-ward blob (west
    # of lon -96, well outside the real Maya heartland) plus dozens of
    # sub-pixel topology slivers in that same seam. Keep the main body and
    # any genuine offshore island (small, on the Caribbean side, east of
    # the isthmus); drop the rest.
    parts_list = list(merged.geoms)
    main_idx = max(range(len(parts_list)), key=lambda i: parts_list[i].area)
    main_part = parts_list[main_idx]
    kept = [main_part]
    dropped = 0
    for i, part in enumerate(parts_list):
        if i == main_idx:
            continue
        minx = part.bounds[0]
        if part.area > 1e-5 and minx > -96:
            kept.append(part)
        else:
            dropped += 1
    merged = MultiPolygon(kept)
    print(f"Mayan merge: {mayan_geom.area:.2f} + {g43.area:.2f} + {g45.area:.2f} "
          f"-> {merged.area:.2f} sq deg, valid={merged.is_valid}, "
          f"parts={len(merged.geoms)} kept, {dropped} sliver/exclave parts dropped")

    # New label position: representative point of the largest part, biased
    # toward the historical Maya heartland (Peten/Yucatan) rather than a
    # pure geometric centroid, which would land near the coastline seam.
    largest = max(merged.geoms, key=lambda p: p.area)
    label_pt = largest.representative_point()

    mayan["geometry"] = mapping(merged)
    mayan["properties"].update({
        "id": "mayan-states",
        "name": "Mayan States",
        "flag": "assets/flags/mayan-states.svg",
        "shield": "assets/flags/mayan-states-shield.svg",
        "boundaryStatus": "Expanded to absorb neighbouring unclaimed provisional territory on 2026-09-11",
        "label": [label_pt.x, label_pt.y],
    })

    features.remove(realm_43)
    features.remove(realm_45)
    print("Removed provisional-realm-43 and provisional-realm-45 (merged into mayan-states).")

    TERRITORIES.write_text(json.dumps(data, separators=(",", ":")))
    print(f"Wrote {TERRITORIES} ({TERRITORIES.stat().st_size:,} bytes).")


if __name__ == "__main__":
    main()
