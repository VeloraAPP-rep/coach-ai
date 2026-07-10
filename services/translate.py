import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv


load_dotenv()

TRANSLATIONS_DIR = Path("translations")
TRANSLATIONS_DIR.mkdir(exist_ok=True)

LANGUAGE_CODES = {
    "Русский": "ru",
    "English": "en",
    "Español": "es",
    "Deutsch": "de",
    "Français": "fr",
    "Italiano": "it",
}

TIMESTAMP_RE = re.compile(r"^(\*\*[^*]+\*\*\s*[—-]\s*)(.*)$")
HEADING_RE = re.compile(r"^(#{1,6}\s+)(.*)$")
SOURCE_RE = re.compile(r"^([^:]+:\s*)(https?://\S+)$")


def _translate_batch(texts: list[str], language_code: str) -> list[str]:
    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    if not api_key or not folder_id:
        raise RuntimeError("YANDEX_API_KEY или YANDEX_FOLDER_ID не настроены")

    response = httpx.post(
        "https://translate.api.cloud.yandex.net/translate/v2/translate",
        headers={"Authorization": f"Api-Key {api_key}"},
        json={
            "folderId": folder_id,
            "targetLanguageCode": language_code,
            "texts": texts,
        },
        timeout=120,
    )
    response.raise_for_status()
    translations = response.json().get("translations", [])
    if len(translations) != len(texts):
        raise RuntimeError("Yandex Translate вернул неполный результат")
    return [item["text"] for item in translations]


def _parts(line: str) -> tuple[str, str, str]:
    if not line.strip():
        return line, "", ""

    match = TIMESTAMP_RE.match(line)
    if match:
        return match.group(1), match.group(2), ""

    match = HEADING_RE.match(line)
    if match:
        return match.group(1), match.group(2), ""

    match = SOURCE_RE.match(line)
    if match:
        return "", match.group(1).strip(), f" {match.group(2)}"

    return "", line, ""


def translate_markdown(markdown_path: str, target_language: str) -> str:
    language_code = LANGUAGE_CODES.get(target_language)
    if not language_code:
        raise ValueError("Выбран неподдерживаемый язык")

    source_path = Path(markdown_path)
    lines = source_path.read_text(encoding="utf-8-sig").splitlines()
    parsed = [_parts(line) for line in lines]
    indexes = [index for index, (_, text, _) in enumerate(parsed) if text]

    translated_by_index: dict[int, str] = {}
    batch_indexes: list[int] = []
    batch_texts: list[str] = []
    batch_chars = 0

    def flush() -> None:
        nonlocal batch_indexes, batch_texts, batch_chars
        if not batch_texts:
            return
        translated = _translate_batch(batch_texts, language_code)
        translated_by_index.update(zip(batch_indexes, translated))
        batch_indexes, batch_texts, batch_chars = [], [], 0

    for index in indexes:
        text = parsed[index][1]
        if batch_texts and (len(batch_texts) >= 50 or batch_chars + len(text) > 9000):
            flush()
        batch_indexes.append(index)
        batch_texts.append(text)
        batch_chars += len(text)
    flush()

    output_lines = []
    for index, (prefix, text, suffix) in enumerate(parsed):
        output_lines.append(prefix + translated_by_index.get(index, text) + suffix)

    output_path = TRANSLATIONS_DIR / f"{source_path.stem}_{target_language}.md"
    output_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8-sig")
    return str(output_path)
