"""Téléchargements des logiciels depuis Cloudflare R2 (via le serveur de licences) au lieu de GitHub.

    python .github/scripts/telechargements_r2.py public

Vérifie d'abord que les 9 fichiers répondent sur https://…workers.dev/telecharger/<fichier> ; si oui, remplace dans
toutes les pages les liens GitHub par ces liens. Sinon, garde les liens GitHub et le signale (avertissement GitHub
Actions) : une page de vente ne doit jamais proposer un téléchargement qui ne marche pas.
Démo Express (3 fichiers) est traité à part : ses liens passent sur R2 seulement quand ses propres fichiers y sont.
"""

import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SERVEUR = "https://licences.patrick-tabountchikoff.workers.dev/telecharger"
FICHIERS = [f"{nom}{fin}" for nom, win in (("BridgeToLeads", ".exe"), ("ChasseurDeSites", ".exe"), ("AuditExpress", "-Windows.zip"))
            for fin in (win, "-mac-apple-silicon.zip", "-mac-intel.zip")]
GITHUB = [
    ("https://github.com/f1aoc/vorelik/releases/download/chasseurdesites-latest/", SERVEUR + "/"),
    ("https://github.com/f1aoc/vorelik/releases/download/bridgetoleads-latest/", SERVEUR + "/"),
    ("https://github.com/f1aoc/audit_express/releases/download/auditexpress-latest/", SERVEUR + "/"),
    # pages Merci : constante + chemin construits dans le script
    ("${TELECHARGEMENTS}/chasseurdesites-latest/", "${TELECHARGEMENTS}/"),
    ("${TELECHARGEMENTS}/bridgetoleads-latest/", "${TELECHARGEMENTS}/"),
    ('"https://github.com/f1aoc/vorelik/releases/download"', f'"{SERVEUR}"'),
    ('"https://github.com/f1aoc/audit_express/releases/download/auditexpress-latest/AuditExpress"', f'"{SERVEUR}/AuditExpress"'),
]


def present(fichier: str, essai: int = 1) -> bool:
    requete = urllib.request.Request(f"{SERVEUR}/{fichier}", method="HEAD", headers={"User-Agent": "vorelik-site/1.0"})
    try:
        with urllib.request.urlopen(requete, timeout=30) as r:
            taille = int(r.headers.get("Content-Length") or 0)
            print(f"{fichier} : HTTP {r.status}, {taille} octets")
            return r.status == 200 and taille > 1_000_000
    except urllib.error.HTTPError as e:
        print(f"{fichier} : HTTP {e.code} {e.read(300)!r}")
        return False
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"{fichier} : {e}")
        if essai < 3:  # coupure réseau passagère : nouvel essai
            time.sleep(5 * essai)
            return present(fichier, essai + 1)
        return False


# Démo Express : ses 3 fichiers, ses liens (adresse complète, ou constante DEMO des pages Merci)
FICHIERS_DEMO = ["DemoExpress.exe", "DemoExpress-mac-apple-silicon.zip", "DemoExpress-mac-intel.zip"]
GITHUB_DEMO = [
    ("https://github.com/f1aoc/vorelik/releases/download/demoexpress-latest/", SERVEUR + "/"),
]
DEMO_SUR_GITHUB = re.compile(r"github\.com/f1aoc/vorelik/releases/download/demoexpress-latest/")

racine = Path(sys.argv[1])
demo_sur_r2 = all(present(f) for f in FICHIERS_DEMO)
if not demo_sur_r2:
    print("::warning::Téléchargements de Démo Express laissés sur GitHub : fichiers absents de Cloudflare R2")
else:
    for page in sorted(racine.rglob("*.html")):
        texte = page.read_text(encoding="utf-8")
        nouveau = texte
        for ancien, neuf in GITHUB_DEMO:
            nouveau = nouveau.replace(ancien, neuf)
        if nouveau != texte:
            page.write_text(nouveau, encoding="utf-8")
            print(f"{page.relative_to(racine)} : Démo Express depuis Cloudflare R2")

manquants = [f for f in FICHIERS if not present(f)]
if manquants:
    print(f"::warning::Téléchargements laissés sur GitHub : fichiers absents de Cloudflare R2 : {', '.join(manquants)}")
    sys.exit(0)
for page in sorted(racine.rglob("*.html")):
    texte = page.read_text(encoding="utf-8")
    nouveau = texte
    for ancien, neuf in GITHUB:
        nouveau = nouveau.replace(ancien, neuf)
    if nouveau != texte:
        page.write_text(nouveau, encoding="utf-8")
        print(f"{page.relative_to(racine)} : téléchargements depuis Cloudflare R2")
    # Liens de Démo Express encore sur GitHub (ses fichiers ne sont pas encore sur R2) : attendus
    if re.search(r"github\.com/f1aoc/[\w-]+/releases/download", DEMO_SUR_GITHUB.sub("", nouveau)):
        sys.exit(f"{page.relative_to(racine)} : lien de téléchargement GitHub non converti")
