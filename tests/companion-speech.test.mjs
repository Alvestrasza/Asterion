import test from "node:test";
import assert from "node:assert/strict";

import { COMPANION_KINDS } from "../lib/companions.ts";
import {
  SPEECH_CONTEXTS,
  SPEECH_VERSION,
  avoidRepeatedSpeechKey,
  chooseSpeechKey,
  careSpeechContext,
  renderSpeech,
  speechForMood,
  moodLabel
} from "../lib/companion-speech.ts";

const locales = ["de", "en", "fr", "es"];

test("versioned speech covers every companion, context and locale with two stable alternatives", () => {
  assert.equal(SPEECH_VERSION, 1);
  for (const locale of locales) for (const kind of COMPANION_KINDS) for (const context of SPEECH_CONTEXTS) {
    const first = renderSpeech(`v1.${kind}.${context}.0`, locale, { level: 15 });
    const second = renderSpeech(`v1.${kind}.${context}.1`, locale, { level: 15 });
    assert.ok(typeof first === "string" && first.length > 8, `${locale}/${kind}/${context}/0`);
    assert.ok(typeof second === "string" && second.length > 8, `${locale}/${kind}/${context}/1`);
    assert.notEqual(first, second, `${locale}/${kind}/${context}`);
    assert.ok(first.length <= 180 && second.length <= 180, `${locale}/${kind}/${context} must fit a small screen`);
    assert.doesNotMatch(first + second, /\{(?:name|level)\}/);
  }
});

test("speech uses the selected identity and never falls back to a fixed masculine pronoun", () => {
  for (const locale of locales) {
    const rabbit = renderSpeech("v1.rabbit.pet.0", locale);
    const orc = renderSpeech("v1.orc.pet.0", locale);
    assert.notEqual(rabbit, orc);
    assert.ok(rabbit.includes("Liora"));
    assert.ok(orc.includes("Brumo"));
    assert.ok(moodLabel("lonely", locale).length > 0);
    assert.ok(speechForMood("hungry", "fairy", locale, "pet-fairy").includes("Selya"));
  }
});

test("keys remain stable under retries and invalid keys never interpolate untrusted text", () => {
  const first = chooseSpeechKey("cat", "play", "pet-1:request-1");
  assert.equal(first, chooseSpeechKey("cat", "play", "pet-1:request-1"));
  assert.match(first, /^v1\.cat\.play\.[01]$/);
  assert.notEqual(avoidRepeatedSpeechKey(first, first), first);
  assert.equal(avoidRepeatedSpeechKey(first, null), first);
  assert.equal(renderSpeech("v1.cat.play.3", "en"), null);
  assert.equal(renderSpeech("v1.cat.unknown.0", "en"), null);
  assert.equal(renderSpeech("v1.cat.levelUp.0", "en", { level: "<script>" }), null);
  assert.equal(renderSpeech("v1.cat.play.0", "xx"), renderSpeech("v1.cat.play.0", "en"));
  assert.equal(careSpeechContext("feed", false, false), "satisfied");
  assert.equal(careSpeechContext("play", false, true), "resting");
  assert.equal(careSpeechContext("wake", false, false), "alreadyAwake");
});
