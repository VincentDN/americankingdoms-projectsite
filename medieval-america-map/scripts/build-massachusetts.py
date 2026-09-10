"""Rebuild Massachusetts county data and borders. Requires shapely>=2.1 and pyproj."""
import json
import sys
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely.ops import unary_union, transform
from shapely import make_valid, coverage_simplify
from pyproj import Transformer

root = Path(__file__).resolve().parents[2]
atlas = root / 'medieval-america-map'
source = json.loads((atlas / 'sources/census-ma-counties-2024.geojson').read_text(encoding='utf-8'))
assert len(source['features']) == 14
to = Transformer.from_crs(4326, 26986, always_xy=True).transform
back = Transformer.from_crs(26986, 4326, always_xy=True).transform
def parts(g):
    if g.geom_type == 'Polygon': return [g]
    return [p for child in getattr(g, 'geoms', []) for p in parts(child)]
def clean(g): return unary_union(parts(make_valid(g)))
regions = {
    'Western Massachusetts': ['Berkshire','Franklin','Hampshire','Hampden'],
    'Central Massachusetts': ['Worcester'],
    'Greater Boston and the North Shore': ['Essex','Middlesex','Suffolk','Norfolk'],
    'Southeastern Massachusetts': ['Bristol','Plymouth'],
    'Cape Cod and the Islands': ['Barnstable','Dukes','Nantucket'],
}
palette = ['#7b4687','#b28b3f','#377e91','#659697','#777d9c','#57947e','#37657d','#a57667','#638449','#92816d','#a44f43','#855788','#ab8139','#758d91']
counties = sorted(source['features'], key=lambda f: f['properties']['BASENAME'])
shapes = [clean(transform(to, shape(f['geometry']))) for f in counties]
# Shared edges are simplified together; retain small offshore islands.
shapes = list(coverage_simplify(shapes, 65))
features = []
for f,g,color in zip(counties,shapes,palette):
    name = f['properties']['BASENAME']
    p = transform(back, max(parts(g), key=lambda x:x.area).representative_point())
    features.append({'type':'Feature','properties':{'id':f['properties']['GEOID'],'name':name,'region':next(r for r,names in regions.items() if name in names),'color':color,'label':[p.x,p.y]},'geometry':mapping(transform(back,g))})
out = atlas / 'data/submaps'
out.mkdir(parents=True,exist_ok=True)
submap = {'type':'FeatureCollection','source':'U.S. Census Bureau, Generalized ACS 2024 counties, 1:500,000; simplified together at 65 metres. Modern geographic reference, not canonical duchies.','features':features}
(out/'massachusetts.geojson').write_text(json.dumps(submap,separators=(',',':')),encoding='utf-8')
territory_path = atlas / 'data/territories.geojson'
t = json.loads(territory_path.read_text(encoding='utf-8'))
ma = next(f for f in t['features'] if f['properties']['id']=='massachusetts')
old = clean(shape(ma['geometry']))
# The user requested modern Massachusetts only. Retain the former northern
# territory as provisional Maine rather than leaving unassigned land.
north = unary_union([g for g in parts(old) if g.bounds[1] > 43.5])
south = transform(back,unary_union(shapes).simplify(180,preserve_topology=True))
new = clean(south)
if old.equals(new) and ma['properties'].get('submap') == 'massachusetts':
    print('County data regenerated; world outline already current. No border rewrite needed.')
    sys.exit(0)
freed = clean(old.difference(unary_union([new,north])))
if not north.is_empty:
    t['features'].append({'type':'Feature','properties':{'id':'placeholder-me','name':'Maine','kind':'region','color':'#879eac','canon':False,'claim':'','wiki':'','summary':'Provisional territory. Name, lord and lore to be added.','source':'Former northern Massachusetts claim from east-coast-canon.png','boundaryStatus':'Separated from Massachusetts; provisional borders pending lore'},'geometry':mapping(north)})
neighbours = [f for f in t['features'] if f['properties']['name'] in ['New Hampshire','New York','Connecticut','Rhode Island']]
admin = json.loads((atlas/'sources/natural-earth-admin1-states.geojson').read_text(encoding='utf-8'))
# Reassign the vacated border strips using adjacent state geography first.
for f in neighbours:
    ref = next(x for x in admin['features'] if x['properties'].get('name') == f['properties']['name'] and x['properties'].get('adm0_a3')=='USA')
    added = clean(freed.intersection(shape(ref['geometry'])))
    f['geometry'] = mapping(clean(clean(shape(f['geometry'])).union(added).difference(new)))
    freed = clean(freed.difference(added))
# Keep remaining land coverage at the existing coarse coastline. No new
# fictional territories: attach residual seam fragments to an adjacent realm.
land = unary_union([shape(f['geometry']) for f in json.loads((atlas/'data/land.geojson').read_text(encoding='utf-8'))['features']])
for piece in parts(clean(freed.intersection(land))):
    f = max(neighbours,key=lambda x:piece.boundary.intersection(shape(x['geometry']).boundary).length)
    f['geometry'] = mapping(clean(shape(f['geometry']).union(piece).difference(new)))
for f in t['features']:
    if f is ma: continue
    g=clean(shape(f['geometry']))
    if g.intersection(new).area > 1e-10: f['geometry']=mapping(clean(g.difference(new)))
ma['geometry']=mapping(new)
ma['properties']['submap']='massachusetts'
ma['properties']['boundaryStatus']='Modern Massachusetts outline from Census ACS 2024 counties; Maine is a separate provisional territory'
ma['properties']['source']='Census ACS 2024 counties'
# Repaired source rings may expose tiny seams with provisional neighbours.
# Resolve them against the rest of the existing map before publishing.
for f in neighbours:
    g=clean(shape(f['geometry']))
    others=[clean(shape(x['geometry'])) for x in t['features'] if x is not f and g.intersects(clean(shape(x['geometry'])))]
    f['geometry']=mapping(clean(g.difference(unary_union(others))))
assert new.is_valid
assert all(shape(f['geometry']).is_valid for f in neighbours)
assert all(new.intersection(clean(shape(f['geometry']))).area < 1e-8 for f in t['features'] if f is not ma)
territory_path.write_text(json.dumps(t,separators=(',',':')),encoding='utf-8')
print('Generated 14 counties; modern Massachusetts outline; Maine separate; no overlaps with Massachusetts.')
print('County payload:', (out/'massachusetts.geojson').stat().st_size, 'bytes')

