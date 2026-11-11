import { catalogueFallback } from "./_lib/catalogue-fallback.js";

/**
 * Corre em todos os pedidos da loja: domínio canónico, bloqueio de caminhos sensíveis, as páginas do catálogo que o
 * build não gerou (RP-04) e os cabeçalhos de segurança.
 *
 * Block sensitive path probes on Cloudflare Pages (SPA otherwise returns index.html).
 */
const BLOCK = [
  /^\/\.env(?:$|\.)/i,
  /^\/\.git(?:$|\/)/i,
  /^\/package(?:-lock)?\.json$/i,
  /^\/vite\.config\./i,
  /^\/src(?:$|\/)/i,
  /^\/backend-api(?:$|\/)/i,
  /^\/\.github(?:$|\/)/i,
  /^\/node_modules(?:$|\/)/i,
];

// Endereços antigos que a loja ainda recebe (o alias /contact do router, o /produtos/<categoria> de antes de
// /categoria/<categoria>). Redireccionam-se aqui, e não em `_redirects`: o Pages não aplica o `_redirects` aos pedidos
// que passam pelas Functions, e este middleware corre em todos os pedidos da loja (FE-04).
function legacyRedirect(path) {
  if (/^\/contact\/?$/.test(path)) return "/contacto";
  const category = /^\/produtos\/([^/]+)\/?$/.exec(path);
  return category ? `/categoria/${category[1]}` : null;
}

// Domínio canónico: diomika.com (sem www) → https://www.diomika.com, mesmo caminho.
const CANONICAL_HOST = "www.diomika.com";
const REDIRECT_HOSTS = new Set(["diomika.com"]);

const CSP =
  "default-src 'self'; script-src 'self' https://challenges.cloudflare.com; script-src-elem 'self' https://challenges.cloudflare.com; connect-src 'self' https://your-project-ref.supabase.co https://challenges.cloudflare.com https://api.diomika.com https://*.i.posthog.com; img-src 'self' data: blob: https://your-project-ref.supabase.co; style-src 'self'; frame-src https://challenges.cloudflare.com; font-src 'self' data:; base-uri 'self'; form-action 'self'; object-src 'none'; frame-ancestors 'none'; upgrade-insecure-requests";

function securityHeaders() {
  return {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()",
    // Igual a public/_headers.production (deploy/verify_csp.py garante). Inclui o
    // Turnstile: sem ele os formulários de contacto e orçamento deixam de funcionar.
    "Content-Security-Policy": CSP,
  };
}

export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (REDIRECT_HOSTS.has(url.hostname)) {
    url.hostname = CANONICAL_HOST;
    url.protocol = "https:";
    return Response.redirect(url.toString(), 301);
  }
  const path = url.pathname;
  const moved = legacyRedirect(path);
  if (moved) {
    url.pathname = moved;
    return Response.redirect(url.toString(), 301);
  }
  if (BLOCK.some((re) => re.test(path))) {
    return new Response("Not Found", {
      status: 404,
      headers: {
        "content-type": "text/plain; charset=utf-8",
        "cache-control": "no-store",
        ...securityHeaders(),
      },
    });
  }
  let response = await context.next();
  // O Pages não achou o ficheiro (404): se for uma página do catálogo que existe mas o build não gerou, serve-se a loja.
  if (response.status === 404) response = (await catalogueFallback(context, url)) ?? response;
  const headers = new Headers(response.headers);
  Object.entries(securityHeaders()).forEach(([key, value]) => {
    headers.set(key, value);
  });
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}
