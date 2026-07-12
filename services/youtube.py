from pathlib import Path
import re
from yt_dlp import YoutubeDL

from services.media import prepare_video_for_telegram

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


def _progress_hook(progress):
    def hook(data):
        if not progress:
            return
        if data.get("status") == "downloading":
            percent = re.sub(r"\x1b\[[0-9;]*m", "", data.get("_percent_str", "")).strip()
            progress.update(f"📥 Скачивание: {percent}")
        elif data.get("status") == "finished":
            progress.update("⚙️ Обработка загруженного файла")
    return hook


def download_video(url: str, progress=None):
    output_template = str(DOWNLOAD_DIR / "%(title)s.%(ext)s")

    options = {
        "format": "137+140/136+140/18",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": False,
        "progress_hooks": [_progress_hook(progress)],
    }

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)

    filename = ydl.prepare_filename(info)

    if filename.endswith(".webm") or filename.endswith(".mkv"):
        filename = str(Path(filename).with_suffix(".mp4"))

    return prepare_video_for_telegram(filename, progress), info["title"]


def download_audio(url: str, progress=None):
    output_template = str(DOWNLOAD_DIR / "%(title)s.%(ext)s")

    options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "progress_hooks": [_progress_hook(progress)],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)

    filename = str(Path(ydl.prepare_filename(info)).with_suffix(".mp3"))

    return filename, info["title"]
