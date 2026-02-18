# Handoff guide for Tanvi

This guide helps you run LogMiner-QA on-prem and provides what we need from you to tailor the tool further.

## Quick start

See the [User guide](USER_GUIDE.md) for full details. In short:

```bash
python -m logminer_qa.cli --input your_logs.jsonl --output out.jsonl --report report.json
```

---

## Example run

We ran the tool on a combined sample (array-wrapped logs, scalar logs, test failures, and PII) to demonstrate all features.

### Command

```bash
python -m logminer_qa.cli \
  --input data/day5_combined_sample.jsonl \
  --output data/day5_sanitized.jsonl \
  --report data/day5_report.json \
  --tests data/day5_tests.feature \
  --ci-summary data/day5_ci_summary.json
```

**Result:** `Completed processing 5 valid records` (all 5 lines were normalized and processed).

### Input sample (`data/day5_combined_sample.jsonl`)

**Line 1 (array-wrapped, Tanvi-style):**
```json
{"timestamp": ["2025-10-08T10:00:00Z"], "message": ["User login"], "type.keyword": ["Mobile Session Start"], "processing_source": ["TechModAPIs"]}
```

**Line 2 (scalar):**
```json
{"time": "2025-10-08T10:01:00Z", "msg": "Transfer completed", "level": "INFO"}
```

**Line 3 (test failure with screenshot path):**
```json
{"error_message": "Error: Deposit with multiple transit checks...", "browser": "Microsoft Edge 144.8.0.0", "os": "Windows 11", "screenshot_path": "C:/screenshots/2026-02-12-18-56-39-test-1/.../errors/1.png"}
```

**Line 4 (test failure with selector):**
```json
{"log_message": "Error in fixture.afterEach hook...", "selector": "Selector('#ct-info-modal-modalbtn-0')", "browser": "Microsoft Edge 144.0.0.0", "os": "Windows 11"}
```

**Line 5 (with PII):**
```json
{"timestamp": "2025-10-08T10:02:00Z", "message": "Payment processed for account 987654321012", "amount": 2500, "email": "customer@example.com", "phone": "+1-555-123-4567"}
```

### Output samples

#### Sanitized logs (`data/day5_sanitized.jsonl`)

**Line 1 (normalized from array-wrapped):**
- `timestamp` and `message` are now **scalars** (not arrays)
- Original fields (`type.keyword`, `processing_source`) preserved
- Added: `redactions`, `hashed_fields`, `analysis` (parsed, embedding, event_label)

**Line 5 (PII redacted):**
- Account `987654321012` → `[TOKEN_6ABBBA3B5092BADAAD9EABE2]`
- Email `customer@example.com` → `[TOKEN_437C3AC129E88936C67E7B21]`
- `redactions` and `hashed_fields` show what was redacted and the hash

#### Report (`data/day5_report.json`)

```json
{
  "frequency_report": {
    "login_event": 0,
    "generic_event": 1,
    "error_event": 1
  },
  "cluster_summary": { ... },
  "anomaly_summary": { ... },
  "compliance_findings": [],
  "fraud_findings": []
}
```

#### Generated tests (`data/day5_tests.feature`)

```gherkin
Feature: Journey 7225542ab5f22dd1bba4cad053e89ea7
  Scenario: Validate journey 7225542ab5f22dd1bba4cad053e89ea7
  Given a sanitized transaction journey
  When the system observes error_event
  Then the compliance checks pass
```

#### CI summary (`data/day5_ci_summary.json`)

```json
{
  "total_records": 5,
  "high_severity_findings": 0,
  "anomalies_detected": 5,
  "compliance_findings": [],
  "fraud_findings": [],
  "top_clusters": { ... }
}
```

---

## What we need from you to tailor further

### 1. Field names

- **Event timestamp:** What field name does your system use for "when this log/event happened"? (We know `customerTenureDate` is customer tenure, not event time.)
- **Message:** What field name is the log message/description? Or should we use `type`/`type.keyword` as the message when there's no separate message field?

### 2. Synthetic sample

Can you provide **2–3 lines of fake data** with the same structure as your real logs (same keys, fake values, no PII)? That way we can support your exact format without ever seeing real data.

Example format (what we'd expect):
```jsonl
{"your_timestamp_field": "2025-10-08T10:00:00Z", "your_message_field": "Fake event", "type.keyword": "Fake Type", ...}
{"your_timestamp_field": "2025-10-08T10:01:00Z", "your_message_field": "Another fake event", ...}
```

### 3. Test failure format

If you send test run stack traces:
- Do they come as **JSON**, **CSV**, or **text**?
- If JSON, can you share one anonymized example (or the list of field names) so we can add a direct ingestion path if needed?

The tool already supports test-failure JSONL (see [Test failure ingestion](TEST_FAILURE_INGESTION.md)); we just want to confirm your format matches or if we need to add support.

### 4. Elastic/Datadog access

- How do you usually **export or query** logs from Elastic/Datadog (e.g. saved search, API, export to file)?
- We support connectors (see [Connectors](CONNECTORS.md)); knowing your access pattern helps us document the exact steps for your org.

---

## How to report issues

After running the tool on-prem, please share:

1. **Command you ran:** e.g. `python -m logminer_qa.cli --input ... --output ...`
2. **Error/log output:** Any validation errors (e.g. "Skipped N invalid records" — what fields were missing?), crashes, or unexpected behavior
3. **Sample input (anonymized):** If possible, 1–2 lines of your input (with PII removed) so we can reproduce

---

## Next steps

- Once you share field names or a synthetic sample, we can add custom mapping or normalization for your exact format.
- Once you test and report issues, we'll iterate.

For questions, see [User guide](USER_GUIDE.md), [Log format](LOG_FORMAT.md), [Connectors](CONNECTORS.md), and [Test failure ingestion](TEST_FAILURE_INGESTION.md).
