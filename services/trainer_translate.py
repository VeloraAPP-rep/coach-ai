import re
import os
from pathlib import Path

from openai import OpenAI

from services.translate import translate_markdown
from services.terminology import glossary_for_user


TRAINER_TRANSLATIONS_DIR = Path("translations")

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
    glossary: dict[str, tuple[str, str]],
    client: OpenAI | None = None,
    model: str | None = None,
) -> str:
    result = translated
    line_terms = []
    for english, (russian, _) in glossary.items():
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


def make_trainer_translation(markdown_path: str, user_id: int = 0) -> str:
    source_path = Path(markdown_path)
    literal_path = Path(translate_markdown(markdown_path, "Русский"))

    original_lines = source_path.read_text(encoding="utf-8-sig").splitlines()
    translated_lines = literal_path.read_text(encoding="utf-8-sig").splitlines()
    if len(original_lines) != len(translated_lines):
        raise RuntimeError("Количество строк оригинала и перевода не совпадает")

    found_terms: set[str] = set()
    glossary = glossary_for_user(user_id)
    client, model = _trainer_client()
    annotated = [
        _annotate_line(original, translated, found_terms, glossary, client, model)
        for original, translated in zip(original_lines, translated_lines)
    ]

    if found_terms:
        annotated.extend(["", "## Словарь тренера", ""])
        for term in sorted(found_terms):
            russian, explanation = glossary[term]
            annotated.append(f"- **{russian} ({term})** — {explanation}.")

    output_path = TRAINER_TRANSLATIONS_DIR / f"{source_path.stem}_Тренерский.md"
    output_path.write_text("\n".join(annotated) + "\n", encoding="utf-8-sig")
    return str(output_path)
