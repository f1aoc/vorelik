"""Familles de métiers : couleurs, accroche, texte de présentation et services types de la maquette.

Le métier vient des « types » Google de la fiche (primaryType d'abord). Les textes sont écrits par métier
(aucune intelligence artificielle) et utilisent {nom}, {ville} et {metier}.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Famille:
    code: str
    nom: dict[str, str]
    couleur: str  # couleur principale
    fonce: str  # titres et fond du pied de page
    clair: str  # fonds de sections
    police_titres: str  # Google Fonts
    accroche: dict[str, str]
    presentation: dict[str, str]
    services: dict[str, list[tuple[str, str]]]  # (titre, description)
    action: dict[str, str]  # bouton principal


FAMILLES: dict[str, Famille] = {
    "restaurant": Famille(
        code="restaurant",
        nom={"fr": "Restaurants et cafés", "en": "Restaurants and cafés"},
        couleur="#B4532A", fonce="#2B1A12", clair="#FBF4EE", police_titres="Playfair Display",
        accroche={"fr": "Une cuisine qui donne envie de revenir", "en": "Food that keeps you coming back"},
        presentation={
            "fr": "{nom} vous accueille à {ville} dans un cadre chaleureux. Produits frais, plats faits maison et "
                  "service attentionné : réservez votre table ou passez nous voir.",
            "en": "{nom} welcomes you in {ville} in a warm setting. Fresh produce, homemade dishes and friendly "
                  "service: book a table or drop by.",
        },
        services={
            "fr": [("Sur place", "Une salle conviviale pour vos repas entre amis, en famille ou entre collègues."),
                   ("À emporter", "Commandez par téléphone, votre repas est prêt quand vous arrivez."),
                   ("Groupes et événements", "Anniversaires, repas d'affaires : demandez notre menu de groupe.")],
            "en": [("Dine in", "A friendly dining room for meals with friends, family or colleagues."),
                   ("Takeaway", "Order by phone, your meal is ready when you arrive."),
                   ("Groups and events", "Birthdays, business lunches: ask for our group menu.")],
        },
        action={"fr": "Réserver une table", "en": "Book a table"},
    ),
    "bouche": Famille(
        code="bouche",
        nom={"fr": "Commerces de bouche", "en": "Food shops"},
        couleur="#C2410C", fonce="#3A2414", clair="#FFF7ED", police_titres="Fraunces",
        accroche={"fr": "Le goût du fait maison, chaque jour", "en": "The taste of homemade, every day"},
        presentation={
            "fr": "Chez {nom}, à {ville}, tout est préparé avec soin à partir de produits sélectionnés. "
                  "Venez découvrir nos spécialités et nos produits de saison.",
            "en": "At {nom} in {ville}, everything is carefully made from selected ingredients. "
                  "Come and discover our specialities and seasonal products.",
        },
        services={
            "fr": [("Nos spécialités", "Les incontournables de la maison, préparés chaque jour."),
                   ("Commandes", "Pour vos fêtes et réceptions, commandez à l'avance par téléphone."),
                   ("Produits de saison", "Une sélection qui change au fil des saisons.")],
            "en": [("Our specialities", "House favourites, made fresh every day."),
                   ("Orders", "For parties and events, order ahead by phone."),
                   ("Seasonal products", "A selection that changes with the seasons.")],
        },
        action={"fr": "Passer commande", "en": "Place an order"},
    ),
    "beaute": Famille(
        code="beaute",
        nom={"fr": "Coiffure et beauté", "en": "Hair and beauty"},
        couleur="#B0476F", fonce="#2A1520", clair="#FCF2F6", police_titres="Cormorant Garamond",
        accroche={"fr": "Prenez du temps pour vous", "en": "Take time for yourself"},
        presentation={
            "fr": "{nom}, votre salon à {ville}. Une équipe à l'écoute, des conseils personnalisés et des soins "
                  "de qualité pour vous sentir bien.",
            "en": "{nom}, your salon in {ville}. A team that listens, personal advice and quality treatments "
                  "to help you feel your best.",
        },
        services={
            "fr": [("Coupes et coiffures", "Femme, homme, enfant : une coupe qui vous ressemble."),
                   ("Couleur et soins", "Colorations, mèches et soins adaptés à votre type de cheveux."),
                   ("Conseils", "Des recommandations personnalisées pour entretenir votre style à la maison.")],
            "en": [("Cuts and styling", "Women, men, children: a cut that suits you."),
                   ("Colour and care", "Colouring, highlights and treatments suited to your hair."),
                   ("Advice", "Personal tips to keep your style at home.")],
        },
        action={"fr": "Prendre rendez-vous", "en": "Book an appointment"},
    ),
    "batiment": Famille(
        code="batiment",
        nom={"fr": "Artisans du bâtiment", "en": "Trades and building"},
        couleur="#1D4ED8", fonce="#0F1E3D", clair="#EFF4FF", police_titres="Montserrat",
        accroche={"fr": "Des travaux bien faits, dans les délais", "en": "Work done right, on time"},
        presentation={
            "fr": "{nom} intervient à {ville} et dans les environs. Devis gratuit, travail soigné et respect des "
                  "délais : un artisan de confiance pour votre projet.",
            "en": "{nom} works in {ville} and the surrounding area. Free quotes, careful work and deadlines met: "
                  "a trusted tradesperson for your project.",
        },
        services={
            "fr": [("Dépannage", "Intervention rapide pour les urgences."),
                   ("Installation et rénovation", "Des travaux réalisés dans les règles de l'art."),
                   ("Devis gratuit", "Un devis clair et détaillé, sans engagement.")],
            "en": [("Repairs", "Fast response for emergencies."),
                   ("Installation and renovation", "Work carried out to the highest standards."),
                   ("Free quote", "A clear, detailed quote with no obligation.")],
        },
        action={"fr": "Demander un devis", "en": "Request a quote"},
    ),
    "sante": Famille(
        code="sante",
        nom={"fr": "Santé et bien-être", "en": "Health and wellbeing"},
        couleur="#0F766E", fonce="#0B2A28", clair="#EFFAF8", police_titres="Nunito",
        accroche={"fr": "Votre bien-être, notre priorité", "en": "Your wellbeing comes first"},
        presentation={
            "fr": "{nom} vous reçoit à {ville}. Une prise en charge attentive et personnalisée, dans un cadre "
                  "calme et accueillant.",
            "en": "{nom} welcomes you in {ville}. Attentive, personal care in a calm and welcoming setting.",
        },
        services={
            "fr": [("Consultations", "Sur rendez-vous, avec une écoute attentive de vos besoins."),
                   ("Suivi personnalisé", "Un accompagnement adapté à chaque personne."),
                   ("Informations pratiques", "Horaires, accès et modalités de rendez-vous.")],
            "en": [("Appointments", "By appointment, with careful attention to your needs."),
                   ("Personal follow-up", "Support tailored to each person."),
                   ("Practical information", "Opening hours, access and booking.")],
        },
        action={"fr": "Prendre rendez-vous", "en": "Book an appointment"},
    ),
    "services": Famille(
        code="services",
        nom={"fr": "Commerces et services", "en": "Shops and services"},
        couleur="#4F46E5", fonce="#1A1846", clair="#F3F3FF", police_titres="Poppins",
        accroche={"fr": "Un service de proximité, à votre écoute", "en": "Local service, here for you"},
        presentation={
            "fr": "{nom} est à votre service à {ville}. Une équipe disponible, des conseils clairs et un accueil "
                  "attentif, pour vous simplifier la vie.",
            "en": "{nom} is at your service in {ville}. An available team, clear advice and a warm welcome "
                  "to make life easier.",
        },
        services={
            "fr": [("Conseil", "Nous prenons le temps de comprendre votre besoin."),
                   ("Service sur mesure", "Une solution adaptée à votre situation."),
                   ("Proximité", "Un interlocuteur près de chez vous, joignable facilement.")],
            "en": [("Advice", "We take the time to understand what you need."),
                   ("Tailored service", "A solution that fits your situation."),
                   ("Close to you", "A local contact who is easy to reach.")],
        },
        action={"fr": "Nous contacter", "en": "Contact us"},
    ),
}

# Types Google (Places API « New ») → famille. Le premier type reconnu de la fiche l'emporte.
TYPES: dict[str, str] = {}
for _famille, _types in {
    "restaurant": "restaurant cafe coffee_shop bar pub wine_bar meal_takeaway meal_delivery fast_food_restaurant "
                  "pizza_restaurant brunch_restaurant breakfast_restaurant bistro cafeteria ice_cream_shop "
                  "tea_house juice_shop food_court diner",
    "bouche": "bakery butcher_shop confectionery deli candy_store chocolate_shop dessert_shop donut_shop "
              "food_store grocery_store liquor_store market supermarket asian_grocery_store cheese_shop "
              "pastry_shop",
    "beaute": "hair_salon hair_care beauty_salon barber_shop nail_salon beautician makeup_artist skin_care_clinic "
              "tanning_studio spa",
    "batiment": "plumber electrician roofing_contractor painter general_contractor locksmith moving_company "
                "carpenter hvac_contractor home_improvement_store hardware_store landscaper",
    "sante": "dentist dental_clinic doctor physiotherapist chiropractor pharmacy drugstore veterinary_care "
             "medical_lab hospital massage wellness_center yoga_studio gym fitness_center sauna",
}.items():
    for _type in _types.split():
        TYPES[_type] = _famille
# Mots du libellé de métier (« Boulangerie-pâtisserie », « Plombier chauffagiste »…) quand le type est générique
MOTS = {
    "restaurant": ("restaurant", "brasserie", "pizzeria", "café", "bistrot", "crêperie", "traiteur", "food"),
    "bouche": ("boulang", "pâtiss", "boucher", "charcut", "fromag", "chocolat", "primeur", "épicer", "caviste",
               "bakery", "butcher", "cheese", "grocer"),
    "beaute": ("coiff", "barbier", "esthéti", "beauté", "ongle", "onglerie", "institut", "hair", "barber",
               "beauty", "nail"),
    "batiment": ("plomb", "électric", "couvreur", "peintre", "menuis", "maçon", "chauffag", "serrur", "carrel",
                 "plaquist", "paysag", "plumb", "roof", "builder", "carpent"),
    "sante": ("dentist", "médec", "kiné", "ostéo", "infirm", "pharmac", "vétérin", "massage", "yoga", "sophro",
              "doctor", "physio", "osteo", "therap"),
}


def famille_de(type_principal: str, types: list[str] | None = None, metier: str = "") -> Famille:
    for t in [type_principal, *(types or [])]:
        if t in TYPES:
            return FAMILLES[TYPES[t]]
    libelle = metier.lower()
    for code, mots in MOTS.items():
        if any(m in libelle for m in mots):
            return FAMILLES[code]
    return FAMILLES["services"]
