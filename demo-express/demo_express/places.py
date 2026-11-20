"""Fiche Google d'une entreprise, via l'API officielle Google Places (API « New »), avec la clé du client.

Aucun scraping de Google Maps : uniquement l'API. Les données restent en mémoire, le temps de la démo.
  rechercher(cle, texte)  → entreprises correspondant à « nom + ville » ou à un lien Google Maps
  details(cle, id)        → la fiche complète (horaires, avis, photos…)
  photo(cle, nom)         → l'image d'une photo de la fiche
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit

import httpx

from demo_express.langue import _, langue_courante

RECHERCHE = "https://places.googleapis.com/v1/places:searchText"
FICHE = "https://places.googleapis.com/v1/places/{id}"
MEDIA = "https://places.googleapis.com/v1/{nom}/media"
CHAMPS_RECHERCHE = [
    "places.id", "places.displayName", "places.formattedAddress", "places.primaryTypeDisplayName",
    "places.rating", "places.userRatingCount", "places.websiteUri", "places.businessStatus", "places.primaryType",
    "places.types",
]
# Résultat qui n'est qu'une adresse (pas une fiche d'entreprise) : Google le renvoie quand la recherche
# contient une adresse complète (« Delphine Fleurs 22 Route Nationale 7, 13670 Saint-Andiol »)
TYPES_ADRESSE = {"street_address", "premise", "subpremise", "route", "geocode", "intersection", "plus_code",
                 "postal_code", "street_number"}
CHAMPS_FICHE = [
    "id", "displayName", "formattedAddress", "shortFormattedAddress", "addressComponents", "nationalPhoneNumber",
    "internationalPhoneNumber", "regularOpeningHours.weekdayDescriptions", "rating", "userRatingCount", "reviews",
    "photos", "primaryType", "primaryTypeDisplayName", "types", "googleMapsUri", "websiteUri", "businessStatus",
]
MAX_PHOTOS = 10
MAX_AVIS = 5
MESSAGES_ERREURS = {
    400: "Requête refusée par Google : vérifiez le nom et la ville saisis.",
    401: "Clé API Google Places refusée : vérifiez-la dans les Réglages.",
    403: "Accès refusé : activez « Places API (New) » dans Google Cloud et vérifiez les restrictions de la clé.",
    404: "Entreprise introuvable sur Google : relancez la recherche.",
    429: "Quota Google Places dépassé : réessayez plus tard ou augmentez le quota dans Google Cloud.",
}
LIENS_COURTS = ("maps.app.goo.gl", "goo.gl")


class ErreurPlaces(RuntimeError):
    pass


@dataclass
class Candidat:
    id: str
    nom: str
    adresse: str
    metier: str
    note: float | None = None
    nombre_avis: int = 0
    site: str = ""
    fermee: bool = False
    adresse_seule: bool = False  # simple adresse, sans fiche d'entreprise


def est_adresse_seule(fiche: "Fiche") -> bool:
    """Fiche d'une simple adresse (aucun métier), pas d'une entreprise."""
    return not fiche.type_principal and not fiche.metier and any(t in TYPES_ADRESSE for t in fiche.types)


PAYS = {"france", "belgique", "belgium", "suisse", "switzerland", "luxembourg", "canada", "usa", "us",
        "united states", "united states of america", "uk", "united kingdom", "england", "ireland", "australia",
        "new zealand"}


def sans_adresse(texte: str) -> str:
    """Nom + ville, sans numéro ni rue :
    « Delphine Fleurs 22 Route Nationale 7, 13670 Saint-Andiol » → « Delphine Fleurs Saint-Andiol » ;
    « Rose Florist 22 Main Street, Springfield, IL 62701 » → « Rose Florist Springfield »."""
    if not re.search(r"\d", texte):
        return ""
    nom = re.split(r"\d", texte, maxsplit=1)[0].strip(" ,-–")
    ville = ""
    for morceau in reversed(texte.split(",")[1:]):  # la ville : dernier morceau qui n'est ni pays, ni état, ni code
        mots = [m for m in morceau.split() if not re.search(r"\d", m)]
        candidat = " ".join(mots).strip(" -–")
        if len(candidat) > 2 and candidat.lower() not in PAYS:
            ville = candidat
            break
    return f"{nom} {ville}".strip() if nom else ""


@dataclass
class Auteur:
    """Auteur d'une photo ou d'un avis, à créditer (règles Google : avatar, nom et lien du profil)."""
    nom: str
    lien: str = ""
    avatar: str = ""


@dataclass
class Avis:
    auteur: Auteur
    note: int
    texte: str
    quand: str  # date relative fournie par Google (« il y a une semaine »)
    lien_google: str = ""  # l'avis sur Google Maps
    visite: tuple[int, int] | None = None  # (année, mois) de la visite : à afficher pour les lieux en France
    traduit: bool = False


@dataclass
class Photo:
    nom: str  # identifiant Google de la photo (places/…/photos/…)
    largeur: int
    hauteur: int
    auteurs: list[Auteur] = field(default_factory=list)
    lien_google: str = ""  # la photo sur Google Maps


@dataclass
class Fiche:
    id: str
    nom: str
    adresse: str
    adresse_courte: str
    ville: str
    telephone: str
    telephone_international: str
    horaires: list[str]
    note: float | None
    nombre_avis: int
    avis: list[Avis]
    photos: list[Photo]
    type_principal: str
    types: list[str]
    metier: str
    lien_maps: str
    site: str
    pays: str = ""  # code pays (FR…), d'après l'adresse
    indice: str = ""  # recherche du vendeur (« fleuriste Saint-Andiol ») : métier deviné si la fiche n'en a pas


def langue_api() -> dict:
    """Résultats dans la langue de l'interface ; recherche centrée sur la France en français."""
    return {"languageCode": "fr", "regionCode": "FR"} if langue_courante() == "fr" else {"languageCode": "en"}


