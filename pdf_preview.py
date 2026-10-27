"""In-app live PDF preview pane & window for ResUme.

Renders compiled LaTeX PDFs using pypdfium2 and Pillow directly onto a dark-mode,
zoomable Tkinter Canvas with smooth trackpad scrolling.
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


class PDFPreviewPane(tk.Frame):
    """Embedded live PDF preview pane with zoom and fit-to-width."""

    def __init__(self, parent, pdf_path=None, tex_path=None):
        super().__init__(parent, bg=BG_APP)
        self.parent = parent
        self.pdf_path = pdf_path
        self.tex_path = tex_path

        self.scale = 1.0
        self.current_page = 0
        self.total_pages = 1
        self.doc = None
        self._photo_images = []
        self._page_records = []
        self._photo_image = None
        self._canvas_img_id = None
        self._shadow_id = None
        self._max_doc_width = 600
        self._total_doc_height = 800

        self._build_ui()
        self._bind_events()
        if self.pdf_path:
            self.load_pdf(self.pdf_path)

    def _build_ui(self):
        # 1. Top Control Toolbar
        self.toolbar = tk.Frame(self, bg=BG_BAR, padx=10, pady=7)
        self.toolbar.pack(side="top", fill="x")
        tk.Frame(self, bg=BORDER_BAR, height=1).pack(side="top", fill="x")

        # Left controls: status indicator
        left_box = tk.Frame(self.toolbar, bg=BG_BAR)
        left_box.pack(side="left")

        self.status_lbl = tk.Label(
            left_box, text="Ready", font=F_LABEL, bg=BG_BAR, fg=FG_MUTED
        )
        self.status_lbl.pack(side="left", padx=2)

        # Right controls: Page navigation, Zoom, Fit
        right_box = tk.Frame(self.toolbar, bg=BG_BAR)
        right_box.pack(side="right")

        # Page navigation (shown when document has multiple pages)
        self.page_frame = tk.Frame(right_box, bg=BG_BAR)
        self.page_prev_btn = PillButton(
            self.page_frame, "‹", self.prev_page,
            parent_bg=BG_BAR, bg=BG_ITEM, fg=FG, border=BORDER_ITEM,
            font=F_BTN_B, padx=7, pady=4, radius=6
        )
        self.page_prev_btn.pack(side="left", padx=1)

        self.page_lbl = tk.Label(
            self.page_frame, text="1 / 1", font=F_LABEL, bg=BG_BAR, fg=FG_MUTED
        )
        self.page_lbl.pack(side="left", padx=3)

        self.page_next_btn = PillButton(
            self.page_frame, "›", self.next_page,
            parent_bg=BG_BAR, bg=BG_ITEM, fg=FG, border=BORDER_ITEM,
            font=F_BTN_B, padx=7, pady=4, radius=6
        )
        self.page_next_btn.pack(side="left", padx=1)

        self.zoom_minus_btn = PillButton(
            right_box, "−", lambda: self.zoom_step(-0.15),
            parent_bg=BG_BAR, bg=BG_ITEM, fg=FG, border=BORDER_ITEM,
            font=F_BTN_B, padx=7, pady=4, radius=6
        )
        self.zoom_minus_btn.pack(side="left", padx=2)

        self.zoom_lbl = tk.Label(
            right_box, text="100%", width=5, font=F_LABEL, bg=BG_BAR, fg=FG
        )
        self.zoom_lbl.pack(side="left", padx=2)

        self.zoom_plus_btn = PillButton(
            right_box, "+", lambda: self.zoom_step(0.15),
            parent_bg=BG_BAR, bg=BG_ITEM, fg=FG, border=BORDER_ITEM,
            font=F_BTN_B, padx=7, pady=4, radius=6
        )
        self.zoom_plus_btn.pack(side="left", padx=2)

        self.fit_width_btn = PillButton(
            right_box, "Fit Width", self.zoom_fit_width,
            parent_bg=BG_BAR, bg=BG_ITEM, fg=FG_MUTED, border=BORDER_ITEM,
            font=F_LABEL, padx=8, pady=4, radius=6
        )
        self.fit_width_btn.pack(side="left", padx=(4, 2))

        self.fit_page_btn = PillButton(
            right_box, "Fit Page", self.zoom_fit_page,
            parent_bg=BG_BAR, bg=BG_ITEM, fg=FG_MUTED, border=BORDER_ITEM,
            font=F_LABEL, padx=8, pady=4, radius=6
        )
        self.fit_page_btn.pack(side="left", padx=2)

        # 2. Main Scrollable Canvas for rendering PDF page
        self.canvas_frame = tk.Frame(self, bg=BG_APP)
        self.canvas_frame.pack(side="top", fill="both", expand=True)

        self.canvas = tk.Canvas(
            self.canvas_frame, bg=BG_APP, borderwidth=0, highlightthickness=0,
            yscrollincrement=1, xscrollincrement=1
        )
        self.v_scrollbar = ttk.Scrollbar(
            self.canvas_frame, orient="vertical", command=self._on_vscroll,
            style="Dark.Vertical.TScrollbar"
        )
        self.h_scrollbar = ttk.Scrollbar(
            self.canvas_frame, orient="horizontal", command=self.canvas.xview
        )

        self.canvas.configure(
            yscrollcommand=self._on_canvas_y_scroll,
            xscrollcommand=self.h_scrollbar.set
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        self.v_scrollbar.pack(side="right", fill="y")

    def _on_vscroll(self, *args):
        self.canvas.yview(*args)

    def _on_canvas_y_scroll(self, first, last):
        self.v_scrollbar.set(first, last)
        try:
            self._update_visible_page_from_scroll(float(first))
        except Exception:
            pass

    def _update_visible_page_from_scroll(self, frac):
        if self.total_pages <= 1 or not self._page_records or not getattr(self, "_total_doc_height", 0):
            return
        top_y = frac * self._total_doc_height
        for rec in self._page_records:
            if rec["y_top"] <= top_y + 80 <= rec["y_bottom"]:
                if self.current_page != rec["page_idx"]:
                    self.current_page = rec["page_idx"]
                    self.page_lbl.configure(text=f"{self.current_page + 1} / {self.total_pages}")
                return
        if top_y < self._page_records[0]["y_top"]:
            self.current_page = 0
            self.page_lbl.configure(text=f"1 / {self.total_pages}")
        elif top_y > self._page_records[-1]["y_top"]:
            self.current_page = self.total_pages - 1
            self.page_lbl.configure(text=f"{self.total_pages} / {self.total_pages}")

    def _bind_events(self):
        self.canvas.bind("<Configure>", self._on_canvas_configure)

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
            high = (event.delta >> 16) & 0xFFFF
            dx = high if high < 0x8000 else high - 0x10000
            if dy != 0:
                self.canvas.yview_scroll(-dy, "units")
            if dx != 0:
                self.canvas.xview_scroll(-dx, "units")
            return "break"

        self.canvas.bind("<MouseWheel>", _on_wheel)
        try:
            self.canvas.bind("<TouchpadScroll>", _on_touchpad)
        except tk.TclError:
            pass

    def _on_canvas_configure(self, event):
        if not self._page_records:
            return
        c_width = max(event.width, getattr(self, "_max_doc_width", 500) + 40)
        total_h = getattr(self, "_total_doc_height", 800)
        for rec in self._page_records:
            w = rec["w"]
            h = rec["h"]
            x_pos = max(20, (c_width - w) // 2)
            y_top = rec["y_top"]
            self.canvas.coords(rec["img_id"], x_pos, y_top)
            if rec.get("shadow_id"):
                self.canvas.coords(
                    rec["shadow_id"],
                    x_pos + 4, y_top + 4, x_pos + w + 4, y_top + h + 4
                )
            if rec.get("badge_id"):
                self.canvas.coords(
                    rec["badge_id"],
                    x_pos + w, y_top - 6
                )
        self.canvas.configure(
            scrollregion=(0, 0, c_width, total_h)
        )

    def load_pdf(self, pdf_path=None, preserve_view=None):
        if pdf_path:
            self.pdf_path = pdf_path

        if not self.pdf_path or not os.path.exists(self.pdf_path):
            self.show_message("Preview ready.\n\nChanges automatically compile to PDF.")
            return

        # Automatically preserve zoom and scroll position if a document was already loaded
        if preserve_view is None:
            preserve_view = (self.doc is not None)

        prev_scale = self.scale
        try:
            prev_xview = self.canvas.xview()[0] if self.canvas else 0.0
            prev_yview = self.canvas.yview()[0] if self.canvas else 0.0
        except Exception:
            prev_xview, prev_yview = 0.0, 0.0

        try:
            if self.doc:
                try:
                    self.doc.close()
                except Exception:
                    pass
                self.doc = None
            self.doc = pdfium.PdfDocument(self.pdf_path)
            self.total_pages = len(self.doc)
            self.current_page = max(0, min(self.current_page, self.total_pages - 1))
            self.status_lbl.configure(
                text=f"Updated {datetime.now().strftime('%H:%M:%S')} ({self.total_pages} page{'s' if self.total_pages > 1 else ''})"
            )

            if preserve_view:
                self.scale = prev_scale
                self.render_pages(preserve_scroll=True, target_xview=prev_xview, target_yview=prev_yview)
            else:
                self.zoom_fit_width()
        except Exception as e:
            self.show_message(f"Failed to read PDF:\n{e}")

    def render_pages(self, preserve_scroll=False, target_xview=None, target_yview=None):
        if not self.doc or self.total_pages == 0:
            return

        if preserve_scroll:
            if target_xview is None:
                try:
                    target_xview = self.canvas.xview()[0]
                except Exception:
                    target_xview = 0.0
            if target_yview is None:
                try:
                    target_yview = self.canvas.yview()[0]
                except Exception:
                    target_yview = 0.0

        try:
            self.canvas.delete("all")
            self._photo_images.clear()
            self._page_records.clear()

            PAGE_GAP = 24
            y_pos = 20
            render_scale = max(0.4, min(self.scale * 1.8, 4.0))

            canvas_w = self.canvas.winfo_width()
            if canvas_w <= 100:
                canvas_w = self.winfo_width() or 600

            max_w = 0
            rendered_data = []
            for i in range(self.total_pages):
                page = self.doc[i]
                bitmap = page.render(scale=render_scale)
                pil_image = bitmap.to_pil()

                display_w = int(pil_image.width / (render_scale / self.scale))
                display_h = int(pil_image.height / (render_scale / self.scale))
                resized = pil_image.resize((display_w, display_h), Image.Resampling.LANCZOS)
                photo_img = ImageTk.PhotoImage(resized)
                self._photo_images.append(photo_img)

                if display_w > max_w:
                    max_w = display_w

                rendered_data.append({
                    "page_idx": i,
                    "photo_img": photo_img,
                    "w": display_w,
                    "h": display_h,
                })

            c_width = max(canvas_w, max_w + 40)

            for item in rendered_data:
                i = item["page_idx"]
                photo_img = item["photo_img"]
                w = item["w"]
                h = item["h"]

                x_pos = max(20, (c_width - w) // 2)
                y_top = y_pos

                # Drop shadow
                shadow_id = self.canvas.create_rectangle(
                    x_pos + 4, y_pos + 4, x_pos + w + 4, y_pos + h + 4,
                    fill="#050506", outline=""
                )
                # Rendered page image
                img_id = self.canvas.create_image(
                    x_pos, y_pos, anchor="nw", image=photo_img
                )

                badge_id = None
                if self.total_pages > 1:
                    badge_id = self.canvas.create_text(
                        x_pos + w, y_top - 6,
                        text=f"Page {i + 1} of {self.total_pages}",
                        fill=FG_MUTED, font=F_TAG, anchor="se"
                    )

                self._page_records.append({
                    "page_idx": i,
                    "img_id": img_id,
                    "shadow_id": shadow_id,
                    "badge_id": badge_id,
                    "w": w,
                    "h": h,
                    "y_top": y_top,
                    "y_bottom": y_pos + h,
                })

                y_pos += h + PAGE_GAP

            total_h = y_pos - PAGE_GAP + 20
            self._total_doc_height = total_h
            self._max_doc_width = max_w

            if self._photo_images:
                self._photo_image = self._photo_images[0]
            if self._page_records:
                self._canvas_img_id = self._page_records[0]["img_id"]
                self._shadow_id = self._page_records[0]["shadow_id"]

            self.canvas.configure(
                scrollregion=(0, 0, max(c_width, max_w + 40), total_h)
            )
            self.zoom_lbl.configure(text=f"{int(self.scale * 100)}%")
            self._update_page_controls()

            if preserve_scroll:
                if target_yview is not None:
                    self.canvas.yview_moveto(target_yview)
                if target_xview is not None:
                    self.canvas.xview_moveto(target_xview)
            else:
                self.canvas.yview_moveto(0.0)

        except Exception as e:
            self.show_message(f"Error rendering PDF:\n{e}")

    render_current_page = render_pages

    def _update_page_controls(self):
        if self.total_pages > 1:
            if not self.page_frame.winfo_ismapped():
                self.page_frame.pack(side="left", padx=(0, 6), before=self.zoom_minus_btn)
            self.page_lbl.configure(text=f"{self.current_page + 1} / {self.total_pages}")
        else:
            self.page_frame.pack_forget()

    def jump_to_page(self, page_num):
        if not self._page_records or not getattr(self, "_total_doc_height", 0):
            return
        idx = max(0, min(page_num, len(self._page_records) - 1))
        self.current_page = idx
        rec = self._page_records[idx]
        frac = max(0.0, min(1.0, rec["y_top"] / max(1, self._total_doc_height)))
        self.canvas.yview_moveto(frac)
        self.page_lbl.configure(text=f"{self.current_page + 1} / {self.total_pages}")

    def prev_page(self):
        self.jump_to_page(self.current_page - 1)

    def next_page(self):
        self.jump_to_page(self.current_page + 1)

    def zoom_step(self, delta):
        self.scale = max(0.4, min(self.scale + delta, 3.0))
        self.render_pages(preserve_scroll=True)

    def zoom_fit_width(self):
        if not self.doc or self.total_pages == 0:
            return
        self.update_idletasks()
        c_w = self.canvas.winfo_width()
        if c_w <= 100:
            c_w = self.winfo_width() or 600
            if c_w <= 100:
                c_w = 600
        max_page_w = 612
        try:
            for p_idx in range(self.total_pages):
                pw, _ = self.doc[p_idx].get_size()
                if pw > max_page_w:
                    max_page_w = pw
        except Exception:
            max_page_w = 612
        self.scale = max(0.4, min(3.0, (c_w - 50) / max_page_w))
        self.render_pages(preserve_scroll=True)

    def zoom_fit_page(self):
        if not self.doc or self.total_pages == 0:
            return
        self.update_idletasks()
        c_w = self.canvas.winfo_width() or 600
        c_h = self.canvas.winfo_height() or 800
        try:
            page_w, page_h = self.doc[0].get_size()
        except Exception:
            page_w, page_h = 612, 792
        scale_w = (c_w - 50) / page_w
        scale_h = (c_h - 50) / page_h
        self.scale = max(0.4, min(scale_w, scale_h))
        self.render_pages(preserve_scroll=True)

    def show_message(self, msg):
        self.canvas.delete("all")
        self.update_idletasks()
        cw = max(self.canvas.winfo_width() // 2, 220)
        ch = max(self.canvas.winfo_height() // 2, 160)
        self.canvas.create_text(
            cw, ch, text=msg, fill=FG_MUTED, font=F_BODY,
            justify="center", width=max(220, cw * 2 - 80)
        )

    def open_in_preview_app(self):
        if self.pdf_path and os.path.exists(self.pdf_path):
            subprocess.run(["open", "-a", "Preview", self.pdf_path])
        else:
            messagebox.showinfo("Preview", "PDF not generated yet.", parent=self.winfo_toplevel())


class PDFPreviewWindow(tk.Toplevel):
    """Floating PDF Preview window (backward-compatible wrapper around PDFPreviewPane)."""

    def __init__(self, parent, pdf_path, tex_path):
        super().__init__(parent)
        self.parent = parent
        self.title("ResUme - Live PDF Preview")
        self.geometry("780x900")
        self.minsize(500, 500)
        self.configure(bg=BG_APP)

        self.pane = PDFPreviewPane(
            self, pdf_path=pdf_path, tex_path=tex_path
        )
        self.pane.pack(fill="both", expand=True)

    def load_pdf(self, pdf_path=None):
        self.pane.load_pdf(pdf_path)
