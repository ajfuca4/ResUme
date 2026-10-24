"""Dark, card-based widget kit for the Resume Builder (pure tkinter).

Tk has no native rounded corners, so cards, buttons and checkboxes are drawn
on small Canvas widgets using smoothed polygons.
"""
import tkinter as tk
import tkinter.font as tkfont

# ---------------------------------------------------------------------------
# Palette: layered shades of black / grey (darker = further back)
# ---------------------------------------------------------------------------
BG_APP = "#0a0a0b"          # window background
BG_BAR = "#111113"          # bottom action bar
BG_SECTION = "#17171a"      # section cards
BG_ITEM = "#222226"         # subsection cards (items / lines)
BG_INPUT = "#2c2c31"        # text inputs
BORDER_BAR = "#1f1f23"
BORDER_SECTION = "#26262b"
BORDER_ITEM = "#313137"
BORDER_INPUT = "#3b3b42"
FOCUS_RING = "#9a9aa3"
FG = "#ececef"
FG_MUTED = "#a1a1aa"
FG_DIM = "#6b6b74"
DANGER = "#f87171"
SELECT_BG = "#4b4b53"

UI_FONT = "Helvetica Neue"
F_TITLE = (UI_FONT, 20, "bold")
F_SUBTITLE = (UI_FONT, 12)
F_SECTION = (UI_FONT, 16, "bold")
F_BODY = (UI_FONT, 12)
F_BODY_B = (UI_FONT, 12, "bold")
F_BODY_I = (UI_FONT, 12, "italic")
F_LABEL = (UI_FONT, 10)
F_TAG = (UI_FONT, 9, "bold")
F_BTN = (UI_FONT, 11)
F_BTN_B = (UI_FONT, 12, "bold")
F_ICON = (UI_FONT, 10)


def shade(hex_color, amount):
    """Lighten (amount > 0) or darken (amount < 0) a hex colour."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if amount >= 0:
        r, g, b = (int(c + (255 - c) * amount) for c in (r, g, b))
    else:
        r, g, b = (int(c * (1 + amount)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def rounded_points(x1, y1, x2, y2, r):
    """Point list for a smoothed polygon that renders as a rounded rectangle."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1,
        x2, y1, x2, y1 + r, x2, y1 + r, x2, y2 - r, x2, y2 - r,
        x2, y2, x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1,
    ]


_font_cache = {}


def _font(spec):
    if spec not in _font_cache:
        _font_cache[spec] = tkfont.Font(font=spec)
    return _font_cache[spec]


class RoundedCard(tk.Canvas):
    """A rounded-rectangle card. Put child widgets inside `card.inner`.

    The card auto-sizes its height to the content and stretches to the width
    it is packed into.
    """

    def __init__(self, parent, bg, parent_bg, border=None, radius=14, padx=14, pady=12):
        super().__init__(parent, bg=parent_bg, highlightthickness=0, bd=0,
                         width=1, height=2 * pady)
        self.card_bg = bg
        self.border = border or bg
        self.radius = radius
        self.padx = padx
        self.pady = pady
        self._cw = 1  # NOTE: never use self._w — tkinter uses it for the widget path
        self._ch = 2 * pady

        self.inner = tk.Frame(self, bg=bg)
        self._win = self.create_window(padx, pady, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._sync_height)
        self.bind("<Configure>", self._on_resize)

    def set_padding(self, pady):
        self.pady = pady
        self.coords(self._win, self.padx, self.pady)
        self._sync_height()

    def _sync_height(self, _event=None):
        h = self.inner.winfo_reqheight() + 2 * self.pady
        if int(float(self.cget("height"))) != h:
            self.configure(height=h)

    def _on_resize(self, event):
        self._cw, self._ch = event.width, event.height
        self.itemconfigure(self._win, width=max(1, event.width - 2 * self.padx))
        self._redraw()

    def _redraw(self):
        self.delete("card")
        if self._cw < 4 or self._ch < 4:
            return
        self.create_polygon(
            rounded_points(0, 0, self._cw - 1, self._ch - 1, self.radius),
            smooth=True, fill=self.card_bg, outline=self.border, width=1, tags="card",
        )
        self.tag_lower("card")


