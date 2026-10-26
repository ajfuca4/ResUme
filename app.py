import sys
import os

# Auto-re-execute using the project's virtual environment if dependencies are missing in global python
_venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "bin", "python3")
if os.path.exists(_venv_python) and os.path.realpath(sys.executable) != os.path.realpath(_venv_python):
    try:
        import yaml
    except ImportError:
        os.execv(_venv_python, [_venv_python] + sys.argv)

import tkinter as tk
from tkinter import messagebox, ttk, filedialog, font as tkfont
import yaml
import shutil
import subprocess
import threading
import queue
from jinja2 import Environment, FileSystemLoader
from ui_widgets import *  # dark theme palette, fonts, RoundedCard, PillButton, Toggle, inputs
from pdf_preview import PDFPreviewPane, PDFPreviewWindow

# 1. Load or initialize master YAML file
def load_data():
    if os.path.exists("master.yaml"):
        with open("master.yaml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    # If sections is not already structured in master.yaml, convert/initialize it
    if "sections" not in data:
        exp_entries = []
        for job in data.get("experiences", []):
            bullets = [
                {"enabled": True, "text": b} if isinstance(b, str) else b
                for b in job.get("bullets", [])
            ]
            exp_entries.append({
                "enabled": True,
                "field1": job.get("title", ""),
                "field2": job.get("dates", ""),
                "field3": job.get("company", ""),
                "field4": job.get("location", ""),
                "bullets": bullets
            })

        default_sections = [
            {
                "title": "Education",
                "enabled": True,
                "entries": [
                    {
                        "enabled": True,
                        "field1": "Southwestern University",
                        "field2": "Aug. 2018 -- May 2021",
                        "field3": "Bachelor of Arts in Computer Science, Minor in Business",
                        "field4": "Georgetown, TX",
                        "bullets": []
                    },
                    {
                        "enabled": True,
                        "field1": "Blinn College",
                        "field2": "Aug. 2014 -- May 2018",
                        "field3": "Associate's in Liberal Arts",
                        "field4": "Bryan, TX",
                        "bullets": []
                    }
                ],
                "simple_lines": []
            },
            {
                "title": "Experience",
                "enabled": True,
                "entries": exp_entries,
                "simple_lines": []
            },
            {
                "title": "Projects",
                "enabled": True,
                "entries": [
                    {
                        "type": "single-line",
                        "enabled": True,
                        "title": "Gitlytics",
                        "subtitle": "Python, Flask, React, PostgreSQL, Docker",
                        "date": "June 2020 -- Present",
                        "bullets": [
                            {"enabled": True, "text": "Developed a full-stack web application using with Flask serving a REST API with React as the frontend"},
                            {"enabled": True, "text": "Implemented GitHub OAuth to get data from user’s repositories"},
                            {"enabled": True, "text": "Visualized GitHub data to show collaboration"},
                            {"enabled": True, "text": "Used Celery and Redis for asynchronous tasks"}
                        ]
                    },
                    {
                        "type": "single-line",
                        "enabled": True,
                        "title": "Simple Paintball",
                        "subtitle": "Spigot API, Java, Maven, TravisCI, Git",
                        "date": "May 2018 -- May 2020",
                        "bullets": [
                            {"enabled": True, "text": "Developed a Minecraft server plugin to entertain kids during free time for a previous job"},
                            {"enabled": True, "text": "Published plugin to websites gaining 2K+ downloads and an average 4.5/5-star review"},
                            {"enabled": True, "text": "Implemented continuous delivery using TravisCI to build the plugin upon new a release"},
                            {"enabled": True, "text": "Collaborated with Minecraft server administrators to suggest features and get feedback about the plugin"}
                        ]
                    }
                ],
                "simple_lines": []
            },
            {
                "title": "Technical Skills",
                "enabled": True,
                "entries": [],
                "simple_lines": [
                    {"enabled": True, "label": "Languages", "text": "Java, Python, C/C++, SQL (Postgres), JavaScript, HTML/CSS, R"},
                    {"enabled": True, "label": "Frameworks", "text": "React, Node.js, Flask, JUnit, WordPress, Material-UI, FastAPI"},
                    {"enabled": True, "label": "Developer Tools", "text": "Git, Docker, TravisCI, Google Cloud Platform, VS Code, Visual Studio, PyCharm, IntelliJ, Eclipse"},
                    {"enabled": True, "label": "Libraries", "text": "pandas, NumPy, Matplotlib"}
                ]
            }
        ]
        data["sections"] = default_sections

    # Header links (identifier shown on the resume + the URL it points to).
    # Migrate the legacy `contact` block on first run.
    if "links" not in data:
        contact = data.pop("contact", {}) or {}
        links = []
        if contact.get("phone"):
            links.append({"enabled": True, "label": contact["phone"], "type": "phone"})
        if contact.get("email"):
            links.append({"enabled": True, "label": contact["email"], "url": f"mailto:{contact['email']}"})
        data["links"] = links
    else:
        for item in data.get("links", []):
            if item.get("type") == "phone" or (item.get("url") == "" and any(c.isdigit() for c in str(item.get("label", "")))):
                item["type"] = "phone"
                item.pop("url", None)

    # Keep the header fields at the top of master.yaml
    ordered = {"name": data.pop("name", ""), "links": data.pop("links", [])}
    ordered.update(data)
    return ordered

master_data = load_data()

# 2. Setup native desktop window
root = tk.Tk()
root.title("Local Resume Builder - Dynamic Section Editor")

screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
win_w = min(1440, max(1000, screen_w - 60))
win_h = min(920, screen_h - 70)
pos_x = max(10, (screen_w - win_w) // 2)
pos_y = max(30, (screen_h - win_h) // 2)
root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
root.minsize(1000, 500)
root.configure(bg=BG_APP)

# Dark, arrow-less scrollbar ('clam' theme allows full colour control on macOS)
_style = ttk.Style(root)
_style.theme_use("clam")
_style.layout("Dark.Vertical.TScrollbar", [
    ("Vertical.Scrollbar.trough", {
        "sticky": "ns",
        "children": [("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})],
    })
])
_style.configure(
    "Dark.Vertical.TScrollbar",
    background=BG_ITEM, troughcolor=BG_APP, bordercolor=BG_APP,
    lightcolor=BG_ITEM, darkcolor=BG_ITEM, gripcount=0, relief="flat", width=10,
)
_style.map("Dark.Vertical.TScrollbar", background=[("active", BORDER_INPUT), ("pressed", BORDER_INPUT)])

root.option_add("*TCombobox*Listbox.background", BG_ITEM)
root.option_add("*TCombobox*Listbox.foreground", FG)
root.option_add("*TCombobox*Listbox.selectBackground", SELECT_BG)
root.option_add("*TCombobox*Listbox.selectForeground", FG)
root.option_add("*TCombobox*Listbox.relief", "flat")
root.option_add("*TCombobox*Listbox.font", F_BODY)

_style.configure(
    "Dark.TCombobox",
    fieldbackground=BG_INPUT,
    background=BG_INPUT,
    foreground=FG,
    arrowcolor=FG_MUTED,
    bordercolor=BORDER_INPUT,
    lightcolor=BORDER_INPUT,
    darkcolor=BORDER_INPUT,
    relief="flat",
    padding=(8, 5)
)
_style.map(
    "Dark.TCombobox",
    fieldbackground=[("readonly", BG_INPUT), ("active", BG_INPUT)],
    background=[("pressed", BG_INPUT), ("active", BG_INPUT), ("readonly", BG_INPUT)],
    foreground=[("readonly", FG), ("active", FG)],
    arrowcolor=[("pressed", FG), ("readonly", FG_MUTED)],
    selectbackground=[("readonly", BG_INPUT)],
    selectforeground=[("readonly", FG)],
    bordercolor=[("focus", FOCUS_RING)]
)

# Header Section
header_frame = tk.Frame(root, bg=BG_APP, padx=28, pady=18)
header_frame.pack(fill="x")

tk.Label(
    header_frame,
    text="ResUme",
    font=F_TITLE,
    bg=BG_APP,
    fg=FG
).pack(anchor="w")

tk.Label(
    header_frame,
    text="Build, toggle, and edit custom sections, subheaders, and bullets.",
    font=F_SUBTITLE,
    bg=BG_APP,
    fg=FG_MUTED
).pack(anchor="w", pady=(2, 0))

# Bottom Action Toolbar (docked cleanly to bottom before expandable center)
action_frame = tk.Frame(root, pady=12, bg=BG_BAR)
action_frame.pack(side="bottom", fill="x")
tk.Frame(root, bg=BORDER_BAR, height=1).pack(side="bottom", fill="x")
autosave_lbl = None

# Horizontal Paned Window splitting Editor (Left) and Live Preview (Right)
content_paned = tk.PanedWindow(
    root,
    orient=tk.HORIZONTAL,
    bg=BORDER_BAR,
    sashwidth=4,
    sashpad=0,
    bd=0,
    opaqueresize=True
)
content_paned.pack(side="top", fill="both", expand=True)

# Left Pane: Scrollable Checklist Editor
checklist_pane = tk.Frame(content_paned, bg=BG_APP)
content_paned.add(checklist_pane, minsize=480, stretch="always")

canvas_container = tk.Frame(checklist_pane, bg=BG_APP)
canvas_container.pack(fill="both", expand=True, padx=(12, 4), pady=(0, 6))

canvas = tk.Canvas(canvas_container, borderwidth=0, highlightthickness=0, yscrollincrement=1, bg=BG_APP)

def _on_scrollbar_scroll(*args):
    close_combobox_popdowns()
    canvas.yview(*args)

scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=_on_scrollbar_scroll, style="Dark.Vertical.TScrollbar")
scrollable_frame = tk.Frame(canvas, bg=BG_APP)

def _on_frame_configure(e):
    canvas.configure(scrollregion=canvas.bbox("all"))

scrollable_frame.bind("<Configure>", _on_frame_configure)

canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

def on_canvas_configure(event):
    canvas.itemconfig(canvas_window, width=event.width)

canvas.bind("<Configure>", on_canvas_configure)
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y", pady=4)

# Right Pane: Embedded Live PDF Preview
preview_pane = PDFPreviewPane(
    content_paned,
    recompile_callback=lambda: recompile_for_preview()
)
content_paned.add(preview_pane, minsize=420, stretch="always")

def _init_paned_split():
    root.update_idletasks()
    total_w = content_paned.winfo_width()
    if total_w > 800:
        content_paned.sash_place(0, int(total_w * 0.52), 0)

root.after(120, _init_paned_split)

def get_scroll_target():
    """Route scrolling to whichever pane is currently under the mouse cursor."""
    if preview_pane and preview_pane.winfo_ismapped():
        try:
            px, py = root.winfo_pointerxy()
            rx = preview_pane.winfo_rootx()
            ry = preview_pane.winfo_rooty()
            rw = preview_pane.winfo_width()
            rh = preview_pane.winfo_height()
            if rx <= px <= rx + rw and ry <= py <= ry + rh:
                return preview_pane.canvas
        except Exception:
            pass
    return canvas

def safe_focus_get():
    try:
        return root.focus_get()
    except Exception:
        return None

style_widgets = {}

def close_combobox_popdowns():
    """Closes any open combobox popdown dropdowns (Font Family, Font Size) when scrolling."""
    try:
        current_grab = root.tk.eval("grab current")
        if current_grab and ".popdown" in current_grab:
            cb_path = current_grab.rsplit(".popdown", 1)[0]
            root.tk.eval(f"ttk::combobox::Unpost {cb_path}")
    except Exception:
        pass
    for key in ("font_combo", "size_combo"):
        try:
            w = style_widgets.get(key)
            if w and w.winfo_exists():
                w.state(["!pressed"])
                popdown = f"{w}.popdown"
                if bool(int(w.tk.eval(f"winfo exists {popdown}"))) and bool(int(w.tk.eval(f"winfo ismapped {popdown}"))):
                    w.tk.eval(f"ttk::combobox::Unpost {w}")
        except Exception:
            pass

def _on_popdown_unmap(event=None):
    for key in ("font_combo", "size_combo"):
        w = style_widgets.get(key)
        if w and w.winfo_exists():
            try:
                w.state(["!pressed"])
            except Exception:
                pass

root.bind_class("ComboboxPopdown", "<Unmap>", _on_popdown_unmap, add="+")

# 1. macOS Trackpad Two-Finger Scrolling (<TouchpadScroll>) in Tk 9 Aqua
def _on_touchpad(event):
    close_combobox_popdowns()
    delta = event.delta
    # In Tk 9 Aqua, dxdy is packed into delta: deltaX = dxdy >> 16, deltaY = low 16 bits signed
    low = delta & 0xFFFF
    dy = low if low < 0x8000 else low - 0x10000
    high = (delta >> 16) & 0xFFFF
    dx = high if high < 0x8000 else high - 0x10000

    px, py = root.winfo_pointerxy()

    # Route to preview pane if cursor is over it
    if preview_pane and preview_pane.winfo_ismapped():
        try:
            rx = preview_pane.winfo_rootx()
            ry = preview_pane.winfo_rooty()
            rw = preview_pane.winfo_width()
            rh = preview_pane.winfo_height()
            if rx <= px <= rx + rw and ry <= py <= ry + rh:
                if dy != 0 and hasattr(preview_pane.canvas, "yview_scroll"):
                    preview_pane.canvas.yview_scroll(-dy, "units")
                if dx != 0 and hasattr(preview_pane.canvas, "xview_scroll"):
                    preview_pane.canvas.xview_scroll(-dx, "units")
                return "break"
        except Exception:
            pass

    if dy != 0 and hasattr(canvas, "yview_scroll"):
        canvas.yview_scroll(-dy, "units")
    return "break"

# 2. Traditional Mouse Wheel Scrolling (<MouseWheel>)
def _on_mousewheel(event):
    close_combobox_popdowns()
    if sys.platform == "darwin":
        delta = event.delta
        if abs(delta) >= 120:
            units = -int((delta / 120) * 35)
        else:
            units = -int(delta * 4)
        if units == 0 and delta != 0:
            units = -4 if delta > 0 else 4
    elif event.num == 5 or event.delta < 0:
        units = 25
    elif event.num == 4 or event.delta > 0:
        units = -25
    else:
        units = 0

    px, py = root.winfo_pointerxy()

    # Route to preview pane if cursor is over it
    if preview_pane and preview_pane.winfo_ismapped():
        try:
            rx = preview_pane.winfo_rootx()
            ry = preview_pane.winfo_rooty()
            rw = preview_pane.winfo_width()
            rh = preview_pane.winfo_height()
            if rx <= px <= rx + rw and ry <= py <= ry + rh:
                if units != 0 and hasattr(preview_pane.canvas, "yview_scroll"):
                    preview_pane.canvas.yview_scroll(units, "units")
                return "break"
        except Exception:
            pass

    if units != 0 and hasattr(canvas, "yview_scroll"):
        canvas.yview_scroll(units, "units")
    return "break"

# Bind across ALL widget classes so trackpad and mousewheel gestures route smoothly
for widget_class in ("Text", "Entry", "Label", "Button", "Checkbutton", "Frame", "LabelFrame", "Canvas", "TCombobox", "ComboboxPopdown", "ComboboxListbox", "Listbox"):
    try:
        root.bind_class(widget_class, "<TouchpadScroll>", _on_touchpad)
    except tk.TclError:
        pass
    root.bind_class(widget_class, "<MouseWheel>", _on_mousewheel)
    root.bind_class(widget_class, "<Button-4>", _on_mousewheel)
    root.bind_class(widget_class, "<Button-5>", _on_mousewheel)

try:
    root.bind_all("<TouchpadScroll>", _on_touchpad)
except tk.TclError:
    pass
root.bind_all("<MouseWheel>", _on_mousewheel)
root.bind_all("<Button-4>", _on_mousewheel)
root.bind_all("<Button-5>", _on_mousewheel)


class TextBoxAutoScroller:
    """Manages smooth continuous auto-scrolling when clicking and dragging to highlight past textbox boundaries."""
    def __init__(self, root_window):
        self.root = root_window
        self.active_widget = None
        self.timer = None
        self.cur_x = 0
        self.cur_y = 0
        self.anchor = None

        self.root.bind_class("Entry", "<ButtonPress-1>", self._on_entry_press, add="+")
        self.root.bind_class("Entry", "<B1-Motion>", self._on_entry_motion, add="+")
        self.root.bind_class("Entry", "<ButtonRelease-1>", self._on_release, add="+")

        self.root.bind_class("Text", "<ButtonPress-1>", self._on_text_press, add="+")
        self.root.bind_class("Text", "<B1-Motion>", self._on_text_motion, add="+")
        self.root.bind_class("Text", "<ButtonRelease-1>", self._on_release, add="+")

        self.root.bind_all("<ButtonRelease-1>", self._on_release, add="+")

    def _on_entry_press(self, event):
        self._cancel_timer()
        w = event.widget
        self.active_widget = w
        self.cur_x = event.x
        self.cur_y = event.y
        try:
            self.anchor = w.index("anchor")
        except Exception:
            try:
                self.anchor = w.index(f"@{event.x}")
            except Exception:
                self.anchor = 0

    def _on_entry_motion(self, event):
        w = event.widget
        self.active_widget = w
        self.cur_x = event.x
        self.cur_y = event.y
        width = w.winfo_width()
        if event.x > width or event.x < 0:
            if not self.timer:
                self._entry_tick()
        else:
            self._cancel_timer()

    def _entry_tick(self):
        self.timer = None
        w = self.active_widget
        if not w or not w.winfo_exists():
            return

        width = w.winfo_width()
        x = self.cur_x
        if x > width:
            dist = x - width
            step = max(1, min(8, dist // 15 + 1))
            w.xview_scroll(step, "units")
            cur = w.index(f"@{width}")
            w.icursor(cur)
            anchor = self.anchor if self.anchor is not None else w.index("anchor")
            w.selection_range(min(anchor, cur), max(anchor, cur))
            self.timer = self.root.after(35, self._entry_tick)
        elif x < 0:
            dist = -x
            step = max(1, min(8, dist // 15 + 1))
            w.xview_scroll(-step, "units")
            cur = w.index("@0")
            w.icursor(cur)
            anchor = self.anchor if self.anchor is not None else w.index("anchor")
            w.selection_range(min(anchor, cur), max(anchor, cur))
            self.timer = self.root.after(35, self._entry_tick)

    def _on_text_press(self, event):
        self._cancel_timer()
        w = event.widget
        self.active_widget = w
        self.cur_x = event.x
        self.cur_y = event.y
        try:
            idx = w.index(f"@{event.x},{event.y}")
            w.mark_set("custom_sel_anchor", idx)
            self.anchor = idx
        except Exception:
            self.anchor = "1.0"

    def _on_text_motion(self, event):
        w = event.widget
        self.active_widget = w
        self.cur_x = event.x
        self.cur_y = event.y
        width = w.winfo_width()
        height = w.winfo_height()
        if event.y > height or event.y < 0 or event.x > width or event.x < 0:
            if not self.timer:
                self._text_tick()
        else:
            self._cancel_timer()

    def _text_tick(self):
        self.timer = None
        w = self.active_widget
        if not w or not w.winfo_exists():
            return

        width = w.winfo_width()
        height = w.winfo_height()
        x = self.cur_x
        y = self.cur_y

        if y > height:
            dist = y - height
            step = max(1, min(4, dist // 25 + 1))
            w.yview_scroll(step, "units")
        elif y < 0:
            dist = -y
            step = max(1, min(4, dist // 25 + 1))
            w.yview_scroll(-step, "units")

        if x > width:
            w.xview_scroll(2, "units")
        elif x < 0:
            w.xview_scroll(-2, "units")

        clamp_x = max(0, min(x, width))
        clamp_y = max(0, min(y, height))
        try:
            cur = w.index(f"@{clamp_x},{clamp_y}")
            w.mark_set("insert", cur)
            anchor = w.index("custom_sel_anchor") if "custom_sel_anchor" in w.mark_names() else (self.anchor or "1.0")
            w.tag_remove("sel", "1.0", "end")
            if w.compare(anchor, "<", cur):
                w.tag_add("sel", anchor, cur)
            else:
                w.tag_add("sel", cur, anchor)
        except Exception:
            pass

        if y > height or y < 0 or x > width or x < 0:
            self.timer = self.root.after(35, self._text_tick)

    def _on_release(self, event=None):
        self._cancel_timer()
        self.active_widget = None

    def _cancel_timer(self):
        if self.timer:
            try:
                self.root.after_cancel(self.timer)
            except Exception:
                pass
            self.timer = None

textbox_autoscroller = TextBoxAutoScroller(root)

# Keyboard navigation (PageUp, PageDown, Home, End, Up, Down)
def _on_key_scroll(event):
    try:
        widget = safe_focus_get()
        in_text = widget and getattr(widget, "winfo_class", lambda: "")() in ("Text", "Entry")

        if event.keysym in ("Next", "Prior") or (event.keysym in ("Home", "End", "Down", "Up") and not in_text):
            close_combobox_popdowns()

        if event.keysym == "Next":
            canvas.yview_scroll(250, "units")
            return "break"
        elif event.keysym == "Prior":
            canvas.yview_scroll(-250, "units")
            return "break"
        elif event.keysym == "Home" and not in_text:
            canvas.yview_moveto(0)
            return "break"
        elif event.keysym == "End" and not in_text:
            canvas.yview_moveto(1)
            return "break"
        elif event.keysym == "Down" and not in_text:
            canvas.yview_scroll(40, "units")
            return "break"
        elif event.keysym == "Up" and not in_text:
            canvas.yview_scroll(-40, "units")
            return "break"
    except Exception:
        pass

root.bind_all("<Key>", _on_key_scroll)

# State tracking for all UI widgets
sections_widgets = []

_scroll_update_pending = False

def update_scroll():
    if not globals().get("_is_ui_initialized", False):
        return
    global _scroll_update_pending
    if not _scroll_update_pending:
        _scroll_update_pending = True
        root.after_idle(_do_update_scroll)

def _do_update_scroll():
    global _scroll_update_pending
    _scroll_update_pending = False
    canvas.configure(scrollregion=canvas.bbox("all"))

# Extract data tree from UI
def extract_sections_from_ui():
    sections_list = []
    for s in sections_widgets:
        sec_title = s["title_entry"].get().strip()
        sec_enabled = s["var"].get()

        entries_list = []
        for it in s["entries"]:
            it_enabled = it["var"].get()
            it_type = it.get("type", "dual-line")

            bullets_list = []
            for b in it["bullets"]:
                b_text = b["text_widget"].get("1.0", "end-1c").strip()
                b_enabled = b["var"].get()
                if b_text:
                    bullets_list.append({"enabled": b_enabled, "text": b_text})

            if it_type == "single-line":
                title_val = it["e_title"].get().strip()
                subtitle_val = it["e_subtitle"].get().strip()
                date_val = it["e_date"].get().strip()
                if title_val or subtitle_val or date_val or bullets_list:
                    entries_list.append({
                        "type": "single-line",
                        "enabled": it_enabled,
                        "title": title_val,
                        "subtitle": subtitle_val,
                        "date": date_val,
                        "bullets": bullets_list
                    })
            else:
                f1 = it["e1"].get().strip()
                f2 = it["e2"].get().strip()
                f3 = it["e3"].get().strip()
                f4 = it["e4"].get().strip()
                if f1 or f2 or f3 or f4 or bullets_list:
                    entries_list.append({
                        "type": "dual-line",
                        "enabled": it_enabled,
                        "field1": f1,
                        "field2": f2,
                        "field3": f3,
                        "field4": f4,
                        "bullets": bullets_list
                    })

        simple_lines_list = []
        for l in s["simple_lines"]:
            lbl = l["label_entry"].get().strip()
            if "flow" in l:
                items = l["flow"].get_items()
                txt = l["flow"].get_enabled_text()
            else:
                txt = l.get("text_entry", tk.Entry(root)).get().strip()
                items = [p.strip() for p in txt.split(",") if p.strip()]
            l_enabled = l["var"].get()
            if lbl or txt or items:
                simple_lines_list.append({
                    "enabled": l_enabled,
                    "label": lbl,
                    "items": items,
                    "text": txt
                })

        sections_list.append({
            "title": sec_title,
            "enabled": sec_enabled,
            "entries": entries_list,
            "simple_lines": simple_lines_list
        })
    return sections_list

# Autosave to master.yaml
def save_master_yaml(show_popup=False, recompile_preview=True):
    global _debounce_save_timer
    if _debounce_save_timer is not None:
        try:
            root.after_cancel(_debounce_save_timer)
        except Exception:
            pass
        _debounce_save_timer = None

    master_data["sections"] = extract_sections_from_ui()
    if header_widgets:
        master_data["name"] = header_widgets["name_entry"].get().strip()
        master_data["links"] = extract_links_from_ui()

    if style_widgets:
        if "font_combo" in style_widgets:
            master_data["font_family"] = style_widgets["font_combo"].get()
        if "size_combo" in style_widgets:
            master_data["font_size"] = style_widgets["size_combo"].get()
    elif header_widgets:
        if "font_combo" in header_widgets:
            master_data["font_family"] = header_widgets["font_combo"].get()
        if "size_combo" in header_widgets:
            master_data["font_size"] = header_widgets["size_combo"].get()

    try:
        with open("master.yaml", "w", encoding="utf-8") as f:
            yaml.dump(master_data, f, sort_keys=False, allow_unicode=True)
        if recompile_preview:
            try:
                recompile_preview_async()
            except Exception:
                pass
        return True
    except Exception as e:
        print(f"Failed to autosave master.yaml: {e}")
        return False

_is_ui_initialized = False
_debounce_save_timer = None
_save_indicator_timer = None

# Non-character navigation and modifier keys that shouldn't trigger an autosave timer
_IGNORED_KEYSYMS = {
    "Shift_L", "Shift_R", "Control_L", "Control_R",
    "Alt_L", "Alt_R", "Meta_L", "Meta_R", "Super_L", "Super_R",
    "Caps_Lock", "Num_Lock", "Scroll_Lock",
    "Up", "Down", "Left", "Right", "Home", "End", "Prior", "Next"
}

def schedule_debounced_save(event=None):
    """Debounce saves: reset timer on keystrokes and only write to disk after 500ms of inactivity."""
    global _debounce_save_timer, _save_indicator_timer
    if not _is_ui_initialized:
        return
    if event and event.keysym in _IGNORED_KEYSYMS:
        return

    if autosave_lbl:
        autosave_lbl.configure(text="Saving...", fg=FG_MUTED)

    if _debounce_save_timer is not None:
        try:
            root.after_cancel(_debounce_save_timer)
        except Exception:
            pass

    _debounce_save_timer = root.after(500, _perform_debounced_save)

def _perform_debounced_save():
    global _debounce_save_timer, _save_indicator_timer
    _debounce_save_timer = None
    success = save_master_yaml(show_popup=False)
    if autosave_lbl and success:
        autosave_lbl.configure(text="All changes saved", fg=FG_DIM)
        if _save_indicator_timer is not None:
            try:
                root.after_cancel(_save_indicator_timer)
            except Exception:
                pass
        _save_indicator_timer = root.after(2500, lambda: autosave_lbl.configure(text="") if autosave_lbl.cget("text") == "All changes saved" else None)

# Autosave when any field loses focus (clicked away / deselected)
def on_field_focus_out(event):
    if not _is_ui_initialized:
        return
    try:
        if event.widget.winfo_toplevel() == root:
            save_master_yaml(show_popup=False)
            if autosave_lbl:
                autosave_lbl.configure(text="All changes saved", fg=FG_DIM)
    except Exception:
        pass

# Ensure clicking anywhere outside an active text/entry field unfocuses it
def on_global_click(event):
    if not _is_ui_initialized:
        return
    try:
        widget = event.widget
        if isinstance(widget, str) or "popdown" in str(widget):
            return
        focused = safe_focus_get()
        if focused and getattr(focused, "winfo_class", lambda: "")() in ("Entry", "Text"):
            w_class = getattr(widget, "winfo_class", lambda: "")()
            if widget != focused and w_class not in ("Entry", "Text"):
                root.focus_set()
    except Exception:
        pass

# Enter key unfocuses entry and triggers save
def on_entry_return(event):
    if not _is_ui_initialized:
        return
    try:
        if event.widget.winfo_toplevel() == root:
            root.focus_set()
    except Exception:
        pass

def on_app_close():
    """Ensure any pending debounced edits are flushed before window closes."""
    try:
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)
    finally:
        root.destroy()

root.protocol("WM_DELETE_WINDOW", on_app_close)

def _on_any_key(event):
    if not _is_ui_initialized:
        return
    w = event.widget
    try:
        if w and (isinstance(w, (tk.Entry, tk.Text)) or getattr(w, "winfo_class", lambda: "")() in ("Entry", "Text")):
            if hasattr(w, "_update_height"):
                try:
                    w.after_idle(w._update_height)
                except Exception:
                    pass
            schedule_debounced_save(event)
    except Exception:
        pass

root.bind_all("<KeyRelease>", _on_any_key, add="+")
root.bind_all("<KeyPress>", _on_any_key, add="+")
root.bind_class("Entry", "<FocusOut>", on_field_focus_out, add="+")
root.bind_class("Text", "<FocusOut>", on_field_focus_out, add="+")
root.bind_class("Entry", "<Return>", on_entry_return, add="+")
root.bind_all("<Button-1>", on_global_click, add="+")

# Reordering helper functions
def move_bullet_up(item_data, bullet_data):
    bullets = item_data["bullets"]
    idx = bullets.index(bullet_data)
    if idx > 0:
        prev_bullet = bullets[idx - 1]
        bullets[idx - 1], bullets[idx] = bullets[idx], bullets[idx - 1]
        bullet_data["frame"].pack(before=prev_bullet["frame"])
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)
        update_scroll()

def move_bullet_down(item_data, bullet_data):
    bullets = item_data["bullets"]
    idx = bullets.index(bullet_data)
    if idx < len(bullets) - 1:
        next_bullet = bullets[idx + 1]
        bullets[idx], bullets[idx + 1] = bullets[idx + 1], bullets[idx]
        bullet_data["frame"].pack(after=next_bullet["frame"])
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)
        update_scroll()

def move_item_up(sec_data, item_data):
    entries = sec_data["entries"]
    idx = entries.index(item_data)
    if idx > 0:
        prev_item = entries[idx - 1]
        entries[idx - 1], entries[idx] = entries[idx], entries[idx - 1]
        item_data["frame"].pack(before=prev_item["frame"])
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)
        update_scroll()

def move_item_down(sec_data, item_data):
    entries = sec_data["entries"]
    idx = entries.index(item_data)
    if idx < len(entries) - 1:
        next_item = entries[idx + 1]
        entries[idx], entries[idx + 1] = entries[idx + 1], entries[idx]
        item_data["frame"].pack(after=next_item["frame"])
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)
        update_scroll()

def move_line_up(sec_data, line_data):
    lines = sec_data["simple_lines"]
    idx = lines.index(line_data)
    if idx > 0:
        prev_line = lines[idx - 1]
        lines[idx - 1], lines[idx] = lines[idx], lines[idx - 1]
        line_data["frame"].pack(before=prev_line["frame"])
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)
        update_scroll()

def move_line_down(sec_data, line_data):
    lines = sec_data["simple_lines"]
    idx = lines.index(line_data)
    if idx < len(lines) - 1:
        next_line = lines[idx + 1]
        lines[idx], lines[idx + 1] = lines[idx + 1], lines[idx]
        line_data["frame"].pack(after=next_line["frame"])
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)
        update_scroll()

def move_section_up(sec_data):
    idx = sections_widgets.index(sec_data)
    if idx > 0:
        prev_data = sections_widgets[idx - 1]
        sections_widgets[idx - 1], sections_widgets[idx] = sections_widgets[idx], sections_widgets[idx - 1]
        sec_data["frame"].pack(before=prev_data["frame"])
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)
        update_scroll()

def move_section_down(sec_data):
    idx = sections_widgets.index(sec_data)
    if idx < len(sections_widgets) - 1:
        next_data = sections_widgets[idx + 1]
        sections_widgets[idx], sections_widgets[idx + 1] = sections_widgets[idx + 1], sections_widgets[idx]
        sec_data["frame"].pack(after=next_data["frame"])
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)
        update_scroll()

# Bullet management
def _autosave():
    if _is_ui_initialized:
        save_master_yaml(show_popup=False)

def _icon_controls(parent, bg, on_up, on_down, on_delete):
    """Compact ▲ ▼ ✕ ghost-button group."""
    box = tk.Frame(parent, bg=bg)
    for text, cmd, fg in (("▲", on_up, FG_MUTED), ("▼", on_down, FG_MUTED), ("✕", on_delete, DANGER)):
        PillButton(box, text, cmd, parent_bg=bg, fg=fg, font=F_ICON,
                   padx=7, pady=3, radius=6).pack(side="left", padx=1)
    return box

def remove_bullet(item_data, bullet_data):
    bullet_data["frame"].destroy()
    item_data["bullets"].remove(bullet_data)
    if _is_ui_initialized:
        save_master_yaml(show_popup=False)
    update_scroll()

def add_bullet_widget(item_data, parent_container, enabled=True, text=""):
    row = tk.Frame(parent_container, bg=BG_ITEM)
    row.pack(fill="x", pady=3)

    var = tk.BooleanVar(value=enabled)
    Toggle(row, var, BG_ITEM, command=_autosave).pack(side="left", anchor="n", padx=(0, 10), pady=8)

    _icon_controls(
        row, BG_ITEM,
        lambda: move_bullet_up(item_data, bullet_data),
        lambda: move_bullet_down(item_data, bullet_data),
        lambda: remove_bullet(item_data, bullet_data),
    ).pack(side="right", anchor="n", padx=(8, 0), pady=5)

    txt_box = tk.Frame(row, bg=BG_ITEM)
    txt_box.pack(side="left", fill="x", expand=True)
    txt_box.pack_propagate(False)

    txt = make_text(txt_box, height=2)
    txt.insert("1.0", text)
    txt.pack(fill="both", expand=True)

    # Dynamic line height calculation: expand by an additional 30% of the next line if > 2 lines
    f = tkfont.Font(font=txt.cget("font"))
    line_h = f.metrics("linespace")
    pady = int(txt.cget("pady"))
    ht = int(txt.cget("highlightthickness"))
    h_2lines = 2 * line_h + 2 * pady + 2 * ht
    h_expanded = h_2lines + max(1, int(round(0.3 * line_h + 0.1)))

    txt_box.configure(height=h_2lines)

    def _update_bullet_height(event=None):
        try:
            if not txt.winfo_exists() or not txt_box.winfo_exists():
                return
            if txt.winfo_width() <= 10:
                return
            res = txt.count("1.0", "end-1c", "displaylines")
            display_lines = (res[0] + 1) if res else 1
            target_h = h_expanded if display_lines > 2 else h_2lines
            if txt_box.cget("height") != target_h:
                txt_box.configure(height=target_h)
                update_scroll()
        except Exception:
            pass

    txt._update_height = _update_bullet_height
    txt.bind("<KeyRelease>", _update_bullet_height, add="+")
    txt.bind("<KeyPress>", lambda e: txt.after_idle(_update_bullet_height), add="+")
    txt.bind("<Configure>", _update_bullet_height, add="+")
    txt.bind("<ButtonRelease-1>", _update_bullet_height, add="+")
    txt.bind("<<Paste>>", lambda e: txt.after_idle(_update_bullet_height), add="+")
    row.after_idle(_update_bullet_height)
    row.after(150, _update_bullet_height)

    bullet_data = {"var": var, "text_widget": txt, "frame": row, "box": txt_box}

    item_data["bullets"].append(bullet_data)
    update_scroll()

# Subheader item management (Field 1, Field 2, Field 3, Field 4 + Bullets)
def remove_item(sec_data, item_data):
    item_data["frame"].destroy()
    sec_data["entries"].remove(item_data)
    if _is_ui_initialized:
        save_master_yaml(show_popup=False)
    update_scroll()

def add_dual_line_item_widget(sec_data, parent_container, item_dict=None):
    if item_dict is None:
        item_dict = {"type": "dual-line", "enabled": True, "field1": "", "field2": "", "field3": "", "field4": "", "bullets": []}

    is_included = item_dict.get("enabled", True)

    card = RoundedCard(parent_container, bg=BG_ITEM, parent_bg=BG_SECTION,
                       border=BORDER_ITEM, radius=12, padx=14,
                       pady=12 if is_included else 8)
    card.pack(fill="x", pady=5)
    body = card.inner

    var = tk.BooleanVar(value=is_included)
    item_data = {"type": "dual-line", "var": var, "frame": card, "bullets": []}

    fields = tk.Frame(body, bg=BG_ITEM)
    fields.pack(fill="x")
    fields.columnconfigure(2, weight=1)
    fields.columnconfigure(4, weight=0 if is_included else 1)

    # Toggle & Title always on Row 0
    Toggle(fields, var, BG_ITEM, command=lambda: update_item_collapse_ui()).grid(row=0, column=0, padx=(0, 10), sticky="w")

    lbl_title = make_label(fields, "Title", BG_ITEM)
    lbl_title.grid(row=0, column=1, sticky="w", padx=(0, 8))
    e1 = make_entry(fields, font=F_BODY_B, fg=FG if is_included else FG_DIM)
    e1.insert(0, item_dict.get("field1") if "field1" in item_dict else item_dict.get("title", ""))
    e1.grid(row=0, column=2, sticky="ew", pady=3)

    # Dates widgets
    lbl_dates = make_label(fields, "Dates", BG_ITEM)
    e2 = make_entry(fields, width=20, fg=FG)
    e2.insert(0, item_dict.get("field2") if "field2" in item_dict else item_dict.get("dates", item_dict.get("date", "")))

    # Subtitle widgets
    lbl_subtitle = make_label(fields, "Subtitle", BG_ITEM)
    e3 = make_entry(fields, font=F_BODY_I, fg=FG if is_included else FG_DIM)
    e3.insert(0, item_dict.get("field3") if "field3" in item_dict else item_dict.get("subtitle", ""))

    # Location widgets
    lbl_location = make_label(fields, "Location", BG_ITEM)
    e4 = make_entry(fields, width=20, fg=FG)
    e4.insert(0, item_dict.get("field4") if "field4" in item_dict else item_dict.get("location", ""))

    status_lbl = tk.Label(fields, text="" if is_included else "EXCLUDED", font=F_TAG, bg=BG_ITEM, fg=FG_DIM)
    status_lbl.grid(row=0, column=5, padx=8, sticky="w")

    _icon_controls(
        fields, BG_ITEM,
        lambda: move_item_up(sec_data, item_data),
        lambda: move_item_down(sec_data, item_data),
        lambda: remove_item(sec_data, item_data),
    ).grid(row=0, column=6, padx=(10, 0), sticky="e")

    item_data.update({"e1": e1, "e2": e2, "e3": e3, "e4": e4})

    # Bullets section container (bullets list + add button)
    bullets_section = tk.Frame(body, bg=BG_ITEM)

    bullets_container = tk.Frame(bullets_section, bg=BG_ITEM)
    bullets_container.pack(fill="x", padx=(28, 0), pady=(8, 0))

    for b in item_dict.get("bullets", []):
        b_en = b.get("enabled", True) if isinstance(b, dict) else True
        b_txt = b.get("text", "") if isinstance(b, dict) else str(b)
        add_bullet_widget(item_data, bullets_container, b_en, b_txt)

    PillButton(
        bullets_section, "+ Add Bullet",
        lambda: (add_bullet_widget(item_data, bullets_container, True, ""), _autosave()),
        parent_bg=BG_ITEM, fg=FG_MUTED, font=F_BTN, padx=10, pady=4,
    ).pack(anchor="w", padx=(22, 0), pady=(6, 0))

    if is_included:
        lbl_dates.grid(row=0, column=3, sticky="w", padx=(14, 8))
        e2.grid(row=0, column=4, sticky="ew", pady=3)
        lbl_subtitle.grid(row=1, column=1, sticky="w", padx=(0, 8))
        e3.grid(row=1, column=2, sticky="ew", pady=3)
        lbl_location.grid(row=1, column=3, sticky="w", padx=(14, 8))
        e4.grid(row=1, column=4, sticky="ew", pady=3)
        bullets_section.pack(fill="x")
    else:
        # In collapsed mode: replace Dates with Subtitle on row 0, hide location & bullets
        lbl_subtitle.grid(row=0, column=3, sticky="w", padx=(14, 8))
        e3.grid(row=0, column=4, sticky="ew", pady=3)

    def update_item_collapse_ui():
        if var.get():
            fields.columnconfigure(4, weight=0)
            lbl_dates.grid(row=0, column=3, sticky="w", padx=(14, 8))
            e2.grid(row=0, column=4, sticky="ew", pady=3)
            lbl_subtitle.grid(row=1, column=1, sticky="w", padx=(0, 8))
            e3.grid(row=1, column=2, sticky="ew", pady=3)
            lbl_location.grid(row=1, column=3, sticky="w", padx=(14, 8))
            e4.grid(row=1, column=4, sticky="ew", pady=3)
            bullets_section.pack(fill="x")
            card.set_padding(pady=12)
            status_lbl.configure(text="")
            e1.configure(fg=FG)
            e2.configure(fg=FG)
            e3.configure(fg=FG)
        else:
            fields.columnconfigure(4, weight=1)
            lbl_dates.grid_remove()
            e2.grid_remove()
            lbl_location.grid_remove()
            e4.grid_remove()
            lbl_subtitle.grid(row=0, column=3, sticky="w", padx=(14, 8))
            e3.grid(row=0, column=4, sticky="ew", pady=3)
            bullets_section.pack_forget()
            card.set_padding(pady=8)
            status_lbl.configure(text="EXCLUDED")
            e1.configure(fg=FG_DIM)
            e3.configure(fg=FG_DIM)
        _autosave()
        update_scroll()

    sec_data["entries"].append(item_data)
    update_scroll()
    return item_data


def add_single_line_item_widget(sec_data, parent_container, item_dict=None):
    if item_dict is None:
        item_dict = {"type": "single-line", "enabled": True, "title": "", "subtitle": "", "date": "", "bullets": []}

    is_included = item_dict.get("enabled", True)

    card = RoundedCard(parent_container, bg=BG_ITEM, parent_bg=BG_SECTION,
                       border=BORDER_ITEM, radius=12, padx=14,
                       pady=12 if is_included else 8)
    card.pack(fill="x", pady=5)
    body = card.inner

    var = tk.BooleanVar(value=is_included)
    item_data = {"type": "single-line", "var": var, "frame": card, "bullets": []}

    fields = tk.Frame(body, bg=BG_ITEM)
    fields.pack(fill="x")
    fields.columnconfigure(2, weight=2)
    fields.columnconfigure(4, weight=3)
    fields.columnconfigure(6, weight=0 if is_included else 1)

    # Toggle & Title always on Row 0
    Toggle(fields, var, BG_ITEM, command=lambda: update_single_collapse_ui()).grid(row=0, column=0, padx=(0, 10), sticky="w")

    lbl_title = make_label(fields, "Title", BG_ITEM)
    lbl_title.grid(row=0, column=1, sticky="w", padx=(0, 8))
    e_title = make_entry(fields, font=F_BODY_B, fg=FG if is_included else FG_DIM)
    e_title.insert(0, item_dict.get("title") if "title" in item_dict else item_dict.get("field1", ""))
    e_title.grid(row=0, column=2, sticky="ew", pady=3)

    # Subtitle widgets
    lbl_subtitle = make_label(fields, "Subtitle", BG_ITEM)
    lbl_subtitle.grid(row=0, column=3, sticky="w", padx=(14, 8))
    e_subtitle = make_entry(fields, font=F_BODY_I, fg=FG if is_included else FG_DIM)
    e_subtitle.insert(0, item_dict.get("subtitle") if "subtitle" in item_dict else item_dict.get("field3", ""))
    e_subtitle.grid(row=0, column=4, sticky="ew", pady=3)

    # Date widgets
    lbl_date = make_label(fields, "Date", BG_ITEM)
    e_date = make_entry(fields, width=20, fg=FG)
    e_date.insert(0, item_dict.get("date") if "date" in item_dict else item_dict.get("field2", ""))

    status_lbl = tk.Label(fields, text="" if is_included else "EXCLUDED", font=F_TAG, bg=BG_ITEM, fg=FG_DIM)
    status_lbl.grid(row=0, column=7, padx=8, sticky="w")

    _icon_controls(
        fields, BG_ITEM,
        lambda: move_item_up(sec_data, item_data),
        lambda: move_item_down(sec_data, item_data),
        lambda: remove_item(sec_data, item_data),
    ).grid(row=0, column=8, padx=(10, 0), sticky="e")

    item_data.update({
        "e_title": e_title,
        "e_subtitle": e_subtitle,
        "e_date": e_date,
        "e1": e_title,
        "e2": e_date,
        "e3": e_subtitle,
        "e4": None,
    })

    # Bullets section container (bullets list + add button)
    bullets_section = tk.Frame(body, bg=BG_ITEM)

    bullets_container = tk.Frame(bullets_section, bg=BG_ITEM)
    bullets_container.pack(fill="x", padx=(28, 0), pady=(8, 0))

    for b in item_dict.get("bullets", []):
        b_en = b.get("enabled", True) if isinstance(b, dict) else True
        b_txt = b.get("text", "") if isinstance(b, dict) else str(b)
        add_bullet_widget(item_data, bullets_container, b_en, b_txt)

    PillButton(
        bullets_section, "+ Add Bullet",
        lambda: (add_bullet_widget(item_data, bullets_container, True, ""), _autosave()),
        parent_bg=BG_ITEM, fg=FG_MUTED, font=F_BTN, padx=10, pady=4,
    ).pack(anchor="w", padx=(22, 0), pady=(6, 0))

    if is_included:
        lbl_date.grid(row=0, column=5, sticky="w", padx=(14, 8))
        e_date.grid(row=0, column=6, sticky="ew", pady=3)
        bullets_section.pack(fill="x")

    def update_single_collapse_ui():
        if var.get():
            fields.columnconfigure(6, weight=0)
            lbl_date.grid(row=0, column=5, sticky="w", padx=(14, 8))
            e_date.grid(row=0, column=6, sticky="ew", pady=3)
            bullets_section.pack(fill="x")
            card.set_padding(pady=12)
            status_lbl.configure(text="")
            e_title.configure(fg=FG)
            e_subtitle.configure(fg=FG)
            e_date.configure(fg=FG)
        else:
            fields.columnconfigure(6, weight=1)
            lbl_date.grid_remove()
            e_date.grid_remove()
            bullets_section.pack_forget()
            card.set_padding(pady=8)
            status_lbl.configure(text="EXCLUDED")
            e_title.configure(fg=FG_DIM)
            e_subtitle.configure(fg=FG_DIM)
        _autosave()
        update_scroll()

    sec_data["entries"].append(item_data)
    update_scroll()
    return item_data


def add_item_widget(sec_data, parent_container, item_dict=None, item_type=None):
    if item_dict is not None:
        t = str(item_dict.get("type") or item_type or "").lower()
        if t in ("single-line", "single", "single_line", "single-line subheader", "single-line subheaders"):
            return add_single_line_item_widget(sec_data, parent_container, item_dict)
        elif t in ("dual-line", "dual", "dual_line", "dual-line subheader", "dual-line subheaders"):
            return add_dual_line_item_widget(sec_data, parent_container, item_dict)
        elif ("title" in item_dict or "date" in item_dict) and "field4" not in item_dict and not item_dict.get("field4"):
            return add_single_line_item_widget(sec_data, parent_container, item_dict)
        else:
            return add_dual_line_item_widget(sec_data, parent_container, item_dict)
    else:
        if str(item_type or "").lower() in ("single-line", "single", "single_line"):
            return add_single_line_item_widget(sec_data, parent_container)
        else:
            return add_dual_line_item_widget(sec_data, parent_container)

# Simple line management (Title + Content, e.g. Technical Skills)
def remove_line(sec_data, line_data):
    line_data["frame"].destroy()
    sec_data["simple_lines"].remove(line_data)
    if _is_ui_initialized:
        save_master_yaml(show_popup=False)
    update_scroll()

# ---------------------------------------------------------------------------
# Single line list flow layout (comma-separated, individually reorderable fields)
# ---------------------------------------------------------------------------
class SingleLineFlow(tk.Frame):
    def __init__(self, parent, bg=BG_ITEM, on_change=None):
        super().__init__(parent, bg=bg, height=35)
        self.pack_propagate(False)
        self.on_change = on_change
        self.items_data = []
        self.add_btn = None
        self.bind("<Configure>", self.reflow)

    def set_items(self, items):
        for c in self.winfo_children():
            c.destroy()
        self.items_data = []

        if not items:
            items = [""]

        for text in items:
            if isinstance(text, dict):
                self._create_item_widget(text.get("text", ""), enabled=text.get("enabled", True))
            else:
                self._create_item_widget(str(text), enabled=True)

        self.add_btn = tk.Frame(self, bg=BG_INPUT, highlightthickness=1, highlightbackground=BORDER_INPUT, cursor="hand2")
        lbl_plus = tk.Label(self.add_btn, text="+ Item", font=F_TAG, fg=FG_MUTED, bg=BG_INPUT, cursor="hand2", padx=7, pady=3)
        lbl_plus.pack()

        def _hover_in(e):
            self.add_btn.configure(highlightbackground=FOCUS_RING)
            lbl_plus.configure(fg=FG)
        def _hover_out(e):
            self.add_btn.configure(highlightbackground=BORDER_INPUT)
            lbl_plus.configure(fg=FG_MUTED)

        self.add_btn.bind("<Enter>", _hover_in)
        self.add_btn.bind("<Leave>", _hover_out)
        lbl_plus.bind("<Enter>", _hover_in)
        lbl_plus.bind("<Leave>", _hover_out)

        def _on_add(e=None):
            self.add_item("")

        self.add_btn.bind("<Button-1>", _on_add)
        lbl_plus.bind("<Button-1>", _on_add)
        self._update_button_states()
        self.reflow()

    def _create_item_widget(self, text, enabled=True):
        chip = tk.Frame(self, bg=BG_INPUT, highlightthickness=1, highlightbackground=BORDER_INPUT)

        var = tk.BooleanVar(value=enabled)

        def _on_toggle():
            if not var.get():
                entry.configure(fg=FG_DIM)
                if self.items_data and self.items_data[-1] is not item_obj:
                    self.items_data.remove(item_obj)
                    self.items_data.append(item_obj)
                    self._update_button_states()
                    self.reflow()
            else:
                entry.configure(fg=FG)
                first_inactive_idx = next((idx for idx, it in enumerate(self.items_data) if not it["var"].get() and it is not item_obj), None)
                cur_idx = self.items_data.index(item_obj)
                if first_inactive_idx is not None and cur_idx > first_inactive_idx:
                    self.items_data.remove(item_obj)
                    self.items_data.insert(first_inactive_idx, item_obj)
                    self._update_button_states()
                    self.reflow()
            if self.on_change:
                self.on_change()

        toggle = Toggle(chip, var, parent_bg=BG_INPUT, size=14, command=_on_toggle)
        toggle.pack(side="left", padx=(5, 3))

        entry = tk.Entry(
            chip, font=F_BODY, bg=BG_INPUT, fg=FG if enabled else FG_DIM, insertbackground=FG,
            relief="flat", bd=0, highlightthickness=0, width=max(3, len(text) + 1)
        )
        entry.insert(0, text)
        entry.pack(side="left", padx=(0, 2), pady=3)

        btn_l = tk.Label(chip, text="◀", font=(UI_FONT, 7), fg=FG_MUTED, bg=BG_INPUT, cursor="hand2", padx=1)
        btn_l.pack(side="left", padx=1)

        btn_r = tk.Label(chip, text="▶", font=(UI_FONT, 7), fg=FG_MUTED, bg=BG_INPUT, cursor="hand2", padx=1)
        btn_r.pack(side="left", padx=(1, 2))

        btn_x = tk.Label(chip, text="✕", font=(UI_FONT, 8, "bold"), fg=FG_DIM, bg=BG_INPUT, cursor="hand2", padx=2)
        btn_x.pack(side="left", padx=(1, 5))

        comma = tk.Label(self, text=",", font=F_BODY_B, fg=FG_MUTED, bg=BG_ITEM)

        item_obj = {"chip": chip, "var": var, "toggle": toggle, "entry": entry, "comma": comma, "btn_l": btn_l, "btn_r": btn_r, "btn_x": btn_x}

        entry.bind("<FocusIn>", lambda e: chip.configure(highlightbackground=FOCUS_RING))
        entry.bind("<FocusOut>", lambda e: chip.configure(highlightbackground=BORDER_INPUT))

        def _move_left(e=None):
            i = self.items_data.index(item_obj)
            if i > 0:
                self.items_data[i - 1], self.items_data[i] = self.items_data[i], self.items_data[i - 1]
                self._update_button_states()
                self.reflow()
                entry.focus_set()
                if self.on_change:
                    self.on_change()
            return "break"

        def _move_right(e=None):
            i = self.items_data.index(item_obj)
            if i < len(self.items_data) - 1:
                self.items_data[i + 1], self.items_data[i] = self.items_data[i], self.items_data[i + 1]
                self._update_button_states()
                self.reflow()
                entry.focus_set()
                if self.on_change:
                    self.on_change()
            return "break"

        def _delete(e=None):
            chip.destroy()
            comma.destroy()
            if item_obj in self.items_data:
                self.items_data.remove(item_obj)
            self._update_button_states()
            self.reflow()
            if self.on_change:
                self.on_change()
            return "break"

        item_obj["move_left"] = _move_left
        item_obj["move_right"] = _move_right
        item_obj["delete"] = _delete

        btn_l.bind("<Button-1>", _move_left)
        btn_r.bind("<Button-1>", _move_right)
        btn_x.bind("<Button-1>", _delete)

        btn_l.bind("<Enter>", lambda e: btn_l.configure(fg=FG) if self.items_data.index(item_obj) > 0 else None)
        btn_l.bind("<Leave>", lambda e: btn_l.configure(fg=FG_MUTED if self.items_data.index(item_obj) > 0 else BORDER_INPUT))
        btn_r.bind("<Enter>", lambda e: btn_r.configure(fg=FG) if self.items_data.index(item_obj) < len(self.items_data) - 1 else None)
        btn_r.bind("<Leave>", lambda e: btn_r.configure(fg=FG_MUTED if self.items_data.index(item_obj) < len(self.items_data) - 1 else BORDER_INPUT))
        btn_x.bind("<Enter>", lambda e: btn_x.configure(fg=DANGER))
        btn_x.bind("<Leave>", lambda e: btn_x.configure(fg=FG_DIM))

        def _on_key_release(e):
            val = entry.get()
            entry.configure(width=max(3, len(val) + 1))
            self.reflow()
            if self.on_change:
                self.on_change()

        entry.bind("<KeyRelease>", _on_key_release)

        def _on_key_press(e):
            if e.keysym == "comma" or getattr(e, "char", "") == ",":
                val = entry.get()
                cur_pos = entry.index("insert")
                part1 = val[:cur_pos].strip()
                part2 = val[cur_pos:].strip()
                entry.delete(0, "end")
                entry.insert(0, part1)
                entry.configure(width=max(3, len(part1) + 1))
                i = self.items_data.index(item_obj)
                self.insert_item(i + 1, part2)
                return "break"
            elif e.keysym in ("Return", "KP_Enter"):
                i = self.items_data.index(item_obj)
                self.insert_item(i + 1, "")
                return "break"

        entry.bind("<KeyPress>", _on_key_press)

        def _on_backspace(e):
            if not entry.get() and len(self.items_data) > 1:
                i = self.items_data.index(item_obj)
                prev_i = max(0, i - 1)
                _delete()
                if prev_i < len(self.items_data):
                    self.items_data[prev_i]["entry"].focus_set()
                return "break"

        entry.bind("<BackSpace>", _on_backspace)
        entry.bind("<Alt-Left>", lambda e: _move_left() or "break")
        entry.bind("<Alt-Right>", lambda e: _move_right() or "break")

        def _on_paste(e):
            try:
                clip = self.clipboard_get()
                if "," in clip:
                    parts = [p.strip() for p in clip.split(",") if p.strip()]
                    if parts:
                        entry.delete(0, "end")
                        entry.insert(0, parts[0])
                        entry.configure(width=max(3, len(parts[0]) + 1))
                        i = self.items_data.index(item_obj)
                        for offset, p in enumerate(parts[1:], start=1):
                            self.insert_item(i + offset, p)
                        return "break"
            except Exception:
                pass

        entry.bind("<<Paste>>", _on_paste)
        entry.bind("<Command-v>", _on_paste)
        entry.bind("<Control-v>", _on_paste)

        self.items_data.append(item_obj)
        self._update_button_states()
        return item_obj

    def _update_button_states(self):
        n = len(self.items_data)
        for i, it in enumerate(self.items_data):
            can_left = (i > 0)
            can_right = (i < n - 1)
            it["btn_l"].configure(
                fg=FG_MUTED if can_left else BORDER_INPUT,
                cursor="hand2" if can_left else ""
            )
            it["btn_r"].configure(
                fg=FG_MUTED if can_right else BORDER_INPUT,
                cursor="hand2" if can_right else ""
            )

    def add_item(self, text="", enabled=True):
        obj = self._create_item_widget(text, enabled=enabled)
        self.reflow()
        obj["entry"].focus_set()
        if self.on_change:
            self.on_change()

    def insert_item(self, index, text="", enabled=True):
        obj = self._create_item_widget(text, enabled=enabled)
        self.items_data.remove(obj)
        self.items_data.insert(index, obj)
        self._update_button_states()
        self.reflow()
        obj["entry"].focus_set()
        if self.on_change:
            self.on_change()

    def get_items(self):
        return [
            {"enabled": it["var"].get(), "text": it["entry"].get().strip()}
            for it in self.items_data
            if it["entry"].get().strip()
        ]

    def get_enabled_text(self):
        return ", ".join(
            it["entry"].get().strip()
            for it in self.items_data
            if it["entry"].get().strip() and it["var"].get()
        )

    def reflow(self, event=None):
        self.update_idletasks()
        avail_w = self.winfo_width()
        if avail_w <= 10:
            return

        cur_x = 0
        cur_y = 0
        row_h = 32
        gap_x = 5
        gap_y = 6

        n = len(self.items_data)
        for i, it in enumerate(self.items_data):
            chip = it["chip"]
            comma = it["comma"]
            cw = chip.winfo_reqwidth()
            comma_w = comma.winfo_reqwidth() if i < n - 1 else 0
            item_tot_w = cw + (comma_w + 3 if i < n - 1 else 0)

            if cur_x + item_tot_w > avail_w and cur_x > 0:
                cur_x = 0
                cur_y += row_h + gap_y

            chip.place(x=cur_x, y=cur_y)
            if i < n - 1:
                comma.place(x=cur_x + cw + 1, y=cur_y + 4)
            else:
                comma.place_forget()
            cur_x += item_tot_w + gap_x

        if self.add_btn:
            btn_w = self.add_btn.winfo_reqwidth()
            if cur_x + btn_w > avail_w and cur_x > 0:
                cur_x = 0
                cur_y += row_h + gap_y
            self.add_btn.place(x=cur_x, y=cur_y + 2)

        total_h = cur_y + row_h + 4
        old_h = getattr(self, "_last_reflow_h", None)
        self._last_reflow_h = total_h
        self.configure(height=total_h)
        if hasattr(self.master, "master") and isinstance(self.master.master, RoundedCard):
            self.master.master._sync_height()
        elif hasattr(self.master, "_sync_height"):
            self.master._sync_height()
        if old_h is not None and old_h != total_h:
            update_scroll()

def add_line_widget(sec_data, parent_container, line_dict=None):
    if line_dict is None:
        line_dict = {"enabled": True, "label": "", "text": "", "items": [""]}

    is_included = line_dict.get("enabled", True)

    card = RoundedCard(parent_container, bg=BG_ITEM, parent_bg=BG_SECTION,
                       border=BORDER_ITEM, radius=12, padx=12,
                       pady=10 if is_included else 6)
    card.pack(fill="x", pady=4)
    inner = card.inner

    top_row = tk.Frame(inner, bg=BG_ITEM)
    top_row.pack(fill="x")

    var = tk.BooleanVar(value=is_included)
    Toggle(top_row, var, BG_ITEM, command=lambda: update_line_collapse_ui()).pack(side="left", padx=(0, 10))

    el = make_entry(top_row, width=18, font=F_BODY_B, fg=FG if is_included else FG_DIM)
    el.insert(0, line_dict.get("label", ""))
    el.pack(side="left", padx=(0, 8))

    status_lbl = tk.Label(top_row, text="" if is_included else "EXCLUDED", font=F_TAG, bg=BG_ITEM, fg=FG_DIM)
    status_lbl.pack(side="left", padx=4)

    flow = SingleLineFlow(inner, bg=BG_ITEM, on_change=_autosave)

    raw_items = line_dict.get("items")
    if not raw_items:
        raw_text = line_dict.get("text", "")
        raw_items = [s.strip() for s in raw_text.split(",") if s.strip()]
    if not raw_items:
        raw_items = [""]

    flow.set_items(raw_items)

    line_data = {"var": var, "label_entry": el, "flow": flow, "frame": card}

    _icon_controls(
        top_row, BG_ITEM,
        lambda: move_line_up(sec_data, line_data),
        lambda: move_line_down(sec_data, line_data),
        lambda: remove_line(sec_data, line_data),
    ).pack(side="right", padx=(8, 0))

    if is_included:
        flow.pack(fill="x", pady=(6, 0))

    def update_line_collapse_ui():
        if var.get():
            status_lbl.configure(text="")
            flow.pack(fill="x", pady=(6, 0))
            card.set_padding(pady=10)
            el.configure(fg=FG)
            flow.reflow()
        else:
            flow.pack_forget()
            status_lbl.configure(text="EXCLUDED")
            card.set_padding(pady=6)
            el.configure(fg=FG_DIM)
        _autosave()
        update_scroll()

    sec_data["simple_lines"].append(line_data)
    update_scroll()

# Section management
def remove_section(sec_data):
    if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete section '{sec_data['title_entry'].get()}'?"):
        sec_data["frame"].destroy()
        sections_widgets.remove(sec_data)
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)
        update_scroll()

def add_section_widget(sec_dict=None):
    if sec_dict is None:
        sec_dict = {"title": "New Section", "enabled": True, "entries": [], "simple_lines": []}

    is_included = sec_dict.get("enabled", True)

    card = RoundedCard(scrollable_frame, bg=BG_SECTION, parent_bg=BG_APP,
                       border=BORDER_SECTION, radius=16, padx=16,
                       pady=14 if is_included else 10)
    card.pack(fill="x", pady=7, padx=(14, 8))
    inner = card.inner

    # Top Bar of Section
    top = tk.Frame(inner, bg=BG_SECTION)
    top.pack(fill="x", pady=(0, 10 if is_included else 0))

    var = tk.BooleanVar(value=is_included)
    Toggle(top, var, BG_SECTION, command=lambda: update_collapse_ui()).pack(side="left", padx=(0, 8))

    # Title looks like a heading; a subtle ring appears on hover / focus
    title_entry = make_entry(top, font=F_SECTION, width=24, bg=BG_SECTION, ring=BG_SECTION,
                             fg=FG if is_included else FG_DIM)
    title_entry.insert(0, sec_dict.get("title", "New Section"))
    title_entry.pack(side="left")
    title_entry.bind("<Enter>", lambda e: title_entry.configure(highlightbackground=BORDER_INPUT))
    title_entry.bind("<Leave>", lambda e: title_entry.configure(highlightbackground=BG_SECTION))

    status_lbl = tk.Label(top, text="" if is_included else "EXCLUDED", font=F_TAG, bg=BG_SECTION, fg=FG_DIM)
    status_lbl.pack(side="left", padx=8)

    sec_data = {
        "var": var,
        "title_entry": title_entry,
        "frame": card,
        "entries": [],
        "simple_lines": []
    }

    sec_controls = tk.Frame(top, bg=BG_SECTION)
    sec_controls.pack(side="right")
    PillButton(sec_controls, "▲", lambda: move_section_up(sec_data), parent_bg=BG_SECTION,
               fg=FG_MUTED, font=F_ICON, padx=8, pady=4).pack(side="left", padx=1)
    PillButton(sec_controls, "▼", lambda: move_section_down(sec_data), parent_bg=BG_SECTION,
               fg=FG_MUTED, font=F_ICON, padx=8, pady=4).pack(side="left", padx=1)
    PillButton(sec_controls, "Delete", lambda: remove_section(sec_data), parent_bg=BG_SECTION,
               fg=DANGER, font=F_BTN, padx=10, pady=4).pack(side="left", padx=(4, 0))

    # Content body container (collapsible)
    body_frame = tk.Frame(inner, bg=BG_SECTION)
    if is_included:
        body_frame.pack(fill="x")

    # Subheaders container
    entries_container = tk.Frame(body_frame, bg=BG_SECTION)
    entries_container.pack(fill="x")

    # Simple lines container
    lines_container = tk.Frame(body_frame, bg=BG_SECTION)
    lines_container.pack(fill="x")

    for item in sec_dict.get("entries", []):
        add_item_widget(sec_data, entries_container, item)

    for line in sec_dict.get("simple_lines", []):
        add_line_widget(sec_data, lines_container, line)

    # Action bar for this section
    sec_actions = tk.Frame(body_frame, bg=BG_SECTION)
    sec_actions.pack(fill="x", pady=(8, 0))

    def _add_dual():
        add_dual_line_item_widget(sec_data, entries_container)
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)
        update_scroll()

    def _add_single():
        add_single_line_item_widget(sec_data, entries_container)
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)
        update_scroll()

    def _add_line():
        add_line_widget(sec_data, lines_container)
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)
        update_scroll()

    PillButton(
        sec_actions, "+ Dual-line Subheader",
        _add_dual,
        parent_bg=BG_SECTION, bg=BG_ITEM, fg=FG_MUTED, border=BORDER_ITEM, padx=12, pady=5,
    ).pack(side="left", padx=(0, 8))

    PillButton(
        sec_actions, "+ Single-line Subheader",
        _add_single,
        parent_bg=BG_SECTION, bg=BG_ITEM, fg=FG_MUTED, border=BORDER_ITEM, padx=12, pady=5,
    ).pack(side="left", padx=(0, 8))

    PillButton(
        sec_actions, "+ Single Line",
        _add_line,
        parent_bg=BG_SECTION, bg=BG_ITEM, fg=FG_MUTED, border=BORDER_ITEM, padx=12, pady=5,
    ).pack(side="left")

    def update_collapse_ui():
        if var.get():
            body_frame.pack(fill="x")
            card.set_padding(pady=14)
            top.pack_configure(pady=(0, 10))
            status_lbl.configure(text="")
            title_entry.configure(fg=FG)
        else:
            body_frame.pack_forget()
            card.set_padding(pady=10)
            top.pack_configure(pady=0)
            status_lbl.configure(text="EXCLUDED")
            title_entry.configure(fg=FG_DIM)
        _autosave()
        update_scroll()

    sections_widgets.append(sec_data)
    update_scroll()

