"""Enable `python -m bookie ...` (so Bookie runs without an editable install)."""
from bookie.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
