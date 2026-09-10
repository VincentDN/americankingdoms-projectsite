"""Fill Florida's peninsula using local physical geography; preserve its northern border.
Run from any directory. Requires shapely>=2.1. No source downloads needed.
"""
import json
from pathlib import Path
from shapely.geometry import shape, mapping, Polygon, box
from shapely.ops import unary_union
from shapely import make_valid

root = Path(__file__).resolve().parents[1]
def read(path): return json.loads((root/path).read_text(encoding='utf-8'))
def parts(g):
    if g.geom_type == 'Polygon': return [g]
    return [p for child in getattr(g,'geoms',[]) for p in parts(child)]
def clean(g): return unary_union(parts(make_valid(g)))

data = read('data/territories.geojson')
florida = next(f for f in data['features'] if f['properties']['id']=='florida')
old = clean(shape(florida['geometry']))
modern = clean(shape(next(f for f in read('sources/natural-earth-admin1-states.geojson')['features'] if f['properties'].get('name')=='Florida')['geometry']))
land = clean(unary_union([shape(f['geometry']) for f in read('data/land.geojson')['features']]))
lakes = clean(unary_union([shape(f['geometry']) for f in read('data/lakes.geojson')['features']]))

# Extrude the existing outline southwards: the upper envelope is exactly
# the existing northern edge, not Florida's modern state boundary. Coastal
# extensions cannot cross it. Below 30N (south of the existing northern
# frontier), include the peninsula's eastward curve and the Keys beyond
# the old outline's longitude span.
shadows = [old, box(-88,24,-79,30)]
for polygon in parts(old):
    coords=list(polygon.exterior.coords)
    for a,b in zip(coords,coords[1:]):
        shadows.append(clean(Polygon([a,b,(b[0],24),(a[0],24),a])))
envelope=clean(unary_union(shadows))
north=old.boundary.intersection(envelope.boundary)
# The small coastal tolerance reconciles admin-1 and the atlas's physical
# base resolution. The actual fill ends at the atlas coastline, never the buffer.
target=clean(land.intersection(modern.buffer(.06)).intersection(envelope).difference(lakes))
new=clean(old.union(target))
added=clean(new.difference(old))
assert old.difference(new).area < 1e-10, 'Existing Florida must not be removed'
assert north.difference(new.boundary.buffer(1e-9)).length < 1e-7, 'Northern edge moved'
assert added.difference(land).area < 1e-9, 'Added fill extends into ocean'
assert added.intersection(lakes).area < 1e-9, 'Lake filled'
for f in data['features']:
    if f is florida: continue
    g=clean(shape(f['geometry']))
    if g.intersection(added).area>1e-12:
        remaining=clean(g.difference(added))
        assert not remaining.is_empty
        f['geometry']=mapping(remaining)
florida['geometry']=mapping(new)
florida['properties']['boundaryStatus']='Existing northern border preserved; peninsula and coastal land filled to Natural Earth coastline'
florida['properties']['source']='east-coast-canon.png (northern border); Natural Earth physical land and admin-1 (peninsula)'
assert new.is_valid
assert target.difference(new).area < 1e-10
(root/'data/territories.geojson').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print(f'Florida extended by {added.area:.6f} square degrees; northern boundary preserved ({north.length:.6f} degrees).')