# ---------------------------------------------------------------------------
# Header (name + contact links)
# ---------------------------------------------------------------------------
header_widgets = {}

def extract_links_from_ui():
    links = []
    for l in header_widgets.get("links", []):
        label = l["label_entry"].get().strip()
        item_type = l.get("type", "link")
        if item_type == "phone":
            if label:
                links.append({"enabled": l["var"].get(), "label": label, "type": "phone"})
        elif item_type == "email":
            if label:
                clean_email = label[7:] if label.lower().startswith("mailto:") else label
                clean_email = clean_email.strip()
                links.append({
                    "enabled": l["var"].get(),
                    "label": clean_email,
                    "url": f"mailto:{clean_email}",
                    "type": "email"
                })
        else:
            url = l["url_entry"].get().strip() if "url_entry" in l else ""
            if label or url:
                links.append({"enabled": l["var"].get(), "label": label, "url": url, "type": "link"})
    return links

def move_link(link_data, step):
    links = header_widgets["links"]
    idx = links.index(link_data)
    new_idx = idx + step
    if 0 <= new_idx < len(links):
        other = links[new_idx]
        links[idx], links[new_idx] = links[new_idx], links[idx]
        if step < 0:
            link_data["frame"].pack(before=other["frame"])
        else:
            link_data["frame"].pack(after=other["frame"])
        _autosave()
        update_scroll()

