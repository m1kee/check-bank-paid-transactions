CURRENCY_NAMES = {
    "CLP": "Pesos (CLP)",
    "USD": "Dólares (USD)",
}


def format_amount(value, currency: str = "CLP") -> str:
    """
    Format an amount the Chilean way: $1.234 for pesos, US$1.234,56 for dollars.
    """
    try:
        value = float(value)
    except (ValueError, TypeError):
        value = 0.0

    if currency == "USD":
        # Swap separators: 1,234.56 -> 1.234,56
        return "US$" + f"{value:,.2f}".translate(str.maketrans(",.", ".,"))
    return f"${value:,.0f}".replace(",", ".")
