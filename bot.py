import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile

from config import BOT_TOKEN
from keyboards import (
    reel_actions_keyboard,
    translation_languages_keyboard,
    video_actions_keyboard,
)
from services.youtube import download_video, download_audio
from services.whisper_service import transcribe_audio
from services.markdown import save_transcript_markdown
from services.openai_summary import make_summary_markdown
from services.translate import translate_markdown
from services.trainer_translate import make_trainer_translation
from services.instagram import download_reel, is_instagram_url
from services.subtitles import burn_subtitles, save_translated_srt
from services.dubbing import create_russian_dub
from services.progress import run_with_progress
from services.source import download_source_audio, download_source_video
from services.pronunciation import list_pronunciations, set_pronunciation
from services.terminology import list_terms, set_term

from aiogram.client.session.aiohttp import AiohttpSession

session = AiohttpSession(timeout=120)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

user_links = {}
user_markdowns = {}
user_reel_segments = {}
user_reel_titles = {}
awaiting_pronunciation = set()
awaiting_terminology = set()


def reel_error_message(error: Exception) -> str:
    text = str(error)
    if "empty media response" in text.lower() or "cookies" in text.lower():
        return (
            "Instagram не отдал видео серверу. Для скачивания нужна "
            "авторизованная сессия Instagram (cookies)."
        )
    return text[:1000]


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer("Привет. Пришли ссылку на своё YouTube-видео.")


@dp.message(F.text.startswith("http"))
async def receive_link(message: types.Message):
    url = message.text.strip()
    user_id = message.from_user.id
    user_links[user_id] = url
    user_markdowns.pop(user_id, None)
    user_reel_segments.pop(user_id, None)
    user_reel_titles.pop(user_id, None)

    keyboard = reel_actions_keyboard() if is_instagram_url(url) else video_actions_keyboard()
    await message.answer("Что сделать с видео?", reply_markup=keyboard)


def get_source_transcript(user_id: int, url: str, progress=None) -> tuple[list[dict], str]:
    if user_id in user_reel_segments:
        return user_reel_segments[user_id], user_reel_titles[user_id]

    audio_file, title = download_source_audio(url, progress)
    if progress:
        progress.update("📝 Расшифровка Reel: 0%")
    segments = transcribe_audio(audio_file, progress)
    user_reel_segments[user_id] = segments
    user_reel_titles[user_id] = title
    return segments, title


@dp.callback_query(F.data == "download_mp4")
async def handle_download_mp4(callback: types.CallbackQuery):
    await callback.answer()

    url = user_links.get(callback.from_user.id)
    if not url:
        await callback.message.answer("Сначала пришли ссылку.")
        return

    status = await callback.message.answer("📥 Подготовка скачивания MP4...")

    try:
        filename, title = await run_with_progress(
            status,
            "📥 Подготовка скачивания MP4",
            lambda progress: download_video(url, progress),
        )
        await status.edit_text("📤 Отправка MP4 в Telegram...")

        await callback.message.answer_video(
            video=FSInputFile(filename),
            caption=title,
            supports_streaming=True
        )
        await status.edit_text("✅ MP4 готов.")

    except Exception as error:
        await status.edit_text(f"❌ Ошибка при скачивании MP4:\n{error}")


@dp.callback_query(F.data == "download_mp3")
async def handle_download_mp3(callback: types.CallbackQuery):
    await callback.answer()

    url = user_links.get(callback.from_user.id)
    if not url:
        await callback.message.answer("Сначала пришли ссылку.")
        return

    status = await callback.message.answer("📥 Подготовка скачивания MP3...")

    try:
        filename, title = await run_with_progress(
            status,
            "📥 Подготовка скачивания MP3",
            lambda progress: download_audio(url, progress),
        )
        await status.edit_text("📤 Отправка MP3 в Telegram...")

        await callback.message.answer_audio(
            FSInputFile(filename),
            title=title
        )
        await status.edit_text("✅ MP3 готов.")

    except Exception as error:
        await status.edit_text(f"❌ Ошибка при скачивании MP3:\n{error}")


