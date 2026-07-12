import asyncio
import threading
import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


class ProgressState:
    def __init__(self, text: str):
        self._text = text
        self._lock = threading.Lock()

    def update(self, text: str) -> None:
        with self._lock:
            self._text = text

    def read(self) -> str:
        with self._lock:
            return self._text


async def run_with_progress(message, initial: str, worker: Callable[[ProgressState], T]) -> T:
    state = ProgressState(initial)
    started = time.monotonic()
    task = asyncio.create_task(asyncio.to_thread(worker, state))
    last_text = ""

    while not task.done():
        elapsed = int(time.monotonic() - started)
        text = f"{state.read()}\n⏱ Прошло: {elapsed // 60:02d}:{elapsed % 60:02d}"
        if text != last_text:
            try:
                await message.edit_text(text)
                last_text = text
            except Exception:
                pass
        await asyncio.sleep(2.5)

    return await task
