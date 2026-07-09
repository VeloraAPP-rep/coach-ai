import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile

from config import BOT_TOKEN
from keyboards import video_actions_keyboard
from services.youtube import download_video, download_audio

from services.whisper_service import transcribe_audio
from services.markdown import save_transcript_markdown

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_links = {}


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привет. Пришли ссылку на своё YouTube-видео.",
    )


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
    await callback.message.answer("Markdown добавим следующим шагом.")


@dp.message()
async def unknown(message: types.Message):
    await message.answer("Пришли ссылку на YouTube-видео.")


async def main():
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())