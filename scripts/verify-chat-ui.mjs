// Isolated UI acceptance with the real React components, WebCrypto and IndexedDB.
// The local fixture deliberately replaces HTTP persistence, not production authorization.
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import assert from 'node:assert/strict';
import ts from 'typescript';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.ASTERION_TEST_PLAYWRIGHT || 'playwright');
const root = resolve(new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const modules = new Map(), styles = [];
async function bundle(path) {
  path = resolve(path);
  if (modules.has(path)) return path;
  modules.set(path, '');
  let source = await readFile(path, 'utf8');
  if (path.endsWith('.css')) {
    styles.push(source.replaceAll(':global(body[data-friends-dock="expanded"])', 'body[data-friends-dock="expanded"]'));
    const names = [...source.matchAll(/\.([a-zA-Z][\w-]*)/g)].map(match => match[1]);
    modules.set(path, `module.exports={default:${JSON.stringify(Object.fromEntries(names.map(name => [name, name])))}};`); return path;
  }
  if (/\.tsx?$/.test(path)) source = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 } }).outputText;
  const deps = new Map();
  for (const match of source.matchAll(/require\(["']([^"']+)["']\)/g)) {
    const name = match[1]; if (deps.has(name)) continue;
    if (name === 'next/link') { deps.set(name, '@link'); continue; }
    let target;
    if (name.startsWith('@/')) target = resolve(root, name.slice(2));
    else if (name.startsWith('.')) target = resolve(dirname(path), name);
    else target = createRequire(path).resolve(name);
    if (name.startsWith('@/') || name.startsWith('.')) {
      for (const candidate of [target, `${target}.ts`, `${target}.tsx`, `${target}.js`]) {
        try { await readFile(candidate); target = candidate; break; } catch { /* Try the next source extension. */ }
      }
    }
    deps.set(name, await bundle(target));
  }
  for (const [name, target] of deps) source = source.replaceAll(`require("${name}")`, `require(${JSON.stringify(target)})`).replaceAll(`require('${name}')`, `require(${JSON.stringify(target)})`);
  modules.set(path, source); return path;
}
const entry = await bundle(resolve(root, 'app/friends/friends-dock.tsx'));
const settingsEntry = await bundle(resolve(root, 'app/friends/friends-client.tsx'));
const socialMessages = await bundle(resolve(root, 'lib/social-messages.ts'));
await bundle(resolve(root, 'app/social.css'));
const react = await bundle(require.resolve('react'));
const client = await bundle(require.resolve('react-dom/client'));
const cryptoModule = await bundle(resolve(root, 'lib/chat-crypto.ts'));
const boot = `const process={env:{NODE_ENV:'production'}};const modules={${[...modules].map(([id, code]) => `${JSON.stringify(id)}:(module,exports,require)=>{${code}\n}`).join(',')}};
const cache={};function R(id){if(id==='@link')return {default:({prefetch,...props})=>R(${JSON.stringify(react)}).createElement('a',props)};if(cache[id])return cache[id].exports;const m={exports:{}};cache[id]=m;modules[id](m,m.exports,R);return m.exports;}
const React=R(${JSON.stringify(react)});window.chatFixtureCrypto=R(${JSON.stringify(cryptoModule)});window.fixtureSocialMessages=R(${JSON.stringify(socialMessages)}).getSocialMessages;
(async()=>{const params=new URLSearchParams(location.search);const settings=params.get('mode')==='settings';
if(!settings){const peer=await window.chatFixtureCrypto.createChatIdentity('peer');window.fixturePeer=peer;await fetch('/fixture-peer',{method:'POST',body:JSON.stringify(peer.registration.identity)});}
R(${JSON.stringify(client)}).createRoot(document.getElementById('root')).render(React.createElement(settings?R(${JSON.stringify(settingsEntry)}).FriendsClient:R(${JSON.stringify(entry)}).FriendsDock,{actorId:'actor',locale:params.get('locale')||'en'}));})();`;
let identity = null, recoveryCode = null, recoveryMode = 'keycloak', peerIdentity = null, blocked = false, dropped = false, registrationDropped = false;
let recoveries = 0;
const messages = [], sends = [], registrations = [], readMarkers = [];
const friendSearches = [], friendRequests = [];
const ownFriendCode = 'ABCDE-123-FGHJK', otherFriendCode = 'MNPQR-456-STVWX';
const server = createServer(async (req, res) => {
  if (req.url?.startsWith('/?') || req.url === '/') {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    const settings = new URL(req.url, 'http://fixture.invalid').searchParams.get('mode') === 'settings';
    res.end(`<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1"><title>Chat UI fixture</title><style>*{box-sizing:border-box}body{margin:0;background:#081522;color:#eee;font-family:system-ui}main{padding:3rem}button,input,textarea{font:inherit}${styles.join('\n')}</style>${settings ? '<main class="social-shell"><h1>Friend settings fixture</h1><div id="root"></div></main>' : '<main><h1>Isolated Starfriends UI</h1><p>No real users or database.</p></main><div id="root"></div>'}<script src="/bundle.js"></script>`); return;
  }
  if (req.url === '/bundle.js') { res.setHeader('Content-Type', 'text/javascript'); res.end(boot); return; }
  if (req.url === '/favicon.ico') { res.writeHead(204).end(); return; }
  let body = ''; for await (const chunk of req) body += chunk;
  const command = JSON.parse(body || '{}');
  if (req.url === '/fixture-peer') { peerIdentity ??= command; res.end('{}'); return; }
  res.setHeader('Content-Type', 'application/json'); res.setHeader('Cache-Control', 'private, no-store');
  if (req.headers['x-asterion-actor'] !== 'actor') { res.writeHead(409).end('{"error":"session_changed"}'); return; }
  let result;
  if (req.url === '/api/friends') {
    if (command.action === 'block') blocked = true;
    result = command.action === 'list' ? { profile: { username: 'StarWalker', discoverable: true, friendCode: ownFriendCode }, friends: blocked ? [] : [{ id: 'friendship', username: 'MoonFox', status: 'accepted', online: true, level: 15 }, { id: 'request', username: 'HiddenPeer', status: 'incoming', online: null, level: null }] } : { ok: true };
    if (command.action === 'search') { friendSearches.push(command); result = { result: command.query.trim().toUpperCase() === otherFriendCode ? { username: 'CocoaCat' } : null }; }
    if (command.action === 'request') friendRequests.push(command);
  } else if (req.url === '/api/chat') {
    if (command.action === 'identity') result = { identity, recoveryMode };
    if (command.action === 'register') {
      registrations.push(command);
      identity ??= command.registration; recoveryCode ??= command.recoveryCode; recoveryMode = 'keycloak';
      if (!registrationDropped) { registrationDropped = true; res.writeHead(503).end('{"error":"temporarily_unavailable"}'); return; }
      result = { identity, recoveryCode };
    }
    if (command.action === 'recover') { recoveries++; result = { identity, recoveryCode }; }
    if (command.action === 'inbox') result = { unread: [] };
    if (command.action === 'open') result = { peerId: 'peer', identity: peerIdentity, messages, hasMore: false };
    if (command.action === 'send') {
      sends.push(command.envelope); const existing = messages.find(message => message.id === command.envelope.id);
      if (!existing) messages.push({ ...command.envelope, sequence: String(messages.length + 1), createdAt: new Date().toISOString() });
      if (!dropped) { dropped = true; res.writeHead(503).end('{"error":"temporarily_unavailable"}'); return; }
      result = { message: messages.find(message => message.id === command.envelope.id) };
    }
    if (command.action === 'read') { readMarkers.push(command.messageId); result = { ok: true }; }
  }
  if (!result) { res.writeHead(404).end('{}'); return; }
  res.end(JSON.stringify(result));
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
let browser;
try {
  browser = await chromium.launch({ channel: process.env.ASTERION_TEST_BROWSER || 'msedge', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage(); const errors = []; page.on('pageerror', error => { errors.push(error.message); console.error('Fixture browser error:', error.message); });
  const url = `http://127.0.0.1:${server.address().port}/`;
  await page.goto(url);
  try { await page.getByRole('button', { name: 'Open conversation with MoonFox' }).click({ timeout: 8000 }); }
  catch (error) { console.error('Fixture initial DOM:', await page.locator('body').innerText()); throw error; }
  assert.equal(await page.getByRole('checkbox').count(), 0);
  assert.equal(await page.getByLabel('Existing recovery code', { exact: true }).count(), 0);
  await page.getByRole('button', { name: 'Enable chat with account recovery' }).click();
  await page.getByRole('button', { name: 'Retry chat activation', exact: true }).click();
  assert.equal(registrations.length, 2); assert.deepEqual(registrations[0], registrations[1]);
  assert.ok(recoveryCode.length > 40);
  assert.equal(await page.locator('body').innerText().then(text => text.includes(recoveryCode)), false);
  await page.getByLabel('Message', { exact: true }).fill('Browser UI secret 🌟'); await page.getByRole('button', { name: 'Send', exact: true }).click();
  await page.getByRole('button', { name: 'Retry encrypted message' }).click();
  await page.getByText('Browser UI secret 🌟', { exact: true }).waitFor();
  assert.equal(messages.length, 1); assert.equal(sends.length, 2); assert.deepEqual(sends[0], sends[1]);
  assert.equal(JSON.stringify(messages).includes('Browser UI secret'), false);
  const reply = await page.evaluate(async own => window.chatFixtureCrypto.encryptMessage(window.fixturePeer.keys, 'actor', own, 'friendship', 'A real encrypted reply 🌟'), identity.identity);
  const readReceipt = page.waitForResponse(response => response.url().endsWith('/api/chat') && response.request().postDataJSON()?.action === 'read' && response.ok());
  messages.push({ ...reply, sequence: '2', createdAt: new Date().toISOString() });
  await page.getByText('A real encrypted reply 🌟', { exact: true }).waitFor();
  await readReceipt;
  assert.ok(readMarkers.includes(reply.id)); assert.ok(!readMarkers.includes(sends[0].id));
  const screenshotDir = process.env.ASTERION_TEST_SCREENSHOTS;
  if (screenshotDir) { await mkdir(screenshotDir, { recursive: true }); await page.screenshot({ path: resolve(screenshotDir, 'messenger-desktop.png') }); }
  await page.getByRole('button', { name: 'Close chat', exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 }); await page.reload();
  await page.getByRole('button', { name: /Expand friends/ }).click(); await page.getByRole('button', { name: 'Open conversation with MoonFox' }).click();
  await page.getByLabel('Message', { exact: true }).waitFor();
  const bounds = await page.getByRole('dialog').boundingBox(); assert.ok(bounds.x >= 0 && bounds.x + bounds.width <= 390 && bounds.height <= 844);
  if (screenshotDir) await page.screenshot({ path: resolve(screenshotDir, 'messenger-mobile.png') });
  await page.keyboard.press('Escape'); assert.equal(await page.getByRole('dialog').count(), 0);
  const fresh = await browser.newContext({ viewport: { width: 1440, height: 1000 } }); const restore = await fresh.newPage();
  restore.on('pageerror', error => errors.push(error.message)); await restore.goto(url);
  await restore.getByRole('button', { name: 'Open conversation with MoonFox' }).click();
  await restore.getByText('Browser UI secret 🌟', { exact: true }).waitFor();
  assert.ok(recoveries > 0); assert.equal(await restore.getByLabel('Existing recovery code', { exact: true }).count(), 0);
  restore.on('dialog', dialog => dialog.accept()); await restore.getByRole('button', { name: 'Block contact', exact: true }).click();
  await restore.getByRole('dialog').waitFor({ state: 'detached' }); assert.equal(blocked, true);
  blocked = false; // Reset only the local fixture for localized layout checks.
  for (const [locale, expand, chat, messageLabel] of [
    ['en', 'Expand friends', 'Open conversation with', 'Message'],
    ['de', 'Freundesliste ausklappen', 'Unterhaltung öffnen mit', 'Nachricht'],
    ['fr', 'Développer la liste d’amis', 'Ouvrir la conversation avec', 'Message'],
    ['es', 'Expandir la lista de amigos', 'Abrir conversación con', 'Mensaje']
  ]) {
    for (const width of [320, 1280]) {
      await page.setViewportSize({width,height:900});
      await page.bringToFront();
      await page.goto(`${url}?locale=${locale}`);
      if (width < 1280) {
        try { await page.getByRole('button', {name:expand,exact:false}).click({timeout:10000}); }
        catch (error) { console.error('Localized fixture:', locale, width, await page.locator('button').evaluateAll(nodes => nodes.map(node => ({label:node.getAttribute('aria-label'),html:node.outerHTML}))), errors); throw error; }
      }
      await page.getByRole('button', {name:`${chat} MoonFox`,exact:true}).click();
      await page.getByLabel(messageLabel,{exact:true}).waitFor();
      const box = await page.getByRole('dialog').boundingBox();
      assert.ok(box.x >= 0 && box.x + box.width <= width && box.height <= 900, `${locale}/${width}: dialog bounds`);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${locale}/${width}: document overflow`);
    }
  }
  // An original, app-only backup must remain manual until explicit migration consent.
  recoveryMode = 'legacy';
  const legacyContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const legacy = await legacyContext.newPage(); legacy.on('pageerror', error => errors.push(error.message));
  await legacy.goto(url); await legacy.getByRole('button', { name: 'Open conversation with MoonFox' }).click();
  await legacy.getByLabel('Existing recovery code', { exact: true }).fill(` ${recoveryCode} `);
  const beforeMigration = registrations.length;
  await legacy.getByRole('button', { name: 'Unlock on this device', exact: true }).click();
  await legacy.getByLabel('Message', { exact: true }).waitFor(); assert.equal(registrations.length, beforeMigration);
  await legacy.getByText('Account recovery is not enabled for this chat', { exact: true }).click();
  await legacy.getByLabel('Existing recovery code', { exact: true }).fill(` ${recoveryCode} `);
  await legacy.getByRole('checkbox').check();
  await legacy.getByRole('button', { name: 'Enable account recovery', exact: true }).click();
  await legacy.getByText('Account recovery is not enabled for this chat', { exact: true }).waitFor({ state: 'detached' });
  assert.equal(registrations.length, beforeMigration + 1);
  assert.equal(registrations.at(-1).registration.identity.fingerprint, identity.identity.fingerprint);
  assert.equal(registrations.at(-1).recoveryCode, recoveryCode);
  // Storage configuration absence may not trigger new identity creation or automatic recovery.
  recoveryMode = 'unavailable';
  const unavailableContext = await browser.newContext({ viewport: { width: 320, height: 900 } });
  const unavailable = await unavailableContext.newPage(); unavailable.on('pageerror', error => errors.push(error.message));
  await unavailable.goto(url); await unavailable.getByRole('button', { name: /Expand friends/ }).click();
  const beforeUnavailable = { registrations: registrations.length, recoveries };
  await unavailable.getByRole('button', { name: 'Open conversation with MoonFox' }).click();
  await unavailable.getByRole('button', { name: 'Try opening chat again', exact: true }).waitFor();
  assert.equal(registrations.length, beforeUnavailable.registrations); assert.equal(recoveries, beforeUnavailable.recoveries);
  await unavailableContext.close(); await legacyContext.close(); recoveryMode = 'keycloak';
  // Actual FriendsClient, independently from the dock: discovery requires a code,
  // while a name is displayed only after previewing a successful code lookup.
  for (const locale of ['en', 'de', 'fr', 'es']) {
    for (const width of [320, 1280]) {
      await page.setViewportSize({ width, height: 900 }); await page.bringToFront();
      await page.goto(`${url}?mode=settings&locale=${locale}`);
      const labels = await page.evaluate(lang => window.fixtureSocialMessages(lang), locale);
      const ownCodeInput = page.getByLabel(labels.friendCode, { exact: true });
      await ownCodeInput.waitFor();
      await page.waitForFunction(value => document.getElementById('own-friend-code')?.value === value, ownFriendCode);
      assert.equal(await ownCodeInput.inputValue(), ownFriendCode); assert.equal(await ownCodeInput.getAttribute('readonly'), '');
      await ownCodeInput.focus();
      assert.deepEqual(await ownCodeInput.evaluate(input => [input.selectionStart, input.selectionEnd]), [0, ownFriendCode.length]);
      assert.equal(await page.getByLabel(labels.username, { exact: true }).inputValue(), 'StarWalker');
      const query = page.getByLabel(labels.query, { exact: true });
      const searchesBefore = friendSearches.length;
      await query.fill('CocoaCat'); await page.getByRole('button', { name: labels.find, exact: true }).click();
      await page.getByText(labels.codeInvalid, { exact: true }).waitFor(); assert.equal(friendSearches.length, searchesBefore);
      await query.fill('child@example.invalid'); await page.getByRole('button', { name: labels.find, exact: true }).click();
      assert.equal(friendSearches.length, searchesBefore);
      await query.fill(` ${otherFriendCode.toLowerCase()} `);
      await page.getByRole('button', { name: labels.find, exact: true }).click();
      const requestButton = page.getByRole('button', { name: labels.request, exact: true });
      await requestButton.waitFor(); await page.getByText('CocoaCat', { exact: false }).waitFor();
      const sent = page.waitForResponse(response => response.url().endsWith('/api/friends') && response.request().postDataJSON()?.action === 'request');
      await requestButton.click(); await sent;
      assert.deepEqual(friendRequests.at(-1), { action: 'request', friendCode: otherFriendCode });
      assert.deepEqual(Object.keys(friendSearches.at(-1)).sort(), ['action', 'query']);
      assert.equal(friendSearches.at(-1).query.trim().toUpperCase(), otherFriendCode);
      assert.equal(friendSearches.length, searchesBefore + 1);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${locale}/${width}: friend settings overflow`);
      const inputBounds = await ownCodeInput.boundingBox(); assert.ok(inputBounds.x >= 0 && inputBounds.x + inputBounds.width <= width);
      if (screenshotDir && locale === 'de') await page.screenshot({ path: resolve(screenshotDir, `friend-code-settings-${width}.png`), fullPage: true });
    }
  }
  assert.deepEqual(errors, []);
  console.log('PASS: hydrated real UI, explicit phase-1 activation without a user code prompt, lost registration response retried identically, automatic fresh-browser recovery/history, legacy manual unlock plus explicit migration, and unavailable-provider denial.');
  console.log('PASS: real encrypted send with identical retry, incoming decryption/read marker, preserved case, mobile bounds, Escape and block-close.');
  console.log('HTTP responses use a local fixture; Keycloak, database and production authorization are not exercised.');
  console.log('PASS: all four locales at 320px and 1280px, no horizontal document overflow or clipped dialog.');
  console.log('PASS: actual friend settings in all four locales at 320px/1280px; own code selectable, case-preserved player name, name/email rejected before lookup, code preview and friendCode-only request, no overflow.');
} finally { await browser?.close(); await new Promise(resolve => server.close(resolve)); }
