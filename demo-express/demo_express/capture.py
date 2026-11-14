"""Images et PDF de la maquette d'export, fabriqués par le navigateur intégré (Chromium, via Playwright).

Le navigateur est téléchargé une seule fois (environ 150 Mo) dans le dossier de données, au premier export.
Variable DEMO_CHROMIUM : chemin d'un Chromium déjà installé (développement, tests).
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from demo_express.langue import _

ORDINATEUR = {"width": 1280, "height": 800}
TELEPHONE = {"width": 390, "height": 844}
MARQUEUR = ".chromium-installe"


class ErreurCapture(RuntimeError):
    pass


@dataclass
class Captures:
    ordinateur: bytes  # PNG, page entière en 1280 px de large
    telephone: bytes  # PNG, page entière en 390 px de large (densité 2, net sur téléphone)
    pdf: bytes  # une seule longue page, comme le site à l'écran


def dossier_navigateurs(dossier_donnees: Path) -> Path:
    return dossier_donnees / "navigateurs"


def preparer(dossier_donnees: Path) -> None:
    """Indique à Playwright où ranger et chercher le navigateur intégré."""
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(dossier_navigateurs(dossier_donnees)))


def chromium_installe(dossier_donnees: Path) -> bool:
    return bool(os.environ.get("DEMO_CHROMIUM")) or (dossier_navigateurs(dossier_donnees) / MARQUEUR).exists()


def installer_chromium(dossier_donnees: Path) -> None:
    """Téléchargement du navigateur intégré par le pilote Playwright embarqué (comme Chasseur de sites)."""
    from playwright._impl._driver import compute_driver_executable, get_driver_env

    preparer(dossier_donnees)
    pilote = compute_driver_executable()
    commande = [*pilote, "install", "chromium"] if isinstance(pilote, (tuple, list)) else [str(pilote), "install", "chromium"]
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    resultat = subprocess.run(commande, env={**os.environ, **get_driver_env()}, check=False, capture_output=True, **options)
    if resultat.returncode != 0:
        raise ErreurCapture(_("Téléchargement du navigateur intégré impossible : vérifiez votre connexion et réessayez."))
    marqueur = dossier_navigateurs(dossier_donnees) / MARQUEUR
    marqueur.parent.mkdir(parents=True, exist_ok=True)
    marqueur.touch()


async def capturer(html: str, dossier_donnees: Path) -> Captures:
    from playwright.async_api import Error as ErreurPlaywright
    from playwright.async_api import async_playwright

    preparer(dossier_donnees)
    if not chromium_installe(dossier_donnees):
        await asyncio.to_thread(installer_chromium, dossier_donnees)  # une seule fois, sans bloquer l'application
    try:
        async with async_playwright() as p:
            options = {"executable_path": os.environ["DEMO_CHROMIUM"]} if os.environ.get("DEMO_CHROMIUM") else {}
            navigateur = await p.chromium.launch(**options)
            try:
                async def page(viewport: dict, echelle: float):
                    onglet = await navigateur.new_page(viewport=viewport, device_scale_factor=echelle)
                    await onglet.set_content(html, wait_until="load")
                    try:  # polices de caractères (Google Fonts) : on attend qu'elles soient prêtes, sans bloquer hors ligne
                        await onglet.wait_for_load_state("networkidle", timeout=8000)
                        await onglet.evaluate("document.fonts.ready.then(() => true)")
                    except ErreurPlaywright:
                        pass
                    return onglet

                ordi = await page(ORDINATEUR, 1)
                image_ordinateur = await ordi.screenshot(full_page=True, type="png")
                await ordi.emulate_media(media="screen")  # le PDF garde l'apparence écran (couleurs, bandeau)
                hauteur = await ordi.evaluate("document.documentElement.scrollHeight")
                pdf = await ordi.pdf(width=f"{ORDINATEUR['width']}px", height=f"{hauteur + 2}px", print_background=True,
                                     margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
                tel = await page(TELEPHONE, 2)
                image_telephone = await tel.screenshot(full_page=True, type="png")
            finally:
                await navigateur.close()
    except ErreurPlaywright as e:
        raise ErreurCapture(_("Le navigateur intégré n'a pas pu fabriquer les fichiers ({erreur}).").format(erreur=str(e).splitlines()[0])) from None
    return Captures(ordinateur=image_ordinateur, telephone=image_telephone, pdf=pdf)
