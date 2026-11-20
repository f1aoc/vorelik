"""Photos utilisables dans les fichiers envoyés au prospect (contrairement aux photos Google) :

  - photothèque intégrée : photos libres de droits (CC0, StockSnap via Openverse), par famille
    de métier, livrées avec l'application (dossier photos/, crédits et licences dans photos/catalogue.json).
    Marquées « Photos d'illustration » dans la maquette ;
  - photos importées par le vendeur (les siennes ou celles fournies par l'entreprise) : gardées en mémoire le
    temps de la session, réduites à 1600 px et réenregistrées en JPEG (ce qui retire les métadonnées EXIF,
    position GPS comprise).

Noms : « biblio/<famille>/<fichier> » et « import/<identifiant> ». Les photos Google gardent le nom donné par
Google (« places/… »).
"""

from __future__ import annotations

import base64
import io
import json
import secrets
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DOSSIER = Path(__file__).parent / "photos"
BIBLIO, IMPORT = "biblio/", "import/"
TAILLE_MAX = 15 * 1024 * 1024  # fichier envoyé par le vendeur
LARGEUR_MAX = 1600
MAX_IMPORTS = 12  # par entreprise
SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"RIFF")  # JPEG, PNG, WebP (RIFF....WEBP)


class ErreurImport(Exception):
    pass


@dataclass(frozen=True)
class PhotoLibre:
    """Même interface que places.Photo pour les gabarits (nom, auteurs, lien_google)."""
    nom: str
    largeur: int
    hauteur: int
    illustration: bool  # photothèque : mention « Photos d'illustration »
    libre: bool = True  # utilisable dans les fichiers envoyés
    auteurs: tuple = ()
    lien_google: str = ""


@dataclass(frozen=True)
class Entree:
    """Ligne du catalogue de la photothèque (source et licence de chaque photo)."""
    fichier: str
    famille: str
    largeur: int
    hauteur: int
    titre: str
    source: str
    auteur: str
    licence: str


@lru_cache(maxsize=1)
def catalogue() -> dict[str, Entree]:
    chemin = DOSSIER / "catalogue.json"
    if not chemin.exists():
        return {}
    lignes = json.loads(chemin.read_text(encoding="utf-8"))
    return {f"{BIBLIO}{x['famille']}/{x['fichier']}": Entree(**x) for x in lignes}


# Thèmes de photos propres à certains métiers (la mise en page reste celle de la famille). Sans thème
# particulier, les photos sont celles de la famille de métier.
THEMES_TYPES = {
    "garage": "car_repair car_wash car_dealer auto_parts_store tire_shop",
    "fleuriste": "florist",
    "immobilier": "real_estate_agency",
}
THEMES_MOTS = {
    "garage": ("garage", "mécani", "carross", "automobile", "pneu", "auto ", "car repair", "mechanic", "body shop"),
    "fleuriste": ("fleur", "florist", "flower"),
    "immobilier": ("immobili", "real estate", "realtor", "estate agent"),
}


NOMS_THEMES = {
    "garage": {"fr": "Garages et automobile", "en": "Garages and cars"},
    "fleuriste": {"fr": "Fleuristes", "en": "Florists"},
    "immobilier": {"fr": "Immobilier", "en": "Real estate"},
}


def theme_de(type_principal: str, types: list[str] | None = None, metier: str = "", indice: str = "") -> str:
    """Thème de photos d'un métier (« garage », « fleuriste », « immobilier ») ; "" si aucun."""
    for t in [type_principal, *(types or [])]:
        for theme, liste in THEMES_TYPES.items():
            if t in liste.split():
                return theme
    from demo_express.familles import TYPES
    connus = set(TYPES) | {t for liste in THEMES_TYPES.values() for t in liste.split()}
    muette = not metier and not any(t in connus for t in [type_principal, *(types or [])])
    for libelle in (metier, indice if muette else ""):  # indice : recherche du vendeur, si la fiche est muette
        libelle = f"{libelle.lower()} "
        for theme, mots in THEMES_MOTS.items():
            if libelle.strip() and any(m in libelle for m in mots):
                return theme
    return ""


def themes() -> list[str]:
    """Codes des collections de la photothèque (familles et thèmes), dans l'ordre du catalogue."""
    return list(dict.fromkeys(e.famille for e in catalogue().values()))


