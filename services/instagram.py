import os
import subprocess
from pathlib import Path

from yt_dlp import YoutubeDL


DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


def _cookie_file() -> str | None:
    configured = os.getenv("INSTAGRAM_COOKIES_FILE")
    if configured and Path(configured).is_file():
        return configured
    default = Path("secrets/instagram_cookies.txt")
    return str(default) if default.is_file() else None


def _common_options() -> dict:
    options = {
        "noplaylist": True,
        "quiet": False,
    }
    cookie_file = _cookie_file()
    if cookie_file:
        options["cookiefile"] = cookie_file
    return options


def is_instagram_url(url: str) -> bool:
    lowered = url.lower()
    return "instagram.com/reel/" in lowered or "instagram.com/reels/" in lowered


def download_reel(url: str) -> tuple[str, str]:
    output_template = str(DOWNLOAD_DIR / "instagram_%(id)s.%(ext)s")
    options = {
        **_common_options(),
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
    }

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = Path(ydl.prepare_filename(info))

    mp4_filename = filename.with_suffix(".mp4")
    if mp4_filename.exists():
        filename = mp4_filename

    telegram_filename = filename.with_name(f"{filename.stem}_telegram.mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(filename),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "high",
            "-level",
            "4.0",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(telegram_filename),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return str(telegram_filename), info.get("title") or f"Instagram Reel {info.get('id', '')}"


def download_reel_audio(url: str) -> tuple[str, str]:
    output_template = str(DOWNLOAD_DIR / "instagram_%(id)s.%(ext)s")
    options = {
        **_common_options(),
        "format": "bestaudio/best",
        "outtmpl": output_template,
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
        filename = Path(ydl.prepare_filename(info)).with_suffix(".mp3")
    return str(filename), info.get("title") or f"Instagram Reel {info.get('id', '')}"
