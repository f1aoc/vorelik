"""Étape 3 : envoi au prospect (B : fichiers sans contenu Google, C : message de prospection)."""

import asyncio
import html
import io
import os
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from demo_express import capture, maquette, messages
from demo_express.familles import FAMILLES
from demo_express.web import creer_app
from conftest import PLACE_ID
from test_conformite import CONTENU_GOOGLE as _TOUT

# L'identité (nom, téléphone, adresse) est préremplie depuis la fiche puis vérifiée par le vendeur : l'adresse est autorisée
CONTENU_GOOGLE = [x for x in _TOUT if x not in ("République", "69002")]

PNG, PDF = b"\x89PNG\r\n\x1a\n", b"%PDF"


class FauxNavigateur:
    def __init__(self, erreur: str = ""):
        self.appels, self.erreur = [], erreur

    async def __call__(self, html_page: str, dossier: Path) -> capture.Captures:
        self.appels.append(html_page)
        if self.erreur:
            raise capture.ErreurCapture(self.erreur)
        return capture.Captures(ordinateur=PNG + b"ordi", telephone=PNG + b"tel", pdf=PDF + b"-1.7")


@pytest.fixture
def navigateur():
    return FauxNavigateur()


@pytest.fixture
def client(reglages, navigateur):
    reglages.enregistrer_vendeur("Camille Durand", "Agence Pixel", "06 11 22 33 44", "camille@pixel.fr")
    return TestClient(creer_app(reglages, hotes=["testserver"], capturer=navigateur), follow_redirects=False)


# --- C : message ---------------------------------------------------------------------------------------------

VENDEUR = messages.Vendeur("Camille Durand", "Agence Pixel", "06 11 22 33 44", "camille@pixel.fr")


def test_message_entreprise_sans_site():
    m = messages.rediger("Boulangerie Martin", "Lyon", FAMILLES["bouche"], "Passer commande", False, VENDEUR)
    assert m.objet == "Une idée de site internet pour Boulangerie Martin"
    assert "J'ai découvert Boulangerie Martin à Lyon" in m.corps and "pas encore de site" in m.corps
    assert "un bouton pour passer commande" in m.corps  # minuscule au milieu de la phrase
    assert "Camille Durand\nAgence Pixel\n06 11 22 33 44\ncamille@pixel.fr" in m.corps
    assert "ne plus recevoir de message" in m.corps
    assert "ici Camille Durand, Agence Pixel" in m.sms and "06 11 22 33 44" in m.sms and "STOP" in m.sms
    assert m.lien_mail.startswith("mailto:?subject=Une%20id%C3%A9e") and "%0A" in m.lien_mail


def test_message_entreprise_avec_site_et_sans_signature():
    m = messages.rediger("Garage Dupont", "", FAMILLES["services"], "", True, messages.Vendeur())
    assert m.objet == "Une nouvelle version du site de Garage Dupont"
    assert "J'ai découvert Garage Dupont et j'ai regardé votre site" in m.corps and "nous contacter" in m.corps
    assert "\n\n\n" not in m.corps and m.sms.startswith("Bonjour, j'ai préparé")


def test_message_en_anglais(monkeypatch):
    monkeypatch.setenv("DEMO_LANGUE", "en")
    m = messages.rediger("Martin's Bakery", "Leeds", FAMILLES["bouche"], "", False, VENDEUR)
    assert m.objet == "A website idea for Martin's Bakery" and "in Leeds" in m.corps and "place an order" in m.corps
    assert "Reply STOP" in m.sms and "this is Camille Durand, Agence Pixel" in m.sms


# --- B : page d'envoi et fichiers ---------------------------------------------------------------------------

def test_page_envoyer(client, google):
    page = html.unescape(client.get(f"/demo/{PLACE_ID}/envoyer").text)
    assert 'value="Boulangerie Martin"' in page and 'value="04 78 00 00 00"' in page and 'value="Lyon"' in page
    assert 'value="12 Rue de la République, 69002 Lyon, France"' in page  # adresse complète proposée
    assert "Une idée de site internet pour Boulangerie Martin" in page and "Camille Durand" in page
    assert f'src="/maquette/{PLACE_ID}?export=1"' in page and "interdisent de copier" in page
    assert f'href="/demo/{PLACE_ID}/envoyer"' in client.get(f"/demo/{PLACE_ID}").text


def test_maquette_d_export_sans_contenu_google(client, google):
    client.get(f"/demo/{PLACE_ID}/envoyer")
    page = client.get(f"/maquette/{PLACE_ID}", params={"export": 1}).text
    for interdit in CONTENU_GOOGLE:
        assert interdit not in page, interdit
    assert "Vos photos ici" in page and "Boulangerie Martin" in page


def test_identite_modifiee_par_le_vendeur(client, google):
    client.get(f"/demo/{PLACE_ID}/envoyer")
    r = client.post(f"/demo/{PLACE_ID}/identite", data={"nom": "Maison Martin", "metier": "Boulangerie", "ville": "Lyon 2e", "telephone": "04 72 11 22 33",
                                                     "adresse": "3 rue Mercière, 69005 Lyon"})
    assert r.status_code == 200 and r.json()["objet"] == "Une idée de site internet pour Maison Martin"
    page = client.get(f"/maquette/{PLACE_ID}", params={"export": 1}).text
    assert "Maison Martin" in page and "Lyon 2e" in page and 'href="tel:0472112233"' in page and "3 rue Mercière, 69005 Lyon" in page
    vide = client.post(f"/demo/{PLACE_ID}/identite", data={"nom": "  "})
    assert vide.status_code == 400 and "nom" in vide.json()["erreur"]


