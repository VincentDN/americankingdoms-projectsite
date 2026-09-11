# American Kingdoms atlas groundwork

## Lightweight mobile atlas branch

On `codex/mobile-lightweight-map`, phones load `data/mobile/atlas.json` instead
of the six full geography files. Automatic selection uses a viewport up to 900px,
coarse pointers up to 1200px, or the browser's Save Data preference. Selection is
made once on page load so rotation does not download another dataset. `?detail=lite`
and `?detail=full` override it; the editor always uses full geometry.

The light map uses Leaflet canvas paths, no city markers/rivers/hover previews,
at most 18 visible heraldic labels, and zoom levels 2–7. The native realm picker
keeps small countries and keyboard navigation accessible. Flags, descriptions,
wiki links, alliances and county-submap links remain available. The detail switch
preserves the viewport through the existing return-state mechanism. Mobile panels
start closed and open as a bounded, scrollable bottom sheet.

Run `python scripts/build-mobile-map.py` with Shapely >= 2.1 after editing source
geography. The generator nodes the shared border network before coverage
simplification, removes minor fragments while retaining every canonical realm,
and validates exported polygons. It enforces a 900 KB raw data ceiling. The current
build is 856,005 bytes versus 6,049,988 bytes for the full data (85.9% smaller),
approximately 290,606 bytes with gzip. Exact figures live in
`data/mobile/build-stats.json`; these are payload measurements, not device FPS.
Rerun this after any edit to `data/territories.geojson`, `data/land.geojson` or
`data/rivers.geojson` so the mobile bundle stays in sync with the full data.

Run `node scripts/test-map-loading.mjs` to check automatic/forced data selection,
canvas settings, realm selection, full-detail switching and offline feedback.
Verified in-browser on real phone-width, touch-emulated viewports: tap-to-select
against the rendered canvas paths, the bottom-sheet map key, and the full/lite
detail switch all work correctly (an earlier manual spot-check that appeared to
find dead taps was miscalibrated screen coordinates, not a hit-testing bug --
Leaflet's per-pane Canvas renderer already hit-tests every layer in its own pane
correctly).

## South America interior trim and Mayan States — 11 September 2026

The "Uncharted Northern South America" catch-all territory covered a large,
label-less inland wedge south-east of Roman Colonies (roughly lon -81..-58,
lat -5..11) with no coastline of its own -- an artifact of the original
Natural Earth import's clip box, not a real landform boundary. Removing just
its political overlay wasn't enough, since `data/land.geojson` is a separate
physical base layer: `scripts/trim-south-america-land.py` subtracts the exact
same wedge polygon from the single continental land ring (recovered from the
pre-edit territories file), and `scripts/trim-south-america-rivers.py` clips
the same wedge out of `data/rivers.geojson` so no river segments are left
dangling over open water. North/Central America and the Roman Colonies
coastal strip are unaffected; `scripts/fix-south-america-and-mayan.py` drops
only that one sub-polygon (of thousands of unrelated Aleutian-island slivers)
from the territory itself. Run in order: `fix-south-america-and-mayan.py`,
then `trim-south-america-land.py`, then `trim-south-america-rivers.py`
(the latter two read the pre-edit territories geometry from
`/tmp/territories-orig.geojson`, written by `git show HEAD:...` beforehand).

