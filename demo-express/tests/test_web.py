import html

from conftest import CLE, PLACE_ID


def test_recherche_et_choix_de_l_entreprise(client, google):
    page = client.get("/", params={"q": "Boulangerie Martin Lyon"}).text
    assert f'href="/demo/{PLACE_ID}"' in page and "Sans site" in page and "A déjà un site" in page


def test_apercu_ordinateur_et_telephone(client, google):
    page = client.get(f"/demo/{PLACE_ID}").text
    assert page.count(f'src="/maquette/{PLACE_ID}"') == 2 and "Commerces de bouche" in page
    html = client.get(f"/maquette/{PLACE_ID}").text
    assert "<h1>Boulangerie Martin</h1>" in html
    # Fiche gardée en mémoire : un seul appel à Google pour l'aperçu et la maquette
    assert sum(1 for c in google.calls if "/places/" + PLACE_ID in str(c.request.url) and "photos" not in str(c.request.url)) == 1


def test_photos_relayees_sans_exposer_la_cle(client, google):
    html = client.get(f"/maquette/{PLACE_ID}").text
    assert CLE not in html and "places.googleapis" not in html
    r = client.get("/photo", params={"nom": f"places/{PLACE_ID}/photos/photo0", "largeur": 900})
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    client.get("/photo", params={"nom": f"places/{PLACE_ID}/photos/photo0", "largeur": 900})
    assert sum(1 for c in google.calls if "/media" in str(c.request.url)) == 1  # mémoire
    assert client.get("/photo", params={"nom": "../../secret"}).status_code == 404


def test_sans_cle_l_accueil_renvoie_aux_reglages(client, google, reglages):
    reglages.enregistrer_cle("")
    page = html.unescape(client.get("/").text)
    assert "Ajoutez d'abord votre clé Google Places dans les" in page


def test_erreur_google_affichee(client, google):
    from httpx import Response

    google.post("https://places.googleapis.com/v1/places:searchText").mock(return_value=Response(403))
    assert "Places API (New)" in client.get("/", params={"q": "Boulangerie"}).text


def test_reglages_cle_chiffree_et_langue(client, reglages):
    r = client.post("/reglages", data={"cle_google": '  "key=AIzaNOUVELLE-cle-5678"  ', "langue": "en"})
    assert r.status_code == 303
    assert reglages.cle_google == "AIzaNOUVELLE-cle-5678"
    contenu = (reglages.dossier / "reglages.json").read_text()
    assert "AIzaNOUVELLE" not in contenu and '"langue": "en"' in contenu
    page = client.get("/reglages").text
    assert "••••••••5678" in page and "AIzaNOUVELLE" not in page


def test_formulaire_venant_d_un_autre_site_refuse(client, reglages):
    r = client.post("/reglages", data={"cle_google": "AIzaPIRATE"}, headers={"Origin": "https://pirate.example"})
    assert r.status_code == 403 and reglages.cle_google == CLE


def test_application_inaccessible_depuis_un_autre_nom_d_hote(client):
    assert client.get("/", headers={"Host": "pirate.example"}).status_code == 400
