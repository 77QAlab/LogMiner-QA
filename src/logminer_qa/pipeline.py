"""
High level orchestration for LogMiner-QA analysis.
"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence

from .anomaly import AnomalyDetector
from .clustering import EventClusterer
from .config import Settings
from .embeddings import EmbeddingService
from .ingestion import aggregate_logs
from .journey import JourneyAnalyzer
from .parsing import LogParser
from .privacy import DifferentialPrivacyAggregator
from .sanitizer import SanitizationLayer
from .compliance import BankingComplianceEngine, FraudDetectionEngine, ComplianceFinding, FraudFinding
from .flaky_test_analyzer import FlakyTestAnalyzer, FlakyTestSummary, TestExecution
from .validation import validate_record, validate_batch

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class AnalysisArtifact:
    sanitized_logs: List[Any]
    frequency_report: Dict[str, int]
    test_cases: List[str]
    parsed_records: List[Dict[str, Any]]
    cluster_summary: Dict[str, Any]
    anomaly_summary: Dict[str, Any]
    journey_insights: Dict[str, Any]
    compliance_findings: List[Dict[str, Any]]
    fraud_findings: List[Dict[str, Any]]
    flaky_test_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LogMinerPipeline:
    settings: Settings = field(default_factory=Settings)
    sanitizer: SanitizationLayer = field(default_factory=SanitizationLayer)
    privacy: DifferentialPrivacyAggregator = field(default_factory=DifferentialPrivacyAggregator)
    parser: LogParser = field(default_factory=LogParser)
    clusterer: EventClusterer = field(default_factory=EventClusterer)
    embeddings: EmbeddingService = field(default_factory=EmbeddingService)
    anomaly: AnomalyDetector = field(default_factory=AnomalyDetector)
    journeys: JourneyAnalyzer = field(default_factory=JourneyAnalyzer)
    compliance: BankingComplianceEngine = field(default_factory=BankingComplianceEngine)
    fraud: FraudDetectionEngine = field(default_factory=FraudDetectionEngine)
    flaky_analyzer: FlakyTestAnalyzer = field(default_factory=FlakyTestAnalyzer)

    def __post_init__(self) -> None:
        self.sanitizer.config = self.settings.sanitizer
        self.privacy.config = self.settings.privacy
        self.parser = LogParser(enable_nlp=self.settings.sanitizer.enable_ner)
        from .flaky_test_analyzer import FlakyTestConfig as _FTC
        self.flaky_analyzer = FlakyTestAnalyzer(config=_FTC(
            flakiness_threshold=self.settings.flaky_tests.flakiness_threshold,
            min_runs_required=self.settings.flaky_tests.min_runs_required,
            true_failure_threshold=self.settings.flaky_tests.true_failure_threshold,
        ))

    @staticmethod
    def _chunk_iterable(iterable: Iterable[Any], chunk_size: int) -> Iterable[List[Any]]:
        """Split an iterable into chunks for memory-efficient processing."""
        chunk: List[Any] = []
        for item in iterable:
            chunk.append(item)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    def process_logs(self, logs: Iterable[Any]) -> AnalysisArtifact:
        sanitized_records: List[Any] = []
        event_counter: Counter = Counter()
        journey_map: Dict[str, List[str]] = defaultdict(list)
        parsed_records: List[Dict[str, Any]] = []
        clustering_messages: List[str] = []
        
        chunk_size = self.settings.chunk_size if self.settings.enable_streaming else 100_000
        total_processed = 0
        invalid_count = 0

        # Process in chunks for memory efficiency
        for chunk in self._chunk_iterable(logs, chunk_size):
            if self.settings.validate_inputs:
                valid_chunk = []
                for record in chunk:
                    is_valid, error = validate_record(record)
                    if is_valid:
                        valid_chunk.append(record)
                    else:
                        invalid_count += 1
                        if error:
                            LOGGER.debug("Skipping invalid record: %s", error)
                chunk = valid_chunk
            
            # Process chunk
            for record in chunk:
                result = self.sanitizer.sanitize_record(record)
                sanitized = result.sanitized
                sanitized_records.append(sanitized)
                label = self._classify_record(sanitized)
                event_counter[label] += 1
                journey_id = self._extract_journey_id(sanitized)
                if journey_id:
                    journey_map[journey_id].append(label)
                parsed = self.parser.parse_record(sanitized).as_dict()
                parsed["event_label"] = label
                parsed_records.append(parsed)
                clustering_messages.append(parsed["message"])
                total_processed += 1
            
            # Log progress for large datasets
            if total_processed % 5000 == 0:
                LOGGER.info("Processed %d records...", total_processed)
        
        if invalid_count > 0:
            LOGGER.warning("Skipped %d invalid records", invalid_count)
        
        LOGGER.info("Completed processing %d valid records", total_processed)
        
        # Flush token store to ensure all tokens are persisted
        if hasattr(self.sanitizer, 'token_store') and hasattr(self.sanitizer.token_store, 'flush'):
            self.sanitizer.token_store.flush()

        cluster_summary = self.clusterer.cluster_messages(clustering_messages)
        labels = cluster_summary.labels
        embeddings = None
        if clustering_messages:
            try:
                embeddings = self.embeddings.embed_texts(clustering_messages)
            except RuntimeError as exc:
                LOGGER.warning("Embedding skipped: %s", exc)
                embeddings = None

        anomaly_summary = self.anomaly.score_embeddings(embeddings)
        scores = anomaly_summary.scores

        for idx, sanitized in enumerate(sanitized_records):
            cluster_id = labels[idx] if idx < len(labels) else -1
            parsed_records[idx]["cluster_id"] = cluster_id
            if embeddings is not None and embeddings.size:
                parsed_records[idx]["embedding"] = embeddings[idx].tolist()
            anomaly_score = scores[idx] if idx < len(scores) else 0.0
            parsed_records[idx]["anomaly_score"] = anomaly_score
            parsed_records[idx]["is_anomaly"] = anomaly_score >= anomaly_summary.threshold if scores else False
            analysis_payload = {
                "parsed": parsed_records[idx],
                "cluster_id": cluster_id,
                "anomaly_score": anomaly_score,
                "is_anomaly": parsed_records[idx]["is_anomaly"],
                "event_label": parsed_records[idx].get("event_label"),
            }
            if isinstance(sanitized, dict):
                sanitized.setdefault("analysis", {}).update(analysis_payload)
            else:
                sanitized_records[idx] = {"message": str(sanitized), "analysis": analysis_payload}

        self.journeys.fit(journey_map)
        journey_insights = self.journeys.analyze(journey_map)

        dict_records = [record for record in sanitized_records if isinstance(record, dict)]
        compliance_findings = self.compliance.evaluate(dict_records)
        fraud_findings = self.fraud.evaluate(dict_records, parsed_records)

        noisy_counts = self.privacy.aggregate_counts(dict(event_counter))
        tests = self._generate_tests(journey_map, compliance_findings, fraud_findings)
        return AnalysisArtifact(
            sanitized_logs=sanitized_records,
            frequency_report=noisy_counts,
            test_cases=tests,
            parsed_records=parsed_records,
            cluster_summary=cluster_summary.as_dict(),
            anomaly_summary=anomaly_summary.as_dict(),
            journey_insights=journey_insights.as_dict(),
            compliance_findings=[finding.as_dict() for finding in compliance_findings],
            fraud_findings=[finding.as_dict() for finding in fraud_findings],
        )

    def process_from_connectors(self, connectors: Iterable[Any]) -> AnalysisArtifact:
        """
        Convenience helper that runs the full pipeline on dynamically ingested logs.
        """
        return self.process_logs(aggregate_logs(connectors))

    def _classify_record(self, record: Any) -> str:
        """Classify a record into an event type, using actual event names when available."""
        if isinstance(record, dict):
            # Prefer explicit event field
            event_name = record.get("event")
            if isinstance(event_name, str) and event_name:
                # Normalize event name
                return event_name.lower().replace(" ", "_").replace("-", "_")
            
            # Check transaction_type
            trans_type = record.get("transaction_type")
            if isinstance(trans_type, str) and trans_type:
                return f"{trans_type.lower().replace(' ', '_')}_event"
            
            # Check for error indicators
            if "error" in record or record.get("level") == "ERROR" or record.get("severity") == "ERROR":
                return "error_event"
            
            # Check message content
            message = record.get("message")
            if isinstance(message, str):
                msg_lower = message.lower()
                if "error" in msg_lower or "exception" in msg_lower or "fail" in msg_lower:
                    return "error_event"
                if "login" in msg_lower or "authenticate" in msg_lower:
                    return "login_event"
                if "transaction" in msg_lower or "transfer" in msg_lower:
                    return "transaction_event"
            
            # Check for transaction-related fields
            if "transaction" in record or "transaction_id" in record:
                return "transaction_event"
        
        if isinstance(record, str):
            record_lower = record.lower()
            if "error" in record_lower:
                return "error_event"
            if "login" in record_lower:
                return "login_event"
            if "transaction" in record_lower:
                return "transaction_event"
        
        return "generic_event"

    def _extract_journey_id(self, record: Any) -> str:
        if isinstance(record, dict):
            for key in ("session_id", "journey_id", "hashed_fields"):
                value = record.get(key)
                if isinstance(value, str):
                    return value
                if key == "hashed_fields" and isinstance(value, dict) and value:
                    first_key = sorted(value.keys())[0]
                    hashed_value = value[first_key]
                    if isinstance(hashed_value, str):
                        return hashed_value
        return ""

    def _generate_tests(
        self,
        journeys: Dict[str, Sequence[str]],
        compliance_findings: Sequence[ComplianceFinding],
        fraud_findings: Sequence[FraudFinding],
    ) -> List[str]:
        scenarios: List[str] = []
        seen_signatures: set[tuple[str, ...]] = set()
        
        # Deduplicate journeys by normalizing event sequences
        for journey_id, events in journeys.items():
            if not events:
                continue
            
            # Normalize: remove consecutive duplicates and create a signature
            normalized_events = self._deduplicate_events(events)
            journey_signature = tuple(normalized_events)
            
            # Only keep unique journey patterns
            if journey_signature not in seen_signatures:
                seen_signatures.add(journey_signature)
                scenario = self._render_gherkin(journey_id, normalized_events)
                if scenario:  # Only add non-empty scenarios
                    scenarios.append(scenario)
        
        # Add compliance and fraud tests (they should already be deduplicated)
        scenarios.extend(self.compliance.generate_tests(compliance_findings))
        scenarios.extend(self.fraud.generate_tests(fraud_findings))
        
        return scenarios

    def _deduplicate_events(self, events: Sequence[str]) -> List[str]:
        """Remove consecutive duplicate events while preserving order."""
        if not events:
            return []
        deduplicated: List[str] = [events[0]]
        for event in events[1:]:
            if event != deduplicated[-1]:
                deduplicated.append(event)
        return deduplicated

    def analyze_test_results(
        self,
        test_results_dir: Any = None,
        executions: Sequence[TestExecution] | None = None,
    ) -> FlakyTestSummary:
        """
        Run flaky test analysis on test result files or pre-parsed executions.

        Args:
            test_results_dir: Path to a directory containing test result files
                              (JUnit XML, JSON, or plain-text logs).
            executions: Pre-parsed list of TestExecution objects.

        Returns:
            FlakyTestSummary with classified tests.
        """
        from pathlib import Path
        all_executions: List[TestExecution] = []
        if test_results_dir is not None:
            all_executions.extend(
                self.flaky_analyzer.load_results_from_directory(Path(test_results_dir))
            )
        if executions:
            all_executions.extend(executions)
        return self.flaky_analyzer.analyze(all_executions)

    def _render_gherkin(self, journey_id: str, events: Sequence[str]) -> str:
        # Events are already deduplicated, just render them
        if not events:
            return ""
        
        # Create steps from unique events
        steps = [f"When the system observes {event}" for event in events]
        steps_text = "\n  ".join(steps)
        
        # Truncate long journey IDs for readability
        short_id = journey_id[:32] if len(journey_id) > 32 else journey_id
        
        template = (
            f"Feature: Journey {short_id}\n"
            f"  Scenario: Validate journey {short_id}\n"
            f"  Given a sanitized transaction journey\n"
            f"  {steps_text}\n"
            f"  Then the compliance checks pass"
        )
        return template
