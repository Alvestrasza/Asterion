// Read-only smoke checks for an isolated local production server with OIDC and test mode disabled.
import assert from "node:assert/strict";

const base = new URL(process.argv[2] ?? "http://127.0.0.1:3000");
assert.ok(["127.0.0.1", "localhost", "[::1]"].includes(base.hostname), "Use a loopback test server only");
assert.ok(["http:", "https:"].includes(base.protocol));
assert.equal(base.username + base.password, "", "Do not put credentials in the URL");

async function page(path, headers = {}) {
  const response = await fetch(new URL(path, base), { headers, redirect: "manual" });
  return { response, html: await response.text() };
}

for (const [acceptLanguage, cookie, expected] of [
  ["de-DE,de;q=0.9,en;q=0.8", "", "de"],
  ["en-GB", "", "en"],
  ["fr-CA,fr;q=0.9", "", "fr"],
  ["es-MX", "", "es"],
  ["ja-JP", "", "en"],
  ["de-DE", "asterion-locale=fr", "fr"]
]) {
  const { response, html } = await page("/", { "Accept-Language": acceptLanguage, Cookie: cookie });
  assert.equal(response.status, 200);
  assert.match(html, new RegExp(`<html[^>]*lang="${expected}"`));
  assert.match(html, /<h1[^>]*id="hero-title"/);
  assert.match(html, /<meta name="description" content="[^"]+"/);
  assert.match(html, /href="\/care"/);
  assert.match(response.headers.get("cache-control") ?? "", /private|no-store/);
  console.log(`PASS public page: ${acceptLanguage}, preference=${cookie || "none"} -> ${expected}`);
}

const login = await page("/login", { "Accept-Language": "en" });
assert.equal(login.response.status, 200);
assert.match(login.html, /<html[^>]*lang="en"/);
assert.match(login.html, /Sign-in is not available yet/);
assert.doesNotMatch(login.html, /class="login-button"/);
assert.match(login.html, /noindex/);
console.log("PASS missing-provider login: explanatory message, no unusable sign-in button");

const care = await page("/care");
const destination = care.response.headers.get("location");
assert.ok(
  ([307, 308].includes(care.response.status) && destination === "/login") ||
  (care.response.status === 200 && /<meta[^>]+http-equiv="refresh"[^>]+content="[01];url=\/login"/.test(care.html)),
  "An anonymous care request must redirect to login, including a streamed Next.js redirect"
);
console.log("PASS anonymous care route: login required");
