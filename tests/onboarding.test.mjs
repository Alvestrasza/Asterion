import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import ts from 'typescript';
import * as engine from '../lib/care-engine.ts';
import * as progression from '../lib/progression.ts';
import { availableSlots, slotsForLevel } from '../lib/companion-slots.ts';
import * as companions from '../lib/companions.ts';
import { getSocialMessages } from '../lib/social-messages.ts';
const compiled = ts.transpileModule(await readFile(new URL('../lib/pet-service.ts', import.meta.url), 'utf8'), { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
function fixture() {
  const pets = new Map(), progress = new Map(), events = [], accessChecks = [];
  const allPets = () => [...pets.values()];
  const matching = where => allPets().filter(p => Object.entries(where).every(([key, value]) => p[key] === value));
  const tx = {
    pet: {
      async findUnique({ where }) {
        if (where.ownerId_kind) return matching(where.ownerId_kind)[0] ?? null;
        if (where.ownerId_adoptionRequestId) return matching(where.ownerId_adoptionRequestId)[0] ?? null;
        return matching(where)[0] ?? null;
      },
      async findFirst({ where }) { return matching(where)[0] ?? null; },
      async findMany({ where }) { return matching(where); },
      async count({ where }) { return matching(where).length; },
      async create({ data }) { assert.equal(matching({ ownerId: data.ownerId, kind: data.kind }).length, 0); const row = { id: `pet-${pets.size}`, createdAt: new Date(), satiety: 76, energy: 82, joy: 74, bond: 24, sleeping: false, level: 1, xp: 0, interactions: 0, version: 1, ...data }; pets.set(row.id, row); return row; },
      async updateMany({ where, data }) { const row = allPets().find(p => p.id === where.id); if (!row || row.version !== where.version) return { count: 0 }; Object.assign(row, data, { version: row.version + 1 }); return { count: 1 }; }
    },
    playerProgress: {
      async findUnique({ where }) { return progress.get(where.userId) ?? null; },
      async create({ data }) { const row = { level: 1, xp: 0, activePetId: null, unlockedSlots: 1, rewardDay: null, earnedToday: 0, lastFeedRewardAt: null, lastPlayRewardAt: null, lastPetRewardAt: null, ...data }; progress.set(data.userId, row); return row; },
      async update({ where, data }) { const row = progress.get(where.userId); Object.assign(row, data); return row; }
    },
    petEvent: {
      async create({ data }) { const row = { id: `event-${events.length}`, xpAwarded: 0, ...data }; events.push(row); return row; },
      async findMany({ where }) { return events.filter(e => e.petId === where.petId).toReversed().slice(0, 10); },
      async findUnique({ where }) { return events.find(e => e.ownerId === where.ownerId_requestId.ownerId && e.requestId === where.ownerId_requestId.requestId) ?? null; },
      async deleteMany({ where }) { for (let i = events.length - 1; i >= 0; i--) if (events[i].petId === where.petId) events.splice(i, 1); }
    }
  };
  const module = { exports: {} };
  class KnownError extends Error {}
  vm.runInNewContext(compiled, { exports: module.exports, module, Date, Error,
    require(name) {
      if (name === '@prisma/client') return { Prisma: { TransactionIsolationLevel: { Serializable: 'Serializable' }, PrismaClientKnownRequestError: KnownError } };
      if (name === '@/lib/care-engine') return engine;
      if (name === '@/lib/progression') return progression;
      if (name === '@/lib/companion-slots') return { availableSlots, slotsForLevel };
      if (name === '@/lib/companions') return companions;
      if (name === '@/lib/db') return { prisma: { ...tx, $transaction: fn => fn(tx) } };
      if (name === '@/lib/deployment-config') return { isPublicDeployment: () => true };
      if (name === '@/lib/access-service') return { assertAccess: async (_, id) => accessChecks.push(id), consumeCareBudget: async () => true };
      throw new Error(name);
    }
  });
  return { service: module.exports, pets, progress, events, accessChecks };
}
test('public visits do not silently hatch a pet; all eight choices start at level one', async () => {
  const f = fixture();
  await assert.rejects(f.service.getPetSnapshot('new-user'), /companion_selection_required/);
  assert.equal(f.pets.size, 0);
  for (const kind of companions.COMPANION_KINDS) {
    const pet = await f.service.chooseFirstPet(kind, kind);
    assert.equal(pet.kind, kind); assert.equal(pet.level, 1); assert.equal(pet.xp, 0); assert.equal(pet.playerLevel, 1); assert.equal(pet.playerXp, 0);
  }
  assert.equal(f.events.length, 8);
});
test('duplicate adoption never changes an existing choice or affects another owner', async () => {
  const f = fixture();
  await f.service.chooseFirstPet('a', 'rabbit');
  await f.service.chooseFirstPet('b', 'orc');
  const retry = await f.service.chooseFirstPet('a', 'cat');
  assert.equal(retry.kind, 'rabbit'); assert.equal([...f.pets.values()].find(p => p.ownerId === 'b').kind, 'orc');
  assert.equal(f.events.length, 2);
  assert.deepEqual(f.accessChecks, ['a', 'b', 'a']);
});
test('unknown companion kinds are rejected before creation', async () => {
  const f = fixture();
  await assert.rejects(f.service.chooseFirstPet('a', 'unknown'), /invalid_companion/);
  assert.equal(f.pets.size, 0);
});
test('care XP is idempotent, shared by player and pet, and never awarded during sleep', async () => {
  const f = fixture();
  const adopted = await f.service.chooseFirstPet('pilot', 'asterion');
  const first = await f.service.performPetCommand('pilot', { requestId: 'first', action: 'pet' }, adopted.id);
  assert.equal(first.feedback.xpAwarded, 16);
  assert.equal(first.pet.xp, 16);
  assert.equal(first.pet.playerXp, 16);
  const replay = await f.service.performPetCommand('pilot', { requestId: 'first', action: 'pet' }, adopted.id);
  assert.equal(replay.replayed, true);
  assert.equal(replay.pet.xp, 16);
  const rapid = await f.service.performPetCommand('pilot', { requestId: 'rapid', action: 'pet' }, adopted.id);
  assert.equal(rapid.feedback.xpAwarded, 0);
  const sleep = await f.service.performPetCommand('pilot', { requestId: 'sleep', action: 'sleep' }, adopted.id);
  assert.equal(sleep.feedback.xpAwarded, 0);
  const asleep = await f.service.performPetCommand('pilot', { requestId: 'asleep', action: 'pet' }, adopted.id);
  assert.equal(asleep.feedback.accepted, false);
  assert.equal(asleep.pet.xp, 16);
  assert.equal(asleep.pet.playerXp, 16);
  const wake = await f.service.performPetCommand('pilot', { requestId: 'wake', action: 'wake' }, adopted.id);
  assert.equal(wake.feedback.xpAwarded, 0);
  const feed = await f.service.performPetCommand('pilot', { requestId: 'feed', action: 'feed' }, adopted.id);
  assert.equal(feed.feedback.xpAwarded, 15);
  assert.equal(feed.pet.xp, 31);
  assert.equal(feed.pet.playerXp, 31);
});
test('account milestones unlock at most five permanent, distinct companions', async () => {
  assert.deepEqual([1, 14, 15, 29, 30, 44, 45, 59, 60, 99].map(slotsForLevel), [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]);
  assert.equal(availableSlots(1, 3), 3);
  const f = fixture();
  await f.service.chooseFirstPet('pilot', 'asterion');
  await assert.rejects(f.service.adoptAdditionalPet('pilot', 'cat', 'request-1'), /companion_slots_full/);
  f.progress.get('pilot').level = 15;
  const cat = await f.service.adoptAdditionalPet('pilot', 'cat', 'request-1');
  assert.equal(cat.level, 1); assert.equal(cat.xp, 0); assert.equal(cat.playerLevel, 15);
  const retry = await f.service.adoptAdditionalPet('pilot', 'cat', 'request-1');
  assert.equal(retry.id, cat.id);
  await assert.rejects(f.service.adoptAdditionalPet('pilot', 'cat', 'request-2'), /companion_slots_full|companion_kind_owned/);
  f.progress.get('pilot').level = 99;
  for (const [index, kind] of ['rabbit', 'dog', 'elf'].entries()) await f.service.adoptAdditionalPet('pilot', kind, `request-${index + 3}`);
  await assert.rejects(f.service.adoptAdditionalPet('pilot', 'pony', 'request-9'), /companion_slots_full/);
  assert.equal((await f.service.getPetCollection('pilot')).pets.length, 5);
});
test('selection changes only the active pointer; commands and retries stay bound to their original pet', async () => {
  const f = fixture();
  const first = await f.service.chooseFirstPet('pilot', 'asterion');
  f.progress.get('pilot').level = 15;
  const second = await f.service.adoptAdditionalPet('pilot', 'cat', 'adopt-cat');
  await f.service.selectOwnedPet('pilot', second.id);
  assert.equal((await f.service.getPetSnapshot('pilot')).id, second.id);
  const action = await f.service.performPetCommand('pilot', { requestId: 'care-first', action: 'pet' }, first.id);
  assert.equal(action.pet.id, first.id);
  const secondAction = await f.service.performPetCommand('pilot', { requestId: 'care-second', action: 'feed' }, second.id);
  assert.equal(secondAction.pet.xp, 15);
  assert.equal(action.pet.xp, 16);
  assert.equal(secondAction.pet.playerXp, 31);
  assert.equal((await f.service.getPetSnapshot('pilot')).id, second.id);
  const replay = await f.service.performPetCommand('pilot', { requestId: 'care-first', action: 'pet' }, first.id);
  assert.equal(replay.replayed, true);
  await assert.rejects(f.service.performPetCommand('pilot', { requestId: 'care-first', action: 'play' }, first.id), /companion_context_changed/);
  await assert.rejects(f.service.performPetCommand('pilot', { requestId: 'care-first', action: 'pet' }, second.id), /companion_context_changed/);
  await assert.rejects(f.service.performPetCommand('other', { requestId: 'steal', action: 'pet' }, second.id), /companion_context_changed/);
  await assert.rejects(f.service.selectOwnedPet('other', second.id), /companion_not_owned/);
  await assert.rejects(f.service.performPetCommand('pilot', { requestId: 'reset-first', action: 'reset' }, first.id), /companion_permanent/);
  await assert.rejects(f.service.performPetCommand('pilot', { requestId: 'change-kind', action: 'select', kind: 'dog' }, first.id), /companion_permanent/);
});
test('social and onboarding text keys are complete in all four languages', () => {
  const keys = Object.keys(getSocialMessages('en')).sort();
  for (const locale of ['de', 'en', 'fr', 'es']) {
    assert.deepEqual(Object.keys(getSocialMessages(locale)).sort(), keys);
    assert.ok(Object.values(getSocialMessages(locale)).every(s => typeof s === 'string' && s.length > 0));
  }
});
