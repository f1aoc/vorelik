"""Interface de Démo Express, dans le navigateur (n'écoute que sur l'ordinateur de l'utilisateur).

  /                 recherche de l'entreprise (nom + ville, ou lien Google Maps)
  /demo/{id}        retouches et aperçu de la maquette, ordinateur et téléphone côte à côte
  /demo/{id}/envoyer  envoi au prospect : maquette d'export (sans contenu Google), fichiers, message
  /maquette/{id}    la maquette elle-même (?export=1 : version d'export)
  /photo            photos de la fiche, relayées depuis Google avec la clé du client
  /reglages         clé Google Places, signature du vendeur et langue
  /licence          activation, vérification, libération de la licence (sans licence active, tout y mène)

Les fiches et photos Google restent en mémoire (le temps de la session), jamais sur le disque ni dans un export.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import io
import re
import unicodedata
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urlencode, urlsplit

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.middleware.trustedhost import TrustedHostMiddleware

from demo_express import __version__, capture, maquette, messages, places
from demo_express import photos as phototheque
from demo_express import licence as lic
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


Capturer = Callable[[str, Path], Awaitable[capture.Captures]]


# Toujours accessibles, même sans licence active
LIBRES = re.compile(r"^/(licence(/.*)?|reglages(/.*)?|static/.*)$")


async def entretien_licence(licence: lic.Licence, intervalle: float = 3600) -> None:
    """Vérification au démarrage, puis dès qu'elle est due (toutes les 24 h)."""
    premier = True
    while True:
        with contextlib.suppress(Exception):
            if premier or licence.verification_due():
                await asyncio.to_thread(licence.verifier)
        premier = False
        await asyncio.sleep(intervalle)


