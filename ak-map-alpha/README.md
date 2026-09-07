# American Kingdoms atlas groundwork

Based on the existing project site's `main` at `f22b95f` (5 September 2026).
This is a standalone static page under `ak-map-alpha/`; the landing page is unchanged.

## Open and edit

Serve the repository with any static HTTP server and open `/ak-map-alpha/`.
Open `/ak-map-alpha/?edit=1` to draw polygons and edit their vertices using Leaflet-Geoman.
Select a polygon to change its name, colour, country/region layer, description and wiki URL.
Export before leaving: edits live only in the current tab, with an unload warning.
Replace `ak-map-alpha/data/territories.geojson` with the exported file and commit to publish an update.
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

Names and descriptions are rendered as text, not injected HTML.
Political geometry is traced from `sources/east-coast-canon.png` (authoritative)
and `sources/continental-outline.jpg` (provisional elsewhere). Massachusetts includes
the Maine territory shown in the reference; New Hampshire includes the Vermont area;
Smokey March remains separate. Florida follows the reference's northern territory,
with the uncoloured southern peninsula retained as provisional land.

The source images are rough, differently projected raster maps. Their pixel colours
were segmented and georeferenced using manually paired landmarks. The resulting
borders are editable approximations, not exact survey lines. Subpixel overlaps were
removed with the smaller territories taking precedence, and every provisional shape
was clipped around the canonical states. The images, original physical data and
reproduction script are preserved under `sources/` and `scripts/`.

To regenerate, install the Python dependencies listed at the top of
`scripts/trace-references.py`, download Natural Earth's
`ne_50m_admin_0_countries.geojson` from the same upstream GeoJSON directory cited
below, then run `python ak-map-alpha/scripts/trace-references.py /path/to/ne_50m_admin_0_countries.geojson`
from the repository root. This overwrites the generated map data; export and preserve
any later hand edits first. Admin-0 geometry is used only to clip the physical extent
to North America through Panama, not as the fictional political boundaries.

`canon`, `claim`, `source` and `boundaryStatus` properties preserve reference provenance.
Ownership labels describe the supplied reference, not independently verified current claims.
Lake polygons are excluded from territory fills. South America is removed from all
displayed background layers, and the viewport is bounded to the setting's extent.
The physical base has no modern political borders or city labels.

## Hosting at map.american-kingdoms.com

Deploy the **contents of `ak-map-alpha/`** as the root of a separate static hosting project.
No build command, API key, paid tile provider, or backend is required.
Relative asset paths work both at `/ak-map-alpha/` and at the subdomain root.
In that project's hosting dashboard, add `map.american-kingdoms.com` as its custom
domain, then use the provider's exact DNS target and finish TLS verification.
The repository does not establish which provider currently controls deployment or DNS;
do not guess a CNAME target or change the existing apex domain configuration.
Keep the current `noindex` metadata until approved canonical content is ready.
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
- Existing American Kingdoms logo, colours, Cinzel / Ysabeau / EB Garamond typography.
  Fonts are requested from Google Fonts, with local serif/sans fallbacks.

The 1:50m base is suitable for the first continental view, not detailed fief boundaries
or navigational accuracy. Upgrade to 1:10m geography, spatially clipped and simplified
at multiple zoom levels, when closer-scale canon is available. The current renderer
uses Mercator; a custom continental projection is a later cartographic decision.

## Verification

JavaScript syntax, GeoJSON parsing, local HTML asset references, polygon validity,
territory overlap and southern-extent checks were run. A static geometry plot was
inspected against the supplied East Coast reference. Browser interaction and browser
visual QA have not yet been performed.
Before launch, check desktop hover, keyboard selection, mobile pan/pinch, border
drawing/editing/deletion, export-and-reload, and rendering at the subdomain root.

## Cloudflare Pages live alpha

The alpha is served at `/ak-map-alpha/` by the existing production Pages project
through its GitHub integration. It has no navigation link on the main site and
retains `noindex` metadata. Publication uses the existing `main` branch; no DNS
change, separate Pages project or new domain is needed.

## Shared-border and interior-region update (7 September 2026)

Run `python ak-map-alpha/scripts/refine-territories.py` after the initial trace
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

Run `python ak-map-alpha/scripts/apply-real-state-placeholders.py` after
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
