import os
import sys
from pathlib import Path

# Set up clean environment paths for xdrop core
engine_dir = Path(__file__).resolve().parent.parent
if str(engine_dir) not in sys.path:
    sys.path.insert(0, str(engine_dir))

# Also add current directory if running in installed flat mode
cur_dir = Path(__file__).resolve().parent
if str(cur_dir) not in sys.path:
    sys.path.insert(0, str(cur_dir))

from xdrop.main import main

if __name__ == "__main__":
    main()
