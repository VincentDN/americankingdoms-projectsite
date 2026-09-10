/* This page requests only its own faction data, never the world layers. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const config = window.ATLAS_SUBMAPS?.[document.body.dataset.submap];
  const status = $('submap-status');
  if (!window.L || !config) { status.textContent='This map is unavailable. Please return to the world map or reload.'; return; }
  const title='The Kingdom of '+config.name+' in 1377 A.D.';
  $('kingdom-title').textContent=title;document.title=title;
  const map = L.map('map',{zoomControl:false,minZoom:6,maxZoom:13,zoomSnap:.25});
  L.control.zoom({position:'topright'}).addTo(map);
  map.attributionControl.setPrefix('<a href="https://leafletjs.com/">Leaflet</a>');
  map.attributionControl.addAttribution('Boundaries: <a href="https://tigerweb.geo.census.gov/arcgis/rest/services/Generalized_ACS2024/State_County/MapServer/11">U.S. Census Bureau, 2024</a>');
  map.setView([42.2,-71.8],7);
  const entries = new Map();
  let counties, selected = null;
  let returnFocus = null;
  function closeDetails() {
    $('county-details').hidden=true;selected=null;refresh();
    history.replaceState(null,'',location.pathname+location.search);
    returnFocus?.focus({preventScroll:true});
  }
  $('county-close').onclick=closeDetails;
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape' && !$('county-details').hidden){event.preventDefault();closeDetails();}
  });
  const region = $('region');
  const nameOf = p => p.displayName || p.name;
  const baseStyle = f => ({color:'#534432',weight:1.3,fillColor:f.properties.color,fillOpacity:.72});
  function refresh() {
    entries.forEach(({layer,button},id) => {
      const active = !region.value || layer.feature.properties.region === region.value;
      const chosen = selected === id;
      layer.setStyle({...baseStyle(layer.feature),fillOpacity:active ? (chosen ? .95 : .72) : .15,weight:chosen?3:1.3,color:chosen?'#8b1728':'#534432'});
      button.hidden=!active;
      button.setAttribute('aria-pressed',String(chosen));
      const path=layer.getElement();
      if(path)path.setAttribute('aria-pressed',String(chosen));
      const label=layer.getTooltip();
      // Hide small labels until zoomed in; county list always exposes names.
      const visible=active && (map.getZoom()>=9 || !['Suffolk','Norfolk'].includes(layer.feature.properties.name));
      if(visible && !layer.isTooltipOpen())layer.openTooltip();
      else if(!visible)layer.closeTooltip();
      if(label?.getElement())label.getElement().setAttribute('aria-hidden','true');
    });
  }
  function fit(bounds) { map.fitBounds(bounds,{padding:[36,36],maxZoom:10,animate:false}); }
  function select(id,zoom=true) {
    const entry=entries.get(id); if(!entry)return;
    if(region.value && entry.layer.feature.properties.region!==region.value)region.value='';
    selected=id;
    const p=entry.layer.feature.properties;
    $('county-details').hidden=false;
    $('county-name').textContent=nameOf(p);
    $('county-region').textContent=p.region;
    $('county-flag').alt='Placeholder flag of '+nameOf(p);
    returnFocus=entry.button;
    $('county-details-title').focus({preventScroll:true});
    $('county-details').querySelector('.panel-body').scrollTop=0;
    entry.layer.bringToFront();
    if(zoom)fit(entry.layer.getBounds());
    refresh();
    const url=new URL(location.href);url.hash='county='+encodeURIComponent(id);history.replaceState(null,'',url);
  }
  function reset() {
    region.value='';selected=null;$('county-details').hidden=true;
    fit(counties.getBounds());refresh();
    history.replaceState(null,'',location.pathname+location.search);
  }
  $('reset-map').onclick=reset;
  region.onchange=()=>{
    selected=null;$('county-details').hidden=true;
    const visible=[...entries.values()].filter(e=>!region.value||e.layer.feature.properties.region===region.value);
    fit(L.featureGroup(visible.map(e=>e.layer)).getBounds());refresh();
    history.replaceState(null,'',location.pathname+location.search);
  };
  map.on('zoomend',refresh);
  new ResizeObserver(()=>map.invalidateSize({pan:false})).observe($('map'));
  async function load() {
    $('retry-map').hidden=true;status.hidden=false;status.textContent='Loading county map…';
    const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),15000);
    try {
      const response=await fetch(config.data,{signal:controller.signal});
      if(!response.ok)throw new Error('County data unavailable');
      const data=await response.json();
      if(data.type!=='FeatureCollection'||!data.features?.length)throw new Error('Invalid county data');
      const regions=[...new Set(data.features.map(f=>f.properties.region))];
      regions.forEach(name=>{const option=document.createElement('option');option.value=name;option.textContent=name;region.append(option);});
      counties=L.geoJSON(data,{style:baseStyle,onEachFeature:(f,layer)=>{
        const p=f.properties, button=document.createElement('button');
        button.type='button';button.className='county-button';button.setAttribute('aria-pressed','false');
        const swatch=document.createElement('span');swatch.className='county-swatch';swatch.style.backgroundColor=p.color;swatch.setAttribute('aria-hidden','true');
        button.append(swatch,document.createTextNode(nameOf(p)));button.onclick=()=>select(p.id);$('county-list').append(button);
        const label=document.createElement('span');label.className='county-map-label';
        const shield=document.createElement('img');shield.src='/medieval-america-map/assets/placeholder-arms.svg';shield.alt='';shield.width=24;shield.height=29;
        label.append(shield,document.createTextNode(nameOf(p)));
        layer.bindTooltip(label,{permanent:true,direction:'center',className:'county-label'});
        layer.on('tooltipopen',()=>layer.getTooltip().setLatLng([p.label[1],p.label[0]]));
        layer.on('click',()=>select(p.id));
        layer.on('add',()=>{
          const path=layer.getElement();if(!path)return;
          path.setAttribute('tabindex','0');path.setAttribute('role','button');path.setAttribute('aria-label',nameOf(p));
          path.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(p.id);}};
        });
        entries.set(p.id,{layer,button});
      }}).addTo(map);
      map.setMaxBounds(counties.getBounds().pad(.6));
      fit(counties.getBounds());refresh();
      const id=new URLSearchParams(location.hash.slice(1)).get('county');if(id)select(id);
      status.hidden=true;region.disabled=false;$('reset-map').disabled=false;
    } catch(error) {
      if(counties)map.removeLayer(counties);entries.clear();$('county-list').replaceChildren();
      while(region.options.length>1)region.remove(1);
      status.textContent='The county map could not load. Try again or return to the world map.';$('retry-map').hidden=false;
      console.error(error);
    } finally {clearTimeout(timeout);}
  }
  $('retry-map').onclick=load;
  load();
})();
