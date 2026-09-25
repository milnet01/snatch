"""Entry point for running as: python -m snatch"""

import sys

from . import HAS_DND
from .logging_setup import configure_logging
from .platform_utils import app_data_dir


def main():
    # `--selftest [REPORT]` checks a packaged build without opening a window;
    # the build scripts run it on every artefact they produce (SNAT-0024).
    if sys.argv[1:2] == ["--selftest"]:
        from .selftest import run
        sys.exit(run(sys.argv[2] if len(sys.argv) > 2 else None))

    # Before anything else, so a failure during startup is recorded too.
    configure_logging(app_data_dir())
    if HAS_DND:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk(className="Snatch")
    else:
        import tkinter as tk
        root = tk.Tk(className="Snatch")

    from .app import SnatchApp
    app = SnatchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
