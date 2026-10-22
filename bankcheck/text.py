"""Text helpers to compare bank descriptions."""
import unicodedata


def normalize(value) -> str:
    """Lowercase, without accents and with single spaces; "" for anything that isn't text."""
    if not isinstance(value, str):
        return ""
    without_accents = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return " ".join(without_accents.casefold().split())


def merchant_key(description) -> str:
    """
    The merchant part of a description, to group charges of the same merchant:
    words with digits (store numbers, transaction codes) are dropped, so
    "SPOTIFY P1A2B3" and "SPOTIFY X9Y8Z7" are the same merchant.
    """
    words = normalize(description).split()
    kept = [w for w in words if not any(c.isdigit() for c in w)]
    return " ".join(kept or words)


def suggest_pattern(description) -> str:
    """A rule fragment for a description: its first two merchant words, in uppercase."""
    return " ".join(merchant_key(description).split()[:2]).upper()
