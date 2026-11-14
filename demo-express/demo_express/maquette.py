"""Fabrication de la maquette HTML d'une entreprise à partir de sa fiche Google et de sa famille de métier.

Chaque famille a sa propre mise en page (templates/maquette/<code>.html, sur la base commune _base.html) et
son ordre de sections. Les retouches de l'utilisateur (Options) remplacent les valeurs par défaut.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from demo_express.familles import FAMILLES, Famille, famille_de
from demo_express.langue import langue_courante, nombre
from demo_express.places import Fiche

GABARITS = Path(__file__).parent / "templates"
SECTIONS = ("a_propos", "services", "galerie", "avis", "infos")
# Ordre des sections de chaque mise en page (le bandeau de tête est toujours en premier)
ORDRES = {
    "restaurant": ("a_propos", "galerie", "services", "avis", "infos"),
    "bouche": ("a_propos", "services", "galerie", "avis", "infos"),
    "beaute": ("galerie", "a_propos", "services", "avis", "infos"),
    "batiment": ("services", "a_propos", "avis", "galerie", "infos"),
    "sante": ("infos", "a_propos", "services", "avis", "galerie"),
    "services": ("a_propos", "services", "avis", "galerie", "infos"),
}
COULEUR = re.compile(r"#[0-9a-fA-F]{6}")
LONGUEURS = {"accroche": 120, "presentation": 900, "action": 40, "titre_service": 60, "texte_service": 220}

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
        "besoin": "Un projet, une question ?",
        "besoin_texte": "Appelez-nous : nous vous répondons rapidement.",
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
        "besoin": "A project or a question?",
        "besoin_texte": "Give us a call: we'll get back to you quickly.",
    },
}


def url_photo_apercu(nom: str, largeur: int = 1600) -> str:
    """Photo servie par l'application (relais vers Google avec la clé du client, jamais enregistrée)."""
    return f"/photo?nom={quote(nom, safe='')}&largeur={largeur}"


@dataclass
class Options:
    """Retouches de l'utilisateur. None ou vide = valeur par défaut (famille de métier, fiche Google)."""
    modele: str = ""  # code de famille ; vide = d'après le métier
    accroche: str = ""
    presentation: str = ""
    couleur: str = ""
    action: str = ""
    services: list[tuple[str, str]] | None = None
    photos: list[str] | None = None  # noms des photos retenues, dans l'ordre ; None = toutes, [] = aucune
    sections: list[str] | None = None  # sections affichées ; None = toutes

    def nettoyer(self) -> "Options":
        """Valeurs sûres : couleur au format #RRGGBB (insérée dans le CSS), modèle et sections connus, textes bornés."""
        self.modele = self.modele if self.modele in FAMILLES else ""
        self.couleur = self.couleur if COULEUR.fullmatch(self.couleur or "") else ""
        self.accroche = (self.accroche or "").strip()[: LONGUEURS["accroche"]]
        self.presentation = (self.presentation or "").strip()[: LONGUEURS["presentation"]]
        self.action = (self.action or "").strip()[: LONGUEURS["action"]]
        if self.services is not None:
            self.services = [(t.strip()[: LONGUEURS["titre_service"]], x.strip()[: LONGUEURS["texte_service"]])
                             for t, x in self.services if t.strip()][:6]
        if self.sections is not None:
            self.sections = [s for s in self.sections if s in SECTIONS]
        if self.photos is not None:
            self.photos = list(dict.fromkeys(self.photos))[:20]
        return self


def _environnement() -> Environment:
    return Environment(loader=FileSystemLoader(GABARITS), autoescape=select_autoescape(["html"]))


def famille_retenue(fiche: Fiche, options: Options | None = None) -> Famille:
    if options and options.modele in FAMILLES:
        return FAMILLES[options.modele]
    return famille_de(fiche.type_principal, fiche.types, fiche.metier)


def contexte(fiche: Fiche, options: Options | None = None, url_photo: Callable[..., str] = url_photo_apercu) -> dict:
    options = (options or Options()).nettoyer()
    langue = langue_courante()
    famille = famille_retenue(fiche, options)
    valeurs = {"nom": fiche.nom, "ville": fiche.ville or fiche.adresse_courte, "metier": fiche.metier}
    photos = fiche.photos
    if options.photos is not None:
        par_nom = {p.nom: p for p in fiche.photos}
        photos = [par_nom[n] for n in options.photos if n in par_nom]
    visibles = SECTIONS if options.sections is None else options.sections
    sections = [s for s in ORDRES[famille.code] if s in visibles]
    if not fiche.avis and "avis" in sections:
        sections.remove("avis")
    if len(photos) < 3 and "galerie" in sections:
        sections.remove("galerie")
    telephone_lien = "tel:" + "".join(c for c in (fiche.telephone_international or fiche.telephone) if c.isdigit() or c == "+")
    return {
        "fiche": fiche,
        "famille": famille,
        "langue": langue,
        "t": TEXTES[langue],
        "accroche": options.accroche or famille.accroche[langue],
        # Le résumé Google n'est pas un modèle : jamais passé à format() (accolades possibles)
        "presentation": options.presentation or fiche.resume or famille.presentation[langue].format(**valeurs),
        "services": options.services if options.services is not None else famille.services[langue],
        "action": options.action or famille.action[langue],
        "atouts": famille.atouts[langue],
        "couleur": options.couleur or famille.couleur,
        "photos": photos,
        "sections": sections,
        "url_photo": url_photo,
        "note": nombre(f"{fiche.note:.1f}") if fiche.note else "",
        "etoiles": round(fiche.note or 0),
        "telephone_lien": telephone_lien if len(telephone_lien) > 6 else "",
        "police": quote(famille.police_titres).replace("%20", "+"),
    }


def rendre(fiche: Fiche, options: Options | None = None, url_photo: Callable[..., str] = url_photo_apercu) -> str:
    ctx = contexte(fiche, options, url_photo)
    return _environnement().get_template(f"maquette/{ctx['famille'].code}.html").render(**ctx)
