/* Physical geography and fictional territories are deliberately separate. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  // Binds an optional control without risking the whole script: if the
  // page and this script ever drift (a stale cached copy of one served
  // alongside a fresh copy of the other -- exactly what a plain, unversioned
  // <script src="atlas.js"> invites), a missing element here only disables
  // that one control instead of throwing and aborting before the map data
  // ever loads.
  const on = (id, event, handler) => { const el = $(id); if (el) el[event] = handler; else console.error('Atlas: expected #'+id+' in the page'); };
  const editMode = new URLSearchParams(location.search).get('edit') === '1';
  const status = $('status');
  const showStatus = text => { status.hidden = false; status.textContent = text; };
  if (!window.L) { showStatus('The map could not load. Please reload the page.'); return; }
  // Azimuthal equidistant, centred on the North Pole rather than Leaflet's
  // default Web Mercator. There is no tile layer here (every layer is
  // vector GeoJSON), so a custom CRS only has to get project/unproject
  // right; nothing depends on a 256px tile pyramid. lon0 picks which
  // meridian points "up" from the pole -- roughly through central Canada,
  // so North America reads upright rather than rotated.
  const R = 6371000, D2R = Math.PI / 180, R2D = 180 / Math.PI, lon0 = -100 * D2R;
  const PolarAzimuthal = {
    R,
    project(latlng) {
      const rho = R * (Math.PI / 2 - latlng.lat * D2R);
      const theta = latlng.lng * D2R - lon0;
      return L.point(rho * Math.sin(theta), -rho * Math.cos(theta));
    },
    unproject(point) {
      const rho = Math.sqrt(point.x * point.x + point.y * point.y);
      const lat = 90 - rho / R * R2D;
      const lon = (((lon0 + Math.atan2(point.x, -point.y)) * R2D + 540) % 360) - 180;
      return L.latLng(lat, lon);
    },
    bounds: L.bounds([-R * Math.PI, -R * Math.PI], [R * Math.PI, R * Math.PI]),
  };
  const polarScale = 0.5 / (Math.PI * R);
  L.CRS.PolarAzimuthal = L.extend({}, L.CRS.Earth, {
    code: 'AK:polar-azimuthal',
    projection: PolarAzimuthal,
    transformation: new L.Transformation(polarScale, 0.5, -polarScale, 0.5),
  });
  const map = L.map('map', {crs:L.CRS.PolarAzimuthal,zoomControl:false,minZoom:2,maxZoom:9,zoomAnimation:false,fadeAnimation:false,markerZoomAnimation:false});
  L.control.zoom({position:'topright'}).addTo(map);
  map.attributionControl.setPrefix('<a href="https://leafletjs.com/">Leaflet</a>');
  map.attributionControl.addAttribution('Geography: <a href="https://www.naturalearthdata.com/">Natural Earth</a>');
  const home = () => map.setView([48,-100], 4, {animate:false});
  home();
  let panelMode = 'key';
  function setPanel(open, mode = panelMode) {
    panelMode = mode;
    $('panel').hidden = !open;
    $('key-content').hidden = mode !== 'key';
    $('details').hidden = mode !== 'details';
    $('editor').hidden = !editMode || mode !== 'details';
    $('panel-title').textContent = mode === 'key' ? 'Map key' : editMode ? 'Edit territory' : 'Territory details';
    $('panel-toggle')?.setAttribute('aria-expanded',String(open && mode === 'key'));
    // Leaflet's map.closeTooltip requires an actual tooltip instance.
    map.eachLayer(layer => { if (layer instanceof L.Tooltip) map.closeTooltip(layer); });
    map.getPane('tooltipPane').style.display = open && matchMedia('(max-width:700px)').matches ? 'none' : '';
    $('panel').querySelector('.panel-body').scrollTop = 0;
  }
  on('panel-toggle','onclick', () => {
    const open = $('panel').hidden || panelMode !== 'key';
    setPanel(open, 'key');
    if (open) $('panel-close')?.focus({preventScroll:true});
  });
  const closePanel = () => { setPanel(false); $('panel-toggle')?.focus({preventScroll:true}); };
  on('panel-close','onclick', closePanel);
  document.addEventListener('keydown', e => { if(e.key === 'Escape' && !$('panel').hidden) closePanel(); });
  setPanel(!matchMedia('(max-width:700px)').matches, 'key');
  for (const [name,z] of [['land',200],['water',250],['countries',350],['regions',360]]) { map.createPane(name); map.getPane(name).style.zIndex=z; }
  const groups = {country:L.featureGroup().addTo(map),region:L.featureGroup().addTo(map),sample:L.featureGroup()};
  const rivers = L.featureGroup().addTo(map);
  // Cities are placeholder real-world data (state/province/national
  // capitals plus population-banded regional cities), the same way the
  // real-state border placeholders are: not in-world canon. Each tier is
  // its own layer group added/removed from the map as the zoom crosses
  // its threshold, rather than hiding individual markers, so zoomed-out
  // views stay uncluttered and the DOM only carries what's on screen.
  // A single brass diamond glyph for every tier; only size and opacity
  // step down the hierarchy, kept small and faint so the glyphs read as a
  // quiet map convention rather than competing with the territory fills.
  const CITY_TIERS = {
    capital:  {minZoom:2, size:7, opacity:.8},
    province: {minZoom:4, size:5, opacity:.65},
    metro:    {minZoom:5, size:4, opacity:.55},
    city:     {minZoom:6, size:3, opacity:.45},
  };
  const cityTierGroups = {capital:L.layerGroup(),province:L.layerGroup(),metro:L.layerGroup(),city:L.layerGroup()};
  let citiesEnabled = true;
  function updateCityTiers() {
    const zoom = map.getZoom();
    for (const [tier,group] of Object.entries(cityTierGroups)) {
      const should = citiesEnabled && zoom >= CITY_TIERS[tier].minZoom, has = map.hasLayer(group);
      if (should && !has) group.addTo(map); else if (!should && has) map.removeLayer(group);
    }
  }
  map.on('zoomend', updateCityTiers);
  let selected = null, dirty = false;
  const markDirty = () => { dirty=true; $('editor-status').textContent='Changes are in this tab only. Export before closing.'; };
  window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
  const safeURL = value => { try { const url=new URL(value); return url.protocol==='https:' ? url.href : null; } catch { return null; } };
  const baseColorOf = feature => /^#[0-9a-f]{6}$/i.test(feature.properties.color) ? feature.properties.color : '#a59670';
  // Map mode recolours canon territories two ways: Realms groups the 13
  // rebelling colonies (properties.alliance === 'union') into a
  // north-to-south blue shade and the crown they're rebelling against
  // (alliance === 'crown') into a single red; Cultures shows each
  // territory's own reference colour (baseColorOf), which is how heritage
  // and origin were already encoded when the map was first traced. Canon
  // territories outside both alliances (Florida, Smokey March, the
  // Sidennic League) always show their own colour, since neither mode has
  // anything else to say about them. Provisional (non-canon) territories
  // are always shown almost blank, regardless of mode, so the lore-backed
  // canon territories stand out.
  let mapMode = 'realms';
  const hslToHex = (h,s,l) => {
    s/=100; l/=100;
    const k = n => (n + h/30) % 12;
    const a = s * Math.min(l, 1-l);
    const f = n => l - a*Math.max(-1, Math.min(k(n)-3, Math.min(9-k(n), 1)));
    const toHex = x => Math.round(255*x).toString(16).padStart(2,'0');
    return '#' + toHex(f(0)) + toHex(f(8)) + toHex(f(4));
  };
  const UNION_ORDER = ['Massachusetts','New Hampshire','Connecticut','Rhode Island','New York','Pennsylvania','New Jersey','Delaware','Maryland','Virginia','North Carolina','South Carolina','Georgia'];
  const unionShade = name => {
    const i = UNION_ORDER.indexOf(name);
    const t = i < 0 ? .5 : i / (UNION_ORDER.length - 1);
    return hslToHex(212, 62, 70 - t * 42);
  };
  const CROWN_SHADE = hslToHex(354, 58, 34);
  const PROVISIONAL_PALE = '#f0e6cd';
  const isProvisional = feature => !feature.properties.canon;
  const colorOf = feature => {
    if (isProvisional(feature)) return PROVISIONAL_PALE;
    if (mapMode === 'realms') {
      const alliance = feature.properties.alliance;
      if (alliance === 'union') return unionShade(feature.properties.name);
      if (alliance === 'crown') return CROWN_SHADE;
    }
    return baseColorOf(feature);
  };
  const borderOf = feature => '#' + colorOf(feature).slice(1).match(/../g).map(c=>Math.round(parseInt(c,16)*.58).toString(16).padStart(2,'0')).join('');
  const style = feature => {
    const canon = feature.properties.canon;
    return canon
      ? {color:borderOf(feature),weight:1.7,opacity:1,fillColor:colorOf(feature),fillOpacity:.72,dashArray:null}
      : {color:borderOf(feature),weight:.6,opacity:.55,fillColor:colorOf(feature),fillOpacity:.22,dashArray:null};
  };
  // Hover and keyboard focus each open a tooltip independently, so crossing
  // straight from one territory into another (a shared border, or tabbing
  // while the mouse still rests elsewhere) can leave more than one open.
  const closeOtherTooltips = current => Object.values(groups).forEach(g => g.eachLayer(l => { if (l !== current) l.closeTooltip(); }));

  function tooltip(feature) {
    const node=document.createElement('div'), title=document.createElement('strong');
    title.textContent=feature.properties.name || 'Unnamed territory';title.style.borderLeft='5px solid '+colorOf(feature);title.style.paddingLeft='8px';node.append(title);
    const desc=document.createElement('span');desc.textContent=feature.properties.summary || feature.properties.kind || 'Territory';node.append(desc);return node;
  }
  function select(layer) {
    selected=layer; setPanel(true, 'details'); layer.closeTooltip(); const p=layer.feature.properties;
    $('details').hidden=false;$('detail-name').textContent=p.name;$('detail-description').textContent=p.summary || '';
    const flag=$('detail-flag');flag.hidden=!p.flag;if(p.flag){flag.src=p.flag;flag.alt='Flag of '+(p.name || 'this territory');}
    const url=safeURL(p.wiki);$('detail-link').hidden=!url;if(url)$('detail-link').href=url;
    const hasAuthor=url && p.claim && p.claim.trim() && p.claim.trim().toLowerCase()!=='unclaimed';
    $('detail-author').hidden=!hasAuthor;if(hasAuthor)$('detail-author').textContent='By '+p.claim.trim();
    if(editMode) { $('edit-name').value=p.name || ''; $('edit-kind').value=p.kind==='region'?'region':'country';$('edit-color').value=p.color || '#b31f34';$('edit-description').value=p.summary || '';$('edit-wiki').value=url || ''; }
  }
  function wire(layer,feature,sample=false) {
    layer.feature=feature;layer.sample=sample;if(!map.hasLayer(layer))layer.options.pane=feature.properties.kind==='region'?'regions':'countries';layer.setStyle(style(feature));
    layer.bindTooltip(tooltip(feature),{className:'territory-tooltip',sticky:true,direction:'top'});
    layer.on('mouseover',()=>{closeOtherTooltips(layer);layer.setStyle({weight:3,opacity:1,fillOpacity:.9});});
    layer.on('mouseout',()=>layer.setStyle(style(layer.feature)));
    layer.on('click',()=>select(layer));
    layer.on('add',()=>{const path=layer.getElement();if(path){path.setAttribute('tabindex','0');path.setAttribute('role','button');path.setAttribute('aria-label',layer.feature.properties.name);path.onfocus=()=>{closeOtherTooltips(layer);layer.openTooltip();};path.onblur=()=>layer.closeTooltip();path.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(layer);}};}});
    layer.on('pm:edit',markDirty);
    groups[sample?'sample':feature.properties.kind==='region'?'region':'country'].addLayer(layer);
  }
  function addFeatures(data,sample=false) {
    L.geoJSON(data,{pane:'countries',pmIgnore:sample,onEachFeature:(f,l)=>wire(l,f,sample)});
  }
  function cityTooltip(feature) {
    const p=feature.properties, node=document.createElement('div'), title=document.createElement('strong');
    title.textContent=p.name;title.style.borderLeft='5px solid #8a6d35';title.style.paddingLeft='8px';node.append(title);
    const place=[p.admin1,p.country].filter(Boolean).join(', ');
    const desc=document.createElement('span');
    desc.textContent = p.tier==='capital' ? 'National capital of '+p.country : p.tier==='province' ? 'Capital of '+place : place;
    node.append(desc);return node;
  }
  function cityIcon(cfg) {
    return L.divIcon({
      className:'city-marker',
      html:`<span class="city-diamond" style="width:${cfg.size}px;height:${cfg.size}px;opacity:${cfg.opacity}"></span>`,
      iconSize:[cfg.size,cfg.size],
      iconAnchor:[cfg.size/2,cfg.size/2],
    });
  }
  function addCities(data) {
    for (const feature of data.features) {
      const cfg=CITY_TIERS[feature.properties.tier];
      if (!cfg) continue;
      const [lon,lat]=feature.geometry.coordinates;
      const marker=L.marker([lat,lon],{icon:cityIcon(cfg),keyboard:false});
      marker.bindTooltip(cityTooltip(feature),{className:'territory-tooltip',direction:'top',offset:[0,-cfg.size]});
      cityTierGroups[feature.properties.tier].addLayer(marker);
    }
  }
  for(const [id,group] of [['countries',groups.country],['regions',groups.region],['samples',groups.sample],['rivers',rivers]]) on(id,'onchange', e=>{if(e.target.checked)group.addTo(map);else map.removeLayer(group);});
  on('cities','onchange', e=>{citiesEnabled=e.target.checked;updateCityTiers();});
  document.querySelectorAll('input[name=mapmode]').forEach(radio=>radio.onchange=e=>{
    if(!e.target.checked)return;
    mapMode=e.target.value;
    Object.values(groups).forEach(group=>group.eachLayer(layer=>{layer.setStyle(style(layer.feature));layer.setTooltipContent(tooltip(layer.feature));}));
  });
  async function read(path){const response=await fetch(path);if(!response.ok)throw new Error(path);return response.json();}
  // A ring/line whose raw longitudes cross +/-180 (Alaska, the Aleutians)
  // would jump ~360 degrees between two adjacent points once projected,
  // tearing the shape into a wedge. Shifting each ring's own longitudes by
  // whatever multiple of 360 keeps consecutive points close together fixes
  // this -- sin/cos are periodic, so the shift doesn't change where any
  // individual ring ends up, only that it stays continuous with itself.
  function unwrapAntimeridian(coords) {
    if (Array.isArray(coords[0]) && typeof coords[0][0] === 'number') {
      let offset = 0;
      for (let i = 1; i < coords.length; i++) {
        const delta = coords[i][0] - coords[i - 1][0];
        if (delta > 180) offset -= 360; else if (delta < -180) offset += 360;
        coords[i][0] += offset;
      }
    } else coords.forEach(unwrapAntimeridian);
    return coords;
  }
  function unwrapFeatures(fc) {
    fc.features.forEach(f => { if (f.geometry) unwrapAntimeridian(f.geometry.coordinates); });
    return fc;
  }
  async function init() {
    try {
      // Cities are Point features -- no ring to keep continuous across the
      // antimeridian -- so they skip unwrapFeatures and are fetched
      // alongside, not through, the polygon/line batch that needs it.
      const [[land,lakes,riverData,territories,samples],cities]=await Promise.all([
        Promise.all(['land','lakes','rivers','territories','samples'].map(name=>read('data/'+name+'.geojson'))).then(fcs=>fcs.map(unwrapFeatures)),
        read('data/cities.geojson'),
      ]);
      L.geoJSON(land,{pane:'land',interactive:false,pmIgnore:true,style:{color:'#796747',weight:1.2,fillColor:'#f0e5cd',fillOpacity:1}}).addTo(map);
      L.geoJSON(lakes,{pane:'water',interactive:false,pmIgnore:true,style:{color:'#9d8961',weight:.7,fillColor:'#d6c6a4',fillOpacity:1}}).addTo(map);
      L.geoJSON(riverData,{pane:'water',interactive:false,pmIgnore:true,style:{color:'#9d8961',weight:1,opacity:.65}}).addTo(rivers);
      addFeatures(territories);addFeatures(samples,true);
      addCities(cities);updateCityTiers();
      if(editMode) await enableEditor();
    } catch(error) { showStatus('Part of the atlas could not load. Reload to try again.');console.error(error); }
  }
  async function enableEditor() {
    const css=document.createElement('link');css.rel='stylesheet';css.href='vendor/geoman.css';document.head.append(css);
    await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='vendor/geoman.js';script.onload=resolve;script.onerror=reject;document.head.append(script);});
    // The editor is loaded lazily after the map and its territory layers exist.
    L.PM.reInitLayer(map);
    Object.values(groups).forEach(group=>L.PM.reInitLayer(group));
    setPanel(true, 'details');
    $('details').hidden = !selected;
    map.pm.addControls({position:'topright',drawMarker:false,drawCircleMarker:false,drawPolyline:false,drawRectangle:false,drawCircle:false,drawText:false,cutPolygon:false,rotateMode:false,dragMode:false});
    map.pm.setGlobalOptions({snappable:true,allowSelfIntersection:false});
    map.on('pm:create',e=>{const f=e.layer.toGeoJSON();f.properties={id:'territory-'+Date.now(),name:'New territory',kind:'country',color:'#b31f34',summary:'',wiki:'',canon:false};wire(e.layer,f);select(e.layer);markDirty();});
    map.on('pm:remove',e=>{Object.values(groups).forEach(g=>g.removeLayer(e.layer));if(selected===e.layer){selected=null;$('details').hidden=true;}markDirty();});
    on('edit-form','onsubmit', e=>{e.preventDefault();if(!selected||selected.sample){$('editor-status').textContent='Draw or select a country or region first.';return;}
      const oldKind=selected.feature.properties.kind;
      Object.assign(selected.feature.properties,{name:$('edit-name').value.trim(),kind:$('edit-kind').value,color:$('edit-color').value,summary:$('edit-description').value,wiki:safeURL($('edit-wiki').value)||''});
      if(oldKind!==selected.feature.properties.kind){groups[oldKind].removeLayer(selected);groups[selected.feature.properties.kind].addLayer(selected);}
      selected.setStyle(style(selected.feature));selected.setTooltipContent(tooltip(selected.feature));selected.getElement()?.setAttribute('aria-label',selected.feature.properties.name);select(selected);markDirty();
    });
    on('export','onclick', ()=>{const features=[];for(const kind of ['country','region'])groups[kind].eachLayer(l=>features.push(l.toGeoJSON()));const blob=new Blob([JSON.stringify({type:'FeatureCollection',features},null,2)],{type:'application/geo+json'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='territories.geojson';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);dirty=false;$('editor-status').textContent='Export requested. Keep the downloaded file; publishing is a separate step.';});
  }
  init();
})();