def creer_app(reglages: Reglages, hotes: list[str] | None = None, capturer: Capturer | None = None,
              licence: lic.Licence | None = None) -> FastAPI:
    capturer = capturer or capture.capturer
    licence = licence or lic.licence_par_defaut(reglages.dossier)

    @contextlib.asynccontextmanager
    async def cycle(_app):
        tache = asyncio.get_running_loop().create_task(entretien_licence(licence))
        yield
        tache.cancel()

    app = FastAPI(title="Démo Express", docs_url=None, redoc_url=None, openapi_url=None, lifespan=cycle)

    @app.middleware("http")
    async def controle_licence(request: Request, suivant):
        if not LIBRES.match(request.url.path) and not licence.etat().utilisable:
            if request.method == "GET":
                return RedirectResponse("/licence", status_code=303)
            return JSONResponse({"erreur": _("Licence inactive : ouvrez l'écran Licence.")}, status_code=403)
        return await suivant(request)

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hotes or HOTES)
    app.mount("/static", StaticFiles(directory=DOSSIER / "static"), name="static")
    env = Environment(loader=FileSystemLoader(DOSSIER / "templates"), autoescape=select_autoescape(["html"]))
    env.globals.update(_=_, version=__version__, licence=licence.etat)
    fiches: Memoire = Memoire(30)
    retouches: dict[str, maquette.Options] = {}  # par entreprise, le temps de la session
    images: Memoire = Memoire(120)
    identites: dict[str, maquette.Identite] = {}  # vérifiées par le vendeur, pour l'export
    exports: Memoire = Memoire(5)  # (entreprise, empreinte de la maquette) → Captures
    importees = phototheque.Imports()  # photos importées par le vendeur, par entreprise

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
        ctx = maquette.contexte(fiche, options, importees=importees.liste(place_id))
        choisies = [p.nom for p in ctx["photos"] if p is not None]
        # Photos : celles retenues dans leur ordre, puis les autres (décochées)
        proposees = maquette.photos_proposees(fiche, ctx["famille"], importees.liste(place_id))
        for nom in choisies:  # illustration d'un autre modèle, retenue avant un changement de modèle
            if nom not in {p.nom for p in proposees} and (p := phototheque.photo_bibliotheque(nom)):
                proposees.append(p)
        photos = [(p, p.nom in choisies) for p in sorted(proposees, key=lambda p: choisies.index(p.nom) if p.nom in choisies else 99)]
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
        defaut = maquette.contexte(fiches[place_id], maquette.Options(modele=options.modele), importees=importees.liste(place_id))
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
    async def maquette_html(place_id: str, export: int = 0):
        try:
            fiche = await fiche_de(place_id)
        except places.ErreurPlaces as e:
            return HTMLResponse(f"<p style='font-family:sans-serif;padding:24px'>{e}</p>", status_code=502)
        if export:
            return HTMLResponse(html_export(place_id), headers={"Cache-Control": "no-store"})
        return HTMLResponse(maquette.rendre(fiche, retouches.get(place_id), importees=importees.liste(place_id)),
                            headers={"Cache-Control": "no-store"})

    # --- Photos importées par le vendeur ------------------------------------------------------------------

    @app.post("/demo/{place_id}/photos")
    async def importer_photos(request: Request, place_id: str):
        if not meme_origine(request):
            return Response(status_code=403)
        if place_id not in fiches:
            return Response(status_code=404)
        formulaire = await request.form(max_files=phototheque.MAX_IMPORTS, max_fields=20)
        ajoutees, erreurs = [], []
        for envoi in formulaire.getlist("photos"):
            if not hasattr(envoi, "read"):
                continue
            donnees = await envoi.read(phototheque.TAILLE_MAX + 1)
            try:
                ajoutees.append(importees.ajouter(place_id, donnees).nom)
            except phototheque.ErreurImport as e:
                erreurs.append(f"{envoi.filename or 'photo'} : {_(str(e))}")
        options = retouches.get(place_id)
        if ajoutees and options is not None and options.photos is not None:
            options.photos = ajoutees + options.photos  # nouvelles photos en tête de la sélection
        return JSONResponse({"ajoutees": ajoutees, "erreurs": erreurs}, status_code=200 if ajoutees or not erreurs else 400)

    @app.post("/demo/{place_id}/photos/retirer")
    async def retirer_photo(request: Request, place_id: str, nom: str = Form("")):
        if not meme_origine(request):
            return Response(status_code=403)
        if not importees.retirer(place_id, nom):
            return Response(status_code=404)
        options = retouches.get(place_id)
        if options is not None and options.photos is not None:
            options.photos = [n for n in options.photos if n != nom]
        return Response(status_code=204)

    # --- Envoi au prospect (B : fichiers sans contenu Google, C : message) ------------------------------------

    def identite_de(place_id: str) -> maquette.Identite:
        if place_id not in identites:
            f = fiches[place_id]
            identites[place_id] = maquette.Identite(f.nom, f.metier, f.ville, f.telephone, f.adresse).nettoyer()
        return identites[place_id]

    def photo_integree(nom: str, largeur: int = 0) -> str:
        """Export : photo intégrée à la page (importée ou d'illustration ; jamais une photo Google)."""
        contenu = importees.contenu(nom) if nom.startswith(phototheque.IMPORT) else phototheque.contenu_bibliotheque(nom)
        return phototheque.uri(contenu) if contenu else ""

    def html_export(place_id: str) -> str:
        vendeur = reglages.vendeur
        return maquette.rendre(fiches[place_id], retouches.get(place_id), photo_integree, identite=identite_de(place_id),
                               importees=importees.liste(place_id), auteur=vendeur.agence or vendeur.nom)

    def message_de(place_id: str) -> messages.Message:
        fiche, identite = fiches[place_id], identite_de(place_id)
        ctx = maquette.contexte(fiche, retouches.get(place_id), identite=identite, importees=importees.liste(place_id))
        return messages.rediger(identite.nom, identite.ville, ctx["famille"], ctx["action"], bool(fiche.site), reglages.vendeur)

    def nom_de_fichier(place_id: str) -> str:
        texte = unicodedata.normalize("NFKD", identite_de(place_id).nom).encode("ascii", "ignore").decode().lower()
        return "maquette-" + (re.sub(r"[^a-z0-9]+", "-", texte).strip("-")[:50] or "site")

    @app.get("/demo/{place_id}/envoyer", response_class=HTMLResponse)
    async def envoyer(request: Request, place_id: str):
        try:
            await fiche_de(place_id)
        except places.ErreurPlaces as e:
            return page("accueil", request, statut=502, q="", candidats=[], erreur=str(e), sans_cle=not cle())
        return page("envoyer", request, fiche=fiches[place_id], identite=identite_de(place_id), message=message_de(place_id),
                    vendeur=reglages.vendeur, navigateur_pret=capture.chromium_installe(reglages.dossier))

    @app.post("/demo/{place_id}/identite")
    async def enregistrer_identite(request: Request, place_id: str):
        if not meme_origine(request):
            return Response(status_code=403)
        if place_id not in fiches:
            return Response(status_code=404)
        f = await request.form()
        identite = maquette.Identite(f.get("nom", ""), f.get("metier", ""), f.get("ville", ""), f.get("telephone", ""),
                                     f.get("adresse", "")).nettoyer()
        if not identite.nom:
            return JSONResponse({"erreur": _("Indiquez le nom de l'entreprise.")}, status_code=400)
        identites[place_id] = identite
        m = message_de(place_id)
        return JSONResponse({"objet": m.objet, "corps": m.corps, "sms": m.sms, "lien_mail": m.lien_mail})

    @app.post("/demo/{place_id}/preparer")
    async def preparer(request: Request, place_id: str):
        """Images et PDF de la maquette d'export (le navigateur intégré est téléchargé au premier usage)."""
        if not meme_origine(request):
            return Response(status_code=403)
        if place_id not in fiches:
            return Response(status_code=404)
        html = html_export(place_id)
        cle_export = (place_id, hashlib.sha256(html.encode()).hexdigest())
        if cle_export not in exports:
            try:
                exports.garder(cle_export, await capturer(html, reglages.dossier))
            except capture.ErreurCapture as e:
                return JSONResponse({"erreur": str(e)}, status_code=503)
        return JSONResponse({"pret": True})

    @app.get("/demo/{place_id}/fichier/{format}")
    async def fichier(place_id: str, format: str):
        if place_id not in fiches:
            return Response(status_code=404)
        html = html_export(place_id)
        nom = nom_de_fichier(place_id)
        if format == "html":
            return telechargement(html.encode("utf-8"), f"{nom}.html", "text/html; charset=utf-8")
        captures = exports.get((place_id, hashlib.sha256(html.encode()).hexdigest()))
        if captures is None:
            return Response(_("Préparez d'abord les fichiers."), status_code=409)
        if format == "ordinateur.png":
            return telechargement(captures.ordinateur, f"{nom}-ordinateur.png", "image/png")
        if format == "telephone.png":
            return telechargement(captures.telephone, f"{nom}-telephone.png", "image/png")
        if format == "pdf":
            return telechargement(captures.pdf, f"{nom}.pdf", "application/pdf")
        if format == "zip":
            m = message_de(place_id)
            tampon = io.BytesIO()
            with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr(f"{nom}.pdf", captures.pdf)
                z.writestr(f"{nom}-ordinateur.png", captures.ordinateur)
                z.writestr(f"{nom}-telephone.png", captures.telephone)
                z.writestr(f"{nom}.html", html)
                z.writestr("message.txt", f"{m.objet}\n\n{m.corps}\n\n---\nSMS :\n{m.sms}\n")
            return telechargement(tampon.getvalue(), f"{nom}.zip", "application/zip")
        return Response(status_code=404)

    @app.get("/photo")
    async def photo(nom: str, largeur: int = 1600):
        if nom.startswith((phototheque.BIBLIO, phototheque.IMPORT)):
            contenu = importees.contenu(nom) if nom.startswith(phototheque.IMPORT) else phototheque.contenu_bibliotheque(nom)
            if contenu is None:
                return Response(status_code=404)
            return Response(contenu, media_type=phototheque.type_mime(contenu), headers={"Cache-Control": "private, max-age=3600"})
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
                    enregistre=bool(enregistre), auto=AUTO, vendeur=reglages.vendeur)

    @app.post("/reglages")
    async def reglages_enregistrer(request: Request, cle_google: str = Form(""), langue: str = Form(AUTO),
                                   vendeur_nom: str = Form(""), vendeur_agence: str = Form(""),
                                   vendeur_telephone: str = Form(""), vendeur_email: str = Form("")):
        if not meme_origine(request):
            return Response(status_code=403)
        if cle_google.strip():
            reglages.enregistrer_cle(places_cle_propre(cle_google))
        reglages.enregistrer_vendeur(vendeur_nom, vendeur_agence, vendeur_telephone, vendeur_email)
        reglages.enregistrer_langue(langue)
        fiches.clear()  # textes Google dans la nouvelle langue
        return RedirectResponse("/reglages?enregistre=1", status_code=303)

    # --- Licence ------------------------------------------------------------------------------------------

    def vers_licence(**params) -> RedirectResponse:
        return RedirectResponse("/licence" + (f"?{urlencode(params)}" if params else ""), status_code=303)

    @app.get("/licence", response_class=HTMLResponse)
    async def licence_page(request: Request, ok: str = "", erreur: str = ""):
        return page("licence", request, etat=licence.etat(), ok=ok, erreur=erreur, tolerance=lic.TOLERANCE_JOURS,
                    lien_achat=lic.LIENS_ACHAT.get(langue_courante(), lic.LIEN_ACHAT))

    @app.post("/licence")
    async def licence_activer(request: Request, cle_licence: str = Form("")):
        if not meme_origine(request):
            return Response(status_code=403)
        try:
            etat = await asyncio.to_thread(licence.activer, cle_licence)
        except lic.ErreurLicence as e:
            return vers_licence(erreur=str(e))
        if etat.client:
            return vers_licence(ok=_("Merci, {nom} ! Votre licence est activée sur cet ordinateur.").format(nom=etat.client))
        return vers_licence(ok=_("Merci ! Votre licence est activée sur cet ordinateur."))

    @app.post("/licence/verifier")
    async def licence_verifier(request: Request):
        if not meme_origine(request):
            return Response(status_code=403)
        etat = await asyncio.to_thread(licence.verifier)
        return vers_licence(ok=_("Licence vérifiée : tout est en ordre.")) if etat.utilisable else vers_licence()

    @app.post("/licence/liberer")
    async def licence_liberer(request: Request):
        if not meme_origine(request):
            return Response(status_code=403)
        try:
            await asyncio.to_thread(licence.liberer)
        except lic.ErreurLicence as e:
            return vers_licence(erreur=str(e))
        return vers_licence(ok=_("Licence libérée : vous pouvez maintenant l'activer sur un autre ordinateur."))

    @app.post("/reglages/oublier-cle")
    async def oublier_cle(request: Request):
        if not meme_origine(request):
            return Response(status_code=403)
        reglages.enregistrer_cle("")
        return RedirectResponse("/reglages?enregistre=1", status_code=303)

    return app


def telechargement(contenu: bytes, nom: str, type_mime: str) -> Response:
    return Response(contenu, media_type=type_mime, headers={"Content-Disposition": f'attachment; filename="{nom}"',
                                                            "Cache-Control": "no-store"})


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
