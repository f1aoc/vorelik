"""Licence Démo Express (clés DEX-…) : même client que Chasseur de sites, branché sur l'interface."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from demo_express import licence as lic
from demo_express.web import creer_app
from conftest import PLACE_ID

CLE = "DEX-3Test000001AbCdEf-0123456789AB"


class FauxServeur:
    """Imite serveur-licences/worker.js pour le produit « demo-express »."""

    def __init__(self):
        self.cles = {CLE: {"produit": "demo-express", "rembourse": False, "machines": []},
                     "CDS-3Test000002AbCdEf-0123456789AB": {"produit": "chasseur-de-sites", "rembourse": False, "machines": []}}
        self.hors_ligne = False
        self.appels = []

    def __call__(self, url, donnees):
        action = url.rsplit("/", 1)[1]
        self.appels.append((action, dict(donnees)))
        if self.hors_ligne:
            raise lic.HorsLigne("pas de réseau")
        c = self.cles.get(donnees["cle"])
        if c is None:
            return 404, {"valide": False, "statut": "inconnue"}
        if donnees.get("produit") != c["produit"]:
            return 403, {"valide": False, "statut": "autre_produit"}
        m = donnees["machine"]
        if action == "liberer":
            c["machines"] = [x for x in c["machines"] if x != m]
            return 200, {"libere": True}
        if c["rembourse"]:
            return 200, {"valide": False, "statut": "desactivee"}
        if action == "activer" and m not in c["machines"]:
            if len(c["machines"]) >= 2:
                return 409, {"valide": False, "statut": "limite"}
            c["machines"].append(m)
        if m not in c["machines"]:
            return 200, {"valide": False, "statut": "machine_inconnue"}
        return 200, {"valide": True, "statut": "active", "nom": "Agence Pixel", "email": "camille@pixel.fr"}


class Horloge:
    def __init__(self):
        self.t = datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.t


@pytest.fixture
def serveur():
    return FauxServeur()


@pytest.fixture
def horloge():
    return Horloge()


@pytest.fixture
def licence(tmp_path, serveur, horloge):
    return lic.Licence(tmp_path / "lic", transport=serveur, maintenant=horloge, serveur="https://licences.test")


@pytest.fixture
def web(reglages, licence, monkeypatch):
    monkeypatch.delenv("DEMO_SANS_LICENCE")
    return TestClient(creer_app(reglages, hotes=["testserver"], licence=licence), follow_redirects=False)


def test_constantes_du_produit():
    assert (lic.PRODUIT, lic.NOM_LOGICIEL, lic.VARIABLE_DEV) == ("demo-express", "Démo Express", "DEMO_SANS_LICENCE")
    assert lic.SERVEUR.startswith("https://") and lic.LIENS_ACHAT["en"].endswith("/en/demo-express/")


def test_activation_puis_remboursement(licence, serveur, horloge):
    assert licence.etat().statut == lic.ABSENTE
    etat = licence.activer(CLE)
    assert etat.utilisable and etat.client == "Agence Pixel"
    assert serveur.appels[0][1]["produit"] == "demo-express"
    serveur.cles[CLE]["rembourse"] = True
    horloge.t += timedelta(hours=25)
    assert licence.verification_due()
    assert licence.verifier().statut == lic.DESACTIVEE and not licence.etat().utilisable


def test_cle_d_un_autre_logiciel_refusee(licence):
    with pytest.raises(lic.ErreurLicence, match="Démo Express"):
        licence.activer("CDS-3Test000002AbCdEf-0123456789AB")


def test_hors_ligne_tolere_14_jours(licence, serveur, horloge):
    licence.activer(CLE)
    serveur.hors_ligne = True
    horloge.t += timedelta(days=10)
    assert licence.verifier().utilisable
    horloge.t += timedelta(days=5)
    assert not licence.verifier().utilisable


def test_sans_licence_tout_mene_a_l_ecran_licence(web, google):
    for chemin in ("/", f"/demo/{PLACE_ID}", f"/maquette/{PLACE_ID}", "/photo?nom=x"):
        r = web.get(chemin)
        assert r.status_code == 303 and r.headers["location"] == "/licence", chemin
    assert web.post(f"/demo/{PLACE_ID}/preparer").status_code == 403
    page = web.get("/licence").text
    assert "Activez Démo Express" in page and "DEX-" in page and "https://www.vorelik.com/demo-express/" in page
    assert web.get("/reglages").status_code == 200 and web.get("/static/app.css").status_code == 200
    assert not google.calls


def test_activation_par_l_interface(web, google):
    r = web.post("/licence", data={"cle_licence": CLE})
    assert r.status_code == 303 and "Agence+Pixel" in r.headers["location"]
    assert "Licence active" in web.get("/licence").text
    assert web.get("/").status_code == 200


def test_cle_inconnue_expliquee(web):
    r = web.post("/licence", data={"cle_licence": "DEX-inconnue-000000000000"}, follow_redirects=True)
    assert "Clé de licence inconnue" in r.text or "Collez la clé" in r.text


def test_liberer(web, serveur):
    web.post("/licence", data={"cle_licence": CLE})
    web.post("/licence/liberer")
    assert serveur.cles[CLE]["machines"] == [] and web.get("/").status_code == 303


def test_formulaires_licence_proteges(web):
    assert web.post("/licence", data={"cle_licence": CLE}, headers={"Origin": "https://pirate.example"}).status_code == 403
