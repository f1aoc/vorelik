"""Réglages de Démo Express, enregistrés dans le dossier de données de l'utilisateur.

Dossier : variable DEMO_DONNEES, sinon ~/.demo-express. La clé Google Places y est chiffrée (secret.py),
jamais écrite en clair. Les données Google des démos ne sont pas enregistrées : elles restent en mémoire
le temps de la session.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from demo_express import secret
from demo_express.langue import AUTO, LANGUES, definir_langue

FICHIER = "reglages.json"


def dossier_par_defaut() -> Path:
    return Path(os.environ.get("DEMO_DONNEES") or Path.home() / ".demo-express")


@dataclass
class Reglages:
    dossier: Path

    def __post_init__(self) -> None:
        self.dossier.mkdir(parents=True, exist_ok=True)
        definir_langue(self.langue)

    @property
    def _chemin(self) -> Path:
        return self.dossier / FICHIER

    def _lire(self) -> dict:
        try:
            return json.loads(self._chemin.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return {}

    def _ecrire(self, donnees: dict) -> None:
        temporaire = self._chemin.with_suffix(".tmp")
        temporaire.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
        temporaire.replace(self._chemin)

    # --- Clé Google Places -------------------------------------------------------------------------------

    @property
    def cle_google(self) -> str:
        jeton = self._lire().get("cle_google", "")
        return secret.dechiffrer(self.dossier, jeton) if jeton else os.environ.get("GOOGLE_MAPS_API_KEY", "")

    def enregistrer_cle(self, cle: str) -> None:
        donnees = self._lire()
        cle = cle.strip()
        if cle:
            donnees["cle_google"] = secret.chiffrer(self.dossier, cle)
        else:
            donnees.pop("cle_google", None)
        self._ecrire(donnees)

    # --- Langue -------------------------------------------------------------------------------------------

    @property
    def langue(self) -> str:
        choix = self._lire().get("langue", AUTO)
        return choix if choix in LANGUES else AUTO

    def enregistrer_langue(self, choix: str) -> None:
        donnees = self._lire()
        donnees["langue"] = choix if choix in LANGUES else AUTO
        self._ecrire(donnees)
        definir_langue(donnees["langue"])
