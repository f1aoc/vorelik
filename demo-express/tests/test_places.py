import asyncio
import json

import pytest
from httpx import Response

from demo_express import places
from conftest import CLE, PLACE_ID, fiche_google


def lancer(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("lien, attendu", [
    ("https://www.google.com/maps/place/Boulangerie+Martin/@45.76,4.83,17z/data=!3m1", "Boulangerie Martin"),
    ("https://www.google.fr/maps/place/Caf%C3%A9+des+Arts/@45,4,17z", "Café des Arts"),
    ("https://maps.google.com/?q=Garage+Dupont+Nantes", "Garage Dupont Nantes"),
    ("https://example.com/page", ""),
])
def test_texte_depuis_un_lien_google_maps(lien, attendu):
    assert places.texte_depuis_lien(lien) == attendu


def test_recherche_par_nom_et_ville(google):
    candidats = lancer(places.rechercher(CLE, "Boulangerie Martin Lyon"))
    assert [c.nom for c in candidats] == ["Boulangerie Martin", "Boulangerie Martin & Fils"]
    assert candidats[0].note == 4.7 and candidats[0].site == "" and candidats[1].site
    requete = google.calls[0].request
    assert requete.headers["X-Goog-Api-Key"] == CLE
    assert "places.websiteUri" in requete.headers["X-Goog-FieldMask"]
    corps = json.loads(requete.content)
    assert corps["textQuery"] == "Boulangerie Martin Lyon" and corps["languageCode"] == "fr"


def test_recherche_par_lien_google_maps(google):
    lancer(places.rechercher(CLE, "https://www.google.com/maps/place/Boulangerie+Martin/@45.7,4.8,17z"))
    assert json.loads(google.calls[0].request.content)["textQuery"] == "Boulangerie Martin"


def test_lien_sans_nom_refuse(google):
    with pytest.raises(places.ErreurPlaces, match="tapez plutôt son nom"):
        lancer(places.rechercher(CLE, "https://example.com/une-page"))


def test_sans_cle():
    with pytest.raises(places.ErreurPlaces, match="Aucune clé"):
        lancer(places.rechercher("", "Boulangerie"))


@pytest.mark.parametrize("code, message", [(403, "Places API \\(New\\)"), (429, "Quota"), (500, "HTTP 500")])
def test_erreurs_google_expliquees(google, code, message):
    google.post("https://places.googleapis.com/v1/places:searchText").mock(return_value=Response(code))
    with pytest.raises(places.ErreurPlaces, match=message):
        lancer(places.rechercher(CLE, "Boulangerie"))


def test_fiche_complete(google):
    fiche = lancer(places.details(CLE, PLACE_ID))
    assert (fiche.nom, fiche.ville, fiche.telephone, fiche.metier) == ("Boulangerie Martin", "Lyon", "04 78 00 00 00", "Boulangerie")
    assert len(fiche.horaires) == 3 and fiche.note == 4.7 and fiche.nombre_avis == 128
    # Ordre de Google (pertinence), avis sans commentaire écartés, 10 photos au plus
    assert [a.auteur.nom for a in fiche.avis] == ["Julie R.", "Paul", "Marc"]
    julie, paul, _ = fiche.avis
    assert julie.auteur.avatar.endswith("/julie") and julie.lien_google.endswith("/julie") and julie.visite == (2026, 10)
    assert not julie.traduit and paul.traduit and paul.visite is None
    assert len(fiche.photos) == places.MAX_PHOTOS and fiche.pays == "FR"
    assert fiche.photos[0].auteurs[0] == places.Auteur("Auteur 0", "https://maps.google.com/maps/contrib/0", "https://lh3.googleusercontent.com/a/auteur0")
    assert fiche.photos[0].lien_google == "https://www.google.com/maps/photo/0"
    masque = google.calls[0].request.headers["X-Goog-FieldMask"]
    assert "reviews" in masque and "photos" in masque and "regularOpeningHours.weekdayDescriptions" in masque


def test_ville_sans_composants_d_adresse():
    fiche = places.vers_fiche(fiche_google(addressComponents=[]))
    assert fiche.ville == "Lyon"


def test_identifiants_invalides_refuses(google):
    with pytest.raises(places.ErreurPlaces):
        lancer(places.details(CLE, "../../etc/passwd"))
    with pytest.raises(places.ErreurPlaces):
        lancer(places.photo(CLE, "https://pirate.example/photo"))
    assert not google.calls


def test_photo(google):
    contenu, type_mime = lancer(places.photo(CLE, f"places/{PLACE_ID}/photos/photo0", 800))
    assert contenu.startswith(b"\xff\xd8") and type_mime == "image/jpeg"
    assert google.calls[0].request.url.params["maxWidthPx"] == "800"
