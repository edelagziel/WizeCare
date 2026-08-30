# WizeCare Video Translation Pipeline

WizeCare is an end-to-end AI-assisted multimedia localization pipeline developed during an internship project at WizeCare. The system takes source video, extracts speech, transcribes it, translates it into multiple languages, reviews and corrects the translated text, regenerates localized speech, preserves timing, and packages the result for browser playback with adaptive HLS streaming.

The project combines AI model orchestration, speech processing, multilingual NLP, neural text-to-speech, media synchronization, and video streaming into one automated workflow.

## End-to-End Flow

```text
Input video
  -> FFmpeg audio extraction
  -> WhisperX transcription with timestamps
  -> Ollama/LLaMA transcript cleanup
  -> NLLB multilingual translation
  -> LLaMA translation review and correction
  -> timestamp alignment
  -> Azure Speech neural TTS
  -> localized audio tracks
  -> multi-bitrate HLS packaging
  -> browser playback with selectable language tracks
```

## Demo

![WizeCare multilingual video player](docs/assets/wizecare-multilingual-player.png)

*Multilingual video playback with selectable localized audio tracks.*

## Engineering Highlights

- Automated orchestration across transcription, translation, validation, TTS, and media packaging
- WhisperX speech-to-text with segment-level timing information
- Hugging Face NLLB-200 for multilingual neural machine translation
- Ollama/LLaMA stages for transcript cleanup, translation review, and correction
- Azure Speech neural voices for localized audio generation
- Timestamp-aware audio reconstruction to preserve synchronization with the original video
- FFmpeg-based extraction, conversion, and media processing
- HLS packaging with multiple localized audio tracks and four video renditions: 1080p, 720p, 480p, and 240p
- Browser delivery through Video.js and HLS playlists
- Python-based pipeline orchestration with Node.js/FFmpeg integration
- Environment-based configuration for credentials and machine-specific paths
- Controlled file handoffs between the AI-processing and video-packaging stages

## Architecture

```mermaid
flowchart LR
    A[Source Video] --> B[Pipeline Orchestrator]
    B --> C[FFmpeg Audio Extraction]
    C --> D[WhisperX Transcription]
    D --> E[LLaMA Transcript Cleanup]
    E --> F[NLLB Translation]
    F --> G[LLaMA Review and Correction]
    G --> H[Timestamp Alignment]
    H --> I[Azure Speech TTS]
    I --> J[Localized Audio Tracks]
    J --> K[HLS Packaging]
    A --> K
    K --> L[Adaptive Video Renditions]
    K --> M[Multilingual Audio Playlists]
    L --> N[Video.js Browser Player]
    M --> N
```

### Main Pipeline Components

`run_two_scripts_and_move.py` acts as the high-level orchestration layer. It coordinates the AI translation pipeline and then passes the generated assets into the video-packaging stage.

`translateSteps/run_pipeline.py` manages the speech and language-processing workflow:

```text
video -> audio -> transcription -> cleanup -> translation -> review -> alignment -> TTS
```

`Become_Video/run_full_hls_pipeline.py` takes the processed media and produces the HLS delivery structure used by the browser player.

This separation keeps the language-processing and media-delivery concerns distinct while still allowing the complete workflow to run from a single orchestration entry point.

## Core Technical Challenges

### Preserving timing across languages

Translation changes sentence length and speaking duration. The pipeline keeps transcript timing information, aligns translated segments back to the original timeline, and generates localized speech with synchronization in mind rather than simply producing independent translated audio.

### Combining multiple AI systems

The workflow is not based on a single model. It coordinates several specialized components:

- WhisperX for speech recognition and timestamps
- NLLB-200 for multilingual translation
- LLaMA/Ollama for cleanup and translation review
- Azure Speech for neural TTS

Each stage produces data required by the next stage, so the pipeline manages intermediate formats, file movement, error boundaries, and synchronization between model outputs.

### Turning AI output into streamable media

The output is not just translated text or WAV files. The final stage converts generated assets into browser-ready HLS playlists with multiple video qualities and selectable localized audio tracks.

That creates a complete path from AI inference to an end-user media experience.

## Supported Languages

The configured project languages include:

- English
- Hebrew
- Russian
- Spanish
- Arabic
- Portuguese

## Project Structure

```text
WizeCare/
├── run_two_scripts_and_move.py       # High-level pipeline orchestrator
├── translateSteps/                   # Transcription, translation, review, alignment and TTS
├── Become_Video/                     # Media conversion and HLS packaging
├── jw_player/                        # Browser playback experiments/integration
├── docs/                             # Architecture and supporting documentation
├── tests/                            # Pipeline smoke/integration checks
├── EngliseDemo.mp4                   # Demo media
├── Heb.mp4                           # Demo media
└── README.md
```

## Technology Stack

### AI & Language Processing

- Python
- WhisperX
- Hugging Face Transformers
- Meta NLLB-200
- Ollama / LLaMA
- Azure Speech Services

### Media Processing

- FFmpeg
- Node.js
- HLS
- Video.js
- PyDub

### Pipeline & Integration

- Python orchestration
- Timestamp-based segment processing
- Environment-based configuration
- Multi-stage file handoff and packaging

## Running the Pipeline

The main orchestration entry point is:

```powershell
.venv\Scripts\python.exe run_two_scripts_and_move.py
```

The runner coordinates the translation pipeline, transfers generated assets between stages, and invokes the HLS packaging pipeline.

The project depends on Python 3.10, Node.js, FFmpeg, Ollama, compatible AI-model dependencies, and Azure Speech credentials.

Local secrets and machine-specific configuration belong in ignored environment files. The repository provides configuration examples without committing credentials.

## Project Outcome

The implemented system successfully demonstrated the complete localization workflow: source-video processing, timestamped transcription, multilingual translation, AI-assisted review, neural speech generation, synchronized localized audio, multi-quality HLS packaging, and browser playback.

The main engineering value of the project is the integration of several independent AI and media-processing technologies into one coordinated end-to-end pipeline rather than any single model in isolation.

## Security

Credentials are environment-based. `.env` files, local models, caches, generated media, and vendor material are excluded through repository ignore rules. Secrets and private service credentials should never be committed to source control.
