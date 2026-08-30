# Canonical Pipeline Runbook

## Start

From the repository root:

```powershell
.venv\Scripts\python.exe run_two_scripts_and_move.py
```

The outer script asks how many videos to process. For a representative run,
enter `1`. `run_pipeline.py` then asks for `all` or `manual` mode unless the
corresponding environment variables are set.

## Inputs

Place the English input in:

```text
translateSteps/videos/
```

Place the matching Hebrew/source video in:

```text
translateSteps/HebVideo/
```

The extraction script selects the newest supported video. The matching helper
extracts the first number from the generated English audio filename and requires
a Hebrew filename containing the same first number. Without that match, the
current normal flow skips transcription.

## Stages and outputs

| Stage | Input | Output / handoff |
| --- | --- | --- |
| English extraction | `videos/*` | `audiofile/output_<n>.wav`, video moves to `doneVideos` |
| Hebrew extraction | matching `HebVideo/*` | `done_all/output_he_<n>.wav`, video moves to `doneHeb` |
| Transcription | newest `audiofile/*` | `TextFiles/EngAudio.txt`, audio moves to `audioDone` |
| LLaMA cleanup | transcription text | cleaned text in memory |
| NLLB translation | cleaned text | translated text in memory |
| Review and correction | translated text | fixed translation in memory |
| Timestamp alignment | `EngAudio.txt` and fixed text | `TextFiles/TimedText.txt` |
| Azure TTS | `TimedText.txt` | `done_all/output_<lang>_<run>.wav` |
| Handoff | `audioDone/*.wav`, `done_all/*.wav` | `Become_Video/WAV/*.wav` |
| Audio packaging | `WAV/*.wav` | `mp4a/audio_<lang>.m4a`, then HLS audio |
| Video packaging | `doneVideos/*` | four HLS quality trees and root playlist |

## Environment variables

Path variables are relative to `translateSteps` unless absolute paths are used:

```text
WIZECARE_VIDEO_DIR
WIZECARE_HEBREW_VIDEO_DIR
WIZECARE_AUDIO_DIR
WIZECARE_TEXT_DIR
WIZECARE_AUDIO_DONE_DIR
WIZECARE_DONE_VIDEO_DIR
WIZECARE_DONE_HEBREW_DIR
WIZECARE_DONE_ALL_DIR
WIZECARE_NUM_VIDEOS
WIZECARE_RUN_MODE
WIZECARE_LANGUAGE
```

Azure TTS requires local ignored values for `AZURE_SPEECH_KEY_1` and
`AZURE_SPEECH_REGION`. Never place those values in tracked files.

## Side effects and safety

- Initial extraction creates missing folders and moves processed input videos.
- Transcription moves processed audio and rewrites `EngAudio.txt`.
- Timestamp alignment rewrites `TimedText.txt`.
- TTS refuses an existing output filename.
- WAV conversion moves WAV files and uses FFmpeg overwrite mode for M4A output.
- HLS conversion removes matching old playlists/segments and moves source files.
- Video HLS conversion moves completed source videos to `finiseVideo`.
- Cleanup is disabled by default and requires explicit `WIZECARE_CLEANUP=1`.

Run against a disposable copy when validating side-effecting stages.

## Monitoring checklist

Monitor these folders during a run:

```text
translateSteps/audiofile
translateSteps/doneVideos
translateSteps/audioDone
translateSteps/TextFiles
translateSteps/done_all
Become_Video/WAV
Become_Video/mp4a
Become_Video/done_m4a
Become_Video/doneVideos
Become_Video/finiseVideo
Become_Video/audio_*
Become_Video/high
Become_Video/medium
Become_Video/low
Become_Video/verylow
```
