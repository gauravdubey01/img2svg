import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
import threading
import webbrowser
import os
import sys
from PIL import Image, ImageTk
from converter import render_preview_bitmap, save_svg, count_paths, TEMP_DIR

VERSION = "1.0.0"
KOFI_URL = "https://ko-fi.com/gauravdubeypro"

# Photo Editor & Filters palette (from UI-UX Pro Max skill)
BG = "#0F172A"
CARD = "#192134"
FG = "#FFFFFF"
MUTED = "#94A3B8"
PRIMARY = "#7C3AED"
SECONDARY = "#6366F1"
ACCENT = "#0891B2"
SUCCESS = "#22C55E"
DESTRUCTIVE_ = "#DC2626"
INP = "#171939"
BORDER = "#1E293B"
SUBTLE = "#0F172A80"
TUTORIAL_FLAG = os.path.join(os.path.expanduser("~"), ".img2svg_tutorial_done")

FONT = ("Segoe UI", 10)
FBOLD = ("Segoe UI", 10, "bold")
FTITLE = ("Segoe UI", 14, "bold")
FSMALL = ("Segoe UI", 9)


def _resource_path(rel):
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel)


def rr(c, x1, y1, x2, y2, r, **kw):
    pts = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2, x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class PillButton(tk.Canvas):
    _CM = None

    @classmethod
    def _cm(cls):
        if cls._CM is None:
            cls._CM = {
                "primary":   (PRIMARY,   "#ffffff"),
                "success":   (SUCCESS,   "#ffffff"),
                "secondary": (SECONDARY, "#ffffff"),
                "accent":    (ACCENT,    "#ffffff"),
                "muted":     (MUTED,     BG),
            }
        return cls._CM

    def __init__(self, parent, text, cmd=None, bootstyle="primary", w=120, h=40, **kw):
        super().__init__(parent, width=w, height=h, highlightthickness=0, **kw)
        bg, fg = self._cm().get(bootstyle, (PRIMARY, "#ffffff"))
        self.cmd = cmd
        self.text = text
        self.tw, self.th = w, h
        self.bg = bg
        self.fg = fg
        pb = parent["bg"] if isinstance(parent, tk.Widget) else BG
        self.configure(bg=pb, bd=0)
        self._draw()
        self.bind("<Button-1>", lambda e: self.cmd() if self.cmd else None)
        self.bind("<Enter>", lambda e: self._draw(True))
        self.bind("<Leave>", lambda e: self._draw())

    def _lighten(self, c, f=1.15):
        r = min(255, int(int(c[1:3], 16) * f))
        g = min(255, int(int(c[3:5], 16) * f))
        b = min(255, int(int(c[5:7], 16) * f))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _draw(self, hover=False):
        self.delete("all")
        c = self._lighten(self.bg) if hover else self.bg
        r = self.th // 2
        rr(self, 0, 0, self.tw, self.th, r, fill=c, outline=c)
        self.create_text(self.tw // 2, self.th // 2, text=self.text, fill=self.fg, font=FBOLD, anchor="center")


class PillRadio(tk.Canvas):
    def __init__(self, parent, text, variable, value, w=100, h=34, **kw):
        super().__init__(parent, width=w, height=h, highlightthickness=0, **kw)
        self.text = text
        self.variable = variable
        self.value = value
        self.tw, self.th = w, h
        pb = parent["bg"] if isinstance(parent, tk.Widget) else BG
        self._bg = pb
        self.configure(bg=pb, bd=0)
        self.bind("<Button-1>", lambda e: variable.set(value))
        variable.trace_add("write", lambda *_: self._draw())
        self._draw()

    def _draw(self):
        self.delete("all")
        sel = self.variable.get() == self.value
        r = self.th // 2
        if sel:
            rr(self, 0, 0, self.tw, self.th, r, fill=PRIMARY, outline=PRIMARY)
            self.create_text(self.tw // 2, self.th // 2, text=self.text, fill="#ffffff", font=FBOLD, anchor="center")
        else:
            rr(self, 0, 0, self.tw, self.th, r, fill=self._bg, outline=PRIMARY, width=2)
            self.create_text(self.tw // 2, self.th // 2, text=self.text, fill=MUTED, font=FONT, anchor="center")


class PillEntry(tk.Frame):
    def __init__(self, parent, textvariable=None, h=36, **kw):
        super().__init__(parent, height=h, **kw)
        self.h = h
        self.pack_propagate(False)
        self.cv = tk.Canvas(self, highlightthickness=0, bd=0, bg=CARD)
        self.cv.pack(fill=tk.BOTH, expand=True)
        self.entry = tk.Entry(self.cv, textvariable=textvariable, bg=INP, fg=FG,
                             insertbackground=FG, bd=0, relief="flat", font=FSMALL)
        self.bind("<Configure>", self._rd)
        self._rd()

    def _rd(self, e=None):
        w = self.winfo_width() or 200
        self.cv.delete("all")
        rr(self.cv, 0, 0, w, self.h, self.h // 2, fill=INP, outline=INP)
        rr(self.cv, 0, 0, w, self.h, self.h // 2, fill="", outline=BORDER, width=1)
        self.cv.create_window(w // 2, self.h // 2, window=self.entry, width=w - 24, height=self.h - 8)


class ToolTip:
    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._id = None
        self._tw = None
        widget.bind("<Enter>", self._start)
        widget.bind("<Leave>", self._hide)

    def _start(self, e=None):
        self._id = self.widget.after(self.delay, self._show)

    def _show(self):
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tw = tk.Toplevel(self.widget, bg=INP)
        self._tw.wm_overrideredirect(True)
        lbl = tk.Label(self._tw, text=self.text, font=FSMALL, fg=FG, bg=INP,
                       padx=12, pady=6)
        lbl.pack()
        self._tw.update_idletasks()
        self._tw.geometry(f"{lbl.winfo_reqwidth()}x{lbl.winfo_reqheight()}+{x}+{y}")

    def _hide(self, e=None):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        if self._tw:
            self._tw.destroy()
            self._tw = None


class TutorialOverlay:
    def __init__(self, root, steps, on_close):
        self.root = root
        self.steps = steps
        self.on_close = on_close
        self._idx = 0

        root.update_idletasks()
        rx = root.winfo_rootx()
        ry = root.winfo_rooty()
        rw = root.winfo_width()
        rh = root.winfo_height()

        self.win = tk.Toplevel(root, bg=BG, bd=0)
        self.win.overrideredirect(True)
        self.win.attributes("-alpha", 0.72)
        self.win.geometry(f"{rw}x{rh}+{rx}+{ry}")
        self.win.lift()

        self.cv = tk.Canvas(self.win, highlightthickness=0, bd=0, bg=CARD)
        self.cv.pack(fill=tk.BOTH, expand=True)
        self._render()

    def _region(self, w):
        ox = self.root.winfo_rootx()
        oy = self.root.winfo_rooty()
        return (w.winfo_rootx() - ox, w.winfo_rooty() - oy,
                w.winfo_rootx() - ox + w.winfo_width(), w.winfo_rooty() - oy + w.winfo_height())

    def _render(self):
        self.cv.delete("all")
        rw = self.win.winfo_width() or self.root.winfo_width()
        rh = self.win.winfo_height() or self.root.winfo_height()
        step = self.steps[self._idx]
        r = step.get("_region")
        if step.get("widget") and hasattr(step["widget"], "winfo_exists"):
            r = self._region(step["widget"])
        if r:
            self.cv.create_rectangle(r, outline=PRIMARY, width=4)

        card_w, card_h = 280, 150
        x1, y1, x2, y2 = r if r else (100, 100, 200, 200)
        cw = (x1 + x2) // 2 - card_w // 2
        ch = y2 + 20
        if ch + card_h > rh:
            ch = y1 - card_h - 20
        cw = max(8, min(cw, rw - card_w - 8))

        rr(self.cv, cw, ch, cw + card_w, ch + card_h, 12, fill=INP, outline=BORDER, width=1)
        self.cv.create_text(cw + 16, ch + 14, text=f"Step {self._idx + 1}/{len(self.steps)}",
                            font=FSMALL, fill=PRIMARY, anchor="w")
        self.cv.create_text(cw + 16, ch + 34, text=step["title"],
                            font=FBOLD, fill=FG, anchor="w")
        self.cv.create_text(cw + 16, ch + 58, text=step["desc"],
                            font=FSMALL, fill=MUTED, anchor="w", width=card_w - 32)

        n = len(self.steps)
        dot_y = ch + card_h - 22
        dot_start = cw + card_w // 2 - (n * 12) // 2
        for i in range(n):
            dc = PRIMARY if i == self._idx else MUTED
            self.cv.create_oval(dot_start + i * 14 - 3, dot_y - 3, dot_start + i * 14 + 3, dot_y + 3, fill=dc, outline=dc)

        btn_y = ch + card_h - 36
        if self._idx > 0:
            self.cv.create_text(cw + 16, btn_y, text="\u2190 Back", font=FBOLD, fill=ACCENT, anchor="w",
                                tags="back")
            self.cv.tag_bind("back", "<Button-1>", lambda e: self._go(-1))
            self.cv.tag_bind("back", "<Enter>", lambda e: self.cv.itemconfig("back", fill=PRIMARY))
            self.cv.tag_bind("back", "<Leave>", lambda e: self.cv.itemconfig("back", fill=ACCENT))

        if self._idx < n - 1:
            self.cv.create_text(cw + card_w - 16, btn_y, text="Next \u2192", font=FBOLD, fill=ACCENT, anchor="e",
                                tags="next")
            self.cv.tag_bind("next", "<Button-1>", lambda e: self._go(1))
            self.cv.tag_bind("next", "<Enter>", lambda e: self.cv.itemconfig("next", fill=PRIMARY))
            self.cv.tag_bind("next", "<Leave>", lambda e: self.cv.itemconfig("next", fill=ACCENT))
        else:
            self.cv.create_text(cw + card_w - 16, btn_y, text="Got it!", font=FBOLD, fill=ACCENT, anchor="e",
                                tags="done")
            self.cv.tag_bind("done", "<Button-1>", lambda e: self._close())
            self.cv.tag_bind("done", "<Enter>", lambda e: self.cv.itemconfig("done", fill=PRIMARY))
            self.cv.tag_bind("done", "<Leave>", lambda e: self.cv.itemconfig("done", fill=ACCENT))

    def _go(self, delta):
        self._idx = max(0, min(len(self.steps) - 1, self._idx + delta))
        self._render()

    def _close(self):
        self.win.destroy()
        self.on_close()


class App:
    def __init__(self, root):
        self.root = root
        root.title("Image to SVG Converter")
        root.geometry("1200x720")
        root.minsize(1000, 620)
        root.configure(bg=BG)
        icon_file = _resource_path("icon.png")
        if os.path.exists(icon_file):
            root.iconphoto(True, tk.PhotoImage(file=icon_file))

        self.input_path = tk.StringVar()
        self.mode = tk.StringVar(value="outline")
        self.threshold = tk.IntVar(value=80)
        self.blur = tk.DoubleVar(value=0.5)
        self.simplify = tk.DoubleVar(value=1.0)
        self.num_colors = tk.IntVar(value=8)
        self.edge_contrast = tk.DoubleVar(value=1.5)
        self.status = tk.StringVar(value="Ready")
        self._ptk = None
        self._itk = None
        self._pending = None

        self._ui()
        for v in (self.threshold, self.blur, self.simplify, self.num_colors, self.edge_contrast, self.mode):
            v.trace_add("write", lambda *_: self._schedule())

        if not os.path.exists(TUTORIAL_FLAG):
            self.root.after(600, lambda: TutorialOverlay(self.root, self._get_steps(),
                            lambda: open(TUTORIAL_FLAG, "w").close()))
        root.protocol("WM_DELETE_WINDOW", self._on_closing)
        root.drop_target_register('*')
        root.dnd_bind('<<Drop>>', self._on_drop)
        root.bind('<Control-o>', lambda e: self._browse())
        root.bind('<Control-s>', lambda e: self._save())
        root.bind('1', lambda e: self.mode.set('outline'))
        root.bind('2', lambda e: self.mode.set('silhouette'))
        root.bind('3', lambda e: self.mode.set('color'))

    def _ui(self):
        o = tk.Frame(self.root, bg=BG)
        o.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        top = tk.Frame(o, bg=BG)
        top.pack(fill=tk.X)
        tk.Label(top, text="Image to SVG", font=FTITLE, bg=BG, fg=FG).pack(side=tk.LEFT)
        self.sl = tk.Label(top, textvariable=self.status, font=FSMALL, bg=BG, fg=MUTED)
        self.sl.pack(side=tk.RIGHT)
        tk.Frame(o, bg=BORDER, height=1).pack(fill=tk.X, pady=(6, 0))

        body = tk.Frame(o, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        left = tk.Frame(body, bg=CARD, width=340)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._left(left)
        self._right(right)

        footer = tk.Frame(o, bg=BG)
        footer.pack(fill=tk.X, pady=(6, 0))
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=1)
        footer.grid_columnconfigure(2, weight=1)
        tk.Label(footer, text="Made by Gaurav Dubey", font=FSMALL, bg=BG, fg=MUTED, anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(footer, text=f"v{VERSION}", font=FSMALL, bg=BG, fg=MUTED, anchor="center").grid(row=0, column=1)
        sf = PillButton(footer, text="\u2615 Support", cmd=self._support, bootstyle="accent", w=110, h=28)
        sf.grid(row=0, column=2, sticky="e")
        ToolTip(sf, "Support the creator on Ko-fi!")

    def _left(self, parent):
        inner = tk.Frame(parent, bg=CARD, padx=14, pady=14)
        inner.pack(fill=tk.BOTH, expand=True)

        def sec(text, pady):
            row = tk.Frame(inner, bg=CARD)
            row.pack(fill=tk.X, pady=(pady, 6))
            tk.Label(row, text=text, font=FBOLD, bg=CARD, fg=PRIMARY, anchor="w").pack(side=tk.LEFT)

        def frow(var, cb, clear_cb=None):
            row = tk.Frame(inner, bg=CARD)
            row.pack(fill=tk.X, pady=(0, 4))
            pe = PillEntry(row, textvariable=var)
            pe.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
            ToolTip(pe, "Drop an image or type the path")
            if clear_cb:
                xb = tk.Label(row, text="\u2715", font=("Segoe UI", 14, "bold"),
                              fg="#DC2626", bg=CARD, cursor="hand2")
                xb.pack(side=tk.RIGHT, padx=(0, 8))
                xb.bind("<Button-1>", lambda e: clear_cb())
                ToolTip(xb, "Clear selected image")
            pb = PillButton(row, text="Browse", cmd=cb, bootstyle="primary", w=90, h=36)
            pb.pack(side=tk.RIGHT)
            ToolTip(pb, "Select an image file (PNG, JPG, BMP, WEBP, TIFF)")
            return row

        tt_slider = {"Threshold": "Edge detection sensitivity. Higher = fewer edges", "Blur": "Gaussian blur radius. Smoothes noise before processing", "Simplify": "RDP simplification. Higher = fewer path points", "Edge Contrast": "Amplifies edge magnitudes for stronger outlines", "Colors": "Number of distinct color regions in color mode"}
        def slider(lbl, var, from_, to):
            row = tk.Frame(inner, bg=CARD)
            row.pack(fill=tk.X, pady=4)
            tk.Label(row, text=lbl, font=FSMALL, bg=CARD, fg=MUTED, width=12, anchor="w").pack(side=tk.LEFT)
            sc = tk.Scale(row, from_=from_, to=to, variable=var, orient=tk.HORIZONTAL,
                         bg=CARD, fg=FG, troughcolor=INP, activebackground=PRIMARY,
                         highlightthickness=0, bd=0, sliderrelief="flat", length=140)
            sc.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
            ToolTip(sc, tt_slider.get(lbl, ""))
            tk.Label(row, textvariable=var, font=FSMALL, bg=CARD, fg=PRIMARY, width=4).pack(side=tk.RIGHT)
            return row

        sec("Input Image", 0)
        self._input_row = frow(self.input_path, self._browse, self._clear_input)

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=6)

        sec("Mode", 0)
        self._mode_frame = tk.Frame(inner, bg=CARD)
        mf = self._mode_frame
        mf.pack(fill=tk.X, pady=(0, 4))
        tt_mode = {"Outline": "Trace edges using Sobel edge detection", "Silhouette": "Create filled shapes from thresholded image", "Color": "Quantize image into colored vector regions"}
        for text, val in [("Outline", "outline"), ("Silhouette", "silhouette"), ("Color", "color")]:
            pr = PillRadio(mf, text=text, variable=self.mode, value=val, w=100, h=34)
            pr.pack(side=tk.LEFT, padx=2)
            ToolTip(pr, tt_mode[text])

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=6)

        sec("Settings", 0)
        self._settings_frame = tk.Frame(inner, bg=CARD)
        sf = self._settings_frame
        sf.pack(fill=tk.X, pady=(0, 4))
        slider("Threshold", self.threshold, 10, 255)
        slider("Blur", self.blur, 0, 5)
        slider("Simplify", self.simplify, 0, 5)
        self.ef = tk.Frame(sf, bg=CARD)
        self.ef.pack(fill=tk.X)
        slider("Edge Contrast", self.edge_contrast, 0.5, 5)
        self.cf = tk.Frame(sf, bg=CARD)
        self.cf.pack(fill=tk.X)
        slider("Colors", self.num_colors, 2, 32)
        if self.mode.get() != "outline":
            self.ef.pack_forget()
            self.cf.pack_forget()
        self.mode.trace_add("write", self._tmode)

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=8)

        self._action_frame = tk.Frame(inner, bg=CARD)
        bf = self._action_frame
        bf.pack(fill=tk.X)
        sb = PillButton(bf, text="Save SVG", cmd=self._save, bootstyle="primary", w=130, h=40)
        sb.pack(side=tk.LEFT, padx=(0, 8))
        ToolTip(sb, "Export the current preview as an SVG vector file")
        ob = PillButton(bf, text="Open Temp", cmd=self._open, bootstyle="accent", w=130, h=40)
        ob.pack(side=tk.LEFT)
        ToolTip(ob, "Browse all recently exported SVG files")

    def _right(self, parent):
        # Original preview card
        orig = tk.Frame(parent, bg=CARD)
        orig.pack(fill=tk.X, pady=(0, 10))
        oi = tk.Frame(orig, bg=CARD, padx=14, pady=10)
        oi.pack(fill=tk.BOTH, expand=True)

        lr = tk.Frame(oi, bg=CARD)
        lr.pack(fill=tk.X, pady=(0, 8))
        tk.Label(lr, text="Original", font=FBOLD, bg=CARD, fg=PRIMARY).pack(side=tk.LEFT)
        self.pl = tk.Label(lr, text="", font=FSMALL, bg=CARD, fg=MUTED)
        self.pl.pack(side=tk.RIGHT)

        self.ic = tk.Canvas(oi, highlightthickness=0, relief="flat", bd=0, height=180)
        self.ic.pack(fill=tk.X)
        self.ic.bind("<Configure>", lambda e: self._draw_preview_bg(self.ic, e.width, e.height, INP))
        self._draw_preview_bg(self.ic, 400, 180, INP)

        # SVG preview card
        svg_c = tk.Frame(parent, bg=CARD)
        svg_c.pack(fill=tk.BOTH, expand=True)
        self._preview_frame = tk.Frame(svg_c, bg=CARD, padx=14, pady=10)
        si = self._preview_frame
        si.pack(fill=tk.BOTH, expand=True)

        lr2 = tk.Frame(si, bg=CARD)
        lr2.pack(fill=tk.X, pady=(0, 8))
        tk.Label(lr2, text="SVG Preview", font=FBOLD, bg=CARD, fg=SUCCESS).pack(side=tk.LEFT)
        self.il = tk.Label(lr2, text="", font=FSMALL, bg=CARD, fg=MUTED)
        self.il.pack(side=tk.RIGHT)

        self.pc = tk.Canvas(si, highlightthickness=0, bd=0, relief="flat")
        self.pc.pack(fill=tk.BOTH, expand=True)
        self.pc.bind("<Configure>", self._uc)

    def _draw_preview_bg(self, cv, w, h, clr):
        cv.delete("all")
        rr(cv, 0, 0, w, h, 12, fill=clr, outline=BORDER, width=1)

    def _support(self):
        webbrowser.open(KOFI_URL)

    def _on_closing(self):
        d = tk.Toplevel(self.root, bg=CARD)
        d.title("Exit")
        d.geometry("380x200")
        d.resizable(False, False)
        d.transient(self.root)
        d.grab_set()
        d.update_idletasks()
        pw = self.root.winfo_width()
        ph = self.root.winfo_height()
        px = self.root.winfo_x()
        py = self.root.winfo_y()
        d.geometry(f"380x200+{px + (pw - 380) // 2}+{py + (ph - 200) // 2}")

        inner = tk.Frame(d, bg=CARD, padx=20, pady=20)
        inner.pack(fill=tk.BOTH, expand=True)

        tk.Label(inner, text="Don't forget to support the creator!",
                 font=FBOLD, bg=CARD, fg=ACCENT, wraplength=320).pack(pady=(0, 8))
        tk.Label(inner, text="If you find this tool useful, consider buying me a coffee!",
                 font=FSMALL, bg=CARD, fg=MUTED, wraplength=320).pack(pady=(0, 16))

        bf = tk.Frame(inner, bg=CARD)
        bf.pack(fill=tk.X)
        PillButton(bf, text="\u2615 Support", cmd=lambda: [webbrowser.open(KOFI_URL), d.destroy()],
                   bootstyle="accent", w=110, h=34).pack(side=tk.LEFT, padx=(0, 8))
        PillButton(bf, text="Exit App", cmd=lambda: [d.destroy(), self.root.destroy()],
                   bootstyle="primary", w=100, h=34).pack(side=tk.LEFT, padx=(0, 8))
        PillButton(bf, text="Cancel", cmd=d.destroy, bootstyle="secondary", w=90, h=34).pack(side=tk.LEFT)

    def _on_drop(self, event):
        path = event.data.strip('{}')
        if path:
            self.input_path.set(path)
            self._load_input(path)
            self._schedule()

    def _uc(self, e=None):
        if e and hasattr(self, 'pc'):
            w, h = e.width, e.height
            self._draw_preview_bg(self.pc, w, h, "#ffffff")

    def _tmode(self, *a):
        m = self.mode.get()
        if m == "outline":
            self.ef.pack(fill=tk.X)
            self.cf.pack_forget()
        elif m == "color":
            self.ef.pack_forget()
            self.cf.pack(fill=tk.X)
        else:
            self.ef.pack_forget()
            self.cf.pack_forget()

    def _get_steps(self):
        return [
            {"widget": self._input_row, "title": "Select an Image",
             "desc": "Click Browse or drag & drop an image file (PNG, JPG, BMP, WEBP, TIFF)."},
            {"widget": self._mode_frame, "title": "Choose a Mode",
             "desc": "Outline \u2013 edge detection lines. Silhouette \u2013 filled shapes. Color \u2013 quantized color regions."},
            {"widget": self._settings_frame, "title": "Adjust Settings",
             "desc": "Fine-tune the result: Threshold, Blur, Simplify, Edge Contrast, and Colors."},
            {"widget": self._action_frame, "title": "Export or Browse",
             "desc": "Click \u2018Save SVG\u2019 to export, or \u2018Open Temp\u2019 to see all recent exports."},
            {"widget": self._preview_frame, "title": "Live Preview",
             "desc": "The SVG preview updates in real-time as you tweak settings."},
        ]

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp"), ("All files", "*.*")])
        if path:
            self.input_path.set(path)
            self._load_input(path)
            self._schedule()

    def _load_input(self, path):
        try:
            img = Image.open(path)
            cw = self.ic.winfo_width() or 500
            ratio = min(cw / img.width, 160 / img.height)
            if ratio < 1:
                img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
            self._itk = ImageTk.PhotoImage(img)
            self.ic.delete("all")
            w = self.ic.winfo_width() or 500
            h = self.ic.winfo_height() or 180
            self._draw_preview_bg(self.ic, w, h, INP)
            self.ic.create_image(cw // 2, 90, image=self._itk)
            self.pl.config(text=os.path.basename(path))
        except Exception:
            pass

    def _clear_input(self):
        self.input_path.set("")
        self._itk = None
        self._ptk = None
        w = self.ic.winfo_width() or 500
        h = self.ic.winfo_height() or 180
        self._draw_preview_bg(self.ic, w, h, INP)
        pw = self.pc.winfo_width() or 400
        ph = self.pc.winfo_height() or 300
        self._draw_preview_bg(self.pc, pw, ph, "#ffffff")
        self.pl.config(text="")
        self.il.config(text="")
        self.status.set("Ready")

    def _schedule(self):
        if self._pending:
            self.root.after_cancel(self._pending)
        self._pending = self.root.after(400, self._do)

    def _do(self):
        path = self.input_path.get()
        if not path or not os.path.exists(path):
            return
        self._pending = None
        threading.Thread(target=self._gen, daemon=True).start()

    def _get_kwargs(self):
        kw = {"blur": self.blur.get(), "simplify": self.simplify.get(), "background_color": "#ffffff"}
        if self.mode.get() == "outline":
            kw.update({"threshold": int(self.threshold.get()), "edge_contrast": self.edge_contrast.get()})
        elif self.mode.get() == "silhouette":
            kw.update({"threshold": int(self.threshold.get()), "fill_color": "#000000"})
        else:
            kw.update({"num_colors": int(self.num_colors.get())})
        return kw

    def _gen(self):
        try:
            kw = self._get_kwargs()
            path = self.input_path.get()
            img = Image.open(path)
            bmp = render_preview_bitmap(img, self.mode.get(), max_size=600, **kw)
            paths = count_paths(path, self.mode.get(), **kw)
            self.root.after(0, lambda: self._show(bmp, paths))
        except Exception as e:
            self.root.after(0, lambda: self.status.set(f"Error: {str(e)[:60]}"))

    def _show(self, img, paths=0):
        cw = self.pc.winfo_width() or 400
        ch = self.pc.winfo_height() or 300
        self._draw_preview_bg(self.pc, cw, ch, "#ffffff")
        ratio = min(cw / img.width, ch / img.height)
        d = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        self._ptk = ImageTk.PhotoImage(d)
        self.pc.create_image((cw - d.width) // 2, (ch - d.height) // 2, image=self._ptk, anchor="nw")
        self.il.config(text=f"{img.width}x{img.height}  |  {paths} paths")
        self.status.set("Preview ready")

    def _save(self):
        if not self.input_path.get():
            messagebox.showerror("Error", "Please select an input image.")
            return
        out = filedialog.asksaveasfilename(
            title="Save SVG As", defaultextension=".svg",
            filetypes=[("SVG files", "*.svg"), ("All files", "*.*")])
        if not out:
            return
        self.status.set("Saving SVG...")
        threading.Thread(target=self._do_save, args=(out,), daemon=True).start()

    def _do_save(self, out):
        try:
            kw = self._get_kwargs()
            c = save_svg(self.input_path.get(), out, self.mode.get(), **kw)
            self.root.after(0, lambda: self.status.set(f"Saved! {c} paths -> {os.path.basename(out)}"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _open(self):
        os.startfile(TEMP_DIR)


if __name__ == "__main__":
    from tkinterdnd2 import TkinterDnD
    root = TkinterDnD.Tk()
    tb.Style(theme="darkly")
    App(root)
    root.mainloop()
