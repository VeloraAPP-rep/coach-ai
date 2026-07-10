import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

SUMMARIES_DIR = Path("summaries")
SUMMARIES_DIR.mkdir(exist_ok=True)

REFUSAL_MARKERS = (
    "я не могу обсуждать",
    "я не могу помочь",
    "не могу выполнить",
)


def _split_markdown(text: str, max_chars: int = 6000) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0

    for paragraph in text.split("\n\n"):
        paragraph_size = len(paragraph) + 2
        if current and current_size + paragraph_size > max_chars:
            chunks.append("\n\n".join(current))
            current = []
            current_size = 0
        current.append(paragraph)
        current_size += paragraph_size

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _content_or_error(response, task: str) -> str:
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError(f"YandexGPT вернул пустой результат: {task}")
    if any(marker in content.lower() for marker in REFUSAL_MARKERS):
        raise RuntimeError(f"YandexGPT ошибочно отклонил безопасный текст: {task}")
    return content


def _client_and_model() -> tuple[OpenAI, str]:
    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    if not api_key or not folder_id:
        raise RuntimeError("YANDEX_API_KEY или YANDEX_FOLDER_ID не настроены")

    client = OpenAI(
        api_key=api_key,
        base_url="https://ai.api.cloud.yandex.net/v1",
    )
    model = f"gpt://{folder_id}/yandexgpt/latest"
    return client, model


def make_summary_markdown(transcript_md_path: str) -> str:
    transcript_path = Path(transcript_md_path)
    transcript_text = transcript_path.read_text(encoding="utf-8-sig")
    client, model = _client_and_model()

    notes = []
    for index, chunk in enumerate(_split_markdown(transcript_text), start=1):
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты редактор спортивных обучающих материалов. Составь краткие "
                        "фактические заметки по фрагменту расшифровки. Сохрани числа, "
                        "результаты исследований и практические рекомендации. Не ставь "
                        "медицинских диагнозов и не добавляй сведения от себя."
                    ),
                },
                {"role": "user", "content": chunk},
            ],
        )
        notes.append(_content_or_error(response, f"часть {index}"))

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Объедини заметки в точный конспект спортивного видео. "
                    "Не придумывай факты. Верни только Markdown со структурой: "
                    "# Краткое содержание; ## О чём видео; ## Основные идеи; "
                    "## Практические выводы; ## Что важно запомнить; "
                    "## Возможные упражнения / действия."
                ),
            },
            {"role": "user", "content": "\n\n---\n\n".join(notes)},
        ],
    )
    summary_text = _content_or_error(response, "итоговый конспект")

    summary_file = SUMMARIES_DIR / f"{transcript_path.stem}_summary.md"
    summary_file.write_text(summary_text, encoding="utf-8-sig")
    return str(summary_file)
