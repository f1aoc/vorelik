"""Photothèque d'illustration (CC0) et photos importées par le vendeur : utilisables dans les fichiers envoyés."""

import html
import io
import json

import pytest
from PIL import Image

from demo_express import maquette, photos
from demo_express.familles import FAMILLES
from conftest import PLACE_ID
from test_envoi import CONTENU_GOOGLE

REEL = photos.DOSSIER  # vraie photothèque (avant le remplacement par le dossier vide des tests)
LICENCES_LIBRES = ("CC0", "Public domain", "Domaine public")


def image(format="PNG", taille=(2400, 1600), mode="RGB", **options) -> bytes:
    tampon = io.BytesIO()
    Image.new(mode, taille, (200, 120, 40, 128)[: len(mode)] if mode != "RGB" else (200, 120, 40)).save(tampon, format, **options)
    return tampon.getvalue()


@pytest.fixture
def phototheque(tmp_path, monkeypatch):
    """Photothèque factice : 3 illustrations pour la famille « bouche » (boulangerie)."""
    dossier = tmp_path / "phototheque"
    (dossier / "bouche").mkdir(parents=True)
    lignes = []
    for i in range(3):
        (dossier / "bouche" / f"{i}.jpg").write_bytes(image("JPEG", (1600, 1067)))
        lignes.append({"fichier": f"{i}.jpg", "famille": "bouche", "largeur": 1600, "hauteur": 1067, "titre": f"Pain {i}",
                       "source": f"https://commons.wikimedia.org/wiki/File:Pain_{i}.jpg", "auteur": "Anonyme", "licence": "CC0"})
    (dossier / "catalogue.json").write_text(json.dumps(lignes), encoding="utf-8")
    monkeypatch.setattr(photos, "DOSSIER", dossier)
    photos.catalogue.cache_clear()
    return dossier


# --- Photothèque livrée avec l'application -------------------------------------------------------------------

def test_phototheque_livree_complete_et_libre_de_droits():
    lignes = json.loads((REEL / "catalogue.json").read_text(encoding="utf-8"))
    for famille in [*FAMILLES, *photos.THEMES_TYPES]:
        assert sum(x["famille"] == famille for x in lignes) >= 6, famille
    for x in lignes:
        assert x["licence"].startswith(LICENCES_LIBRES), x
        assert x["source"].startswith(("https://stocksnap.io/photo/", "https://commons.wikimedia.org/wiki/File:")), x
        chemin = REEL / x["famille"] / x["fichier"]
        assert chemin.exists() and chemin.stat().st_size < 450_000, chemin
        with Image.open(chemin) as im:
            assert im.format == "JPEG" and im.size == (x["largeur"], x["hauteur"]) and im.width <= 1600


# --- Préparation des photos importées -------------------------------------------------------------------------

def test_photo_importee_reduite_et_sans_metadonnees():
    exif = Image.Exif()
    exif[0x010F] = "Appareil"  # marque de l'appareil
    jpeg, largeur, hauteur = photos.preparer_image(image("JPEG", exif=exif.tobytes()))
    assert (largeur, hauteur) == (1600, 1067) and jpeg.startswith(b"\xff\xd8\xff")
    assert b"Appareil" not in jpeg and b"Exif" not in jpeg


def test_photo_transparente_et_webp_acceptees():
    for donnees in (image("PNG", (800, 600), "RGBA"), image("WEBP", (800, 600))):
        jpeg, largeur, _ = photos.preparer_image(donnees)
        assert jpeg.startswith(b"\xff\xd8\xff") and largeur == 800


@pytest.mark.parametrize("donnees", [b"<svg onload=alert(1)>", b"GIF89a" + b"\0" * 40, b"\x89PNG\r\n\x1a\n" + b"\0" * 40,
                                     b"RIFF\0\0\0\0WAVEfmt "])
def test_fichier_qui_n_est_pas_une_photo_refuse(donnees):
    with pytest.raises(photos.ErreurImport):
        photos.preparer_image(donnees)


def test_photo_trop_lourde_refusee():
    with pytest.raises(photos.ErreurImport, match="15 Mo"):
        photos.preparer_image(b"\xff\xd8\xff" + b"\0" * photos.TAILLE_MAX)


# --- Import dans l'atelier ------------------------------------------------------------------------------------

def importer(client, *fichiers):
    return client.post(f"/demo/{PLACE_ID}/photos", files=[("photos", (nom, donnees, "image/png")) for nom, donnees in fichiers])


def test_import_puis_export_avec_la_photo_du_vendeur(client, google):
    client.get(f"/demo/{PLACE_ID}")
    r = importer(client, ("vitrine.png", image()))
    assert r.status_code == 200 and len(r.json()["ajoutees"]) == 1
    nom = r.json()["ajoutees"][0]
    assert nom.startswith("import/")
    atelier = client.get(f"/demo/{PLACE_ID}").text
    assert f'value="{nom}" checked' in atelier and "Importée" in atelier
    assert client.get("/photo", params={"nom": nom}).headers["content-type"] == "image/jpeg"
    # Aperçu : la photo importée en tête, puis les photos Google
    apercu = client.get(f"/maquette/{PLACE_ID}").text
    assert apercu.index(f"/photo?nom={nom.replace('/', '%2F')}") < apercu.index("/photo?nom=places")
    # Export : la photo du vendeur, intégrée à la page ; aucune photo Google
    export = client.get(f"/maquette/{PLACE_ID}", params={"export": 1}).text
    assert export.count("data:image/jpeg;base64,") >= 1
    for interdit in CONTENU_GOOGLE:
        assert interdit not in export, interdit


