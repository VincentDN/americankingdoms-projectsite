"""Dissolve sub-metre overlay seams after repair-territory-borders.py.
Run with no arguments. Requires Shapely. Coastlines and lake cutouts are reapplied.
"""
import json
from pathlib import Path
from shapely import make_valid, set_precision
from shapely.geometry import shape, mapping, Polygon, Point
from shapely.ops import unary_union
root = Path(__file__).resolve().parents[1]
read = lambda name: json.loads((root/'data'/name).read_text(encoding='utf-8'))
def parts(g):
    if g.geom_type == 'Polygon': return [g]
    return [p for c in getattr(g,'geoms',[]) for p in parts(c)]
def clean(g): return unary_union(parts(make_valid(g)))
data = read('territories.geojson')
land = clean(unary_union([shape(f['geometry']) for f in read('land.geojson')['features']]).difference(unary_union([shape(f['geometry']) for f in read('lakes.geojson')['features']])))
features = data['features']
protected = ['Massachusetts', 'La Florida']
canon = sorted([f for f in features if f['properties'].get('canon')], key=lambda f: f['properties']['name'] not in protected)
occupied = Polygon()
for f in canon:
    print('Normalize:',f['properties']['name'],flush=True)
    g = clean(shape(f['geometry']))
    if f['properties']['name'] not in protected:
        # The overlay leaves extremely narrow interior rings that still receive
        # a full-width SVG stroke. Close those numerical seams before rendering.
        g = set_precision(g, 0.00001)
        g = clean(unary_union([Polygon(p.exterior,[r for r in p.interiors if Polygon(r).area>0.0001]) for p in parts(g)]))
        g = clean(g.intersection(land).difference(occupied))
    f['geometry'] = mapping(g)
    occupied = clean(occupied.union(g))
for f in features:
    if not f['properties'].get('canon'):
        f['geometry'] = mapping(clean(shape(f['geometry']).difference(occupied)))
data['features'] = [f for f in features if not shape(f['geometry']).is_empty]
for f in data['features']:
    p = f['properties']; g = shape(f['geometry'])
    if p.get('label') and not g.covers(Point(*p['label'])):
        point = max(parts(g),key=lambda x:x.area).representative_point()
        p['label'] = [point.x,point.y]
(root/'data/territories.geojson').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('Dissolved numerical seams; reapplied land, lakes and provisional coverage.',flush=True)
