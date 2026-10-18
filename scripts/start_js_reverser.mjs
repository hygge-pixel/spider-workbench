// Keep MCP in the host-owned Node process; preflight Python is short-lived.
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const argv = process.argv.slice(2);
const value = name => argv[argv.indexOf(name) + 1];
const python = value('--python');
const candidate = value('--candidate');
if (!argv.includes('--python') || !argv.includes('--candidate') || !['chrome', 'cloak'].includes(candidate)) {
  console.error('Use --python <project-tool-python> --candidate chrome|cloak');
  process.exit(1);
}
const preflight = spawnSync(python, [path.join(root, 'scripts/start_js_reverser.py'), '--candidate', candidate, '--describe'], {
  cwd: root, encoding: 'utf8', windowsHide: true, timeout: 20000,
});
if (preflight.status !== 0) {
  console.error('Browser preflight failed; run spider.py browser status/ensure for the selected candidate.');
  process.exit(1);
}
const spec = JSON.parse(preflight.stdout);
fs.mkdirSync(spec.cwd, { recursive: true });
process.chdir(spec.cwd);
Object.assign(process.env, spec.env);
process.argv = [process.execPath, spec.command[1], ...spec.command.slice(2)];
await import(pathToFileURL(spec.command[1]).href);
