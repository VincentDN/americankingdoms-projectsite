"""Extract editable polygons from Vincent's two rough maps.
Requires Pillow, numpy, scipy, matplotlib, shapely, pyproj.
Run from repo root with the Natural Earth admin-0 GeoJSON path as argv[1].
The control points are approximate georeferencing, not surveyed borders.
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
from scipy.interpolate import RBFInterpolator
from shapely.geometry import Polygon, MultiPolygon, shape, mapping, box
from shapely.ops import unary_union, transform
from shapely import make_valid
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pyproj import Transformer
ROOT=Path('ak-map-alpha')
merc=Transformer.from_crs(4326,3857,always_xy=True)
back=Transformer.from_crs(3857,4326,always_xy=True)
def warp(points):
 p=np.array(points); xy=np.array(merc.transform(p[:,2],p[:,3])).T/100000
 f=RBFInterpolator(p[:,:2],xy,kernel='thin_plate_spline',smoothing=2)
 def fn(x,y,z=None):
  v=f(np.column_stack([x,y]))*100000
  return back.transform(v[:,0],v[:,1])
 return fn
# Pixel landmarks paired with geographic river/coast/state-border landmarks.
east_warp=warp([
 [680,249,-80.52,39.72],[756,245,-75.79,39.72],
 [754,327,-75.87,36.55],[592,330,-83.68,36.55],
 [695,392,-78.54,33.85],[651,442,-81.1,32.1],
 [636,470,-81.45,30.7],[610,530,-82.65,27.9],
 [653,577,-80.4,25.15],[490,476,-87.63,30.25],
 [877,198,-69.95,41.7],[845,212,-71.85,41.05],
 [940,117,-67.05,44.65],[867,84,-69.22,47.45],
 [801,184,-73.5,42.05],[804,110,-73.35,45],
 [734,186,-79.76,42.27],[713,194,-80.52,41.99],
 [1210,16,-55.6,51.5],[982,135,-66.1,44.4],
 [998,3,-66.9,49.9],[723,111,-77.1,44.1],
])
wide_warp=warp([
 [306,540,-80.1,25.1],[56,558,-109.9,22.9],[19,431,-117.2,32.5],
 [8,389,-122.4,37.8],[62,265,-122.3,47.6],[219,602,-86.8,21.5],
 [240,638,-90.6,14],[324,707,-79.5,9],[265,490,-89.4,29],
 [185,532,-97.2,26],[385,305,-80,51],[499,306,-68,48.5],
 [574,316,-53,47],[424,388,-67,45],[375,431,-74,40.7],
 [368,461,-75.5,35.3],[655,140,-45,70],[18,163,-166,64],
 [173,114,-141,70],[89,208,-130,55],[300,53,-100,78],
 [250,284,-106,52],[235,385,-102,40],[151,573,-99.1,19.4],
 [256,615,-84,19],[412,594,-69.9,18.5],[361,568,-77.3,20],
])
def polygons(g):
 g=make_valid(g)
 if g.geom_type=='Polygon':return [g]
 if hasattr(g,'geoms'):return [p for x in g.geoms for p in polygons(x)]
 return []
def clean(g):
 parts=polygons(g)
 return unary_union(parts) if parts else Polygon()
def contours(mask,fn,min_pixels):
 labs,n=ndimage.label(mask)
 result=[]
 objects=ndimage.find_objects(labs)
 for idx,slices in enumerate(objects,1):
  if slices is None or np.count_nonzero(labs[slices]==idx)<min_pixels:continue
  binary=np.pad(labs[slices]==idx,1)
  fig,ax=plt.subplots(); cs=ax.contour(binary.astype(float),levels=[.5])
  for seg in cs.allsegs[0]:
   if len(seg)<4:continue
   seg[:,0]+=slices[1].start-1;seg[:,1]+=slices[0].start-1
   p=Polygon(seg).simplify(.6,preserve_topology=True)
   if p.area<min_pixels:continue
   result.extend(polygons(transform(fn,p)))
  plt.close(fig)
 return clean(unary_union(result))
admin=json.loads(Path(sys.argv[1]).read_text())
na=clean(unary_union([shape(f['geometry']) for f in admin['features'] if f['properties'].get('CONTINENT')=='North America']))
na=clean(na.intersection(box(-179,7,-40,83)))
# Physically remove South America from all displayed background layers.
for name in ['land','lakes','rivers']:
 p=ROOT/'data'/f'{name}.geojson';source=ROOT/'sources'/f'natural-earth-{name}.geojson'
 if not source.exists():source.write_bytes(p.read_bytes())
 data=json.loads(source.read_text());out=[]
 for f in data['features']:
  g=make_valid(shape(f['geometry'])).intersection(na if name=='land' else na.buffer(.025))
  if g.is_empty:continue
  if name!='rivers':g=clean(g)
  if not g.is_empty:out.append({'type':'Feature','properties':{},'geometry':mapping(g)})
 p.write_text(json.dumps({'type':'FeatureCollection','features':out},separators=(',',':')))
land=clean(unary_union([shape(f['geometry']) for f in json.loads((ROOT/'data/land.geojson').read_text())['features']]))
lakes=unary_union([shape(f['geometry']) for f in json.loads((ROOT/'data/lakes.geojson').read_text())['features']])
land=clean(land.difference(lakes))
features=[]
def feature(name,color,g,canon,claim=''):
 g=clean(g.intersection(land))
 if g.is_empty:return
 properties={'id':name.lower().replace(' ','-'),'name':name,'kind':'country' if canon else 'region','color':color,'summary':('Lord / claim: '+claim+'.' if canon else 'Name, lord and lore to be added.'),'wiki':'','canon':canon,'claim':claim,'source':'east-coast-canon.png' if canon else 'continental-outline.jpg','boundaryStatus':'Approximate trace of supplied reference'}
 features.append({'type':'Feature','properties':properties,'geometry':mapping(g)})
im=np.array(Image.open(ROOT/'sources/east-coast-canon.png').convert('RGB'))
names=['English Canada','Massachusetts','New Hampshire','Connecticut','Rhode Island','New York','Pennsylvania','New Jersey','Delaware','Maryland','Virginia','North Carolina','South Carolina','Georgia','Smokey March','Florida']
coords=[(868,y) for y in [280,308,336,364,392,421,449,477]]+[(1148,y) for y in [280,308,336,364,392,421,449,498]]
colors=np.array([im[y,x] for x,y in coords])
palette=np.vstack([colors,[[217,187,149],[189,149,98],[57,35,18]]]).astype(float)
labels=np.argmin(np.sum((im[:,:,None,:].astype(float)-palette)**2,axis=3),axis=2)
y,x=np.indices(labels.shape);valid=((x<840)|(y<230))&(y<548)
claims={'Maryland':'KaiserBadger','Georgia':'Stifo','Smokey March':'DanteTHYPRODICAL SON','Florida':'KaiserBismark'}
for i,name in enumerate(names):
 mask=(labels==i)&valid
 mask=ndimage.binary_fill_holes(mask)
 g=contours(mask,east_warp,6 if name=='Rhode Island' else 12)
 color='#'+''.join(f'{int(c):02x}' for c in colors[i])
 feature(name,color,g,True,claims.get(name,'Unclaimed'))
# Resolve subpixel tracing overlaps, preserving the smallest states first.
occupied=Polygon()
for f in sorted(features,key=lambda f:shape(f['geometry']).area):
 g=clean(shape(f['geometry']).difference(occupied))
 f['geometry']=mapping(g);occupied=unary_union([occupied,g])
canon=occupied
wide=Image.open(ROOT/'sources/continental-outline.jpg').convert('RGB').crop((0,0,610,723)).filter(ImageFilter.MedianFilter(3))
quant=wide.quantize(colors=40);labs=np.array(quant);pal=np.array(quant.getpalette()).reshape(-1,3)
for i,col in enumerate(pal[:40]):
 # Exclude water, dark labels, white ice and the bright magenta framing line.
 if np.linalg.norm(col.astype(float)-[153,204,255])<62 or col.max()<85 or col.min()>220 or (col[0]>205 and col[2]>205 and col[1]<50):continue
 mask=ndimage.binary_fill_holes(labs==i)
 g=contours(mask,wide_warp,55)
 g=clean(g.intersection(land).difference(canon))
 for part in polygons(g):
  if part.area<.07:continue
  n=sum(not f['properties']['canon'] for f in features)+1
  # Muted inks retain the reference's distinct colour families on parchment.
  muted=np.round(.75*col+.25*np.array([173,146,102])).astype(int)
  feature(f'Uncharted realm {n:02d}','#'+''.join(f'{c:02x}' for c in muted),part,False)
# Make provisional territories a non-overlapping partition as well.
occupied=canon
for f in sorted([f for f in features if not f['properties']['canon']],key=lambda f:shape(f['geometry']).area):
 g=clean(shape(f['geometry']).difference(occupied))
 f['geometry']=mapping(g);occupied=unary_union([occupied,g])
features=[f for f in features if not shape(f['geometry']).is_empty]
# Keep all remaining land interactive, including portions outside the rough crop.
covered=unary_union([shape(f['geometry']) for f in features])
remaining=clean(land.difference(covered))
feature('Uncharted lands','#a59670',remaining,False)
(ROOT/'data/territories.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},separators=(',',':')))
print('Canonical states:',[(f['properties']['name'],round(shape(f['geometry']).area,2)) for f in features if f['properties']['canon']])
print('Provisional territories:',sum(not f['properties']['canon'] for f in features))
