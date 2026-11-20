# PyInstaller : application « Démo Express ».
#   pip install -e . pyinstaller pillow
#   python packaging/icone.py
#   pyinstaller packaging/demo.spec --noconfirm
# Résultat, comme Chasseur de sites :
#   Windows : dist/DemoExpress.exe (un seul fichier, sans console, écran de démarrage)
#   macOS   : dist/DemoExpress.app (à zipper avec « ditto »)
#   Linux   : dist/DemoExpress/ (dossier)
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

from demo_express import __version__

RACINE = Path(SPECPATH).parent
GENERE = RACINE / "packaging" / "genere"
WINDOWS, MAC = sys.platform == "win32", sys.platform == "darwin"

donnees = [
    (str(GENERE / "icone.png"), "."),
    (str(RACINE / "demo_express" / "templates"), "demo_express/templates"),
    (str(RACINE / "demo_express" / "static"), "demo_express/static"),
    (str(RACINE / "demo_express" / "langues"), "demo_express/langues"),
    (str(RACINE / "demo_express" / "photos"), "demo_express/photos"),  # photothèque d'illustration (CC0)
]

caches = collect_submodules("uvicorn") + collect_submodules("demo_express") + ["multipart", "python_multipart",
          "PIL.Image", "PIL.ImageOps", "PIL.JpegImagePlugin", "PIL.PngImagePlugin", "PIL.WebPImagePlugin"]

a = Analysis(
    [str(RACINE / "packaging" / "lancer.py")],
    pathex=[str(RACINE)],
    datas=donnees,
    hiddenimports=caches,
    excludes=["pytest", "respx"],
    noarchive=False,
)
pyz = PYZ(a.pure)

if WINDOWS:
    ecran = Splash(str(GENERE / "demarrage.png"), binaries=a.binaries, datas=a.datas, text_pos=None)
    exe = EXE(
        pyz, a.scripts, ecran, ecran.binaries, a.binaries, a.datas, [],
        name="DemoExpress",
        console=False,  # une petite fenêtre remplace la console noire
        icon=str(GENERE / "icone.ico"),
        upx=False,
    )
else:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="DemoExpress",
        console=not MAC,
        icon=str(GENERE / ("icone-1024.png" if MAC else "icone.ico")),
    )
    dossier = COLLECT(exe, a.binaries, a.datas, name="DemoExpress")
    if MAC:
        app = BUNDLE(
            dossier,
            name="DemoExpress.app",
            icon=str(GENERE / "icone-1024.png"),
            bundle_identifier="com.vorelik.demoexpress",
            version=__version__,
            info_plist={
                "CFBundleDisplayName": "Démo Express",
                "CFBundleName": "Démo Express",
                "NSHighResolutionCapable": True,
                "LSMinimumSystemVersion": "11.0",
            },
        )
