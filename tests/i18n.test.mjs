import test from "node:test";
import assert from "node:assert/strict";
import { normalizeLocale, resolveLocale, languageReturnPath, languageCookieOptions } from "../lib/i18n.ts";

test("locale normalization supports regional tags but rejects unsupported input", () => {
  assert.equal(normalizeLocale("FR-ca"), "fr");
  assert.equal(normalizeLocale("es-MX"), "es");
  for (const input of [null, undefined, "", "ja", "english", "de<script>", "de_DE", ["de"]]) {
    assert.equal(normalizeLocale(input), null);
  }
});

test("saved manual language wins over browser preferences", () => {
  assert.equal(resolveLocale("es", "de-DE,de;q=0.9,en;q=0.8"), "es");
  assert.equal(resolveLocale("invalid", "fr-CA, en;q=0.8"), "fr");
});

test("browser languages use quality, stable priority, regions and English fallback", () => {
  assert.equal(resolveLocale(null, "de;q=0.3,fr-CA;q=0.9,en;q=0.7"), "fr");
  assert.equal(resolveLocale(null, "es-MX,fr;q=1"), "es");
  assert.equal(resolveLocale(null, "ja, en-GB;q=0.7"), "en");
  assert.equal(resolveLocale(null, "ja,zh;q=0.8"), "en");
  assert.equal(resolveLocale(null, null), "en");
  assert.equal(resolveLocale(null, ""), "en");
});

test("invalid qualities and excluded languages do not override a valid preference", () => {
  assert.equal(resolveLocale(null, "de;q=2,es;q=0.8"), "es");
  assert.equal(resolveLocale(null, "fr;q=no,de;q=0.5"), "de");
  assert.equal(resolveLocale(null, "de;q=0,fr;q=0.2"), "fr");
  assert.equal(resolveLocale(null, "en;q=0,*;q=0.5"), "de");
  assert.equal(resolveLocale(null, "de;q=0,*;q=0.9,en;q=0.8"), "fr");
  assert.equal(resolveLocale(null, "fr;q=0;foo=x,es;q=0.8"), "es");
});

test("language forms can only return to known local pages", () => {
  for (const path of ["/", "/login", "/care"]) assert.equal(languageReturnPath(path), path);
  for (const path of ["https://evil.invalid", "//evil.invalid", "/\\evil.invalid", "/api/auth/signout", "/care?next=bad", null]) {
    assert.equal(languageReturnPath(path), "/");
  }
});

test("preference cookies support isolated HTTP testing without weakening public HTTPS defaults", () => {
  assert.equal(languageCookieOptions(true, false).secure, true);
  assert.equal(languageCookieOptions(true, true).secure, false);
  assert.equal(languageCookieOptions(false, false).secure, false);
  assert.equal(languageCookieOptions(true, true).httpOnly, true);
  assert.equal(languageCookieOptions(true, false).sameSite, "lax");
});
