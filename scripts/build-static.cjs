// Dependency-free static packaging. No recursive source-directory copying.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const FILES = Object.freeze([
  'index.html', 'dashboard.html', 'styles.css', 'app.js', 'dashboard-ui.js',
  'frontend/config.js', 'frontend/js/api.js',
  'assets/homepage-hero-terminal.png', 'assets/logo/tradepulse-ai-horizontal.png',
  'assets/fonts/fonts.css', 'assets/fonts/inter-0.woff2', 'assets/fonts/inter-OFL.txt',
  'assets/fonts/jetbrainsmono-0.woff2', 'assets/fonts/jetbrainsmono-1.woff2',
  'assets/fonts/jetbrainsmono-OFL.txt', 'assets/fonts/plusjakartasans-0.woff2',
  'assets/fonts/plusjakartasans-OFL.txt',
]);

function publicApiBase(value = '') {
  if (!value) return '';
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash ||
      ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) {
    throw new Error('Public API URL must be HTTPS without credentials, query, fragment, or loopback host.');
  }
  return url.href.replace(/\/$/, '');
}

function assertNoLinks(root, relative) {
  let current = root;
  if (fs.lstatSync(current).isSymbolicLink()) throw new Error('Linked root rejected');
  for (const part of relative.split('/')) {
    current = path.join(current, part);
    if (fs.existsSync(current) && fs.lstatSync(current).isSymbolicLink()) {
      throw new Error(`Linked file/directory rejected: ${relative}`);
    }
  }
}

function listedFiles(root, prefix = '') {
  return fs.readdirSync(path.join(root, prefix), {withFileTypes: true}).flatMap(entry => {
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
    assertNoLinks(root, relative);
    if (entry.isDirectory()) return listedFiles(root, relative);
    if (!entry.isFile()) throw new Error(`Unsupported output entry: ${relative}`);
    return [relative];
  });
}

function scan(relative, bytes) {
  if (bytes.includes(Buffer.from('SQLite format 3\0'))) throw new Error(`Database content rejected: ${relative}`);
  if (/\.(?:js|css|html|txt)$/.test(relative)) {
    const text = bytes.toString('utf8');
    if (/-----BEGIN (?:[A-Z ]*PRIVATE KEY)-----|\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16}|sk-(?:proj-)?[A-Za-z0-9_-]{30,})/.test(text)) {
      throw new Error(`Potential secret rejected: ${relative}`);
    }
  }
}

function build({root = path.resolve(__dirname, '..'), apiBaseUrl = ''} = {}) {
  root = path.resolve(root);
  const output = path.join(root, 'dist');
  const api = publicApiBase(apiBaseUrl);
  const content = new Map();
  // Validate every input and any existing output before writing anything.
  for (const relative of FILES) {
    assertNoLinks(root, relative);
    if (!fs.statSync(path.join(root, relative)).isFile()) throw new Error(`Missing file: ${relative}`);
    let bytes = fs.readFileSync(path.join(root, relative));
    if (relative === 'frontend/config.js') {
      bytes = Buffer.from('// Public deployment configuration; no credentials.\nwindow.TRADEPULSE_CONFIG = Object.freeze(' + JSON.stringify({apiBaseUrl: api}) + ');\n');
    }
    scan(relative, bytes);
    content.set(relative, bytes);
  }
  assertNoLinks(root, 'dist');
  if (fs.existsSync(output)) {
    for (const relative of listedFiles(output)) {
      if (!FILES.includes(relative)) throw new Error(`Unexpected dist file; refusing to publish: ${relative}`);
    }
  }
  for (const [relative, bytes] of content) {
    const target = path.join(output, relative);
    fs.mkdirSync(path.dirname(target), {recursive: true});
    fs.writeFileSync(target, bytes);
  }
  return [...content].map(([file, bytes]) => ({file, bytes: bytes.length,
    sha256: crypto.createHash('sha256').update(bytes).digest('hex')}));
}

if (require.main === module) {
  try {
    const manifest = build({apiBaseUrl: process.env.TRADEPULSE_PUBLIC_API_BASE_URL || ''});
    console.log(JSON.stringify({output: 'dist', files: manifest}, null, 2));
  } catch (error) {
    // Never echo environment values or invalid URLs, which could contain secrets.
    console.error('Static packaging failed: ' + (error.code || 'input/output safety validation failed'));
    process.exitCode = 1;
  }
}
module.exports = {FILES, build, publicApiBase};
