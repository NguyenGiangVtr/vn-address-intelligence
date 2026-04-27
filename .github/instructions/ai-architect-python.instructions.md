---
description: "Use when implementing or modifying FastAPI, Celery, FFmpeg, WhisperX, async subtitle pipeline, retry/backoff, and Python architecture in this project. Enforces clean architecture, dependency injection, strict typing, structured logging, and resilient worker behavior."
name: "AI Architect Rules - Auto Subtitle Project"
applyTo: "**/*.py"
---
# AI Architect Rules: Auto-Subtitle Project

## Tech Stack and Architecture
- Use FastAPI for asynchronous API boundaries and Celery for distributed task execution.
- Keep clean architecture boundaries explicit: API layer orchestration only, service layer domain logic, infrastructure layer external integrations.
- Prefer dependency injection patterns for service/model wiring instead of hard-coded dependencies.
- Use Pydantic v2 models for API contracts and structured payload validation.

## Coding Standards
- All file, process, network, and external I/O must be non-blocking using `asyncio` boundaries.
- Do not use `print()`; use structured logging via `logger.info` and `logger.error` with contextual fields.
- Require Google-style docstrings (`Args`, `Returns`, `Raises`) for all public functions, API endpoints, and Celery tasks.
- Private helpers (names starting with `_`) must keep strict type hints; add a short one-line comment only when logic is non-trivial.
- Prefer modern Python typing syntax (Python 3.10+): `list[str]`, `dict[str, Any]`, and union with `| None`.

## Domain-Specific Logic
- Audio extraction must force FFmpeg output to mono PCM `s16le`, `16000` Hz.
- WhisperX model weights must be loaded once per worker process (singleton) and reused across tasks.
- Optimize for batch and queue throughput; avoid per-request model initialization.
- Perform aggressive VRAM cleanup at worker process shutdown/recycle hooks.
- Keep singleton-loaded models resident during active task execution to optimize inference speed.
- Run `torch.cuda.empty_cache()` only after large batches (for example, more than 5 files) to reduce memory fragmentation risk.

## Error Handling and Reliability
- Use custom exceptions for domain failures: `AudioExtractionError`, `TranscriptionError`, and `AlignmentError`.
- Celery tasks must implement retry with exponential backoff for transient failures.
- Configure task execution for safe shutdown and requeue behavior to minimize in-flight task loss.

## Practical Defaults for This Repository
- Keep API endpoints thin in `app/main.py`; move business logic into `app/services/`.
- Keep worker task wrappers thin in `app/tasks.py`; call async service functions from tasks.
- Keep model bootstrap logic isolated in `app/services/whisperx_singleton.py`.
- Keep audio extraction isolated in `app/services/audio.py`.