def _erreur(r: httpx.Response) -> ErreurPlaces:
    if r.status_code in MESSAGES_ERREURS:
        return ErreurPlaces(_(MESSAGES_ERREURS[r.status_code]))
    return ErreurPlaces(_("Erreur Google Places (HTTP {code}).").format(code=r.status_code))


def _exiger_cle(cle: str) -> None:
    if not cle:
        raise ErreurPlaces(_("Aucune clé Google Places : ajoutez-la dans les Réglages."))


async def _envoyer(http: httpx.AsyncClient, methode: str, url: str, **options) -> httpx.Response:
    try:
        return await http.request(methode, url, **options)
    except httpx.HTTPError as e:
        raise ErreurPlaces(_("Google Places injoignable ({erreur}) : vérifiez votre connexion.").format(erreur=type(e).__name__)) from None


# --- Lien Google Maps → texte à rechercher -----------------------------------------------------------------

def texte_depuis_lien(lien: str) -> str:
    """« https://www.google.com/maps/place/Boulangerie+Martin/@45.7,4.8,17z/… » → « Boulangerie Martin ».

    Renvoie "" si le lien ne contient pas de nom (lien court à résoudre d'abord, ou autre page)."""
    morceaux = urlsplit(lien.strip())
    m = re.search(r"/maps/place/([^/@]+)", morceaux.path)
    if m:
        return unquote(m.group(1).replace("+", " ")).strip()
    m = re.search(r"(?:^|&)q=([^&]+)", morceaux.query)
    if m and "maps" in (morceaux.netloc + morceaux.path):
        return unquote(m.group(1).replace("+", " ")).strip()
    return ""


async def resoudre_lien(lien: str, http: httpx.AsyncClient) -> str:
    """Lien court partagé depuis l'application Google Maps (maps.app.goo.gl/…) → lien complet."""
    if urlsplit(lien).netloc not in LIENS_COURTS:
        return lien
    try:
        r = await http.head(lien, follow_redirects=True, timeout=10)
        return str(r.url)
    except httpx.HTTPError:
        return lien


