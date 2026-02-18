"""
Command line interface for the LogMiner-QA tool.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import csv
from itertools import chain
from typing import Iterable, List, Any

from .config import Settings
from .ci import generate_summary, write_summary
from .ingestion import load_connectors_from_path
from .log_format import LogFormatConfig
from .pipeline import LogMinerPipeline

LOGGER = logging.getLogger("logminer_qa.cli")


def _convert_numpy_types(obj: Any) -> Any:
    """Convert NumPy types to native Python types for JSON serialization."""
    try:
        import numpy as np
    except ImportError:
        # NumPy not available, return as-is
        return obj
    
    # Handle NumPy integer types
    if isinstance(obj, (np.integer, np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64)):
        return int(obj)
    # Handle NumPy float types
    if isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
        return float(obj)
    # Handle NumPy bool
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {key: _convert_numpy_types(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_numpy_types(item) for item in obj]
    return obj


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LogMiner-QA: Turn production logs into test coverage."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Path to newline-delimited JSON log file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Optional path to write sanitized logs.",
    )
    parser.add_argument(
        "--report",
        "-r",
        type=Path,
        help="Optional path to write privacy-preserving frequency report.",
    )
    parser.add_argument(
        "--tests",
        "-t",
        type=Path,
        help="Optional path to write generated Gherkin scenarios.",
    )
    parser.add_argument(
        "--connectors-config",
        type=Path,
        help="Optional JSON file describing external ingestion connectors.",
    )
    parser.add_argument(
        "--ci-summary",
        type=Path,
        help="Optional path to write a compact CI summary JSON.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level (DEBUG, INFO, WARNING, ERROR).",
    )
    parser.add_argument(
        "--timestamp-field",
        metavar="KEY",
        help="Custom JSON key for timestamp (e.g. event_time). See docs/LOG_FORMAT.md.",
    )
    parser.add_argument(
        "--message-field",
        metavar="KEY",
        help="Custom JSON key for message (e.g. log_line). See docs/LOG_FORMAT.md.",
    )
    parser.add_argument(
        "--severity-field",
        metavar="KEY",
        help="Custom JSON key for severity/level. See docs/LOG_FORMAT.md.",
    )
    return parser.parse_args(argv)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


def load_records(path: Path) -> Iterable[object]:
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        yield from _load_json_lines(path)
    elif suffix == ".csv":
        yield from _load_csv(path)
    elif suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, list):
                yield from data
            else:
                yield data
    else:
        LOGGER.warning("Treating %s as plain text; JSON/CSV parsing skipped.", path)
        yield from _load_plain_text(path)


def _load_json_lines(path: Path) -> Iterable[object]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                yield line


def _load_csv(path: Path) -> Iterable[object]:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            LOGGER.warning("CSV file %s has no header; rows emitted as positional dicts.", path)
        for row in reader:
            if row is None:
                continue
            cleaned = {key or f"column_{idx}": value for idx, (key, value) in enumerate(row.items())}
            yield cleaned


def _load_plain_text(path: Path) -> Iterable[object]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield line


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level)

    sources: List[Iterable[object]] = []
    if args.input:
        LOGGER.info("Loading logs from %s", args.input)
        sources.append(load_records(args.input))

    settings = Settings()
    if args.timestamp_field or args.message_field or args.severity_field:
        settings.log_format = LogFormatConfig(
            timestamp_field=args.timestamp_field,
            message_field=args.message_field,
            severity_field=args.severity_field,
        )
    connectors = []
    if args.connectors_config:
        LOGGER.info("Loading connectors from %s", args.connectors_config)
        connectors = load_connectors_from_path(str(args.connectors_config))
        settings.connectors = {
            connector.config.name: dict(connector.config.options) for connector in connectors
        }
        sources.append(chain.from_iterable(connector.fetch() for connector in connectors))

    if not sources:
        LOGGER.error("No input logs or connectors provided.")
        return 1

    pipeline = LogMinerPipeline(settings)
    combined = chain.from_iterable(sources)
    
    # Process logs in streaming fashion
    artifact = pipeline.process_logs(combined)

    if args.output:
        LOGGER.info("Writing sanitized logs to %s", args.output)
        with args.output.open("w", encoding="utf-8") as handle:
            for record in artifact.sanitized_logs:
                cleaned = _convert_numpy_types(record)
                handle.write(json.dumps(cleaned))
                handle.write("\n")

    if args.report:
        LOGGER.info("Writing frequency and clustering report to %s", args.report)
        report_payload = {
            "frequency_report": artifact.frequency_report,
            "cluster_summary": artifact.cluster_summary,
            "anomaly_summary": artifact.anomaly_summary,
            "journey_insights": artifact.journey_insights,
            "compliance_findings": artifact.compliance_findings,
            "fraud_findings": artifact.fraud_findings,
        }
        cleaned_payload = _convert_numpy_types(report_payload)
        with args.report.open("w", encoding="utf-8") as handle:
            json.dump(cleaned_payload, handle, indent=2)

    if args.tests:
        LOGGER.info("Writing generated test cases to %s", args.tests)
        with args.tests.open("w", encoding="utf-8") as handle:
            handle.write("\n\n".join(artifact.test_cases))

    if args.ci_summary:
        LOGGER.info("Writing CI summary to %s", args.ci_summary)
        summary = generate_summary(artifact)
        write_summary(summary, args.ci_summary)

    LOGGER.info("Processed %d log records", len(artifact.sanitized_logs))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
