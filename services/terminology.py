import sqlite3
from pathlib import Path


DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATA_DIR / "terminology.db"

DEFAULT_TERMS = {
    "overstride": (
        "переразмах шага",
        "приземление стопы слишком далеко впереди относительно центра массы",
        "бег",
    ),
    "overstriding": (
        "переразмах шага",
        "приземление стопы слишком далеко впереди относительно центра массы",
        "бег",
    ),
    "cadence": (
        "каденс",
        "частота шагов, обычно измеряемая количеством шагов в минуту",
        "бег",
    ),
    "ground contact time": (
        "время контакта с опорой",
        "продолжительность контакта стопы с поверхностью при каждом шаге",
        "биомеханика",
    ),
    "hip drop": (
        "опускание таза",
        "снижение противоположной стороны таза во время опорной фазы шага",
        "биомеханика",
    ),
    "pronation": (
        "пронация",
        "естественное движение стопы с перекатом внутрь во время опоры",
        "биомеханика",
    ),
    "propulsion": (
        "отталкивание",
        "фаза шага, в которой тело получает направленный вперёд импульс",
        "бег",
    ),
    "running economy": (
        "экономичность бега",
        "энергетические затраты при заданной скорости бега",
        "физиология",
    ),
    "stride length": (
        "длина шага",
        "расстояние, преодолеваемое за один шаг",
        "бег",
    ),
    "rate of perceived exertion": (
        "субъективная оценка нагрузки",
        "самооценка интенсивности усилия по шкале RPE",
        "физиология",
    ),
    "range of motion": (
        "амплитуда движения",
        "диапазон движения в суставе или упражнении",
        "биомеханика",
    ),
    "progressive overload": (
        "прогрессивная перегрузка",
        "постепенное повышение тренировочной нагрузки",
        "силовая подготовка",
    ),
    "reps in reserve": (
        "повторения в запасе",
        "число дополнительных повторений, которые можно выполнить до отказа",
        "силовая подготовка",
    ),
    "drive the knee": (
        "активно выносить колено",
        "тренерское указание на активное движение колена вперёд",
        "бег",
    ),
    "push the ground away": (
        "активно отталкиваться от опоры",
        "тренерское указание на направленное усилие в опору",
        "бег",
    ),
    "stay tall": (
        "сохранять высокое положение корпуса",
        "указание не складываться и не сутулиться во время движения",
        "техника",
    ),
}


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS terms (
            user_id INTEGER NOT NULL,
            source_term TEXT NOT NULL COLLATE NOCASE,
            preferred_translation TEXT NOT NULL,
            explanation TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT 'общее',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, source_term)
        )
        """
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO terms(
            user_id, source_term, preferred_translation, explanation, category
        ) VALUES (0, ?, ?, ?, ?)
        """,
        ((source, *values) for source, values in DEFAULT_TERMS.items()),
    )
    connection.commit()
    return connection


def set_term(
    user_id: int,
    source_term: str,
    preferred_translation: str,
    explanation: str = "",
    category: str = "общее",
) -> None:
    source_term = source_term.strip().lower()
    preferred_translation = preferred_translation.strip()
    explanation = explanation.strip()
    category = category.strip() or "общее"
    if not source_term or not preferred_translation:
        raise ValueError("Оригинальный термин и перевод обязательны")
    if len(source_term) > 150 or len(preferred_translation) > 200:
        raise ValueError("Термин или перевод слишком длинный")
    if len(explanation) > 500 or len(category) > 80:
        raise ValueError("Пояснение или категория слишком длинные")

    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO terms(
                user_id, source_term, preferred_translation, explanation,
                category, updated_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, source_term) DO UPDATE SET
                preferred_translation = excluded.preferred_translation,
                explanation = excluded.explanation,
                category = excluded.category,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, source_term, preferred_translation, explanation, category),
        )


def list_terms(user_id: int, limit: int = 50) -> list[tuple[str, str, str, str]]:
    with _connect() as connection:
        return connection.execute(
            """
            SELECT source_term, preferred_translation, explanation, category
            FROM terms
            WHERE user_id IN (0, ?)
            ORDER BY user_id DESC, source_term
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()


def glossary_for_user(user_id: int) -> dict[str, tuple[str, str]]:
    glossary: dict[str, tuple[str, str]] = {}
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT user_id, source_term, preferred_translation, explanation
            FROM terms
            WHERE user_id IN (0, ?)
            ORDER BY user_id
            """,
            (user_id,),
        ).fetchall()
    for _, source, translation, explanation in rows:
        glossary[source] = (translation, explanation)
    return glossary