def est_un_lien(texte: str) -> bool:
    return texte.strip().lower().startswith(("http://", "https://", "maps.app.goo.gl", "www.google."))


# --- Recherche -----------------------------------------------------------------------------------------------

async def rechercher(cle: str, texte: str, client: httpx.AsyncClient | None = None) -> list[Candidat]:
    """Entreprises correspondant à « nom + ville » ou à un lien Google Maps (10 au plus)."""
    _exiger_cle(cle)
    texte = texte.strip()
    if not texte:
        raise ErreurPlaces(_("Indiquez le nom de l'entreprise et sa ville, ou collez son lien Google Maps."))
    http = client or httpx.AsyncClient(timeout=20)
    try:
        if est_un_lien(texte):
            lien = texte if texte.lower().startswith("http") else "https://" + texte
            texte = texte_depuis_lien(await resoudre_lien(lien, http))
            if not texte:
                raise ErreurPlaces(_("Ce lien ne permet pas de retrouver l'entreprise : tapez plutôt son nom et sa ville."))
        resultats = await _chercher(cle, texte, http)
        if all(c.adresse_seule for c in resultats) and (simple := sans_adresse(texte)) and simple != texte:
            # Seulement des adresses : nouvelle recherche sans le numéro et la rue (nom + ville)
            vus = {c.id for c in resultats}
            entreprises = [c for c in await _chercher(cle, simple, http) if c.id not in vus]
            resultats = [*(c for c in entreprises if not c.adresse_seule), *resultats,
                         *(c for c in entreprises if c.adresse_seule)]
        # Entreprises d'abord, simples adresses ensuite
        return sorted(resultats, key=lambda c: c.adresse_seule)
    finally:
        if client is None:
            await http.aclose()


async def _chercher(cle: str, texte: str, http: httpx.AsyncClient) -> list[Candidat]:
    corps = {"textQuery": texte, "pageSize": 10, **langue_api()}
    entetes = {"X-Goog-Api-Key": cle, "X-Goog-FieldMask": ",".join(CHAMPS_RECHERCHE)}
    r = await _envoyer(http, "POST", RECHERCHE, json=corps, headers=entetes)
    if r.status_code != 200:
        raise _erreur(r)
    return [
        Candidat(
            id=p["id"],
            nom=p.get("displayName", {}).get("text", ""),
            adresse=p.get("formattedAddress", ""),
            metier=p.get("primaryTypeDisplayName", {}).get("text", ""),
            note=p.get("rating"),
            nombre_avis=p.get("userRatingCount", 0),
            site=p.get("websiteUri", ""),
            fermee=p.get("businessStatus", "OPERATIONAL") != "OPERATIONAL",
            adresse_seule=not p.get("primaryType") and not p.get("primaryTypeDisplayName")
            and any(t in TYPES_ADRESSE for t in p.get("types", [])),
        )
        for p in r.json().get("places", [])
        if p.get("id")
    ]


# --- Fiche complète ------------------------------------------------------------------------------------------

def _ville(composants: list[dict], adresse: str) -> str:
    for c in composants or []:
        if "locality" in c.get("types", []):
            return c.get("longText") or c.get("shortText") or ""
    # « 12 rue X, 69001 Lyon, France » → « Lyon »
    morceaux = [m.strip() for m in adresse.split(",")]
    if len(morceaux) >= 2:
        return re.sub(r"^\d{4,5}\s*", "", morceaux[-2]).strip()
    return ""


def _auteur(a: dict) -> Auteur:
    return Auteur(nom=a.get("displayName", ""), lien=a.get("uri", ""), avatar=a.get("photoUri", ""))


def _pays(composants: list[dict]) -> str:
    for c in composants or []:
        if "country" in c.get("types", []):
            return (c.get("shortText") or "").upper()
    return ""