def remove_link(link_data):
    link_data["frame"].destroy()
    header_widgets["links"].remove(link_data)
    _autosave()
    update_scroll()

def add_phone_widget(parent_container, phone_dict=None):
    if phone_dict is None:
        phone_dict = {"enabled": True, "label": "", "type": "phone"}

    is_included = phone_dict.get("enabled", True)

    card = RoundedCard(parent_container, bg=BG_ITEM, parent_bg=BG_SECTION,
                       border=BORDER_ITEM, radius=12, padx=12,
                       pady=9 if is_included else 6)
    card.pack(fill="x", pady=4)
    row = card.inner

    var = tk.BooleanVar(value=is_included)
    Toggle(row, var, BG_ITEM, command=lambda: update_phone_collapse_ui()).pack(side="left", padx=(0, 10))

    make_label(row, "Phone", BG_ITEM).pack(side="left", padx=(0, 8))

    status_lbl = tk.Label(row, text="" if is_included else "EXCLUDED", font=F_TAG, bg=BG_ITEM, fg=FG_DIM)
    status_lbl.pack(side="left", padx=4)

    link_data = {"var": var, "frame": card, "type": "phone"}

    _icon_controls(
        row, BG_ITEM,
        lambda: move_link(link_data, -1),
        lambda: move_link(link_data, 1),
        lambda: remove_link(link_data),
    ).pack(side="right", padx=(8, 0))

    el = make_entry(row, font=F_BODY_B, fg=FG if is_included else FG_DIM)
    el.insert(0, phone_dict.get("label", ""))
    el.pack(side="left", fill="x", expand=True)
    link_data["label_entry"] = el

    def update_phone_collapse_ui():
        if var.get():
            status_lbl.configure(text="")
            card.set_padding(pady=9)
            el.configure(fg=FG)
        else:
            status_lbl.configure(text="EXCLUDED")
            card.set_padding(pady=6)
            el.configure(fg=FG_DIM)
        _autosave()
        update_scroll()

    header_widgets["links"].append(link_data)
    update_scroll()

