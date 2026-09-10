// Run against an isolated production-build preview, never a live deployment.
import assert from "node:assert/strict";
const origin = process.env.ASTERION_TEST_ORIGIN ?? "http://127.0.0.1:3188";
assert.match(origin, /^http:\/\/127\.0\.0\.1:\d+$/);
const request = (path, headers = {}) => fetch(`${origin}${path}`, { headers, redirect: "manual", signal: AbortSignal.timeout(10_000) });
for (const locale of ["de", "en", "fr", "es"]) {
  for (const path of ["", "/login"]) {
    const response = await request(`/${locale}${path}`, { "Accept-Language": "ja", "x-asterion-locale": "en", Cookie: "asterion-locale=en" });
    assert.equal(response.status, 200, `${locale}${path}`);
    const html = await response.text();
    assert.match(html, new RegExp(`<html[^>]+lang="${locale}"`));
    assert.doesNotMatch(html, /Übernehmen|>Apply<|>Appliquer<|>Aplicar</);
    assert.doesNotMatch(html, /x-middleware-rewrite/);
    if (path === "/login") {
      const label = { de: "Konto erstellen", en: "Create account", fr: "Créer un compte", es: "Crear cuenta" }[locale];
      assert.ok(html.includes(label));
      assert.match(html, /type="submit"/);
    } else assert.ok(html.includes(`href="/${locale}/login"`));
  }
  const redirect = await request("/login?error=AccessDenied", { "Accept-Language": `${locale};q=1` });
  assert.equal(redirect.status, 307);
  assert.equal(new URL(redirect.headers.get("location"), origin).pathname, `/${locale}/login`);
  assert.equal(new URL(redirect.headers.get("location"), origin).search, "?error=AccessDenied");
  for (const path of ["/api/internal/access-sync", "/api/auth/signin", "/api/friends"]) {
    assert.equal((await request(`/${locale}${path}`)).status, 404);
  }
}
assert.equal(new URL((await request("/", { "Accept-Language": "ja" })).headers.get("location"), origin).pathname, "/en");
assert.equal(new URL((await request("/", { "Accept-Language": "fr", Cookie: "asterion-locale=es" })).headers.get("location"), origin).pathname, "/es");
const unsupported = await request("/it");
// Next.js may have started streaming before the locale layout calls notFound().
if (unsupported.status !== 404) {
  assert.equal(unsupported.status, 200);
  const html = await unsupported.text();
  assert.match(html, /NEXT_HTTP_ERROR_FALLBACK;404/);
  assert.match(html, /name="robots" content="noindex"/);
}
console.log("Localized production HTTP checks passed: four home/login routes, labels, locale precedence, query preservation, English fallback and no localized APIs.");
