const {test, after} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const {FILES, build, publicApiBase} = require('../../scripts/build-static.cjs');
const repo = path.resolve(__dirname, '../..');
const temporary = [];
function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'tradepulse-static-'));
  temporary.push(root);
  for (const file of FILES) {
    fs.mkdirSync(path.dirname(path.join(root, file)), {recursive: true});
    fs.copyFileSync(path.join(repo, file), path.join(root, file));
  }
  return root;
}
after(() => temporary.forEach(root => fs.rmSync(root, {recursive: true, force: true})));

test('packaging publishes only the exact allowlist, repeatably, without private inputs', () => {
  const root = fixture();
  for (const file of ['private.db', '.env', 'backup.zip', 'backend/main.py', 'assets/unapproved.txt']) {
    fs.mkdirSync(path.dirname(path.join(root, file)), {recursive: true});
    fs.writeFileSync(path.join(root, file), 'PRIVATE CANARY NEVER PUBLISH');
  }
  const first = build({root});
  assert.deepEqual(build({root}), first);
  assert.deepEqual(first.map(x => x.file), [...FILES]);
  for (const row of first) assert.ok(!fs.readFileSync(path.join(root, 'dist', row.file)).includes(Buffer.from('PRIVATE CANARY')));
  assert.match(fs.readFileSync(path.join(root, 'dist/frontend/config.js'), 'utf8'), /"apiBaseUrl":""/);
});

test('unexpected output and missing assets fail before packaging writes', () => {
  const root = fixture();
  build({root});
  fs.writeFileSync(path.join(root, 'dist/private.db'), 'retain');
  assert.throws(() => build({root}), /Unexpected dist file/);
  assert.equal(fs.readFileSync(path.join(root, 'dist/private.db'), 'utf8'), 'retain');
  fs.unlinkSync(path.join(root, 'dist/private.db'));
  fs.unlinkSync(path.join(root, 'assets/logo/tradepulse-ai-horizontal.png'));
  assert.throws(() => build({root}));
});

test('database bytes and secret patterns hidden in allowed text are rejected', () => {
  for (const content of ['SQLite format 3\0private', '-----BEGIN PRIVATE KEY-----']) {
    const root = fixture();
    fs.writeFileSync(path.join(root, 'app.js'), content);
    assert.throws(() => build({root}), /rejected/);
    assert.equal(fs.existsSync(path.join(root, 'dist')), false);
  }
});

test('linked output cannot redirect packaging outside the disposable fixture', () => {
  const root = fixture();
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'tradepulse-link-target-'));
  temporary.push(outside);
  fs.writeFileSync(path.join(outside, 'retain.txt'), 'unchanged');
  fs.symlinkSync(outside, path.join(root, 'dist'), process.platform === 'win32' ? 'junction' : 'dir');
  assert.throws(() => build({root}), /Linked/);
  assert.deepEqual(fs.readdirSync(outside), ['retain.txt']);
});

test('public configuration accepts HTTPS and rejects credentials or local/private settings', () => {
  assert.equal(publicApiBase('https://api.example.invalid/'), 'https://api.example.invalid');
  for (const value of ['http://example.invalid', 'https://user:secret@example.invalid',
    'https://example.invalid?token=secret', 'https://example.invalid/#secret',
    'https://127.0.0.1', 'javascript:alert(1)']) assert.throws(() => publicApiBase(value));
  const root = fixture();
  build({root, apiBaseUrl: 'https://api.example.invalid'});
  assert.match(fs.readFileSync(path.join(root, 'dist/frontend/config.js'), 'utf8'), /https:\/\/api.example.invalid/);
});

const apiSource = fs.readFileSync(path.join(repo, 'frontend/js/api.js'), 'utf8');
function client(base = '', fetch = () => {throw new Error('Unexpected network request');}) {
  const events = [];
  const context = vm.createContext({window: {TRADEPULSE_CONFIG: {apiBaseUrl: base},
    location: {hostname: 'preview.example.invalid'}, dispatchEvent(e) {events.push(e.type);}},
    URL, Event, AbortController, setTimeout, clearTimeout, performance, console, fetch});
  vm.runInContext(apiSource, context);
  return {api: context.window.TradePulseAPI, events};
}

test('unconfigured frontend makes no network calls and reports offline', async () => {
  const {api} = client();
  assert.equal(await api.pingBackend(), null);
  await assert.rejects(api.getTrades(), /not configured/);
});