def add_email_widget(parent_container, email_dict=None):
    if email_dict is None:
        email_dict = {"enabled": True, "label": "", "type": "email"}

    is_included = email_dict.get("enabled", True)

    card = RoundedCard(parent_container, bg=BG_ITEM, parent_bg=BG_SECTION,
                       border=BORDER_ITEM, radius=12, padx=12,
                       pady=9 if is_included else 6)
    card.pack(fill="x", pady=4)
    row = card.inner

    var = tk.BooleanVar(value=is_included)
    Toggle(row, var, BG_ITEM, command=lambda: update_email_collapse_ui()).pack(side="left", padx=(0, 10))

    make_label(row, "Email", BG_ITEM).pack(side="left", padx=(0, 8))

    status_lbl = tk.Label(row, text="" if is_included else "EXCLUDED", font=F_TAG, bg=BG_ITEM, fg=FG_DIM)
    status_lbl.pack(side="left", padx=4)

    link_data = {"var": var, "frame": card, "type": "email"}

    _icon_controls(
        row, BG_ITEM,
        lambda: move_link(link_data, -1),
        lambda: move_link(link_data, 1),
        lambda: remove_link(link_data),
    ).pack(side="right", padx=(8, 0))

    raw_val = email_dict.get("label", "")
    if not raw_val and email_dict.get("url", "").startswith("mailto:"):
        raw_val = email_dict.get("url", "")[7:]
    elif raw_val.lower().startswith("mailto:"):
        raw_val = raw_val[7:]

    el = make_entry(row, font=F_BODY_B, fg=FG if is_included else FG_DIM)
    el.insert(0, raw_val)
    el.pack(side="left", fill="x", expand=True)
    link_data["label_entry"] = el

    def update_email_collapse_ui():
        if var.get():
            status_lbl.configure(text="")
            card.set_padding(pady=9)
            el.configure(fg=FG)
        else:
            status_lbl.configure(text="EXCLUDED")
            card.set_padding(pady=6)
            el.configure(fg=FG_DIM)
        _autosave()
        update_scroll()

    header_widgets["links"].append(link_data)
    update_scroll()

