"""Place state labels inside their largest land component. Requires shapely, pyproj."""
import json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import transform, polylabel
from shapely import make_valid
from pyproj import Transformer

root=Path(__file__).resolve().parents[1]
path=root/'data/territories.geojson'
data=json.loads(path.read_text(encoding='utf-8'))
to=Transformer.from_crs(4326,'+proj=laea +lat_0=45 +lon_0=-100 +datum=WGS84',always_xy=True).transform
back=Transformer.from_crs('+proj=laea +lat_0=45 +lon_0=-100 +datum=WGS84',4326,always_xy=True).transform
def polygons(g):
    if g.geom_type=='Polygon':return [g]
    return [p for child in getattr(g,'geoms',[]) for p in polygons(child)]
count=0
for f in data['features']:
    p=f['properties']
    if not p.get('name') or p['name'].startswith('Provisional realm '):continue
    g=max(polygons(make_valid(transform(to,shape(f['geometry'])))),key=lambda g:g.area)
    center=transform(back,polylabel(g,tolerance=1500))
    assert shape(f['geometry']).covers(center)
    p['label']=[round(center.x,6),round(center.y,6)]
    p['labelMinZoom']=max(4 if p.get('canon') else 5,6 if g.area<10e9 else 5 if g.area<50e9 else 4)
    count+=1
path.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print(f'Placed {count} labels inside named territories; geometry unchanged.')
