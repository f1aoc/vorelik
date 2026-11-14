"""Interface de Démo Express, dans le navigateur (n'écoute que sur l'ordinateur de l'utilisateur).

  /                 recherche de l'entreprise (nom + ville, ou lien Google Maps)
  /demo/{id}        retouches et aperçu de la maquette, ordinateur et téléphone côte à côte
  /maquette/{id}    la maquette elle-même
  /photo            photos de la fiche, relayées depuis Google avec la clé du client
  /reglages         clé Google Places et langue

Les fiches et photos Google restent en mémoire (le temps de la session), jamais sur le disque.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.middleware.trustedhost import TrustedHostMiddleware

from demo_express import __version__, maquette, places
from demo_express.familles import FAMILLES
from demo_express.langue import AUTO, _, langue_courante
from demo_express.reglages import Reglages
from demo_express.secret import ErreurSecret, masquer

DOSSIER = Path(__file__).parent
HOTES = ["127.0.0.1", "localhost"]


class Memoire(OrderedDict):
    """Petit cache en mémoire, les plus anciens éléments partent en premier."""

    def __init__(self, taille: int):
        super().__init__()
        self.taille = taille

    def garder(self, cle, valeur):
        self[cle] = valeur
        self.move_to_end(cle)
        while len(self) > self.taille:
            self.popitem(last=False)
        return valeur


def creer_app(reglages: Reglages, hotes: list[str] | None = None) -> FastAPI:
    app = FastAPI(title="Démo Express", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hotes or HOTES)
    app.mount("/static", StaticFiles(directory=DOSSIER / "static"), name="static")
    env = Environment(loader=FileSystemLoader(DOSSIER / "templates"), autoescape=select_autoescape(["html"]))
    env.globals.update(_=_, version=__version__)
    fiches: Memoire = Memoire(30)
    retouches: dict[str, maquette.Options] = {}  # par entreprise, le temps de la session
    images: Memoire = Memoire(120)

    def page(nom: str, request: Request, statut: int = 200, **valeurs) -> HTMLResponse:
        html = env.get_template(f"app/{nom}.html").render(request=request, langue=langue_courante(), **valeurs)
        return HTMLResponse(html, status_code=statut)

    def cle() -> str:
        try:
            return reglages.cle_google
        except ErreurSecret:
            return ""

    def meme_origine(request: Request) -> bool:
        """Formulaires : refusés s'ils viennent d'une autre page web que l'application."""
        origine = request.headers.get("origin") or request.headers.get("referer") or ""
        return not origine or urlsplit(origine).netloc == request.headers.get("host", "")

    async def fiche_de(place_id: str) -> places.Fiche:
        if place_id not in fiches:
            fiches.garder(place_id, await places.details(cle(), place_id))
        return fiches[place_id]

    @app.get("/", response_class=HTMLResponse)
    async def accueil(request: Request, q: str = ""):
        candidats, erreur = [], ""
        if q.strip():
            try:
                candidats = await places.rechercher(cle(), q)
                if not candidats:
                    erreur = _("Aucune entreprise trouvée : vérifiez l'orthographe ou ajoutez la ville.")
            except places.ErreurPlaces as e:
                erreur = str(e)
        return page("accueil", request, q=q, candidats=candidats, erreur=erreur, sans_cle=not cle())

    @app.get("/demo/{place_id}", response_class=HTMLResponse)
    async def demo(request: Request, place_id: str):
        try:
            fiche = await fiche_de(place_id)
        except places.ErreurPlaces as e:
            return page("accueil", request, statut=502, q="", candidats=[], erreur=str(e), sans_cle=not cle())
        options = retouches.get(place_id, maquette.Options())
        ctx = maquette.contexte(fiche, options)
        choisies = [p.nom for p in ctx["photos"]]
        # Photos : celles retenues dans leur ordre, puis les autres (décochées)
        photos = [(p, p.nom in choisies) for p in sorted(fiche.photos, key=lambda p: choisies.index(p.nom) if p.nom in choisies else 99)]
        langue = langue_courante()
        return page("demo", request, fiche=fiche, ctx=ctx, photos=photos, retouche=place_id in retouches,
                    modeles=[(f.code, f.modele[langue], f.nom[langue]) for f in FAMILLES.values()],
                    sections=[(s, s in ctx["sections"]) for s in maquette.SECTIONS],
                    noms_sections=NOMS_SECTIONS, palette=palette(ctx["famille"].couleur))

    @app.post("/demo/{place_id}/options")
    async def enregistrer_options(request: Request, place_id: str):
        if not meme_origine(request) or place_id not in fiches:
            return Response(status_code=403 if not meme_origine(request) else 404)
        formulaire = await request.form()
        options = options_du_formulaire(formulaire)
        # Valeurs identiques à celles du modèle : non retenues (elles suivront un changement de modèle)
        defaut = maquette.contexte(fiches[place_id], maquette.Options(modele=options.modele))
        for champ in ("accroche", "presentation", "action", "couleur"):
            if getattr(options, champ) == defaut[champ]:
                setattr(options, champ, "")
        if options.services is not None and [tuple(x) for x in defaut["services"]] == options.services:
            options.services = None
        retouches[place_id] = options
        return Response(status_code=204)

    @app.post("/demo/{place_id}/reinitialiser")
    async def reinitialiser(request: Request, place_id: str):
        if not meme_origine(request):
            return Response(status_code=403)
        retouches.pop(place_id, None)
        return RedirectResponse(f"/demo/{place_id}", status_code=303)

    @app.get("/maquette/{place_id}", response_class=HTMLResponse)
    async def maquette_html(place_id: str):
        try:
            fiche = await fiche_de(place_id)
        except places.ErreurPlaces as e:
            return HTMLResponse(f"<p style='font-family:sans-serif;padding:24px'>{e}</p>", status_code=502)
        return HTMLResponse(maquette.rendre(fiche, retouches.get(place_id)), headers={"Cache-Control": "no-store"})

    @app.get("/photo")
    async def photo(nom: str, largeur: int = 1600):
        cle_cache = (nom, largeur)
        if cle_cache not in images:
            try:
                images.garder(cle_cache, await places.photo(cle(), nom, largeur))
            except places.ErreurPlaces:
                return Response(status_code=404)
        contenu, type_mime = images[cle_cache]
        return Response(contenu, media_type=type_mime, headers={"Cache-Control": "private, max-age=3600"})

    @app.get("/reglages", response_class=HTMLResponse)
    async def reglages_page(request: Request, enregistre: int = 0):
        return page("reglages", request, cle_masquee=masquer(cle()) if cle() else "", choix=reglages.langue,
                    enregistre=bool(enregistre), auto=AUTO)

    @app.post("/reglages")
    async def reglages_enregistrer(request: Request, cle_google: str = Form(""), langue: str = Form(AUTO)):
        if not meme_origine(request):
            return Response(status_code=403)
        if cle_google.strip():
            reglages.enregistrer_cle(places_cle_propre(cle_google))
        reglages.enregistrer_langue(langue)
        fiches.clear()  # textes Google dans la nouvelle langue
        return RedirectResponse("/reglages?enregistre=1", status_code=303)

    @app.post("/reglages/oublier-cle")
    async def oublier_cle(request: Request):
        if not meme_origine(request):
            return Response(status_code=403)
        reglages.enregistrer_cle("")
        return RedirectResponse("/reglages?enregistre=1", status_code=303)

    return app


