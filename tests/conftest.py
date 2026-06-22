import sys
from pathlib import Path

# Make scripts/ importable without installing anything heavy.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