def test_retrait_d_une_photo_importee(client, google):
    client.get(f"/demo/{PLACE_ID}")
    nom = importer(client, ("a.png", image())).json()["ajoutees"][0]
    client.post(f"/demo/{PLACE_ID}/options", data={"photos_choisies": "1", "photos": [nom, f"places/{PLACE_ID}/photos/photo0"]})
    assert client.post(f"/demo/{PLACE_ID}/photos/retirer", data={"nom": nom}).status_code == 204
    assert client.get("/photo", params={"nom": nom}).status_code == 404
    assert nom not in client.get(f"/demo/{PLACE_ID}").text
    assert client.post(f"/demo/{PLACE_ID}/photos/retirer", data={"nom": nom}).status_code == 404


def test_import_refuse_un_fichier_qui_n_est_pas_une_photo(client, google):
    client.get(f"/demo/{PLACE_ID}")
    r = importer(client, ("page.html", b"<script>alert(1)</script>"))
    assert r.status_code == 400 and "page.html" in r.json()["erreurs"][0]


def test_import_refuse_depuis_un_autre_site(client, google):
    client.get(f"/demo/{PLACE_ID}")
    r = client.post(f"/demo/{PLACE_ID}/photos", files=[("photos", ("a.png", image(), "image/png"))],
                    headers={"origin": "https://site-malveillant.example"})
    assert r.status_code == 403


def test_nombre_de_photos_importees_limite():
    imports = photos.Imports()
    petite = image("PNG", (40, 30))
    for _ in range(photos.MAX_IMPORTS):
        imports.ajouter("x", petite)
    with pytest.raises(photos.ErreurImport):
        imports.ajouter("x", petite)
    assert len(imports.liste("y")) == 0


# --- Photos d'illustration ------------------------------------------------------------------------------------

def test_export_illustre_avec_la_phototheque(client, google, phototheque):
    client.get(f"/demo/{PLACE_ID}/envoyer")
    export = client.get(f"/maquette/{PLACE_ID}", params={"export": 1}).text
    assert export.count("data:image/jpeg;base64,") == 3 and "Photos d&#39;illustration" in export
    assert "Vos photos ici" not in export
    for interdit in CONTENU_GOOGLE:
        assert interdit not in export, interdit


def test_photos_google_remplacees_par_des_illustrations_a_l_export(client, google, phototheque):
    client.get(f"/demo/{PLACE_ID}")
    choix = [f"places/{PLACE_ID}/photos/photo{i}" for i in range(4)]
    client.post(f"/demo/{PLACE_ID}/options", data={"photos_choisies": "1", "photos": choix})
    export = client.get(f"/maquette/{PLACE_ID}", params={"export": 1}).text
    # 4 photos choisies : 3 illustrations, puis un emplacement (photothèque épuisée)
    assert export.count("data:image/jpeg;base64,") == 3 and export.count('class="photo emplacement-photo') == 1
    apercu = client.get(f"/maquette/{PLACE_ID}").text
    assert "data:image" not in apercu and apercu.count("/photo?nom=places") == 4


def test_illustration_choisie_dans_l_atelier(client, google, phototheque):
    atelier = client.get(f"/demo/{PLACE_ID}").text
    assert 'value="biblio/bouche/0.jpg"' in atelier and "Illustration" in atelier
    client.post(f"/demo/{PLACE_ID}/options", data={"photos_choisies": "1", "photos": ["biblio/bouche/2.jpg"]})
    apercu = client.get(f"/maquette/{PLACE_ID}").text
    assert "/photo?nom=biblio%2Fbouche%2F2.jpg" in apercu and "Photo d&#39;illustration" in apercu
    assert client.get("/photo", params={"nom": "biblio/bouche/2.jpg"}).status_code == 200


@pytest.mark.parametrize("nom", ["biblio/../catalogue.json", "biblio/bouche/../../secret", "biblio/bouche/9.jpg", "import/inconnu"])
def test_photo_hors_catalogue_introuvable(client, phototheque, nom):
    assert client.get("/photo", params={"nom": nom}).status_code == 404


@pytest.mark.parametrize("type_principal, metier, theme", [
    ("car_repair", "", "garage"), ("", "Garage automobile", "garage"), ("", "Carrosserie Dupont", "garage"),
    ("florist", "", "fleuriste"), ("", "Artisan fleuriste", "fleuriste"),
    ("real_estate_agency", "", "immobilier"), ("", "Agence immobilière", "immobilier"),
    ("bakery", "Boulangerie", ""), ("", "Plombier", ""),
])
def test_theme_de_photos_selon_le_metier(type_principal, metier, theme):
    assert photos.theme_de(type_principal, [], metier) == theme


