import assert from "node:assert/strict";
import test from "node:test";
import { getMessages, MESSAGES } from "../lib/messages.ts";

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
