"""Entry point for running as: python -m snatch"""

from . import HAS_DND


def main():
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
