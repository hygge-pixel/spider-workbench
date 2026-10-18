import json
from pathlib import Path
import sys
import tempfile
import unittest

from scripts.browser_toolchain import build_definitions, merge_definitions, probe_stdio


class BrowserToolchainTests(unittest.TestCase):
    def test_default_generated_mcp_only_enables_chrome(self):
        definitions = build_definitions(Path('/project'), Path(sys.executable), node=Path(sys.executable))
        self.assertEqual(set(definitions), {'js-reverse'})
        self.assertEqual(definitions['js-reverse']['args'][-1], 'chrome')

    def test_definitions_use_launcher_and_candidate_from_current_workspace(self):
        with tempfile.TemporaryDirectory(prefix='tools space ') as directory:
            root = Path(directory)
            definitions = build_definitions(root, Path(sys.executable), ('chrome', 'cloak'), node=Path(sys.executable))
            for name, candidate in (('js-reverse', 'chrome'), ('js-reverse-cloak', 'cloak')):
                self.assertEqual(definitions[name]['command'], sys.executable)
                self.assertIn(str(root / 'scripts/start_js_reverser.mjs'), definitions[name]['args'])
                self.assertEqual(definitions[name]['args'][-1], candidate)

    def test_merge_preserves_unrelated_settings_and_refuses_named_conflict(self):
        old = {'theme': 'keep', 'mcpServers': {'other': {'command': 'keep'}}}
        new = {'js-reverse': {'command': 'new', 'args': []}}
        merged = merge_definitions(old, new)
        self.assertEqual(merged['theme'], 'keep')
        self.assertEqual(merged['mcpServers']['other'], {'command': 'keep'})
        self.assertNotIn('js-reverse', old['mcpServers'])
        conflict = {'mcpServers': {'js-reverse': {'command': 'old'}}}
        with self.assertRaises(ValueError):
            merge_definitions(conflict, new)
        self.assertEqual(merge_definitions(conflict, new, replace_managed=True)['mcpServers'], new)

    def test_stdio_probe_uses_real_local_protocol_without_browser(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'fake_mcp.py'
            script.write_text('''import sys,json
for line in sys.stdin:
    request=json.loads(line)
    if 'id' not in request: continue
    method=request['method']
    if method=='initialize': result={'protocolVersion':'2024-11-05','capabilities':{'tools':{}},'serverInfo':{'name':'fixture','version':'1'}}
    elif method=='tools/list': result={'tools':[{'name':'list_pages','inputSchema':{'type':'object'}}]}
    else: result={'content':[{'type':'text','text':'private page value must not be returned'}]}
    print(json.dumps({'jsonrpc':'2.0','id':request['id'],'result':result}),flush=True)
''', encoding='utf-8')
            result = probe_stdio([sys.executable, str(script)], Path(directory), {}, live=True)
            self.assertTrue(result['passed'])
            self.assertTrue(result['read_only_tool_passed'])
            self.assertEqual(result['tools'], 1)
            self.assertNotIn('private page', json.dumps(result))

    def test_stdio_probe_does_not_accept_protocol_tool_error(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'bad_mcp.py'
            script.write_text('''import sys,json
for line in sys.stdin:
    r=json.loads(line)
    if 'id' in r: print(json.dumps({'jsonrpc':'2.0','id':r['id'],'error':{'code':-1,'message':'private error'}}),flush=True)
''', encoding='utf-8')
            with self.assertRaises(RuntimeError):
                probe_stdio([sys.executable, str(script)], Path(directory), {}, live=True)


if __name__ == '__main__':
    unittest.main()