def add_link_widget(parent_container, link_dict=None):
    if link_dict is None:
        link_dict = {"enabled": True, "label": "", "url": "", "type": "link"}

    is_included = link_dict.get("enabled", True)

    card = RoundedCard(parent_container, bg=BG_ITEM, parent_bg=BG_SECTION,
                       border=BORDER_ITEM, radius=12, padx=12,
                       pady=9 if is_included else 6)
    card.pack(fill="x", pady=4)
    row = card.inner

    var = tk.BooleanVar(value=is_included)
    Toggle(row, var, BG_ITEM, command=lambda: update_link_collapse_ui()).pack(side="left", padx=(0, 10))

    make_label(row, "Identifier", BG_ITEM).pack(side="left", padx=(0, 6))
    el = make_entry(row, width=20, font=F_BODY_B, fg=FG if is_included else FG_DIM)
    el.insert(0, link_dict.get("label", ""))
    el.pack(side="left", padx=(0, 12))

    status_lbl = tk.Label(row, text="" if is_included else "EXCLUDED", font=F_TAG, bg=BG_ITEM, fg=FG_DIM)
    status_lbl.pack(side="left", padx=4)

    link_data = {"var": var, "label_entry": el, "frame": card, "type": "link"}

    _icon_controls(
        row, BG_ITEM,
        lambda: move_link(link_data, -1),
        lambda: move_link(link_data, 1),
        lambda: remove_link(link_data),
    ).pack(side="right", padx=(8, 0))

    lbl_link = make_label(row, "Link", BG_ITEM)
    eu = make_entry(row)
    eu.insert(0, link_dict.get("url", ""))

    if is_included:
        lbl_link.pack(side="left", padx=(0, 6))
        eu.pack(side="left", fill="x", expand=True)

    link_data["url_entry"] = eu

    def update_link_collapse_ui():
        if var.get():
            status_lbl.configure(text="")
            lbl_link.pack(side="left", padx=(0, 6))
            eu.pack(side="left", fill="x", expand=True)
            card.set_padding(pady=9)
            el.configure(fg=FG)
        else:
            lbl_link.pack_forget()
            eu.pack_forget()
            status_lbl.configure(text="EXCLUDED")
            card.set_padding(pady=6)
            el.configure(fg=FG_DIM)
        _autosave()
        update_scroll()

    header_widgets["links"].append(link_data)
    update_scroll()

