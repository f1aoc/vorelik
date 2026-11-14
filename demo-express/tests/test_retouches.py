import html

import pytest

from demo_express import maquette, places
from demo_express.familles import FAMILLES
from conftest import PLACE_ID, fiche_google

MARQUES = {  # élément propre à chaque mise en page
    "restaurant": 'class="filet"', "bouche": 'class="arche"', "beaute": 'class="duo"',
    "batiment": 'class="appel-devis"', "sante": 'class="carte-photo"', "services": 'class="carte-inclinee"',
}


def fiche(**autres):
    return places.vers_fiche(fiche_google(**autres))


@pytest.mark.parametrize("code", list(FAMILLES))
def test_chaque_modele_a_sa_mise_en_page(code):
    page = maquette.rendre(fiche(), maquette.Options(modele=code))
    assert f'class="modele-{code}"' in page and MARQUES[code] in page
    for autre, marque in MARQUES.items():
        if autre != code:
            assert marque not in page
    # Ordre des sections propre au modèle
    positions = [page.index(f'id="{s.replace("_", "-")}"') for s in maquette.ORDRES[code]]
    assert positions == sorted(positions)
    assert "Maquette de démonstration" in page and "Photos et avis : Google" in page


def test_couleur_inseree_dans_le_css_uniquement_si_valide():
    piege = maquette.Options(couleur="red;}</style><script>alert(1)</script>").nettoyer()
    assert piege.couleur == ""
    page = maquette.rendre(fiche(), maquette.Options(couleur="red;}</style><script>alert(1)</script>"))
    assert "<script>" not in page and f"--couleur: {FAMILLES['bouche'].couleur}" in page
    assert "--couleur: #123ABC" in maquette.rendre(fiche(), maquette.Options(couleur="#123ABC"))


def test_textes_retouches_et_echappes():
    options = maquette.Options(accroche="Le pain <b>du</b> quartier", presentation="Ligne 1\nLigne 2", action="Commander",
                               services=[("Pains", "Au levain"), ("", "ignoré"), ("Viennoiseries", "Pur beurre")])
    page = maquette.rendre(fiche(), options)
    assert "Le pain &lt;b&gt;du&lt;/b&gt; quartier" in page and "Ligne 1\nLigne 2" in page and ">Commander<" in page
    assert "Pains" in page and "Viennoiseries" in page and "ignoré" not in page and "Nos spécialités" not in page


def test_textes_trop_longs_coupes():
    o = maquette.Options(accroche="x" * 500, presentation="y" * 5000, services=[("t" * 200, "d" * 900)] * 10).nettoyer()
    assert len(o.accroche) == 120 and len(o.presentation) == 900 and len(o.services) == 6
    assert len(o.services[0][0]) == 60 and len(o.services[0][1]) == 220


def test_photos_choisies_ordre_et_aucune():
    f = fiche()
    page = maquette.rendre(f, maquette.Options(photos=[f.photos[4].nom, f.photos[2].nom, f.photos[7].nom]))
    assert page.index("photo4") < page.index("photo2") < page.index("photo7") and "photo0" not in page
    sans = maquette.rendre(f, maquette.Options(photos=[]))
    assert "/photo?" not in sans and 'id="galerie"' not in sans


def test_sections_masquees():
    page = maquette.rendre(fiche(), maquette.Options(sections=["a_propos", "infos", "inconnue"]))
    assert 'id="a-propos"' in page and 'id="infos"' in page
    assert 'id="services"' not in page and 'id="avis"' not in page and 'id="galerie"' not in page


def test_modele_inconnu_remplace_par_celui_du_metier():
    assert 'class="modele-bouche"' in maquette.rendre(fiche(), maquette.Options(modele="../../etc"))


# --- Interface de retouches -------------------------------------------------------------------------------

def test_panneau_de_retouches(client, google):
    page = html.unescape(client.get(f"/demo/{PLACE_ID}").text)
    assert page.count('name="modele"') == 6 and 'value="bouche" checked' in page
    assert 'value="Le goût du fait maison, chaque jour"' in page
    assert page.count('name="photos"') == 10 and page.count('name="sections"') == 5


def test_retouches_appliquees_a_la_maquette(client, google):
    client.get(f"/demo/{PLACE_ID}")
    photos = [f"places/{PLACE_ID}/photos/photo{i}" for i in (3, 1, 5)]
    r = client.post(f"/demo/{PLACE_ID}/options", data={
        "modele": "beaute", "accroche": "Votre pause gourmande", "presentation": "", "couleur": "#0E7490", "action": "",
        "services_choisis": "1", "service_titre": ["Pains", "Gâteaux"], "service_texte": ["Au levain", "Sur commande"],
        "photos_choisies": "1", "photos": photos, "sections_choisies": "1", "sections": ["a_propos", "services", "infos"],
    })
    assert r.status_code == 204
    page = client.get(f"/maquette/{PLACE_ID}").text
    assert 'class="modele-beaute"' in page and "Votre pause gourmande" in page and "--couleur: #0E7490" in page
    assert "Gâteaux" in page and page.index("photo3") < page.index("photo1") and "photo0" not in page
    assert 'id="avis"' not in page
    # Le panneau reflète les retouches
    panneau = html.unescape(client.get(f"/demo/{PLACE_ID}").text)
    assert 'value="beaute" checked' in panneau and 'value="Votre pause gourmande"' in panneau
    assert "Revenir à la maquette d'origine" in panneau


def test_valeurs_par_defaut_non_figees(client, google):
    """Texte laissé tel quel puis changement de modèle : le texte du nouveau modèle s'affiche."""
    client.get(f"/demo/{PLACE_ID}")
    client.post(f"/demo/{PLACE_ID}/options", data={"modele": "bouche", "accroche": "Le goût du fait maison, chaque jour"})
    client.post(f"/demo/{PLACE_ID}/options", data={"modele": "batiment", "accroche": ""})
    assert "Des travaux bien faits" in client.get(f"/maquette/{PLACE_ID}").text


def test_reinitialiser(client, google):
    client.get(f"/demo/{PLACE_ID}")
    client.post(f"/demo/{PLACE_ID}/options", data={"accroche": "Retouchée"})
    assert client.post(f"/demo/{PLACE_ID}/reinitialiser").status_code == 303
    assert "Retouchée" not in client.get(f"/maquette/{PLACE_ID}").text


def test_retouches_protegees(client, google):
    client.get(f"/demo/{PLACE_ID}")
    r = client.post(f"/demo/{PLACE_ID}/options", data={"accroche": "Pirate"}, headers={"Origin": "https://pirate.example"})
    assert r.status_code == 403
    assert client.post("/demo/ChIJ_inconnue_000000/options", data={"accroche": "x"}).status_code == 404
