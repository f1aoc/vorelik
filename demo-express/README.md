# Démo Express by VORELIK

Fabrique en deux minutes la **maquette de site** d'une entreprise locale, à partir de sa fiche Google :
nom, métier, horaires, avis et photos. On l'envoie au commerçant ou on la montre en rendez-vous :
« Voici à quoi pourrait ressembler votre site ».

Complète la gamme : BridgeToLeads trouve les entreprises sans site, Chasseur de sites repère les sites en panne,
Audit express prouve le problème, Démo Express fait signer.

## État : étape 1 sur 4

| Étape | Contenu | État |
|---|---|---|
| 1 | Recherche (nom + ville ou lien Google Maps), fiche Google, premier modèle, aperçu ordinateur et téléphone | fait |
| 2 | 6 modèles par famille de métier, retouches (accroche, textes, couleurs, photos, sections) | à faire |
| 3 | Exports (images, PDF, version web), message de prospection — après vérification des règles Google | à faire |
| 4 | Installateurs Windows et Mac, licence Stripe (`DEX-…`), pages de vente FR et EN (99 €), vitrine, pack | à faire |

## Règles Google respectées

- Uniquement l'API officielle Google Places (« New »), avec la clé du client : aucun scraping.
- Fiches et photos gardées **en mémoire** le temps de la session, jamais enregistrées sur le disque.
- Crédits affichés : auteur de chaque photo et de chaque avis, mention « Photos et avis : Google ».
- Bandeau « Maquette de démonstration — site non publié » et `noindex` : la maquette n'est pas un site publié.
- La clé Google est chiffrée sur l'ordinateur et n'apparaît jamais dans la maquette (les photos passent par
  l'application).

## Développeurs

```bash
pip install -e ".[dev]"
python -m demo_express          # interface sur http://127.0.0.1:8777
pytest -q                       # tests (faux Google Places, aucun appel réel)
```

Organisation : `places.py` (API Google), `familles.py` (métiers → couleurs et textes FR/EN), `maquette.py` et
`templates/maquette/` (la maquette), `web.py` et `templates/app/` (l'interface), `langues/en.yaml` (anglais).
