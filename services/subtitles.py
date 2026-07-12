import re
import subprocess
from pathlib import Path

from services.translate import translate_texts
from services.media import prepare_video_for_telegram


SUBTITLES_DIR = Path("subtitles")
SUBTITLES_DIR.mkdir(exist_ok=True)


def _safe_name(title: str) -> str:
    name = re.sub(r"[^\w\-. ]+", "_", title, flags=re.UNICODE).strip(" ._")
    return (name or "reel")[:80]


def _srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def save_translated_srt(title: str, segments: list[dict]) -> str:
    if not segments:
        raise RuntimeError(
            "В Reel не обнаружена речь. Если текст показан только на видео, нужен OCR кадров."
        )

    source_texts = [segment["text"] for segment in segments]
    translated_texts = translate_texts(source_texts, "ru")
    if len(translated_texts) != len(segments):
        raise RuntimeError("Количество субтитров после перевода не совпадает")

    blocks = []
    for index, (segment, text) in enumerate(zip(segments, translated_texts), start=1):
        blocks.append(
            f"{index}\n{_srt_time(segment['start'])} --> {_srt_time(segment['end'])}\n{text}"
        )

    path = SUBTITLES_DIR / f"{_safe_name(title)}_ru.srt"
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return str(path)


def burn_subtitles(video_path: str, srt_path: str, title: str) -> str:
    output_path = SUBTITLES_DIR / f"{_safe_name(title)}_ru_subtitles.mp4"
    subtitle_filter = f"subtitles={Path(srt_path).resolve().as_posix()}"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vf",
            subtitle_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "copy",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return prepare_video_for_telegram(str(output_path))
