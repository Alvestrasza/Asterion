import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import ts from 'typescript';
import * as engine from '../lib/care-engine.ts';
import * as companions from '../lib/companions.ts';
import { getSocialMessages } from '../lib/social-messages.ts';
const compiled = ts.transpileModule(await readFile(new URL('../lib/pet-service.ts', import.meta.url), 'utf8'), { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
function fixture() {
  const pets = new Map(), events = [], accessChecks = [];
  const tx = {
    pet: {
      async findUnique({ where }) { return where.ownerId ? pets.get(where.ownerId) ?? null : [...pets.values()].find(p => p.id === where.id) ?? null; },
      async create({ data }) { assert.equal(pets.has(data.ownerId), false); const row = { id: `pet-${data.ownerId}`, satiety: 76, energy: 82, joy: 74, bond: 24, sleeping: false, level: 1, xp: 0, interactions: 0, version: 1, ...data }; pets.set(data.ownerId, row); return row; }
    },
    petEvent: { async create({ data }) { const row = { id: `event-${events.length}`, ...data }; events.push(row); return row; }, async findMany({ where }) { return events.filter(e => e.petId === where.petId); } }
  };
  const module = { exports: {} };
  class KnownError extends Error {}
  vm.runInNewContext(compiled, { exports: module.exports, module, Date, Error,
    require(name) {
      if (name === '@prisma/client') return { Prisma: { TransactionIsolationLevel: { Serializable: 'Serializable' }, PrismaClientKnownRequestError: KnownError } };
      if (name === '@/lib/care-engine') return engine;
      if (name === '@/lib/companions') return companions;
      if (name === '@/lib/db') return { prisma: { ...tx, $transaction: fn => fn(tx) } };
      if (name === '@/lib/deployment-config') return { isPublicDeployment: () => true };
      if (name === '@/lib/access-service') return { assertAccess: async (_, id) => accessChecks.push(id) };
      throw new Error(name);
    }
  });
  return { service: module.exports, pets, events, accessChecks };
}
test('public visits do not silently hatch a pet; all eight choices start at level one', async () => {
  const f = fixture();
  await assert.rejects(f.service.getPetSnapshot('new-user'), /companion_selection_required/);
  assert.equal(f.pets.size, 0);
  for (const kind of companions.COMPANION_KINDS) {
    const pet = await f.service.chooseFirstPet(kind, kind);
    assert.equal(pet.kind, kind); assert.equal(pet.level, 1); assert.equal(pet.xp, 0);
  }
  assert.equal(f.events.length, 8);
});
test('duplicate adoption never changes an existing choice or affects another owner', async () => {
  const f = fixture();
  await f.service.chooseFirstPet('a', 'rabbit');
  await f.service.chooseFirstPet('b', 'orc');
  const retry = await f.service.chooseFirstPet('a', 'cat');
  assert.equal(retry.kind, 'rabbit'); assert.equal(f.pets.get('b').kind, 'orc');
  assert.equal(f.events.length, 2);
  assert.deepEqual(f.accessChecks, ['a', 'b', 'a']);
});
test('unknown companion kinds are rejected before creation', async () => {
  const f = fixture();
  await assert.rejects(f.service.chooseFirstPet('a', 'unknown'), /invalid_companion/);
  assert.equal(f.pets.size, 0);
});
test('social and onboarding text keys are complete in all four languages', () => {
  const keys = Object.keys(getSocialMessages('en')).sort();
  for (const locale of ['de', 'en', 'fr', 'es']) {
    assert.deepEqual(Object.keys(getSocialMessages(locale)).sort(), keys);
    assert.ok(Object.values(getSocialMessages(locale)).every(s => typeof s === 'string' && s.length > 0));
  }
});
