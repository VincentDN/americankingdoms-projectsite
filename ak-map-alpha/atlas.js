/* Physical geography and fictional territories are deliberately separate. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const editMode = new URLSearchParams(location.search).get('edit') === '1';
  const status = $('status');
  if (!window.L) { status.textContent = 'The map could not load. Please reload the page.'; return; }
  const map = L.map('map', {zoomControl:false,minZoom:2,maxZoom:9,maxBounds:[[7,-179],[83,-40]],maxBoundsViscosity:1,zoomAnimation:false,fadeAnimation:false,markerZoomAnimation:false});
  L.control.zoom({position:'topright'}).addTo(map);
  map.attributionControl.setPrefix('<a href="https://leafletjs.com/">Leaflet</a>');
  map.attributionControl.addAttribution('Geography: <a href="https://www.naturalearthdata.com/">Natural Earth</a>');
  const home = () => map.fitBounds([[14,-125],[55,-58]], {padding:[20,20],animate:false});
  home(); $('reset').onclick = home;
  let panelMode = 'key';
  function setPanel(open, mode = panelMode) {
    panelMode = mode;
    $('panel').hidden = !open;
    $('key-content').hidden = mode !== 'key';
    $('details').hidden = mode !== 'details';
    $('editor').hidden = !editMode || mode !== 'details';
    $('panel-title').textContent = mode === 'key' ? 'Map key' : editMode ? 'Edit territory' : 'Territory details';
    $('panel-toggle').setAttribute('aria-expanded',String(open && mode === 'key'));
    // Leaflet's map.closeTooltip requires an actual tooltip instance.
    map.eachLayer(layer => { if (layer instanceof L.Tooltip) map.closeTooltip(layer); });
    map.getPane('tooltipPane').style.display = open && matchMedia('(max-width:700px)').matches ? 'none' : '';
    $('panel').querySelector('.panel-body').scrollTop = 0;
  }
  $('panel-toggle').onclick = () => {
    const open = $('panel').hidden || panelMode !== 'key';
    setPanel(open, 'key');
    if (open) $('panel-close').focus({preventScroll:true});
  };
  const closePanel = () => { setPanel(false); $('panel-toggle').focus({preventScroll:true}); };
  $('panel-close').onclick = closePanel;
  document.addEventListener('keydown', e => { if(e.key === 'Escape' && !$('panel').hidden) closePanel(); });
  setPanel(!matchMedia('(max-width:700px)').matches, 'key');
  for (const [name,z] of [['land',200],['water',250],['countries',350],['regions',360]]) { map.createPane(name); map.getPane(name).style.zIndex=z; }
  const groups = {country:L.featureGroup().addTo(map),region:L.featureGroup().addTo(map),sample:L.featureGroup()};
  const rivers = L.featureGroup().addTo(map);
  let selected = null, dirty = false;
  const markDirty = () => { dirty=true; $('editor-status').textContent='Changes are in this tab only. Export before closing.'; };
  window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
  const safeURL = value => { try { const url=new URL(value); return url.protocol==='https:' ? url.href : null; } catch { return null; } };
  const colorOf = feature => /^#[0-9a-f]{6}$/i.test(feature.properties.color) ? feature.properties.color : '#a59670';
  const borderOf = feature => '#' + colorOf(feature).slice(1).match(/../g).map(c=>Math.round(parseInt(c,16)*.58).toString(16).padStart(2,'0')).join('');
  const style = feature => ({color:borderOf(feature),weight:feature.properties.canon?1.7:1,fillColor:colorOf(feature),fillOpacity:feature.properties.canon?.72:.48,dashArray:null});
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
    layer.on('mouseover',()=>{closeOtherTooltips(layer);layer.setStyle({weight:3,fillOpacity:.9});});
    layer.on('mouseout',()=>layer.setStyle(style(layer.feature)));
    layer.on('click',()=>select(layer));
    layer.on('add',()=>{const path=layer.getElement();if(path){path.setAttribute('tabindex','0');path.setAttribute('role','button');path.setAttribute('aria-label',layer.feature.properties.name);path.onfocus=()=>{closeOtherTooltips(layer);layer.openTooltip();};path.onblur=()=>layer.closeTooltip();path.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(layer);}};}});
    layer.on('pm:edit',markDirty);
    groups[sample?'sample':feature.properties.kind==='region'?'region':'country'].addLayer(layer);
  }
  function addFeatures(data,sample=false) {
    L.geoJSON(data,{pane:'countries',pmIgnore:sample,onEachFeature:(f,l)=>wire(l,f,sample)});
  }
  function refreshList() {
    const list=$('territory-list');list.replaceChildren();
    const provisional=document.createElement('details'),summary=document.createElement('summary');
    summary.textContent='Provisional territories';provisional.append(summary);
    Object.values(groups).forEach(group=>{if(map.hasLayer(group))group.eachLayer(layer=>{
      const button=document.createElement('button'),swatch=document.createElement('span');
      swatch.className='territory-swatch';swatch.style.background=colorOf(layer.feature);swatch.setAttribute('aria-hidden','true');
      button.append(swatch,document.createTextNode(layer.feature.properties.name));
      button.onclick=()=>{map.fitBounds(layer.getBounds(),{maxZoom:6,animate:false,padding:[30,30]});select(layer);};
      (layer.feature.properties.canon?list:provisional).append(button);
    });});
    if(provisional.children.length>1)list.append(provisional);
  }

  for(const [id,group] of [['countries',groups.country],['regions',groups.region],['samples',groups.sample],['rivers',rivers]]) $(''+id).onchange=e=>{if(e.target.checked)group.addTo(map);else map.removeLayer(group);refreshList();};
  async function read(path){const response=await fetch(path);if(!response.ok)throw new Error(path);return response.json();}
  async function init() {
    try {
      const [land,lakes,riverData,territories,samples]=await Promise.all(['land','lakes','rivers','territories','samples'].map(name=>read('data/'+name+'.geojson')));
      L.geoJSON(land,{pane:'land',interactive:false,pmIgnore:true,style:{color:'#796747',weight:1.2,fillColor:'#f0e5cd',fillOpacity:1}}).addTo(map);
      L.geoJSON(lakes,{pane:'water',interactive:false,pmIgnore:true,style:{color:'#9d8961',weight:.7,fillColor:'#d6c6a4',fillOpacity:1}}).addTo(map);
      L.geoJSON(riverData,{pane:'water',interactive:false,pmIgnore:true,style:{color:'#9d8961',weight:1,opacity:.65}}).addTo(rivers);
      addFeatures(territories);addFeatures(samples,true);refreshList();
      status.textContent='East Coast realms follow the canonical reference. Interior borders follow rivers and inferred mountain divides; their names and lore remain provisional.';
      if(editMode) await enableEditor();
    } catch(error) { status.textContent='Part of the atlas could not load. Reload to try again.';console.error(error); }
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
    map.on('pm:create',e=>{const f=e.layer.toGeoJSON();f.properties={id:'territory-'+Date.now(),name:'New territory',kind:'country',color:'#b31f34',summary:'',wiki:'',canon:false};wire(e.layer,f);select(e.layer);refreshList();markDirty();});
    map.on('pm:remove',e=>{Object.values(groups).forEach(g=>g.removeLayer(e.layer));if(selected===e.layer){selected=null;$('details').hidden=true;}refreshList();markDirty();});
    $('edit-form').onsubmit=e=>{e.preventDefault();if(!selected||selected.sample){$('editor-status').textContent='Draw or select a country or region first.';return;}
      const oldKind=selected.feature.properties.kind;
      Object.assign(selected.feature.properties,{name:$('edit-name').value.trim(),kind:$('edit-kind').value,color:$('edit-color').value,summary:$('edit-description').value,wiki:safeURL($('edit-wiki').value)||''});
      if(oldKind!==selected.feature.properties.kind){groups[oldKind].removeLayer(selected);groups[selected.feature.properties.kind].addLayer(selected);}
      selected.setStyle(style(selected.feature));selected.setTooltipContent(tooltip(selected.feature));selected.getElement()?.setAttribute('aria-label',selected.feature.properties.name);select(selected);refreshList();markDirty();
    };
    $('export').onclick=()=>{const features=[];for(const kind of ['country','region'])groups[kind].eachLayer(l=>features.push(l.toGeoJSON()));const blob=new Blob([JSON.stringify({type:'FeatureCollection',features},null,2)],{type:'application/geo+json'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='territories.geojson';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);dirty=false;$('editor-status').textContent='Export requested. Keep the downloaded file; publishing is a separate step.';};
  }
  init();
})();
