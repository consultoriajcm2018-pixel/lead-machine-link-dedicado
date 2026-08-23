"""Catalogo de modelos usado para classificar carroceria e faixa de marca.

E conhecimento de mercado sobre quais modelos sao SUV/crossover e quais
marcas sao premium. Nao contem preco, ano nem qualquer dado de lote.
"""

from __future__ import annotations

import re
import unicodedata

# Modelos SUV / crossover comercializados no Brasil.
SUV_MODELS: dict[str, tuple[str, ...]] = {
    "premium": (
        "x1", "x2", "x3", "x4", "x5", "x6", "x7", "ix3",
        "gla", "glb", "glc", "gle", "gls", "gla200", "gla250", "ml", "ml350",
        "classe gl", "gl 320", "gl320",
        "q2", "q3", "q5", "q7", "q8", "e-tron", "etron",
        "xc40", "xc60", "xc90",
        "range rover", "rangerover", "evoque", "velar", "discovery",
        "defender", "freelander", "sport hse",
        "cayenne", "macan",
        "f-pace", "fpace", "e-pace", "epace",
        "nx200", "nx300", "rx350", "rx450", "ux250", "lexus nx", "lexus rx",
        "countryman",
        "touareg",
        "land cruiser", "prado", "sw4", "hilux sw4",
        "grand cherokee", "commander", "wrangler",
        "pajero full", "pajero sport",
        "murano", "x-trail", "xtrail",
        "santa fe", "santafe", "grand santa fe",
        "sorento", "mohave",
        "trailblazer",
        "explorer", "edge",
        "cx-9", "cx9",
    ),
    "intermediario": (
        "compass", "renegade",
        "tiguan", "taos", "t-cross", "tcross", "nivus",
        "tucson", "ix35", "creta",
        "sportage", "soul",
        "cr-v", "crv", "hr-v", "hrv", "wr-v", "wrv",
        "corolla cross", "rav4", "rav-4",
        "outlander", "asx", "eclipse cross",
        "duster", "captur", "koleos",
        "ecosport", "kuga", "territory",
        "tracker", "captiva", "equinox",
        "kicks", "qashqai",
        "2008", "3008", "5008",
        "c4 cactus", "aircross", "c3 aircross", "c4 aircross",
        "pulse", "fastback", "freemont",
        "tiggo", "haval", "song", "yuan", "tan",
        "grand vitara", "vitara", "jimny", "s-cross", "scross",
        "actyon", "kyron", "rexton", "korando",
        "journey", "compass sport",
        "cx-5", "cx5", "cx-3",
        "t60", "t80", "t40", "t50",
        "trailhawk",
    ),
}

PREMIUM_BRANDS = (
    "bmw", "mercedes", "mercedes-benz", "audi", "volvo", "land rover",
    "landrover", "porsche", "jaguar", "lexus", "mini", "range rover",
    "maserati", "infiniti", "acura",
)

# Palavras que indicam que o lote NAO e um SUV mesmo aparecendo em busca de carros.
NON_SUV_HINTS = (
    "caminhao", "carreta", "reboque", "semirreboque", "onibus", "micro-onibus",
    "microonibus", "van", "furgao", "kombi", "motocicleta", "moto ", "scooter",
    "trator", "empilhadeira", "retroescavadeira", "aeronave", "lancha",
    "embarcacao", "jet ski", "quadriciclo", "sucata", "carcaca",
)

PICKUP_HINTS = (
    "caminhonete", "picape", "pick-up", "pickup", "strada", "saveiro",
    "montana", "toro", "ranger", "s10", "s-10", "amarok", "frontier",
    "l200", "hilux", "oroch", "rampage", "maverick", "hoggar",
    "courier", "hr hdlwbsc",
)

# Modelos cujo nome e ambiguo (numero ou palavra comum): so valem quando a
# marca correspondente aparece no mesmo titulo.
BRAND_REQUIRED: dict[str, tuple[str, ...]] = {
    "santa fe": ("hyundai",),
    "2008": ("peugeot",),
    "3008": ("peugeot",),
    "5008": ("peugeot",),
    "song": ("byd",),
    "yuan": ("byd",),
    "tan": ("byd",),
    "t40": ("jac", "foton"),
    "t50": ("jac", "foton"),
    "t60": ("jac", "foton"),
    "t80": ("jac", "foton"),
    "soul": ("kia",),
    "ml": ("mercedes",),
    "gla": ("mercedes",),
    "glb": ("mercedes",),
    "glc": ("mercedes",),
    "gle": ("mercedes",),
    "gls": ("mercedes",),
    "edge": ("ford",),
    "commander": ("jeep",),
    "journey": ("dodge",),
    "vitara": ("suzuki",),
    "grand vitara": ("suzuki",),
    "captur": ("renault",),
    "koleos": ("renault",),
    "ml350": ("mercedes",),
    "x1": ("bmw",),
    "x2": ("bmw",),
    "x3": ("bmw",),
    "x4": ("bmw",),
    "x5": ("bmw",),
    "x6": ("bmw",),
    "x7": ("bmw",),
    "q2": ("audi",),
    "q3": ("audi",),
    "q5": ("audi",),
    "q7": ("audi",),
    "q8": ("audi",),
}


