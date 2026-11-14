"""Faux Google Places (respx) : mêmes adresses et même forme de réponses que l'API « New »."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

PLACE_ID = "ChIJ_boulangerie_martin_lyon"
CLE = "AIzaSyTEST-cle-de-test-1234"


def fiche_google(**autres) -> dict:
    fiche = {
        "id": PLACE_ID,
        "displayName": {"text": "Boulangerie Martin", "languageCode": "fr"},
        "formattedAddress": "12 Rue de la République, 69002 Lyon, France",
        "shortFormattedAddress": "12 Rue de la République, Lyon",
        "addressComponents": [{"longText": "Lyon", "shortText": "Lyon", "types": ["locality", "political"]}],
        "nationalPhoneNumber": "04 78 00 00 00",
        "internationalPhoneNumber": "+33 4 78 00 00 00",
        "regularOpeningHours": {"weekdayDescriptions": ["lundi: 07:00–19:30", "mardi: 07:00–19:30", "dimanche: Fermé"]},
        "rating": 4.7,
        "userRatingCount": 128,
        "primaryType": "bakery",
        "primaryTypeDisplayName": {"text": "Boulangerie"},
        "types": ["bakery", "food_store", "store"],
        "googleMapsUri": "https://maps.google.com/?cid=123",
        "reviews": [
            {"rating": 3, "text": {"text": "Correct."}, "authorAttribution": {"displayName": "Paul", "uri": "https://www.google.com/maps/contrib/1"},
             "relativePublishTimeDescription": "il y a 2 mois"},
            {"rating": 5, "text": {"text": "Le meilleur pain du quartier, accueil adorable !"},
             "authorAttribution": {"displayName": "Julie R.", "uri": "https://www.google.com/maps/contrib/2"},
             "relativePublishTimeDescription": "il y a une semaine"},
            {"rating": 5, "text": {"text": "Croissants délicieux."}, "authorAttribution": {"displayName": "Marc"}},
        ],
        "photos": [
            {"name": f"places/{PLACE_ID}/photos/photo{i}", "widthPx": 1600, "heightPx": 1200,
             "authorAttributions": [{"displayName": f"Auteur {i}", "uri": f"https://maps.google.com/maps/contrib/{i}"}]}
            for i in range(12)
        ],
    }
    fiche.update(autres)
    return fiche


@pytest.fixture(autouse=True)
def isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_DONNEES", str(tmp_path / "donnees"))
    monkeypatch.setenv("DEMO_LANGUE", "fr")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)


@pytest.fixture
def google():
    with respx.mock(assert_all_called=False) as mock:
        mock.post("https://places.googleapis.com/v1/places:searchText").mock(return_value=Response(200, json={"places": [
            {"id": PLACE_ID, "displayName": {"text": "Boulangerie Martin"}, "formattedAddress": "12 Rue de la République, 69002 Lyon, France",
             "primaryTypeDisplayName": {"text": "Boulangerie"}, "rating": 4.7, "userRatingCount": 128, "businessStatus": "OPERATIONAL"},
            {"id": "ChIJ_autre_boulangerie_1", "displayName": {"text": "Boulangerie Martin & Fils"}, "formattedAddress": "Villeurbanne",
             "websiteUri": "https://martin-et-fils.fr", "businessStatus": "OPERATIONAL"},
        ]}))
        mock.get(f"https://places.googleapis.com/v1/places/{PLACE_ID}").mock(return_value=Response(200, json=fiche_google()))
        mock.get(url__regex=r"https://places\.googleapis\.com/v1/places/.+/photos/.+/media.*").mock(
            return_value=Response(200, content=b"\xff\xd8\xff-image-jpeg", headers={"content-type": "image/jpeg"}))
        yield mock


@pytest.fixture
def reglages(tmp_path):
    from demo_express.reglages import Reglages

    r = Reglages(tmp_path / "donnees")
    r.enregistrer_cle(CLE)
    return r


@pytest.fixture
def client(reglages):
    from fastapi.testclient import TestClient

    from demo_express.web import creer_app

    return TestClient(creer_app(reglages, hotes=["testserver", "127.0.0.1"]), follow_redirects=False)
