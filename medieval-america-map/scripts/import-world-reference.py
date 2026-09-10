"""Import colored factions from the supplied 1420 reference, preserving existing canon.
Usage: python import-world-reference.py PATH_TO_PRE_IMPORT_DATA_DIRECTORY
Dependencies: Pillow, numpy, scipy, shapely>=2.1, pyproj.
Raster borders are approximate; inspect the output before committing.
"""
import json,sys,re
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
from scipy import ndimage
from scipy.interpolate import RBFInterpolator
from shapely.geometry import shape,mapping,box,Polygon
from shapely.ops import unary_union,transform,polylabel
from shapely import make_valid
from pyproj import Transformer
root=Path(__file__).resolve().parents[1]
baseline=Path(sys.argv[1])
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def parts(g):
    if g.geom_type=='Polygon':return [g]
    return [p for child in getattr(g,'geoms',[]) for p in parts(child)]
def clean(g):return unary_union(parts(make_valid(g)))
def lines(g):
    if g.geom_type=='LineString':return [g]
    return [p for child in getattr(g,'geoms',[]) for p in lines(child)]
def fc(gs):return {'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':mapping(g)} for g in gs if not g.is_empty]}
def write(name,d):(root/'data'/f'{name}.geojson').write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
to=Transformer.from_crs(4326,3857,always_xy=True).transform
back=Transformer.from_crs(3857,4326,always_xy=True).transform
# Coastline and lake landmarks on the supplied 1080px image, paired with WGS84.
controls=[
 [697,558,-80.5,25.15],[681,496,-81.45,30.7],[587,509,-89.4,29],
 [545,570,-97.2,26],[367,587,-109.9,22.9],[253,402,-117.15,32.53],
 [214,344,-122.42,37.77],[200,285,-124.4,42],[182,235,-123.1,48.5],
 [159,214,-127.5,50.5],[505,594,-99.1,19.4],[628,607,-86.8,21.5],
 [591,702,-88.1,15.8],[653,723,-83.65,10.95],[732,777,-77.4,8.6],
 [707,750,-79.5,9],[887,733,-71.6,12.4],[936,760,-62.0,10.5],
 [712,894,-80.75,-0.9],[701,874,-79.8,1.8],[857,648,-67.2,18.4],
 [806,640,-69.9,18.5],[752,616,-74.1,20],[666,595,-82.4,23.1],
 [743,333,-79.76,42.27],[805,322,-74,40.7],[870,278,-67,45],
 [985,229,-53,47],[966,191,-55.7,51.5],[748,263,-69.7,47.3],
 [711,218,-80,51],[556,235,-92,46.8],[578,282,-87.6,46.7],
 [639,315,-87,41.8],[545,159,-97,58.8],[727,0,-78,72],
 [422,0,-110,72],[341,93,-116,60],[1070,12,-42,70],
 # Inland anchors constrain the stylized image where coastal-only warping
 # otherwise drifts east. These locate recognizable named regions, not
 # modern state borders, and are deliberately recorded as approximations.
 [348,342,-111.6,38.5],[500,313,-100,45],[501,423,-98,35.7],
 [435,450,-105,33.4],[516,518,-97.3,28.5],[690,349,-82,41],
 [595,375,-89.1,40.5],[418,244,-107,46],[340,225,-112.5,48.5],
]
c=np.array(controls);xy=np.array(to(c[:,2],c[:,3])).T/100000
rbf=RBFInterpolator(c[:,:2],xy,kernel='thin_plate_spline',smoothing=1)
def warp(x,y,z=None):
    out=rbf(np.column_stack([x,y]))*100000
    return back(out[:,0],out[:,1])

# Extend the physical layers only into the northern South America window.
extension=box(-83,-5,-58,13)
old_land=clean(unary_union([shape(f['geometry']) for f in read(baseline/'land.geojson')['features']]))
raw_land=clean(unary_union([shape(f['geometry']) for f in read(root/'sources/natural-earth-land.geojson')['features']]))
new_land=clean(old_land.union(raw_land.intersection(extension)))
write('land',fc([new_land]))
for name in ['lakes','rivers']:
    old=[make_valid(shape(f['geometry'])) for f in read(baseline/f'{name}.geojson')['features']]
    extra=[make_valid(shape(f['geometry'])).intersection(extension).difference(old_land.buffer(.025)) for f in read(root/f'sources/natural-earth-{name}.geojson')['features']]
    merged=unary_union(old+extra)
    if name=='lakes':merged=clean(merged)
    else:merged=unary_union(lines(merged))
    write(name,fc([merged]))
print('Physical land, lakes and rivers extended.',flush=True)
lakes=clean(unary_union([shape(f['geometry']) for f in read(root/'data/lakes.geojson')['features']]))
land=clean(new_land.difference(lakes))

