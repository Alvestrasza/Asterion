/** Asterion achievement regressions. Version: 1.1.0 | License: UNLICENSED | Updated: 2026-10-05 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { PGlite } from "@electric-sql/pglite";
import * as catalog from "../lib/achievements.ts";
import * as care from "../lib/care-engine.ts";
import * as companions from "../lib/companions.ts";
import * as speech from "../lib/companion-speech.ts";
import * as media from "../lib/companion-3d.ts";
import { utcRewardDay } from "../lib/progression.ts";
import { getMessages } from "../lib/messages.ts";
import { formatJournalTime } from "../lib/journal-time.ts";
import { createRequestId } from "../lib/request-id.ts";

const require = createRequire(import.meta.url);
async function module(file, dependencies = {}, globals = {}) {
  const source = await readFile(new URL(file, import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  const result = { exports: {} };
  vm.runInNewContext(compiled, { module: result, exports: result.exports, Date, Intl, process: { env: {} },
    require: name => name in dependencies ? dependencies[name] : require(name), ...globals });
  return result.exports;
}
const service = await module("../lib/achievement-service.ts", { "./achievements.ts": catalog, "./progression.ts": { utcRewardDay } });
const collection = await module("../app/achievement-collection.tsx", { "@/lib/achievements": catalog });
const sql = await readFile(new URL("../prisma/migrations/20261001130000_add_achievements/migration.sql", import.meta.url), "utf8");

// Real PostgreSQL SQL in memory. This adapter substitutes Prisma's transport only.
// PGlite has one connection; multi-node serializable retry acceptance is a separate gate.
function adapter(db) {
  const rows = async (sql, values) => (await db.query(sql, values)).rows;
  return {
    pet: { findMany: ({ where }) => rows('SELECT "kind" FROM "Pet" WHERE "ownerId"=$1', [where.ownerId]) },
    achievementProgress: {
      async findUnique({ where }) { const k = where.ownerId_scopeKey_achievementId; return (await rows('SELECT * FROM "AchievementProgress" WHERE "ownerId"=$1 AND "scopeKey"=$2 AND "achievementId"=$3', [k.ownerId, k.scopeKey, k.achievementId]))[0] ?? null; },
      findMany({ where }) { return rows('SELECT * FROM "AchievementProgress" WHERE "ownerId"=$1 AND ("scopeKey"=$2 OR "petId"=$3)', [where.ownerId, where.OR[0].scopeKey, where.OR[1].petId]); },
      async upsert({ create: c, update: u }) {
        return (await rows('INSERT INTO "AchievementProgress" ("ownerId","scopeKey","achievementId","petId","catalogVersion","progress","earnedAt") VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT ("ownerId","scopeKey","achievementId") DO UPDATE SET "progress"=$8,"earnedAt"=$9 RETURNING *', [c.ownerId,c.scopeKey,c.achievementId,c.petId,c.catalogVersion,c.progress,c.earnedAt,u.progress,u.earnedAt]))[0];
      }
    },
    achievementCareDay: {
      async findUnique({ where }) { const k = where.petId_day; return (await rows('SELECT * FROM "AchievementCareDay" WHERE "petId"=$1 AND "day"=$2', [k.petId,k.day]))[0] ?? null; },
      findMany: ({ where }) => rows('SELECT * FROM "AchievementCareDay" WHERE "petId"=$1 AND "ownerId"=$2', [where.petId,where.ownerId]),
      async upsert({ create: c, update: u }) {
        return (await rows('INSERT INTO "AchievementCareDay" ("ownerId","petId","day","careMask","healthy") VALUES ($1,$2,$3,$4,$5) ON CONFLICT ("petId","day") DO UPDATE SET "careMask"=$6,"healthy"=$7 RETURNING *', [c.ownerId,c.petId,c.day,c.careMask,c.healthy,u.careMask,u.healthy]))[0];
      }
    }
  };
}

async function fixture(legacy = false, migrate = true) {
  const db = new PGlite();
  await db.exec(`CREATE TABLE "User" (id text PRIMARY KEY);
    CREATE TABLE "Pet" (id text PRIMARY KEY,"ownerId" text NOT NULL REFERENCES "User"(id),kind text NOT NULL,level int NOT NULL);
    CREATE TABLE "PlayerProgress" ("userId" text PRIMARY KEY REFERENCES "User"(id),level int NOT NULL,xp int NOT NULL DEFAULT 0);
    CREATE TABLE "PetEvent" (id text PRIMARY KEY,"ownerId" text NOT NULL,"petId" text NOT NULL REFERENCES "Pet"(id),action text NOT NULL,accepted bool NOT NULL,"xpAwarded" int NOT NULL,"occurredAt" timestamp(3) NOT NULL);
    INSERT INTO "User" VALUES ('owner-a'),('owner-b');
    INSERT INTO "Pet" VALUES ('pet-a','owner-a','asterion',${legacy ? 5 : 1}),('pet-b','owner-b','cat',1);
    INSERT INTO "PlayerProgress" ("userId",level) VALUES ('owner-a',${legacy ? 5 : 1}),('owner-b',1);`);
  if (legacy) await db.exec(`INSERT INTO "PetEvent" VALUES
    ('e1','owner-a','pet-a','feed',true,15,'2026-09-01 10:00'),
    ('e2','owner-a','pet-a','play',true,25,'2026-09-01 14:00'),
    ('e3','owner-a','pet-a','pet',false,16,'2026-09-02 10:00'),
    ('e4','owner-a','pet-a','pet',true,0,'2026-09-03 10:00'),
    ('e5','owner-b','pet-a','pet',true,16,'2026-09-04 10:00');`);
  if (migrate) await db.exec(sql);
  return db;
}
const pet = { id: "pet-a", ownerId: "owner-a", level: 5, satiety: 80, energy: 80, joy: 80, bond: 50, sleeping: false };
const now = new Date("2026-10-01T10:00:00Z");
const accepted = action => ({ action, accepted: true, xpAwarded: 15 });

test("catalog has stable distinct scopes, four languages, fallback and real visual assets", async () => {
  assert.equal(new Set(catalog.ACHIEVEMENTS.map(def => def.id)).size, 8);
  assert.equal(catalog.achievementCopy("xx"), catalog.achievementCopy("en"));
  for (const locale of ["de","en","fr","es"]) {
    const views = catalog.achievementViews(locale, []);
    assert.equal(views.length, 8);
    assert.ok(views.every(row => row.name && row.description && row.progress === 0 && !row.earnedAt));
    for (const entry of views) assert.match(await readFile(new URL("../public" + entry.icon, import.meta.url), "utf8"), /<svg/);
  }
  assert.equal(catalog.healthyCare({ ...pet, energy: 49.9 }, false), false);
  assert.equal(catalog.healthyCare(pet, true), false);
});

test("migration preserves legacy data and backfills only proven facts", async () => {
  const db = await fixture(true);
  try {
    const days = (await db.query('SELECT * FROM "AchievementCareDay"')).rows;
    assert.equal(days.length, 1);
    assert.equal(days[0].careMask, 3);
    assert.equal(days[0].healthy, false, "historical health is unknown");
    const views = await service.readAchievements(adapter(db), "owner-a", "pet-a", "en");
    assert.ok(views.find(x => x.id === "v1.pet-level-five").earnedAt);
    assert.ok(views.find(x => x.id === "v1.player-level-five").earnedAt);
    assert.equal(views.find(x => x.id === "v1.varied-care").progress, 2);
    assert.equal(views.find(x => x.id === "v1.healthy-bond").progress, 0);
    assert.equal((await db.query('SELECT count(*)::int AS n FROM "PetEvent"')).rows[0].n, 5);
    assert.equal((await db.query('SELECT xp FROM "PlayerProgress" WHERE "userId"=$1', ["owner-a"])).rows[0].xp, 0);
  } finally { await db.close(); }
});

test("a failed backfill rolls back both new tables and the composite pet index", async () => {
  const db = await fixture(false, false);
  try {
    await db.exec('UPDATE "PlayerProgress" SET level=-1 WHERE "userId"=\'owner-a\'');
    await assert.rejects(db.exec(sql), /check constraint/i);
    await db.exec("ROLLBACK");
    const names = (await db.query("SELECT to_regclass('\"AchievementProgress\"') AS table_name, to_regclass('\"Pet_id_ownerId_key\"') AS index_name")).rows[0];
    assert.equal(names.table_name, null);
    assert.equal(names.index_name, null);
    assert.equal((await db.query('SELECT count(*)::int AS n FROM "Pet"')).rows[0].n, 2);
  } finally { await db.close(); }
});

test("repeated transactional care awards once, isolates owners and keeps locale-independent progress", async () => {
  const db = await fixture();
  try {
    const outcomes = await Promise.all([1,2].map(() => db.transaction(tx => service.recordCareAchievements(adapter(tx), "owner-a", pet, accepted("feed"), now, 5))));
    assert.equal(outcomes.flat().filter(id => id === "v1.first-care").length, 1);
    for (const action of ["play","pet"]) await db.transaction(tx => service.recordCareAchievements(adapter(tx), "owner-a", pet, accepted(action), now, 5));
    assert.equal((await db.query('SELECT count(*)::int AS n FROM "AchievementCareDay"')).rows[0].n, 1);
    for (const locale of ["de","en","fr","es"]) {
      const views = await service.readAchievements(adapter(db), "owner-a", "pet-a", locale);
      assert.ok(views.find(x => x.id === "v1.varied-care").earnedAt);
      assert.equal(views.find(x => x.id === "v1.healthy-bond").progress, 1);
    }
    const other = await service.readAchievements(adapter(db), "owner-b", "pet-a", "en");
    assert.ok(other.filter(x => x.scope === "pet").every(x => x.progress === 0 && x.earnedAt === null));
    await assert.rejects(service.recordCareAchievements(adapter(db), "owner-b", pet, accepted("feed"), now, 5), /ownership/);
    await assert.rejects(db.query('INSERT INTO "AchievementCareDay" VALUES ($1,$2,$3,1,true)', ["owner-b","pet-a","2026-10-02"]), /foreign key/i);
  } finally { await db.close(); }
});

test("no-op, sleep, reset and imports do not earn; health days survive pauses and aborted transactions", async () => {
  const db = await fixture();
  try {
    for (const event of [{ action:"feed",accepted:false,xpAwarded:0 }, { action:"pet",accepted:true,xpAwarded:0 }, ...["sleep","wake","reset","restore","select"].map(action => ({action,accepted:true,xpAwarded:100}))]) {
      assert.equal((await service.recordCareAchievements(adapter(db), "owner-a", pet, event, now, 5)).length, 0);
    }
    await assert.rejects(db.transaction(async tx => { await service.recordCareAchievements(adapter(tx), "owner-a", pet, accepted("feed"), now, 5); throw new Error("abort"); }), /abort/);
    assert.equal((await db.query('SELECT count(*)::int AS n FROM "AchievementCareDay"')).rows[0].n, 0);
    for (const day of [0,2,5,10,15,30,60]) {
      await db.transaction(tx => service.recordCareAchievements(adapter(tx), "owner-a", pet, accepted("feed"), new Date(now.getTime() + day*86400000), 5));
    }
    const before = await service.readAchievements(adapter(db), "owner-a", "pet-a", "en");
    assert.ok(before.find(x => x.id === "v1.healthy-bond").earnedAt);
    await service.recordCareAchievements(adapter(db), "owner-a", { ...pet, energy: 0, sleeping: true }, { action:"pet",accepted:false,xpAwarded:0 }, now, 5);
    assert.deepEqual(await service.readAchievements(adapter(db), "owner-a", "pet-a", "en"), before);
    assert.equal((await db.query('SELECT xp FROM "PlayerProgress" WHERE "userId"=$1',["owner-a"])).rows[0].xp,0);
  } finally { await db.close(); }
});

test("additional adoption is permanent account recognition and cannot leak another companion's awards", async () => {
  const db = await fixture();
  try {
    await db.exec(`INSERT INTO "Pet" VALUES ('pet-a2','owner-a','rabbit',1);`);
    assert.ok((await service.recordAdoptionAchievements(adapter(db), "owner-a", now)).includes("v1.companion-family"));
    assert.equal((await service.recordAdoptionAchievements(adapter(db), "owner-a", now)).length, 0);
    await service.recordCareAchievements(adapter(db), "owner-a", pet, accepted("pet"), now, 5);
    const nextPet = await service.readAchievements(adapter(db), "owner-a", "pet-a2", "en");
    assert.equal(nextPet.find(x => x.id === "v1.first-care").earnedAt, null);
    assert.ok(nextPet.find(x => x.id === "v1.companion-family").earnedAt);
    assert.equal(nextPet.find(x => x.id === "v1.constellation").progress, 2);
  } finally { await db.close(); }
});

test("actual React collection exposes locked/earned progress in each language without relying on color", () => {
  for (const locale of ["de","en","fr","es"]) {
    const entries = catalog.achievementViews(locale,[{achievementId:"v1.first-care",progress:1,earnedAt:now}]);
    const html = renderToStaticMarkup(React.createElement(collection.AchievementCollection,{achievements:entries,companionName:"Asterion",locale}));
    assert.doesNotMatch(html, /<details/);
    assert.equal((html.match(/<section/g) ?? []).length, 2);
    assert.equal((html.match(/<h2/g) ?? []).length, 2);
    assert.equal((html.match(/<h3/g) ?? []).length, 8);
    assert.match(html, /Asterion/);
    assert.equal((html.match(/<progress/g) ?? []).length, 8);
    assert.ok(html.includes(catalog.achievementCopy(locale).earned));
    assert.ok(html.includes(catalog.achievementCopy(locale).locked));
    assert.ok(html.includes(`lang="${locale}"`));
  }
});

test("actual care buttons disable all three care actions while asleep and preserve wake", async () => {
  const nil = () => null;
  const client = await module("../app/asterion-client.tsx", {
    "next/image": { default: nil }, "@/app/asterion-model": { AsterionModel:nil }, "./site-header": { SiteHeader:nil },
    "@/lib/care-engine":care,"@/lib/companions":companions,"@/lib/companion-3d":media,
    "@/lib/request-id":{createRequestId},"@/lib/journal-time":{formatJournalTime},"@/lib/messages":{getMessages},
    "@/lib/companion-speech":speech,"@/app/companion-background":{CompanionBackground:nil},"./companion-art":{CompanionArt:nil},
    "./companion-collection":{CompanionCollection:nil},"./achievement-collection":collection,"@/lib/achievements":catalog
  });
  for (const sleeping of [true,false]) {
    const snapshot = { ...care.createInitialState(now.getTime()), id:"pet-a",kind:"asterion",version:1,playerLevel:1,playerXp:0,returnedAfterAbsence:false,achievements:[],journal:[],sleeping };
    const html = renderToStaticMarkup(React.createElement(client.AsterionClient,{ initialPet:snapshot,collection:{pets:[],activePetId:"pet-a",unlockedSlots:1,playerLevel:1},userId:"owner-a",userName:"Player",internalTestMode:true,originalPetId:"pet-a" }));
    for (const action of ["feed","play","pet"]) {
      const tag = html.match(new RegExp(`<button[^>]*class="care-action ${action}-action"[^>]*>`))?.[0];
      assert.ok(tag);
      assert.equal(tag.includes('disabled=""'), sleeping);
    }
    assert.ok(!html.match(/<button[^>]*class="care-action sleep-action"[^>]*>/)[0].includes('disabled=""'));
  }
});

test("overlapping care refreshes cannot restore an older sleeping presentation", async () => {
  // Execute the actual effect with controlled hooks/network; browser acceptance is separate.
  const states = [];
  const effects = [];
  const pending = [];
  const handlers = new Map();
  const nil = () => null;
  const hooks = { ...React,
    useState(initial) {
      const index = states.length;
      states.push(typeof initial === "function" ? initial() : initial);
      return [states[index], next => { states[index] = typeof next === "function" ? next(states[index]) : next; }];
    },
    useRef: value => ({ current: value }), useCallback: fn => fn,
    useEffect: effect => effects.push(effect)
  };
  const client = await module("../app/asterion-client.tsx", {
    react: hooks, "next/image": { default: nil }, "@/app/asterion-model": { AsterionModel:nil }, "./site-header": { SiteHeader:nil },
    "@/lib/care-engine":care,"@/lib/companions":companions,"@/lib/companion-3d":media,
    "@/lib/request-id":{createRequestId},"@/lib/journal-time":{formatJournalTime},"@/lib/messages":{getMessages},
    "@/lib/companion-speech":speech,"@/app/companion-background":{CompanionBackground:nil},"./companion-art":{CompanionArt:nil},
    "./companion-collection":{CompanionCollection:nil},"./achievement-collection":collection,"@/lib/achievements":catalog
  }, {
    navigator: { onLine: true }, document: { visibilityState: "visible" }, AbortController,
    window: { addEventListener: (name, fn) => handlers.set(name, fn), removeEventListener: name => handlers.delete(name) },
    setInterval: () => 1, clearInterval: nil, clearTimeout: nil,
    fetch: () => new Promise(resolve => pending.push(resolve))
  });
  const snapshot = { ...care.createInitialState(now.getTime()), id:"pet-a",kind:"asterion",version:1,playerLevel:1,playerXp:0,returnedAfterAbsence:false,achievements:[],journal:[] };
  client.AsterionClient({ initialPet:snapshot,collection:{pets:[],activePetId:"pet-a",unlockedSlots:1,playerLevel:1},userId:"owner-a",userName:"Player",internalTestMode:true,originalPetId:"pet-a" });
  const cleanup = effects[0]();
  try {
    const older = handlers.get("focus")();
    const newer = handlers.get("focus")();
    pending[1]({ ok:true, json:async () => ({ pet:{...snapshot,version:3,sleeping:false} }) });
    await newer;
    const presentation = states.slice(1,5);
    pending[0]({ ok:true, json:async () => ({ pet:{...snapshot,version:2,sleeping:true} }) });
    await older;
    assert.equal(states[0].version, 3);
    assert.deepEqual(states.slice(1,5), presentation, "older sleeping state must not change speech or animation");
    const cancelled = handlers.get("focus")();
    cleanup();
    pending[2]({ ok:true, json:async () => ({ pet:{...snapshot,version:4,sleeping:true} }) });
    await cancelled;
    assert.equal(states[0].version, 3, "an unmounted refresh cannot update state");
  } finally { cleanup(); }
});
