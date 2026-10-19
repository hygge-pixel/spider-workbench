"""Generate/apply/remove a bounded Cordis overlay; preserve all unrelated profile text."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BEGIN = '# Spider Workbench js-reverse BEGIN\n'
END = '# Spider Workbench js-reverse END\n'


def read_text_exact(path):
    with Path(path).open('r', encoding='utf-8', newline='') as stream:
        return stream.read()


def block(root, definition):
    identifier = hashlib.sha256(str(Path(root).resolve()).encode('utf-8')).hexdigest()[:12]
    entry = {'id': 'mcp-spider-workbench-' + identifier, 'name': '@deepseek-ai/dsh-mcp-client',
             'config': {'serverName': 'js-reverse', 'transport': 'stdio', 'command': definition['command'],
                        'args': definition['args'], 'cwd': str(Path(root).resolve()), 'failOnStartupError': False}}
    # JSON flow collections and quoted strings are valid YAML 1.2; no YAML dependency needed.
    return BEGIN + '- insert: ' + json.dumps([entry], ensure_ascii=True) + '\n' + END


def split_managed(text):
    if BEGIN not in text and END not in text:
        return text, ''
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError('harness_managed_block_requires_review')
    start, stop = text.index(BEGIN), text.index(END) + len(END)
    if stop <= start:
        raise ValueError('harness_managed_block_requires_review')
    return text[:start] + text[stop:], text[start:stop]


def write_backed_up(path, text):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if path.exists():
        backup = path.with_name(path.name + '.bak-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
        with backup.open('xb') as stream:
            stream.write(path.read_bytes())
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False, newline='') as stream:
        stream.write(text)
        temporary = Path(stream.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return str(backup) if backup else None


def configure(root, path, definition, replace_managed=False):
    path = Path(path)
    text = read_text_exact(path) if path.is_file() else ''
    remaining, managed = split_managed(text)
    expected = block(root, definition)
    if re.search(r'["\']?serverName["\']?\s*:\s*["\']?js-reverse\b', remaining):
        raise ValueError('harness_unmanaged_service_name_conflict; review existing service')
    if managed:
        prior = json.loads(managed.split('- insert: ', 1)[1].split('\n', 1)[0])[0]
        if prior['config']['cwd'] != str(Path(root).resolve()):
            raise ValueError('harness_other_project_conflict; select a separate profile')
    if managed == expected:
        return {'passed': True, 'action': 'reused', 'patch': str(path)}
    if managed and not replace_managed:
        raise ValueError('harness_managed_service_conflict; review before --replace-managed')
    if remaining and not remaining.endswith('\n'):
        raise ValueError('harness_profile_needs_final_newline; review file before merge')
    backup = write_backed_up(path, remaining + expected)
    return {'passed': True, 'action': 'configured', 'patch': str(path), 'backup': backup,
            'host_tool_call_passed': None, 'scope': 'selected profile; other workspaces using it also see this server'}


def remove(root, path):
    path = Path(path)
    remaining, managed = split_managed(read_text_exact(path))
    if not managed:
        return {'passed': True, 'action': 'already_absent'}
    # Do not remove another project's entry.
    entry = json.loads(managed.split('- insert: ', 1)[1].split('\n', 1)[0])[0]
    if entry['config']['cwd'] != str(Path(root).resolve()):
        raise ValueError('harness_other_project_conflict')
    return {'passed': True, 'action': 'removed', 'backup': write_backed_up(path, remaining)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('generate', 'apply', 'remove'))
    parser.add_argument('--patch', type=Path, help='actual selected Harness profile cordis.patch.yml; no guessed global path')
    parser.add_argument('--replace-managed', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'remove':
            if not args.patch:
                parser.error('remove requires --patch')
            result = remove(ROOT, args.patch)
        else:
            generated = ROOT / 'runs/_mcp/generated/mcp_config.json'
            definition = json.loads(generated.read_text('utf-8'))['mcpServers']['js-reverse']
            path = args.patch if args.action == 'apply' else ROOT / 'runs/_mcp/generated/deepseek-harness.patch.yml'
            if path is None:
                parser.error('apply requires --patch')
            result = configure(ROOT, path, definition, args.replace_managed)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except (ValueError, OSError, KeyError):
        print(json.dumps({'passed': False, 'code': 'harness_configuration_requires_review; preserve_profile_and_read_guide'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