class PillButton(tk.Canvas):
    """Flat rounded button with hover state (works on macOS, unlike tk.Button bg)."""

    def __init__(self, parent, text, command, parent_bg, bg=None, fg=FG, hover_bg=None,
                 font=F_BTN, padx=12, pady=5, radius=8, border=None):
        self._bg = bg if bg is not None else parent_bg
        self._hover = hover_bg or shade(self._bg, 0.08)
        f = _font(font)
        w = f.measure(text) + 2 * padx
        h = f.metrics("linespace") + 2 * pady
        super().__init__(parent, width=w, height=h, bg=parent_bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._shape = self.create_polygon(
            rounded_points(0, 0, w - 1, h - 1, radius), smooth=True,
            fill=self._bg, outline=border or self._bg,
        )
        self.create_text(w / 2, h / 2, text=text, fill=fg, font=font)
        self._command = command
        self.bind("<Enter>", lambda e: self.itemconfigure(self._shape, fill=self._hover))
        self.bind("<Leave>", lambda e: self.itemconfigure(self._shape, fill=self._bg))
        self.bind("<Button-1>", self._click)

    def _click(self, _event):
        try:
            self.winfo_toplevel().focus_set()  # commit/autosave any field being edited
        except tk.TclError:
            pass
        if self._command:
            self._command()
        return "break"


class Toggle(tk.Canvas):
    """Rounded checkbox bound to a tk.BooleanVar."""

    SIZE = 18

    def __init__(self, parent, variable, parent_bg, command=None, size=None):
        self.size = size or self.SIZE
        super().__init__(parent, width=self.size, height=self.size, bg=parent_bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.var = variable
        self.command = command
        self.bind("<Button-1>", self._click)
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self.size
        r = max(2, int(s * 0.28))
        pts = rounded_points(1, 1, s - 2, s - 2, r)
        if self.var.get():
            self.create_polygon(pts, smooth=True, fill=FG, outline=FG)
            self.create_line(s * 0.25, s * 0.52, s * 0.44, s * 0.72, s * 0.75, s * 0.3,
                             fill=BG_APP, width=max(1.5, s * 0.11),
                             capstyle="round", joinstyle="round")
        else:
            self.create_polygon(pts, smooth=True, fill="", outline=FG_DIM, width=1.5)

    def _click(self, _event):
        try:
            self.winfo_toplevel().focus_set()
        except tk.TclError:
            pass
        self.var.set(not self.var.get())
        self._draw()
        if self.command:
            self.command()
        return "break"


def make_entry(parent, font=F_BODY, width=None, bg=BG_INPUT, fg=FG, ring=BORDER_INPUT):
    kw = dict(
        font=font, bg=bg, fg=fg, insertbackground=FG,
        selectbackground=SELECT_BG, selectforeground=FG,
        relief="flat", bd=5, highlightthickness=1,
        highlightbackground=ring, highlightcolor=FOCUS_RING,
    )
    if width:
        kw["width"] = width
    return tk.Entry(parent, **kw)


def make_text(parent, height=2, bg=BG_INPUT):
    return tk.Text(
        parent, height=height, wrap="word", font=F_BODY, bg=bg, fg=FG,
        insertbackground=FG, selectbackground=SELECT_BG, selectforeground=FG,
        relief="flat", bd=0, padx=8, pady=6, highlightthickness=1,
        highlightbackground=BORDER_INPUT, highlightcolor=FOCUS_RING,
    )


def make_label(parent, text, bg, fg=FG_MUTED, font=F_LABEL):
    return tk.Label(parent, text=text, bg=bg, fg=fg, font=font)
