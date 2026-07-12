from services.instagram import (
    download_reel,
    download_reel_audio,
    is_instagram_url,
)
from services.youtube import download_audio, download_video


def download_source_video(url: str, progress=None) -> tuple[str, str]:
    if is_instagram_url(url):
        return download_reel(url, progress)
    return download_video(url, progress)


def download_source_audio(url: str, progress=None) -> tuple[str, str]:
    if is_instagram_url(url):
        return download_reel_audio(url, progress)
    return download_audio(url, progress)