NOMS_SECTIONS = {
    "a_propos": "À propos", "services": "Services", "galerie": "Galerie de photos", "avis": "Avis clients",
    "infos": "Horaires et accès",
}


def palette(couleur: str) -> list[str]:
    """Couleurs proposées : celle du modèle et les couleurs des autres familles."""
    return list(dict.fromkeys([couleur, *(f.couleur for f in FAMILLES.values()), "#111827", "#0E7490", "#7C3AED"]))


def options_du_formulaire(f) -> maquette.Options:
    options = maquette.Options(
        modele=f.get("modele", ""), accroche=f.get("accroche", ""), presentation=f.get("presentation", ""),
        couleur=f.get("couleur", ""), action=f.get("action", ""),
    )
    if f.get("services_choisis"):
        options.services = list(zip(f.getlist("service_titre"), f.getlist("service_texte")))
    if f.get("photos_choisies"):
        options.photos = f.getlist("photos")
    if f.get("sections_choisies"):
        options.sections = f.getlist("sections")
    return options.nettoyer()


def places_cle_propre(texte: str) -> str:
    """Clé collée avec des espaces, des guillemets ou « key= » devant : on garde la clé seule."""
    texte = texte.strip().strip("\"'").strip()
    if "key=" in texte:
        texte = texte.split("key=", 1)[1].split("&", 1)[0]
    return "".join(texte.split())
