#!/usr/bin/env python3
"""Extract a tiered placeholder city dataset for the US, Canada and Mexico.

Reads Natural Earth 1:10m populated places (public domain) and writes
data/cities.geojson: national capitals, state/province/admin-1 capitals,
and two population bands of other cities, each tagged with a `tier` used
by atlas.js to show or hide them by zoom level. Real-world names and
locations are a visual placeholder, the same way the real-state border
placeholders are -- not in-world canon.

Usage: python3 medieval-america-map/scripts/extract-cities.py
Input:  medieval-america-map/sources/natural-earth-populated-places.geojson -- the US,
        Canada and Mexico features (ISO_A2 US/CA/MX) from Natural Earth 1:10m
        populated places (ne_10m_populated_places.geojson), downloaded from
        https://github.com/nvkelso/natural-earth-vector/tree/master/geojson
        on 8 September 2026 and pre-filtered to those three countries so the
        committed source stays a few megabytes instead of the ~19MB global
        file. Re-filter with e.g.
        `jq '.features |= map(select(.properties.ISO_A2 as $c | ["US","CA","MX"] | index($c)))'`
        if the full file is ever needed again.
Output: medieval-america-map/data/cities.geojson
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'sources' / 'natural-earth-populated-places.geojson'
OUTPUT = ROOT / 'data' / 'cities.geojson'

COUNTRIES = {'US', 'CA', 'MX'}
# Non-capital population bands, most-populous tier first.
BANDS = [('metro', 500_000), ('city', 150_000)]


def clean_name(props):
    name = props.get('NAME') or props.get('NAMEASCII') or ''
    return re.sub(r'\s+', ' ', name).strip()


def classify(props):
    if props['FEATURECLA'] == 'Admin-0 capital':
        return 'capital'
    if props['FEATURECLA'] == 'Admin-1 capital':
        return 'province'
    if props['FEATURECLA'] == 'Populated place':
        pop = props.get('POP_MAX') or 0
        for tier, threshold in BANDS:
            if pop >= threshold:
                return tier
    return None


def main():
    source = json.loads(SOURCE.read_text())
    features = []
    for f in source['features']:
        p = f['properties']
        if p.get('ISO_A2') not in COUNTRIES:
            continue
        tier = classify(p)
        if tier is None:
            continue
        name = clean_name(p)
        if not name:
            continue
        features.append({
            'type': 'Feature',
            'properties': {
                'name': name,
                'tier': tier,
                'country': p.get('ADM0NAME'),
                'admin1': p.get('ADM1NAME') or None,
                'population': int(p['POP_MAX']) if p.get('POP_MAX') else None,
            },
            'geometry': {
                'type': 'Point',
                'coordinates': [p['LONGITUDE'], p['LATITUDE']],
            },
        })

    tier_order = {'capital': 0, 'province': 1, 'metro': 2, 'city': 3}
    features.sort(key=lambda f: (tier_order[f['properties']['tier']], f['properties']['name']))

    counts = {}
    for f in features:
        counts[f['properties']['tier']] = counts.get(f['properties']['tier'], 0) + 1
    print('Cities by tier:', counts, '- total', len(features))

    OUTPUT.write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, separators=(',', ':')))
    print('Wrote', OUTPUT)


if __name__ == '__main__':
    main()
