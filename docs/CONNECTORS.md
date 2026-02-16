# Connectors: Elasticsearch and Datadog

LogMiner-QA can pull logs directly from **Elasticsearch** (ELK) and **Datadog** via a connectors config file. Records from connectors are normalized to include `message` and `timestamp` so they pass validation and flow through the same pipeline as file input (array normalization, test-failure handling, sanitization, reporting).

## How to run with connectors

Use `--connectors-config` with a JSON file that defines one or more connectors:

```bash
python -m logminer_qa.cli --connectors-config connectors.json --output out.jsonl --report report.json
```

You can combine file input and connectors; all sources are merged into one stream:

```bash
python -m logminer_qa.cli --input logs.jsonl --connectors-config connectors.json --output out.jsonl --report report.json
```

The tool does **not** substitute placeholders like `{{ env VAR }}` in the JSON file. Use environment variables for secrets and inject them when building the config (e.g. via a script or your deployment tooling).

---

## Elasticsearch (ELK)

Connector name in config: **`elk`** or **`elasticsearch`**.

### Required options

| Option     | Description |
|-----------|-------------|
| `endpoint` | Base URL of the Elasticsearch cluster, e.g. `https://your-elastic.example.com:9200` |
| `index`   | Index name or pattern, e.g. `logs-*` or `myapp-2025.01` |

### Optional options

| Option      | Description | Default |
|------------|-------------|---------|
| `query`    | Elasticsearch query DSL (object) | `{"query": {"match_all": {}}, "sort": [{"@timestamp": {"order": "desc"}}]}` |
| `page_size`| Number of documents per request | `500` |
| `auth`     | Object with `username` and `password`, or `api_key` | none |
| `verify_ssl` | Whether to verify TLS certificates | `true` |

### Example `connectors.json` (Elasticsearch)

```json
{
  "elk": {
    "endpoint": "https://your-elastic.example.com:9200",
    "index": "logs-*",
    "page_size": 500,
    "auth": {
      "username": "elastic",
      "password": "YOUR_ELASTIC_PASSWORD"
    },
    "verify_ssl": true
  }
}
```

Use environment variables for the password in production (e.g. generate the JSON with `ELASTIC_PASSWORD` from env so the secret is not stored in the file).

### Normalized fields

The connector reads `_source` from each hit and sets:

- **`message`**: from `_source.message` or the document `_id` if message is missing
- **`timestamp`**: from `_source["@timestamp"]` or `_source.timestamp`, or current UTC time if missing
- **`event`**: from `_source.event` or `"elk_event"`
- **`source`**: connector name (e.g. `"elk"`)

---

## Datadog

Connector name in config: **`datadog`**.

### Required options

| Option    | Description |
|----------|-------------|
| `api_key` | Datadog API key |
| `app_key` | Datadog application key |
| `query`   | Log query string, e.g. `service:myapp status:error` |

### Optional options

| Option     | Description | Default |
|-----------|-------------|---------|
| `region`  | Datadog region, e.g. `"us"`, `"us3"`, `"eu"` | `"us"` |
| `timeframe` | Object with `from` and `to` (e.g. `"now-1h"`, `"now"`) | `{"from": "now-1h", "to": "now"}` |
| `limit`   | Max number of log events per request | `500` |

### Example `connectors.json` (Datadog)

```json
{
  "datadog": {
    "api_key": "YOUR_DD_API_KEY",
    "app_key": "YOUR_DD_APP_KEY",
    "query": "service:myapp status:error",
    "limit": 500,
    "region": "us"
  }
}
```

Set `DD_API_KEY` and `DD_APP_KEY` in the environment and substitute them when generating the config so secrets are not stored in the file.

### Normalized fields

The connector reads each log event and sets:

- **`message`**: from `content.attributes.message` or `content.message`
- **`timestamp`**: from `attributes.timestamp` or the event `timestamp`
- **`event`**: from `attributes.service` or `"datadog_event"`
- **`source`**: connector name (e.g. `"datadog"`)

---

## Alternative: export to JSONL and use `--input`

If the tool cannot reach Elasticsearch or Datadog from the run environment (e.g. air-gapped or no network path), export logs to a **JSONL file** (one JSON document per line) and run with `--input`:

```bash
python -m logminer_qa.cli --input exported_logs.jsonl --output out.jsonl --report report.json
```

If your export uses different field names for timestamp and message, use [field mapping](LOG_FORMAT.md#custom-field-mapping):

```bash
python -m logminer_qa.cli --input exported_logs.jsonl --timestamp-field @timestamp --message-field log_message --output out.jsonl --report report.json
```

See [Log format and field mapping](LOG_FORMAT.md) for built-in aliases and custom mapping.

---

## Compatibility with the pipeline

Connector records already include `message` and `timestamp` (or defaults). They are:

- Validated (required fields)
- Normalized (single-element arrays unwrapped) if the source returns array-valued fields
- Treated as test-failure records only if they have test-failure keys and lack required fields (unusual for connector output)

So no extra configuration is needed for Elastic/Datadog beyond the connectors config file.
