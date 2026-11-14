"""Dessine l'icône de Démo Express et l'écran de démarrage (Pillow). Lancé avant PyInstaller :

    python packaging/icone.py

Écrit dans packaging/genere/ : icone.ico (Windows), icone.png (fenêtre), icone-1024.png (Mac, pages de vente),
demarrage.png (écran affiché pendant le démarrage de l'exécutable Windows).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SORTIE = Path(__file__).resolve().parent / "genere"
T = 1024  # dessiné en grand puis réduit : bords lisses
COULEURS = [(167, 139, 250), (244, 114, 182), (251, 146, 60)]  # dégradé VORELIK : violet, rose, orange
NUIT = (10, 15, 31)


def degrade(taille: int) -> Image.Image:
    fond = Image.new("RGB", (taille, taille))
    px = fond.load()
    for y in range(taille):
        for x in range(taille):
            t = (x + y) / (2 * taille - 2)
            a, b, u = (COULEURS[0], COULEURS[1], t * 2) if t < .5 else (COULEURS[1], COULEURS[2], t * 2 - 1)
            px[x, y] = tuple(round(c1 + (c2 - c1) * u) for c1, c2 in zip(a, b))
    return fond


def dessiner() -> Image.Image:
    masque = Image.new("L", (T, T), 0)
    ImageDraw.Draw(masque).rounded_rectangle((0, 0, T - 1, T - 1), radius=230, fill=255)
    img = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    img.paste(degrade(T), (0, 0), masque)
    d = ImageDraw.Draw(img)
    # Maquette de site : fenêtre blanche, bandeau sombre, photo, titre, bouton
    d.rounded_rectangle((170, 210, 854, 740), radius=56, fill="white")
    d.rounded_rectangle((170, 210, 854, 320), radius=56, fill=NUIT)
    d.rectangle((170, 270, 854, 320), fill=NUIT)
    for i, x in enumerate((235, 290, 345)):
        d.ellipse((x - 17, 248, x + 17, 282), fill=[(244, 114, 182), (251, 146, 60), (167, 139, 250)][i])
    d.rounded_rectangle((230, 370, 520, 420), radius=25, fill=NUIT)  # titre
    d.rounded_rectangle((230, 450, 470, 482), radius=16, fill=(200, 205, 222))
    d.rounded_rectangle((230, 530, 420, 600), radius=35, fill=(244, 114, 182))  # bouton
    d.rounded_rectangle((570, 370, 794, 680), radius=40, fill=(251, 226, 205))  # photo
    d.polygon([(600, 650), (680, 540), (760, 650)], fill=(251, 146, 60))
    d.ellipse((700, 405, 760, 465), fill="white")
    # Étincelle : « en deux minutes »
    cx, cy = 820, 790
    for r, couleur in ((118, NUIT), (90, "white")):
        d.polygon([(cx, cy - r), (cx + r * .28, cy - r * .28), (cx + r, cy), (cx + r * .28, cy + r * .28),
                   (cx, cy + r), (cx - r * .28, cy + r * .28), (cx - r, cy), (cx - r * .28, cy - r * .28)], fill=couleur)
    return img


def police(taille: int):
    for nom in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "Helvetica.ttc"):
        try:
            return ImageFont.truetype(nom, taille)
        except OSError:
            continue
    return ImageFont.load_default(size=taille)


def ecran_de_demarrage(icone: Image.Image) -> Image.Image:
    ecran = Image.new("RGB", (600, 200), (245, 247, 252))
    petite = icone.resize((136, 136), Image.LANCZOS)
    ecran.paste(petite, (32, 32), petite)
    d = ImageDraw.Draw(ecran)
    d.text((196, 46), "Démo Express", fill=(15, 23, 51), font=police(34))
    d.text((198, 92), "by VORELIK", fill=(109, 91, 239), font=police(18))
    d.text((198, 132), "Démarrage… · Starting…", fill=(91, 100, 128), font=police(18))  # avant le choix de la langue
    return ecran


def main() -> None:
    SORTIE.mkdir(exist_ok=True)
    icone = dessiner()
    icone.save(SORTIE / "icone.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    icone.save(SORTIE / "icone-1024.png")
    icone.resize((256, 256), Image.LANCZOS).save(SORTIE / "icone.png")
    ecran_de_demarrage(icone).save(SORTIE / "demarrage.png")
    print(f"Icônes écrites dans {SORTIE}")


if __name__ == "__main__":
    main()
