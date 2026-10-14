"""In-app live PDF preview window for ResUme.

Renders compiled LaTeX PDFs using pypdfium2 and Pillow directly onto a dark-mode,
zoomable Tkinter Canvas with smooth trackpad scrolling and live recompile controls.
"""
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import pypdfium2 as pdfium
from PIL import Image, ImageTk

from ui_widgets import (
    BG_APP, BG_BAR, BG_SECTION, BG_ITEM, BG_INPUT,
    BORDER_BAR, BORDER_SECTION, BORDER_ITEM, BORDER_INPUT,
    FG, FG_MUTED, FG_DIM, DANGER,
    UI_FONT, F_BODY, F_BODY_B, F_BTN, F_BTN_B, F_LABEL, F_TAG, F_ICON,
    PillButton, RoundedCard
)

class PDFPreviewWindow(tk.Toplevel):
    """Floating PDF Preview window with zoom, fit-to-width, and live recompile."""

    def __init__(self, parent, pdf_path, tex_path, recompile_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.pdf_path = pdf_path
        self.tex_path = tex_path
        self.recompile_callback = recompile_callback

        self.title("ResUme - Live PDF Preview")
        self.geometry("780x900")
        self.minsize(500, 500)
        self.configure(bg=BG_APP)

        # Center or position adjacent to parent
        self._position_window()

        self.scale = 1.0
        self.current_page = 0
        self.total_pages = 1
        self.doc = None
        self._photo_image = None
        self._canvas_img_id = None

        self._build_ui()
        self._bind_events()
        self.load_pdf(self.pdf_path)

    def _position_window(self):
        try:
            self.parent.update_idletasks()
            px = self.parent.winfo_x()
            py = self.parent.winfo_y()
            pw = self.parent.winfo_width()
            # Position to the right of main window if screen space permits
            screen_w = self.winfo_screenwidth()
            if px + pw + 800 <= screen_w:
                x = px + pw + 10
            else:
                x = max(20, px + 40)
            y = max(30, py + 10)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self):
        # 1. Top Control Toolbar
        self.toolbar = tk.Frame(self, bg=BG_BAR, padx=14, pady=8)
        self.toolbar.pack(side="top", fill="x")
        tk.Frame(self, bg=BORDER_BAR, height=1).pack(side="top", fill="x")

        # Left controls: Recompile and status
        left_box = tk.Frame(self.toolbar, bg=BG_BAR)
        left_box.pack(side="left")

        PillButton(
            left_box, "↻ Recompile", self.on_recompile,
            parent_bg=BG_BAR, bg=BG_ITEM, fg=FG, border=BORDER_ITEM,
            font=F_BTN_B, padx=12, pady=5, radius=8
        ).pack(side="left", padx=(0, 10))

        self.status_lbl = tk.Label(
            left_box, text="Ready", font=F_LABEL, bg=BG_BAR, fg=FG_MUTED
        )
        self.status_lbl.pack(side="left", padx=4)

        # Right controls: Zoom and Open in Preview
        right_box = tk.Frame(self.toolbar, bg=BG_BAR)
        right_box.pack(side="right")

        PillButton(
            right_box, "−", lambda: self.zoom_step(-0.15),
            parent_bg=BG_BAR, bg=BG_ITEM, fg=FG, border=BORDER_ITEM,
            font=F_BTN_B, padx=8, pady=5, radius=6
        ).pack(side="left", padx=2)

        self.zoom_lbl = tk.Label(
            right_box, text="100%", width=6, font=F_LABEL, bg=BG_BAR, fg=FG
        )
        self.zoom_lbl.pack(side="left", padx=2)

        PillButton(
            right_box, "+", lambda: self.zoom_step(0.15),
            parent_bg=BG_BAR, bg=BG_ITEM, fg=FG, border=BORDER_ITEM,
            font=F_BTN_B, padx=8, pady=5, radius=6
        ).pack(side="left", padx=2)

        PillButton(
            right_box, "Fit Width", self.zoom_fit_width,
            parent_bg=BG_BAR, bg=BG_ITEM, fg=FG_MUTED, border=BORDER_ITEM,
            font=F_LABEL, padx=10, pady=5, radius=6
        ).pack(side="left", padx=(6, 2))

        PillButton(
            right_box, "Fit Page", self.zoom_fit_page,
            parent_bg=BG_BAR, bg=BG_ITEM, fg=FG_MUTED, border=BORDER_ITEM,
            font=F_LABEL, padx=10, pady=5, radius=6
        ).pack(side="left", padx=2)

        PillButton(
            right_box, "↗ macOS Preview", self.open_in_preview_app,
            parent_bg=BG_BAR, bg=BG_ITEM, fg=FG_MUTED, border=BORDER_ITEM,
            font=F_LABEL, padx=10, pady=5, radius=6
        ).pack(side="left", padx=(8, 0))

        # 2. Main Scrollable Canvas for rendering PDF page
        self.canvas_frame = tk.Frame(self, bg=BG_APP)
        self.canvas_frame.pack(side="top", fill="both", expand=True)

        self.canvas = tk.Canvas(
            self.canvas_frame, bg=BG_APP, borderwidth=0, highlightthickness=0,
            yscrollincrement=1, xscrollincrement=1
        )
        self.v_scrollbar = ttk.Scrollbar(
            self.canvas_frame, orient="vertical", command=self.canvas.yview,
            style="Dark.Vertical.TScrollbar"
        )
        self.h_scrollbar = ttk.Scrollbar(
            self.canvas_frame, orient="horizontal", command=self.canvas.xview
        )

        self.canvas.configure(
            yscrollcommand=self.v_scrollbar.set,
            xscrollcommand=self.h_scrollbar.set
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        self.v_scrollbar.pack(side="right", fill="y")

    def _bind_events(self):
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Trackpad and mousewheel scrolling
        def _on_wheel(event):
            if sys.platform == "darwin":
                delta = event.delta
                units = -int((delta / 120) * 35) if abs(delta) >= 120 else -int(delta * 4)
                if units == 0 and delta != 0:
                    units = -4 if delta > 0 else 4
                self.canvas.yview_scroll(units, "units")
            else:
                self.canvas.yview_scroll(-1 * (event.delta // 120), "units")
            return "break"

        def _on_touchpad(event):
            low = event.delta & 0xFFFF
            dy = low if low < 0x8000 else low - 0x10000
            if dy != 0:
                self.canvas.yview_scroll(-dy, "units")
            return "break"

        self.canvas.bind("<MouseWheel>", _on_wheel)
        self.canvas.bind("<TouchpadScroll>", _on_touchpad)
        self.bind("<MouseWheel>", _on_wheel)
        self.bind("<TouchpadScroll>", _on_touchpad)

        # Keyboard shortcuts
        self.bind("<Command-plus>", lambda e: self.zoom_step(0.15))
        self.bind("<Command-equal>", lambda e: self.zoom_step(0.15))
        self.bind("<Command-minus>", lambda e: self.zoom_step(-0.15))
        self.bind("<Command-0>", lambda e: self.zoom_fit_width())
        self.bind("<Command-r>", lambda e: self.on_recompile())
        self.bind("<F5>", lambda e: self.on_recompile())

    def _on_canvas_configure(self, event):
        pass

    def load_pdf(self, pdf_path=None):
        if pdf_path:
            self.pdf_path = pdf_path

        if not self.pdf_path or not os.path.exists(self.pdf_path):
            self.show_message("PDF not found. Please compile your resume first.")
            return

        try:
            self.doc = pdfium.PdfDocument(self.pdf_path)
            self.total_pages = len(self.doc)
            self.current_page = 0
            self.status_lbl.configure(
                text=f"Updated {datetime.now().strftime('%H:%M:%S')} ({self.total_pages} page{'s' if self.total_pages > 1 else ''})"
            )
            # Default to fit-width on initial load
            self.zoom_fit_width()
        except Exception as e:
            self.show_message(f"Failed to read PDF:\n{e}")

    def render_current_page(self):
        if not self.doc or self.total_pages == 0:
            return

        try:
            page = self.doc[self.current_page]
            # Baseline PDF resolution is 72 dpi; scale relative to that
            render_scale = max(0.4, min(self.scale * 1.8, 4.0))
            bitmap = page.render(scale=render_scale)
            pil_image = bitmap.to_pil()

            # Display dimensions
            display_w = int(pil_image.width / (render_scale / self.scale))
            display_h = int(pil_image.height / (render_scale / self.scale))

            resized = pil_image.resize((display_w, display_h), Image.Resampling.LANCZOS)
            self._photo_image = ImageTk.PhotoImage(resized)

            # Center horizontally on canvas
            c_width = max(self.canvas.winfo_width(), display_w + 40)
            c_height = max(self.canvas.winfo_height(), display_h + 40)
            x_pos = max(20, (c_width - display_w) // 2)
            y_pos = 20

            self.canvas.delete("all")
            # Drop shadow
            self.canvas.create_rectangle(
                x_pos + 4, y_pos + 4, x_pos + display_w + 4, y_pos + display_h + 4,
                fill="#050506", outline=""
            )
            # Rendered page image
            self._canvas_img_id = self.canvas.create_image(
                x_pos, y_pos, anchor="nw", image=self._photo_image
            )

            # Update scroll region
            self.canvas.configure(
                scrollregion=(0, 0, x_pos + display_w + 40, y_pos + display_h + 40)
            )
            self.zoom_lbl.configure(text=f"{int(self.scale * 100)}%")
        except Exception as e:
            self.show_message(f"Error rendering PDF:\n{e}")

    def zoom_step(self, delta):
        self.scale = max(0.4, min(self.scale + delta, 3.0))
        self.render_current_page()

    def zoom_fit_width(self):
        if not self.doc:
            return
        self.update_idletasks()
        c_w = self.canvas.winfo_width()
        if c_w <= 100:
            c_w = 720
        # Typical 8.5 x 11 inch page has width 612 pts
        try:
            page_w, _ = self.doc[self.current_page].get_size()
        except Exception:
            page_w = 612
        self.scale = max(0.5, (c_w - 60) / page_w)
        self.render_current_page()

    def zoom_fit_page(self):
        if not self.doc:
            return
        self.update_idletasks()
        c_w = self.canvas.winfo_width() or 720
        c_h = self.canvas.winfo_height() or 800
        try:
            page_w, page_h = self.doc[self.current_page].get_size()
        except Exception:
            page_w, page_h = 612, 792
        scale_w = (c_w - 60) / page_w
        scale_h = (c_h - 60) / page_h
        self.scale = max(0.4, min(scale_w, scale_h))
        self.render_current_page()

    def show_message(self, msg):
        self.canvas.delete("all")
        self.canvas.create_text(
            350, 200, text=msg, fill=FG_MUTED, font=F_BODY,
            justify="center", width=500
        )

    def on_recompile(self):
        if self.recompile_callback:
            self.status_lbl.configure(text="Compiling...")
            self.update_idletasks()
            success, err_msg = self.recompile_callback()
            if success:
                self.load_pdf()
            else:
                self.status_lbl.configure(text="Compile failed")
                if err_msg:
                    messagebox.showerror("LaTeX Compilation Error", err_msg, parent=self)
        else:
            self.load_pdf()

    def open_in_preview_app(self):
        if self.pdf_path and os.path.exists(self.pdf_path):
            subprocess.run(["open", "-a", "Preview", self.pdf_path])
        else:
            messagebox.showinfo("Preview", "PDF not generated yet.", parent=self)
