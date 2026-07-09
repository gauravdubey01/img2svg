import numpy as np
from PIL import Image, ImageFilter
import math
import os
import sys
import atexit
import shutil
import tempfile
import ctypes
from scipy.ndimage import convolve as sp_convolve

if getattr(sys, 'frozen', False):
    _base = sys._MEIPASS
    _cairo_path = os.path.join(_base, "libcairo-2.dll")
    if os.path.exists(_cairo_path):
        try:
            ctypes.CDLL(_cairo_path)
        except Exception:
            pass

DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]

TEMP_DIR = os.path.join(tempfile.gettempdir(), "img2svg_preview")
os.makedirs(TEMP_DIR, exist_ok=True)
atexit.register(lambda: shutil.rmtree(TEMP_DIR, ignore_errors=True))


def _convolve2d(arr, kernel):
    return sp_convolve(arr, kernel)


def _perp_distance(p, a, b):
    ab = (b[0] - a[0], b[1] - a[1])
    ap = (p[0] - a[0], p[1] - a[1])
    ab_sq = ab[0] * ab[0] + ab[1] * ab[1]
    if ab_sq == 0:
        return math.hypot(ap[0], ap[1])
    t = max(0, min(1, (ap[0] * ab[0] + ap[1] * ab[1]) / ab_sq))
    proj = (a[0] + t * ab[0], a[1] + t * ab[1])
    return math.hypot(p[0] - proj[0], p[1] - proj[1])


def _rdp(points, epsilon):
    if len(points) < 3:
        return points
    first, last = points[0], points[-1]
    max_dist = 0
    max_idx = 0
    for i in range(1, len(points) - 1):
        d = _perp_distance(points[i], first, last)
        if d > max_dist:
            max_dist = d
            max_idx = i
    if max_dist > epsilon:
        left = _rdp(points[:max_idx + 1], epsilon)
        right = _rdp(points[max_idx:], epsilon)
        return left[:-1] + right
    return [first, last]


def _trace_contour(binary, start_x, start_y, visited):
    h, w = binary.shape
    contour = []
    x, y = start_x, start_y
    search_dir = 0
    max_steps = h * w
    steps = 0
    while steps < max_steps:
        steps += 1
        contour.append((x, y))
        visited[y, x] = True
        found = False
        for i in range(8):
            d = (search_dir + i) % 8
            nx, ny = x + DIRS[d][0], y + DIRS[d][1]
            if 0 <= nx < w and 0 <= ny < h and binary[ny, nx] and not visited[ny, nx]:
                x, y = nx, ny
                search_dir = (d + 6) % 8
                found = True
                break
        if not found:
            break
        if (x, y) == (start_x, start_y):
            break
    return contour


def _find_contours(binary):
    h, w = binary.shape
    visited = np.zeros_like(binary, dtype=bool)
    contours = []
    for y in range(h):
        for x in range(w):
            if binary[y, x] and not visited[y, x]:
                c = _trace_contour(binary, x, y, visited)
                if len(c) > 5:
                    contours.append(c)
    return contours


def _get_svg_data(mode, img, **kwargs):
    orig_w, orig_h = img.size
    blur = kwargs.get("blur", 0.5)
    simplify = kwargs.get("simplify", 1.0)
    bg = kwargs.get("background_color", "#ffffff")

    if mode == "outline":
        threshold = int(kwargs.get("threshold", 80))
        edge_contrast = kwargs.get("edge_contrast", 1.5)
        sw = kwargs.get("stroke_width", 1.0)
        sc = kwargs.get("stroke_color", "#000000")

        gray = img.convert("L")
        if blur > 0:
            gray = gray.filter(ImageFilter.GaussianBlur(radius=blur))
        arr = np.array(gray, dtype=np.float32)
        sx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
        sy = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)
        ix = _convolve2d(arr, sx)
        iy = _convolve2d(arr, sy)
        mag = np.hypot(ix, iy) * edge_contrast
        mag = np.clip(mag, 0, 255).astype(np.uint8)
        binary = mag > threshold
        contours = _find_contours(binary)
        simplified = []
        for c in contours:
            s = _rdp(c, simplify)
            if len(s) >= 2:
                simplified.append(s)
        return _svg_string_outline(orig_w, orig_h, simplified, sw, sc, bg)

    elif mode == "silhouette":
        threshold = int(kwargs.get("threshold", 128))
        fc = kwargs.get("fill_color", "#000000")
        gray = img.convert("L")
        if blur > 0:
            gray = gray.filter(ImageFilter.GaussianBlur(radius=blur))
        arr = np.array(gray)
        binary = arr > threshold
        contours = _find_contours(binary)
        simplified = []
        for c in contours:
            s = _rdp(c, simplify)
            if len(s) >= 3:
                simplified.append(s)
        return _write_string_filled(orig_w, orig_h, simplified, fc, bg)

    else:
        num_colors = int(kwargs.get("num_colors", 8))
        if blur > 0:
            img = img.filter(ImageFilter.GaussianBlur(radius=blur))
        try:
            quantized = img.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
        except Exception:
            quantized = img.quantize(colors=num_colors)
        palette = quantized.getpalette()[:num_colors * 3]
        arr = np.array(quantized, dtype=np.uint8)
        all_paths = []
        all_colors = []
        for color_idx in range(num_colors):
            binary = arr == color_idx
            if not binary.any():
                continue
            contours = _find_contours(binary)
            for c in contours:
                s = _rdp(c, simplify)
                if len(s) >= 3:
                    all_paths.append(s)
                    r, g, b = palette[color_idx * 3], palette[color_idx * 3 + 1], palette[color_idx * 3 + 2]
                    all_colors.append(f"#{r:02x}{g:02x}{b:02x}")
        return _write_string_color_filled(orig_w, orig_h, all_paths, all_colors, bg)


