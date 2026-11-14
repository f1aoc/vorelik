import pytest

from demo_express import maquette, places
from demo_express.familles import FAMILLES, famille_de
from conftest import fiche_google


@pytest.mark.parametrize("type_principal, types, metier, famille", [
    ("bakery", [], "", "bouche"),
    ("italian_restaurant", ["restaurant"], "", "restaurant"),
    ("hair_salon", [], "", "beaute"),
    ("plumber", [], "", "batiment"),
    ("dentist", [], "", "sante"),
    ("establishment", ["point_of_interest"], "Plombier chauffagiste", "batiment"),
    ("", [], "Ostéopathe", "sante"),
    ("insurance_agency", [], "Agence d'assurance", "services"),
])
def test_famille_de_metier(type_principal, types, metier, famille):
    assert famille_de(type_principal, types, metier).code == famille


def test_chaque_famille_a_ses_textes_en_francais_et_en_anglais():
    for f in FAMILLES.values():
        for langue in ("fr", "en"):
            assert f.accroche[langue] and f.action[langue] and len(f.services[langue]) == 3
            assert "{nom}" in f.presentation[langue] and "{ville}" in f.presentation[langue]


def test_maquette_d_une_boulangerie():
    html = maquette.rendre(places.vers_fiche(fiche_google()))
    assert "<h1>Boulangerie Martin</h1>" in html
    assert "Maquette de démonstration" in html and 'name="robots" content="noindex, nofollow"' in html
    assert "Le goût du fait maison" in html  # famille « commerces de bouche »
    assert "Chez Boulangerie Martin, à Lyon" in html
    assert 'href="tel:+33478000000"' in html
    # Crédits Google (vérifiés en détail dans test_conformite.py)
    assert "Auteur 0" in html and "Julie R." in html and 'translate="no">Google Maps</span>' in html
    assert "/photo?nom=places%2F" in html
    assert "lundi: 07:00–19:30" in html


def test_maquette_en_anglais(monkeypatch):
    monkeypatch.setenv("DEMO_LANGUE", "en")
    html = maquette.rendre(places.vers_fiche(fiche_google()))
    assert 'lang="en"' in html and "Demo mockup" in html and "The taste of homemade" in html and "Place an order" in html


def test_contenu_google_echappe():
    piege = fiche_google(displayName={"text": "<script>alert(1)</script>{0}{nom}"})
    html = maquette.rendre(places.vers_fiche(piege))
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;{0}{nom}" in html


def test_fiche_sans_photo_ni_avis_ni_horaires():
    html = maquette.rendre(places.vers_fiche(fiche_google(photos=[], reviews=[], regularOpeningHours={}, nationalPhoneNumber="",
                                                           internationalPhoneNumber="")))
    assert "Horaires communiqués sur demande" in html and "Ils nous recommandent" not in html and "tel:" not in html


def test_choix_des_photos():
    fiche = places.vers_fiche(fiche_google())
    options = maquette.Options(photos=[fiche.photos[3].nom, fiche.photos[1].nom])
    html = maquette.rendre(fiche, options)
    assert html.index("photo3") < html.index("photo1") and "photo0" not in html
