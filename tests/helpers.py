"""Builders for synthetic test data shaped like the bank's export (no real data)."""
import pandas as pd

from bankcheck.parsers import COLUMNS

WIDTH = 11
HEADER = {1: "Fecha", 2: "Tipo de Tarjeta", 4: "Descripción", 6: "Ciudad", 7: "Cuotas", 8: "Monto ($)"}


def _blank():
    return [None] * WIDTH


def raw_section(rows, title="Movimientos Nacionales", header=None):
    """
    Rows for one section of the raw export: title, header and data.
    Each data row is (date "DD/MM/YYYY", description, amount[, installments[, city]]).
    """
    title_row = _blank()
    title_row[1] = title
    header_row = _blank()
    for col, label in (header or HEADER).items():
        header_row[col] = label

    out = [title_row, header_row]
    for date, description, amount, *rest in rows:
        row = _blank()
        row[1] = date
        row[2] = "Titular********0000"
        row[4] = description
        row[6] = rest[1] if len(rest) > 1 else None
        row[7] = rest[0] if rest else "01/01"
        row[8] = "1 / 0"
        row[10] = amount
        out.append(row)
    return out


def raw_export(*sections, leading_rows=16):
    """A raw export (as read with header=None): metadata rows followed by the sections."""
    rows = [_blank() for _ in range(leading_rows)]
    for i, section in enumerate(sections):
        if i:
            rows.append(_blank())
        rows.extend(section)
    return pd.DataFrame(rows)


def movements(rows, currency="CLP"):
    """
    A normalized movements DataFrame.
    Each row is (date "YYYY-MM-DD", description, amount[, installments]).
    """
    records = []
    for date, description, amount, *rest in rows:
        records.append(
            {
                "Currency": currency,
                "Date": pd.Timestamp(date),
                "Card Type": "Titular********0000",
                "Description": description,
                "City": "",
                "Installments": rest[0] if rest else "01/01",
                "Installment Details": "1 / 0",
                "Amount": amount,
            }
        )
    return pd.DataFrame(records, columns=COLUMNS)
