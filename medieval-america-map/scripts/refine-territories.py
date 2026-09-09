"""Close traced seams and replace raster fragments with inferred natural regions.
Run from repo root. Requires shapely>=2.1, pyproj, numpy, scipy.
Only Natural Earth's public-domain river data and hand-inferred mountain divides
are used; these are fictional provisional regions, not measured watersheds.
"""
import json, math
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from pyproj import Transformer
from shapely import make_valid,set_precision,coverage_simplify,coverage_is_valid
from shapely.geometry import shape,mapping,Polygon,LineString
from shapely.ops import unary_union,transform,polygonize,linemerge,nearest_points
ROOT=Path('medieval-america-map')
to=Transformer.from_crs(4326,'+proj=laea +lat_0=45 +lon_0=-100 +datum=WGS84 +units=m',always_xy=True).transform
back=Transformer.from_crs('+proj=laea +lat_0=45 +lon_0=-100 +datum=WGS84 +units=m',4326,always_xy=True).transform
def parts(g):
 if g.is_empty:return []
 if g.geom_type=='Polygon':return [g]
 if hasattr(g,'geoms'):return [p for x in g.geoms for p in parts(x)]
 return []
def clean(g):return unary_union(parts(make_valid(g)))
def project(g):return set_precision(clean(transform(to,g)),10)
def read(name):return json.loads((ROOT/name).read_text())
land=project(unary_union([shape(f['geometry']) for f in read('data/land.geojson')['features']]))
lakes=project(unary_union([shape(f['geometry']) for f in read('data/lakes.geojson')['features']]))
land=clean(land.difference(lakes))
fs=read('sources/canonical-territories.geojson')['features']
canon=[clean(project(shape(f['geometry'])).intersection(land)) for f in fs]
# Resolve any precision-grid overlaps, keeping the small coastal states intact.
occupied=Polygon()
for i in sorted(range(len(canon)),key=lambda i:canon[i].area):
 canon[i]=clean(canon[i].difference(occupied));occupied=unary_union([occupied,canon[i]])
original=unary_union(canon)
# Only narrow missing seams and thin coastal land remnants are repair targets.
closed=original.buffer(6000,quad_segs=3).buffer(-6000,quad_segs=3)
coastal=land.boundary.buffer(2000,quad_segs=2).intersection(original.buffer(6000,quad_segs=3))
target=set_precision(clean(unary_union([closed,coastal]).intersection(land).difference(original)),10)
remaining=target
order=sorted(range(len(canon)),key=lambda i:canon[i].area)
seeds=list(canon)
for distance in range(500,12500,500):
 for i in order:
  if remaining.is_empty:break
  take=clean(seeds[i].buffer(distance,quad_segs=2).intersection(remaining))
  if not take.is_empty:
   canon[i]=clean(unary_union([canon[i],take]));remaining=clean(remaining.difference(take))
 if remaining.is_empty or remaining.area<1:break
canonical=unary_union(canon)
print('Canonical seam/coast land repaired (km2):',round((canonical.area-original.area)/1e6),flush=True)
# Inferred mountain/ridge guides. Exact passes are intentionally not claimed.
guides={
 'Rocky Mountain / Sierra Madre divide':[(-179,70),(-151,65),(-139,61),(-130,57),(-121,53),(-116,49),(-113,46),(-110,43),(-107,40),(-106,36),(-108,32),(-107,28),(-104,24),(-101,21),(-97,17),(-92,12),(-89,5)],
 'Coast Mountains / Cascades / Sierra Nevada':[(-179,57),(-150,60),(-137,58),(-129,54),(-124,49),(-121.7,46),(-121.3,42),(-119.5,38),(-118.4,36),(-116.7,34),(-115.7,30),(-111.4,26),(-110,20),(-108,5)],
 'Appalachian divide':[(-55,75),(-66,54),(-70,48),(-73,45),(-75,42),(-78,40),(-81,37),(-84,35),(-86,33),(-87,25),(-87,5)],
 'Northern drainage divide':[(-179,72),(-145,68),(-132,64),(-120,60),(-108,59),(-100,57),(-91,51),(-80,48),(-65,52),(-40,56)],
 'Mexican volcanic belt':[(-130,19),(-109,20),(-105,21),(-101,19.5),(-97,19),(-93,17),(-88,18),(-75,20),(-40,22)],
 'Central American highlands':[(-130,12),(-96,13),(-91,15),(-87,14),(-85,12),(-82,10),(-79,9),(-70,8),(-40,8)],
}
# A full rectangular frame gives each provisional region one shared planar mesh.
frame=land.envelope.buffer(100000)
barriers=[frame.boundary,land.boundary]
named=[]
for name,coords in guides.items():
 from scipy.interpolate import CubicSpline
 raw=np.array(transform(to,LineString(coords)).coords)
 distances=np.r_[0,np.cumsum(np.linalg.norm(np.diff(raw,axis=0),axis=1))]
 sampled=CubicSpline(distances,raw,axis=0)(np.linspace(0,distances[-1],max(20,int(distances[-1]/60000))))
 line=LineString(sampled);barriers.append(line);named.append((name,line))