# ---------------------------------------------------------------------------
# Document Style (typography and layout)
# ---------------------------------------------------------------------------
def build_document_style_widget():
    card = RoundedCard(scrollable_frame, bg=BG_SECTION, parent_bg=BG_APP,
                       border=BORDER_SECTION, radius=16, padx=16, pady=14)
    card.pack(fill="x", pady=7, padx=(14, 8))
    inner = card.inner

    top = tk.Frame(inner, bg=BG_SECTION)
    top.pack(fill="x", pady=(0, 10))
    tk.Label(top, text="Document Style", font=F_SECTION, bg=BG_SECTION, fg=FG).pack(side="left")
    tk.Label(top, text="Font and sizing options for the compiled resume",
             font=F_LABEL, bg=BG_SECTION, fg=FG_DIM).pack(side="left", padx=10, pady=(4, 0))

    style_card = RoundedCard(inner, bg=BG_ITEM, parent_bg=BG_SECTION,
                            border=BORDER_ITEM, radius=12, padx=14, pady=10)
    style_card.pack(fill="x")
    row = style_card.inner

    make_label(row, "Font Family", BG_ITEM).pack(side="left", padx=(0, 8))
    cur_font = master_data.get("font_family") or "Default (Computer Modern)"
    font_var = tk.StringVar(value=cur_font)
    font_combo = ttk.Combobox(
        row,
        textvariable=font_var,
        values=[
            "Default (Computer Modern)",
            "Charter",
            "Cormorant Garamond",
            "Fira Sans",
            "Roboto",
            "Noto Sans",
            "Source Sans Pro",
        ],
        state="readonly",
        width=24,
        style="Dark.TCombobox"
    )
    font_combo.var = font_var
    font_combo.set(cur_font)
    font_combo.pack(side="left", padx=(0, 24))

    make_label(row, "Font Size", BG_ITEM).pack(side="left", padx=(0, 8))
    cur_size = master_data.get("font_size") or "10pt"
    size_var = tk.StringVar(value=cur_size)
    size_combo = ttk.Combobox(
        row,
        textvariable=size_var,
        values=["8pt", "9pt", "10pt", "11pt", "12pt", "14pt"],
        state="readonly",
        width=8,
        style="Dark.TCombobox"
    )
    size_combo.var = size_var
    size_combo.set(cur_size)
    size_combo.pack(side="left")

    def _on_typography_change(event=None):
        if event and hasattr(event, "widget"):
            try:
                event.widget.state(["!pressed"])
            except Exception:
                pass
        for key in ("font_combo", "size_combo"):
            w = style_widgets.get(key)
            if w and w.winfo_exists():
                try:
                    w.state(["!pressed"])
                except Exception:
                    pass
        try:
            root.focus_set()
        except Exception:
            pass
        if _is_ui_initialized:
            save_master_yaml(show_popup=False)

    font_combo.bind("<<ComboboxSelected>>", _on_typography_change)
    size_combo.bind("<<ComboboxSelected>>", _on_typography_change)

    # Disable mouse wheel / trackpad scrolling over comboboxes so scrolling the page doesn't change dropdown values
    for cb in (font_combo, size_combo):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            cb.bind(seq, _on_mousewheel)
        try:
            cb.bind("<TouchpadScroll>", _on_touchpad)
        except tk.TclError:
            pass

    style_widgets["card"] = card
    style_widgets["font_combo"] = font_combo
    style_widgets["font_var"] = font_var
    style_widgets["size_combo"] = size_combo
    style_widgets["size_var"] = size_var