def bibliotheque(famille: str) -> list[PhotoLibre]:
    """Photos d'illustration d'un thème ou d'une famille de métier, dans l'ordre du catalogue."""
    return [PhotoLibre(nom, e.largeur, e.hauteur, True) for nom, e in catalogue().items() if e.famille == famille]


def photo_bibliotheque(nom: str) -> PhotoLibre | None:
    e = catalogue().get(nom)
    return PhotoLibre(nom, e.largeur, e.hauteur, True) if e else None


def contenu_bibliotheque(nom: str) -> bytes | None:
    """Seuls les noms du catalogue sont servis (pas de chemin arbitraire)."""
    e = catalogue().get(nom)
    if e is None:
        return None
    try:
        return (DOSSIER / e.famille / e.fichier).read_bytes()
    except OSError:
        return None


def preparer_image(donnees: bytes) -> tuple[bytes, int, int]:
    """Photo envoyée par le vendeur → JPEG de 1600 px de large au plus, sans métadonnées."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    if len(donnees) > TAILLE_MAX:
        raise ErreurImport("Photo trop lourde (15 Mo au plus).")
    if not donnees.startswith(SIGNATURES) or (donnees.startswith(b"RIFF") and donnees[8:12] != b"WEBP"):
        raise ErreurImport("Format non reconnu : choisissez une photo JPEG, PNG ou WebP.")
    Image.MAX_IMAGE_PIXELS = 60_000_000
    try:
        with Image.open(io.BytesIO(donnees)) as image:
            if image.format not in ("JPEG", "PNG", "WEBP"):
                raise ErreurImport("Format non reconnu : choisissez une photo JPEG, PNG ou WebP.")
            image = ImageOps.exif_transpose(image)
            if image.mode in ("RGBA", "LA", "P"):
                fond = Image.new("RGB", image.size, (255, 255, 255))
                image = image.convert("RGBA")
                fond.paste(image, mask=image.split()[-1])
                image = fond
            image = image.convert("RGB")
            if image.width > LARGEUR_MAX:
                image = image.resize((LARGEUR_MAX, round(image.height * LARGEUR_MAX / image.width)), Image.LANCZOS)
            sortie = io.BytesIO()
            image.save(sortie, "JPEG", quality=82, optimize=True, progressive=True)
            return sortie.getvalue(), image.width, image.height
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as e:
        raise ErreurImport("Photo illisible : choisissez une photo JPEG, PNG ou WebP.") from e


@dataclass
class Imports:
    """Photos importées par le vendeur, par entreprise, en mémoire (le temps de la session)."""
    entreprises_max: int = 30
    par_entreprise: OrderedDict = field(default_factory=OrderedDict)  # place_id → {nom: PhotoLibre}
    contenus: dict = field(default_factory=dict)  # nom → octets JPEG

    def ajouter(self, place_id: str, donnees: bytes) -> PhotoLibre:
        photos = self.par_entreprise.setdefault(place_id, {})
        self.par_entreprise.move_to_end(place_id)
        if len(photos) >= MAX_IMPORTS:
            raise ErreurImport(f"{MAX_IMPORTS} photos au plus par entreprise : retirez-en une d'abord.")
        jpeg, largeur, hauteur = preparer_image(donnees)
        photo = PhotoLibre(IMPORT + secrets.token_hex(8), largeur, hauteur, False)
        photos[photo.nom] = photo
        self.contenus[photo.nom] = jpeg
        while len(self.par_entreprise) > self.entreprises_max:
            _, anciennes = self.par_entreprise.popitem(last=False)
            for nom in anciennes:
                self.contenus.pop(nom, None)
        return photo

    def liste(self, place_id: str) -> list[PhotoLibre]:
        return list(self.par_entreprise.get(place_id, {}).values())

    def retirer(self, place_id: str, nom: str) -> bool:
        if self.par_entreprise.get(place_id, {}).pop(nom, None) is None:
            return False
        self.contenus.pop(nom, None)
        return True

    def contenu(self, nom: str) -> bytes | None:
        return self.contenus.get(nom)


def type_mime(contenu: bytes) -> str:
    if contenu.startswith(b"\x89PNG"):
        return "image/png"
    if contenu.startswith(b"RIFF"):
        return "image/webp"
    return "image/jpeg"


def uri(contenu: bytes) -> str:
    """Photo intégrée dans la page envoyée (un seul fichier HTML, lisible sans l'application)."""
    return f"data:{type_mime(contenu)};base64," + base64.b64encode(contenu).decode()
