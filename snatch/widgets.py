"""Custom tkinter widgets"""

import sys
import tkinter as tk

from .theme import get_theme


def attach_context_menu(widget, editable=True):
    """Give an Entry or Text a right-click Cut / Copy / Paste / Select All menu.

    The menu is a child of the widget, so it is destroyed with it — a theme
    switch rebuilds every widget, which rebuilds the menu in the new colours
    and leaves nothing to clean up.

    Right-click is Button-3 everywhere except macOS, where Tk reports it as
    Button-2. Binding Button-2 on X11 would shadow middle-click paste of the
    primary selection, so the sequence is chosen per platform, not both.
    """
    theme = get_theme()
    menu = tk.Menu(widget, tearoff=0,
                   bg=theme.BG_LIGHT, fg=theme.FG,
                   activebackground=theme.ACCENT,
                   activeforeground=theme.BUTTON_FG,
                   borderwidth=1, relief="solid")

    def _emit(virtual_event):
        return lambda: widget.event_generate(virtual_event)

    def _select_all():
        if isinstance(widget, tk.Text):
            widget.tag_add(tk.SEL, "1.0", "end-1c")
        else:
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)

    if editable:
        menu.add_command(label="Cut", command=_emit("<<Cut>>"))
    menu.add_command(label="Copy", command=_emit("<<Copy>>"))
    if editable:
        menu.add_command(label="Paste", command=_emit("<<Paste>>"))
    menu.add_separator()
    menu.add_command(label="Select All", command=_select_all)

    def _popup(event):
        widget.focus_set()
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    widget.bind("<Button-2>" if sys.platform == "darwin" else "<Button-3>", _popup)
    return menu


class ToggleSwitch(tk.Canvas):
    """A custom on/off toggle switch widget"""

    WIDTH = 50
    HEIGHT = 26
    PAD = 3

    def __init__(self, parent, variable, on_text="Merge Audio", off_text="Format Only",
                 on_color=None, off_color=None, **kwargs):
        theme = get_theme()
        if on_color is None:
            on_color = theme.SUCCESS
        if off_color is None:
            off_color = theme.BG_LIGHTER
        super().__init__(parent, width=self.WIDTH, height=self.HEIGHT,
                         bg=theme.BG, highlightthickness=0, **kwargs)
        self.variable = variable
        self.on_text = on_text
        self.off_text = off_text
        self.on_color = on_color
        self.off_color = off_color

        self.label = tk.Label(parent, text="", font=("Helvetica", 9, "bold"),
                              bg=theme.BG, fg=theme.FG)

        self.bind("<Button-1>", self._toggle)
        self.label.bind("<Button-1>", self._toggle)

        self._last_drawn_value = None

        # Watch variable changes (store trace ID for cleanup)
        self._trace_id = self.variable.trace_add("write", self._on_var_change)
        self._draw()

    def cleanup(self):
        """Remove variable trace to prevent callback accumulation"""
        if self._trace_id is not None:
            try:
                self.variable.trace_remove("write", self._trace_id)
            except (tk.TclError, ValueError):
                pass
            self._trace_id = None

    def _toggle(self, event=None):
        self.variable.set(0 if self.variable.get() else 1)

    def _on_var_change(self, *args):
        # Skip redraw if visual state hasn't changed
        current = self.variable.get()
        if current == self._last_drawn_value:
            return
        self._draw()

    def _draw(self):
        theme = get_theme()
        self.delete("all")
        is_on = self.variable.get() == 1
        self._last_drawn_value = self.variable.get()
        w, h, pad = self.WIDTH, self.HEIGHT, self.PAD
        r = h // 2

        # Track (pill shape)
        track_color = self.on_color if is_on else self.off_color
        self.create_oval(0, 0, h, h, fill=track_color, outline=track_color)
        self.create_oval(w - h, 0, w, h, fill=track_color, outline=track_color)
        self.create_rectangle(r, 0, w - r, h, fill=track_color, outline=track_color)

        # Knob
        knob_r = r - pad
        if is_on:
            cx = w - r
        else:
            cx = r
        self.create_oval(cx - knob_r, pad, cx + knob_r, h - pad,
                         fill=theme.KNOB, outline=theme.KNOB)

        # Update label text
        self.label.config(text=self.on_text if is_on else self.off_text,
                          fg=self.on_color if is_on else theme.FG_DIM)

    def grid(self, **kwargs):
        """Grid the switch; label must be placed separately"""
        super().grid(**kwargs)

    def pack(self, **kwargs):
        """Pack the switch only; label must be placed separately"""
        super().pack(**kwargs)