def build_header_widget():
    card = RoundedCard(scrollable_frame, bg=BG_SECTION, parent_bg=BG_APP,
                       border=BORDER_SECTION, radius=16, padx=16, pady=14)
    card.pack(fill="x", pady=7, padx=(14, 8))
    inner = card.inner

    top = tk.Frame(inner, bg=BG_SECTION)
    top.pack(fill="x", pady=(0, 10))
    tk.Label(top, text="Header", font=F_SECTION, bg=BG_SECTION, fg=FG).pack(side="left")
    tk.Label(top, text="Name and contact links shown at the top of the resume",
             font=F_LABEL, bg=BG_SECTION, fg=FG_DIM).pack(side="left", padx=10, pady=(4, 0))

    # Name
    name_card = RoundedCard(inner, bg=BG_ITEM, parent_bg=BG_SECTION,
                            border=BORDER_ITEM, radius=12, padx=14, pady=10)
    name_card.pack(fill="x", pady=(0, 6))
    make_label(name_card.inner, "Full Name", BG_ITEM).pack(side="left", padx=(0, 10))
    name_entry = make_entry(name_card.inner, font=(UI_FONT, 15, "bold"))
    name_entry.insert(0, master_data.get("name", "") or "")
    name_entry.pack(side="left", fill="x", expand=True)

    header_widgets["name_entry"] = name_entry
    header_widgets["links"] = []

    # Links
    make_label(inner, "LINKS & CONTACT  ·  phone numbers, emails, portfolios, github, etc.",
               BG_SECTION, fg=FG_DIM, font=F_TAG).pack(anchor="w", pady=(8, 2))
    links_container = tk.Frame(inner, bg=BG_SECTION)
    links_container.pack(fill="x")

    for link in master_data.get("links", []) or []:
        l_type = link.get("type")
        url = str(link.get("url", ""))
        lbl = str(link.get("label", ""))
        if l_type == "phone" or (l_type != "email" and url == "" and any(c.isdigit() for c in lbl) and "@" not in lbl):
            add_phone_widget(links_container, link)
        elif l_type == "email" or url.lower().startswith("mailto:") or ("@" in lbl and "." in lbl and not url.startswith("http")):
            add_email_widget(links_container, link)
        else:
            add_link_widget(links_container, link)

    btn_row = tk.Frame(inner, bg=BG_SECTION)
    btn_row.pack(fill="x", pady=(8, 0))

    PillButton(
        btn_row, "+ Add Phone Number",
        lambda: add_phone_widget(links_container),
        parent_bg=BG_SECTION, bg=BG_ITEM, fg=FG_MUTED, border=BORDER_ITEM, padx=12, pady=5,
    ).pack(side="left", padx=(0, 8))

    PillButton(
        btn_row, "+ Add Email",
        lambda: add_email_widget(links_container),
        parent_bg=BG_SECTION, bg=BG_ITEM, fg=FG_MUTED, border=BORDER_ITEM, padx=12, pady=5,
    ).pack(side="left", padx=(0, 8))

    PillButton(
        btn_row, "+ Add Link",
        lambda: add_link_widget(links_container),
        parent_bg=BG_SECTION, bg=BG_ITEM, fg=FG_MUTED, border=BORDER_ITEM, padx=12, pady=5,
    ).pack(side="left")

# Build document style + header + initial sections in UI
build_document_style_widget()
build_header_widget()
for sec in master_data.get("sections", []):
    add_section_widget(sec)
_is_ui_initialized = True
update_scroll()

# Escape special characters that have special meaning in LaTeX
def escape_latex(s):
    if not isinstance(s, str):
        return s
    result = []
    i = 0
    n = len(s)
    # Characters that must be escaped in LaTeX
    special_chars = {
        "%": r"\%",
        "&": r"\&",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "~": r"\textasciitilde{}",
    }
    while i < n:
        char = s[i]
        if char == "\\":
            # If already escaped (e.g. \% or \&), preserve it and avoid double-escaping
            if i + 1 < n and s[i+1] in special_chars:
                result.append(s[i:i+2])
                i += 2
                continue
            else:
                result.append(char)
                i += 1
                continue
        elif char in special_chars:
            result.append(special_chars[char])
            i += 1
        else:
            result.append(char)
            i += 1
    return "".join(result)

