"""Message de prospection qui accompagne la maquette : e-mail (objet + texte) et SMS, en français ou en anglais.

Deux versions : entreprise sans site, ou entreprise dont le site existe déjà (proposition de refonte).
Le message propose toujours de ne plus être recontacté (prospection B2B : droit d'opposition).
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from demo_express.familles import Famille
from demo_express.langue import langue_courante

MODELES = {
    "fr": {
        "objet_sans_site": "Une idée de site internet pour {nom}",
        "objet_avec_site": "Une nouvelle version du site de {nom}",
        "corps_sans_site": (
            "Bonjour,\n\n"
            "J'ai découvert {nom}{a_ville} et j'ai remarqué que vous n'avez pas encore de site internet.\n\n"
            "J'ai pris l'initiative de préparer une maquette de ce à quoi il pourrait ressembler (en pièce jointe) : "
            "vos clients y trouveraient en un coup d'œil vos services, vos coordonnées et un bouton pour {action}.\n\n"
            "Les photos, les avis et les horaires sont à compléter : le site final utiliserait les vôtres.\n\n"
            "Seriez-vous d'accord pour en parler dix minutes cette semaine ?\n\n"
            "{signature}"
            "Si vous préférez ne plus recevoir de message de ma part, il suffit de me le dire."
        ),
        "corps_avec_site": (
            "Bonjour,\n\n"
            "J'ai découvert {nom}{a_ville} et j'ai regardé votre site internet.\n\n"
            "J'ai pris l'initiative de préparer une maquette d'une version plus moderne (en pièce jointe), pensée d'abord "
            "pour le téléphone, avec un bouton pour {action} bien visible.\n\n"
            "Les photos, les avis et les horaires sont à compléter : le site final utiliserait les vôtres.\n\n"
            "Seriez-vous d'accord pour en parler dix minutes cette semaine ?\n\n"
            "{signature}"
            "Si vous préférez ne plus recevoir de message de ma part, il suffit de me le dire."
        ),
        "sms": "Bonjour, {presentation}j'ai préparé une maquette de site internet pour {nom}, sans engagement. "
               "Puis-je vous l'envoyer par e-mail ?{tel} (Répondez STOP pour ne plus recevoir de message.)",
        "presentation": "ici {qui}, ",
        "a_ville": " à {ville}",
    },
    "en": {
        "objet_sans_site": "A website idea for {nom}",
        "objet_avec_site": "A new version of {nom}'s website",
        "corps_sans_site": (
            "Hello,\n\n"
            "I came across {nom}{a_ville} and noticed you don't have a website yet.\n\n"
            "I took the liberty of preparing a mockup of what it could look like (attached): your customers would "
            "see your services, your contact details and a button to {action} at a glance.\n\n"
            "The photos, reviews and opening hours are placeholders: the final website would use yours.\n\n"
            "Would you be open to a ten-minute chat this week?\n\n"
            "{signature}"
            "If you'd rather not hear from me again, just let me know."
        ),
        "corps_avec_site": (
            "Hello,\n\n"
            "I came across {nom}{a_ville} and had a look at your website.\n\n"
            "I took the liberty of preparing a mockup of a more modern version (attached), designed for mobile "
            "first, with a clear button to {action}.\n\n"
            "The photos, reviews and opening hours are placeholders: the final website would use yours.\n\n"
            "Would you be open to a ten-minute chat this week?\n\n"
            "{signature}"
            "If you'd rather not hear from me again, just let me know."
        ),
        "sms": "Hello, {presentation}I've prepared a website mockup for {nom}, no strings attached. "
               "May I email it to you?{tel} (Reply STOP to opt out.)",
        "presentation": "this is {qui}, ",
        "a_ville": " in {ville}",
    },
}


@dataclass
class Vendeur:
    """Signature du vendeur (Réglages)."""
    nom: str = ""
    agence: str = ""
    telephone: str = ""
    email: str = ""

    def signature(self) -> str:
        lignes = [x for x in (self.nom, self.agence, self.telephone, self.email) if x.strip()]
        return "\n".join(lignes) + "\n\n" if lignes else ""


@dataclass
class Message:
    objet: str
    corps: str
    sms: str

    @property
    def lien_mail(self) -> str:
        """Ouvre la messagerie avec l'objet et le texte (la pièce jointe s'ajoute à la main)."""
        return f"mailto:?subject={quote(self.objet)}&body={quote(self.corps)}"


def rediger(nom: str, ville: str, famille: Famille, action: str, a_un_site: bool, vendeur: Vendeur) -> Message:
    langue = langue_courante()
    m = MODELES[langue]
    variante = "avec_site" if a_un_site else "sans_site"
    # « Prendre rendez-vous » → « prendre rendez-vous » au milieu d'une phrase
    action = (action or famille.action[langue]).strip()
    action = action[:1].lower() + action[1:]
    a_ville = m["a_ville"].format(ville=ville) if ville else ""
    qui = ", ".join(x for x in (vendeur.nom.strip(), vendeur.agence.strip()) if x)
    return Message(
        objet=m[f"objet_{variante}"].format(nom=nom),
        corps=m[f"corps_{variante}"].format(nom=nom, a_ville=a_ville, action=action, signature=vendeur.signature()),
        sms=m["sms"].format(nom=nom, presentation=m["presentation"].format(qui=qui) if qui else "",
                            tel=f" {vendeur.telephone.strip()}" if vendeur.telephone.strip() else ""),
    )