@dp.callback_query(F.data == "make_markdown")
async def handle_make_markdown(callback: types.CallbackQuery):
    await callback.answer()

    url = user_links.get(callback.from_user.id)
    if not url:
        await callback.message.answer("Сначала пришли ссылку.")
        return

    status = await callback.message.answer("📥 Скачиваю аудио...")

    try:
        def build_markdown(progress):
            audio_file, title = download_audio(url, progress)
            progress.update("📝 Расшифровка: 0%")
            transcript = transcribe_audio(audio_file, progress)
            progress.update("💾 Сохранение Markdown")
            return save_transcript_markdown(title, url, transcript)

        markdown_file = await run_with_progress(
            status, "📥 Скачиваю аудио", build_markdown
        )

        user_markdowns[callback.from_user.id] = markdown_file

        await callback.message.answer_document(
            FSInputFile(markdown_file),
            caption="✅ Markdown готов."
        )
        await status.edit_text("✅ Markdown готов.")

    except Exception as error:
        await status.edit_text(f"❌ Ошибка при создании Markdown:\n{error}")


@dp.callback_query(F.data == "make_summary")
async def handle_make_summary(callback: types.CallbackQuery):
    await callback.answer()

    markdown_file = user_markdowns.get(callback.from_user.id)
    if not markdown_file:
        await callback.message.answer("Сначала создайте Markdown.")
        return

    status = await callback.message.answer("🧠 Делаю краткое содержание...")

    try:
        summary_file = await run_with_progress(
            status,
            "🧠 YandexGPT создаёт Summary",
            lambda progress: make_summary_markdown(markdown_file),
        )

        await callback.message.answer_document(
            FSInputFile(summary_file),
            caption="🧠 Summary готов."
        )
        await status.edit_text("✅ Summary готов.")

    except Exception as error:
        await status.edit_text(f"❌ Ошибка при создании Summary:\n{error}")


@dp.callback_query(F.data == "translate_markdown")
async def handle_translate_markdown(callback: types.CallbackQuery):
    await callback.answer()

    if not user_markdowns.get(callback.from_user.id):
        await callback.message.answer("Сначала создайте Markdown.")
        return

    await callback.message.answer(
        "Выберите язык перевода:",
        reply_markup=translation_languages_keyboard(),
    )


@dp.callback_query(F.data.startswith("translate:"))
async def handle_translation_language(callback: types.CallbackQuery):
    await callback.answer()

    markdown_file = user_markdowns.get(callback.from_user.id)
    if not markdown_file:
        await callback.message.answer("Сначала создайте Markdown.")
        return

    target_language = callback.data.partition(":")[2]
    status = await callback.message.answer("🌍 Перевожу Markdown...")

    try:
        translated_file = await run_with_progress(
            status,
            "🌍 Yandex Translate обрабатывает Markdown",
            lambda progress: translate_markdown(markdown_file, target_language),
        )
        await callback.message.answer_document(
            FSInputFile(translated_file),
            caption="✅ Перевод готов.",
        )
        await status.edit_text("✅ Перевод готов.")
    except Exception as error:
        await status.edit_text(f"❌ Ошибка при переводе:\n{error}")


@dp.callback_query(F.data == "trainer_translation")
async def handle_trainer_translation(callback: types.CallbackQuery):
    await callback.answer()

    markdown_file = user_markdowns.get(callback.from_user.id)
    if not markdown_file:
        await callback.message.answer("Сначала создайте Markdown.")
        return

    status = await callback.message.answer(
        "Делаю тренерский перевод: сохраняю термины и добавляю словарь..."
    )

    try:
        translated_file = await run_with_progress(
            status,
            "🧠 Тренерский редактор обрабатывает термины",
            lambda progress: make_trainer_translation(
                markdown_file, callback.from_user.id
            ),
        )
        await callback.message.answer_document(
            FSInputFile(translated_file),
            caption="🧠 Тренерский перевод готов.",
        )
        await status.edit_text("✅ Тренерский перевод готов.")
    except Exception as error:
        await status.edit_text(f"❌ Ошибка тренерского перевода:\n{error}")


@dp.callback_query(F.data == "download_reel")
async def handle_download_reel(callback: types.CallbackQuery):
    await callback.answer()
    url = user_links.get(callback.from_user.id)
    if not url or not is_instagram_url(url):
        await callback.message.answer("Сначала пришлите ссылку на Instagram Reel.")
        return

    status = await callback.message.answer("📥 Подготовка скачивания Reel...")
    try:
        filename, title = await run_with_progress(
            status,
            "📥 Подготовка скачивания Reel",
            lambda progress: download_reel(url, progress),
        )
        await status.edit_text("📤 Отправка Reel в Telegram...")
        await callback.message.answer_video(
            FSInputFile(filename),
            caption=title,
            supports_streaming=True,
        )
        await status.edit_text("✅ Reel готов.")
    except Exception as error:
        await status.edit_text(
            f"❌ Ошибка при скачивании Reel:\n{reel_error_message(error)}"
        )


