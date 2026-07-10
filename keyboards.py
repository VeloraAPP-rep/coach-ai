from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def video_actions_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📹 Скачать MP4",
                    callback_data="download_mp4"
                ),
                InlineKeyboardButton(
                    text="🎵 Скачать MP3",
                    callback_data="download_mp3"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📝 Markdown",
                    callback_data="make_markdown"
                ),
                InlineKeyboardButton(
                    text="🧠 Summary",
                    callback_data="make_summary"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌍 Перевести Markdown",
                    callback_data="translate_markdown"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🧠 Тренерский перевод (RU)",
                    callback_data="trainer_translation"
                ),
            ],
        ]
    )


def translation_languages_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="translate:Русский"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="translate:English"),
            ],
            [
                InlineKeyboardButton(text="🇪🇸 Español", callback_data="translate:Español"),
                InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="translate:Deutsch"),
            ],
            [
                InlineKeyboardButton(text="🇫🇷 Français", callback_data="translate:Français"),
                InlineKeyboardButton(text="🇮🇹 Italiano", callback_data="translate:Italiano"),
            ],
        ]
    )


def reel_actions_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📹 Скачать Reel", callback_data="download_reel"),
                InlineKeyboardButton(text="📝 Markdown", callback_data="reel_markdown"),
            ],
            [
                InlineKeyboardButton(text="🇷🇺 Субтитры SRT", callback_data="reel_srt_ru"),
            ],
            [
                InlineKeyboardButton(
                    text="🎬 Видео с RU-субтитрами",
                    callback_data="reel_video_ru",
                ),
            ],
        ]
    )
