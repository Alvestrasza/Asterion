import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import vm from "node:vm";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import * as atlas from "../lib/animation-atlas.ts";

// Read original GIF timing records, independently from the application timeline.
function gifDelays(data) {
  assert.match(data.toString("ascii", 0, 6), /^GIF8[79]a$/);
  let offset = 13 + (data[10] & 128 ? 3 * 2 ** ((data[10] & 7) + 1) : 0);
  let delay = 0;
  const delays = [];
  function skipBlocks() { while (data[offset]) offset += data[offset] + 1; offset++; }
  while (offset < data.length) {
    const marker = data[offset++];
    if (marker === 0x3b) break;
    if (marker === 0x21) {
      const extension = data[offset++];
      if (extension === 0xf9) delay = data.readUInt16LE(offset + 2) * 10;
      skipBlocks();
    } else if (marker === 0x2c) {
      const packed = data[offset + 8];
      offset += 9 + (packed & 128 ? 3 * 2 ** ((packed & 7) + 1) : 0);
      offset++; // LZW minimum code size
      skipBlocks();
      delays.push(delay);
    } else throw new Error(`Unexpected GIF block ${marker}`);
  }
  return delays;
}

test("all existing animation frames and their original nonuniform GIF delays are retained", async () => {
  const rows = { idle: 0, "running-right": 1, "running-left": 2, waving: 3, jumping: 4, failed: 5, waiting: 6, running: 7, review: 8 };
  for (const [name, row] of Object.entries(rows)) {
    const gif = await readFile(new URL(`../public/assets/animations/${name}.gif`, import.meta.url));
    const delays = gifDelays(gif);
    assert.deepEqual([...atlas.ASTERION_ANIMATIONS[name].delays], delays);
    const timeline = atlas.atlasTimeline(name);
    assert.equal(timeline.row, row);
    assert.equal(timeline.duration, delays.reduce((a, b) => a + b, 0));
    assert.equal(timeline.frames.length, delays.length);
    for (let index = 0; index < delays.length; index++) {
      assert.equal(timeline.frames[index].column, index);
      assert.equal(timeline.frames[index].offset, delays.slice(0, index).reduce((a, b) => a + b, 0) / timeline.duration);
    }
  }
});

test("CSS discrete frame boundaries follow GIF timing and never enter a neighboring atlas row", async () => {
  const css = await readFile(new URL("../app/companion-art.module.css", import.meta.url), "utf8");
  assert.match(css, /animation-timing-function:\s*steps\(1, end\)/);
  for (const name of Object.keys(atlas.ASTERION_ANIMATIONS)) {
    const block = css.split(`@keyframes ${name} {`)[1].split("\n}")[0];
    const timeline = atlas.atlasTimeline(name);
    const frames = [...block.matchAll(/([\d.]+)%(?:, 100%)?\s*\{ transform: translate\((-?[\d.]+)px, var\(--atlas-row\)\); \}/g)];
    assert.equal(frames.length, timeline.frames.length, name);
    for (const [index, frame] of frames.entries()) {
      assert.ok(Math.abs(Number(frame[1]) / 100 - timeline.frames[index].offset) < 0.00000001, `${name} frame ${index}`);
      assert.equal(Number(frame[2]), index === 0 ? 0 : -index * 192);
    }
  }
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)\s*\{\s*\.sprite \{ animation: none; transform: translate\(0px, 0px\);/);
});

test("approved atlas image bytes remain unchanged and invalid animation names fall back safely", async () => {
  const bytes = await readFile(new URL("../public/assets/spritesheet.webp", import.meta.url));
  assert.equal(createHash("sha256").update(bytes).digest("hex"), "69fadd98d86df3d84bcfff74b4f5bde258257abeaaf0b4bdf1d41a34a81ef35d");
  for (const value of [undefined, "__proto__", "constructor", "missing", "../untrusted"]) assert.equal(atlas.atlasAnimation(value), "idle");
});

test("atlas renderer preserves aspect ratio, clips letterbox gutters and supports reduced motion and decorative images", async () => {
  const source = await readFile(new URL("../app/companion-art.tsx", import.meta.url), "utf8");
  const output = ts.transpileModule(source, { compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const require = createRequire(import.meta.url), module = { exports: {} };
  const styles = new Proxy({}, { get: (_, key) => key });
  vm.runInNewContext(output, { exports: module.exports, module, require: name => name === "@/lib/animation-atlas" ? atlas : name === "./companion-art.module.css" ? { default: styles } : require(name) });
  const Component = module.exports.CompanionArt;
  const html = renderToStaticMarkup(React.createElement(Component, { alt: "Asterion", animation: "review", fill: true }));
  assert.match(html, /viewBox="0 0 192 208"/);
  assert.match(html, /preserveAspectRatio="xMidYMid meet"/);
  assert.match(html, /<svg width="192" height="208" overflow="hidden"/);
  assert.match(html, /class="viewport fill /);
  assert.match(html, /role="img" aria-label="Asterion"/);
  assert.match(html, /data-asterion-animation="review"/);
  assert.match(html, /--atlas-row:-1664px;animation-duration:1030ms/);
  const still = renderToStaticMarkup(React.createElement(Component, { alt: "", animation: "review", reducedMotion: true }));
  assert.match(still, /data-asterion-animation="still"/);
  assert.match(still, /--atlas-row:0px/);
  assert.match(still, /aria-hidden="true"/);
  assert.doesNotMatch(still, /role="img"|aria-label=/);
});
