from PIL import Image
import os

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Assets")
ICON_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icon.png")
BG = "#0F172A"

SIZES = {
    "Square44x44Logo.png": (44, 44),
    "Square71x71Logo.png": (71, 71),
    "Square150x150Logo.png": (150, 150),
    "Square310x310Logo.png": (310, 310),
    "StoreLogo.png": (50, 50),
    "Wide310x150Logo.png": (310, 150),
    "SplashScreen.png": (620, 300),
}


def resize_centered(img, size):
    out = Image.new("RGB", size, BG)
    img.thumbnail((size[0], size[1]), Image.LANCZOS)
    x = (size[0] - img.width) // 2
    y = (size[1] - img.height) // 2
    out.paste(img, (x, y))
    return out


def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    src = Image.open(ICON_SRC).convert("RGBA")
    for name, size in SIZES.items():
        img = resize_centered(src, size)
        img.save(os.path.join(ASSETS_DIR, name))
        print(f"  {name}: {size[0]}x{size[1]}")
    print("Done.")


if __name__ == "__main__":
    main()
