# ResUme

A local desktop editor for a one-page LaTeX resume. You write your experience and projects in your own words, then check the pieces that belong on the page for a given application. ResUme stores that content in YAML, fills [Jake's Resume](https://github.com/jakegut/resume), and compiles a PDF in a pane next to the form.

The name is resume, with the **U** capitalized: the page is yours to customize, and the wording is yours.

## Why it exists

As a student applying to a lot of different roles, tailoring a resume for each one became nearly impossible. Keeping a separate copy for every posting is hard to track, and AI rewrites often invent experience or add buzzwords that are not accurate. I wanted one resume I could change easily: write the experience and projects in my own words, then select only the pieces that fit the application in front of me.

I use it for my own applications. Clone the repo and you can do the same. Jake's Resume is the layout because automated resume parsers read it reliably.

Edits autosave. The preview recompiles in the background, so the page updates as you work. Nothing is uploaded. Your resume text stays in `master.yaml` on this machine, and that file is gitignored. A fresh clone opens `example.yaml`, a sample resume under the name Anthony Fuca, and writes `master.yaml` the first time you change something.

## What you can do

- Edit a header (name, phone numbers, emails, and other links) and any number of sections.
- Use three entry shapes:
  - **Dual-line** for education and experience: organization and dates on the first line, role and location on the second, then bullets.
  - **Single-line** for projects: title, subtitle (often a tech stack), date, then bullets.
  - **Single line** for skill rows: a label plus comma-separated items you can reorder one by one.
- Include or exclude a section, entry, bullet, or link without deleting it. Excluded content stays in `master.yaml` and is left out of the PDF, so one master list can produce a different page per application.
- Reorder sections, entries, bullets, skill items, and links.
- Pick a font family (Computer Modern, Charter, Cormorant Garamond, Fira Sans, Roboto, Noto Sans, Source Sans Pro) and a size from 8pt to 14pt.
- Watch a zoomable, multi-page PDF preview with fit-to-width and fit-to-page.
- Download a PDF into `~/Downloads` as `Name's_Resume.pdf`. If that name already exists, the next file is `Name's_Resume_(1).pdf`, then `_(2)`, and so on.

The template enables `pdfgentounicode`, so the PDF text stays selectable and readable by applicant-tracking systems when compiled with pdfTeX. Tectonic (XeTeX) is Unicode-native.

## Requirements

ResUme is built for macOS. The window uses Tk on Aqua, including trackpad scrolling, and the compiler lookup checks common Homebrew and MacTeX paths.

- Python 3 with Tkinter (the python.org and Homebrew builds on macOS include it)
- A LaTeX engine, either:
  - [Tectonic](https://tectonic-typesetting.github.io/) (preferred; it fetches missing packages), or
  - `pdflatex` from [BasicTeX](https://www.tug.org/mactex/morepackages.html) or MacTeX

## Setup

```bash
cd ResUme
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install tectonic
python app.py
```

If you launch `app.py` with a Python that does not have PyYAML, and `.venv` already exists, the script restarts itself with `.venv/bin/python3`.

BasicTeX is the other compiler option:

```bash
brew install --cask basictex
```

Open a new terminal after installing BasicTeX so `/Library/TeX/texbin` is on your `PATH`. The app also checks that path directly.

Non-default fonts (Charter, Fira Sans, and the others) come from LaTeX packages. Tectonic downloads them on first compile. With BasicTeX you install the matching packages yourself (`tlmgr`) the first time a font fails to compile.

## Daily use

The window is split: the editor is on the left, the PDF is on the right.

1. The first launch shows the sample from `example.yaml`, with the name Anthony Fuca. Closing the window without changing anything leaves `master.yaml` uncreated.
2. Type in a field, reorder an entry, or toggle something on or off. After a short pause, or when the field loses focus, ResUme creates `master.yaml` and recompiles. Later edits update that file.
3. Use **+ New Section** for a section with your own title, then add dual-line entries, single-line entries, or skill lines inside it.
4. Uncheck anything that does not belong on this application. It stays in the master file and is omitted from the PDF.
5. **Download PDF** copies the compiled file into `~/Downloads` and leaves the working copy in `~/.resume_build`.
6. Press **⌘R** or **F5** to compile again immediately.

The status line on the preview shows `Compiling...` and then the time of the last successful render. If no LaTeX engine is installed, a dialog prints the `brew install` commands. Generated `.tex` still lands in `~/.resume_build` so you can compile it later.

## Where files live

| Path | What it is |
| --- | --- |
| `example.yaml` | Sample resume, named Anthony Fuca. Committed. The window shows this until you edit. |
| `master.yaml` | Your resume. Created on the first edit. Gitignored. |
| `jakes-resume-tmpl.tex` | Jinja2 template. Editing it recompiles the preview. |
| `~/.resume_build/` | Rendered `.tex` and the working PDF, named from your header (`Ada_Lovelace's_Resume.pdf`). |
| `~/Downloads/` | PDFs written by **Download PDF**. |

Once it exists, `master.yaml` is the source of truth. Build artifacts and downloads are derived from it. `example.yaml` is only the starting sample.

## Content shape

```yaml
name: Ada Lovelace
font_family: Charter
font_size: 10pt
links:
  - enabled: true
    label: ada@example.com
    url: mailto:ada@example.com
    type: email
sections:
  - title: Experience
    enabled: true
    entries:
      - enabled: true
        field1: Analytical Engines
        field2: 1843
        field3: Notes on the engine
        field4: London
        bullets:
          - enabled: true
            text: Wrote the first published algorithm.
    simple_lines: []
  - title: Technical Skills
    enabled: true
    entries: []
    simple_lines:
      - enabled: true
        label: Languages
        text: Mathematics, Music
```

Dual-line entries use `field1`–`field4`. Single-line entries use `type: single-line` with `title`, `subtitle`, and `date`. Skill rows use `simple_lines`. Bare emails and domains in link URLs are turned into `mailto:` and `https://` links at compile time. Characters that are special in LaTeX (`% & $ # _ ~`) are escaped when the template is rendered.

## How it is put together

```
app.py          editor, autosave, Jinja render, compile
ui_widgets.py   dark cards, buttons, and inputs (pure Tkinter)
pdf_preview.py  PDF pane (pypdfium2 + Pillow)
jakes-resume-tmpl.tex
```

Python dependencies are PyYAML, Jinja2, pypdfium2, and Pillow. Tkinter comes with Python.

Jinja delimiters in the template are `\BLOCK{ }`, `\VAR{ }`, and `\COMMENT{ }` so they can sit inside LaTeX without colliding with `{ }` groups. Compilation prefers `tectonic`; otherwise it uses `pdflatex -interaction=nonstopmode`. Compile work runs on a background thread. If you edit again while a compile is in flight, one more compile is queued so the preview settles on the latest text.

## Template credit

`jakes-resume-tmpl.tex` is Jake Gutierrez's resume, based on [sb2nov/resume](https://github.com/sb2nov/resume). That template is MIT licensed. See the header comment in the `.tex` file.
