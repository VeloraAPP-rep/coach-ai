import re
import os
from pathlib import Path

from openai import OpenAI

from services.translate import translate_markdown


TRAINER_TRANSLATIONS_DIR = Path("translations")

RUNNING_GLOSSARY = {
    "overstride": (
        "переразмах шага",
        "приземление стопы слишком далеко впереди относительно центра массы",
    ),
    "overstriding": (
        "переразмах шага",
        "приземление стопы слишком далеко впереди относительно центра массы",
    ),
    "cadence": (
        "каденс",
        "частота шагов, обычно измеряемая количеством шагов в минуту",
    ),
    "ground contact time": (
        "время контакта с опорой",
        "продолжительность контакта стопы с поверхностью при каждом шаге",
    ),
    "hip drop": (
        "опускание таза",
        "снижение противоположной стороны таза во время опорной фазы шага",
    ),
    "pronation": (
        "пронация",
        "естественное движение стопы с перекатом внутрь во время опоры",
    ),
    "propulsion": (
        "отталкивание",
        "фаза шага, в которой тело получает направленный вперёд импульс",
    ),
    "running economy": (
        "экономичность бега",
        "энергетические затраты при заданной скорости бега",
    ),
    "stride length": (
        "длина шага",
        "расстояние, преодолеваемое за один шаг",
    ),
    "rate of perceived exertion": (
        "субъективная оценка нагрузки",
        "самооценка интенсивности усилия по шкале RPE",
    ),
    "range of motion": (
        "амплитуда движения",
        "диапазон движения в суставе или упражнении",
    ),
    "progressive overload": (
        "прогрессивная перегрузка",
        "постепенное повышение тренировочной нагрузки",
    ),
    "reps in reserve": (
        "повторения в запасе",
        "число дополнительных повторений, которые спортсмен мог бы выполнить до отказа",
    ),
}


def _trainer_client() -> tuple[OpenAI, str]:
    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    if not api_key or not folder_id:
        raise RuntimeError("YANDEX_API_KEY или YANDEX_FOLDER_ID не настроены")
    return (
        OpenAI(api_key=api_key, base_url="https://ai.api.cloud.yandex.net/v1"),
        f"gpt://{folder_id}/yandexgpt/latest",
    )


def _annotate_line(
    original: str,
    translated: str,
    found_terms: set[str],
    client: OpenAI | None = None,
    model: str | None = None,
) -> str:
    result = translated
    line_terms = []
    for english, (russian, _) in RUNNING_GLOSSARY.items():
        if not re.search(rf"\b{re.escape(english)}\b", original, re.IGNORECASE):
            continue

        found_terms.add(english)
        line_terms.append((english, russian))

    if not line_terms:
        return result

    if client and model:
        required = ", ".join(f"{english} = {russian} ({english})" for english, russian in line_terms)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты редактор перевода для тренеров. Переведи английскую строку "
                        "на естественный русский, строго используя заданные термины. "
                        "Сохрани числа и смысл. Верни только одну переведённую строку."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Термины: {required}\nОригинал: {original}",
                },
            ],
        )
        edited = response.choices[0].message.content
        if edited and "я не могу" not in edited.lower():
            result = edited.strip()

    for english, russian in line_terms:
        if re.search(rf"\({re.escape(english)}\)", result, re.IGNORECASE):
            continue

        match = re.search(re.escape(russian), result, re.IGNORECASE)
        if match:
            result = result[:match.end()] + f" ({english})" + result[match.end():]
        else:
            result += f" *({english})*"
    return result


def make_trainer_translation(markdown_path: str) -> str:
    source_path = Path(markdown_path)
    literal_path = Path(translate_markdown(markdown_path, "Русский"))

    original_lines = source_path.read_text(encoding="utf-8-sig").splitlines()
    translated_lines = literal_path.read_text(encoding="utf-8-sig").splitlines()
    if len(original_lines) != len(translated_lines):
        raise RuntimeError("Количество строк оригинала и перевода не совпадает")

    found_terms: set[str] = set()
    client, model = _trainer_client()
    annotated = [
        _annotate_line(original, translated, found_terms, client, model)
        for original, translated in zip(original_lines, translated_lines)
    ]

    if found_terms:
        annotated.extend(["", "## Словарь тренера", ""])
        for term in sorted(found_terms):
            russian, explanation = RUNNING_GLOSSARY[term]
            annotated.append(f"- **{russian} ({term})** — {explanation}.")

    output_path = TRAINER_TRANSLATIONS_DIR / f"{source_path.stem}_Тренерский.md"
    output_path.write_text("\n".join(annotated) + "\n", encoding="utf-8-sig")
    return str(output_path)
