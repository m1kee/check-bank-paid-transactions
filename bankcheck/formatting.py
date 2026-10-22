CURRENCY_NAMES = {
    "CLP": "Pesos (CLP)",
    "USD": "Dólares (USD)",
}


def format_amount(value, currency: str = "CLP") -> str:
    """
    Format an amount the Chilean way: $1.234 for pesos, US$1.234,56 for dollars,
    with the sign before the symbol (-$4.500).
    """
    try:
        value = float(value)
    except (ValueError, TypeError):
        value = 0.0

    sign = "-" if value < 0 and round(abs(value), 2) else ""
    value = abs(value)
    if currency == "USD":
        # Swap separators: 1,234.56 -> 1.234,56
        return sign + "US$" + f"{value:,.2f}".translate(str.maketrans(",.", ".,"))
    return sign + f"${value:,.0f}".replace(",", ".")


def compact_amount(value, currency: str = "CLP") -> str:
    """Short amounts for chart axes: $45K, $1,2M, US$120."""
    try:
        value = float(value)
    except (ValueError, TypeError):
        value = 0.0
    symbol = "US$" if currency == "USD" else "$"
    sign = "-" if value < 0 else ""
    value = abs(value)
    for limit, suffix in ((1_000_000, "M"), (1_000, "K")):
        if value >= limit:
            short = value / limit
            text = f"{short:.1f}".rstrip("0").rstrip(".") if short < 10 else f"{short:.0f}"
            return f"{sign}{symbol}{text.replace('.', ',')}{suffix}"
    return f"{sign}{symbol}{value:.0f}"
