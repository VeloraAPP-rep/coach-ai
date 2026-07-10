import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile

from config import BOT_TOKEN
from keyboards import video_actions_keyboard, translation_languages_keyboard
from services.youtube import download_video, download_audio
from services.whisper_service import transcribe_audio
from services.markdown import save_transcript_markdown
from services.openai_summary import make_summary_markdown
from services.translate import translate_markdown

from aiogram.client.session.aiohttp import AiohttpSession

session = AiohttpSession(timeout=120)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

user_links = {}
user_markdowns = {}


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer("Привет. Пришли ссылку на своё YouTube-видео.")


@dp.message(F.text.startswith("http"))
async def receive_link(message: types.Message):
    url = message.text.strip()
    user_links[message.from_user.id] = url

    await message.answer(
        "Что сделать с видео?",
        reply_markup=video_actions_keyboard()
    )


@dp.callback_query(F.data == "download_mp4")
async def handle_download_mp4(callback: types.CallbackQuery):
    await callback.answer()

    url = user_links.get(callback.from_user.id)
    if not url:
        await callback.message.answer("Сначала пришли ссылку.")
        return

    await callback.message.answer("Скачиваю MP4...")

    try:
        filename, title = download_video(url)

        await callback.message.answer_video(
            video=FSInputFile(filename),
            caption=title,
            supports_streaming=True
        )

    except Exception as error:
        await callback.message.answer(f"Ошибка при скачивании MP4:\n{error}")


@dp.callback_query(F.data == "download_mp3")
async def handle_download_mp3(callback: types.CallbackQuery):
    await callback.answer()

    url = user_links.get(callback.from_user.id)
    if not url:
        await callback.message.answer("Сначала пришли ссылку.")
        return

    await callback.message.answer("Скачиваю MP3...")

    try:
        filename, title = download_audio(url)

        await callback.message.answer_audio(
            FSInputFile(filename),
            title=title
        )

    except Exception as error:
        await callback.message.answer(f"Ошибка при скачивании MP3:\n{error}")


@dp.callback_query(F.data == "make_markdown")
async def handle_make_markdown(callback: types.CallbackQuery):
    await callback.answer()

    url = user_links.get(callback.from_user.id)
    if not url:
        await callback.message.answer("Сначала пришли ссылку.")
        return

    await callback.message.answer("Скачиваю аудио и делаю расшифровку. Это может занять несколько минут...")

    try:
        audio_file, title = download_audio(url)
        transcript = transcribe_audio(audio_file)
        markdown_file = save_transcript_markdown(title, url, transcript)

        user_markdowns[callback.from_user.id] = markdown_file

        await callback.message.answer_document(
            FSInputFile(markdown_file),
            caption="✅ Markdown готов."
        )

    except Exception as error:
        await callback.message.answer(f"Ошибка при создании Markdown:\n{error}")


@dp.callback_query(F.data == "make_summary")
async def handle_make_summary(callback: types.CallbackQuery):
    await callback.answer()

    markdown_file = user_markdowns.get(callback.from_user.id)
    if not markdown_file:
        await callback.message.answer("Сначала создайте Markdown.")
        return

    await callback.message.answer("🧠 Делаю краткое содержание...")

    try:
        summary_file = make_summary_markdown(markdown_file)

        await callback.message.answer_document(
            FSInputFile(summary_file),
            caption="🧠 Summary готов."
        )

    except Exception as error:
        await callback.message.answer(f"Ошибка при создании Summary:\n{error}")


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
    await callback.message.answer("Перевожу Markdown. Это может занять несколько минут...")

    try:
        translated_file = translate_markdown(markdown_file, target_language)
        await callback.message.answer_document(
            FSInputFile(translated_file),
            caption="✅ Перевод готов.",
        )
    except Exception as error:
        await callback.message.answer(f"Ошибка при переводе:\n{error}")


@dp.message()
async def unknown(message: types.Message):
    await message.answer("Пришли ссылку на YouTube-видео.")


async def main():
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
