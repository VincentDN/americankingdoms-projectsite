// Cloudflare Pages Function: POST /api/subscribe
// Subscribes an email to Shopify Mail (marketing consent on the Shopify customer record)
// via the Shopify Admin GraphQL API, so the newsletter form can live on this static site
// while KCC keeps sending from Shopify.
//
// Required Pages project environment variables (set as secrets, not committed):
//   SHOPIFY_STORE_DOMAIN     e.g. "kaisercatcinema.myshopify.com"
//   SHOPIFY_ADMIN_API_TOKEN  Admin API access token from a custom app with the
//                            `write_customers` and `read_customers` scopes.

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
  const token = env.SHOPIFY_ADMIN_API_TOKEN;
  if (!shop || !token) {
    return jsonResponse({ ok: false, error: 'Newsletter signup is not configured yet.' }, 500);
  }

  try {
    await subscribeCustomer(shop, token, email);
    return jsonResponse({ ok: true });
  } catch (err) {
    return jsonResponse({ ok: false, error: 'Something went wrong. Please try again later.' }, 502);
  }
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
async function subscribeCustomer(shop, token, email) {
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
    return;
  }

  const createMutation = `
    mutation CreateCustomer($input: CustomerInput!) {
      customerCreate(input: $input) {
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
}

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
