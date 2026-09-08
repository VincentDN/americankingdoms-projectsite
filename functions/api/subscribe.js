// Cloudflare Pages Function: POST /api/subscribe
// Subscribes an email to Shopify Mail (marketing consent on the Shopify customer record)
// via the Shopify Admin GraphQL API, so the newsletter form can live on this static site
// while KCC keeps sending from Shopify. Also tags the customer with which site they
// signed up from, so subscribers can be filtered/segmented by source in Shopify.
//
// Since January 1, 2026 Shopify custom apps (created via the Dev Dashboard) no longer
// hand out a permanent Admin API token. Instead we exchange a Client ID + Client Secret
// for a short-lived (~24h) access token on every request, via the client_credentials
// OAuth grant.
//
// Required Pages project environment variables (set as secrets, not committed):
//   SHOPIFY_STORE_DOMAIN     e.g. "kaisercatcinema.myshopify.com"
//   SHOPIFY_CLIENT_ID        Client ID from the app's API credentials page
//   SHOPIFY_CLIENT_SECRET    Client secret from the app's API credentials page
//                            (the app needs the `write_customers` and `read_customers`
//                            Admin API scopes)
//   SHOPIFY_SOURCE_TAG       e.g. "source:ak_projectsite" or "source:tds_projectsite"
//                            (plain text, not secret) — applied to every subscriber
//                            via this site. Optional: tagging is skipped if unset.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SHOPIFY_API_VERSION = '2024-10';

export async function onRequestPost({ request, env }) {
  let email = '';
  let honeypot = '';

  try {
    const contentType = request.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const body = await request.json();
      email = String(body.email || '');
      honeypot = String(body.company || '');
    } else {
      const form = await request.formData();
      email = String(form.get('email') || '');
      honeypot = String(form.get('company') || '');
    }
  } catch (err) {
    return jsonResponse({ ok: false, error: 'Invalid request.' }, 400);
  }

  // Honeypot field: real visitors never fill it in. Report success so bots
  // don't learn the field is a trap, without actually subscribing anything.
  if (honeypot) {
    return jsonResponse({ ok: true });
  }

  email = email.trim().toLowerCase();
  if (!EMAIL_RE.test(email)) {
    return jsonResponse({ ok: false, error: 'Please enter a valid email address.' }, 400);
  }

  const shop = env.SHOPIFY_STORE_DOMAIN;
  const clientId = env.SHOPIFY_CLIENT_ID;
  const clientSecret = env.SHOPIFY_CLIENT_SECRET;
  if (!shop || !clientId || !clientSecret) {
    return jsonResponse({ ok: false, error: 'Newsletter signup is not configured yet.' }, 500);
  }

  try {
    const token = await getAccessToken(shop, clientId, clientSecret);
    await subscribeCustomer(shop, token, email, env.SHOPIFY_SOURCE_TAG);
    return jsonResponse({ ok: true });
  } catch (err) {
    return jsonResponse({ ok: false, error: 'Something went wrong. Please try again later.' }, 502);
  }
}

// Client credentials grant: exchange the app's Client ID + Secret for a
// short-lived Admin API access token. Tokens are valid ~24h; at this
// signup volume it's simplest to fetch a fresh one on every request
// rather than cache it.
async function getAccessToken(shop, clientId, clientSecret) {
  const res = await fetch(`https://${shop}/admin/oauth/access_token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'client_credentials',
      client_id: clientId,
      client_secret: clientSecret,
    }),
  });
  const data = await res.json();
  if (!res.ok || !data.access_token) {
    throw new Error('Failed to obtain Shopify access token: ' + JSON.stringify(data));
  }
  return data.access_token;
}

async function shopifyGraphQL(shop, token, query, variables) {
  const res = await fetch(`https://${shop}/admin/api/${SHOPIFY_API_VERSION}/graphql.json`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Shopify-Access-Token': token,
    },
    body: JSON.stringify({ query, variables }),
  });
  const data = await res.json();
  if (!res.ok || data.errors) {
    throw new Error(JSON.stringify(data.errors || data));
  }
  return data.data;
}

// Shopify has no "upsert" customer mutation, so look the email up first and
// either update its marketing consent or create a new customer with it.
// Tagging is applied afterwards via tagsAdd, which merges into the existing
// tag set instead of replacing it (unlike passing `tags` on customerUpdate).
async function subscribeCustomer(shop, token, email, sourceTag) {
  const findQuery = `
    query FindCustomer($query: String!) {
      customers(first: 1, query: $query) {
        edges { node { id } }
      }
    }
  `;
  const found = await shopifyGraphQL(shop, token, findQuery, { query: `email:"${email}"` });
  const existingId = found.customers.edges[0]?.node?.id;

  const consent = { marketingState: 'SUBSCRIBED', marketingOptInLevel: 'SINGLE_OPT_IN' };
  let customerId = existingId;

  if (existingId) {
    const updateMutation = `
      mutation UpdateConsent($input: CustomerInput!) {
        customerUpdate(input: $input) {
          userErrors { field message }
        }
      }
    `;
    const result = await shopifyGraphQL(shop, token, updateMutation, {
      input: { id: existingId, emailMarketingConsent: consent },
    });
    if (result.customerUpdate.userErrors.length) {
      throw new Error(JSON.stringify(result.customerUpdate.userErrors));
    }
  } else {
    const createMutation = `
      mutation CreateCustomer($input: CustomerInput!) {
        customerCreate(input: $input) {
          customer { id }
          userErrors { field message }
        }
      }
    `;
    const result = await shopifyGraphQL(shop, token, createMutation, {
      input: { email, emailMarketingConsent: consent },
    });
    if (result.customerCreate.userErrors.length) {
      throw new Error(JSON.stringify(result.customerCreate.userErrors));
    }
    customerId = result.customerCreate.customer.id;
  }

  if (sourceTag && customerId) {
    const tagsAddMutation = `
      mutation AddSourceTag($id: ID!, $tags: [String!]!) {
        tagsAdd(id: $id, tags: $tags) {
          userErrors { field message }
        }
      }
    `;
    const result = await shopifyGraphQL(shop, token, tagsAddMutation, {
      id: customerId,
      tags: [sourceTag],
    });
    if (result.tagsAdd.userErrors.length) {
      throw new Error(JSON.stringify(result.tagsAdd.userErrors));
    }
  }
}

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
