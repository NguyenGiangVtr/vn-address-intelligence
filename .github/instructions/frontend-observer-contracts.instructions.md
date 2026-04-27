---
description: "Use when implementing frontend observer contracts for subtitle task tracking, including state machine transitions, websocket reconnection policy, and task log truncation behavior."
name: "Frontend Observer Contracts"
applyTo: "frontend/src/**/*.{ts,tsx}"
---
# Frontend Observer Contracts

## State Machine Contract
- Task stage enum must use these values:
  - `UPLOADED`
  - `EXTRACTING_AUDIO`
  - `TRANSCRIBING`
  - `COMPLETED`
  - Optional terminal fallback: `FAILED`
- UI stepper should display exactly 4 visible milestones (UPLOADED -> EXTRACTING_AUDIO -> TRANSCRIBING -> COMPLETED).
- `FAILED` should render as error state on nearest active milestone and must not create extra milestone nodes.

## WebSocket Reconnection Policy
- Primary source for live logs is websocket endpoint per task.
- If websocket disconnects before terminal status:
  - retry with exponential backoff: 1s, 2s, 4s, 8s, max 15s.
  - stop retries once task reaches `COMPLETED` or `FAILED`.
- During reconnect gaps, polling endpoint may be used as fallback for status continuity.

## Log Truncation and Rendering
- Keep at most 200 log lines per task in client state.
- Render newest logs at bottom; auto-scroll only when user is already near bottom.
- `current_log` should always mirror the latest `log_history` entry when available.
- On `error_detail`, append highlighted red block in log console and preserve all previously streamed logs.

## Error Visibility
- Do not show generic failure text if `error_detail` exists.
- Log console must display exact backend error details and traceback text.
- Toast notifications should summarize failure, while log console holds full detail.
