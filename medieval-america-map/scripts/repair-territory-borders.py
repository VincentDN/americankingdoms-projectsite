"""Repair narrow tracing gaps and apply the requested Aztec/Dragon Coast expansion.
Usage: python repair-territory-borders.py PRE_REPAIR_TERRITORIES.geojson
Requires shapely >= 2.1, numpy and pyproj. All distances below are metres.
Run after import-world-reference.py; use a pre-repair snapshot for repeatability.
"""
import json, sys
from pathlib import Path
import numpy as np
from shapely import make_valid, voronoi_polygons
from shapely.geometry import shape, mapping, Polygon, MultiPoint, Point
from shapely.ops import unary_union, transform
from pyproj import Transformer

root = Path(__file__).resolve().parents[1]
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
to = Transformer.from_crs(4326, 5070, always_xy=True).transform
back = Transformer.from_crs(5070, 4326, always_xy=True).transform
def parts(g):
    if g.geom_type == 'Polygon': return [g]
    return [p for child in getattr(g, 'geoms', []) for p in parts(child)]
def clean(g): return unary_union(parts(make_valid(g)))
def project(g): return clean(transform(to, g))
def layer(name): return project(unary_union([shape(f['geometry']) for f in read(root / ('data/'+name+'.geojson'))['features']]))
data = read(sys.argv[1])
features = data['features']
originals = [clean(shape(f['geometry'])) for f in features]
geoms = [project(shape(f['geometry'])) for f in features]
canon = [i for i, f in enumerate(features) if f['properties'].get('canon')]
byname = {f['properties']['name']: i for i, f in enumerate(features)}
land = layer('land').difference(layer('lakes'))
aztec = byname['Aztec Empire']
ming = byname['Land of Torch Trees (Ming)']
mexico = {f['properties']['name']: project(shape(f['geometry'])) for f in read(root / 'sources/natural-earth-mexico-states.geojson')['features']}
baja = unary_union([mexico[n] for n in ['Baja California', 'Baja California Sur']]).buffer(10000).intersection(land)
california_coast = project(Polygon([(-126,42.2),(-122,42.2),(-121,40),(-119.1,38),(-116.9,35.5),(-115.5,32.5),(-118,31.5),(-126,31.5)]))
occupied = unary_union([geoms[i] for i in canon if i != ming])
geoms[ming] = clean(geoms[ming].union(baja.union(california_coast).intersection(land).difference(occupied)))
west_states = ['Sonora','Chihuahua','Durango','Sinaloa','Nayarit','Jalisco','Colima','Michoacán','Guerrero','Oaxaca','Zacatecas','Aguascalientes','Guanajuato','México','Morelos']
western_mexico = unary_union([mexico[n] for n in west_states])
occupied = unary_union([geoms[i] for i in canon if i != aztec])
geoms[aztec] = clean(geoms[aztec].union(western_mexico.intersection(land).difference(occupied)))

# A morphological opening keeps broad unclaimed territory but removes narrow
# raster-tracing corridors. Nearest boundary sites split additions between
# adjacent realms instead of overlapping buffered territory polygons.
claimed = unary_union([geoms[i] for i in canon])
unclaimed = clean(land.difference(claimed))
interior = unclaimed.buffer(-35000).buffer(35000)
gaps = clean(unclaimed.difference(interior).intersection(claimed.buffer(45000)))
# Closing a corridor can isolate its wider middle. Fill these enclosed pockets
# as well, rather than leaving rounded unclaimed holes among adjoining realms.
closed = clean(claimed.union(gaps))
shells = unary_union([Polygon(p.exterior) for p in parts(closed)])
gaps = clean(gaps.union(shells.difference(claimed).intersection(land)))
# Massachusetts remains its explicitly requested modern outline; Maine stays
# separate. Do not move Florida's northern frontier during this repair.
admin = {f['properties']['name']: project(shape(f['geometry'])) for f in read(root / 'sources/natural-earth-admin1-states.geojson')['features'] if f['properties']['admin']=='United States of America'}
gaps = clean(gaps.difference(admin['Maine']).difference(admin['Massachusetts']))
sites, owners = [], []
seen = set()
for i in canon:
    if features[i]['properties']['name'] in ['Massachusetts','La Florida']: continue
    for p in parts(geoms[i]):
        for ring in [p.exterior, *p.interiors]:
            for distance in np.linspace(0, ring.length, max(2, int(ring.length / 7000)+1), endpoint=False):
                point = ring.interpolate(distance)
                key = (round(point.x,3), round(point.y,3))
                if key not in seen:
                    seen.add(key); sites.append(key); owners.append(i)
print('Partitioning gaps with',len(sites),'boundary sites',flush=True)
cells = voronoi_polygons(MultiPoint(sites), extend_to=land.envelope, ordered=True)
additions = {i: [] for i in canon}
for cell, owner in zip(cells.geoms, owners):
    if cell.intersects(gaps):
        piece = clean(cell.intersection(gaps))
        if not piece.is_empty: additions[owner].append(piece)
for i, pieces in additions.items():
    if pieces: geoms[i] = clean(unary_union([geoms[i], *pieces]))
claimed = unary_union([geoms[i] for i in canon])
for i in range(len(features)):
    if i not in canon: geoms[i] = clean(geoms[i].difference(claimed))

p = features[ming]['properties']
p['name'] = 'The Dragon Coast (Ming Empire)'
p['summary'] = 'Along the Dragon Coast, Ming ports and settlements command the Pacific shores of California and the long peninsula of Baja California. Ships, trade and imperial ambition bind these distant shores to the Middle Kingdom.'
for i in [ming, aztec]:
    features[i]['properties']['boundaryStatus'] = 'Expanded to user-directed borders on 2026-09-10'
result = []
# Reuse the original WGS84 edges: projecting long straight GeoJSON segments
# and then subdividing them can otherwise create tiny new water slivers.
land_ll = clean(unary_union([shape(f['geometry']) for f in read(root/'data/land.geojson')['features']]).difference(unary_union([shape(f['geometry']) for f in read(root/'data/lakes.geojson')['features']])))
occupied_ll = unary_union([originals[i] for i in canon])
final = list(originals)
for i in canon:
    candidate = clean(transform(back,geoms[i]))
    extra = clean(candidate.difference(occupied_ll, grid_size=1e-8))
    added = clean(extra.intersection(land_ll, grid_size=1e-8))
    final[i] = clean(originals[i].union(added))
    occupied_ll = clean(occupied_ll.union(added))
occupied_ll = clean(unary_union([final[i] for i in canon]))
for i in range(len(features)):
    if i not in canon: final[i] = clean(originals[i].difference(occupied_ll))
for f, g in zip(features, final):
    if g.is_empty: continue
    p = f['properties']
    if p.get('label') and not g.covers(Point(*p['label'])):
        point = max(parts(g), key=lambda x:x.area).representative_point()
        p['label'] = [point.x, point.y]
    f['geometry'] = mapping(g)
    result.append(f)
data['features'] = result
(root/'data/territories.geojson').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('Repaired',round(gaps.area/1e6),'square kilometres of narrow gaps; expanded Aztec and Dragon Coast territories.',flush=True)
