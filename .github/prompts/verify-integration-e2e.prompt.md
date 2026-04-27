---
mode: "agent"
description: "Run end-to-end integration verification for upload->transcribe->worker->observer flow with progress state assertions and error propagation checks."
---
You are performing a strict end-to-end integration verification for the subtitle pipeline.

## Goals
1. Upload a sample media file using `/uploads` and validate absolute `file_path` is returned.
2. Enqueue `/transcribe` with returned `file_path` and capture `task_id`.
3. Validate `/subtitles/{task_id}` contract fields:
   - `status`
   - `progress`
   - `current_log`
   - `log_history`
   - `error_detail`
4. Validate state transition order in responses/log stream:
   - `UPLOADED` -> `EXTRACTING_AUDIO` -> `TRANSCRIBING` -> `COMPLETED`
5. Validate websocket stream `/ws/tasks/{task_id}` provides live logs and progress changes.
6. Force one negative case (invalid file path) and confirm `error_detail` includes specific traceback or detailed message, not generic failure.
7. Validate cleanup behavior by creating stale temp files and confirming 24-hour cleanup removes expired files only.

## Constraints
- Follow repository instructions in `.github/instructions/`.
- Prefer existing test/sample assets under `samples/`.
- Keep verification reproducible and scriptable.

## Deliverables
- A concise verification report with:
  1. Commands executed.
  2. API/websocket payload samples.
  3. Pass/fail matrix per goal.
  4. Root cause notes for any failures.
  5. Minimal code fixes applied (if needed) and re-test outcome.
