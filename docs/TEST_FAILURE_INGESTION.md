# Test failure / stack trace ingestion

LogMiner-QA can ingest **test run stack trace** data (e.g. from TestCafe, Cypress, or similar runners) so it is processed like normal logs. Each test-failure entry is normalized to a canonical log record with `message` and `timestamp` before validation.

## How to feed test failure data

Use the same CLI as for log files. Pass a **JSONL file** where each line is a JSON object describing one test failure:

```bash
python -m logminer_qa --input test_failures.jsonl --output out.jsonl --report report.json
```

No extra flags are required. Records that look like test failures (see schema below) are automatically converted to the canonical shape; records that already have `message` and `timestamp` (or aliases) are left unchanged.

## Test failure record schema

A single test-failure entry is a JSON object with some of the following fields. **Message** and **timestamp** are derived if missing.

| Field | Purpose | Used for canonical |
|-------|---------|--------------------|
| `error_message` or `log_message` or `message` | Main error text | **message** (first present) |
| `timestamp`, `time`, `event_time`, etc. | When the failure occurred | **timestamp** (if present) |
| `screenshot_path` | File path (e.g. containing date/time) | **timestamp** extracted from path if pattern `YYYY-MM-DD-HH-MM-SS` is found |
| `hook_error` | e.g. "Error in fixture.afterEach hook" | Appended to **message** if present |
| `selector` | e.g. "Selector('#ct-info-modal-modalbtn-8')" | Appended to **message**; also kept as field |
| `browser` | e.g. "Microsoft Edge 144.8.0.0" | Kept as field |
| `os`, `operating_system` | e.g. "Windows 11" | Kept as field |

- If **message** cannot be built from the above, it becomes `"Test failure (no message)"`.
- If **timestamp** is not in the record and cannot be parsed from `screenshot_path`, the ingestion time (UTC) is used.

A record is treated as a **test failure** only if (1) it is a dict, (2) it has at least one of: `error_message`, `log_message`, `selector`, `screenshot_path`, `hook_error`, `browser`, `os`, `operating_system`, and (3) it does **not** already satisfy the normal log requirement (timestamp-like + message-like field). So normal logs are never rewritten.

## Example JSONL lines

```jsonl
{"error_message": "Error: Deposit with multiple transit checks with ON US Check and 3 day hold in BEEundefined", "browser": "Microsoft Edge 144.8.0.0", "os": "Windows 11", "screenshot_path": "C:/screenshots/2026-02-12-18-56-39-test-1/Microsoft_Edge_144.8.0.0_Windows_11/errors/1.png"}
{"log_message": "Error in fixture.afterEach hook - The specified selector does not match any element in the DOM tree.", "selector": "Selector('#ct-info-modal-modalbtn-0')", "browser": "Microsoft Edge 144.0.0.0", "os": "Windows 11"}
```

After normalization, the first line gets a **timestamp** from the path (`2026-02-12T18:56:39Z`) and **message** from `error_message`; the second gets **timestamp** from the current time and **message** from `log_message` and `selector`. Both then pass validation and flow through sanitization, parsing, and reporting like any other log.

## Implementation

See `src/logminer_qa/test_failure.py`: `is_test_failure_record()`, `test_failure_to_canonical()`. The pipeline calls these before validation when `validate_inputs` is enabled.
