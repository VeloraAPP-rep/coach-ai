from pathlib import Path
from yt_dlp import YoutubeDL

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


def download_video(url: str):
    output_template = str(DOWNLOAD_DIR / "%(title)s.%(ext)s")

    options = {
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": False,
    }

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)

    filename = ydl.prepare_filename(info)

    if filename.endswith(".webm") or filename.endswith(".mkv"):
        filename = str(Path(filename).with_suffix(".mp4"))

    return filename, info["title"]


def download_audio(url: str):
    output_template = str(DOWNLOAD_DIR / "%(title)s.%(ext)s")

    options = {
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

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)

    filename = str(Path(ydl.prepare_filename(info)).with_suffix(".mp3"))

    return filename, info["title"]