"""Safe, dependency-light smoke tests for the canonical WizeCare pipeline.

This test intentionally does not import or invoke AI, Azure, Ollama, WhisperX,
Torch, Transformers, or FFmpeg. It validates configuration, wiring contracts,
and a small non-AI timestamp transformation using temporary fixture files.
"""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
TRANSLATE_DIR = ROOT_DIR / "translateSteps"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_configuration() -> None:
    sys.path.insert(0, str(TRANSLATE_DIR))
    import pipeline_config

    check(pipeline_config.BASE_DIR == TRANSLATE_DIR, "BASE_DIR is not project-relative")
    check(pipeline_config.VIDEO_DIR == TRANSLATE_DIR / "videos", "unexpected default VIDEO_DIR")
    check(pipeline_config.TEXT_DIR == TRANSLATE_DIR / "TextFiles", "unexpected default TEXT_DIR")
    check(pipeline_config.NUM_VIDEOS == 1, "unexpected default NUM_VIDEOS")
    check(pipeline_config.LANGUAGE == "", "unexpected default LANGUAGE")

    source = (TRANSLATE_DIR / "pipeline_config.py").read_text(encoding="utf-8")
    check("C:\\Users\\edenl" not in source, "Eden-specific path is hard-coded in config")
    check("Users/edenl" not in source, "Eden-specific path is hard-coded in config")

    override_code = (
        "import pipeline_config; "
        "assert pipeline_config.NUM_VIDEOS == 3; "
        "assert pipeline_config.LANGUAGE == 'he'; "
        "assert pipeline_config.VIDEO_DIR == pipeline_config.BASE_DIR / 'smoke_inputs'; "
        "print('configuration overrides ok')"
    )
    env = os.environ.copy()
    env.update(
        {
            "WIZECARE_NUM_VIDEOS": "3",
            "WIZECARE_LANGUAGE": "he",
            "WIZECARE_VIDEO_DIR": "smoke_inputs",
            "PYTHONPATH": str(TRANSLATE_DIR),
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", override_code],
        cwd=ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    check(result.returncode == 0, f"configuration override failed: {result.stderr.strip()}")


def test_timestamp_stage() -> None:
    sys.path.insert(0, str(TRANSLATE_DIR))
    from build_timed_script import map_text_to_timestamps_anylang

    with tempfile.TemporaryDirectory(prefix="wizecare-smoke-") as temp_dir:
        temp = Path(temp_dir)
        timestamps = temp / "timestamps.txt"
        output = temp / "timed_script.txt"
        timestamps.write_text(
            "[00:00:01.000 --> 00:00:02.000]\n"
            "[00:00:02.000 --> 00:00:03.000]\n",
            encoding="utf-8",
        )
        map_text_to_timestamps_anylang("first\nsecond", timestamps, output)
        rendered = output.read_text(encoding="utf-8")
        check(rendered.count("[") == 2, "timestamp fixture did not produce two entries")
        check("first" in rendered and "second" in rendered, "timestamp text was not preserved")


def test_safety_and_wiring() -> None:
    cleanup_source = (ROOT_DIR / "Become_Video" / "cleanUp.py").read_text(encoding="utf-8")
    check("WIZECARE_ALLOW_CLEANUP" in cleanup_source, "cleanup opt-in guard is missing")
    check(
        "Cleanup is disabled" in cleanup_source,
        "cleanup disabled message is missing",
    )

    runner_source = (ROOT_DIR / "run_two_scripts_and_move.py").read_text(encoding="utf-8")
    check("move_without_overwrite" in runner_source, "safe move helper is missing")
    check("sys.executable" in runner_source, "runner does not use the active Python executable")

    for path in (
        ROOT_DIR / "run_two_scripts_and_move.py",
        TRANSLATE_DIR / "pipeline_config.py",
        TRANSLATE_DIR / "run_pipeline.py",
        TRANSLATE_DIR / "audio_transcriber.py",
        TRANSLATE_DIR / "find_matching_file.py",
        TRANSLATE_DIR / "llama3_Run.py",
        ROOT_DIR / "Become_Video" / "run_full_hls_pipeline.py",
        ROOT_DIR / "Become_Video" / "cleanUp.py",
    ):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def report_tools() -> None:
    print(f"python={sys.executable}")
    print(f"ffmpeg={shutil.which('ffmpeg') or 'not found'}")
    print(f"node={shutil.which('node') or 'not found'}")
    print("no external pipeline stages invoked")


def main() -> int:
    test_configuration()
    test_timestamp_stage()
    test_safety_and_wiring()
    report_tools()
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
