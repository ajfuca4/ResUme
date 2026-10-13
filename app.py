import tkinter as tk
from tkinter import messagebox, simpledialog
import yaml
import os
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
).pack(pady=(2, 6))

# Top Toolbar
top_toolbar = tk.Frame(header_frame, bg="#f8fafc")
top_toolbar.pack(fill="x", padx=16, pady=4)

# Scrollable canvas for dynamic resume components
canvas_container = tk.Frame(root)
canvas = tk.Canvas(canvas_container, borderwidth=0, highlightthickness=0)
scrollbar = tk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

def on_canvas_configure(event):
    canvas.itemconfig(canvas_window, width=event.width)

canvas.bind("<Configure>", on_canvas_configure)
canvas.configure(yscrollcommand=scrollbar.set)

canvas_container.pack(fill="both", expand=True, padx=12, pady=4)
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

def _on_mousewheel(event):
    if event.num == 5 or event.delta < 0:
        canvas.yview_scroll(1, "units")
    elif event.num == 4 or event.delta > 0:
        canvas.yview_scroll(-1, "units")

root.bind_all("<MouseWheel>", _on_mousewheel)

# State tracking for all UI widgets
sections_widgets = []

def update_scroll():
    scrollable_frame.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))

# Bullet management
def remove_bullet(item_data, bullet_data):
    bullet_data["frame"].destroy()
    item_data["bullets"].remove(bullet_data)
    update_scroll()

def add_bullet_widget(item_data, parent_container, enabled=True, text=""):
    row = tk.Frame(parent_container)
    row.pack(fill="x", expand=True, pady=2, padx=(12, 0))

    var = tk.BooleanVar(value=enabled)
    cb = tk.Checkbutton(row, variable=var)
    cb.pack(side="left", anchor="n")

    txt = tk.Text(row, height=2, wrap="word", font=("Arial", 10), relief="solid", bd=1)
    txt.insert("1.0", text)
    txt.pack(side="left", fill="x", expand=True, padx=4)

    bullet_data = {"var": var, "text_widget": txt, "frame": row}

    del_btn = tk.Button(
        row,
        text="✕",
        fg="#dc2626",
        bd=0,
        padx=4,
        font=("Arial", 9),
        command=lambda: remove_bullet(item_data, bullet_data)
    )
    del_btn.pack(side="right", anchor="n")

    item_data["bullets"].append(bullet_data)
    update_scroll()

# Subheader item management (Field 1, Field 2, Field 3, Field 4 + Bullets)
def remove_item(sec_data, item_data):
    item_data["frame"].destroy()
    sec_data["entries"].remove(item_data)
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

    tk.Checkbutton(r1, variable=var).pack(side="left")

    tk.Label(r1, text="Field 1 (Title/Header):", font=("Arial", 9, "bold")).pack(side="left")
    e1 = tk.Entry(r1, font=("Arial", 10, "bold"))
    e1.insert(0, item_dict.get("field1", ""))
    e1.pack(side="left", fill="x", expand=True, padx=4)

    tk.Label(r1, text="Field 2 (Dates/Right):", font=("Arial", 9)).pack(side="left")
    e2 = tk.Entry(r1, width=22)
    e2.insert(0, item_dict.get("field2", ""))
    e2.pack(side="left", padx=4)

    item_data = {"var": var, "e1": e1, "e2": e2, "frame": card, "bullets": []}

    del_btn = tk.Button(
        r1,
        text="✕ Delete Item",
        fg="#dc2626",
        bd=0,
        font=("Arial", 9),
        command=lambda: remove_item(sec_data, item_data)
    )
    del_btn.pack(side="right")

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
    update_scroll()

def add_line_widget(sec_data, parent_container, line_dict=None):
    if line_dict is None:
        line_dict = {"enabled": True, "label": "", "text": ""}

    row = tk.Frame(parent_container, pady=2)
    row.pack(fill="x", expand=True, padx=4)

    var = tk.BooleanVar(value=line_dict.get("enabled", True))
    tk.Checkbutton(row, variable=var).pack(side="left")

    tk.Label(row, text="Title/Label:", font=("Arial", 9, "bold")).pack(side="left")
    el = tk.Entry(row, width=18, font=("Arial", 10, "bold"))
    el.insert(0, line_dict.get("label", ""))
    el.pack(side="left", padx=4)

    tk.Label(row, text="Content List:", font=("Arial", 9)).pack(side="left")
    et = tk.Entry(row, font=("Arial", 10))
    et.insert(0, line_dict.get("text", ""))
    et.pack(side="left", fill="x", expand=True, padx=4)

    line_data = {"var": var, "label_entry": el, "text_entry": et, "frame": row}

    del_btn = tk.Button(
        row,
        text="✕",
        fg="#dc2626",
        bd=0,
        font=("Arial", 9),
        command=lambda: remove_line(sec_data, line_data)
    )
    del_btn.pack(side="right")

    sec_data["simple_lines"].append(line_data)
    update_scroll()

