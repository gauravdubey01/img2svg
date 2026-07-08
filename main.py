import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import os
from PIL import Image, ImageTk
from converter import render_preview_bitmap, save_svg, TEMP_DIR

BG = "#1e1e2e"
CARD = "#2a2a3e"
INP = "#353550"
FG = "#cdd6f4"
MUTED = "#6c7086"
ACCENT = "#89b4fa"
AHOVER = "#74c7ec"
GREEN = "#a6e3a1"
BORDER = "#45475a"
FONT = ("Segoe UI", 10)
FBOLD = ("Segoe UI", 10, "bold")
FTITLE = ("Segoe UI", 14, "bold")
FSMALL = ("Segoe UI", 9)


def rr(c, x1, y1, x2, y2, r, **kw):
    pts = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2, x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class MButton(tk.Canvas):
    def __init__(self, parent, text, cmd=None, bg=ACCENT, fg="#11111b", w=120, h=34, **kw):
        super().__init__(parent, width=w, height=h, highlightthickness=0, **kw)
        self.cmd = cmd
        self.bg = bg
        self.fg = fg
        self.tw, self.th = w, h
        self.configure(bg=BG, bd=0)
        self._d(text)
        self.bind("<Button-1>", lambda e: self.cmd() if self.cmd else None)
        self.bind("<Enter>", lambda e: self._d(text, True))
        self.bind("<Leave>", lambda e: self._d(text))

    def _d(self, text, hover=False):
        self.delete("all")
        c = self.bg if not hover else AHOVER
        rr(self, 0, 0, self.tw, self.th, 8, fill=c, outline=c)
        self.create_text(self.tw // 2, self.th // 2, text=text, fill=self.fg, font=FBOLD, anchor="center")


MODE_MAP = {"outline": "outline", "silhouette": "silhouette", "color": "color"}


class App:
    def __init__(self, root):
        self.root = root
        root.title("Image to SVG Converter")
        root.geometry("1200x720")
        root.minsize(1000, 620)
        root.configure(bg=BG)

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

        self._style()
        self._ui()
        for v in (self.threshold, self.blur, self.simplify, self.num_colors, self.edge_contrast, self.mode):
            v.trace_add("write", lambda *_: self._schedule())

    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG, font=FONT)
        s.configure("TLabel", background=BG, foreground=FG)
        s.configure("TFrame", background=BG)
        s.configure("TLabelframe", background=CARD, foreground=FG, bordercolor=BORDER, relief="flat")
        s.configure("TLabelframe.Label", background=CARD, foreground=ACCENT, font=FBOLD)
        s.configure("TEntry", fieldbackground=INP, foreground=FG, bordercolor=BORDER, insertcolor=FG)
        s.configure("TScale", background=CARD, troughcolor=INP, sliderlength=16)
        s.configure("TRadiobutton", background=BG, foreground=FG, indicatoron=False)
        s.map("TRadiobutton",
              background=[("selected", ACCENT), ("!selected", INP)],
              foreground=[("selected", "#11111b"), ("!selected", FG)])

    def _ui(self):
        o = tk.Frame(self.root, bg=BG)
        o.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        top = tk.Frame(o, bg=BG)
        top.pack(fill=tk.X)
        tk.Label(top, text="Image to SVG", font=FTITLE, bg=BG, fg=FG).pack(side=tk.LEFT)
        self.sl = tk.Label(top, textvariable=self.status, font=FSMALL, bg=BG, fg=MUTED)
        self.sl.pack(side=tk.RIGHT)

        body = tk.Frame(o, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        left = tk.Frame(body, bg=BG, width=340)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._left(left)
        self._right(right)

    def _left(self, parent):
        card = tk.Frame(parent, bg=CARD)
        card.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(card, bg=CARD, padx=14, pady=14)
        inner.pack(fill=tk.BOTH, expand=True)

        def sec(text, pady):
            tk.Label(inner, text=text, font=FBOLD, bg=CARD, fg=ACCENT, anchor="w").pack(fill=tk.X, pady=(pady, 4))

        def frow(var, cb):
            row = tk.Frame(inner, bg=CARD)
            row.pack(fill=tk.X, pady=(0, 4))
            e = tk.Entry(row, textvariable=var, bg=INP, fg=FG, insertbackground=FG, bd=0, font=FSMALL,
                         relief="flat", highlightbackground=BORDER, highlightthickness=1)
            e.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 6))
            tk.Button(row, text="Browse", command=cb, bg=ACCENT, fg="#11111b", bd=0, padx=10,
                      font=FSMALL, activebackground=AHOVER, cursor="hand2", relief="flat").pack(side=tk.RIGHT)

        def slider(lbl, var, from_, to, step=1):
            row = tk.Frame(inner, bg=CARD)
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=lbl, font=FSMALL, bg=CARD, fg=FG, width=12, anchor="w").pack(side=tk.LEFT)
            sc = tk.Scale(row, from_=from_, to=to, variable=var, orient=tk.HORIZONTAL,
                          bg=CARD, fg=FG, troughcolor=INP, activebackground=ACCENT,
                          highlightthickness=0, bd=0, sliderrelief="flat", length=140)
            sc.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
            tk.Label(row, textvariable=var, font=FSMALL, bg=CARD, fg=ACCENT, width=4).pack(side=tk.RIGHT)
            return row

        sec("Input Image", 0)
        frow(self.input_path, self._browse)

        sec("Mode", 10)
        mf = tk.Frame(inner, bg=CARD)
        mf.pack(fill=tk.X)
        for text, val in [("Outline", "outline"), ("Silhouette", "silhouette"), ("Color", "color")]:
            rb = tk.Radiobutton(mf, text=text, variable=self.mode, value=val,
                               bg=CARD, fg=FG, selectcolor=ACCENT, activebackground=CARD,
                               activeforeground=ACCENT, font=FONT, bd=0, padx=8,
                               indicatoron=False, relief="flat", overrelief="flat", width=10)
            rb.pack(side=tk.LEFT, padx=2)

        sec("Settings", 10)
        sf = tk.Frame(inner, bg=CARD)
        sf.pack(fill=tk.X)
        slider("Threshold", self.threshold, 10, 255)
        slider("Blur", self.blur, 0, 5, 0.1)
        slider("Simplify", self.simplify, 0, 5, 0.1)
        self.ef = tk.Frame(sf, bg=CARD)
        self.ef.pack(fill=tk.X)
        slider("Edge Contrast", self.edge_contrast, 0.5, 5, 0.1)
        self.cf = tk.Frame(sf, bg=CARD)
        self.cf.pack(fill=tk.X)
        slider("Colors", self.num_colors, 2, 32)
        if self.mode.get() != "outline":
            self.cf.pack_forget()
            self.ef.pack_forget()
        self.mode.trace_add("write", self._tmode)

        tk.Frame(inner, bg=BG, height=1).pack(fill=tk.X, pady=10)
        bf = tk.Frame(inner, bg=CARD)
        bf.pack(fill=tk.X)
        MButton(bf, "Save SVG", self._save, bg=GREEN, fg="#11111b", w=140, h=36).pack(side=tk.LEFT, padx=(0, 8))
        MButton(bf, "Open Temp Folder", self._open, bg=INP, fg=FG, w=140, h=36).pack(side=tk.LEFT)

    def _right(self, parent):
        pf = tk.Frame(parent, bg=CARD)
        pf.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(pf, bg=CARD, padx=14, pady=14)
        inner.pack(fill=tk.BOTH, expand=True)

        lr = tk.Frame(inner, bg=CARD)
        lr.pack(fill=tk.X, pady=(0, 8))
        tk.Label(lr, text="Original", font=FBOLD, bg=CARD, fg=ACCENT).pack(side=tk.LEFT)
        self.pl = tk.Label(lr, text="", font=FSMALL, bg=CARD, fg=MUTED)
        self.pl.pack(side=tk.RIGHT)

        self.ic = tk.Canvas(inner, bg=INP, highlightthickness=0, relief="flat", bd=0, height=200)
        self.ic.pack(fill=tk.X, pady=(0, 12))

        lr2 = tk.Frame(inner, bg=CARD)
        lr2.pack(fill=tk.X, pady=(0, 8))
        tk.Label(lr2, text="SVG Preview", font=FBOLD, bg=CARD, fg=GREEN).pack(side=tk.LEFT)
        self.il = tk.Label(lr2, text="", font=FSMALL, bg=CARD, fg=MUTED)
        self.il.pack(side=tk.RIGHT)

        self.pc = tk.Canvas(inner, bg="#ffffff", highlightthickness=0, bd=0, relief="flat")
        self.pc.pack(fill=tk.BOTH, expand=True)
        self.pt = self.pc.create_text(300, 150, text="Load an image to see preview", fill=MUTED, font=FONT)
        self.pc.bind("<Configure>", self._uc)

    def _uc(self, e=None):
        if hasattr(self, 'pt'):
            self.pc.coords(self.pt, e.width // 2 if e else 300, e.height // 2 if e else 150)

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
            ratio = min(cw / img.width, 180 / img.height)
            if ratio < 1:
                img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
            self._itk = ImageTk.PhotoImage(img)
            self.ic.delete("all")
            self.ic.create_image(cw // 2, 100, image=self._itk)
            self.pl.config(text=os.path.basename(path))
        except Exception:
            pass

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
            img = Image.open(self.input_path.get())
            bmp = render_preview_bitmap(img, self.mode.get(), max_size=600, **kw)
            self.root.after(0, lambda: self._show(bmp))
        except Exception as e:
            self.root.after(0, lambda: self.status.set(f"Error: {str(e)[:60]}"))

    def _show(self, img):
        cw = self.pc.winfo_width() or 400
        ch = self.pc.winfo_height() or 300
        ratio = min(cw / img.width, ch / img.height)
        d = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        self._ptk = ImageTk.PhotoImage(d)
        self.pc.delete("all")
        self.pc.create_image((cw - d.width) // 2, (ch - d.height) // 2, image=self._ptk, anchor="nw")
        self.il.config(text=f"{img.width}x{img.height}")
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
    root = tk.Tk()
    App(root)
    root.mainloop()