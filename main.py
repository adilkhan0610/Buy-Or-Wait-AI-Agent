"""Root entry point for Buy or Wait? AI-Powered Financial Decision Agent.

Redirects directly to code.main.main().
"""

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from code.main import main

if __name__ == "__main__":
    sys.exit(main())

