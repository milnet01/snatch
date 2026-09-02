"""Entry point for running as: python -m snatch"""

from . import HAS_DND
from .logging_setup import configure_logging
from .platform_utils import app_data_dir


def main():
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
