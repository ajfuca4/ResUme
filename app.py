import tkinter as tk
from tkinter import messagebox
import yaml
import os
import sys
import shutil
from jinja2 import Environment, FileSystemLoader

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
                        "enabled": True,
                        "field1": "Gitlytics",
                        "field2": "June 2020 -- Present",
                        "field3": "Python, Flask, React, PostgreSQL, Docker",
                        "field4": "",
                        "bullets": [
                            {"enabled": True, "text": "Developed a full-stack web application using with Flask serving a REST API with React as the frontend"},
                            {"enabled": True, "text": "Implemented GitHub OAuth to get data from user’s repositories"},
                            {"enabled": True, "text": "Visualized GitHub data to show collaboration"},
                            {"enabled": True, "text": "Used Celery and Redis for asynchronous tasks"}
                        ]
                    },
                    {
                        "enabled": True,
                        "field1": "Simple Paintball",
                        "field2": "May 2018 -- May 2020",
                        "field3": "Spigot API, Java, Maven, TravisCI, Git",
                        "field4": "",
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

    return data

master_data = load_data()

# 2. Setup native desktop window
root = tk.Tk()
root.title("Local Resume Builder - Dynamic Section Editor")
root.geometry("860x880")

# Header Section
header_frame = tk.Frame(root, pady=8, bg="#f8fafc")
header_frame.pack(fill="x")

tk.Label(
    header_frame,
    text="Local Resume Builder",
    font=("Arial", 16, "bold"),
    bg="#f8fafc",
    fg="#0f172a"
).pack()

tk.Label(
    header_frame,
    text="Build, toggle, and edit custom sections, subheaders, and bullets.",
    font=("Arial", 10),
    bg="#f8fafc",
    fg="#64748b"
).pack(pady=(2, 8))

# Bottom Action Toolbar (docked cleanly to bottom before expandable center)
action_frame = tk.Frame(root, pady=10, bg="#f1f5f9")
action_frame.pack(side="bottom", fill="x")

# Scrollable canvas for dynamic resume components (occupies all remaining space)
canvas_container = tk.Frame(root)
canvas_container.pack(side="top", fill="both", expand=True, padx=12, pady=4)

canvas = tk.Canvas(canvas_container, borderwidth=0, highlightthickness=0, yscrollincrement=1)
scrollbar = tk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas)

def _on_frame_configure(e):
    canvas.configure(scrollregion=canvas.bbox("all"))

scrollable_frame.bind("<Configure>", _on_frame_configure)

canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

def on_canvas_configure(event):
    canvas.itemconfig(canvas_window, width=event.width)

canvas.bind("<Configure>", on_canvas_configure)
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# 1. macOS Trackpad Two-Finger Scrolling (<TouchpadScroll>) in Tk 9 Aqua
def _on_touchpad(event):
    delta = event.delta
    # In Tk 9 Aqua, dxdy is packed into delta: deltaX = dxdy >> 16, deltaY = low 16 bits signed
    low = delta & 0xFFFF
    dy = low if low < 0x8000 else low - 0x10000
    if dy != 0:
        # yscrollincrement=1 makes units equal to pixels for smooth 1:1 trackpad scrolling
        canvas.yview_scroll(-dy, "units")
    return "break"

# 2. Traditional Mouse Wheel Scrolling (<MouseWheel>)
def _on_mousewheel(event):
    if sys.platform == "darwin":
        delta = event.delta
        if abs(delta) >= 120:
            units = -int((delta / 120) * 35)
        else:
            units = -int(delta * 4)
        if units == 0 and delta != 0:
            units = -4 if delta > 0 else 4
        canvas.yview_scroll(units, "units")
    elif event.num == 5 or event.delta < 0:
        canvas.yview_scroll(25, "units")
    elif event.num == 4 or event.delta > 0:
        canvas.yview_scroll(-25, "units")
    return "break"

# Bind across ALL widget classes so trackpad gestures scroll the page even when hovering over text boxes/entries
for widget_class in ("Text", "Entry", "Label", "Button", "Checkbutton", "Frame", "LabelFrame", "Canvas"):
    root.bind_class(widget_class, "<TouchpadScroll>", _on_touchpad)
    root.bind_class(widget_class, "<MouseWheel>", _on_mousewheel)
    root.bind_class(widget_class, "<Button-4>", _on_mousewheel)
    root.bind_class(widget_class, "<Button-5>", _on_mousewheel)

