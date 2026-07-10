from pathlib import Path
from datetime import timedelta


TRANSCRIPTS_DIR = Path("transcripts")
TRANSCRIPTS_DIR.mkdir(exist_ok=True)


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    return str(timedelta(seconds=seconds))


def save_transcript_markdown(title: str, url: str, segments: list[dict]) -> str:
    safe_title = "".join(
        c for c in title
        if c.isalnum() or c in (" ", "-", "_")
    ).strip()

    if not safe_title:
        safe_title = "transcript"

    filename = TRANSCRIPTS_DIR / f"{safe_title[:80]}.md"

    lines = [
        f"# {title}",
        "",
        f"Источник: {url}",
        "",
        "## Расшифровка",
        "",
    ]

    for segment in segments:
        start = format_time(segment["start"])
        text = segment["text"]
        if text:
            lines.append(f"**{start}** — {text}")
            lines.append("")

    filename.write_text("\n".join(lines), encoding="utf-8-sig")
    return str(filename)
