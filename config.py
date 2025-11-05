# --- File Paths ---
# New folder to store raw files after they are processed
PROCESSED_ARCHIVE_FOLDER = "processed-archive"


# --- Pre-processing Configuration ---

# Columns to extract from the raw XLS file (0-based index)
# Date(B=1), Card(C=2), Description(E=4), City(G=6), 
# Installment1(H=7), Installment2(I=8), Amount(K=10)
RAW_COLUMN_INDICES = [1, 2, 4, 6, 7, 8, 10]

# Final column names for the clean XLSX file
CLEAN_COLUMN_NAMES = [
    "Date",
    "Card Type",
    "Description",
    "City",
    "Installments",  # "Installments" is repeated
    "Installments",
    "Amount ($)"
]

# Number of header/metadata rows to skip in the raw file
ROWS_TO_SKIP = 18

# --- Analysis Configuration ---

# Terms that identify a payment in the "Description" column
PAYMENT_TERMS = ["Pago Pesos TAR", "Pago Pesos TEF PAGO NORMAL"]

# Condition to identify a purchase (e.g., "01/01" in installments)
PURCHASE_INSTALLMENT_CONDITION = "01/01"