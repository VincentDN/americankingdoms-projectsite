# americankingdoms-projectsite
The project website for https://american-kingdoms.com/

## Newsletter signup

The email box in the Connect section posts to `/api/subscribe`, a Cloudflare
Pages Function (`functions/api/subscribe.js`) that subscribes the address to
Shopify Mail by setting marketing consent on the matching Shopify customer via
the Shopify Admin GraphQL API. No email addresses are stored in this repo or
on Cloudflare; Shopify remains the only list.

The timed `#newsletterModal` popup and the hero/dev-diaries "Join the
Newsletter" links still point to `kaisercatcinema.com/newsletter`; they were
left as-is and can be pointed at the inline form later if wanted.

This requires two secrets set on the Cloudflare Pages project (Settings →
Environment variables), never committed to the repo:

- `SHOPIFY_STORE_DOMAIN` — e.g. `kaisercatcinema.myshopify.com`
- `SHOPIFY_ADMIN_API_TOKEN` — an Admin API access token from a custom app in
  the KCC Shopify admin, with the `read_customers` and `write_customers`
  scopes.

See `.dev.vars.example` for local development with `wrangler pages dev`.
