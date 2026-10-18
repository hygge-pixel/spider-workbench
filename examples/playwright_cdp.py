"""Browser connection diagnostic using a synthetic tab; not a data-collection runner."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.browser_toolchain import cdp_smoke

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--candidate', choices=('chrome', 'cloak'), required=True)
args = parser.parse_args()
print(json.dumps(cdp_smoke(args.candidate), ensure_ascii=False, indent=2))