def test_garage_illustre_avec_ses_propres_photos(tmp_path, monkeypatch, google):
    """Un garage garde la mise en page de sa famille mais reçoit les photos du thème « garage »."""
    dossier = tmp_path / "phototheque"
    (dossier / "garage").mkdir(parents=True)
    (dossier / "garage" / "01.jpg").write_bytes(image("JPEG", (960, 640)))
    (dossier / "catalogue.json").write_text(json.dumps([{"fichier": "01.jpg", "famille": "garage", "largeur": 960, "hauteur": 640,
        "titre": "Moteur", "source": "https://stocksnap.io/photo/x", "auteur": "A", "licence": "CC0 1.0"}]), encoding="utf-8")
    monkeypatch.setattr(photos, "DOSSIER", dossier)
    photos.catalogue.cache_clear()
    import asyncio
    from demo_express import places
    fiche = asyncio.run(places.details("CLE", PLACE_ID))
    fiche = maquette.replace(fiche, type_principal="car_repair", types=["car_repair"], metier="Garage", photos=[])
    ctx = maquette.contexte(fiche)
    assert [p.nom for p in ctx["photos"]] == ["biblio/garage/01.jpg"] and ctx["famille"].code == "services"


def test_pied_de_page_de_l_export_signe_par_l_agence(client, google, phototheque, reglages):
    client.get(f"/demo/{PLACE_ID}")
    export = html.unescape(client.get(f"/maquette/{PLACE_ID}", params={"export": 1}).text)
    assert "Nous complèterons votre site par vos photos, vos avis et vos horaires. Photos d'illustration." in export
    assert "Démo Express" not in export and "réalisée par" not in export  # vendeur sans nom ni agence
    reglages.enregistrer_vendeur("Camille Durand", "Agence Pixel", "", "")
    export = html.unescape(client.get(f"/maquette/{PLACE_ID}", params={"export": 1}).text)
    assert "Maquette réalisée par Agence Pixel" in export
    reglages.enregistrer_vendeur("Camille Durand", "", "", "")
    export = html.unescape(client.get(f"/maquette/{PLACE_ID}", params={"export": 1}).text)
    assert "Maquette réalisée par Camille Durand" in export


@pytest.fixture
def phototheque_themes(tmp_path, monkeypatch):
    """Photothèque factice : 1 photo « services » et 1 photo « fleuriste »."""
    dossier = tmp_path / "phototheque-themes"
    lignes = []
    for theme in ("services", "fleuriste"):
        (dossier / theme).mkdir(parents=True)
        (dossier / theme / "01.jpg").write_bytes(image("JPEG", (960, 640)))
        lignes.append({"fichier": "01.jpg", "famille": theme, "largeur": 960, "hauteur": 640, "titre": theme,
                       "source": "https://stocksnap.io/photo/x", "auteur": "A", "licence": "CC0 1.0"})
    (dossier / "catalogue.json").write_text(json.dumps(lignes), encoding="utf-8")
    monkeypatch.setattr(photos, "DOSSIER", dossier)
    photos.catalogue.cache_clear()


def test_fiche_sans_metier_devinee_d_apres_la_recherche(phototheque_themes):
    from demo_express.familles import famille_de
    assert photos.theme_de("", [], "", "fleuriste Saint-Andiol") == "fleuriste"
    assert photos.theme_de("", [], "Boulangerie", "fleuriste") == ""  # la recherche ne sert que si la fiche est muette
    assert photos.theme_de("", ["premise", "establishment"], "", "fleuriste") == "fleuriste"  # types génériques
    assert photos.theme_de("bakery", ["bakery"], "", "fleuriste") == ""
    assert famille_de("", [], "", "plombier Avignon").code == "batiment"


def test_illustrations_choisies_par_le_vendeur(client, google, phototheque_themes):
    atelier = client.get(f"/demo/{PLACE_ID}").text
    assert '<option value="fleuriste"' in atelier and "Automatique" in atelier
    client.post(f"/demo/{PLACE_ID}/options", data={"illustrations": "fleuriste", "modele": "services"})
    export = client.get(f"/maquette/{PLACE_ID}", params={"export": 1}).text
    assert export.count("data:image/jpeg;base64,") == 1
    atelier = client.get(f"/demo/{PLACE_ID}").text
    assert 'value="biblio/fleuriste/01.jpg"' in atelier and 'value="biblio/services/01.jpg"' not in atelier
    assert '<option value="fleuriste" selected>' in atelier
    client.post(f"/demo/{PLACE_ID}/options", data={"illustrations": "inconnu"})
    assert '<option value="" selected>' in client.get(f"/demo/{PLACE_ID}").text


def test_recherche_retenue_pour_une_fiche_muette(client, google, phototheque_themes):
    client.get("/", params={"q": "fleuriste Lyon"})
    atelier = client.get(f"/demo/{PLACE_ID}").text
    # La fiche de test est une boulangerie (type « bakery ») : son métier l'emporte sur la recherche
    assert 'value="biblio/fleuriste/01.jpg"' not in atelier