left=['Roman Colonies','Pagan Norse Holdouts','England','Kalmar Union','13 Kingdoms','Muslim Settlements','Mali Empire','Louisiana Territory','La Florida','Calusa Kingdom (Occupied)','Corsair Territories (La Florida)','Iberian Merchant Republics','Aztec Empire','Mayan Civilizations','Land of Torch Trees (Ming)','Muromachi Japan','Ming & Polynesian Hawaii','Illinois Confederation','Oceti Sakowin','Shawnee','Teutonic Ohio','Vargas Freehold']
right=['Aotearoan Settlements (Polynesian)','Utah Templars','Cherokee','Yuchi','Coushatta','Chickasaw','Choctaw','Caddo','Kitsai','Apache','Wichita','Cree Territories','Blackfeet','Crow','Shoshone','Leon and Castille','Al Andalus','Portugal','Scotland','Texas','Cow Nation']
ys=[667,683,699,716,732,749,765,781,797,813,830,846,862,879,895,911,928,944,960,976,992,1009]
names=left+right
regions={
 'Roman Colonies':[(799,679,968,792),(895,448,924,482)],
 'Pagan Norse Holdouts':[(544,210,772,364)],'Kalmar Union':[(493,0,1080,295)],
 'Muslim Settlements':[(810,630,939,753)],'Louisiana Territory':[(522,451,623,529)],
 'Corsair Territories (La Florida)':[(695,533,801,641)],'Iberian Merchant Republics':[(643,575,781,634)],
 'Aztec Empire':[(415,498,549,697)],'Mayan Civilizations':[(540,598,641,708)],
 'Land of Torch Trees (Ming)':[(193,277,377,599)],'Illinois Confederation':[(563,320,635,432)],
 'Oceti Sakowin':[(462,246,553,379)],'Shawnee':[(623,331,779,429)],'Teutonic Ohio':[(666,334,715,376)],
 'Vargas Freehold':[(480,34,582,137)],
 'Aotearoan Settlements (Polynesian)':[(140,187,219,257),(688,866,735,915),(695,740,746,772)],
 'Utah Templars':[(311,317,382,368)],'Cherokee':[(610,400,693,479)],'Yuchi':[(604,396,687,452)],
 'Coushatta':[(599,419,653,470)],'Chickasaw':[(574,417,629,479)],'Choctaw':[(590,446,665,500)],
 'Caddo':[(486,426,571,500)],'Kitsai':[(461,435,524,492)],'Apache':[(383,406,490,513)],
 'Wichita':[(460,397,551,448)],'Cree Territories':[(275,0,749,297)],'Blackfeet':[(282,179,388,280)],
 'Crow':[(356,177,477,306)],'Shoshone':[(273,187,417,352)],'Texas':[(474,480,550,558)],
 'Cow Nation':[(594,445,679,502)],
}
im=Image.open(root/'sources/world-factions-1420-reference.jpg').convert('RGB')
rgb=np.array(im.filter(ImageFilter.MedianFilter(3))).astype(float)
palette=np.array([np.median(np.array(im)[y-2:y+3,x-2:x+3].reshape(-1,3),axis=0) for x,y in [(62,y) for y in ys]+[(232,y) for y in ys[:-1]]])
# Use clean interior samples where a tiny JPEG legend swatch is contaminated.
samples={'Oceti Sakowin':(504,310),'Illinois Confederation':(592,371),'Utah Templars':(345,343),'Land of Torch Trees (Ming)':(268,449),'Muslim Settlements':(868,649),'Roman Colonies':(903,749)}
for name,(x,y) in samples.items():
    if name in names:palette[names.index(name)]=np.median(rgb[y-1:y+2,x-1:x+2].reshape(-1,3),axis=0)
background=np.array([[188,149,98],[217,187,149],[0,0,0],[255,255,255]])
allcolors=np.vstack([palette,background])
best=np.full(rgb.shape[:2],1e9);labels=np.zeros(rgb.shape[:2],dtype=np.int16)
for i,color in enumerate(allcolors):
    distance=((rgb-color)**2).sum(axis=2);pick=distance<best;labels[pick]=i;best[pick]=distance[pick]
