"""Série 2 de publications VORELIK : 10 visuels 1080 × 1350 (Facebook, Instagram, LinkedIn), en français et en anglais.

python3 posts.py DOSSIER   puis   node ../facebook/rendu.cjs DOSSIER   (Playwright)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "facebook"))
from facebook import A, BASE, FONDS, ICONES, LOGO, R, fond  # noqa: E402

ICONES = {**ICONES, "dex": A / "demo-express-icone.png"}
FONDS["dex"] = ("#DB2777", "#7C3AED", "#F59E0B")
DEX = {"fr": R / "demo-express/site/assets", "en": R / "vitrine-en/demo-express/assets"}
BTL = {"fr": A / "bridgetoleads-apercu.jpg", "en": R / "vitrine-en/bridgetoleads/assets/app-screenshot.png"}

CSS = """<style>
  html, body { width: 1080px; height: 1350px; }
  .page { position: absolute; inset: 0; padding: 64px 64px 60px; display: flex; flex-direction: column; }
  .tete { display: flex; align-items: center; justify-content: space-between; height: 76px; }
  .tete .logo { width: 230px; }
  .tete .pastille { font-size: 28px; }
  h1 { margin-top: 56px; font-size: 88px; line-height: 1.02; letter-spacing: -.035em; text-shadow: 0 6px 0 rgba(0,0,0,.3), 0 18px 40px rgba(0,0,0,.45); }
  h1.petit { font-size: 74px; }
  .sous { margin-top: 26px; font-size: 32px; line-height: 1.35; color: #DDE2F2; font-weight: 600; max-width: 900px; }
  .corps { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 18px; margin: 34px 0; position: relative; }
  .bas { display: flex; align-items: center; justify-content: space-between; }
  .bouton { font-size: 30px; }
  .bas .logo { width: 190px; }
  .ligne { display: flex; align-items: center; gap: 22px; background: rgba(10,15,31,.55); padding: 20px 26px 20px 20px; border-radius: 24px;
     box-shadow: inset 0 0 0 2px rgba(255,255,255,.14); }
  .ligne .num { flex: none; width: 64px; height: 64px; border-radius: 18px; display: grid; place-items: center; font-size: 34px; font-weight: 800;
     background: #fff; color: #1E1B4B; }
  .ligne .num.rouge { background: #DC2626; color: #fff; } .ligne .num.vert { background: #10B981; color: #fff; }
  .ligne img { flex: none; width: 64px; height: 64px; border-radius: 16px; }
  .ligne b { display: block; font-size: 33px; line-height: 1.15; } .ligne span { display: block; font-size: 24px; color: #C3CAE0; margin-top: 4px; line-height: 1.3; }
  .ligne .prix { margin-left: auto; font-size: 40px; font-weight: 800; color: #FDE68A; white-space: nowrap; }
  .citation { font-size: 48px; line-height: 1.15; font-weight: 800; background: #fff; color: #1E1B4B; padding: 34px 40px; border-radius: 30px 30px 30px 6px;
     box-shadow: 0 30px 60px -20px rgba(0,0,0,.7); transform: rotate(-1.5deg); }
  .bulle { font-size: 37px; line-height: 1.35; font-weight: 600; background: rgba(255,255,255,.12); padding: 22px 28px; border-radius: 26px 26px 26px 6px;
     box-shadow: inset 0 0 0 2px rgba(255,255,255,.18); }
  .bulle b { color: #FDE68A; }
  .fen { border-radius: 20px; overflow: hidden; background: #fff; box-shadow: 0 40px 80px -25px rgba(0,0,0,.75), 0 0 0 6px rgba(255,255,255,.95); }
  .fen img { display: block; width: 100%; }
  .eti { position: absolute; font-weight: 800; padding: 14px 28px; border-radius: 18px; font-size: 40px; box-shadow: 0 18px 40px -10px rgba(0,0,0,.6), 0 0 0 5px #fff; }
  .barre { text-decoration: line-through; color: #C3CAE0; font-weight: 700; }
</style>"""


def page(couleur, tete, titre, corps, bouton, sous="", petit=False, logo_bas=True):
    tete_html = (f'<div class="pastille"><img src="{ICONES[tete[0]]}">{tete[1]}</div>' if tete else f'<img class="logo" src="{LOGO}">')
    return (f'<!doctype html><html data-taille="1080x1350"><head><meta charset="utf-8">{BASE}{CSS}</head><body>{fond(couleur)}'
            f'<div class="page"><div class="tete">{tete_html}</div>'
            f'<h1 class="{"petit" if petit else ""}">{titre}</h1>{f"<p class=sous>{sous}</p>" if sous else ""}'
            f'<div class="corps">{corps}</div>'
            f'<div class="bas"><span class="bouton">{bouton}</span>{f"<img class=logo src={LOGO}>" if logo_bas and tete else ""}</div></div></body></html>')


def lignes(elements):
    """elements : (marque, titre, détail[, prix]) ; marque = clé d'icône, ou texte pour une pastille (« 1 », « ✖ rouge »…)."""
    html = ""
    for m, b, s, *prix in elements:
        if m in ICONES:
            pic = f'<img src="{ICONES[m]}">'
        else:
            texte, *classe = m.split(" ")
            taille = ' style="font-size:22px;width:74px"' if len(texte) > 1 else ""
            pic = f'<div class="num {" ".join(classe)}"{taille}>{texte}</div>'
        html += (f'<div class="ligne">{pic}<p><b>{b}</b>{f"<span>{s}</span>" if s else ""}</p>'
                 f'{f"<div class=prix>{prix[0]}</div>" if prix else ""}</div>')
    return html


def fenetre(image, largeur=900, rotation=-2, etiquette=None):
    eti = (f'<div class="eti" style="right:20px;top:-26px;transform:rotate(5deg);background:{etiquette[1]};color:{etiquette[2]}">{etiquette[0]}</div>'
           if etiquette else "")
    return f'<div class="fen" style="width:{largeur}px;align-self:center;transform:rotate({rotation}deg)"><img src="{image}"></div>{eti}'


T = {
    "fr": dict(
        cds="Chasseur de sites", aex="Audit express", site="vorelik.com", essai="vorelik.com/essai", dex_url="vorelik.com/demo-express",
        posts=[
            ("1-demo-express", "dex", ("dex", "Démo Express"), 'Montrez-lui<br>son <span class="jaune">futur site.</span>',
             "Tapez le nom d'un commerce : Démo Express crée la maquette de son site à partir de sa fiche Google, en 2 minutes.",
             "fenetre", "app-screenshot.jpg", ("Nouveau", "#FDE68A", "#1E1B4B"), "Découvrir Démo Express →"),
            ("2-de-la-liste-au-contrat", "vorelik", None, 'De la liste<br>au <span class="jaune">contrat signé.</span>', "",
             "lignes", [("btl", "1. Trouver", "BridgeToLeads et Chasseur de sites : les commerces sans site ou au site dépassé"),
                        ("dex", "2. Montrer", "Démo Express : la maquette de leur futur site, à leur nom"),
                        ("aex", "3. Convaincre", "Audit express : la note de leur site actuel, en PDF"),
                        ("✍ vert", "4. Signer", "Vous faites ce que vous savez faire : leur site")], None, "vorelik.com →"),
            ("3-quoi-dire-au-telephone", "btl", ("btl", "Astuce de prospection"), 'Quoi dire<br>au <span class="jaune">téléphone ?</span>', "",
             "bulles", ["« J'ai vu vos <b>120 avis</b> sur Google, mais aucun site pour vous trouver. »",
                        "« Vos clients cherchent vos <b>horaires</b> et vos <b>tarifs</b> : aujourd'hui, ils ne les trouvent pas. »",
                        "« Je peux vous montrer en <b>10 minutes</b> à quoi ressemblerait le vôtre. »"], None, "Essayez avec 10 prospects gratuits →"),
            ("4-ma-page-facebook-suffit", "cds", None, "L'objection<br>que vous entendez<br><span class=\"jaune\">tout le temps.</span>", "",
             "citation", ("« J'ai une page Facebook, ça suffit. »",
                          [("✔ vert", "Elle n'apparaît pas toujours sur Google", "Un site, si : avec vos horaires, vos services, votre ville"),
                           ("✔ vert", "Elle ne vous appartient pas", "Votre site, oui : votre nom de domaine, vos règles"),
                           ("✔ vert", "Elle parle à vos abonnés", "Votre site parle à ceux qui ne vous connaissent pas encore")]), None, "vorelik.com →"),
            ("5-signes-site-a-refaire", "cds", ("cds", "Chasseur de sites"), '5 signes qu\'un site<br>est <span class="jaune">à refaire.</span>', "",
             "lignes", [("✖ rouge", "« Non sécurisé » dans le navigateur", ""), ("✖ rouge", "Illisible sur téléphone", ""),
                        ("✖ rouge", "« © 2014 » en bas de page", ""), ("✖ rouge", "Plus de 5 secondes pour s'afficher", ""),
                        ("✖ rouge", "Nom de domaine expiré", "")], None, "Chasseur de sites les trouve pour vous →"),
            ("6-paiement-unique", "vorelik", None, 'Payez une fois.<br><span class="jaune">Gardez-le.</span>',
             "Pas d'abonnement. Une licence pour 2 ordinateurs. Windows et Mac.",
             "lignes", [("btl", "BridgeToLeads", "Les commerces sans site web", "59 €"), ("cds", "Chasseur de sites", "Les sites cassés ou dépassés", "99 €"),
                        ("aex", "Audit express", "Un audit qui fait signer", "79 €"), ("dex", "Démo Express", "La maquette de leur futur site", "89 €")],
             None, "vorelik.com →"),
            ("7-pack", "vorelik", None, '3 logiciels.<br><span class="jaune">179 €</span> <span class="barre">237 €</span>',
             "BridgeToLeads, Chasseur de sites et Audit express : 58 € d'économie, en paiement unique.",
             "lignes", [("btl", "BridgeToLeads", "Trouver les commerces sans site"), ("cds", "Chasseur de sites", "Trouver les sites à refaire"),
                        ("aex", "Audit express", "Prouver qu'il faut un nouveau site")], None, "Le pack sur vorelik.com →"),
            ("8-avant-apres", "dex", ("dex", "Démo Express"), 'Avant : une fiche Google.<br>Après : <span class="jaune">un vrai site.</span>',
             "6 modèles selon le métier : restaurant, artisan, beauté, santé, bâtiment… La maquette est prête avant le rendez-vous.",
             "fenetre", "modeles.jpg", None, "Découvrir Démo Express →"),
            ("9-semaine-de-prospection", "vorelik", None, 'Votre semaine<br>de <span class="jaune">prospection.</span>', "",
             "lignes", [("Lun", "La liste", "BridgeToLeads : les commerces sans site de votre ville"),
                        ("Mar", "Les maquettes", "Démo Express : leur futur site, pour les 10 meilleurs"),
                        ("Mer", "Les appels", "Vous montrez la maquette, ils voient leur nom"),
                        ("Jeu", "Les audits", "Audit express : pour ceux qui ont déjà un vieux site"),
                        ("Ven", "Les rendez-vous", "Et les premiers devis signés")], None, "vorelik.com →"),
            ("10-defi-essai-gratuit", "btl", ("btl", "Essai gratuit"), 'Combien de<br><span class="jaune">plombiers sans site</span><br>dans votre ville ?',
             "Choisissez un métier et une ville : la réponse arrive dans votre boîte mail, avec les 10 plus établis.",
             "fenetre-btl", None, ("100 % gratuit", "#FDE68A", "#1E1B4B"), "vorelik.com/essai →"),
        ]),
    "en": dict(
        cds="Site Hunter", aex="Audit Express", site="vorelik.com/en", essai="vorelik.com/en/trial", dex_url="vorelik.com/en/demo-express",
        posts=[
            ("1-demo-express", "dex", ("dex", "Démo Express"), 'Show them<br>their <span class="jaune">future website.</span>',
             "Type a business name: Démo Express builds a mockup of their website from their Google listing, in 2 minutes.",
             "fenetre", "app-screenshot.jpg", ("New", "#FDE68A", "#1E1B4B"), "Discover Démo Express →"),
            ("2-from-list-to-contract", "vorelik", None, 'From prospect list<br>to <span class="jaune">signed contract.</span>', "",
             "lignes", [("btl", "1. Find", "BridgeToLeads and Site Hunter: businesses with no website or an outdated one"),
                        ("dex", "2. Show", "Démo Express: a mockup of their future website, in their name"),
                        ("aex", "3. Convince", "Audit Express: their current website's grade, as a PDF"),
                        ("✍ vert", "4. Sign", "You do what you do best: build their website")], None, "vorelik.com/en →"),
            ("3-what-to-say-on-the-phone", "btl", ("btl", "Prospecting tip"), 'What to say<br>on the <span class="jaune">phone?</span>', "",
             "bulles", ["“I saw your <b>120 reviews</b> on Google, but no website for people to find you.”",
                        "“Your customers look for your <b>hours</b> and <b>prices</b>: right now, they can't find them.”",
                        "“I can show you in <b>10 minutes</b> what yours could look like.”"], None, "Try it with 10 free leads →"),
            ("4-my-facebook-page-is-enough", "cds", None, 'The objection<br>you hear<br><span class="jaune">all the time.</span>', "",
             "citation", ("“My Facebook page is enough.”",
                          [("✔ vert", "It doesn't always show up on Google", "A website does: with your hours, services and city"),
                           ("✔ vert", "It isn't yours", "Your website is: your domain name, your rules"),
                           ("✔ vert", "It talks to your followers", "Your website talks to people who don't know you yet")]), None, "vorelik.com/en →"),
            ("5-signs-website-needs-redo", "cds", ("cds", "Site Hunter"), '5 signs a website<br><span class="jaune">needs a redo.</span>', "",
             "lignes", [("✖ rouge", "“Not secure” in the browser", ""), ("✖ rouge", "Unreadable on a phone", ""),
                        ("✖ rouge", "“© 2014” in the footer", ""), ("✖ rouge", "Over 5 seconds to load", ""),
                        ("✖ rouge", "Expired domain name", "")], None, "Site Hunter finds them for you →"),
            ("6-one-time-payment", "vorelik", None, 'Pay once.<br><span class="jaune">Keep it.</span>',
             "No subscription. One licence for 2 computers. Windows and Mac.",
             "lignes", [("btl", "BridgeToLeads", "Businesses with no website", "$69"), ("cds", "Site Hunter", "Broken or outdated websites", "$109"),
                        ("aex", "Audit Express", "Audits that win deals", "$89"), ("dex", "Démo Express", "A mockup of their future website", "$99")],
             None, "vorelik.com/en →"),
            ("7-bundle", "vorelik", None, '3 apps.<br><span class="jaune">$199</span> <span class="barre">$267</span>',
             "BridgeToLeads, Site Hunter and Audit Express: save $68, one-time payment.",
             "lignes", [("btl", "BridgeToLeads", "Find businesses with no website"), ("cds", "Site Hunter", "Find websites that need a redo"),
                        ("aex", "Audit Express", "Prove they need a new website")], None, "The bundle on vorelik.com/en →"),
            ("8-before-after", "dex", ("dex", "Démo Express"), 'Before: a Google listing.<br>After: <span class="jaune">a real website.</span>',
             "6 layouts by trade: restaurant, food shop, beauty, health, trades… The mockup is ready before the meeting.",
             "fenetre", "modeles.jpg", None, "Discover Démo Express →"),
            ("9-prospecting-week", "vorelik", None, 'Your<br><span class="jaune">prospecting week.</span>', "",
             "lignes", [("Mon", "The list", "BridgeToLeads: the businesses with no website in your city"),
                        ("Tue", "The mockups", "Démo Express: their future website, for the top 10"),
                        ("Wed", "The calls", "You show the mockup, they see their name"),
                        ("Thu", "The audits", "Audit Express: for those with an old website"),
                        ("Fri", "The meetings", "And the first signed quotes")], None, "vorelik.com/en →"),
            ("10-free-trial-challenge", "btl", ("btl", "Free trial"), 'How many<br><span class="jaune">plumbers with no website</span><br>in your city?',
             "Pick a trade and a city: the answer lands in your inbox, with the 10 most established.",
             "fenetre-btl", None, ("100% free", "#FDE68A", "#1E1B4B"), "vorelik.com/en/trial →"),
        ]),
}


def construire(langue, p):
    nom, couleur, tete, titre, sous, genre, contenu, etiquette, bouton = p
    if genre == "fenetre":
        corps = f'<div style="position:relative;align-self:center">{fenetre(DEX[langue] / contenu, 920 if "modeles" in contenu else 860, -2, etiquette)}</div>'
    elif genre == "fenetre-btl":
        corps = f'<div style="position:relative;align-self:center">{fenetre(BTL[langue], 840, -3, etiquette)}</div>'
    elif genre == "bulles":
        corps = "".join(f'<div class="bulle" style="align-self:{"flex-start" if i % 2 == 0 else "flex-end"};max-width:880px">{b}</div>'
                        for i, b in enumerate(contenu))
    elif genre == "citation":
        corps = f'<div class="citation">{contenu[0]}</div><div style="height:16px"></div>{lignes(contenu[1])}'
    else:
        corps = lignes(contenu)
    petit = len(titre) > 70 or genre in ("citation",)
    return f"vorelik-{langue}-{nom}", page(couleur, tete, titre, corps, bouton, sous, petit)


if __name__ == "__main__":
    sortie = Path(sys.argv[1])
    for langue, t in T.items():
        for p in t["posts"]:
            nom, html = construire(langue, p)
            (sortie / f"{nom}.html").write_text(html)
    print("ok")