@dp.callback_query(F.data == "reel_markdown")
async def handle_reel_markdown(callback: types.CallbackQuery):
    await callback.answer()
    url = user_links.get(callback.from_user.id)
    if not url or not is_instagram_url(url):
        await callback.message.answer("Сначала пришлите ссылку на Instagram Reel.")
        return

    status = await callback.message.answer("📥 Подготовка Reel к расшифровке...")
    try:
        segments, title = await run_with_progress(
            status,
            "📥 Подготовка Reel к расшифровке",
            lambda progress: get_source_transcript(
                callback.from_user.id, url, progress
            ),
        )
        markdown_file = save_transcript_markdown(title, url, segments)
        user_markdowns[callback.from_user.id] = markdown_file
        await callback.message.answer_document(
            FSInputFile(markdown_file), caption="✅ Markdown для Reel готов."
        )
        await status.edit_text("✅ Markdown для Reel готов.")
    except Exception as error:
        await status.edit_text(
            f"❌ Ошибка расшифровки Reel:\n{reel_error_message(error)}"
        )


@dp.callback_query(F.data.in_({"reel_srt_ru", "source_srt_ru"}))
async def handle_source_srt(callback: types.CallbackQuery):
    await callback.answer()
    url = user_links.get(callback.from_user.id)
    if not url:
        await callback.message.answer("Сначала пришлите ссылку на видео.")
        return

    status = await callback.message.answer("🇷🇺 Создаю русские субтитры...")
    try:
        def build_srt(progress):
            segments, title = get_source_transcript(
                callback.from_user.id, url, progress
            )
            progress.update("🌍 Перевод субтитров")
            return save_translated_srt(title, segments)

        srt_file = await run_with_progress(status, "📥 Подготовка видео", build_srt)
        await callback.message.answer_document(
            FSInputFile(srt_file), caption="🇷🇺 Русские субтитры готовы."
        )
        await status.edit_text("✅ Русские субтитры готовы.")
    except Exception as error:
        await status.edit_text(
            f"Ошибка создания субтитров:\n{reel_error_message(error)}"
        )


@dp.callback_query(F.data.in_({"reel_video_ru", "source_video_ru"}))
async def handle_source_video_ru(callback: types.CallbackQuery):
    await callback.answer()
    url = user_links.get(callback.from_user.id)
    if not url:
        await callback.message.answer("Сначала пришлите ссылку на видео.")
        return

    status = await callback.message.answer("🎬 Создаю видео с русскими субтитрами...")
    try:
        def build_subtitled_video(progress):
            segments, title = get_source_transcript(
                callback.from_user.id, url, progress
            )
            progress.update("🌍 Перевод субтитров")
            srt_file = save_translated_srt(title, segments)
            progress.update("📥 Подготовка исходного видео")
            video_file, _ = download_source_video(url, progress)
            progress.update("🎬 Встраивание субтитров")
            return burn_subtitles(video_file, srt_file, title)

        subtitled_video = await run_with_progress(
            status, "📥 Подготовка видео", build_subtitled_video
        )
        await status.edit_text("📤 Отправка видео в Telegram...")
        await callback.message.answer_video(
            FSInputFile(subtitled_video),
            caption="🎬 Reel с русскими субтитрами готов.",
            supports_streaming=True,
        )
        await status.edit_text("✅ Видео с русскими субтитрами готово.")
    except Exception as error:
        await status.edit_text(
            f"Ошибка перевода Reel:\n{reel_error_message(error)}"
        )