`fix-south-america-and-mayan.py` also expands Mayan Civilizations -- renamed
**Mayan States** -- south and west to absorb the neighbouring unclaimed
provisional realms 43 (Chiapas/Guatemala/Belize) and 45 (El Salvador/Honduras/
Nicaragua's Pacific coast), matching both the user-traced extent and the real
historical reach of Maya civilization. The union produces a disconnected
sliver toward Oaxaca and dozens of sub-pixel topology slivers along that same
imprecise canon/provisional seam (west of lon -96, well outside the historical
Maya heartland); the script keeps the main body plus genuine small offshore
islands and drops the rest. `assets/flags/mayan-states.svg` and
`-shield.svg` are an original tricolour after the historical Republic of
Yucatan flag (green/white/red bands, three five-pointed stars per band on the
flag, one per vertical band on the shield). Its `summary` blends that real
history with AK lore: Roman contact on the Gulf coast taught Maya engineers
iron tools, arch-and-vault masonry and the wheel, and the Mayan States run a
rich sea trade with the Sidennic League.

Aztec Empire also gained an original flag/shield (a golden sun with five
rays rising over green and red, after the reference supplied for this
change) and a `summary` blending the real founding of Tenochtitlan and the
Triple Alliance with an AK-specific note that the Aztecs trade only warily
with the Roman colonies and Mayan States to their east.

## Background music player — 11 September 2026

`music-player.js` (loaded by both `index.html` and the Massachusetts submap
page, never the main site) shuffles the three tracks in
`assets/music/`, advancing to the next shuffled track on `ended` and
reshuffling once the queue is exhausted (never immediately repeating the
track that just played across a reshuffle). Nothing is fetched until
playback is requested: the `<audio preload="none">` element only downloads
once the visitor presses play, and the player starts at volume 0 ("muted by
default") regardless. The nav gets a third "Music" button that opens a small
popover with a play/pause button and a volume slider; both pages already
share `atlas.css`/this script via absolute `/medieval-america-map/...` paths,
so no page-specific wiring was needed beyond the shared markup. On narrow
viewports the popover switches from anchoring off the small button (which
would overflow the viewport) to spanning the full nav width instead.

## Border repair and western expansions — 10 September 2026

After the reference import, `scripts/repair-territory-borders.py PRE_REPAIR_TERRITORIES.geojson`
closes narrow tracing corridors by assigning their land to the nearest adjacent
realm boundary. Broad unclaimed interiors remain provisional. New additions are
clipped to the physical land and lakes, with shared edges rather than overlapping
buffers. The initial pre-repair snapshot is `e2d6f6c`'s territories file.
The repair requires NumPy, Shapely >= 2.1 and pyproj.
Then run `scripts/normalize-territory-topology.py` to dissolve numerical overlay
seams that would otherwise receive visible SVG border strokes, and reclip the
provisional layer against the final canonical coverage.

The Dragon Coast (Ming Empire), formerly Land of Torch Trees (Ming), now covers
Baja California and Baja California Sur and a broader California coastal belt
with a modest inland reach toward Nevada. The Aztec Empire expands through the
western mainland Mexican states, excluding existing claimed territory. The
explicit state list and coastal control points are recorded in the repair script.
`sources/natural-earth-mexico-states.geojson` contains Mexico's states extracted
from Natural Earth's public-domain 10m admin-1 GeoJSON in the
`nvkelso/natural-earth-vector` repository. The existing 50m source lacks Mexico.

The earlier import's exact-geometry preservation applies to that import stage;
the subsequent user-requested repair adds border slivers to existing realms.
Massachusetts retains its modern outline and Florida's northern frontier stays fixed.

## Additional factions and northern South America

The supplied `sources/world-factions-1420-reference.jpg` adds colored factions
to the existing 1377 atlas. This is an additive interpretation of a circa 1420
reference: the original 17 canonical entries, including their geometry, names,
claims, custom flags and shields, are preserved exactly. England, the 13 Kingdoms,
La Florida and occupied Calusa therefore do not overwrite those established realms.
New reference factions replace overlapping unclaimed placeholder areas, receive
floating labels and the standard infobox, and retain explicit `referenceYear`,
`source` and `boundaryStatus` metadata. Their heraldry and lore remain placeholders.

Land, lakes and rivers now include northern South America to 5° south, covering
the Colombia/Venezuela Caribbean coastline and Ecuador's Pacific coast. The
**Southern coasts** control jumps to this area. The source has no complete city
dataset for the extension, so existing city markers are retained unchanged.
County submaps remain isolated from the world-page data.

`scripts/import-world-reference.py BASELINE_DATA_DIRECTORY` reproduces the import
from an exported pre-import `data/` directory (the initial baseline was commit
`af3ff8b`). It requires Pillow, NumPy, SciPy, Shapely and pyproj. Do not point the
baseline argument at the output directory. Pixel colors are segmented within
identified map regions, warped with recorded coastal/lake and approximate inland
anchors, then clipped to physical land and around existing canonical realms.
These are approximate illustrated borders, not surveyed lines. Named Hawaiian
and Bahamian island groups use the available physical coastline because their
tiny reference marks do not support reliable detailed tracing.

`sources/world-reference-import-report.json` records each legend entry's outcome,
control points, region masks and island assumptions. Mali Empire, Muromachi Japan,
Leon and Castille, Al Andalus, Portugal and Scotland have no unambiguous visible
footprint in this image and are left unplaced pending a location reference.

Validation checks preserve the original canonical entries, require valid added
polygons, exclude ocean/lake fill and reject newly introduced overlaps. Static
geographic overviews were inspected in addition to the data checks.

## World labels and unclaimed territories

Named world territories have floating shield/name labels. Interior anchors and
zoom thresholds are generated by `scripts/place-state-labels.py` (Shapely and
pyproj); rerun after border edits. Larger canonical realms appear first, with
smaller and provisional states visible at closer zooms. Screen-space collision
checks suppress overlapping labels. Labels follow their territory layer's
visibility, allow clicks through to the polygon, and do not load county data.
Unnamed provisional fragments remain hoverable without floating labels.

Unclaimed territories have a `placeholderColor` from a pale eight-color palette,
placeholder flags and shields, and starter text where lore was missing. Existing
custom flags and descriptions are retained. The optional `shield` property
overrides the default heraldic placeholder. Map shadows and label halos use tan.
The supplied September 2026 SVG favicon is used by the homepage and both atlas
pages, with identical source copies retained in their asset directories.

## Massachusetts submap — 10 September 2026

The world atlas remains at `/medieval-america-map/`; `/world-map/` redirects
there so existing indexed URLs and bookmarks remain intact. Select Massachusetts
to reveal the red **Load Duchy and County Map** link. The separate static page at
`/world-map/massachusetts/` supports direct loading, refresh, county deep links
(for example `#county=25025`), and a back link that restores the world viewport,
selected faction, map mode, and layer settings when session storage is available.
The misspelled `/world-map/massachussets` redirects to the canonical spelling.

Only `submap.js` requests `data/submaps/massachusetts.geojson` (about 159 KiB).
The world page loads a small metadata registry, `submaps.js`, with no county
geometry or prefetch. The county page reuses the vendored Leaflet library and
atlas styles, but never loads the continental land, lakes, rivers, cities, or
territories. No framework, runtime dependency, or external map service is needed
by visitors. Normal HTTP caching reuses the library and styles between pages.

All 14 modern counties are selectable through polygons and keyboard-accessible
buttons. Five explicitly provisional geographic groupings aid navigation; these
are not assertions of canonical duchy boundaries. The page includes reset,
loading, timeout, retry, mobile layout, and return navigation.

Submap headings and browser titles use **The Kingdom of [StateName] in 1377 A.D.**,
with the name taken from the registry. County labels carry a small shared
placeholder heraldic shield. Selecting a county opens a parchment details panel
with a placeholder flag, county name, Patreon Lord link, lorem ipsum, the same
flag-shop link as the world atlas, and a wiki link to the main wiki homepage.
The panel supports its close button and Escape, returning focus to the county
list; mobile uses a bottom panel. The shared SVG placeholders are original simple
geometric stand-ins, not canonical heraldry.

Medieval territory titles are stored in `sources/massachusetts-titles.json`
and emitted as `displayName` in the county payload. Map labels, county buttons,
accessible labels, flags' alternative text and infoboxes all use this title.
The original geographic `name` and stable IDs remain intact for regeneration
and county deep links. Edit the titles file and rebuild to change names.

Massachusetts now uses its modern outline, as requested. The former northern
claim becomes provisional Maine; adjacent territory edges are trimmed and
repaired to avoid overlaps. The rest of those factions' lore is retained.

County geometry: [U.S. Census Bureau, Generalized ACS 2024, Counties 500K](https://tigerweb.geo.census.gov/arcgis/rest/services/Generalized_ACS2024/State_County/MapServer/11),
downloaded 10 September 2026 with `STATE='25'`, `outFields=NAME,GEOID,BASENAME`,
`outSR=4326`, `returnGeometry=true`, `f=geojson`. The raw response is retained in
`sources/census-ma-counties-2024.geojson`. Shared county borders are simplified
together at 65 metres; the dissolved world outline uses 180 metres. The supplied
reference image informed county coverage; its copyrighted artwork is not shipped.

Rebuild from the repository root with
`python medieval-america-map/scripts/build-massachusetts.py` after installing
`shapely>=2.1` and `pyproj`. Review changes before committing: this updates the
county payload and world territory geometry and can replace manual county edits.

To add a faction, create a static `world-map/<slug>/index.html` from this page,
set its `data-submap`, title, description and canonical URL; register its name,
page URL and versioned data URL in `submaps.js`; add its county FeatureCollection;
and set the world territory's `properties.submap` to the same slug. County
properties are `id`, `name`, `region`, `color` and an interior `[lon,lat]` `label`.
Unavailable factions have no detail-map button. Serve the repository root for
these routes; deploying only the old `medieval-america-map/` directory does not
include the new `world-map/` pages.

Validation: all 14 county polygons are valid and non-overlapping; Massachusetts
has no overlaps with neighboring territories; no territory overlap was increased.
Navigation logic was checked for keyboard selection, regional filtering, reset,
county-only fetching, and error/retry. Static routes and local assets were checked
over HTTP. This update retains the site's existing Cloudflare Pages deployment.

Based on the existing project site's `main` at `f22b95f` (5 September 2026).
This is a standalone static page under `medieval-america-map/`; the landing page is unchanged.

## Open and edit

Serve the repository with any static HTTP server and open `/medieval-america-map/`.
Open `/medieval-america-map/?edit=1` to draw polygons and edit their vertices using Leaflet-Geoman.
Select a polygon to change its name, colour, country/region layer, description and wiki URL.
Export before leaving: edits live only in the current tab, with an unload warning.
Replace `medieval-america-map/data/territories.geojson` with the exported file and commit to publish an update.
The editor does not write to the server and is not an authenticated admin system.
The sample territory is hidden, excluded from exports, and explicitly non-canonical.
The atlas now opens with coloured territories from Vincent's two supplied references.
Sixteen East Coast territories use the canonical reference's names, colour families
and claim labels. Other territories have provisional names and placeholder lore.

For a larger editing workspace, https://editor.geoman.io/ can edit GeoJSON geometry;
preserve the feature properties below. Shared-border topology is not enforced by this
prototype. Snapping helps, but check adjoining polygons for gaps and overlaps.

## Data model

`data/territories.geojson` is a GeoJSON FeatureCollection using WGS84 coordinates
in `[longitude, latitude]` order. Each Polygon or MultiPolygon has properties:

| Property | Purpose |
| --- | --- |
| id | Stable unique identifier |
| name | Display name |
| kind | `country` or `region` |
| color | Six-digit hex fill colour |
| summary | Plain-text hover and details copy |
| wiki | Optional HTTPS lore URL |
| flag | Optional path to a small flag image, shown in the details panel |
| alliance | Optional: `union` (the 13 rebelling colonies) or `crown` (English Canada). Drives the Realms colouring described below. |

Names and descriptions are rendered as text, not injected HTML.
Political geometry is traced from `sources/east-coast-canon.png` (authoritative)
and `sources/continental-outline.jpg` (provisional elsewhere). Massachusetts now uses
its modern outline; the former northern claim is separate provisional Maine. New Hampshire includes the Vermont area;
Smokey March remains separate. Florida retains its existing northern border and
now fills the entire peninsula and coastal islands to the physical coastline,
with lake areas excluded. `scripts/fill-florida.py` reproduces this repair using
the local Natural Earth physical and admin-1 sources (requires Shapely). It checks
that the northern edge is retained and removes overlapping provisional fragments
from the newly filled land.

The source images are rough, differently projected raster maps. Their pixel colours
were segmented and georeferenced using manually paired landmarks. The resulting
borders are editable approximations, not exact survey lines. Subpixel overlaps were
removed with the smaller territories taking precedence, and every provisional shape
was clipped around the canonical states. The images, original physical data and
reproduction script are preserved under `sources/` and `scripts/`.

To regenerate, install the Python dependencies listed at the top of
`scripts/trace-references.py`, download Natural Earth's
`ne_50m_admin_0_countries.geojson` from the same upstream GeoJSON directory cited
below, then run `python medieval-america-map/scripts/trace-references.py /path/to/ne_50m_admin_0_countries.geojson`
from the repository root. This overwrites the generated map data; export and preserve
any later hand edits first. Admin-0 geometry is used only to clip the physical extent
to North America through Panama, not as the fictional political boundaries.

`canon`, `claim`, `source` and `boundaryStatus` properties preserve reference provenance.
Ownership labels describe the supplied reference, not independently verified current claims.
Lake polygons are excluded from territory fills. The original North America-only
physical layer is now extended into northern South America as described above.
The physical base has no modern political borders or city labels.

## Hosting at map.american-kingdoms.com

Deploy the **contents of `medieval-america-map/`** as the root of a separate static hosting project.
No build command, API key, paid tile provider, or backend is required.
Relative asset paths work both at `/medieval-america-map/` and at the subdomain root.
In that project's hosting dashboard, add `map.american-kingdoms.com` as its custom
domain, then use the provider's exact DNS target and finish TLS verification.
The repository does not establish which provider currently controls deployment or DNS;
do not guess a CNAME target or change the existing apex domain configuration.
No DNS changes or production deployment have been made by this groundwork change.

## Sources and dependencies

- Leaflet 1.9.4: https://leafletjs.com/reference.html
  Vendored JS and CSS; BSD license in `vendor/leaflet-LICENSE`.
- Leaflet-Geoman Free 2.18.3: https://geoman.io/docs/leaflet
  Vendored and loaded only in editor mode; MIT license in `vendor/geoman-LICENSE`.
- Natural Earth 1:50m land, lakes, rivers:
  https://www.naturalearthdata.com/downloads/50m-physical-vectors/
  GeoJSON from https://github.com/nvkelso/natural-earth-vector/tree/master/geojson
  (`ne_50m_land.geojson`, `ne_50m_lakes.geojson`, `ne_50m_rivers_lake_centerlines.geojson`).
  Downloaded 6 September 2026, stored locally. Natural Earth data is public domain:
  https://www.naturalearthdata.com/about/terms-of-use/
- Natural Earth 1:50m admin-1 states/provinces (`ne_50m_admin_1_states_provinces.geojson`),
  same upstream directory and licensing as above. Downloaded 7 September 2026 and used
  only for the real-world state-line placeholders described below; the fictional
  canon and provisional layers are unaffected.
- Natural Earth 1:10m populated places (`ne_10m_populated_places.geojson`), same
  upstream directory and licensing as above. Downloaded 8 September 2026, filtered
  to `ISO_A2` `US`/`CA`/`MX` before committing (see "City markers" below), and used
  only for the placeholder city layer; the fictional canon and provisional layers
  are unaffected.
- Existing American Kingdoms logo, colours, Cinzel / Ysabeau / EB Garamond typography.
  Fonts are requested from Google Fonts, with local serif/sans fallbacks.

The 1:50m base is suitable for the first continental view, not detailed fief boundaries
or navigational accuracy. Upgrade to 1:10m geography, spatially clipped and simplified
at multiple zoom levels, when closer-scale canon is available. The renderer uses a
custom polar azimuthal-equidistant projection rather than Leaflet's default Mercator;
see "Polar projection" below.

## Verification

JavaScript syntax, GeoJSON parsing, local HTML asset references, polygon validity,
territory overlap and southern-extent checks were run. A static geometry plot was
inspected against the supplied East Coast reference. Browser interaction and browser
visual QA have not yet been performed.
Before launch, check desktop hover, keyboard selection, mobile pan/pinch, border
drawing/editing/deletion, export-and-reload, and rendering at the subdomain root.

## Cloudflare Pages live alpha

The alpha is served at `/medieval-america-map/` by the existing production Pages project
through its GitHub integration. Publication uses the existing `main` branch; no
DNS change, separate Pages project or new domain is needed.

## Shared-border and interior-region update (7 September 2026)

Run `python medieval-america-map/scripts/refine-territories.py` after the initial trace
to reproduce the current map. It uses the frozen 16-state canonical input in
`sources/canonical-territories.geojson`, the existing physical land/lake mask,
Natural Earth river courses and the inferred guide lines saved in
`sources/inferred-divides.geojson`. The original rough continental reference
remains available, but its hundreds of raster fragments no longer determine
the provisional state boundaries.

Narrow missing canonical seams are allocated to adjoining states by distance,
in 500-metre steps, within a fixed 6-kilometre morphological closing target.
Thin coastal remnants are attached without filling bays or lakes. The interior
is a single polygonized network using major river trunks and inferred mountain
divides; small remnants are merged into neighbouring territories. Common edges
are simplified together. All remaining land belongs to a coloured region.

These 46 provisional regions are a fictional interpretation of geography, not
HydroBASINS data, surveyed catchments, or established American Kingdoms canon.
River courses are from the existing public-domain Natural Earth source. Mountain
guides and connecting passes are inferred and editable. The pipeline checks
coverage, overlap, validity and lake exclusion before publication.

## Real-state placeholder borders (7 September 2026)

Run `python medieval-america-map/scripts/apply-real-state-placeholders.py` after
`refine-territories.py` to replace the interior river/mountain provisional
regions, for every continental US state outside the 13 colonies and Florida,
with a placeholder shaped like that state's real-world boundary. This is a
visual stand-in requested to roughly resemble published "natural state
borders" redraws, not new canon: names, colours and summaries stay
provisional pending real lore and borders.

Source geometry is `sources/natural-earth-admin1-states.geojson`, Natural
Earth 1:50m admin-1 states/provinces (public domain), downloaded 7 September
2026 from the same upstream GeoJSON directory cited above. Each of the 32
target states is clipped to land and to the existing canon footprint (which
is never modified); Maine and Vermont are skipped by name because their land
is already part of the canon Massachusetts/New Hampshire shapes, per the
canon note above. Alaska, Hawaii, DC and the 14 real states already covered
by canon geometry are also skipped. Whatever land the old provisional mesh
still covers outside the new placeholders -- Canada, Mexico, Central America,
Alaska -- is kept, trimmed to the new seams.

Because each placeholder is clipped independently rather than built from one
shared polygonized mesh, seams are numerically but not always vertex-exact,
so this pipeline step validates against a coarser (1-5 km²) tolerance than
`refine-territories.py`'s exact-mesh check; this is still trivial at
continental scale and was checked visually along several borders. A later
pass could re-node the full coverage into one mesh to simplify vertex
density at the new seams, the way `refine-territories.py` already does for
its own regions.

## First hand-added canon territory: the Sidennic League (7 September 2026)

Added as a test of taking a territory from provisional placeholder to full
canon: name, colour, wiki link and a small flag image, sourced from the
existing "Featured Wiki Articles" copy on the main site. Cuba's landmass was
split out of the larger Caribbean provisional region it was previously
bundled into (a MultiPolygon also covering Jamaica and nearby cays, which
keeps its old provisional id and the rest of its geometry) into its own
canon `country` feature, `sidennic-league`, coloured `#2e7d32` to match its
flag. The split only reassigns which feature owns which existing polygon
part; no other territory's geometry changed.

The `flag` property (see the data model above) is new: an optional path to
a small image shown above the name in the details panel. Sidennic League's
flag is a hand-drawn SVG placeholder at
`assets/flags/sidennic-league.svg` -- seven golden apples (one per Sister
City) on a green field, 3:5 ratio -- not sourced from any established
in-world heraldry.

## Polar projection (8 September 2026)

The renderer now uses a custom Leaflet CRS, `L.CRS.PolarAzimuthal`, defined
in `atlas.js`: an azimuthal-equidistant projection centred on the North
Pole, replacing Leaflet's default Web Mercator. This is only practical
because every layer here is vector GeoJSON with no tile layer -- a custom
CRS only has to implement `project`/`unproject`, with nothing depending on
a 256px tile pyramid. The central meridian (`lon0`, currently -100 degrees)
runs up through central Canada so North America reads upright rather than
rotated; the projection math and scale factor are otherwise ordinary
(the same world-diameter-to-unit-square convention Leaflet's own EPSG3857
uses, reusing `L.CRS.Earth` for `wrapLng`/`distance`).

Two things needed fixing beyond the projection math itself:
- Any ring crossing +/-180 degrees longitude (Alaska, the Aleutians) would
  jump ~360 degrees between two adjacent points once projected, tearing
  into a wedge. `unwrapFeatures`/`unwrapAntimeridian` in `atlas.js` shift
  each ring's own longitudes by whatever multiple of 360 keeps consecutive
  points close together before the ring is projected; sin/cos are
  periodic, so this changes nothing about where any individual ring ends
  up, only that it stays continuous with itself.
- The old Mercator-era `maxBounds` (a lat/lng rectangle meant to keep
  panning within North America) reinterpreted under the new projection
  clamped the initial view to the wrong location entirely. It has been
  removed rather than reworked; panning is currently unrestricted aside
  from `minZoom`. A proper replacement (bounds expressed in the projected
  plane, or a smaller/differently-shaped lat/lng region) is a reasonable
  follow-up if unrestricted panning proves annoying in practice.

Verified in-browser: pan/zoom, territory hover/selection/tooltips, the
details panel (including the flag and wiki-author additions above), the
`?edit=1` polygon editor (Leaflet-Geoman draw/select still lands exactly
where clicked), and mobile touch panning/tap-select.

## Alpha banner and Realms colouring (8 September 2026)

The page now opens with a red banner above the header flagging the map as
alpha and pointing shenanigans, shekanery and tomfoolery at Vincent. It's a
plain flex child of `body`, styled in `atlas.css` (`#alpha-banner`); remove
it and its `<div>` in `index.html` once the atlas leaves alpha.

The map also now opens in **Realms** view by default: instead of colouring
each canon territory individually, the 13 rebelling colonies (`alliance:
"union"` in `territories.geojson`) shade from pale to deep blue
north-to-south, and English Canada (`alliance: "crown"`) is a single red --
the two sides of the Revolutionary War the atlas' subtitle describes. Every
other provisional (non-canon) territory is recoloured to a near-parchment
pale so the alliance colours read clearly against the pale interior; canon
territories outside both alliances (Florida, Smokey March, the Sidennic
League) keep their own individual colours in Realms view. The shades
themselves are generated at runtime via a small HSL-to-hex helper rather
than stored per feature, so adding or reordering `union` states only means
editing the `UNION_ORDER` list in `atlas.js`.

The "Map mode" radio group in the map key (`input[name=mapmode]` in
`atlas.js`) switches between **Realms** (the alliance colouring above) and
**Cultures**, which shows each canon territory's own reference colour
instead -- how heritage and origin were already encoded when the map was
first traced. Switching modes re-styles every layer and its tooltip in
place, without reloading data. Provisional territories are always shown
almost blank (very low fill and stroke opacity against the near-parchment
pale) regardless of mode.

## Fixed a stale-cache blank-map bug (8 September 2026)

Shortly after the mode-selector change above shipped, the live atlas loaded
with the header and map key intact but a completely blank map area -- no
land, borders or rivers at all. The cause: `index.html` and `atlas.js` are
two separate cacheable requests, referenced by plain filename with no
version or hash. A visitor (or an intermediate cache) can end up with a
fresh copy of one and a stale copy of the other. In this case, an old
`atlas.js` still ran `$('reset').onclick = home` for the "Full map" button
that a newer `index.html` had already removed; `$('reset')` was `null`,
the assignment threw, and since that line ran near the top of the script's
single synchronous pass, everything after it -- including the call to
`init()` that fetches and renders the map data -- never ran.

Two changes fix this:
- `index.html` now loads `atlas.css?v=3` and `atlas.js?v=3`. Bump that
  query string whenever either file changes so caches can't pair a stale
  copy of one with a fresh copy of the other.
- `atlas.js` now binds its optional controls (the panel toggle/close
  buttons, the layer checkboxes, the editor form and export button)
  through a small `on(id, event, handler)` helper that checks the element
  exists first. A missing element now logs a console error and disables
  just that one control instead of throwing and aborting the whole script
  before the map data ever loads. Core structural lookups (`#map`,
  `#panel`, `#details`, and the like) are unchanged, since if those are
  missing the page has bigger problems than a script error.

## City markers (8 September 2026)

The atlas now plots national capitals, state/province/admin-1 capitals,
and two population bands of other cities across the US, Canada and
Mexico -- the same real-world-placeholder approach as the real-state
border placeholders: locations and names are real, standing in until
in-world capitals and settlements are canon.

`scripts/extract-cities.py` reads `sources/natural-earth-populated-places.geojson`
(Natural Earth 1:10m populated places, pre-filtered to the three
countries) and writes `data/cities.geojson`, a `FeatureCollection` of
`Point`s. Each feature's `properties` are `name`, `tier`
(`capital`/`province`/`metro`/`city`), `country`, `admin1` (state/province
name, `null` for national capitals) and `population`. `tier` comes from
Natural Earth's `FEATURECLA` (`Admin-0 capital`, `Admin-1 capital`) for
the two capital tiers; the remaining `Populated place` records split into
`metro` (population >= 500,000) and `city` (150,000-500,000) -- smaller
places are left out to keep the closest zoom readable rather than solid
with dots. Re-run the script after editing the thresholds or source data;
it's idempotent and safe to run repeatedly.

In `atlas.js`, `CITY_TIERS` maps each tier to a `minZoom`, a marker radius
and a stroke/fill colour -- capitals are a larger gold dot, the other
three tiers step down in size through the ink/parchment palette. Each
tier lives in its own `L.layerGroup` (`cityTierGroups`), added to or
removed from the map as `map.getZoom()` crosses that tier's `minZoom` (on
`zoomend`, via `updateCityTiers()`) -- national capitals always show,
state/province capitals appear at the default zoom, and the two city
bands reveal only once zoomed in further. This add/remove-the-whole-group
approach (the same one already used for the countries/regions/rivers
checkboxes) keeps the DOM light when zoomed out rather than creating all
~330 markers up front and toggling per-marker visibility. The "Cities"
checkbox in the map key (`#cities`) turns the whole layer off regardless
of zoom. Markers use Leaflet's default marker pane, which already renders
above the `countries`/`regions` panes, so no new pane was needed. Hovering
a marker opens a tooltip reusing the `.territory-tooltip` styling (name,
then "National capital of `<country>`", "Capital of `<admin1>`,
`<country>`", or just "`<admin1>`, `<country>`" for the two city bands);
cities aren't otherwise selectable and don't open the details panel.

## SEO metadata and flag link fix (9 September 2026)

The page now ships a real title (`American Kingdoms Alt-History Map | A
Medieval America in 1377 A.D.`), a description, a canonical link and Open
Graph/Twitter tags in `index.html`, reusing the main site's
`washington-throne.jpg` for the social preview image since the atlas has no
dedicated hero art of its own. `robots` was changed from `noindex` to
`index, follow` to make the page discoverable now that it has real metadata;
the earlier notes in this file about keeping `noindex` no longer apply.

The details panel's "Purchase a flag on Flagmaker & Print" link was also
pointed at the current `https://flagmaker-print.com/collections/alt-history-flags`
collection URL (it previously used a stale `-kcc` suffixed URL).

## Renamed to medieval-america-map, and selection colour (9 September 2026)

The directory (and its served path) moved from `ak-map-alpha/` to
`medieval-america-map/`, so the page is now published at
`https://american-kingdoms.com/medieval-america-map/`; the `canonical` and
`og:url` tags, the main site's nav link and its new Discover More card, and
every script's `ROOT`/docstring path were updated to match. "Alpha" was
dropped from every user-facing label this touched (the nav link now just
reads "World Map"), but the `#alpha-banner` element and its "Map is
currently in alpha state" text are unchanged -- the map is still alpha
software, just no longer labelled that way in the URL or navigation.

A root-level `_redirects` file (Cloudflare Pages' Netlify-style redirects
config) 301s the old `/ak-map-alpha` and `/ak-map-alpha/*` paths to
`/medieval-america-map/` and `/medieval-america-map/:splat` respectively,
so old links and bookmarks keep working.

Text selection on the page defaulted to the browser's blue highlight since
nothing here set `::selection`. `atlas.css` now styles it with the same
`var(--red)` on cream (`#f5f1dc`) used by the main site's `::selection`
rule, and its cache-busting query string was bumped to `atlas.css?v=7`.