# Join tiny gaps between river/lake-centreline segments before finding the trunk.
river_features=read('sources/natural-earth-rivers.geojson')['features']
def river(name):
 lines=[]
 for f in river_features:
  if f['properties'].get('name')!=name:continue
  for line in shape(f['geometry']).geoms:
   if line.bounds[1]<7 or line.bounds[0]>-40:continue
   if line.length>.025:lines.append(transform(to,line))
 ends=np.array([p for l in lines for p in [l.coords[0],l.coords[-1]]]);tree=cKDTree(ends)
 parent=list(range(len(ends)))
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for a,b in tree.query_pairs(5000):parent[root(b)]=root(a)
 centers={r:ends[[root(i)==r for i in range(len(ends))]].mean(axis=0) for r in {root(i) for i in range(len(ends))}}
 fixed=[]
 for i,l in enumerate(lines):
  c=list(l.coords);c[0]=centers[root(2*i)];c[-1]=centers[root(2*i+1)];fixed.append(LineString(c))
 merged=unary_union(fixed)
 if merged.geom_type!='LineString':merged=linemerge(merged)
 candidates=[merged] if merged.geom_type=='LineString' else list(merged.geoms)
 return max(candidates,key=lambda l:l.length).simplify(1300,preserve_topology=True)
# Explicit headwater-to-divide and tributary-to-trunk joins make complete
# boundaries, rather than dangling lines ending at a lake or short of a river.
river_joins={
 'Mackenzie':((-114,61),'Northern drainage divide',None),
 'Nelson':((-97,51),'Northern drainage divide',None),
 'Mississippi':((-95,47),'Northern drainage divide',None),
 'Missouri':((-112,46),'Rocky Mountain / Sierra Madre divide','Mississippi river corridor'),
 'Ohio':((-80,40),'Appalachian divide','Mississippi river corridor'),
 'Arkansas':((-106,39),'Rocky Mountain / Sierra Madre divide','Mississippi river corridor'),
 'Rio Grande':((-107,38),'Rocky Mountain / Sierra Madre divide',None),
 'Columbia':((-116,50),'Rocky Mountain / Sierra Madre divide',None),
 'Colorado':((-106,40),'Rocky Mountain / Sierra Madre divide',None),
 'Yukon':((-135,62),'Rocky Mountain / Sierra Madre divide',None),
 'Fraser':((-118,52),'Rocky Mountain / Sierra Madre divide',None),
 'Saskatchewan':((-105,53),'Rocky Mountain / Sierra Madre divide','Nelson river corridor'),
}
for name,(hint,source_guide,mouth_guide) in river_joins.items():
 from shapely.geometry import Point
 line=river(name);endpoints=[Point(line.coords[0]),Point(line.coords[-1])]
 hint=transform(to,Point(hint));source=min(endpoints,key=lambda p:p.distance(hint));mouth=max(endpoints,key=lambda p:p.distance(hint))
 targets=dict(named)
 for point,target in [(source,targets[source_guide]),(mouth,targets[mouth_guide] if mouth_guide else land.boundary)]:
  dest=nearest_points(point,target)[1]
  if point.distance(dest)>1:barriers.append(LineString([point,dest]))
 barriers.append(line);named.append((name+' river corridor',line))

mesh=unary_union([set_precision(l,10) for l in barriers])
zones=list(polygonize(mesh))
interior=clean(land.difference(canonical))
regions=[]
for zone in zones:
 g=clean(zone.intersection(interior))
 if not g.is_empty:regions.append(g)
