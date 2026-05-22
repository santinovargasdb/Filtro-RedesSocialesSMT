import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

# API Keys
APIFY_API_KEY = os.getenv("APIFY_API_KEY", "")

# SMATA Branding Colors
SMATA_COLORS = {
    "GREEN_DARK": "#1B4D2E",
    "GREEN_MID": "#2E7D32",
    "GREEN_LIGHT": "#4CAF50",
    "GREEN_PALE": "#E8F5E9",
    "GOLD": "#FFC107"
}

# Core Terms for Scoring
SMATA_CORE_TERMS = {
    "inclusion": [
        "automotriz", "sindicato", "gremio", "trabajadores", "paritaria",
        "convenio colectivo", "industria automotriz", "cadena de suministro",
        "manufactura", "comercio exterior", "regulación laboral", "vehículos",
        "SMATA", "metalúrgico", "fábrica", "planta automotriz", "exportación",
        "aranceles", "empleo industrial"
    ],
    "exclusion": [
        "deportes", "fútbol", "entretenimiento", "farándula", "chimentos",
        "celebrities", "espectáculos", "moda", "gaming", "música"
    ]
}

# Network Scrapers Configuration (Apify Actor IDs)
APIFY_ACTORS = {
    "twitter": "apidojo/twitter-scraper-lite",
    "instagram": "apidojo/instagram-scraper",
    "tiktok": "apidojo/tiktok-scraper"
}
