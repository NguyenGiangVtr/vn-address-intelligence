# Project Guidelines

## Code Style
- Use Python 3.11+ with full type hints for all public functions.
- Keep I/O boundaries async where possible (`asyncio.create_subprocess_exec`, `asyncio.to_thread`).
- Prefer small service modules under `app/services/` and keep API/task layers thin.

## Architecture
- API entrypoint: `app/main.py`.
- Celery app and worker config: `app/celery_app.py`.
- Task orchestration: `app/tasks.py`.
- Subtitle pipeline: `app/services/subtitles.py`.
- Audio extraction and model bootstrapping should stay in dedicated service files.

## Build and Test
- Install dependencies: `pip install -r requirements.txt`.
- Run API: `uvicorn app.main:app --reload`.
- Run worker: `celery -A app.celery_app.celery_app worker --loglevel=INFO`.
- Run lint/type tools when added; keep this file updated with exact commands.

## Conventions
- WhisperX weights must be loaded once per worker process via singleton pattern.
- Output subtitle payloads must remain JSON and SRT-compatible (`index`, `start`, `end`, `text`, `words`).
- Redis must be used as broker/backend and worker shutdown behavior must favor requeue safety (`acks_late`, reject on lost worker, low prefetch).
- Prefer linking docs instead of duplicating detailed operational guidance as the repo grows.