test('configured API preserves routes and emits connection loss only for outages', async () => {
  const urls = [];
  const connected = client('https://api.example.invalid', async url => {
    urls.push(url); return {ok: true, status: 200, json: async () => []};
  });
  await connected.api.getTrades();
  assert.deepEqual(urls, ['https://api.example.invalid/api/trades']);
  const offline = client('https://api.example.invalid', async () => {throw new Error('unreachable');});
  await assert.rejects(offline.api.getTrades(), /unreachable/);
  assert.deepEqual(offline.events, ['tradepulse:api-unavailable']);
  const invalid = client('https://api.example.invalid', async () => ({ok: false, status: 422,
    json: async () => ({detail: 'invalid trade'})}));
  await assert.rejects(invalid.api.getTrades(), /invalid trade/);
  assert.deepEqual(invalid.events, []);
  const unavailable = client('https://api.example.invalid', async () => ({ok: false, status: 503,
    json: async () => ({detail: 'database unavailable'})}));
  await assert.rejects(unavailable.api.getTrades(), /database unavailable/);
  assert.deepEqual(unavailable.events, ['tradepulse:api-unavailable']);
  assert.throws(() => client('https://127.0.0.1'), /Invalid public API/);
});

test('HTML nesting, unique IDs, local assets and anchors resolve in packaged pages', () => {
  const root = fixture(); build({root});
  const voidTags = new Set('area base br col embed hr img input link meta param source track wbr'.split(' '));
  for (const file of ['index.html', 'dashboard.html']) {
    const html = fs.readFileSync(path.join(root, 'dist', file), 'utf8');
    const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
    assert.equal(ids.length, new Set(ids).size, `${file} duplicate IDs`);
    const tags = html.replace(/<!--[\s\S]*?-->/g, '').replace(/(<script\b[^>]*>)[\s\S]*?(<\/script>)/g, '$1$2');
    const stack = [];
    for (const match of tags.matchAll(/<(\/?)([a-z][\w-]*)\b[^>]*>/gi)) {
      const [, close, tag] = match;
      if (close) assert.equal(stack.pop(), tag, `${file} mismatched ${tag}`);
      else if (!voidTags.has(tag)) stack.push(tag);
    }
    assert.deepEqual(stack, []);
    for (const [, ref] of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
      if (ref.startsWith('https://')) continue;
      if (ref.startsWith('#')) {assert.ok(ids.includes(ref.slice(1))); continue;}
      assert.ok(FILES.includes(ref.split(/[?#]/)[0]), `${file}: unbundled ${ref}`);
    }
    assert.doesNotMatch(html, /LIVE MARKET SNAPSHOT|LIVE TERMINAL|Live Technical/);
  }
  for (const file of ['styles.css', 'assets/fonts/fonts.css']) {
    const css = fs.readFileSync(path.join(root, 'dist', file), 'utf8');
    for (const [, ref] of css.matchAll(/url\(['"]?([^'"\)]+)['"]?\)/g)) {
      const target = path.posix.normalize(path.posix.join(path.posix.dirname(file), ref));
      assert.ok(FILES.includes(target), `unbundled CSS reference ${target}`);
    }
    const stripped = css.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(['"])(?:\\.|(?!\1)[^\\])*?\1/g, '');
    let depth = 0;
    for (const char of stripped) {
      if (char === '{') depth++;
      if (char === '}') depth--;
      assert.ok(depth >= 0, 'unmatched CSS close brace');
    }
    assert.equal(depth, 0, 'unmatched CSS open brace');
  }
});

test('Vercel serves dist as Other with no Python entrypoint or catch-all rewrite', () => {
  const config = JSON.parse(fs.readFileSync(path.join(repo, 'vercel.json')));
  assert.equal(config.framework, null);
  assert.equal(config.outputDirectory, 'dist');
  assert.equal(config.cleanUrls, true);
  assert.equal(config.buildCommand, 'node scripts/build-static.cjs');
  assert.equal(config.rewrites, undefined);
  assert.equal(config.builds, undefined);
});

test('homepage examples are labeled and unsupported adoption claims are absent', () => {
  const html = fs.readFileSync(path.join(repo, 'index.html'), 'utf8');
  assert.match(html, /Fictional example · not your account/);
  assert.doesNotMatch(html, /data-count|Global active traders|Less emotion-driven leakage|Trader Feedback/);
  const dashboard = fs.readFileSync(path.join(repo, 'dashboard.html'), 'utf8');
  assert.match(dashboard, /id="connectionNotice"/);
  assert.match(dashboard, /id="marketDataNotice"/);
  assert.ok(dashboard.indexOf('src="frontend/config.js"') < dashboard.indexOf('src="frontend/js/api.js'));
});
