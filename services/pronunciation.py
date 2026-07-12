import re
import sqlite3
from pathlib import Path


DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATA_DIR / "terminology.db"

DEFAULT_PRONUNCIATIONS = {
    "каденс": "кад+енс",
    "пронация": "прон+ация",
    "биомеханика": "биомех+аника",
    "камбаловидная": "камбалов+идная",
    "голеностоп": "голеност+оп",
}


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS pronunciations (
            term TEXT PRIMARY KEY COLLATE NOCASE,
            marked_text TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.executemany(
        "INSERT OR IGNORE INTO pronunciations(term, marked_text) VALUES (?, ?)",
        DEFAULT_PRONUNCIATIONS.items(),
    )
    connection.commit()
    return connection


def set_pronunciation(term: str, marked_text: str) -> None:
    term = term.strip().lower()
    marked_text = marked_text.strip().lower()
    if not term or not marked_text:
        raise ValueError("Термин и вариант произношения не должны быть пустыми")
    if "+" not in marked_text:
        raise ValueError("Поставьте + перед ударной гласной, например: кад+енс")
    if len(term) > 100 or len(marked_text) > 120:
        raise ValueError("Слишком длинный термин")

    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO pronunciations(term, marked_text, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(term) DO UPDATE SET
                marked_text = excluded.marked_text,
                updated_at = CURRENT_TIMESTAMP
            """,
            (term, marked_text),
        )


def list_pronunciations(limit: int = 30) -> list[tuple[str, str]]:
    with _connect() as connection:
        return connection.execute(
            "SELECT term, marked_text FROM pronunciations ORDER BY term LIMIT ?",
            (limit,),
        ).fetchall()


def apply_pronunciations(text: str) -> str:
    result = text
    entries = sorted(list_pronunciations(500), key=lambda item: len(item[0]), reverse=True)
    for term, marked_text in entries:
        result = re.sub(
            rf"(?<!\w){re.escape(term)}(?!\w)",
            marked_text,
            result,
            flags=re.IGNORECASE,
        )
    return result