# Modelos que nao sao SUV. Servem para derrubar um falso positivo vindo de um
# nome ambiguo (ex.: "Ford Fiesta Edge" casando com o Ford Edge).
NON_SUV_MODELS = (
    "fiesta", "focus", " ka ", "ka+", "courier", "escort", "fusion",
    "gol", "voyage", "saveiro", "fox", "polo", "virtus", "jetta", "golf",
    "up!", "bora", "santana", "parati", "passat",
    "celta", "onix", "prisma", "corsa", "classic", "cruze", "cobalt", "vectra",
    "astra", "monza", "kadett",
    "palio", "uno", "siena", "argo", "mobi", "punto", "idea", "doblo", "linea",
    "hb20", "i30", "elantra", "azera", "sonata", "veloster",
    "civic", "city", "fit", "accord",
    "corolla", "etios", "yaris", "prius", "camry",
    "sentra", "march", "versa", "tiida", "livina",
    "logan", "sandero", "clio", "megane", "fluence", "symbol",
    "206", "207", "307", "308", "408", "partner",
    "xsara", "picasso", "berlingo",
    "ecosport",  # tratado adiante: e SUV, fica fora do bloqueio
)

# Excecoes ao bloqueio acima: sao SUV apesar de aparecerem na lista.
NON_SUV_EXCEPTIONS = ("ecosport",)


SUNROOF_PATTERNS = (
    "teto solar",
    "teto panoramico",
    "teto-solar",
    "sunroof",
    "teto eletrico",
)


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def norm(text: str) -> str:
    """Minusculas, sem acento, espacos colapsados."""
    return re.sub(r"\s+", " ", strip_accents(text or "").lower()).strip()


_YEAR_PAIR = re.compile(r"\b(?:19|20)\d{2}\s*/\s*(?:19|20)?\d{2}\b|\b\d{2}\s*/\s*\d{2}\b")
_LOCALITY = re.compile(r"\s*[-–]\s*[a-z\s.']+/[a-z]{2}\s*$")


def limpar_titulo(title: str) -> str:
    """Remove par de anos e cidade/UF do fim, que geram falso positivo."""
    t = norm(title)
    t = _YEAR_PAIR.sub(" ", t)
    for _ in range(2):
        t = _LOCALITY.sub("", t)
    return re.sub(r"\s+", " ", t).strip()


def _bloqueado_por_modelo_comum(text: str, matched: str) -> bool:
    """Nome ambiguo perde para um modelo nao-SUV citado no mesmo titulo."""
    if matched not in BRAND_REQUIRED:
        return False
    for modelo in NON_SUV_MODELS:
        if modelo in NON_SUV_EXCEPTIONS:
            continue
        alvo = modelo.strip()
        if re.search(rf"(?<![a-z0-9]){re.escape(alvo)}(?![a-z0-9])", text):
            return True
    return False


def _matches_model(text: str, model: str) -> bool:
    if not re.search(rf"(?<![a-z0-9]){re.escape(model)}(?![a-z0-9])", text):
        return False
    required = BRAND_REQUIRED.get(model)
    if required and not any(brand in text for brand in required):
        return False
    if _bloqueado_por_modelo_comum(text, model):
        return False
    return True


def classify_body(title: str) -> str:
    """Devolve 'suv', 'picape', 'outro' ou 'nao_carro'."""
    t = limpar_titulo(title)
    if any(h in t for h in NON_SUV_HINTS):
        # 'Hilux SW4' e SUV mesmo que a origem escreva 'caminhonete'.
        if not any(m in t for m in SUV_MODELS["premium"] + SUV_MODELS["intermediario"]):
            return "nao_carro"
    for tier in ("premium", "intermediario"):
        for model in SUV_MODELS[tier]:
            if _matches_model(t, model):
                return "suv"
    if any(h in t for h in PICKUP_HINTS):
        return "picape"
    return "outro"


def suv_tier(title: str) -> str | None:
    """'premium' | 'intermediario' | None. Marca premium promove o modelo."""
    t = limpar_titulo(title)
    if classify_body(title) != "suv":
        return None
    for model in SUV_MODELS["premium"]:
        if _matches_model(t, model):
            return "premium"
    if any(brand in t for brand in PREMIUM_BRANDS):
        return "premium"
    return "intermediario"


def has_sunroof(*texts: str) -> bool:
    """True somente quando o texto do lote diz literalmente que tem teto solar.

    Nunca deduzimos teto solar por versao ou modelo.
    """
    blob = norm(" ".join(t for t in texts if t))
    return any(p in blob for p in SUNROOF_PATTERNS)
