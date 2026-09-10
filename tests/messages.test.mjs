import assert from "node:assert/strict";
import test from "node:test";
import { getMessages, MESSAGES } from "../lib/messages.ts";
import { readFile } from "node:fs/promises";

const locales = ["de", "en", "fr", "es"];
const companionKinds = ["asterion", "rabbit", "cat", "orc", "pony", "fairy", "dog", "elf"];

function messageLeaves(value, prefix = "") {
  return Object.entries(value).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof child === "object" && child !== null
      ? messageLeaves(child, path)
      : [[path, child]];
  });
}

function placeholders(value) {
  return [...value.matchAll(/\{[A-Za-z][A-Za-z0-9_]*\}/g)].map(([match]) => match).sort();
}

test("the public message catalog includes precisely the four supported languages", () => {
  assert.deepEqual(Object.keys(MESSAGES).sort(), [...locales].sort());
  for (const locale of locales) assert.equal(getMessages(locale), MESSAGES[locale]);
});

test("every language has the same complete message structure and nonempty text", () => {
  const reference = messageLeaves(MESSAGES.en);
  assert.deepEqual(Object.keys(MESSAGES.en).sort(), [
    "meta", "nav", "hero", "about", "gallery", "companions", "roadmap", "footer", "login", "care", "errors"
  ].sort());

  for (const locale of locales) {
    const leaves = messageLeaves(MESSAGES[locale]);
    assert.deepEqual(leaves.map(([path]) => path).sort(), reference.map(([path]) => path).sort(), locale);
    for (const [path, value] of leaves) {
      assert.equal(typeof value, "string", `${locale}.${path}`);
      assert.ok(value.trim().length > 0, `${locale}.${path} must not be empty`);
      assert.equal(value, value.trim(), `${locale}.${path} has surrounding whitespace`);
      assert.doesNotMatch(value, /\b(?:TODO|TBD|FIXME)\b/, `${locale}.${path} is unfinished`);
    }
  }
});

test("each of the eight companions has a translated species, introduction and image description", () => {
  for (const locale of locales) {
    assert.deepEqual(Object.keys(MESSAGES[locale].companions).sort(), [...companionKinds].sort(), locale);
    for (const kind of companionKinds) {
      assert.deepEqual(Object.keys(MESSAGES[locale].companions[kind]).sort(), ["species", "description", "alt"].sort());
    }
  }
});

test("translations preserve interpolation placeholders", () => {
  const reference = new Map(messageLeaves(MESSAGES.en));
  for (const locale of locales) {
    for (const [path, value] of messageLeaves(MESSAGES[locale])) {
      assert.deepEqual(placeholders(value), placeholders(reference.get(path)), `${locale}.${path}`);
    }
  }
});

test("public copy describes immediate onboarding without a manual approval requirement", () => {
  for (const locale of locales) {
    const t = MESSAGES[locale];
    assert.ok(t.hero.description.length <= 200, locale);
    assert.ok(t.hero.note.length <= 100, locale);
    assert.ok(t.login.title.length <= 40, locale);
    assert.ok(t.login.description.length <= 150, locale);
    assert.doesNotMatch(t.hero.description + t.login.description, /prototype|Prototyp|prototipo|universum|universe|univers /i);
  }
  assert.match(MESSAGES.de.login.register, /Konto erstellen/);
  assert.match(MESSAGES.en.login.register, /Create account/);
  for (const locale of locales) {
    assert.equal("apply" in MESSAGES[locale].nav, false);
    assert.doesNotMatch(MESSAGES[locale].hero.note + MESSAGES[locale].footer.status, /Freigabe|freigeschaltet|approved|approval|approuvé|aprobada|aprobación/);
  }
});

test("the landing page does not market unfinished diary, chat or progression features", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(page, /t\.roadmap|href="#roadmap"/);
  assert.match(page, /t\.hero\.note/);
  assert.match(page, /t\.footer\.status/);
});
