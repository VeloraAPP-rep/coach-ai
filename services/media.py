import subprocess
from pathlib import Path


TELEGRAM_UPLOAD_LIMIT = 49_000_000
TARGET_FILE_SIZE = 47_000_000


def _duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def prepare_video_for_telegram(filename: str, progress=None) -> str:
    source = Path(filename)
    if source.stat().st_size <= TELEGRAM_UPLOAD_LIMIT:
        return str(source)

    if progress:
        progress.update("🗜 Сжатие видео: проход 1 / 2")

    duration = _duration(source)
    audio_bitrate = 64_000
    total_bitrate = int(TARGET_FILE_SIZE * 8 / duration)
    video_bitrate = total_bitrate - audio_bitrate
    if video_bitrate < 200_000:
        raise RuntimeError(
            "Видео слишком длинное для отправки через Telegram даже после сжатия."
        )

    output = source.with_name(f"{source.stem}_telegram.mp4")
    passlog = source.parent / f".{source.stem}_ffmpeg2pass"
    scale_filter = "scale='min(1280,iw)':-2"

    common = [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-b:v",
        str(video_bitrate),
        "-vf",
        scale_filter,
        "-pix_fmt",
        "yuv420p",
        "-passlogfile",
        str(passlog),
    ]
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            *common,
            "-pass",
            "1",
            "-an",
            "-f",
            "mp4",
            "/dev/null",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if progress:
        progress.update("🗜 Сжатие видео: проход 2 / 2")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            *common,
            "-pass",
            "2",
            "-c:a",
            "aac",
            "-b:a",
            "64k",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    for log_file in source.parent.glob(f"{passlog.name}*"):
        log_file.unlink(missing_ok=True)

    if output.stat().st_size > TELEGRAM_UPLOAD_LIMIT:
        output.unlink(missing_ok=True)
        raise RuntimeError("Не удалось сжать видео до лимита Telegram 50 МБ.")
    return str(output)
