import os
import re
import subprocess
from pathlib import Path

import httpx

from services.translate import translate_texts
from services.media import prepare_video_for_telegram


VOICEOVERS_DIR = Path("voiceovers")
VOICEOVERS_DIR.mkdir(exist_ok=True)


def _safe_name(title: str) -> str:
    name = re.sub(r"[^\w\-. ]+", "_", title, flags=re.UNICODE).strip(" ._")
    return (name or "reel")[:80]


def _synthesize(text: str, output_path: Path, target_seconds: float) -> None:
    api_key = os.getenv("YANDEX_API_KEY")
    if not api_key:
        raise RuntimeError("YANDEX_API_KEY не настроен")

    estimated_speed = len(text) / max(target_seconds * 13, 1)
    speed = min(3.0, max(0.7, estimated_speed))
    response = httpx.post(
        "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize",
        headers={"Authorization": f"Api-Key {api_key}"},
        data={
            "text": text,
            "lang": "ru-RU",
            "format": "mp3",
            "speed": f"{speed:.2f}",
        },
        timeout=120,
    )
    response.raise_for_status()
    output_path.write_bytes(response.content)


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


def _atempo_chain(speed: float) -> str:
    filters = []
    while speed > 2.0:
        filters.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        filters.append("atempo=0.5")
        speed /= 0.5
    filters.append(f"atempo={speed:.4f}")
    return ",".join(filters)


def create_russian_dub(
    video_path: str,
    title: str,
    segments: list[dict],
) -> str:
    if not segments:
        raise RuntimeError("В Reel не обнаружена речь для озвучивания")

    translations = translate_texts([segment["text"] for segment in segments], "ru")
    if len(translations) != len(segments):
        raise RuntimeError("Получен неполный перевод для озвучивания")

    stem = _safe_name(title)
    phrase_files = []
    for index, (segment, text) in enumerate(zip(segments, translations), start=1):
        path = VOICEOVERS_DIR / f"{stem}_{index:04d}.mp3"
        target_seconds = max(0.3, float(segment["end"]) - float(segment["start"]))
        _synthesize(text, path, target_seconds)
        phrase_files.append(path)

    command = ["ffmpeg", "-y", "-i", video_path]
    for path in phrase_files:
        command.extend(["-i", str(path)])

    filters = ["[0:a]volume=0.12[background]"]
    mix_inputs = ["[background]"]
    for index, (segment, path) in enumerate(zip(segments, phrase_files), start=1):
        target_seconds = max(0.3, float(segment["end"]) - float(segment["start"]))
        speed = _duration(path) / target_seconds
        delay_ms = max(0, round(float(segment["start"]) * 1000))
        label = f"voice{index}"
        filters.append(
            f"[{index}:a]{_atempo_chain(speed)},"
            f"apad,atrim=0:{target_seconds:.3f},adelay={delay_ms}|{delay_ms}[{label}]"
        )
        mix_inputs.append(f"[{label}]")

    filters.append(
        "".join(mix_inputs)
        + f"amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0[mixed]"
    )

    output_path = VOICEOVERS_DIR / f"{stem}_ru_voice.mp4"
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "0:v:0",
            "-map",
            "[mixed]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output_path),
        ]
    )
    subprocess.run(command, check=True, capture_output=True, text=True)
    return prepare_video_for_telegram(str(output_path))
