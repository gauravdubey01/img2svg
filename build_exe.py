import PyInstaller.__main__
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
main_script = os.path.join(script_dir, "main.py")
icon_path = os.path.join(script_dir, "icon.ico") if os.path.exists(os.path.join(script_dir, "icon.ico")) else None

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

if icon_path:
    args.extend(["--icon", icon_path])

PyInstaller.__main__.run(args)

print("\nDone. EXE is in the 'dist' folder.")