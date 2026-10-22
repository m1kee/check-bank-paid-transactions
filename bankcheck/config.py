import os

# --- File Paths ---
# Folder for the clean .xlsx files, the history and the uploads. Relative to the
# current directory unless BANKCHECK_DATA_DIR says otherwise (e.g. /data in Docker).
DATA_DIR = os.environ.get("BANKCHECK_DATA_DIR", "data")

# Folder where the cleaned .xlsx files are saved
CLEAN_DATA_FOLDER = DATA_DIR

# Folder to store raw files after they are processed
PROCESSED_ARCHIVE_FOLDER = "processed-archive"

# Folder to store the generated HTML reports
REPORTS_FOLDER = "reports"

# SQLite history of every imported movement (used with --db and by the web app)
DB_PATH = os.path.join(DATA_DIR, "bank.db")

# Original files uploaded through the web app, kept to re-import if the logic changes
UPLOADS_FOLDER = os.path.join(DATA_DIR, "uploads")

# --- Bank Export Formats ---

# Each section of the bank export starts with a title row (e.g. "Movimientos
# Nacionales") followed by a header row. The header cells are merged in the
# original file, so "Monto ($)" sits on column 8 while the amounts live on
# column 10: data is read by column index (0-based), and the header labels are
# only used to find the section and check that the layout hasn't changed.
FORMAT_PROFILES = [
    {
        "name": "Movimientos Nacionales",
        "currency": "CLP",
        "section_title": "Movimientos Nacionales",
        "header_labels": {1: "Fecha", 2: "Tipo de Tarjeta", 4: "Descripción", 6: "Ciudad", 7: "Cuotas"},
        "columns": {
            "Date": 1,
            "Card Type": 2,
            "Description": 4,
            "City": 6,
            "Installments": 7,
            "Installment Details": 8,
            "Amount": 10,
        },
        "verified": True,
    },
    {
        # Assumed to share the national layout; not yet checked against a real file.
        "name": "Movimientos Internacionales",
        "currency": "USD",
        "section_title": "Movimientos Internacionales",
        "header_labels": {1: "Fecha", 2: "Tipo de Tarjeta", 4: "Descripción", 6: "Ciudad", 7: "Cuotas"},
        "columns": {
            "Date": 1,
            "Card Type": 2,
            "Description": 4,
            "City": 6,
            "Installments": 7,
            "Installment Details": 8,
            "Amount": 10,
        },
        "verified": False,
    },
]

# --- Analysis Configuration ---

# Terms that identify a payment in the "Description" column
PAYMENT_TERMS = [
    "PAGO PESOS TAR",
    "PAGO PESOS TEF",
    "PAGO ONLINE",
    "MERCADOPAGO",
]

# Descriptions that contain a payment term but are purchases
# (e.g. stores that charge through MercadoPago)
PAYMENT_EXCLUSIONS = [
    "COMERCIALSANA",
]

# Condition to identify a purchase (e.g., "01/01" in installments)
PURCHASE_INSTALLMENT_CONDITION = "01/01"

# A payment can only cover a purchase made at most this many days before it
MATCH_WINDOW_DAYS = 45

# Days a payment may be dated *before* the purchase it covers
# (0 = the payment must be on or after the purchase date)
PAYMENT_EARLY_TOLERANCE_DAYS = 0

# Folder the CLI reads when it gets no files (proposal 08)
INPUT_FOLDER = "pre-process-data"

# --- Grouped payments (proposal 11) ---

# A payment left without a purchase may cover up to this many unpaid purchases together
GROUP_MATCH_MAX_PURCHASES = 4

# Allowed difference between the payment and the sum of the purchases (rounding)
GROUP_MATCH_TOLERANCE = 0

# --- Categories (proposal 13) ---

# Starting categories and the description fragments that identify them. The web
# app copies them into the history the first time and from then on they are
# edited there. When several fragments match, the longest wins ("UBER EATS"
# beats "UBER"); comparisons ignore case and accents.
DEFAULT_CATEGORIES = {
    "Supermercado": ["LIDER", "JUMBO", "UNIMARC", "SANTA ISABEL", "TOTTUS", "ACUENTA", "EKONO", "OXXO"],
    "Transporte": ["UBER", "DIDI", "CABIFY", "METRO", "TURBUS", "PULLMAN", "PARKING", "AUTOPISTA"],
    "Combustible": ["COPEC", "SHELL", "PETROBRAS", "ARAMCO"],
    "Delivery": ["UBER EATS", "RAPPI", "PEDIDOSYA", "JUSTO"],
    "Restaurantes": ["STARBUCKS", "MCDONALDS", "BURGER KING", "JUAN MAESTRO", "DOMINO", "RESTAURANT", "CAFE"],
    "Suscripciones": ["NETFLIX", "SPOTIFY", "YOUTUBE", "APPLE.COM", "DISNEY", "HBO", "PRIME VIDEO", "OPENAI", "ICLOUD"],
    "Salud": ["FARMACIA", "CRUZ VERDE", "SALCOBRAND", "AHUMADA", "CLINICA", "DENTAL"],
    "Hogar": ["SODIMAC", "EASY", "IKEA", "HOMY", "CONSTRUMART"],
    "Servicios": ["ENEL", "AGUAS ANDINAS", "METROGAS", "ENTEL", "MOVISTAR", "CLARO", "WOM", "VTR"],
    "Compras": ["FALABELLA", "RIPLEY", "PARIS", "MERCADOLIBRE", "MERCADO LIBRE", "ALIEXPRESS", "AMAZON"],
}

# --- Subscriptions (proposal 15) ---

SUBSCRIPTION_MIN_MONTHS = 3       # distinct months with a charge
SUBSCRIPTION_INTERVAL_DAYS = (25, 35)  # days between consecutive charges
SUBSCRIPTION_AMOUNT_TOLERANCE = 0.15   # charges within ±15% of the usual amount

# --- Alerts (proposal 16) ---

ALERT_LOOKBACK_DAYS = 60          # only movements this recent raise alerts
DUPLICATE_MAX_DAYS = 2            # same description and amount within these days
UNUSUAL_AMOUNT_FACTOR = 3         # times the merchant's median amount
UNUSUAL_MIN_HISTORY = 3           # previous charges needed to know what's "usual"
NEW_MERCHANT_MIN_HISTORY_DAYS = 60  # history span needed before "new" means anything