def test_retouches_reprises_dans_l_export(client, google):
    client.get(f"/demo/{PLACE_ID}")
    client.post(f"/demo/{PLACE_ID}/options", data={"modele": "batiment", "accroche": "Votre pause gourmande"})
    page = client.get(f"/maquette/{PLACE_ID}", params={"export": 1}).text
    assert 'class="modele-batiment"' in page and "Votre pause gourmande" in page


def test_fichiers_prepares_puis_telecharges(client, google, navigateur):
    client.get(f"/demo/{PLACE_ID}/envoyer")
    assert client.get(f"/demo/{PLACE_ID}/fichier/pdf").status_code == 409
    assert client.post(f"/demo/{PLACE_ID}/preparer").json() == {"pret": True}
    client.post(f"/demo/{PLACE_ID}/preparer")
    assert len(navigateur.appels) == 1  # maquette inchangée : pas de nouvelle capture
    for interdit in CONTENU_GOOGLE:
        assert interdit not in navigateur.appels[0], interdit
    attendus = {"pdf": ("application/pdf", "maquette-boulangerie-martin.pdf"),
                "ordinateur.png": ("image/png", "maquette-boulangerie-martin-ordinateur.png"),
                "telephone.png": ("image/png", "maquette-boulangerie-martin-telephone.png"),
                "html": ("text/html; charset=utf-8", "maquette-boulangerie-martin.html")}
    for format, (type_mime, nom) in attendus.items():
        r = client.get(f"/demo/{PLACE_ID}/fichier/{format}")
        assert r.status_code == 200 and r.headers["content-type"] == type_mime and nom in r.headers["content-disposition"]
    z = zipfile.ZipFile(io.BytesIO(client.get(f"/demo/{PLACE_ID}/fichier/zip").content))
    assert sorted(z.namelist()) == ["maquette-boulangerie-martin-ordinateur.png", "maquette-boulangerie-martin-telephone.png",
                                    "maquette-boulangerie-martin.html", "maquette-boulangerie-martin.pdf", "message.txt"]
    texte = z.read("message.txt").decode()
    assert "Une idée de site internet" in texte and "SMS" in texte
    assert "Vos photos ici" in z.read("maquette-boulangerie-martin.html").decode()
    # Identité modifiée : les fichiers préparés ne correspondent plus
    client.post(f"/demo/{PLACE_ID}/identite", data={"nom": "Maison Martin"})
    assert client.get(f"/demo/{PLACE_ID}/fichier/pdf").status_code == 409


def test_erreur_du_navigateur_expliquee(reglages, google):
    app = TestClient(creer_app(reglages, hotes=["testserver"], capturer=FauxNavigateur("Connexion impossible")))
    app.get(f"/demo/{PLACE_ID}/envoyer")
    r = app.post(f"/demo/{PLACE_ID}/preparer")
    assert r.status_code == 503 and r.json()["erreur"] == "Connexion impossible"


def test_envoi_protege(client, google):
    client.get(f"/demo/{PLACE_ID}/envoyer")
    autre = {"Origin": "https://pirate.example"}
    assert client.post(f"/demo/{PLACE_ID}/identite", data={"nom": "x"}, headers=autre).status_code == 403
    assert client.post(f"/demo/{PLACE_ID}/preparer", headers=autre).status_code == 403
    assert client.post("/demo/ChIJ_inconnue_000000/preparer").status_code == 404
    assert client.get("/demo/ChIJ_inconnue_000000/fichier/html").status_code == 404


def test_signature_dans_les_reglages(client, reglages):
    client.post("/reglages", data={"vendeur_nom": "Alex", "vendeur_agence": "Studio A", "vendeur_telephone": "", "vendeur_email": ""})
    assert reglages.vendeur == messages.Vendeur("Alex", "Studio A", "", "")
    assert 'value="Studio A"' in client.get("/reglages").text


# --- Capture réelle (navigateur intégré) -------------------------------------------------------------------

CHROMIUM = os.environ.get("DEMO_CHROMIUM") or ("/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").exists() else "")


@pytest.mark.skipif(not CHROMIUM, reason="Chromium absent")
def test_capture_reelle(tmp_path, monkeypatch):
    from demo_express import places
    from conftest import fiche_google

    monkeypatch.setenv("DEMO_CHROMIUM", CHROMIUM)
    page = maquette.rendre(places.vers_fiche(fiche_google()), identite=maquette.Identite("Boulangerie Martin", "Boulangerie", "Lyon", "04 78 00 00 00"))
    c = asyncio.run(capture.capturer(page, tmp_path))
    assert c.ordinateur.startswith(PNG) and c.telephone.startswith(PNG) and c.pdf.startswith(PDF)
    largeur = int.from_bytes(c.ordinateur[16:20], "big")
    largeur_tel = int.from_bytes(c.telephone[16:20], "big")
    assert largeur == 1280 and largeur_tel == 780  # téléphone : 390 px en densité 2
    assert c.pdf.count(b"/Type /Page") - c.pdf.count(b"/Type /Pages") == 1  # une seule longue page


def test_fiche_adresse_seule_prend_le_nom_tape(client, google):
    from conftest import fiche_google
    from httpx import Response
    google.get(f"https://places.googleapis.com/v1/places/{PLACE_ID}").mock(return_value=Response(200, json=fiche_google(
        displayName={"text": "22 Route Nationale 7"}, primaryType="", primaryTypeDisplayName={}, types=["street_address"])))
    client.get("/", params={"q": "DELPHINE FLEURS 22 Route Nationale 7, 13670 Saint-Andiol"})
    atelier = client.get(f"/demo/{PLACE_ID}").text
    assert "<h1>DELPHINE FLEURS</h1>" in atelier or "DELPHINE FLEURS" in atelier.split("</h1>")[0]
    assert 'value="DELPHINE FLEURS"' in client.get(f"/demo/{PLACE_ID}/envoyer").text
