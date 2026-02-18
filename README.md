# LogMiner-QA

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

> **"Turn Production Wisdom into Test Coverage"** — Privacy-first log analysis and automated test generation for banking and enterprise workloads.

## Overview

LogMiner-QA ingests raw banking logs, scrubs sensitive customer data, and generates actionable test cases. The tool is composed of:

- **Intelligent Log Sanitizer**: Detects PII via pattern matching and optional spaCy NER, redacts sensitive data with stable tokens, and hashes identifiers for correlation without exposure.
- **Differential Privacy Layer**: Adds calibrated noise to aggregate metrics to prevent reconstruction of individual behaviour.
- **Analysis & Test Generation**: Reconstructs journeys, prioritises high-risk flows, and emits Gherkin scenarios for CI/CD pipelines.
- **On-Prem Deployment**: Designed for containerised, air-gapped environments where logs never leave the bank’s infrastructure.

## Features

- PII detection for emails, account numbers, phone numbers, IBANs, and more.
- Configurable hashing algorithm and token format with referential integrity.
- Laplace-mechanism aggregator for counts, histograms, and ratios.
- Multi-source ingestion via local JSON/CSV, Elasticsearch, and Datadog connectors.
- NLP enrichment with regex + spaCy, transformer embeddings, clustering, and Isolation Forest anomaly scoring.
- LSTM-based journey analysis surfacing anomalous customer flows.
- Compliance (PCI, GDPR, audit trail) and fraud (velocity, high-value, failed-login) test generation modules.
- CI/CD friendly summary generation and FastAPI microservice for on-prem orchestration.
- CLI workflow to process logs into sanitized outputs, privacy-preserving reports, and templated Gherkin tests.

## Quick Start

Get started in 5 minutes! See [Quick Start Guide](docs/QUICK_START.md) for detailed instructions.

```bash
# 1. Install dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Install package in editable mode (required for CLI)
pip install -e .

# 3. Set security secret (optional but recommended)
export LOGMINER_HASH_SECRET=$(openssl rand -hex 32)  # Linux/Mac
# Windows PowerShell: See docs/QUICK_START.md

# 4. Run analysis
python -m logminer_qa.cli \
  --input data/sample_logs.jsonl \
  --output sanitized.jsonl \
  --report report.json \
  --tests tests.feature
```

**Windows (PowerShell):** After activating the venv (`.\.venv\Scripts\Activate.ps1`), ensure you've run `pip install -e .` first. Then you can use `.\.venv\Scripts\python.exe -m logminer_qa.cli ...` or the one-step script: `.\run_sample.ps1` (runs the installation test, ensures package is installed, then runs the sample pipeline).

### CI mode

Emit a compact JSON summary for pipeline gates:

```bash
python -m logminer_qa.cli --input data/sample_logs.jsonl --ci-summary build/logminer-summary.json
```

Inspect `high_severity_findings` / `anomalies_detected` and fail the build if thresholds are exceeded.

### API Server

Run the analysis service in-process:

```bash
uvicorn logminer_qa.server:create_app --factory --host 0.0.0.0 --port 8080
```

POST `{"records": [...]}` to `/analyze` to receive sanitized previews, risk summaries, and generated tests.

## Project Structure

- src/logminer_qa/sanitizer.py — PII detection, tokenisation, and hashing.
- src/logminer_qa/privacy.py — Differential privacy utilities.
- src/logminer_qa/pipeline.py — Orchestrates sanitization, aggregation, and test generation.
- src/logminer_qa/cli.py — End-user entry point.
- Dockerfile / helm/ (optional) — Templates for on-prem deployment.

## Configuration

Refer to src/logminer_qa/config.py for tunable parameters:

- SanitizerConfig toggles NER, hashing algorithm, token store path, and entity types.
- PrivacyConfig defines epsilon/delta budgets and toggles DP.
- **Log format**: Records must have at least a timestamp-like and message-like field. Built-in aliases support `time`/`timestamp`, `msg`/`message`, etc.; custom mapping is available via CLI (`--timestamp-field`, `--message-field`, `--severity-field`) or `Settings.log_format`. See [Log format and field mapping](docs/LOG_FORMAT.md) (includes [data cleaning expectations](docs/LOG_FORMAT.md#data-cleaning-expectations): encoding, size limits, PII handling).

Environment variables:

- LOGMINER_HASH_SECRET — Secret key for deterministic hashing (default fallback provided with warning).

## Differential Privacy Guarantees

The Laplace mechanism ensures ε-differential privacy for count-based metrics. Configure ε per compliance needs; smaller ε yields stronger privacy at the cost of accuracy.

## Extensibility

- Plug in custom PII detection patterns or new NER models.
- Extend LogMinerPipeline._classify_record to reflect domain-specific risk classification.
- Replace _generate_tests with connectors to Cucumber, Pytest-BDD, or internal tooling.

## Deployment Notes

- Package the tool as a container; run sanitizer and analysis components in the same secure cluster.
- Disable outbound networking, mount model/token stores to persistent volumes, and integrate with the bank’s secrets manager.
- Export Prometheus metrics from the pipeline while respecting privacy budgets.

## Early Adopters

We're looking for early adopters to help shape LogMiner-QA! 

- 📖 Read the [Early Adopter Guide](docs/EARLY_ADOPTER_GUIDE.md)
- 🚀 Try it out with our [Quick Start](docs/QUICK_START.md)
- 💬 Share feedback via [GitHub Issues](https://github.com/77QAlab/LogMiner-QA/issues)
- 🤝 Contribute following our [Contributing Guide](CONTRIBUTING.md)

## Documentation

- [User guide](docs/USER_GUIDE.md) - How to run on-prem (file, Elastic/Datadog), field mapping, test failures, outputs
- [Handoff guide](docs/HANDOFF.md) - Example run, sample outputs, and follow-up questions for early adopters
- [Connectors](docs/CONNECTORS.md) - Elasticsearch and Datadog config, options, export JSONL alternative
- [Environment Setup](docs/ENVIRONMENT_SETUP.md) - Step-by-step install (replicable)
- [Quick Start Guide](docs/QUICK_START.md) - Get running in 5 minutes
- [Log format and field mapping](docs/LOG_FORMAT.md) - Required fields, aliases, custom mapping, data cleaning expectations
- [Test failure ingestion](docs/TEST_FAILURE_INGESTION.md) - Ingest test run stack traces (error_message, browser, os, selector) as JSONL
- [Early Adopter Guide](docs/EARLY_ADOPTER_GUIDE.md) - For early users
- [Workflow Diagram](docs/WORKFLOW.md) - System architecture
- [Tech Stack](docs/TECH_STACK.md) - Complete technology reference
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Future Enhancements

- Expand connector catalog (Splunk, CloudWatch, Datadog streaming)
- Integrate model registry + fine-tuned fraud detection models
- Surface dashboard visualisations (Streamlit/React) and CI/CD automation hooks
- Enhanced test generation with prioritization and risk scoring
