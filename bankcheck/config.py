# --- File Paths ---
# Folder where the cleaned .xlsx files are saved
CLEAN_DATA_FOLDER = "data"

# Folder to store raw files after they are processed
PROCESSED_ARCHIVE_FOLDER = "processed-archive"

# Folder to store the generated HTML reports
REPORTS_FOLDER = "reports"

# SQLite history of every imported movement (used with --db and by the web app)
DB_PATH = "data/bank.db"

# Original files uploaded through the web app, kept to re-import if the logic changes
UPLOADS_FOLDER = "data/uploads"

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
