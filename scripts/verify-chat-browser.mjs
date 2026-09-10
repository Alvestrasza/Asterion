// Local-only browser acceptance. No production credentials, user data or network endpoints.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import ts from 'typescript';
const require = createRequire(import.meta.url);
const playwrightPath = process.env.ASTERION_TEST_PLAYWRIGHT || 'playwright';
const { chromium } = require(playwrightPath);
const sources = new Map();
for (const name of ['chat-crypto', 'chat-vault']) {
  sources.set(`/${name}.js`, ts.transpileModule(await readFile(new URL(`../lib/${name}.ts`, import.meta.url), 'utf8'), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 }
  }).outputText);
}
const server = createServer((req, res) => {
  if (req.url === '/') { res.setHeader('Content-Type', 'text/html'); res.end('<!doctype html><title>Isolated chat crypto acceptance</title>'); }
  else if (sources.has(req.url)) { res.setHeader('Content-Type', 'text/javascript'); res.end(sources.get(req.url)); }
  else { res.statusCode = 404; res.end(); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
let browser;
try {
  browser = await chromium.launch({ channel: process.env.ASTERION_TEST_BROWSER || 'msedge', headless: true });
  const a = await browser.newContext(); const b = await browser.newContext();
  const ap = await a.newPage(); const bp = await b.newPage();
  const url = `http://127.0.0.1:${server.address().port}/`;
  await Promise.all([ap.goto(url), bp.goto(url)]);
  const initialize = async (page, actorId) => page.evaluate(async actorId => {
    const c = await import('/chat-crypto.js'); const v = await import('/chat-vault.js');
    window.fixture = await c.createChatIdentity(actorId);
    await v.saveChatKeys(window.fixture.keys);
    return { registration: window.fixture.registration, recoveryCode: window.fixture.recoveryCode };
  }, actorId);
  const af = await initialize(ap, 'fixture-a'); const bf = await initialize(bp, 'fixture-b');
  const envelope = await ap.evaluate(async peer => {
    const c = await import('/chat-crypto.js');
    return c.encryptMessage(window.fixture.keys, 'fixture-b', peer, 'fixture-pair', 'Browser-only secret 🌟');
  }, bf.registration.identity);
  assert.ok(!JSON.stringify(envelope).includes('secret'));
  assert.equal(await bp.evaluate(async ({ peer, envelope }) => {
    const c = await import('/chat-crypto.js');
    return c.decryptMessage(window.fixture.keys, 'fixture-a', peer, 'fixture-pair', envelope);
  }, { peer: af.registration.identity, envelope }), 'Browser-only secret 🌟');
  await ap.reload();
  assert.equal(await ap.evaluate(async ({ own, peer, envelope }) => {
    const c = await import('/chat-crypto.js'); const v = await import('/chat-vault.js');
    const keys = await v.loadChatKeys('fixture-a', own.fingerprint);
    if (!keys || keys.encryptionKey.extractable || keys.signingKey.extractable) throw new Error('persisted_key_invalid');
    if (await v.loadChatKeys('fixture-other', own.fingerprint)) throw new Error('actor_leak');
    return c.decryptMessage(keys, 'fixture-b', peer, 'fixture-pair', envelope);
  }, { own: af.registration.identity, peer: bf.registration.identity, envelope }), 'Browser-only secret 🌟');
  const fresh = await browser.newContext(); const fp = await fresh.newPage(); await fp.goto(url);
  assert.equal(await fp.evaluate(async ({ af, peer, envelope }) => {
    const c = await import('/chat-crypto.js'); const v = await import('/chat-vault.js');
    if (await v.loadChatKeys('fixture-a', af.registration.identity.fingerprint)) throw new Error('context_leak');
    const keys = await c.restoreChatIdentity('fixture-a', af.registration, af.recoveryCode);
    await v.savePeerPin('fixture-a', 'fixture-b', { fingerprint: peer.fingerprint, verified: true });
    try { await v.savePeerPin('fixture-a', 'fixture-b', { fingerprint: af.registration.identity.fingerprint, verified: true }); throw new Error('changed_pin_accepted'); }
    catch (error) { if (error.message !== 'peer_key_changed') throw error; }
    if (await v.getPeerPin('fixture-other', 'fixture-b')) throw new Error('pin_actor_leak');
    const races = await Promise.allSettled([
      v.savePeerPin('fixture-a', 'fixture-race', { fingerprint: peer.fingerprint, verified: false }),
      v.savePeerPin('fixture-a', 'fixture-race', { fingerprint: af.registration.identity.fingerprint, verified: false })
    ]);
    if (races.filter(r => r.status === 'fulfilled').length !== 1 || races.filter(r => r.status === 'rejected' && r.reason.message === 'peer_key_changed').length !== 1) throw new Error('pin_race');
    return c.decryptMessage(keys, 'fixture-b', peer, 'fixture-pair', envelope);
  }, { af, peer: bf.registration.identity, envelope }), 'Browser-only secret 🌟');
  console.log('PASS: two isolated browser profiles, WebCrypto round-trip, non-extractable IndexedDB reload, actor isolation, fresh-device recovery, immutable actor-scoped peer pins.');
  console.log('This does not exercise Keycloak, PostgreSQL, the HTTP chat service or the Messenger UI.');
} finally { await browser?.close(); await new Promise(resolve => server.close(resolve)); }