def escape_tree(obj):
    if isinstance(obj, str):
        return escape_latex(obj)
    elif isinstance(obj, list):
        return [escape_tree(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: escape_tree(v) for k, v in obj.items()}
    return obj

# Make bare links clickable: emails -> mailto:, domains -> https://
def normalize_url(url):
    url = (url or "").strip()
    if not url or "://" in url or url.startswith(("mailto:", "tel:")):
        return url
    if "@" in url:
        return f"mailto:{url}"
    return f"https://{url}"

# ---------------------------------------------------------------------------
# LaTeX Compilation & Preview Logic
# ---------------------------------------------------------------------------
preview_window = None

def find_latex_compiler():
    """Locate tectonic or pdflatex across PATH and standard macOS locations."""
    # 1. Tectonic (modern, auto-downloads packages)
    for path in [
        shutil.which("tectonic"),
        "/opt/homebrew/bin/tectonic",
        "/usr/local/bin/tectonic"
    ]:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return ("tectonic", path)

    # 2. pdflatex (MacTeX / BasicTeX)
    for path in [
        shutil.which("pdflatex"),
        "/Library/TeX/texbin/pdflatex",
        "/usr/local/bin/pdflatex",
        "/opt/homebrew/bin/pdflatex"
    ]:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return ("pdflatex", path)

    return (None, None)

def get_resume_base_filename():
    """Generate dynamic filename based on the user's name: {Name}'s_Resume."""
    name = ""
    if header_widgets and "name_entry" in header_widgets:
        name = header_widgets["name_entry"].get().strip()
    elif master_data and "name" in master_data:
        name = str(master_data.get("name", "")).strip()

    if name:
        # Sanitize filename (remove characters that are invalid in filenames)
        safe_name = "".join(c for c in name if c not in r'/\:*?"<>|').strip()
        safe_name = safe_name.replace(" ", "_")
        if safe_name:
            return f"{safe_name}'s_Resume"
    return "Resume"

def get_next_download_path(downloads_dir, base_name):
    """Find next available versioned filename: [Name]'s_Resume.pdf, [Name]'s_Resume_(1).pdf, etc."""
    base_pdf = os.path.join(downloads_dir, f"{base_name}.pdf")
    base_space_pdf = os.path.join(downloads_dir, f"{base_name.replace('_', ' ')}.pdf")

    # If neither base file exists yet in Downloads, use the base filename
    if not os.path.exists(base_pdf) and not os.path.exists(base_space_pdf):
        return base_pdf

    # If existing file(s) exist, find the first unused version number: (1), (2), (3)...
    idx = 1
    while True:
        cand_pdf = os.path.join(downloads_dir, f"{base_name}_({idx}).pdf")
        cand_space_pdf = os.path.join(downloads_dir, f"{base_name} ({idx}).pdf")
        cand_space_pdf2 = os.path.join(downloads_dir, f"{base_name.replace('_', ' ')} ({idx}).pdf")
        cand_space_pdf3 = os.path.join(downloads_dir, f"{base_name.replace('_', ' ')}_({idx}).pdf")
        if (not os.path.exists(cand_pdf) and not os.path.exists(cand_space_pdf)
                and not os.path.exists(cand_space_pdf2) and not os.path.exists(cand_space_pdf3)):
            return cand_pdf
        idx += 1

def render_latex_source():
    """Render current UI state through Jinja2 to ~/<Name>'s Resume.tex."""
    ui_sections = extract_sections_from_ui()
    compiled_sections = []

    for sec in ui_sections:
        if not sec["enabled"]:
            continue

        c_entries = []
        for item in sec["entries"]:
            if not item["enabled"]:
                continue
            c_bullets = [b["text"] for b in item["bullets"] if b["enabled"]]
            c_item = item.copy()
            c_item["bullets"] = c_bullets
            if c_item.get("type") in ("single-line", "single"):
                c_item["type"] = "single-line"
                c_item["title"] = item.get("title", item.get("field1", ""))
                c_item["subtitle"] = item.get("subtitle", item.get("field3", ""))
                c_item["date"] = item.get("date", item.get("field2", ""))
            else:
                c_item["type"] = "dual-line"
                c_item["field1"] = item.get("field1", item.get("title", ""))
                c_item["field2"] = item.get("field2", item.get("date", item.get("dates", "")))
                c_item["field3"] = item.get("field3", item.get("subtitle", ""))
                c_item["field4"] = item.get("field4", item.get("location", ""))
            c_entries.append(c_item)

        c_lines = [l for l in sec["simple_lines"] if l["enabled"]]

        if c_entries or c_lines:
            compiled_sections.append({
                "title": sec["title"],
                "enabled": True,
                "entries": c_entries,
                "simple_lines": c_lines
            })

    final_data = master_data.copy()
    final_data["sections"] = compiled_sections
    final_data.pop("links", None)

    # Escape all LaTeX special characters
    final_data = escape_tree(final_data)

    final_data["links"] = [
        {
            "label": escape_latex(l.get("label", "") or l.get("url", "")),
            "url": normalize_url(l.get("url", "")).replace("%", r"\%").replace("#", r"\#") if l.get("url") else "",
        }
        for l in master_data.get("links", []) or []
        if l.get("enabled", True) and (l.get("label") or l.get("url"))
    ]

    script_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
    env = Environment(
        loader=FileSystemLoader(script_dir),
        block_start_string=r'\BLOCK{',
        block_end_string='}',
        variable_start_string=r'\VAR{',
        variable_end_string='}',
        comment_start_string=r'\COMMENT{',
        comment_end_string='}',
        trim_blocks=True,
        autoescape=False
    )
    env.filters['latex_escape'] = escape_latex

    template = env.get_template("jakes-resume-tmpl.tex")
    rendered_tex = template.render(final_data)

    base_name = get_resume_base_filename()
    build_dir = os.path.expanduser("~/.resume_build")
    os.makedirs(build_dir, exist_ok=True)
    tex_path = os.path.join(build_dir, f"{base_name}.tex")
    pdf_path = os.path.join(build_dir, f"{base_name}.pdf")

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(rendered_tex)

    return tex_path, pdf_path, build_dir, base_name

def compile_tex_to_pdf(compiler_type, compiler_bin, build_dir, tex_path, pdf_path, base_name):
    """Pure subprocess compiler worker (no Tkinter widgets touched, safe for background threads)."""
    if not compiler_type:
        return (False, pdf_path, tex_path, "NO_COMPILER")

    try:
        if compiler_type == "tectonic":
            cmd = [compiler_bin, "-X", "compile", "--outdir", build_dir, tex_path]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode == 0 and os.path.exists(pdf_path):
                return (True, pdf_path, tex_path, None)
            err = proc.stderr.strip() or proc.stdout.strip()
            return (False, pdf_path, tex_path, err or "Tectonic compilation failed.")

        elif compiler_type == "pdflatex":
            cmd = [compiler_bin, "-interaction=nonstopmode", "-output-directory", build_dir, tex_path]
            proc = subprocess.run(cmd, capture_output=True, text=True)

            # Clean auxiliary files
            for ext in [".aux", ".out"]:
                aux_file = os.path.join(build_dir, f"{base_name}{ext}")
                if os.path.exists(aux_file):
                    try:
                        os.remove(aux_file)
                    except OSError:
                        pass

            if proc.returncode == 0 and os.path.exists(pdf_path):
                log_file = os.path.join(build_dir, f"{base_name}.log")
                if os.path.exists(log_file):
                    try:
                        os.remove(log_file)
                    except OSError:
                        pass
                return (True, pdf_path, tex_path, None)

            log_file = os.path.join(build_dir, f"{base_name}.log")
            log_tail = ""
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        log_tail = "".join(lines[-40:])
                except Exception:
                    pass
            return (False, pdf_path, tex_path, log_tail or proc.stderr.strip() or proc.stdout.strip() or "pdflatex compilation failed.")

    except Exception as e:
        return (False, pdf_path, tex_path, str(e))

def compile_resume_pdf():
    """Compile LaTeX source to PDF in ~/.resume_build. Returns (success, pdf_path, tex_path, err_msg)."""
    tex_path, pdf_path, build_dir, base_name = render_latex_source()
    compiler_type, compiler_bin = find_latex_compiler()
    return compile_tex_to_pdf(compiler_type, compiler_bin, build_dir, tex_path, pdf_path, base_name)

_is_compiling = False
_compile_queued = False
_compile_queue = queue.Queue()

def _poll_compile_queue():
    """Poll queue on the main Tkinter thread for finished background compilations."""
    global _is_compiling, _compile_queued
    try:
        while not _compile_queue.empty():
            success, pdf_path, tex_path, err = _compile_queue.get_nowait()
            _is_compiling = False

            if success and pdf_path and os.path.exists(pdf_path):
                if preview_pane:
                    preview_pane.load_pdf(pdf_path)
            else:
                if preview_pane and hasattr(preview_pane, "status_lbl"):
                    preview_pane.status_lbl.configure(text="Compile issue")

            if _compile_queued:
                _compile_queued = False
                recompile_preview_async()
    except Exception:
        pass
    root.after(80, _poll_compile_queue)

def recompile_preview_async():
    """Compile LaTeX to PDF in a background thread and update the preview pane without blocking the UI."""
    global _is_compiling, _compile_queued
    if not preview_pane:
        return

    if _is_compiling:
        _compile_queued = True
        return

    # Render LaTeX on the main thread (reads UI widgets in <2ms)
    try:
        tex_path, pdf_path, build_dir, base_name = render_latex_source()
        compiler_type, compiler_bin = find_latex_compiler()
    except Exception as e:
        print(f"Error rendering LaTeX source: {e}")
        return

    if not compiler_type:
        return

    _is_compiling = True
    _compile_queued = False

    if preview_pane and hasattr(preview_pane, "status_lbl"):
        preview_pane.status_lbl.configure(text="Compiling...")

    def _worker():
        try:
            res = compile_tex_to_pdf(compiler_type, compiler_bin, build_dir, tex_path, pdf_path, base_name)
        except Exception as e:
            res = (False, pdf_path, tex_path, str(e))
        _compile_queue.put(res)

    threading.Thread(target=_worker, daemon=True).start()

root.after(100, _poll_compile_queue)

def show_compiler_install_dialog(tex_path=None):
    """Dialog guiding user on how to install a LaTeX compiler."""
    dialog = tk.Toplevel(root)
    dialog.title("LaTeX Compiler Needed")
    dialog.configure(bg=BG_SECTION)
    dialog.geometry("520x240")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    root.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - 260
    y = root.winfo_y() + (root.winfo_height() // 2) - 120
    dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

    tk.Label(
        dialog,
        text="LaTeX Compiler Not Found",
        font=F_BODY_B,
        bg=BG_SECTION,
        fg=FG
    ).pack(anchor="w", padx=24, pady=(20, 6))

    saved_note = f"Your resume source was generated at:\n{tex_path}" if tex_path else ""
    msg = (
        "To compile and preview your resume directly, install Tectonic (modern, fast XeTeX engine):\n\n"
        "        brew install tectonic\n\n"
        "or install BasicTeX with:\n"
        "        brew install --cask basictex"
    )
    if saved_note:
        msg += f"\n\n{saved_note}"
    tk.Label(
        dialog,
        text=msg,
        font=F_BODY,
        bg=BG_SECTION,
        fg=FG_MUTED,
        justify="left"
    ).pack(anchor="w", padx=24, pady=4)

    btn_frame = tk.Frame(dialog, bg=BG_SECTION)
    btn_frame.pack(fill="x", padx=24, pady=(16, 0))

    PillButton(
        btn_frame, "Close", dialog.destroy, parent_bg=BG_SECTION,
        bg=BG_ITEM, fg=FG, border=BORDER_ITEM, font=F_BTN_B, padx=16, pady=6
    ).pack(side="right")

def recompile_for_preview():
    save_master_yaml(show_popup=False, recompile_preview=False)
    success, pdf_path, tex_path, err = compile_resume_pdf()
    return (success, pdf_path, err)

def on_preview_click():
    if not save_master_yaml(show_popup=False, recompile_preview=False):
        return

    preview_pane.status_lbl.configure(text="Compiling...")
    root.update_idletasks()

    success, pdf_path, tex_path, err_msg = compile_resume_pdf()

    if not success:
        preview_pane.status_lbl.configure(text="Compile failed")
        if err_msg == "NO_COMPILER":
            show_compiler_install_dialog(tex_path)
        else:
            messagebox.showerror("LaTeX Compilation Error", err_msg, parent=root)
        return

    preview_pane.load_pdf(pdf_path)

def generate_pdf():
    if not save_master_yaml(show_popup=False, recompile_preview=False):
        return

    success, pdf_path, tex_path, err_msg = compile_resume_pdf()

    if not success:
        if err_msg == "NO_COMPILER":
            show_compiler_install_dialog(tex_path)
        else:
            messagebox.showerror(
                "Compilation Error",
                f"LaTeX compilation failed.\n\n"
                f"Source saved to: {tex_path}\n\n"
                f"Error details:\n{err_msg}"
            )
        return

    downloads_dir = os.path.expanduser("~/Downloads")
    base_name = get_resume_base_filename()
    download_pdf_path = get_next_download_path(downloads_dir, base_name)

    # Copy to fresh versioned file to guarantee a new inode and current "Date Added" in Finder
    try:
        shutil.copyfile(pdf_path, download_pdf_path)
    except Exception as e:
        download_pdf_path = pdf_path

    messagebox.showinfo(
        "Download Complete",
        f"Resume downloaded successfully to your Downloads folder!\n\n"
        f"File: {os.path.basename(download_pdf_path)}\n"
        f"Location: {download_pdf_path}\n\n"
        f"(master.yaml also updated)"
    )

# Function to add new custom section (custom modal dialog compatible with Tk 9 on macOS)
def prompt_new_section():
    dialog = tk.Toplevel(root)
    dialog.title("Add New Section")
    dialog.configure(bg=BG_SECTION)
    dialog.geometry("420x170")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    # Center relative to root window
    root.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - 210
    y = root.winfo_y() + (root.winfo_height() // 2) - 85
    dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

    tk.Label(
        dialog,
        text="Enter the title for the new section",
        font=F_BODY_B,
        bg=BG_SECTION,
        fg=FG
    ).pack(anchor="w", padx=24, pady=(22, 8))

    entry = make_entry(dialog, font=F_BODY)
    entry.pack(fill="x", padx=24)
    entry.focus_set()

    def on_ok():
        title = entry.get().strip()
        if title:
            add_section_widget({"title": title, "enabled": True, "entries": [], "simple_lines": []})
            update_scroll()
            canvas.yview_moveto(1.0)
        dialog.destroy()

    def on_cancel():
        dialog.destroy()

    btn_frame = tk.Frame(dialog, bg=BG_SECTION)
    btn_frame.pack(fill="x", padx=24, pady=18)

    PillButton(
        btn_frame, "Add Section", on_ok, parent_bg=BG_SECTION,
        bg=FG, fg=BG_APP, hover_bg="#ffffff", font=F_BTN_B, padx=14, pady=6,
    ).pack(side="right")

    PillButton(
        btn_frame, "Cancel", on_cancel, parent_bg=BG_SECTION,
        bg=BG_ITEM, fg=FG_MUTED, border=BORDER_ITEM, font=F_BTN, padx=14, pady=6,
    ).pack(side="right", padx=(0, 8))

    entry.bind("<Return>", lambda e: on_ok())
    entry.bind("<Escape>", lambda e: on_cancel())



PillButton(
    action_frame, "+  New Section", prompt_new_section, parent_bg=BG_BAR,
    bg=BG_ITEM, fg=FG, border=BORDER_ITEM, font=F_BTN_B, padx=14, pady=7, radius=10,
).pack(side="left", padx=(20, 10))

autosave_lbl = tk.Label(action_frame, text="", font=F_LABEL, bg=BG_BAR, fg=FG_MUTED)
autosave_lbl.pack(side="left", padx=10)

PillButton(
    action_frame, "Download PDF", generate_pdf, parent_bg=BG_BAR,
    bg=FG, fg=BG_APP, hover_bg="#ffffff", font=F_BTN_B, padx=16, pady=7, radius=10,
).pack(side="right", padx=(8, 20))


# Try to load existing PDF on launch into the embedded preview pane
def _init_preview_on_launch():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
        tmpl_path = os.path.join(script_dir, "jakes-resume-tmpl.tex")
        base_name = get_resume_base_filename()
        build_dir = os.path.expanduser("~/.resume_build")
        build_pdf = os.path.join(build_dir, f"{base_name}.pdf")
        if os.path.exists(build_pdf):
            preview_pane.load_pdf(build_pdf)
            # If the template was modified more recently than the existing PDF, recompile immediately
            if os.path.exists(tmpl_path) and os.path.getmtime(tmpl_path) > os.path.getmtime(build_pdf):
                recompile_preview_async()
            return

        downloads_dir = os.path.expanduser("~/Downloads")
        pdf_path = os.path.join(downloads_dir, f"{base_name}.pdf")
        if os.path.exists(pdf_path):
            preview_pane.load_pdf(pdf_path)
        else:
            space_pdf = os.path.join(downloads_dir, f"{base_name.replace('_', ' ')}.pdf")
            if os.path.exists(space_pdf):
                preview_pane.load_pdf(space_pdf)
            else:
                output_fallback = os.path.join(downloads_dir, "output.pdf")
                if os.path.exists(output_fallback):
                    preview_pane.load_pdf(output_fallback)
                else:
                    preview_pane.show_message("Preview ready.\n\nChanges automatically compile to PDF.")
        recompile_preview_async()
    except Exception as e:
        preview_pane.show_message(f"Preview ready.\n\n{e}")

root.after(250, _init_preview_on_launch)

_last_tmpl_mtime = None

def _watch_template_file():
    """Continuously monitor jakes-resume-tmpl.tex and trigger preview recompile on file change."""
    global _last_tmpl_mtime
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
        tmpl_path = os.path.join(script_dir, "jakes-resume-tmpl.tex")
        if os.path.exists(tmpl_path):
            current_mtime = os.path.getmtime(tmpl_path)
            if _last_tmpl_mtime is None:
                _last_tmpl_mtime = current_mtime
            elif current_mtime != _last_tmpl_mtime:
                _last_tmpl_mtime = current_mtime
                recompile_preview_async()
    except Exception:
        pass
    root.after(500, _watch_template_file)

root.after(500, _watch_template_file)

# Global keyboard shortcuts for live preview compile
root.bind("<Command-r>", lambda e: on_preview_click())
root.bind("<F5>", lambda e: on_preview_click())

if __name__ == "__main__":
    root.mainloop()