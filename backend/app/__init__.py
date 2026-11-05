import sys
from pathlib import Path

# Make the sibling `ai_engine` package importable both locally and in Docker.
_root = str(Path(__file__).resolve().parents[2])
if _root not in sys.path:
    sys.path.insert(0, _root)