root.bind_all("<TouchpadScroll>", _on_touchpad)
root.bind_all("<MouseWheel>", _on_mousewheel)
root.bind_all("<Button-4>", _on_mousewheel)
root.bind_all("<Button-5>", _on_mousewheel)

# Keyboard navigation (PageUp, PageDown, Home, End, Up, Down)
def _on_key_scroll(event):
    widget = root.focus_get()
    in_text = widget and widget.winfo_class() in ("Text", "Entry")

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

root.bind_all("<Key>", _on_key_scroll)

# State tracking for all UI widgets
sections_widgets = []

def update_scroll():
    scrollable_frame.update_idletasks()
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
            f1 = it["e1"].get().strip()
            f2 = it["e2"].get().strip()
            f3 = it["e3"].get().strip()
            f4 = it["e4"].get().strip()

            bullets_list = []
            for b in it["bullets"]:
                b_text = b["text_widget"].get("1.0", "end-1c").strip()
                b_enabled = b["var"].get()
                if b_text:
                    bullets_list.append({"enabled": b_enabled, "text": b_text})

            if f1 or f2 or f3 or f4 or bullets_list:
                entries_list.append({
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
            txt = l["text_entry"].get().strip()
            l_enabled = l["var"].get()
            if lbl or txt:
                simple_lines_list.append({
                    "enabled": l_enabled,
                    "label": lbl,
                    "text": txt
                })

        sections_list.append({
            "title": sec_title,
            "enabled": sec_enabled,
            "entries": entries_list,
            "simple_lines": simple_lines_list
        })
    return sections_list

# Save to master.yaml
def save_master_yaml(show_popup=True):
    master_data["sections"] = extract_sections_from_ui()

    try:
        with open("master.yaml", "w", encoding="utf-8") as f:
            yaml.dump(master_data, f, sort_keys=False, allow_unicode=True)
        if show_popup:
            messagebox.showinfo("Saved", "All sections, subheaders, and bullets saved to master.yaml!")
        return True
    except Exception as e:
        messagebox.showerror("Save Error", f"Failed to save master.yaml:\n{e}")
        return False

_is_ui_initialized = False

# Autosave when any field loses focus (clicked away / deselected)
def on_field_focus_out(event):
    if not _is_ui_initialized:
        return
    try:
        if event.widget.winfo_toplevel() == root:
            save_master_yaml(show_popup=False)
    except Exception:
        pass

# Ensure clicking anywhere outside an active text/entry field unfocuses it
def on_global_click(event):
    if not _is_ui_initialized:
        return
    widget = event.widget
    focused = root.focus_get()
    if focused and focused.winfo_class() in ("Entry", "Text"):
        if widget != focused and widget.winfo_class() not in ("Entry", "Text"):
            root.focus_set()

# Enter key unfocuses entry and triggers save
def on_entry_return(event):
    if not _is_ui_initialized:
        return
    try:
        if event.widget.winfo_toplevel() == root:
            root.focus_set()
    except Exception:
        pass

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
def remove_bullet(item_data, bullet_data):
    bullet_data["frame"].destroy()
    item_data["bullets"].remove(bullet_data)
    if _is_ui_initialized:
        save_master_yaml(show_popup=False)
    update_scroll()

def add_bullet_widget(item_data, parent_container, enabled=True, text=""):
    row = tk.Frame(parent_container)
    row.pack(fill="x", expand=True, pady=2, padx=(12, 0))

    var = tk.BooleanVar(value=enabled)
    cb = tk.Checkbutton(
        row,
        variable=var,
        command=lambda: save_master_yaml(show_popup=False) if _is_ui_initialized else None
    )
    cb.pack(side="left", anchor="n")

    txt = tk.Text(row, height=2, wrap="word", font=("Arial", 10), relief="solid", bd=1)
    txt.insert("1.0", text)
    txt.pack(side="left", fill="x", expand=True, padx=4)

    bullet_data = {"var": var, "text_widget": txt, "frame": row}

    btn_box = tk.Frame(row)
    btn_box.pack(side="right", anchor="n")

    tk.Button(
        btn_box,
        text="▲",
        font=("Arial", 8),
        bd=1,
        relief="groove",
        padx=2,
        pady=0,
        command=lambda: move_bullet_up(item_data, bullet_data)
    ).pack(side="left", padx=1)

    tk.Button(
        btn_box,
        text="▼",
        font=("Arial", 8),
        bd=1,
        relief="groove",
        padx=2,
        pady=0,
        command=lambda: move_bullet_down(item_data, bullet_data)
    ).pack(side="left", padx=1)

    tk.Button(
        btn_box,
        text="✕",
        fg="#dc2626",
        bd=0,
        padx=3,
        pady=0,
        font=("Arial", 9),
        command=lambda: remove_bullet(item_data, bullet_data)
    ).pack(side="left", padx=(1, 0))

    item_data["bullets"].append(bullet_data)
    update_scroll()

# Subheader item management (Field 1, Field 2, Field 3, Field 4 + Bullets)
def remove_item(sec_data, item_data):
    item_data["frame"].destroy()
    sec_data["entries"].remove(item_data)
    if _is_ui_initialized:
        save_master_yaml(show_popup=False)
    update_scroll()

def add_item_widget(sec_data, parent_container, item_dict=None):
    if item_dict is None:
        item_dict = {"enabled": True, "field1": "", "field2": "", "field3": "", "field4": "", "bullets": []}

    card = tk.LabelFrame(parent_container, text=" Subheader Item ", padx=8, pady=6, fg="#334155")
    card.pack(fill="x", expand=True, pady=4, padx=4)

    var = tk.BooleanVar(value=item_dict.get("enabled", True))

    # Row 1: Field 1 (Subheader / Title) & Field 2 (Right-hand text / Dates)
    r1 = tk.Frame(card)
    r1.pack(fill="x", expand=True, pady=1)

    tk.Checkbutton(
        r1,
        variable=var,
        command=lambda: save_master_yaml(show_popup=False) if _is_ui_initialized else None
    ).pack(side="left")

    tk.Label(r1, text="Field 1 (Title/Header):", font=("Arial", 9, "bold")).pack(side="left")
    e1 = tk.Entry(r1, font=("Arial", 10, "bold"))
    e1.insert(0, item_dict.get("field1", ""))
    e1.pack(side="left", fill="x", expand=True, padx=4)

    tk.Label(r1, text="Field 2 (Dates/Right):", font=("Arial", 9)).pack(side="left")
    e2 = tk.Entry(r1, width=22)
    e2.insert(0, item_dict.get("field2", ""))
    e2.pack(side="left", padx=4)

    item_data = {"var": var, "e1": e1, "e2": e2, "frame": card, "bullets": []}

    item_controls = tk.Frame(r1)
    item_controls.pack(side="right")

    tk.Button(
        item_controls,
        text="▲",
        font=("Arial", 8),
        bd=1,
        relief="groove",
        padx=3,
        pady=0,
        command=lambda: move_item_up(sec_data, item_data)
    ).pack(side="left", padx=1)

    tk.Button(
        item_controls,
        text="▼",
        font=("Arial", 8),
        bd=1,
        relief="groove",
        padx=3,
        pady=0,
        command=lambda: move_item_down(sec_data, item_data)
    ).pack(side="left", padx=1)

    tk.Button(
        item_controls,
        text="✕ Delete Item",
        fg="#dc2626",
        bd=0,
        font=("Arial", 9),
        command=lambda: remove_item(sec_data, item_data)
    ).pack(side="left", padx=(2, 0))

    # Row 2: Field 3 (Left-hand subtext / Company/Degree) & Field 4 (Right-hand subtext / Location)
    r2 = tk.Frame(card)
    r2.pack(fill="x", expand=True, pady=1)

    tk.Label(r2, text="Field 3 (Subtext/Company):", font=("Arial", 9)).pack(side="left", padx=(24, 0))
    e3 = tk.Entry(r2, font=("Arial", 10, "italic"))
    e3.insert(0, item_dict.get("field3", ""))
    e3.pack(side="left", fill="x", expand=True, padx=4)

    tk.Label(r2, text="Field 4 (Location/Right):", font=("Arial", 9)).pack(side="left")
    e4 = tk.Entry(r2, width=22)
    e4.insert(0, item_dict.get("field4", ""))
    e4.pack(side="left", padx=4)

    item_data["e3"] = e3
    item_data["e4"] = e4

    # Bullets container
    bullets_container = tk.Frame(card)
    bullets_container.pack(fill="x", expand=True, pady=(4, 2))

    for b in item_dict.get("bullets", []):
        b_en = b.get("enabled", True) if isinstance(b, dict) else True
        b_txt = b.get("text", "") if isinstance(b, dict) else str(b)
        add_bullet_widget(item_data, bullets_container, b_en, b_txt)

    add_b_btn = tk.Button(
        card,
        text="+ Add Bullet",
        font=("Arial", 9),
        command=lambda: add_bullet_widget(item_data, bullets_container, True, "")
    )
    add_b_btn.pack(anchor="w", padx=24, pady=(2, 4))

    sec_data["entries"].append(item_data)
    update_scroll()

# Simple line management (Title + Content, e.g. Technical Skills)
def remove_line(sec_data, line_data):
    line_data["frame"].destroy()
    sec_data["simple_lines"].remove(line_data)
    if _is_ui_initialized:
        save_master_yaml(show_popup=False)
    update_scroll()

def add_line_widget(sec_data, parent_container, line_dict=None):
    if line_dict is None:
        line_dict = {"enabled": True, "label": "", "text": ""}

    row = tk.Frame(parent_container, pady=2)
    row.pack(fill="x", expand=True, padx=4)

    var = tk.BooleanVar(value=line_dict.get("enabled", True))
    tk.Checkbutton(
        row,
        variable=var,
        command=lambda: save_master_yaml(show_popup=False) if _is_ui_initialized else None
    ).pack(side="left")

    tk.Label(row, text="Title/Label:", font=("Arial", 9, "bold")).pack(side="left")
    el = tk.Entry(row, width=18, font=("Arial", 10, "bold"))
    el.insert(0, line_dict.get("label", ""))
    el.pack(side="left", padx=4)

    tk.Label(row, text="Content List:", font=("Arial", 9)).pack(side="left")
    et = tk.Entry(row, font=("Arial", 10))
    et.insert(0, line_dict.get("text", ""))
    et.pack(side="left", fill="x", expand=True, padx=4)

    line_data = {"var": var, "label_entry": el, "text_entry": et, "frame": row}

    line_controls = tk.Frame(row)
    line_controls.pack(side="right")

    tk.Button(
        line_controls,
        text="▲",
        font=("Arial", 8),
        bd=1,
        relief="groove",
        padx=2,
        pady=0,
        command=lambda: move_line_up(sec_data, line_data)
    ).pack(side="left", padx=1)

    tk.Button(
        line_controls,
        text="▼",
        font=("Arial", 8),
        bd=1,
        relief="groove",
        padx=2,
        pady=0,
        command=lambda: move_line_down(sec_data, line_data)
    ).pack(side="left", padx=1)

    tk.Button(
        line_controls,
        text="✕",
        fg="#dc2626",
        bd=0,
        font=("Arial", 9),
        command=lambda: remove_line(sec_data, line_data)
    ).pack(side="left", padx=(1, 0))

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

    card = tk.LabelFrame(
        scrollable_frame,
        text="",
        padx=12,
        pady=10 if is_included else 4,
        bd=2,
        relief="groove",
        bg="#ffffff"
    )
    card.pack(fill="x", expand=True, pady=8, padx=10)

    # Top Bar of Section
    top = tk.Frame(card, bg="#ffffff")
    top.pack(fill="x", expand=True, pady=(0, 6 if is_included else 0))

    var = tk.BooleanVar(value=is_included)

    cb = tk.Checkbutton(top, variable=var, bg="#ffffff")
    cb.pack(side="left")

    tk.Label(top, text="Section Name:", font=("Arial", 10, "bold"), bg="#ffffff").pack(side="left")
    title_entry = tk.Entry(top, font=("Arial", 12, "bold"), width=24)
    title_entry.insert(0, sec_dict.get("title", "New Section"))
    title_entry.pack(side="left", padx=6)

    status_lbl = tk.Label(
        top,
        text="" if is_included else "(Excluded)",
        font=("Arial", 9, "italic"),
        bg="#ffffff",
        fg="#64748b"
    )
    status_lbl.pack(side="left", padx=4)

    sec_data = {
        "var": var,
        "title_entry": title_entry,
        "frame": card,
        "entries": [],
        "simple_lines": []
    }

    sec_controls = tk.Frame(top, bg="#ffffff")
    sec_controls.pack(side="right")

    tk.Button(
        sec_controls,
        text="▲ Move Up",
        font=("Arial", 9),
        bd=1,
        relief="groove",
        bg="#f1f5f9",
        fg="#334155",
        padx=4,
        pady=1,
        command=lambda: move_section_up(sec_data)
    ).pack(side="left", padx=2)

    tk.Button(
        sec_controls,
        text="▼ Move Down",
        font=("Arial", 9),
        bd=1,
        relief="groove",
        bg="#f1f5f9",
        fg="#334155",
        padx=4,
        pady=1,
        command=lambda: move_section_down(sec_data)
    ).pack(side="left", padx=2)

    tk.Button(
        sec_controls,
        text="✕ Delete Section",
        fg="#dc2626",
        bd=0,
        font=("Arial", 9),
        bg="#ffffff",
        padx=4,
        command=lambda: remove_section(sec_data)
    ).pack(side="left", padx=(4, 0))

    # Content body container (collapsible)
    body_frame = tk.Frame(card, bg="#ffffff")
    if is_included:
        body_frame.pack(fill="x", expand=True)

    # Subheaders container
    entries_container = tk.Frame(body_frame, bg="#ffffff")
    entries_container.pack(fill="x", expand=True)

    # Simple lines container
    lines_container = tk.Frame(body_frame, bg="#ffffff")
    lines_container.pack(fill="x", expand=True)

    for item in sec_dict.get("entries", []):
        add_item_widget(sec_data, entries_container, item)

    for line in sec_dict.get("simple_lines", []):
        add_line_widget(sec_data, lines_container, line)

    # Action bar for this section
    sec_actions = tk.Frame(body_frame, pady=6, bg="#ffffff")
    sec_actions.pack(fill="x")

    tk.Button(
        sec_actions,
        text="+ Add Subheader Item (with bullets)",
        font=("Arial", 9),
        command=lambda: add_item_widget(sec_data, entries_container)
    ).pack(side="left", padx=(0, 8))

    tk.Button(
        sec_actions,
        text="+ Add Single Line (e.g. Skills / Cert)",
        font=("Arial", 9),
        command=lambda: add_line_widget(sec_data, lines_container)
    ).pack(side="left")

    def update_collapse_ui():
        if var.get():
            body_frame.pack(fill="x", expand=True)
            card.configure(pady=10)
            top.pack_configure(pady=(0, 6))
            status_lbl.configure(text="")
        else:
            body_frame.pack_forget()
            card.configure(pady=4)
            top.pack_configure(pady=0)
            status_lbl.configure(text="(Excluded)")
            save_master_yaml(show_popup=False)
        update_scroll()

    cb.configure(command=update_collapse_ui)

    sections_widgets.append(sec_data)
    update_scroll()

# Build initial sections in UI
for sec in master_data.get("sections", []):
    add_section_widget(sec)
update_scroll()
_is_ui_initialized = True

# Escape special characters that have special meaning in LaTeX
def escape_latex(s):
    if not isinstance(s, str):
        return s
    result = []
    i = 0
    n = len(s)
    # Characters that must be escaped with a backslash in LaTeX
    special_chars = {"%": r"\%", "&": r"\&", "$": r"\$", "#": r"\#", "_": r"\_"}
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

# Generate PDF Compilation Logic
def generate_pdf():
    # 1. Sync and save latest edits
    if not save_master_yaml(show_popup=False):
        return

    # 2. Build filtered sections for LaTeX (only checked items and bullets)
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

    # Escape all LaTeX special characters (e.g., % -> \%, & -> \&, $ -> \$, _ -> \_, # -> \#)
    final_data = escape_tree(final_data)

    # 3. Configure Jinja for LaTeX
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

    try:
        template = env.get_template("jakes-resume-tmpl.tex")
        rendered_tex = template.render(final_data)

        # Target user's Downloads folder
        downloads_dir = os.path.expanduser("~/Downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        tex_path = os.path.join(downloads_dir, "output.tex")
        pdf_path = os.path.join(downloads_dir, "output.pdf")

        # Save to ~/Downloads/output.tex
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(rendered_tex)

        # Remove any stale output files in root directory to avoid confusion
        for stale in ["output.tex", "output.pdf"]:
            if os.path.exists(stale):
                try:
                    os.remove(stale)
                except OSError:
                    pass

        # Trigger LaTeX compiler if available
        if shutil.which("pdflatex"):
            exit_code = os.system(f'pdflatex -interaction=nonstopmode -output-directory "{downloads_dir}" "{tex_path}"')

            # Clean up auxiliary files from downloads folder
            for ext in [".aux", ".out"]:
                aux_file = os.path.join(downloads_dir, f"output{ext}")
                if os.path.exists(aux_file):
                    try:
                        os.remove(aux_file)
                    except OSError:
                        pass

            if exit_code == 0:
                log_file = os.path.join(downloads_dir, "output.log")
                if os.path.exists(log_file):
                    try:
                        os.remove(log_file)
                    except OSError:
                        pass
                messagebox.showinfo(
                    "Success",
                    f"Resume compiled successfully to your Downloads folder!\n\n"
                    f"PDF: {pdf_path}\n"
                    f"(master.yaml also updated)"
                )
            else:
                messagebox.showerror(
                    "Compilation Error",
                    f"LaTeX compilation failed.\n"
                    f"Source saved to: {tex_path}\n"
                    f"Check {os.path.join(downloads_dir, 'output.log')} for details."
                )
        else:
            messagebox.showwarning(
                "LaTeX Output Saved",
                f"output.tex was created successfully and saved to your Downloads folder:\n{tex_path}\n\n"
                "Note: 'pdflatex' was not found on your system.\n"
                "To generate PDFs directly, install BasicTeX with:\n"
                "brew install --cask basictex"
            )
    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate resume:\n{e}")

# Function to add new custom section (custom modal dialog compatible with Tk 9 on macOS)
def prompt_new_section():
    dialog = tk.Toplevel(root)
    dialog.title("Add New Section")
    dialog.geometry("400x160")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    # Center relative to root window
    root.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - 200
    y = root.winfo_y() + (root.winfo_height() // 2) - 80
    dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

    tk.Label(
        dialog,
        text="Enter the title for the new section:",
        font=("Arial", 11, "bold")
    ).pack(pady=(20, 8))

    entry = tk.Entry(dialog, font=("Arial", 11), width=30)
    entry.pack(pady=4)
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

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=14)

    ok_btn = tk.Button(
        btn_frame,
        text="Add Section",
        font=("Arial", 10, "bold"),
        bg="#10b981",
        fg="#047857",
        padx=12,
        command=on_ok
    )
    ok_btn.pack(side="left", padx=6)

    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        font=("Arial", 10),
        padx=8,
        command=on_cancel
    )
    cancel_btn.pack(side="left", padx=6)

    entry.bind("<Return>", lambda e: on_ok())
    entry.bind("<Escape>", lambda e: on_cancel())



tk.Button(
    action_frame,
    text="+ Add New Section",
    font=("Arial", 10, "bold"),
    command=prompt_new_section,
    padx=10,
    pady=4
).pack(side="left", padx=(20, 10))

tk.Button(
    action_frame,
    text="💾 Save to master.yaml",
    font=("Arial", 10, "bold"),
    command=lambda: save_master_yaml(show_popup=True),
    padx=10,
    pady=4
).pack(side="left", padx=10)

tk.Button(
    action_frame,
    text="📄 Generate Resume PDF",
    font=("Arial", 10, "bold"),
    bg="#2563eb",
    fg="#1d4ed8",
    padx=14,
    pady=4,
    command=generate_pdf
).pack(side="right", padx=(10, 20))

if __name__ == "__main__":
    root.mainloop()