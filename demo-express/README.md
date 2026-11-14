# Démo Express by VORELIK

Fabrique en deux minutes la **maquette de site** d'une entreprise locale, à partir de sa fiche Google :
nom, métier, horaires, avis et photos. On l'envoie au commerçant ou on la montre en rendez-vous :
« Voici à quoi pourrait ressembler votre site ».

Complète la gamme : BridgeToLeads trouve les entreprises sans site, Chasseur de sites repère les sites en panne,
Audit express prouve le problème, Démo Express fait signer.

## État : étape 3 sur 4

| Étape | Contenu | État |
|---|---|---|
| 1 | Recherche (nom + ville ou lien Google Maps), fiche Google, premier modèle, aperçu ordinateur et téléphone | fait |
| 2 | 6 mises en page (Élégant, Artisan, Douceur, Pro, Sérénité, Moderne), retouches en direct : modèle, accroche, présentation, bouton, couleur, services, photos (choix et ordre), sections | fait |
| 3 | Conformité Google (crédits « Google Maps », auteurs, liens, date de visite, sélection des avis expliquée) ; envoi au prospect : PNG ordinateur et téléphone, PDF, page web, ZIP **sans contenu Google** ; message e-mail et SMS (FR/EN) signé | fait |
| 4 | Installateurs Windows et Mac, licence Stripe (`DEX-…`), pages de vente FR et EN (99 €), vitrine, pack | à faire |

## Règles Google respectées

Source : « Policies and attributions for Places API » (developers.google.com, mise à jour du 9 novembre 2026).
Les conditions propres à l'Espace économique européen n'ont pas été lues : on applique la version la plus stricte.

- Uniquement l'API officielle Google Places (« New »), avec la clé du client : aucun scraping.
- **Pas d'export du contenu Google** : fiches et photos gardées en mémoire le temps de la session, jamais sur le
  disque ; les fichiers envoyés au prospect (images, PDF, page web) ne contiennent ni photo, ni avis, ni note, ni
  horaires, ni adresse Google — emplacements « Vos photos ici » et identité vérifiée par le vendeur.
- Aperçu en direct : mention « Google Maps » au format exigé (Roboto ou sans-serif, 400, #5E5E5E ou blanc,
  13 px, sur une ligne, `translate="no"`) près de la note, des photos, des avis et des horaires ; auteur de chaque
  photo et avis (avatar, nom, lien) ; lien vers chaque photo et avis sur Google Maps ; date relative ; **date de
  visite** pour les lieux en France ; phrase expliquant la sélection des avis ; avis traduits signalés ; avis non
  vérifiés par Google signalés.
- Bandeau « Maquette de démonstration — site non publié » et `noindex`.
- La clé Google est chiffrée sur l'ordinateur et n'apparaît jamais dans la maquette (les photos passent par
  l'application).

## Développeurs

```bash
pip install -e ".[dev]"
python -m demo_express          # interface sur http://127.0.0.1:8777
pytest -q                       # tests (faux Google Places, aucun appel réel)
```

Organisation : `places.py` (API Google), `capture.py` (images et PDF par le navigateur intégré),
`messages.py` (message de prospection), `familles.py` (métiers → couleurs et textes FR/EN), `maquette.py` (options, ordre des sections) et
`templates/maquette/` (base commune `_base.html`, sections `_sections.html`, une mise en page par famille), `web.py` et `templates/app/` (l'interface), `langues/en.yaml` (anglais).
