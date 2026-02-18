# Log format and field mapping

LogMiner-QA expects each log record to be a JSON object (or similar) with **at least** a timestamp-like field and a message-like field. Different organisations use different key names; the tool supports this via **built-in aliases** and **optional custom mapping**.

## Required fields

| Canonical name | Meaning | Required |
|----------------|---------|----------|
| **timestamp**  | When the event occurred | Yes |
| **message**    | Main log text or event description | Yes |
| **severity**   | Log level (e.g. INFO, ERROR) | No |

A record is **valid** only if it has at least one non-empty **timestamp**-like field and one non-empty **message**-like field. Invalid records are skipped and the count is reported in the logs.

## Built-in aliases

If you do not set custom mapping, the following keys are recognised (first match in the record wins).

- **Timestamp:** `timestamp`, `time`, `ts`, `@timestamp`, `date`, `datetime`, `created_at`, `logged_at`
- **Message:** `message`, `msg`, `text`, `log`, `body`, `content`, `description`, `summary`
- **Severity:** `severity`, `level`, `log_level`, `priority`, `loglevel`

Keys can be any string, including **dot-notation** (e.g. `type.keyword`, `user.keyword`). Use custom mapping to point to such keys: `--message-field type.keyword`.

So for example:

- Records with `time` and `msg` are valid.
- Records with `timestamp` and `message` are valid.
- Records with `ts` and `text` are valid.
- Records with `@timestamp` and `log` are valid.
- Records must have a message-like key such as `message`, `msg`, `text`, etc.; `event` is not treated as the message.

## Custom field mapping

If your logs use different key names (e.g. `event_time`, `log_line`), you can map them via config or CLI.

### CLI

```bash
python -m logminer_qa --input logs.jsonl --timestamp-field event_time --message-field log_line
```

Optional:

- `--timestamp-field KEY` – JSON key for timestamp
- `--message-field KEY` – JSON key for message
- `--severity-field KEY` – JSON key for severity/level

Custom keys are tried first; if the key is missing in a record, the built-in aliases are still used.

### Array-wrapped values

Some systems (e.g. Elasticsearch exports) store fields as **single-element arrays**, e.g. `"message": ["text"]`, `"@timestamp": ["2025-10-08T00:00:00.000Z"]`. LogMiner-QA:

- Treats such a value as the single element for **validation** (so the record is valid if that element is non-empty).
- **Normalizes** it to a scalar before processing, so downstream (sanitizer, parser) always see e.g. `"message": "text"`.

Only single-element lists/tuples are unwrapped; multi-element or empty arrays are left as-is.

### Config (Settings)

In code, set `settings.log_format` to a `LogFormatConfig` with optional `timestamp_field`, `message_field`, and `severity_field`. See `src/logminer_qa/log_format.py` and `src/logminer_qa/config.py`.

## Validation rules

- **Missing timestamp:** No recognised timestamp key, or value is `null`/empty string → record invalid, skipped.
- **Missing message:** No recognised message key, or value is `null`/empty string → record invalid, skipped.
- **Empty message:** A key exists but its value is blank (e.g. `"message": ""`) → invalid.

Valid records are processed; invalid ones are skipped and the number of skipped records is logged (e.g. `Skipped N invalid records`).

## Examples

**Valid (timestamp + message):**

```json
{"time": "2025-10-08T10:00:00Z", "msg": "User login"}
{"timestamp": "2025-10-08T10:00:00Z", "message": "Transfer completed"}
{"ts": "2025-10-08T10:00:00Z", "text": "Error in payment"}
{"@timestamp": "2025-10-08T10:00:00Z", "log": "Session started"}
{"timestamp": "2025-10-08T10:00:00Z", "message": "login"}
```

**Invalid (missing or empty message):**

```json
{"timestamp": "2025-10-08T10:00:00Z"}
{"time": "2025-10-08T10:00:00Z", "message": ""}
```

**Custom mapping:**

If your schema uses `event_time` and `log_line`:

```bash
python -m logminer_qa -i logs.jsonl --timestamp-field event_time --message-field log_line
```

Then a record like `{"event_time": "2025-10-08T10:00:00Z", "log_line": "Something happened"}` is valid.

**Array-wrapped (Elastic-style):**

```json
{"timestamp": ["2025-10-08T10:00:00Z"], "message": ["User login"], "type.keyword": ["Mobile Session Start"]}
```

This is valid and is normalized to scalar values before processing.

**Test run stack traces:** Records that look like test failures (e.g. `error_message`, `browser`, `selector`) are automatically normalized to have `message` and `timestamp` before validation. See [Test failure ingestion](TEST_FAILURE_INGESTION.md).

## Data cleaning expectations

What the tool **assumes** and **enforces** so logs are processable:

- **Required fields:** Each record must have at least one non-empty timestamp-like field and one non-empty message-like field (see [Required fields](#required-fields) and [Built-in aliases](#built-in-aliases)). Records missing either are skipped and counted.
- **Encoding:** Input files are read as **UTF-8**. Non-UTF-8 content may cause decode errors; the tool does not transcode.
- **Size limits (validation):**
  - String records: max **1 MB** per record.
  - Dict records: max **10,000 keys** and max **20 levels** of nesting. Larger or deeper records are rejected to reduce DoS risk.
- **Normalization:** Single-element array values (e.g. `["value"]`) are **unwrapped** to scalars before PII detection and hashing, so the sanitizer and parser always see scalar values.
- **PII handling:** The sanitizer scans **string** fields for patterns (emails, account-like numbers, phones, IBANs, etc.), redacts matches with stable tokens, and stores hashes for referential integrity. Non-string fields are left as-is. See `src/logminer_qa/sanitizer.py` and `SanitizerConfig` in `config.py`.