def render_preview_bitmap(img, mode="outline", max_size=600, **kwargs):
    """Fast bitmap preview matching what the SVG will look like."""
    w, h = img.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    blur = kwargs.get("blur", 0.5)
    thresh = int(kwargs.get("threshold", 80))
    ec = kwargs.get("edge_contrast", 1.5)
    nc = int(kwargs.get("num_colors", 8))

    if mode == "outline":
        gray = img.convert("L")
        if blur > 0:
            gray = gray.filter(ImageFilter.GaussianBlur(radius=blur))
        arr = np.array(gray, dtype=np.float32)
        sx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
        sy = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)
        ix = _convolve2d(arr, sx)
        iy = _convolve2d(arr, sy)
        mag = np.hypot(ix, iy) * ec
        mag = np.clip(mag, 0, 255).astype(np.uint8)
        binary = (mag > thresh).astype(np.uint8) * 255
        return Image.fromarray(binary, mode="L").convert("RGB")

    elif mode == "silhouette":
        gray = img.convert("L")
        if blur > 0:
            gray = gray.filter(ImageFilter.GaussianBlur(radius=blur))
        arr = np.array(gray)
        binary = (arr > kwargs.get("threshold", 128)).astype(np.uint8) * 255
        return Image.fromarray(binary, mode="L").convert("RGB")

    else:
        if blur > 0:
            img = img.filter(ImageFilter.GaussianBlur(radius=blur))
        try:
            quantized = img.quantize(colors=nc, method=Image.Quantize.MEDIANCUT)
        except Exception:
            quantized = img.quantize(colors=nc)
        return quantized.convert("RGB")


def save_temp_svgs(image_path, **kwargs):
    """Save all 3 modes as temp SVG files. Returns dict of {mode: filepath}."""
    img = Image.open(image_path)
    results = {}
    for mode in ("outline", "silhouette", "color"):
        try:
            svg = _get_svg_data(mode, img, **kwargs)
            name = f"{os.path.basename(image_path)}.{mode}.svg"
            out = os.path.join(TEMP_DIR, name)
            with open(out, "w", encoding="utf-8") as f:
                f.write(svg)
            results[mode] = out
        except Exception:
            results[mode] = None
    return results


def count_paths(image_path, mode="outline", **kwargs):
    """Count SVG paths without writing a file."""
    img = Image.open(image_path)
    svg = _get_svg_data(mode, img, **kwargs)
    return svg.count('d="M ')


def save_svg(image_path, output_path, mode="outline", **kwargs):
    """Save single SVG file. Returns path count."""
    img = Image.open(image_path)
    svg = _get_svg_data(mode, img, **kwargs)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    return svg.count('d="M ')


def _svg_string_outline(w, h, contours, sw, sc, bg):
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    if bg and bg != "none":
        lines.append(f'<rect width="{w}" height="{h}" fill="{bg}"/>')
    lines.append(f'<g fill="none" stroke="{sc}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">')
    for contour in contours:
        d = "M " + " L ".join(f"{p[0]},{p[1]}" for p in contour)
        lines.append(f'<path d="{d}"/>')
    lines.append("</g></svg>")
    return "\n".join(lines)


def _write_string_filled(w, h, contours, fc, bg):
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    if bg and bg != "none":
        lines.append(f'<rect width="{w}" height="{h}" fill="{bg}"/>')
    lines.append(f'<g fill="{fc}">')
    for contour in contours:
        d = "M " + " L ".join(f"{p[0]},{p[1]}" for p in contour) + " Z"
        lines.append(f'<path d="{d}"/>')
    lines.append("</g></svg>")
    return "\n".join(lines)


def _write_string_color_filled(w, h, contours, colors, bg):
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    if bg and bg != "none":
        lines.append(f'<rect width="{w}" height="{h}" fill="{bg}"/>')
    for contour, color in zip(contours, colors):
        d = "M " + " L ".join(f"{p[0]},{p[1]}" for p in contour) + " Z"
        lines.append(f'<path d="{d}" fill="{color}"/>')
    lines.append("</svg>")
    return "\n".join(lines)