/**
 * Runtime path helpers that stay stable even when the host launches the
 * server with an unexpected working directory (for example Windows system32).
 * Modified by Spider Workbench contributors: SPIDER_MCP_RUN_DIR redirects
 * artifacts, debugger sessions and code cache into the workspace run tree.
 */

import {existsSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

function findPackageRoot(fromDir: string): string | undefined {
  let currentDir = fromDir;

  while (true) {
    if (existsSync(path.join(currentDir, 'package.json'))) {
      return currentDir;
    }

    const parentDir = path.dirname(currentDir);
    if (parentDir === currentDir) {
      return undefined;
    }
    currentDir = parentDir;
  }
}

export function resolvePackageRoot(moduleUrl: string): string {
  const packageRoot = findPackageRoot(path.dirname(fileURLToPath(moduleUrl)));
  return packageRoot ?? process.cwd();
}

export function resolveDefaultArtifactsTasksDir(moduleUrl: string): string {
  if (process.env.SPIDER_MCP_RUN_DIR) return path.join(process.env.SPIDER_MCP_RUN_DIR, 'artifacts', 'tasks');
  return path.join(resolvePackageRoot(moduleUrl), 'artifacts', 'tasks');
}

export function resolveDefaultDebuggerSessionsDir(moduleUrl: string): string {
  if (process.env.SPIDER_MCP_RUN_DIR) return path.join(process.env.SPIDER_MCP_RUN_DIR, 'debugger-sessions');
  return path.join(resolvePackageRoot(moduleUrl), 'debugger-sessions');
}

export function resolveDefaultCodeCacheDir(moduleUrl: string): string {
  if (process.env.SPIDER_MCP_RUN_DIR) return path.join(process.env.SPIDER_MCP_RUN_DIR, '.cache', 'code');
  return path.join(resolvePackageRoot(moduleUrl), '.cache', 'code');
}

export function resolveDefaultEnvPath(moduleUrl: string): string {
  return path.join(resolvePackageRoot(moduleUrl), '.env');
}
