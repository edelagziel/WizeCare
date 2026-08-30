"""Small environment-backed configuration layer for the canonical pipeline."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default
    path = Path(value).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


VIDEO_DIR = _path_from_env("WIZECARE_VIDEO_DIR", BASE_DIR / "videos")
HEBREW_VIDEO_DIR = _path_from_env("WIZECARE_HEBREW_VIDEO_DIR", BASE_DIR / "HebVideo")
AUDIO_DIR = _path_from_env("WIZECARE_AUDIO_DIR", BASE_DIR / "audiofile")
TEXT_DIR = _path_from_env("WIZECARE_TEXT_DIR", BASE_DIR / "TextFiles")
AUDIO_DONE_DIR = _path_from_env("WIZECARE_AUDIO_DONE_DIR", BASE_DIR / "audioDone")
DONE_VIDEO_DIR = _path_from_env("WIZECARE_DONE_VIDEO_DIR", BASE_DIR / "doneVideos")
DONE_HEBREW_DIR = _path_from_env("WIZECARE_DONE_HEBREW_DIR", BASE_DIR / "doneHeb")
DONE_ALL_DIR = _path_from_env("WIZECARE_DONE_ALL_DIR", BASE_DIR / "done_all")

try:
    NUM_VIDEOS = max(1, int(os.getenv("WIZECARE_NUM_VIDEOS", "1")))
except ValueError as exc:
    raise ValueError("WIZECARE_NUM_VIDEOS must be a positive integer") from exc

RUN_MODE = os.getenv("WIZECARE_RUN_MODE", "").strip().lower()
LANGUAGE = os.getenv("WIZECARE_LANGUAGE", "").strip().lower()
