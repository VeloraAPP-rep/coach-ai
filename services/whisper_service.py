from faster_whisper import WhisperModel

_model = None


def get_model():
    global _model
    if _model is None:
        _model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8"
        )
    return _model


def transcribe_audio(audio_path: str) -> list[dict]:
    model = get_model()

    segments, info = model.transcribe(
        audio_path,
        language=None,
        vad_filter=True,
        beam_size=1
    )

    result = []

    for segment in segments:
        result.append(
            {
                "start": float(segment.start),
                "end": float(segment.end),
                "text": segment.text.strip(),
            }
        )

    return result
