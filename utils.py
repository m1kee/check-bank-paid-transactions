import pandas as pd

def format_clp(x) -> str:
    """
    Formats a number into CLP currency format (e.g., $1.234).
    """
    try:
        x = float(x)
        # .0f = no decimals, , = thousands separator
        return f"${x:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "$0"

def safe_to_datetime(series: pd.Series) -> pd.Series:
    """
    Attempts to convert a series to datetime. 
    If it's already datetime, it formats it.
    If it's text, it converts it.
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        # If already datetime, just format
        return series.dt.strftime('%d/%m/%Y')
    
    # Attempt to convert from text, handling errors
    # 'dayfirst=True' assumes DD/MM/YYYY format
    # 'coerce' turns errors into NaT (Not a Time)
    converted = pd.to_datetime(series, dayfirst=True, errors='coerce')
    
    # Format the converted dates
    return converted.dt.strftime('%d/%m/%Y')

def safe_to_int(series: pd.Series) -> pd.Series:
    """
    Converts a series to numeric and then to integer,
    filling errors/NaN with 0.
    """
    return pd.to_numeric(series, errors='coerce').fillna(0).astype(int)