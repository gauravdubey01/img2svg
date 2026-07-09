# Image to SVG Converter

Convert PNG, JPG, BMP, WEBP and TIFF images to scalable vector (SVG) files with a modern dark-themed desktop GUI.

## Features

- **Three conversion modes:** Outline (edge detection), Silhouette (filled shapes), Color (quantized regions)
- **Live preview** updates in real-time as you tweak settings
- **Adjustable controls:** Threshold, Blur, Simplify, Edge Contrast, and Color count
- **Multi-step tutorial overlay** on first launch
- **Drag & drop** support for quick image loading
- **One-click export** to SVG or open temp folder for all recent exports
- **Keyboard shortcuts:** Ctrl+O (open), Ctrl+S (save), 1/2/3 (switch mode)

## Tech Stack

- **Python 3.12** — tkinter + ttkbootstrap GUI
- **Pillow** — image I/O and quantization
- **scipy** — fast Sobel edge detection via convolution
- **PyInstaller** — single-file Windows EXE packaging

## Usage

1. Browse or drag an image onto the window
2. Select a mode (Outline / Silhouette / Color)
3. Adjust settings until the preview looks right
4. Click **Save SVG** to export

## Download

Pre-built EXE is available in the `dist/` folder or from [Releases](https://github.com/gauravdubey01/img2svg/releases).

## Build from Source

```bash
pip install -r requirements.txt
python build_exe.py
```

## Support

If you find this tool useful, consider [buying me a coffee](https://ko-fi.com/gauravdubeypro)!