# Section management
def remove_section(sec_data):
    if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete section '{sec_data['title_entry'].get()}'?"):
        sec_data["frame"].destroy()
        sections_widgets.remove(sec_data)
        update_scroll()

def add_section_widget(sec_dict=None):
    if sec_dict is None:
        sec_dict = {"title": "New Section", "enabled": True, "entries": [], "simple_lines": []}

    card = tk.LabelFrame(
        scrollable_frame,
        text="",
        padx=12,
        pady=10,
        bd=2,
        relief="groove",
        bg="#ffffff"
    )
    card.pack(fill="x", expand=True, pady=8, padx=10)

    # Top Bar of Section
    top = tk.Frame(card, bg="#ffffff")
    top.pack(fill="x", expand=True, pady=(0, 6))

    var = tk.BooleanVar(value=sec_dict.get("enabled", True))
    cb = tk.Checkbutton(top, variable=var, bg="#ffffff")
    cb.pack(side="left")

    tk.Label(top, text="Section Name:", font=("Arial", 10, "bold"), bg="#ffffff").pack(side="left")
    title_entry = tk.Entry(top, font=("Arial", 12, "bold"), width=24)
    title_entry.insert(0, sec_dict.get("title", "New Section"))
    title_entry.pack(side="left", padx=6)

    sec_data = {
        "var": var,
        "title_entry": title_entry,
        "frame": card,
        "entries": [],
        "simple_lines": []
    }

    del_btn = tk.Button(
        top,
        text="✕ Delete Section",
        fg="#dc2626",
        bd=0,
        font=("Arial", 9),
        bg="#ffffff",
        command=lambda: remove_section(sec_data)
    )
    del_btn.pack(side="right")

    # Subheaders container
    entries_container = tk.Frame(card, bg="#ffffff")
    entries_container.pack(fill="x", expand=True)

    # Simple lines container
    lines_container = tk.Frame(card, bg="#ffffff")
    lines_container.pack(fill="x", expand=True)

    for item in sec_dict.get("entries", []):
        add_item_widget(sec_data, entries_container, item)

    for line in sec_dict.get("simple_lines", []):
        add_line_widget(sec_data, lines_container, line)

    # Action bar for this section
    sec_actions = tk.Frame(card, pady=6, bg="#ffffff")
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

    sections_widgets.append(sec_data)
    update_scroll()

# Build initial sections in UI
for sec in master_data.get("sections", []):
    add_section_widget(sec)

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

    # 3. Configure Jinja for LaTeX
    env = Environment(
        loader=FileSystemLoader('.'),
        block_start_string=r'\BLOCK{',
        block_end_string='}',
        variable_start_string=r'\VAR{',
        variable_end_string='}',
        comment_start_string=r'\COMMENT{',
        comment_end_string='}',
        trim_blocks=True,
        autoescape=False
    )

    try:
        template = env.get_template("jakes-resume-tmpl.tex")
        rendered_tex = template.render(final_data)

        with open("output.tex", "w", encoding="utf-8") as f:
            f.write(rendered_tex)

        # Trigger LaTeX compiler
        exit_code = os.system("pdflatex output.tex")
        if exit_code == 0:
            messagebox.showinfo("Success", "Resume compiled successfully to output.pdf!\n(master.yaml also updated)")
        else:
            if os.system("which pdflatex > /dev/null 2>&1") != 0:
                messagebox.showwarning(
                    "LaTeX Output Saved",
                    "output.tex was created successfully with your selected sections!\n\n"
                    "Note: 'pdflatex' was not found on your system.\n"
                    "To generate PDFs directly, install BasicTeX with:\n"
                    "brew install --cask basictex"
                )
            else:
                messagebox.showerror("Compilation Error", "LaTeX compilation failed. Check output.log for details.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate resume:\n{e}")

# Function to add new custom section
def prompt_new_section():
    title = simpledialog.askstring("Add Section", "Enter the title for the new section:")
    if title and title.strip():
        add_section_widget({"title": title.strip(), "enabled": True, "entries": [], "simple_lines": []})

# Add toolbar buttons to top
tk.Button(
    top_toolbar,
    text="+ Add New Section",
    font=("Arial", 10, "bold"),
    bg="#10b981",
    fg="#047857",
    padx=10,
    pady=3,
    command=prompt_new_section
).pack(side="left", padx=(0, 10))

tk.Button(
    top_toolbar,
    text="💾 Save to master.yaml",
    font=("Arial", 10, "bold"),
    padx=10,
    pady=3,
    command=lambda: save_master_yaml(show_popup=True)
).pack(side="left", padx=(0, 10))

tk.Button(
    top_toolbar,
    text="📄 Generate Resume PDF",
    font=("Arial", 10, "bold"),
    bg="#2563eb",
    fg="#1d4ed8",
    padx=12,
    pady=3,
    command=generate_pdf
).pack(side="right")

# Bottom Action Toolbar
action_frame = tk.Frame(root, pady=10, bg="#f1f5f9")
action_frame.pack(fill="x", side="bottom")

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