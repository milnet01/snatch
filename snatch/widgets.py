"""Custom tkinter widgets"""

import tkinter as tk
from .theme import get_theme


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

    def apply_theme(self, theme):
        """Update widget colors for a new theme"""
        self.configure(bg=theme.BG)
        self.label.configure(bg=theme.BG)
        self._draw()

    def grid(self, **kwargs):
        """Grid the switch; label must be placed separately"""
        super().grid(**kwargs)

    def pack(self, **kwargs):
        """Pack the switch only; label must be placed separately"""
        super().pack(**kwargs)
