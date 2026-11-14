"""Fabrication de la maquette HTML d'une entreprise à partir de sa fiche Google et de sa famille de métier."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from demo_express.familles import Famille, famille_de
from demo_express.langue import langue_courante, nombre
from demo_express.places import Fiche

GABARITS = Path(__file__).parent / "templates"
MODELE = "maquette/classique.html"

TEXTES = {
    "fr": {
        "bandeau": "Maquette de démonstration — site non publié",
        "appeler": "Appeler",
        "itineraire": "Itinéraire",
        "avis_google": "avis Google",
        "a_propos": "À propos",
        "services": "Nos services",
        "galerie": "En images",
        "temoignages": "Ils nous recommandent",
        "infos": "Horaires et accès",
        "horaires": "Horaires",
        "adresse": "Adresse",
        "telephone": "Téléphone",
        "voir_carte": "Voir sur Google Maps",
        "photo_de": "Photo : {auteur}",
        "credits": "Photos et avis : Google",
        "realise": "Maquette réalisée avec Démo Express",
        "horaires_absents": "Horaires communiqués sur demande.",
        "avis_de": "Avis Google de {auteur}",
    },
    "en": {
        "bandeau": "Demo mockup — website not published",
        "appeler": "Call",
        "itineraire": "Directions",
        "avis_google": "Google reviews",
        "a_propos": "About us",
        "services": "Our services",
        "galerie": "Gallery",
        "temoignages": "What our customers say",
        "infos": "Opening hours and location",
        "horaires": "Opening hours",
        "adresse": "Address",
        "telephone": "Phone",
        "voir_carte": "View on Google Maps",
        "photo_de": "Photo: {auteur}",
        "credits": "Photos and reviews: Google",
        "realise": "Mockup made with Démo Express",
        "horaires_absents": "Opening hours available on request.",
        "avis_de": "Google review by {auteur}",
    },
}


def url_photo_apercu(nom: str, largeur: int = 1600) -> str:
    """Photo servie par l'application (relais vers Google avec la clé du client, jamais enregistrée)."""
    return f"/photo?nom={quote(nom, safe='')}&largeur={largeur}"


@dataclass
class Options:
    """Choix de l'utilisateur (retouches : étape 2). Vide = valeurs de la famille de métier."""
    accroche: str = ""
    presentation: str = ""
    couleur: str = ""
    photos: list[str] = field(default_factory=list)  # noms des photos retenues, dans l'ordre ; vide = toutes


def _environnement() -> Environment:
    return Environment(loader=FileSystemLoader(GABARITS), autoescape=select_autoescape(["html"]))


def contexte(fiche: Fiche, options: Options | None = None, url_photo: Callable[..., str] = url_photo_apercu) -> dict:
    options = options or Options()
    langue = langue_courante()
    famille: Famille = famille_de(fiche.type_principal, fiche.types, fiche.metier)
    valeurs = {"nom": fiche.nom, "ville": fiche.ville or fiche.adresse_courte, "metier": fiche.metier}
    photos = fiche.photos
    if options.photos:
        par_nom = {p.nom: p for p in fiche.photos}
        photos = [par_nom[n] for n in options.photos if n in par_nom]
    telephone_lien = "tel:" + "".join(c for c in (fiche.telephone_international or fiche.telephone) if c.isdigit() or c == "+")
    return {
        "fiche": fiche,
        "famille": famille,
        "langue": langue,
        "t": TEXTES[langue],
        "accroche": options.accroche or famille.accroche[langue],
        # Le résumé Google n'est pas un modèle : jamais passé à format() (accolades possibles)
        "presentation": options.presentation or fiche.resume or famille.presentation[langue].format(**valeurs),
        "services": famille.services[langue],
        "action": famille.action[langue],
        "couleur": options.couleur or famille.couleur,
        "photos": photos,
        "url_photo": url_photo,
        "note": nombre(f"{fiche.note:.1f}") if fiche.note else "",
        "telephone_lien": telephone_lien if len(telephone_lien) > 6 else "",
        "police": quote(famille.police_titres).replace("%20", "+"),
    }


def rendre(fiche: Fiche, options: Options | None = None, url_photo: Callable[..., str] = url_photo_apercu) -> str:
    return _environnement().get_template(MODELE).render(**contexte(fiche, options, url_photo))
