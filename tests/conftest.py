"""Make the package importable without installing it.

Snatch is never pip-installed: it is run from source or frozen by PyInstaller,
so there is no editable install to lean on and the repo root has to go on
sys.path explicitly.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
