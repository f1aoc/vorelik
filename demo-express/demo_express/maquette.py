"""Fabrication de la maquette HTML d'une entreprise à partir de sa fiche Google et de sa famille de métier.

Chaque famille a sa propre mise en page (templates/maquette/<code>.html, sur la base commune _base.html) et
son ordre de sections. Les retouches de l'utilisateur (Options) remplacent les valeurs par défaut.

Deux usages, selon les règles de Google Maps Platform (pas d'export du contenu Google hors de l'application) :
  - aperçu dans l'application : fiche Google en direct, avec les crédits exigés ;
  - export (images, PDF, page web envoyés au prospect) : aucun contenu Google. Seules les informations
    d'identité vérifiées par le vendeur (Identite), ses propres textes et des photos utilisables y figurent :
    photos importées par le vendeur, sinon photos d'illustration libres de droits (photos.py). Les avis sont
    remplacés par un emplacement « Vos avis clients ».
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from demo_express import photos as phototheque
from demo_express.familles import FAMILLES, Famille, famille_de
from demo_express.langue import MOIS, langue_courante, nombre
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
        "photo_de_debut": "Photo : ",
        "voir_sur": "Voir sur",
        "avis": "avis",
        "credits": "Informations, photos et avis :",
        "credits_export": "Maquette à compléter avec vos photos, vos avis et vos horaires",
        "illustrations": "Photos d'illustration",
        "illustration": "Photo d'illustration",
        "realise": "Maquette réalisée avec Démo Express",
        "horaires_absents": "Horaires communiqués sur demande.",
        "selection_avis": "3 avis avec commentaire, parmi les plus pertinents selon",
        "verification_avis": "Les avis ne sont pas vérifiés par Google Maps, qui recherche et supprime les faux contenus.",
        "traduit": "Traduit par Google",
        "visite": "Visite : {mois} {annee}",
        "vos_photos": "Vos photos ici",
        "vos_avis": "Les avis de vos clients s'afficheront ici.",
        "vos_horaires": "Vos horaires d'ouverture",
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
        "photo_de_debut": "Photo: ",
        "voir_sur": "View on",
        "avis": "reviews",
        "credits": "Information, photos and reviews:",
        "credits_export": "Mockup to be completed with your photos, reviews and opening hours",
        "illustrations": "Illustrative photos",
        "illustration": "Illustrative photo",
        "realise": "Mockup made with Démo Express",
        "horaires_absents": "Opening hours available on request.",
        "selection_avis": "3 reviews with comments, among the most relevant according to",
        "verification_avis": "Reviews are not verified by Google Maps, which checks for and removes fake content.",
        "traduit": "Translated by Google",
        "visite": "Visited {mois} {annee}",
        "vos_photos": "Your photos here",
        "vos_avis": "Your customers' reviews will appear here.",
        "vos_horaires": "Your opening hours",
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


@dataclass
class Identite:
    """Informations de l'entreprise pour l'export, vérifiées (ou tapées) par le vendeur."""
    nom: str
    metier: str = ""
    ville: str = ""
    telephone: str = ""
    adresse: str = ""  # adresse complète (rue, code postal, ville)

    def nettoyer(self) -> "Identite":
        self.nom, self.metier, self.ville = (x.strip()[:80] for x in (self.nom, self.metier, self.ville))
        self.adresse = " ".join(self.adresse.split())[:160]
        self.telephone = "".join(c for c in self.telephone if c.isdigit() or c in "+ .()-")[:30].strip()
        return self


NOMBRE_EMPLACEMENTS = 8  # photos de la maquette, au plus


def fiche_export(fiche: Fiche, identite: Identite) -> Fiche:
    """Fiche sans aucun contenu Google : identité vérifiée par le vendeur, le reste vide."""
    return replace(
        fiche, nom=identite.nom, metier=identite.metier, ville=identite.ville,
        adresse=identite.adresse or identite.ville, adresse_courte=identite.ville, telephone=identite.telephone, telephone_international="", horaires=[],
        note=None, nombre_avis=0, avis=[], photos=[], lien_maps="", site="",
    )


def visite(date: tuple[int, int]) -> str:
    """(2026, 3) → « Visite : mars 2026 » (exigé par Google pour les avis de lieux en France)."""
    langue = langue_courante()
    annee, mois = date
    return TEXTES[langue]["visite"].format(mois=MOIS[langue][mois - 1], annee=annee)


def _environnement() -> Environment:
    return Environment(loader=FileSystemLoader(GABARITS), autoescape=select_autoescape(["html"]))


def famille_retenue(fiche: Fiche, options: Options | None = None) -> Famille:
    if options and options.modele in FAMILLES:
        return FAMILLES[options.modele]
    return famille_de(fiche.type_principal, fiche.types, fiche.metier)


def illustrations(fiche: Fiche, famille: Famille) -> list:
    """Photos d'illustration du métier (garage, fleuriste, immobilier…), sinon celles de la famille."""
    theme = phototheque.theme_de(fiche.type_principal, fiche.types, fiche.metier)
    return phototheque.bibliotheque(theme) or phototheque.bibliotheque(famille.code)


