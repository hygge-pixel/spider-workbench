// Local regression for Spider Workbench changes to the bundled MCP.
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {test} from 'node:test';
import {McpContext} from '../vendor/js-reverse-mcp/build/src/McpContext.js';
import {BrowserManager} from '../vendor/js-reverse-mcp/build/src/browser.js';
import {McpResponse} from '../vendor/js-reverse-mcp/build/src/McpResponse.js';
import {checkBrowserHealth} from '../vendor/js-reverse-mcp/build/src/tools/page.js';
import {getJSHookRuntime} from '../vendor/js-reverse-mcp/build/src/tools/runtime.js';
// The pre-fix handler used this secondary controller and could launch a real
// browser. Keep the red regression strictly offline as well.
getJSHookRuntime().pageController.getPage = async () => {throw new Error('offline: no secondary page');};

async function health(context) {
  const lines=[];
  await checkBrowserHealth.handler({}, {appendResponseLine: line => lines.push(line)}, context);
  return JSON.parse(lines.slice(1,-1).join('\n'));
}

test('health uses the actual MCP browser even without an active page', async () => {
  const result = await health({isBrowserConnected:()=>true, getSelectedPage:() => {throw new Error('No page selected');}});
  assert.equal(result.connected, true);
  assert.equal(result.pageReady, false);
  assert.equal(result.state, 'connected_no_active_page');
  assert.equal(result.healthy, false);
  assert.deepEqual(result.issues.map(x=>x.code), ['NO_ACTIVE_PAGE']);
  assert.ok(!result.recommendations.some(x=>/reconnect/i.test(x)));
});

test('health reports a disconnected MCP without claiming a usable page', async () => {
  const result = await health({isBrowserConnected:()=>false, getSelectedPage:() => {throw new Error('No page selected');}});
  assert.equal(result.connected, false);
  assert.equal(result.state, 'disconnected');
  assert.ok(result.issues.some(x=>x.code==='BROWSER_DISCONNECTED'));
});

test('health probes the page selected in the current MCP context', async () => {
  const result = await health({isBrowserConnected:()=>true, getSelectedPage:() => ({
    url:()=>'about:blank', title:async()=>'', evaluate:async()=>2,
  })});
  assert.equal(result.healthy, true);
  assert.equal(result.pageReady, true);
  assert.equal(result.state, 'ready');
});

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
