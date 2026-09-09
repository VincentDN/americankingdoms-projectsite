"""Replace interior provisional regions with real-world state placeholders.

For every continental US state outside the 13 colonies (and Florida, already
canon), swap the procedurally-generated river/mountain provisional region for
a placeholder shaped like that state's real-world boundary -- a visual stand-in
until custom lore-based borders exist, requested to roughly resemble published
"natural state borders" redraws. Canon geometry (data/territories.geojson
features with canon:true) is never modified; new placeholders are clipped to
land and to the existing canon footprint, and whatever land the old provisional
mesh still covers outside the new placeholders (Canada, Mexico, Central
America, Alaska) is kept, trimmed to the new seams.

Run from repo root. Requires shapely>=2.1, pyproj. Source data:
sources/natural-earth-admin1-states.geojson, Natural Earth 1:50m admin-1
states/provinces (public domain), downloaded 7 September 2026 from
https://github.com/nvkelso/natural-earth-vector/tree/master/geojson
"""
import json
from pathlib import Path
from pyproj import Transformer
from shapely import make_valid, set_precision
from shapely.geometry import shape, mapping
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree

ROOT = Path('medieval-america-map')
to = Transformer.from_crs(4326, '+proj=laea +lat_0=45 +lon_0=-100 +datum=WGS84 +units=m', always_xy=True).transform
back = Transformer.from_crs('+proj=laea +lat_0=45 +lon_0=-100 +datum=WGS84 +units=m', 4326, always_xy=True).transform


def parts(g):
    if g.is_empty:
        return []
    if g.geom_type == 'Polygon':
        return [g]
    if hasattr(g, 'geoms'):
        return [p for x in g.geoms for p in parts(x)]
    return []


def clean(g):
    return unary_union(parts(make_valid(g)))


def project(g):
    return set_precision(clean(transform(to, g)), 10)


def read(path):
    return json.loads((ROOT / path).read_text())


# Excluded: Alaska/Hawaii/DC are out of scope for this continental redraw,
# and the 13 colonies plus Florida already have real, hand-traced canon
# geometry. The canon shapes are stylised alt-history borders, not accurate
# real-world state lines (that's the point of the setting), so they do not
# reliably geometrically overlap their real-world namesakes enough to detect
# automatically -- Maine and New Hampshire's Vermont-shaped canon lobe are
# the exception, per the README, so Maine/Vermont are excluded by name too.
SKIP = {'AK', 'HI', 'DC', 'MA', 'NH', 'CT', 'RI', 'NY', 'PA', 'NJ', 'DE',
        'MD', 'VA', 'NC', 'SC', 'GA', 'FL', 'ME', 'VT'}
MIN_KEEP_AREA = 300e6      # 300 km^2, in projected square metres
MIN_LEFTOVER_AREA = 50e6   # 50 km^2

territories = read('data/territories.geojson')
canon_features = [f for f in territories['features'] if f['properties'].get('canon')]
old_provisional = [f for f in territories['features'] if not f['properties'].get('canon')]

land = project(unary_union([shape(f['geometry']) for f in read('data/land.geojson')['features']]))
lakes = project(unary_union([shape(f['geometry']) for f in read('data/lakes.geojson')['features']]))
land = clean(land.difference(lakes))
canon_union = clean(unary_union([project(shape(f['geometry'])) for f in canon_features]))

admin1 = read('sources/natural-earth-admin1-states.geojson')['features']
states = [f for f in admin1 if f['properties'].get('adm0_a3') == 'USA' and f['properties'].get('postal') not in SKIP]
states.sort(key=lambda f: shape(f['geometry']).area)

placed = []       # (postal, name, geometry)
occupied = canon_union
for f in states:
    name = f['properties']['name']
    postal = f['properties']['postal']
    g = clean(project(shape(f['geometry'])).intersection(land))
    g = clean(g.difference(occupied))
    if g.area < MIN_KEEP_AREA:
        continue
    placed.append([postal, name, g])
    occupied = clean(unary_union([occupied, g]))
new_us_union = clean(unary_union([g for _, _, g in placed]))

leftover = []
for f in old_provisional:
    g = clean(project(shape(f['geometry'])).difference(new_us_union))
    if g.area < MIN_LEFTOVER_AREA:
        continue
    leftover.append([f['properties'], g])

# Each feature was clipped independently (difference/intersection against
# canon_union or new_us_union), so shared seams are numerically exact (the
# same source geometry subtracted from both sides) but not exactly noded --
# too fine-grained for coverage_simplify's strict shared-topology check,
# which needs a single polygonize() mesh (as refine-territories.py builds)
# rather than independently-clipped polygons. Left at full resolution rather
# than simplified per-polygon, which would reintroduce real seam gaps.
placed = [(postal, name, set_precision(g, 10)) for postal, name, g in placed]
leftover = [(props, set_precision(g, 10)) for props, g in leftover]

palette = ['#b58a45', '#768757', '#a9654b', '#708984', '#b6a25e', '#8a7898',
           '#648878', '#bd8b68', '#879eac', '#a87576', '#9c995e', '#617a96']
features = list(canon_features)
assigned = []
for postal, name, g in sorted(placed, key=lambda p: p[2].representative_point().y, reverse=True):
    neighbours = {color for old, color in assigned if g.distance(old) < 100}
    color = next((c for c in palette if c not in neighbours), palette[len(assigned) % len(palette)])
    assigned.append((g, color))
    features.append({
        'type': 'Feature',
        'properties': {
            'id': 'placeholder-' + postal.lower(),
            'name': name,
            'kind': 'region',
            'color': color,
            'canon': False,
            'claim': '',
            'wiki': '',
            'summary': f'Placeholder boundary modeled on {name}’s real-world state lines. Name, lord and lore to be added.',
            'source': 'Natural Earth admin-1 boundary (real-world placeholder)',
            'boundaryStatus': 'Placeholder based on real state lines, pending custom lore-based borders',
        },
        'geometry': mapping(transform(back, g)),
    })
for props, g in leftover:
    features.append({'type': 'Feature', 'properties': dict(props), 'geometry': mapping(transform(back, g))})

print('Canon:', len(canon_features), 'Real-state placeholders:', len(placed), 'Remaining provisional:', len(leftover))

# Verify there is no unassigned land, overlap, or lake coverage before
# writing. Independent per-feature clipping (rather than one shared
# polygonize() mesh) leaves small numerical noise at new seams, so this
# uses a coarser tolerance than refine-territories.py's exact-mesh check --
# still negligible next to a continent of tens of millions of km^2.
TOLERANCE = 5e6  # 5 km^2, in projected square metres
geoms = [transform(to, shape(f['geometry'])) for f in features]
assert all(g.is_valid and not g.is_empty for g in geoms)
covered = unary_union(geoms)
assert land.difference(covered).area < TOLERANCE, ('uncovered land', land.difference(covered).area)
assert covered.difference(land).area < TOLERANCE, ('land overrun', covered.difference(land).area)
assert covered.intersection(lakes).area < TOLERANCE, ('lake overlap', covered.intersection(lakes).area)
index = STRtree(geoms)
for i, g in enumerate(geoms):
    for j in index.query(g, predicate='intersects'):
        if j > i:
            assert g.intersection(geoms[j]).area < TOLERANCE, ('overlap', i, j, g.intersection(geoms[j]).area)
print('PASS: complete land coverage, shared borders, no overlaps, clear lakes')

(ROOT / 'data/territories.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, separators=(',', ':')))
