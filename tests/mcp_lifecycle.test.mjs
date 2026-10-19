// Local regression for Spider Workbench changes to the bundled MCP.
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {test} from 'node:test';
import {McpContext} from '../vendor/js-reverse-mcp/build/src/McpContext.js';
import {BrowserManager} from '../vendor/js-reverse-mcp/build/src/browser.js';
import {McpResponse} from '../vendor/js-reverse-mcp/build/src/McpResponse.js';

test('filtered welcome page / zero visible pages is a valid read-only snapshot', async () => {
  const browser = new EventEmitter();
  browser.pages = async () => [];
  const context = await McpContext.from(browser, () => {}, {experimentalDevToolsDebugging:false});
  assert.deepEqual(await context.createPagesSnapshot(), []);
  assert.throws(() => context.getSelectedPage(), /No page selected/);
  const response=new McpResponse();
  response.setIncludePages(true);
  const content=await response.handle('list_pages', context);
  assert.match(content.map(item=>item.text ?? '').join(''), /## Pages/);
  context.dispose();
});

test('closing an attached remote MCP disconnects without closing the project browser', async () => {
  const manager = BrowserManager.getInstance({browserURL:'http://127.0.0.1:9222'});
  let disconnected=0, closed=0;
  manager.browser = {disconnect:() => {disconnected++;},close:async () => {closed++;}};
  await manager.close();
  assert.equal(closed, 0);
  assert.equal(disconnected, 1);
});
