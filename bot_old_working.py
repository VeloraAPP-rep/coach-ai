import asyncio
import os
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from yt_dlp import YoutubeDL

BOT_TOKEN = "8902081226:AAHOVNez9NQjh_w9iTgj-NwBw6bM4bKm0dA"

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_links = {}


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привет. Пришли ссылку на своё YouTube-видео, а я предложу скачать MP4 или MP3."
    )


@dp.message(F.text.startswith("http"))
async def receive_link(message: types.Message):
    url = message.text.strip()
    user_links[message.from_user.id] = url

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📹 Скачать MP4", callback_data="download_mp4"),
                InlineKeyboardButton(text="🎵 Скачать MP3", callback_data="download_mp3"),
            ]
        ]
    )

    await message.answer("Что сделать с видео?", reply_markup=keyboard)


@dp.callback_query(F.data == "download_mp4")
async def download_mp4(callback: types.CallbackQuery):
    await callback.answer()
    url = user_links.get(callback.from_user.id)

    if not url:
        await callback.message.answer("Сначала пришли ссылку.")
        return

    await callback.message.answer("Скачиваю MP4...")

    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    opts = {
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "noplaylist": True,
    }

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video")

        mp4_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp4")

        await callback.message.answer_video(
            FSInputFile(mp4_path),
            caption=title
        )

        os.remove(mp4_path)

    except Exception as e:
        await callback.message.answer(f"Ошибка при скачивании MP4:\n{e}")


@dp.callback_query(F.data == "download_mp3")
async def download_mp3(callback: types.CallbackQuery):
    await callback.answer()
    url = user_links.get(callback.from_user.id)

    if not url:
        await callback.message.answer("Сначала пришли ссылку.")
        return

    await callback.message.answer("Скачиваю MP3...")

    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "audio")

        mp3_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp3")

        await callback.message.answer_audio(
            FSInputFile(mp3_path),
            title=title
        )

        os.remove(mp3_path)

    except Exception as e:
        await callback.message.answer(f"Ошибка при скачивании MP3:\n{e}")


@dp.message()
async def unknown(message: types.Message):
    await message.answer("Пришли ссылку на YouTube-видео.")


async def main():
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())