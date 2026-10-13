import tkinter as tk
from tkinter import messagebox
import yaml
import os
from jinja2 import Environment, FileSystemLoader

# 1. Load the master YAML file
with open("master.yaml", "r", encoding="utf-8") as f:
    master_data = yaml.safe_load(f)

# 2. Setup the native desktop window
root = tk.Tk()
root.title("Local Resume Builder")
root.geometry("720x750")

# Header section
header_frame = tk.Frame(root, pady=10)
header_frame.pack(fill="x")

tk.Label(header_frame, text="Local Resume Builder", font=("Arial", 16, "bold")).pack()
tk.Label(
    header_frame,
    text="Check bullets to include in the PDF. Edit text directly in the boxes below.",
    font=("Arial", 10),
    fg="#555555"
).pack(pady=(4, 0))

# Scrollable canvas for job experiences & bullets
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

canvas_container.pack(fill="both", expand=True, padx=15, pady=5)
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Mouse wheel scrolling (works on macOS and other platforms)
def _on_mousewheel(event):
    if event.num == 5 or event.delta < 0:
        canvas.yview_scroll(1, "units")
    elif event.num == 4 or event.delta > 0:
        canvas.yview_scroll(-1, "units")

root.bind_all("<MouseWheel>", _on_mousewheel)

# Track UI state: list of { 'job': job_dict, 'bullets': [ { 'var': BooleanVar, 'text_widget': Text, 'row': Frame } ] }
job_bullet_widgets = []

def remove_bullet(item, bullet_entry):
    bullet_entry["row"].destroy()
    item["bullets"].remove(bullet_entry)
    scrollable_frame.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))

def add_bullet_row(item, bullets_container, text=""):
    row = tk.Frame(bullets_container)
    row.pack(fill="x", expand=True, pady=3, padx=(10, 5))

    var = tk.BooleanVar(value=True) # Checked by default for resume inclusion
    cb = tk.Checkbutton(row, variable=var)
    cb.pack(side="left", anchor="n", padx=(0, 4))

    txt = tk.Text(row, height=2, wrap="word", font=("Arial", 10), relief="solid", bd=1)
    txt.insert("1.0", text)
    txt.pack(side="left", fill="x", expand=True)

    bullet_entry = {"var": var, "text_widget": txt, "row": row}

    del_btn = tk.Button(
        row,
        text="✕",
        font=("Arial", 9),
        fg="#cc0000",
        bd=0,
        padx=4,
        command=lambda: remove_bullet(item, bullet_entry)
    )
    del_btn.pack(side="right", anchor="n", padx=(4, 0))

    item["bullets"].append(bullet_entry)
    scrollable_frame.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))

# 3. Dynamically generate editable bullet rows for each job
for job in master_data.get("experiences", []):
    job_section = tk.Frame(scrollable_frame, pady=8)
    job_section.pack(fill="x", expand=True, padx=10)

    title_text = f"{job.get('title', '')} at {job.get('company', '')}"
    tk.Label(job_section, text=title_text, font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 4))

    bullets_container = tk.Frame(job_section)
    bullets_container.pack(fill="x", expand=True)

    item = {"job": job, "bullets": []}

    for bullet in job.get("bullets", []):
        add_bullet_row(item, bullets_container, bullet)

    job_bullet_widgets.append(item)

    add_btn = tk.Button(
        job_section,
        text="+ Add Bullet",
        font=("Arial", 9),
        command=lambda it=item, bc=bullets_container: add_bullet_row(it, bc, "")
    )
    add_btn.pack(anchor="w", padx=30, pady=(2, 6))

# 4. Save to master.yaml logic
def save_master_yaml(show_popup=True):
    for item in job_bullet_widgets:
        job = item["job"]
        updated_bullets = []
        for b in item["bullets"]:
            content = b["text_widget"].get("1.0", "end-1c").strip()
            if content:
                updated_bullets.append(content)
        job["bullets"] = updated_bullets

    try:
        with open("master.yaml", "w", encoding="utf-8") as f:
            yaml.dump(master_data, f, sort_keys=False, allow_unicode=True)
        if show_popup:
            messagebox.showinfo("Saved", "All changes successfully saved to master.yaml!")
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save to master.yaml:\n{e}")
        return False

# 5. Compilation Logic
def generate_pdf():
    # Automatically sync edits into master_data and save to master.yaml
    if not save_master_yaml(show_popup=False):
        return

    # Extract only checked bullets for the compiled resume
    selected_experiences = []
    for item in job_bullet_widgets:
        job = item["job"]
        selected_bullets = []
        for b in item["bullets"]:
            content = b["text_widget"].get("1.0", "end-1c").strip()
            if b["var"].get() and content:
                selected_bullets.append(content)

        if selected_bullets:
            job_copy = job.copy()
            job_copy["bullets"] = selected_bullets
            selected_experiences.append(job_copy)

    final_data = master_data.copy()
    final_data["experiences"] = selected_experiences

    # Configure Jinja for LaTeX
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

        # Trigger the local LaTeX compiler
        exit_code = os.system("pdflatex output.tex")
        if exit_code == 0:
            messagebox.showinfo("Success", "PDF compiled successfully as output.pdf!\n(master.yaml also updated)")
        else:
            if os.system("which pdflatex > /dev/null 2>&1") != 0:
                messagebox.showwarning(
                    "LaTeX File Generated",
                    "output.tex was created and master.yaml was updated!\n\n"
                    "Note: 'pdflatex' was not found on your system.\n"
                    "To compile PDFs directly, install BasicTeX with:\n"
                    "brew install --cask basictex"
                )
            else:
                messagebox.showerror("Compilation Error", "LaTeX compilation failed. Check output.log for details.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate resume:\n{e}")

# 6. Bottom Action Toolbar
action_frame = tk.Frame(root, pady=12, bg="#f5f5f5")
action_frame.pack(fill="x", side="bottom")

save_btn = tk.Button(
    action_frame,
    text="💾 Save to master.yaml",
    command=lambda: save_master_yaml(show_popup=True),
    font=("Arial", 11, "bold"),
    padx=10,
    pady=4
)
save_btn.pack(side="left", padx=(20, 10))

gen_btn = tk.Button(
    action_frame,
    text="📄 Generate Resume PDF",
    command=generate_pdf,
    font=("Arial", 11, "bold"),
    padx=12,
    pady=4
)
gen_btn.pack(side="right", padx=(10, 20))

# Run the desktop application
if __name__ == "__main__":
    root.mainloop()