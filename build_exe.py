import PyInstaller.__main__
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
main_script = os.path.join(script_dir, "main.py")

# Convert icon.png → icon.ico for EXE taskbar icon
icon_png = os.path.join(script_dir, "icon.png")
icon_ico = os.path.join(script_dir, "icon.ico")
if os.path.exists(icon_png):
    from PIL import Image
    img = Image.open(icon_png)
    img.save(icon_ico, sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])

cairo_dll = os.path.join(script_dir, "libcairo-2.dll")
args = [
    main_script,
    "--onefile",
    "--windowed",
    "--name", "ImageToSVG",
    "--add-data", f"converter.py{os.pathsep}.",
]
if os.path.exists(cairo_dll):
    args.extend(["--add-binary", f"{cairo_dll}{os.pathsep}."])

if os.path.exists(icon_png):
    args.extend(["--add-data", f"icon.png{os.pathsep}."])

if os.path.exists(icon_ico):
    args.extend(["--icon", icon_ico])

PyInstaller.__main__.run(args)

print("\nDone. EXE is in the 'dist' folder.")
