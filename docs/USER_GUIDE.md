# User guide

This guide explains how to run LogMiner-QA on-prem: what input it expects, how to run from files or from Elasticsearch/Datadog, and where to find the outputs.

## What you need before running

### Required fields per record

Each log record must have **at least one timestamp-like field** and **one message-like field** (non-empty). The tool accepts many common key names; you can also map custom names.

- **Timestamp:** `timestamp`, `time`, `ts`, `@timestamp`, `date`, `datetime`, `created_at`, `logged_at` (or your field via `--timestamp-field`).
- **Message:** `message`, `msg`, `text`, `log`, `body`, `content`, `description`, `summary` (or your field via `--message-field`).

Records that lack either are **skipped** and the count is logged. See [Log format and field mapping](LOG_FORMAT.md) for full aliases and custom mapping.

### Optional: field mapping

If your logs use different key names (e.g. `event_time`, `log_line`), pass them on the command line:

```bash
python -m logminer_qa.cli --input logs.jsonl --timestamp-field event_time --message-field log_line --output out.jsonl --report report.json
```

Custom keys are tried first; if missing in a record, the built-in aliases are still used.

---

## How to run on-prem

### From a file

Supported formats: **JSONL** (`.jsonl`, `.ndjson`), **JSON** (single object or array), **CSV**, or **plain text** (one line per record).

```bash
python -m logminer_qa.cli --input path/to/logs.jsonl --output out.jsonl --report report.json
```

You can add generated tests and a CI summary:

```bash
python -m logminer_qa.cli --input logs.jsonl --output out.jsonl --report report.json --tests tests.feature --ci-summary build/summary.json
```

If your file uses non-standard field names, add `--timestamp-field` and `--message-field` as above.

### From Elasticsearch or Datadog

Use a **connectors config file** (JSON) that defines one or more connectors. The tool fetches logs from the configured sources and processes them through the same pipeline.

```bash
python -m logminer_qa.cli --connectors-config connectors.json --output out.jsonl --report report.json
```

You can combine file input and connectors; all sources are merged:

```bash
python -m logminer_qa.cli --input local.jsonl --connectors-config connectors.json --output out.jsonl --report report.json
```

See [Connectors: Elasticsearch and Datadog](CONNECTORS.md) for required/optional options and example configs. Use environment variables for API keys and passwords; the tool does not substitute placeholders in the JSON file.

### If you cannot connect directly

Export logs from Elastic/Datadog to a **JSONL file** (one document per line) and run with `--input`. Use `--timestamp-field` and `--message-field` if your export uses different key names. See [Connectors – Alternative: export to JSONL](CONNECTORS.md#alternative-export-to-jsonl-and-use---input).

---

## Test failure / stack trace data

You can feed **test run stack traces** (e.g. from TestCafe, Cypress) as JSONL. Each line should be a JSON object with fields such as `error_message`, `log_message`, `browser`, `os`, `selector`, `screenshot_path`. The tool normalizes these into `message` and `timestamp` so they pass validation and are processed like normal logs.

Same CLI; no extra flags:

```bash
python -m logminer_qa.cli --input test_failures.jsonl --output out.jsonl --report report.json
```

See [Test failure ingestion](TEST_FAILURE_INGESTION.md) for the exact schema and examples.

---

## Where to find outputs

| Output | Flag | Description |
|--------|------|-------------|
| **Sanitized logs** | `--output path` | One JSON object per line; PII redacted, normalized. |
| **Report** | `--report path` | JSON with frequency report, cluster summary, anomaly summary, journey insights, compliance and fraud findings. |
| **Generated tests** | `--tests path` | Gherkin (`.feature`) scenarios. |
| **CI summary** | `--ci-summary path` | Compact JSON for pipeline gates (e.g. high-severity findings, anomaly count). |

---

## Data cleaning and limits

The tool assumes and enforces:

- **Encoding:** Input files are read as **UTF-8**.
- **Size limits:** String records max **1 MB**; dict records max **10,000 keys** and **20 levels** of nesting. Larger records are rejected.
- **Normalization:** Single-element array values (e.g. `["value"]`) are unwrapped to scalars before PII handling.
- **PII:** String fields are scanned for patterns (emails, account-like numbers, phones, IBANs, etc.); matches are redacted and hashed. Non-string fields are left as-is.

See [Data cleaning expectations](LOG_FORMAT.md#data-cleaning-expectations) for full details.

---

## For organisations using Elastic or Datadog

- **Direct access:** Use [Connectors](CONNECTORS.md) with a `connectors.json` file. Point `endpoint`/`index` (Elastic) or `query` (Datadog) at your logs. Keep API keys and passwords in environment variables or a secrets manager.
- **No direct access:** Export logs to JSONL (e.g. from Kibana or Datadog UI) and run with `--input exported.jsonl`. Use `--timestamp-field` and `--message-field` if your export uses different field names.
- **Test failures:** If you also ingest test run stack traces, use the [test failure JSONL format](TEST_FAILURE_INGESTION.md); the same CLI run can mix normal logs and test-failure records.

For a quick local run, see [Quick Start](QUICK_START.md).
