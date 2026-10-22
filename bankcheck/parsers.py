"""Read the bank's movements export and turn it into a normalized DataFrame."""
import logging
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from bankcheck import config

COLUMNS = [
    "Currency",
    "Date",
    "Card Type",
    "Description",
    "City",
    "Installments",
    "Installment Details",
    "Amount",
]

log = logging.getLogger(__name__)

# How many rows below a section title the header row may appear
HEADER_SEARCH_ROWS = 3


class ParseError(Exception):
    """The file can't be read or doesn't match a known export format."""


@dataclass(frozen=True)
class FormatProfile:
    name: str
    currency: str
    section_title: str
    header_labels: dict
    columns: dict
    verified: bool = True


@dataclass
class ParsedFile:
    movements: pd.DataFrame
    sections: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


PROFILES = [FormatProfile(**profile) for profile in config.FORMAT_PROFILES]


def parse_file(path: str) -> ParsedFile:
    """Read a bank export (.xls/.xlsx) and return its normalized movements."""
    engine = "xlrd" if path.lower().endswith(".xls") else None
    try:
        raw = pd.read_excel(path, header=None, engine=engine)
    except FileNotFoundError:
        raise ParseError(f"No existe el archivo: '{path}'")
    except ImportError:
        raise ParseError("Falta la librería 'xlrd'. Instálala con: pip install xlrd")
    except Exception as e:
        raise ParseError(f"No se pudo leer '{path}': {e}") from e
    return parse_raw(raw)


def parse_raw(raw: pd.DataFrame) -> ParsedFile:
    """Normalize a raw export already loaded with header=None."""
    sections = _find_sections(raw)
    if not sections:
        titles = ", ".join(f"'{p.section_title}'" for p in PROFILES)
        raise ParseError(f"No se encontró ninguna sección de movimientos conocida ({titles}).")

    result = ParsedFile(movements=pd.DataFrame(columns=COLUMNS))
    frames = []
    for i, (profile, header_row) in enumerate(sections):
        next_section_row = sections[i + 1][1] - 1 if i + 1 < len(sections) else len(raw)
        frame, warnings = _read_section(raw, profile, header_row, next_section_row)
        log.debug("Sección '%s': encabezado en la fila %d, %d movimientos", profile.name, header_row + 1, len(frame))
        if not profile.verified:
            warnings.append(
                f"El formato '{profile.name}' aún no se ha validado con un archivo real; revisa los montos."
            )
        frames.append(frame)
        result.sections.append(profile.name)
        result.warnings.extend(warnings)

    result.movements = pd.concat(frames, ignore_index=True) if frames else result.movements
    return result


def _normalize_text(value) -> str:
    if not isinstance(value, str):
        return ""
    without_accents = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return " ".join(without_accents.casefold().split())


def _row_texts(raw: pd.DataFrame, row: int) -> set:
    return {_normalize_text(v) for v in raw.iloc[row] if isinstance(v, str)}


def _header_matches(raw: pd.DataFrame, row: int, profile: FormatProfile) -> bool:
    for col, label in profile.header_labels.items():
        if col >= raw.shape[1] or _normalize_text(raw.iat[row, col]) != _normalize_text(label):
            return False
    return True


def _find_sections(raw: pd.DataFrame) -> list:
    """Return (profile, header_row) for every known section title in the file."""
    sections = []
    for row in range(len(raw)):
        texts = _row_texts(raw, row)
        for profile in PROFILES:
            if _normalize_text(profile.section_title) not in texts:
                continue
            last = min(row + HEADER_SEARCH_ROWS, len(raw) - 1)
            header_row = next(
                (r for r in range(row + 1, last + 1) if _header_matches(raw, r, profile)), None
            )
            if header_row is None:
                expected = ", ".join(
                    f"'{label}' (columna {col})" for col, label in profile.header_labels.items()
                )
                raise ParseError(
                    f"Se encontró la sección '{profile.section_title}' (fila {row + 1}), pero su "
                    f"encabezado no coincide con el formato esperado: {expected}. "
                    "¿Cambió el formato del banco?"
                )
            sections.append((profile, header_row))
    return sections


def _to_date(value):
    if isinstance(value, (datetime, pd.Timestamp)):
        return pd.Timestamp(value).normalize()
    if isinstance(value, str):
        try:
            return pd.Timestamp(datetime.strptime(value.strip(), "%d/%m/%Y"))
        except ValueError:
            return None
    return None


def _clean_text(series: pd.Series) -> pd.Series:
    return series.where(series.notna(), "").astype(str).str.strip()


def _read_section(raw: pd.DataFrame, profile: FormatProfile, header_row: int, end_row: int):
    """Read the data rows of one section: every row with a date right below the header."""
    max_col = max(profile.columns.values())
    if raw.shape[1] <= max_col:
        raise ParseError(
            f"La sección '{profile.name}' tiene {raw.shape[1]} columnas y se necesitan {max_col + 1}."
        )

    date_col = profile.columns["Date"]
    dates = [_to_date(raw.iat[r, date_col]) for r in range(header_row + 1, end_row)]
    count = next((i for i, d in enumerate(dates) if d is None), len(dates))

    warnings = []
    skipped = sum(d is not None for d in dates[count:])
    if skipped:
        warnings.append(
            f"'{profile.name}': se ignoraron {skipped} filas con fecha que aparecen después de "
            f"una fila sin fecha (fila {header_row + count + 2} del archivo)."
        )

    rows = raw.iloc[header_row + 1 : header_row + 1 + count]
    frame = pd.DataFrame({name: rows.iloc[:, col].values for name, col in profile.columns.items()})
    frame["Date"] = pd.to_datetime(pd.Series(dates[:count], dtype="object"))
    frame.insert(0, "Currency", profile.currency)

    for name in ("Card Type", "Description", "City", "Installments", "Installment Details"):
        frame[name] = _clean_text(frame[name])

    amounts = pd.to_numeric(frame["Amount"], errors="coerce")
    bad = amounts.isna()
    if bad.any():
        file_rows = ", ".join(str(header_row + 2 + i) for i in frame.index[bad][:5])
        raise ParseError(
            f"'{profile.name}': hay {bad.sum()} montos que no son números (filas {file_rows}). "
            "¿Cambió la columna de montos?"
        )
    if profile.currency == "CLP":
        frame["Amount"] = amounts.round().astype("int64")
    else:
        frame["Amount"] = amounts.round(2)

    return frame[COLUMNS], warnings


def read_clean_file(path: str) -> pd.DataFrame:
    """Read back a clean .xlsx saved by the CLI (data/cleaned-movements_*.xlsx)."""
    try:
        df = pd.read_excel(path)
    except FileNotFoundError:
        raise ParseError(f"No existe el archivo: '{path}'")
    except Exception as e:
        raise ParseError(f"No se pudo leer '{path}': {e}") from e
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ParseError(f"'{path}' no es un archivo limpio de bankcheck: faltan las columnas {', '.join(missing)}.")
    df = df[COLUMNS].copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    for name in ("Card Type", "Description", "City", "Installments", "Installment Details"):
        df[name] = _clean_text(df[name])
    return df
