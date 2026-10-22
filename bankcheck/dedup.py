"""Merge several downloads of the movements view without counting a movement twice."""
import hashlib

import pandas as pd

KEY_COLUMNS = [
    "Currency",
    "Date",
    "Card Type",
    "Description",
    "City",
    "Installments",
    "Installment Details",
    "Amount",
]


def add_fingerprints(movements: pd.DataFrame) -> pd.DataFrame:
    """
    Add a "Fingerprint" column that identifies each movement across downloads.

    Identical movements inside the same download (two equal coffees on the same
    day) get different fingerprints through their occurrence number, so they are
    kept apart, while the same movement in two downloads gets the same one.
    """
    df = movements.copy()
    keys = df[KEY_COLUMNS].astype(str).agg("|".join, axis=1)
    occurrence = keys.groupby(keys).cumcount()
    df["Fingerprint"] = [
        hashlib.sha1(f"{key}|{n}".encode("utf-8")).hexdigest() for key, n in zip(keys, occurrence)
    ]
    return df


def merge_downloads(frames: list) -> pd.DataFrame:
    """Union of several downloads, keeping each movement once, sorted by date."""
    if not frames:
        return pd.DataFrame(columns=KEY_COLUMNS)
    combined = pd.concat([add_fingerprints(f) for f in frames], ignore_index=True)
    merged = combined.drop_duplicates("Fingerprint").drop(columns="Fingerprint")
    return merged.sort_values("Date", kind="stable").reset_index(drop=True)
