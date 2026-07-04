from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def video_actions_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📹 Скачать MP4", callback_data="download_mp4"),
                InlineKeyboardButton(text="🎵 Скачать MP3", callback_data="download_mp3"),
            ],
            [
                InlineKeyboardButton(text="📝 Markdown", callback_data="make_markdown"),
            ],
        ]
    )