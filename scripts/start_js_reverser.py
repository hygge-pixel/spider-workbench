"""Read-only browser preflight descriptor for start_js_reverser.mjs."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.browser_toolchain import launch_spec
from spider_core.browser import status_browser_candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', choices=('chrome', 'cloak'), required=True)
    parser.add_argument('--describe', action='store_true', required=True)
    args = parser.parse_args()
    try:
        status_browser_candidate(ROOT, args.candidate)
        command, runtime, overrides = launch_spec(args.candidate)
        import json
        print(json.dumps({'command': command, 'cwd': str(runtime), 'env': overrides}))
        return 0
    except Exception as error:
        print('JSReverser preflight failed: ' + type(error).__name__ +
              '; run spider.py browser status/ensure for the chosen candidate.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