valid=np.ones(labels.shape,dtype=bool);valid[638:1020,50:390]=False
valid&=best<65**2
data=read(baseline/'territories.geojson')
protected=[f for f in data['features'] if f['properties'].get('canon')]
protected_union=clean(unary_union([make_valid(shape(f['geometry'])) for f in protected]))
available=clean(land.difference(protected_union))
skip={'England','13 Kingdoms','La Florida','Calusa Kingdom (Occupied)'}
report=[];candidates=[]
for index,name in enumerate(names):
    if name in skip:report.append({'name':name,'status':'Existing realms preserved'});continue
    # The named archipelagos are too small for reliable color segmentation.
    # Use the atlas coastline for their identified geographic footprints.
    if name in ['Corsair Territories (La Florida)','Ming & Polynesian Hawaii']:
        island_frame=box(-80.5,20.5,-72,28) if name.startswith('Corsair') else box(-161,18,-154,23)
        g=clean(available.intersection(island_frame))
        if not g.is_empty:candidates.append((name,palette[index],g))
        else:report.append({'name':name,'status':'Named island footprint outside available geography'})
        continue
    if name not in regions:
        report.append({'name':name,'status':'Legend entry has no unambiguous visible footprint; not placed'})
        continue
    mask=(labels==index)&valid
    region_mask=np.zeros(mask.shape,dtype=bool)
    for x1,y1,x2,y2 in regions[name]:region_mask[y1:y2,x1:x2]=True
    mask &= region_mask
    components,n=ndimage.label(mask)
    sizes=np.bincount(components.ravel());keep=sizes>=5;keep[0]=False
    mask=keep[components]
    # Merge scanline pixel runs rather than individually unioning every pixel.
    runs=[]
    for y,row in enumerate(mask):
        edges=np.flatnonzero(np.diff(np.r_[False,row,False].astype(int)))
        runs.extend(box(int(a)-.5,y-.5,int(b)-.5,y+.5) for a,b in zip(edges[::2],edges[1::2]))
    if not runs:report.append({'name':name,'status':'No distinct visible footprint in reference'});continue
    pixel=clean(unary_union(runs)).simplify(.8,preserve_topology=True)
    g=clean(clean(transform(warp,pixel)).intersection(available))
    # Ignore subpixel color-noise fragments while retaining mapped island colonies.
    g=clean(unary_union([p for p in parts(g) if p.area>.0003]))
    if g.is_empty:report.append({'name':name,'status':'Visible footprint overlaps preserved realms or lies outside extent'});continue
    candidates.append((name,palette[index],g))
    print(name,round(g.area,3),flush=True)

occupied=protected_union;new=[]
for name,color,g in sorted(candidates,key=lambda x:x[2].area):
    g=clean(g.difference(occupied))
    if g.is_empty:continue
    occupied=clean(occupied.union(g))
    slug=re.sub('[^a-z0-9]+','-',name.lower()).strip('-')
    label=max(parts(g),key=lambda p:p.area).representative_point()
    props={'id':'reference-'+slug,'name':name,'kind':'country','canon':True,'claim':'Unclaimed','color':'#'+''.join(f'{int(x):02x}' for x in color),'flag':'assets/flags/placeholder-state-1.svg','shield':'assets/flags/placeholder-shield-1.svg','wiki':'https://wiki.american-kingdoms.com/','summary':f'{name} appears in the supplied circa 1420 map. These borders are an approximate reference trace; its rulers, heraldry and place in the 1377 setting remain to be developed.','source':'world-factions-1420-reference.jpg','referenceYear':1420,'boundaryStatus':'Approximate raster trace; existing 1377 realms take precedence','label':[label.x,label.y],'labelMinZoom':4 if g.area>10 else 5 if g.area>1 else 6}
    new.append({'type':'Feature','properties':props,'geometry':mapping(g)})
    report.append({'name':name,'status':'Added','areaSquareDegrees':g.area})
provisional=[]
for f in data['features']:
    if f['properties'].get('canon'):continue
    g=clean(make_valid(shape(f['geometry'])).difference(occupied))
    if g.is_empty:continue
    f['geometry']=mapping(g)
    if f['properties']['name'] in {name for name,_,_ in candidates}:
        f['properties']['name']='Unclaimed '+f['properties']['name']
    if f['properties'].get('label'):
        p=max(parts(g),key=lambda p:p.area).representative_point();f['properties']['label']=[p.x,p.y]
    provisional.append(f)
covered=clean(unary_union([make_valid(shape(f['geometry'])) for f in protected+new+provisional]))
remaining=clean(land.difference(covered))
if not remaining.is_empty:
    provisional.append({'type':'Feature','properties':{'id':'northern-south-america-interior','name':'Uncharted Northern South America','kind':'region','canon':False,'claim':'Unclaimed','color':'#d6c5a6','placeholderColor':'#d6c5a6','summary':'Uncharted territory beyond the northern coasts. Borders and lore are yet to be developed.','wiki':'https://wiki.american-kingdoms.com/','flag':'assets/flags/placeholder-state-1.svg'},'geometry':mapping(remaining)})
result={'type':'FeatureCollection','features':protected+new+provisional}
write('territories',result)
(root/'sources/world-reference-import-report.json').write_text(json.dumps({'referenceYear':1420,'approach':'Preserve existing canonical realms','southernExtent':[-83,-5,-58,13],'controlPoints':controls,'pixelRegions':regions,'islandResolution':'Corsair Territories use Bahamas/Turks and Caicos coastline; Ming & Polynesian Hawaii uses Hawaiian coastline. Internal occupation boundaries are not inferred.','factions':report},indent=2),encoding='utf-8')
print('Added',len(new),'factions. Preserved',len(protected),'existing realms.',flush=True)
