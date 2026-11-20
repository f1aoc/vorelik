"""Règles Google Maps Platform (« Policies and attributions for Places API »).

Aperçu : mention « Google Maps » au bon format, auteur de chaque photo et avis (avatar, nom, lien), lien vers
Google Maps, date de visite pour la France, explication de la sélection des avis.
Export : aucun contenu Google (ni photo, ni avis, ni note, ni horaires, ni adresse, ni lien Google Maps).
"""

import re

import pytest

from demo_express import maquette, places
from demo_express.familles import FAMILLES
from conftest import fiche_google

GMP = 'translate="no">Google Maps</span>'


@pytest.fixture
def apercu():
    return maquette.rendre(places.vers_fiche(fiche_google()))


def section(page, ident):
    return re.search(rf'<section id="{ident}".*?</section>', page, re.S).group(0)


def test_mention_google_maps_au_format_exige(apercu):
    css = re.search(r"\n\s*\.gmp-attribution \{(.*?)\}", apercu, re.S).group(1)
    for regle in ("font-family: Roboto, Sans-Serif", "font-weight: 400", "white-space: nowrap", "font-size: 13px",
                  "font-style: normal", "letter-spacing: normal", "color: #5E5E5E"):
        assert regle in css
    assert "Google Maps" in apercu and ">Google<" not in apercu  # plus jamais « Google » seul


def test_note_attribuee(apercu):
    note = re.search(r'<div class="note contenu-google">.*?</div>', apercu, re.S).group(0)
    assert "4,7" in note and "128" in note and GMP in note


def test_photos_creditees_avec_lien_auteur_et_google_maps(apercu):
    galerie = section(apercu, "galerie")
    for i in range(2, 8):
        assert f'href="https://maps.google.com/maps/contrib/{i}"' in galerie
        assert f'href="https://www.google.com/maps/photo/{i}"' in galerie
    assert GMP in galerie
    # grande photo d'en-tête aussi
    assert 'href="https://www.google.com/maps/photo/0"' in apercu and 'class="credit-photo"' in apercu


def test_avis_avec_auteur_lien_date_de_visite_et_explications(apercu):
    avis = section(apercu, "avis")
    assert avis.count('class="carte-avis"') == 3
    assert 'src="https://lh3.googleusercontent.com/a/julie"' in avis  # avatar
    assert re.search(r'href="https://www.google.com/maps/contrib/2"[^>]*>Julie R.</a>', avis)
    assert 'href="https://www.google.com/maps/reviews/julie"' in avis
    assert "Visite : octobre 2026" in avis and "il y a une semaine" in avis
    assert "Traduit par Google" in avis  # avis de Paul, traduit de l'anglais
    assert re.search(r"parmi les plus pertinents selon <span[^>]*>Google Maps</span>", avis)
    assert "ne sont pas vérifiés par Google Maps" in avis
    assert "Sans texte" not in avis


def test_horaires_et_adresse_attribues(apercu):
    infos = section(apercu, "infos")
    assert "lundi: 07:00–19:30" in infos and infos.count(GMP) >= 2


def test_date_de_visite_en_anglais(monkeypatch):
    monkeypatch.setenv("DEMO_LANGUE", "en")
    page = maquette.rendre(places.vers_fiche(fiche_google()))
    assert "Visited October 2026" in page and "View on" in page


# --- Export -------------------------------------------------------------------------------------------------

IDENTITE = maquette.Identite("Boulangerie Martin", "Boulangerie", "Lyon", "04 78 00 00 00", "8 place Bellecour, 69005 Lyon")
CONTENU_GOOGLE = ["/photo?", "googleusercontent", "google.com/maps", "maps.google.com", "Le meilleur pain", "Croissants",
                  "Good bread", "Julie", "Paul", "4,7", "128", "07:00", "République", "69002", "Auteur 0", "Google Maps"]


@pytest.mark.parametrize("code", list(FAMILLES))
def test_export_sans_aucun_contenu_google(code):
    page = maquette.rendre(places.vers_fiche(fiche_google()), maquette.Options(modele=code), identite=IDENTITE)
    for interdit in CONTENU_GOOGLE:
        assert interdit not in page, interdit
    assert "Boulangerie Martin" in page and "Lyon" in page and 'href="tel:0478000000"' in page
    assert "8 place Bellecour, 69005 Lyon" in page  # adresse vérifiée par le vendeur
    assert "Vos photos ici" in page and "Vos horaires d&#39;ouverture" in page
    assert "Maquette à compléter avec vos photos" in page and "Maquette de démonstration" in page


def test_export_garde_les_retouches_du_vendeur():
    f = places.vers_fiche(fiche_google())
    options = maquette.Options(accroche="Votre pause gourmande", photos=[f.photos[0].nom, f.photos[1].nom, f.photos[2].nom, f.photos[3].nom])
    page = maquette.rendre(f, options, identite=IDENTITE)
    assert "Votre pause gourmande" in page
    assert page.count('class="photo emplacement-photo') == 4  # autant d'emplacements que de photos retenues
    assert "Les avis de vos clients" in page


def test_identite_nettoyee_et_echappee():
    identite = maquette.Identite(" <b>Chez Léa</b> ", "Coiffeur", "Nantes", "06 12 <script> 34 56 78").nettoyer()
    assert identite.telephone == "06 12  34 56 78" and identite.nom == "<b>Chez Léa</b>"
    page = maquette.rendre(places.vers_fiche(fiche_google()), identite=identite)
    assert "&lt;b&gt;Chez Léa&lt;/b&gt;" in page and "<script>" not in page
