# americankingdoms-projectsite
The project website for https://american-kingdoms.com/

## Roadmap notes (raise these next time we pick up site work)

- **Full interactive map, for both the AK site and the TDS site.** The
  current `/medieval-america-map/` atlas (this repo) is still alpha —
  see the dated entries in `medieval-america-map/README.md` for its
  current feature set and known follow-ups (panning bounds, label
  density, etc). TDS (The Divided States) is a separate sister site, not
  in this repo (`VincentDN/dividedstates-projectsite`); it now has a
  first alpha of its own at `/map-alpha/` (four-faction 1940 civil-war
  map, see that repo's `map-alpha/README.md`), orphaned and noindexed,
  with a provisional/unconfirmed state-to-faction border split. Worth
  scoping what "full interactive" means for each site long-term (zoom
  depth, submap coverage, mobile parity) rather than assuming either
  atlas's approach transfers directly to the other.
- **Every flag should be purchasable via a direct link to its Flagmaker
  product page**, not just the generic collection link. Right now every
  "Purchase a flag on Flagmaker & Print" link (main site, world atlas
  details panel, Massachusetts submap panel) points at the same
  `https://flagmaker-print.com/collections/alt-history-flags` collection
  URL regardless of which territory/flag is showing. Territories already
  carry a `flag` image path in `medieval-america-map/data/territories.geojson`;
  they'd need a matching Flagmaker product URL (new property, e.g.
  `flagShopUrl`) to link each territory's own flag straight to checkout
  instead of the collection page.

## Newsletter signup

The email box in the Connect section posts to `/api/subscribe`, a Cloudflare
Pages Function (`functions/api/subscribe.js`) that subscribes the address to
Shopify Mail by setting marketing consent on the matching Shopify customer via
the Shopify Admin GraphQL API. No email addresses are stored in this repo or
on Cloudflare; Shopify remains the only list.

The `#newsletterModal` popup (opened after 40s, or by clicking the footer
eagle) uses the same inline form. The hero and dev-diaries "Join the
Newsletter" links still point to `kaisercatcinema.com/newsletter`; they were
left as-is and can be pointed at the inline form later if wanted.

This requires four variables set on the Cloudflare Pages project (Settings →
Environment variables), never committed to the repo:

- `SHOPIFY_STORE_DOMAIN` (Text) — e.g. `kaisercatcinema.myshopify.com`
- `SHOPIFY_CLIENT_ID` and `SHOPIFY_CLIENT_SECRET` (Secret) — from the custom
  app's API credentials page in the Shopify Dev Dashboard, with the
  `read_customers` and `write_customers` Admin API scopes configured.
- `SHOPIFY_SOURCE_TAG` (Text) — `source:ak_projectsite` on this project. Every
  subscriber who signs up here gets tagged with this in Shopify, so you can
  filter/segment customers by which site brought them in.

Since January 1, 2026 Shopify custom apps no longer hand out a permanent
`shpat_` token — instead the Function exchanges the Client ID/Secret for a
short-lived (~24h) access token on every request via the `client_credentials`
OAuth grant.

See `.dev.vars.example` for local development with `wrangler pages dev`.