@dp.callback_query(F.data.in_({"reel_voice_ru", "source_voice_ru"}))
async def handle_source_voice_ru(callback: types.CallbackQuery):
    await callback.answer()
    url = user_links.get(callback.from_user.id)
    if not url:
        await callback.message.answer("Сначала пришлите ссылку на видео.")
        return

    status = await callback.message.answer(
        "🎙️ Создаю русскую озвучку. Это может занять несколько минут..."
    )
    try:
        def build_dub(progress):
            segments, title = get_source_transcript(
                callback.from_user.id, url, progress
            )
            progress.update("📥 Подготовка исходного видео")
            video_file, _ = download_source_video(url, progress)
            progress.update("🎙️ Синтез русской речи")
            return create_russian_dub(video_file, title, segments)

        dubbed_video = await run_with_progress(
            status, "📥 Подготовка видео", build_dub
        )
        await status.edit_text("📤 Отправка озвученного видео...")
        await callback.message.answer_video(
            FSInputFile(dubbed_video),
            caption="🎙️ Reel с русской озвучкой готов.",
            supports_streaming=True,
        )
        await status.edit_text("✅ Видео с русской озвучкой готово.")
    except Exception as error:
        await status.edit_text(
            f"Ошибка озвучивания Reel:\n{reel_error_message(error)}"
        )


@dp.callback_query(F.data == "pronunciation_settings")
async def handle_pronunciation_settings(callback: types.CallbackQuery):
    await callback.answer()
    awaiting_pronunciation.add(callback.from_user.id)

    entries = list_pronunciations(20)
    current = "\n".join(f"• {term} → {marked}" for term, marked in entries)
    await callback.message.answer(
        "🔤 Отправьте исправление в формате:\n\n"
        "каденс = кад+енс\n\n"
        "+ ставится перед ударной гласной. Разметка применяется только к озвучке.\n"
        "Для отмены отправьте /cancel.\n\n"
        f"Текущий словарь:\n{current or 'пока пуст'}"
    )


@dp.callback_query(F.data == "terminology_settings")
async def handle_terminology_settings(callback: types.CallbackQuery):
    await callback.answer()
    awaiting_terminology.add(callback.from_user.id)

    entries = list_terms(callback.from_user.id, 20)
    current = "\n".join(
        f"• {source} → {translation} [{category}]"
        for source, translation, _, category in entries
    )
    await callback.message.answer(
        "📚 Отправьте термин или устойчивую фразу в формате:\n\n"
        "overstride = переразмах шага | "
        "приземление стопы слишком далеко впереди | бег\n\n"
        "После = обязательный перевод. Пояснение и категория после | необязательны.\n"
        "Для отмены отправьте /cancel.\n\n"
        f"Текущий словарь:\n{current or 'пока пуст'}"
    )


@dp.message()
async def unknown(message: types.Message):
    user_id = message.from_user.id
    if user_id in awaiting_terminology and message.text:
        if message.text.strip().lower() == "/cancel":
            awaiting_terminology.discard(user_id)
            await message.answer("Настройка термина отменена.")
            return

        if "=" not in message.text:
            await message.answer(
                "Используйте формат:\n"
                "термин = перевод | пояснение | категория"
            )
            return

        source_term, details = message.text.split("=", 1)
        parts = [part.strip() for part in details.split("|", 2)]
        translation = parts[0] if parts else ""
        explanation = parts[1] if len(parts) > 1 else ""
        category = parts[2] if len(parts) > 2 else "общее"
        try:
            set_term(
                user_id,
                source_term,
                translation,
                explanation,
                category,
            )
            awaiting_terminology.discard(user_id)
            await message.answer(
                "✅ Термин сохранён:\n"
                f"{source_term.strip().lower()} → {translation}\n"
                f"Категория: {category}\n\n"
                "Он будет применён в следующем тренерском переводе."
            )
        except ValueError as error:
            await message.answer(f"Ошибка: {error}")
        return

    if user_id in awaiting_pronunciation and message.text:
        if message.text.strip().lower() == "/cancel":
            awaiting_pronunciation.discard(user_id)
            await message.answer("Настройка ударения отменена.")
            return

        if "=" not in message.text:
            await message.answer(
                "Используйте формат: термин = вариант с ударением\n"
                "Например: каденс = кад+енс"
            )
            return

        term, marked_text = message.text.split("=", 1)
        try:
            set_pronunciation(term, marked_text)
            awaiting_pronunciation.discard(user_id)
            await message.answer(
                f"✅ Произношение сохранено:\n"
                f"{term.strip().lower()} → {marked_text.strip().lower()}\n\n"
                "Оно будет применено при следующей генерации озвучки."
            )
        except ValueError as error:
            await message.answer(f"Ошибка: {error}")
        return

    await message.answer("Пришли ссылку на YouTube-видео.")


async def main():
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
