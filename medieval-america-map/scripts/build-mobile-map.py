"""Build the phone atlas: shared-edge simplification, no cities or rivers.
Requires Shapely >= 2.1. Run after editing the full-resolution data.
"""
import json, gzip
from pathlib import Path
from shapely import make_valid, set_precision, coverage_is_valid, coverage_simplify
from shapely.geometry import shape, mapping, Polygon
from shapely.ops import unary_union, polygonize
from shapely.strtree import STRtree
root=Path(__file__).resolve().parents[1]
def read(name): return json.loads((root/'data'/f'{name}.geojson').read_text(encoding='utf-8'))
def parts(g):
    if g.geom_type=='Polygon': return [g]
    return [p for c in getattr(g,'geoms',[]) for p in parts(c)]
def clean(g): return unary_union(parts(make_valid(g)))
def rounded(value):
    if isinstance(value,float): return round(value,5)
    if isinstance(value,(list,tuple)): return [rounded(v) for v in value]
    if isinstance(value,dict): return {k:rounded(v) for k,v in value.items()}
    return value
def fc(features): return {'type':'FeatureCollection','features':features}
full=read('territories')
geoms=[]
for f in full['features']:
    polygons=parts(clean(shape(f['geometry'])))
    largest=max(polygons,key=lambda p:p.area)
    # Preserve each canonical realm even when it is an island or tiny city-state.
    kept=[p for p in polygons if p.area>=0.008 or (p==largest and (f['properties'].get('canon') or p.area>=0.001))]
    g=unary_union([Polygon(p.exterior,[r for r in p.interiors if Polygon(r).area>=0.004]) for p in kept])
    geoms.append(set_precision(g,0.00001))
tree=STRtree(geoms)
print('Building shared-edge coverage',flush=True)
faces=list(polygonize(unary_union([g.boundary for g in geoms])))
owned=[[] for g in geoms]
for face in faces:
    point=face.representative_point()
    candidates=[i for i in tree.query(point) if geoms[i].covers(point)]
    if candidates:
        owner=max(candidates,key=lambda i:bool(full['features'][i]['properties'].get('canon')))
        owned[owner].append(face)
coverage=[unary_union(faces) if faces else Polygon() for faces in owned]
assert coverage_is_valid(coverage), 'Territory edges must match before simplification'
simple=coverage_simplify(coverage,0.1)
assert coverage_is_valid(simple), 'Simplified borders must remain non-overlapping'
keep={'id','name','kind','canon','color','placeholderColor','flag','shield','wiki','summary','claim','label','labelMinZoom','alliance','submap'}
features=[]
for original,g in zip(full['features'],simple):
    g=set_precision(g,0.00001)
    if g.is_empty: continue
    assert g.is_valid
    properties={k:v for k,v in original['properties'].items() if k in keep}
    features.append({'type':'Feature','properties':properties,'geometry':mapping(g)})
assert {f['properties']['id'] for f in full['features'] if f['properties'].get('canon')} <= {f['properties']['id'] for f in features}
bundle={'territories':fc(features)}
for name in ['land','lakes']:
    # Broad coastlines and major lakes only; fine coastal detail stays on desktop.
    geometries=[]
    for f in read(name)['features']:
        for p in parts(clean(shape(f['geometry']))):
            if p.area>=0.025:
                g=p.simplify(0.04,preserve_topology=True)
                geometries.append({'type':'Feature','properties':{},'geometry':mapping(g)})
    bundle[name]=fc(geometries)
bundle=rounded(bundle)
for collection in bundle.values():
    for f in collection['features']:
        g=shape(f['geometry'])
        if not g.is_valid: f['geometry']=mapping(clean(g))
        assert shape(f['geometry']).is_valid
raw=json.dumps(bundle,separators=(',',':')).encode()
print({k:len(json.dumps(rounded(v),separators=(',',':'))) for k,v in bundle.items()},flush=True)
assert len(raw)<900000, f'Mobile data budget exceeded: {len(raw)} bytes'
out=root/'data/mobile';out.mkdir(exist_ok=True)
(out/'atlas.json').write_bytes(raw)
source_bytes=sum((root/'data'/f'{n}.geojson').stat().st_size for n in ['land','lakes','rivers','territories','cities','samples'])
stats={'fullDataBytes':source_bytes,'mobileDataBytes':len(raw),'mobileGzipBytes':len(gzip.compress(raw)),'reductionPercent':round(100*(1-len(raw)/source_bytes),1),'territories':len(features),'canonicalTerritories':sum(bool(f['properties'].get('canon')) for f in features)}
(out/'build-stats.json').write_text(json.dumps(stats,indent=2)+'\n',encoding='utf-8')
print(json.dumps(stats),flush=True)
