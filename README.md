# americankingdoms-projectsite
The project website for https://american-kingdoms.com/

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