def photos_proposees(fiche: Fiche, famille: Famille, importees: list | None = None) -> list:
    """Toutes les photos que le vendeur peut choisir : importées, Google (aperçu seulement), illustrations."""
    return [*(importees or []), *fiche.photos, *illustrations(fiche, famille)]


def photos_retenues(fiche: Fiche, options: Options, famille: Famille, importees: list | None, export: bool) -> list:
    """Photos de la maquette, dans l'ordre (la première sert de grande photo d'accueil).

    Par défaut : photos importées puis photos Google ; sans aucune photo, les illustrations du métier.
    Export : chaque photo Google est remplacée par une illustration du métier (ou un emplacement « Vos photos
    ici » s'il n'en reste plus) ; par défaut, photos importées puis illustrations.
    """
    importees = importees or []
    biblio = illustrations(fiche, famille)
    if options.photos is None:
        choisies = [*importees, *([] if export else fiche.photos)] or biblio
        if export:  # photothèque vide (ou absente) : emplacements « Vos photos ici »
            choisies = [*choisies, *(b for b in biblio if b not in choisies)] or [None] * NOMBRE_EMPLACEMENTS
    else:
        par_nom = {p.nom: p for p in [*importees, *fiche.photos]}
        choisies = [p for p in (par_nom.get(n) or phototheque.photo_bibliotheque(n) for n in options.photos) if p]
    choisies = choisies[:NOMBRE_EMPLACEMENTS]
    if export:
        reserve = [b for b in biblio if b not in choisies]
        choisies = [p if p is not None and getattr(p, "libre", False) else (reserve.pop(0) if reserve else None) for p in choisies]
    return choisies


def contexte(fiche: Fiche, options: Options | None = None, url_photo: Callable[..., str] = url_photo_apercu,
             identite: Identite | None = None, importees: list | None = None) -> dict:
    """identite donnée : contexte d'export (aucun contenu Google), sinon aperçu en direct.
    importees : photos importées par le vendeur pour cette entreprise (photos.PhotoLibre)."""
    options = (options or Options()).nettoyer()
    langue = langue_courante()
    famille = famille_retenue(fiche, options)
    export = identite is not None
    photos = photos_retenues(fiche, options, famille, importees, export)
    avec_avis = bool(fiche.avis)
    if export:
        fiche = fiche_export(fiche, identite.nettoyer())
        avec_avis = True
    valeurs = {"nom": fiche.nom, "ville": fiche.ville or fiche.adresse_courte, "metier": fiche.metier}
    visibles = SECTIONS if options.sections is None else options.sections
    sections = [s for s in ORDRES[famille.code] if s in visibles]
    if not avec_avis and "avis" in sections:
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
        "export": export,
        "visite": visite,
        "presentation": options.presentation or famille.presentation[langue].format(**valeurs),
        "services": options.services if options.services is not None else famille.services[langue],
        "action": options.action or famille.action[langue],
        "atouts": famille.atouts[langue],
        "couleur": options.couleur or famille.couleur,
        "photos": photos,
        "illustrations": any(getattr(p, "illustration", False) for p in photos),
        "sections": sections,
        "url_photo": url_photo,
        "note": nombre(f"{fiche.note:.1f}") if fiche.note else "",
        "etoiles": round(fiche.note or 0),
        "telephone_lien": telephone_lien if len(telephone_lien) > 6 else "",
        "police": quote(famille.police_titres).replace("%20", "+"),
    }


def rendre(fiche: Fiche, options: Options | None = None, url_photo: Callable[..., str] = url_photo_apercu,
           identite: Identite | None = None, importees: list | None = None) -> str:
    ctx = contexte(fiche, options, url_photo, identite, importees)
    return _environnement().get_template(f"maquette/{ctx['famille'].code}.html").render(**ctx)