# Partition all islands too; mesh exterior remnants become their own provisional zone.
missing=clean(interior.difference(unary_union(regions)))
if not missing.is_empty:regions.append(missing)
# Merge little leftovers into their closest substantial neighbour rather than
# publishing separate speck-sized states. Shared boundaries remain identical.
large=[g for g in regions if g.area>12000e6]
small=[g for g in regions if g.area<=12000e6]
for g in sorted(small,key=lambda g:g.area,reverse=True):
 i=min(range(len(large)),key=lambda i:(g.distance(large[i]),-g.boundary.intersection(large[i].boundary).length))
 large[i]=clean(unary_union([large[i],g]))
regions=large
# Same simplification operation on the entire coverage preserves common edges.
all_shapes=[set_precision(g,10) for g in canon+regions]
# Node the full coverage once so even rounding-sized seams have a single owner.
from shapely.strtree import STRtree
owners=STRtree(all_shapes)
faces=polygonize(unary_union([land.boundary]+[g.boundary for g in all_shapes]))
buckets=[[] for g in all_shapes]
for face in faces:
 point=face.representative_point()
 if not land.covers(point):continue
 hits=owners.query(point,predicate='within')
 owner=int(min(hits)) if len(hits) else int(owners.nearest(point))
 buckets[owner].append(face)
all_shapes=[unary_union(bucket) for bucket in buckets]
assert coverage_is_valid(all_shapes), 'Mesh must be a valid shared-edge coverage'
all_shapes=list(coverage_simplify(all_shapes,250,simplify_boundary=False))
canon=all_shapes[:len(fs)];regions=all_shapes[len(fs):]
for f,g in zip(fs,canon):
 f['geometry']=mapping(transform(back,g));f['properties']['boundaryStatus']='Canonical reference; narrow seams repaired and coast aligned'
palette=['#b58a45','#768757','#a9654b','#708984','#b6a25e','#8a7898','#648878','#bd8b68','#879eac','#a87576','#9c995e','#617a96']
# Greedy neighbour-aware colouring avoids identical fills on shared borders.
assigned=[]
for i,g in enumerate(sorted(regions,key=lambda g:g.representative_point().y,reverse=True)):
 neighbours={color for old,color in assigned if g.distance(old)<100}
 choices=[c for c in palette if c not in neighbours] or palette
 color=choices[i%len(choices)];assigned.append((g,color))
 nearest=sorted(named,key=lambda n:g.representative_point().distance(n[1]))[:2]
 basis=' and '.join(n[0] for n in nearest)
 fs.append({'type':'Feature','properties':{'id':f'provisional-realm-{i+1:02d}','name':f'Provisional realm {i+1:02d}','kind':'region','color':color,'canon':False,'claim':'','wiki':'','summary':f'Provisional boundary informed by {basis}. Name, lord and lore to be added.','source':'Natural Earth rivers plus inferred mountain divides','boundaryStatus':'Fictional geographic inference, not a surveyed watershed'},'geometry':mapping(transform(back,g))})
(ROOT/'data/territories.geojson').write_text(json.dumps({'type':'FeatureCollection','features':fs},separators=(',',':')))
(ROOT/'sources/inferred-divides.geojson').write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'name':name,'status':'inferred guide'},'geometry':mapping(LineString(coords))} for name,coords in guides.items()]},separators=(',',':')))
print('Canonical states:',len(canon),'Provisional regions:',len(regions),flush=True)
# Verify there is no unassigned land, overlap, or lake coverage in metric space.
from shapely.strtree import STRtree
# Validate in floating precision; re-snapping simplified vertices would create artificial gaps.
land=set_precision(land,0);lakes=set_precision(lakes,0)
geoms=[transform(to,shape(f['geometry'])) for f in fs]
assert all(g.is_valid and not g.is_empty for g in geoms)
covered=unary_union(geoms)
assert land.difference(covered).area<10,land.difference(covered).area
assert covered.difference(land).area<10
assert covered.intersection(lakes).area<10
index=STRtree(geoms)
for i,g in enumerate(geoms):
 for j in index.query(g,predicate='intersects'):
  if j>i:assert g.intersection(geoms[j]).area<10,(i,j)
print('PASS: complete land coverage, shared borders, no overlaps, clear lakes',flush=True)