def _visite(a: dict) -> tuple[int, int] | None:
    v = a.get("visitDate") or {}
    return (int(v["year"]), int(v["month"])) if v.get("year") and v.get("month") else None


def vers_fiche(p: dict) -> Fiche:
    avis = []
    for a in p.get("reviews", []):
        texte, original = a.get("text") or {}, a.get("originalText") or {}
        avis.append(Avis(
            auteur=_auteur(a.get("authorAttribution", {})),
            note=int(a.get("rating") or 0),
            texte=(texte or original).get("text", "").strip(),
            quand=a.get("relativePublishTimeDescription", ""),
            lien_google=a.get("googleMapsUri", ""),
            visite=_visite(a),
            traduit=bool(texte and original and texte.get("languageCode") != original.get("languageCode")),
        ))
    photos = [
        Photo(
            nom=ph["name"],
            largeur=int(ph.get("widthPx") or 0),
            hauteur=int(ph.get("heightPx") or 0),
            auteurs=[_auteur(x) for x in ph.get("authorAttributions", [])],
            lien_google=ph.get("googleMapsUri", ""),
        )
        for ph in p.get("photos", [])
        if ph.get("name")
    ]
    adresse = p.get("formattedAddress", "")
    return Fiche(
        id=p.get("id", ""),
        nom=p.get("displayName", {}).get("text", ""),
        adresse=adresse,
        adresse_courte=p.get("shortFormattedAddress", "") or adresse,
        ville=_ville(p.get("addressComponents", []), adresse),
        telephone=p.get("nationalPhoneNumber", ""),
        telephone_international=p.get("internationalPhoneNumber", ""),
        horaires=p.get("regularOpeningHours", {}).get("weekdayDescriptions", []),
        note=p.get("rating"),
        nombre_avis=int(p.get("userRatingCount") or 0),
        # Ordre de Google (pertinence), avis avec commentaire seulement : la maquette l'indique (règles Google)
        avis=[a for a in avis if a.texte][:MAX_AVIS],
        photos=photos[:MAX_PHOTOS],
        type_principal=p.get("primaryType", ""),
        types=p.get("types", []),
        metier=p.get("primaryTypeDisplayName", {}).get("text", ""),
        lien_maps=p.get("googleMapsUri", ""),
        site=p.get("websiteUri", ""),
        pays=_pays(p.get("addressComponents", [])),
    )


async def details(cle: str, place_id: str, client: httpx.AsyncClient | None = None) -> Fiche:
    _exiger_cle(cle)
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,300}", place_id or ""):
        raise ErreurPlaces(_("Entreprise introuvable sur Google : relancez la recherche."))
    http = client or httpx.AsyncClient(timeout=20)
    try:
        entetes = {"X-Goog-Api-Key": cle, "X-Goog-FieldMask": ",".join(CHAMPS_FICHE)}
        r = await _envoyer(http, "GET", FICHE.format(id=place_id), params=langue_api(), headers=entetes)
        if r.status_code != 200:
            raise _erreur(r)
        return vers_fiche(r.json())
    finally:
        if client is None:
            await http.aclose()


async def photo(cle: str, nom: str, largeur: int = 1600, client: httpx.AsyncClient | None = None) -> tuple[bytes, str]:
    """Image d'une photo de la fiche : (octets, type MIME)."""
    _exiger_cle(cle)
    if not re.fullmatch(r"places/[A-Za-z0-9_-]+/photos/[A-Za-z0-9_-]+", nom or ""):
        raise ErreurPlaces(_("Photo introuvable."))
    http = client or httpx.AsyncClient(timeout=30)
    try:
        r = await _envoyer(
            http, "GET", MEDIA.format(nom=nom), params={"maxWidthPx": max(200, min(largeur, 4800))},
            headers={"X-Goog-Api-Key": cle}, follow_redirects=True,
        )
        if r.status_code != 200:
            raise _erreur(r)
        return r.content, r.headers.get("content-type", "image/jpeg").split(";")[0]
    finally:
        if client is None:
            await http.aclose()
