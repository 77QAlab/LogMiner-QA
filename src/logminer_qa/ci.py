"""
Utilities for producing CI/CD friendly summaries of LogMiner-QA outputs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


@dataclass(slots=True)
class CISummary:
    total_records: int
    high_severity_findings: int
    anomalies_detected: int
    compliance_findings: List[Dict[str, Any]]
    fraud_findings: List[Dict[str, Any]]
    top_clusters: Dict[str, Any]
    flaky_test_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "total_records": self.total_records,
            "high_severity_findings": self.high_severity_findings,
            "anomalies_detected": self.anomalies_detected,
            "compliance_findings": self.compliance_findings,
            "fraud_findings": self.fraud_findings,
            "top_clusters": self.top_clusters,
        }
        if self.flaky_test_summary:
            result["flaky_test_summary"] = self.flaky_test_summary
        return result


def generate_summary(artifact: Any = None, flaky_summary: Any = None) -> CISummary:
    total_records = 0
    high_severity = 0
    anomalies_detected = 0
    compliance: List[Dict[str, Any]] = []
    fraud: List[Dict[str, Any]] = []
    top_clusters: Dict[str, Any] = {}

    if artifact is not None:
        compliance = artifact.compliance_findings if hasattr(artifact, "compliance_findings") else []
        fraud = artifact.fraud_findings if hasattr(artifact, "fraud_findings") else []
        parsed_records = getattr(artifact, "parsed_records", [])
        anomalies_detected = sum(1 for record in parsed_records if record.get("is_anomaly"))
        high_severity = sum(
            1
            for finding in compliance
            if finding.get("severity", "").lower() in {"critical", "high"}
        ) + sum(
            1
            for finding in fraud
            if finding.get("severity", "").lower() in {"critical", "high"}
        )
        top_clusters = _summarise_clusters(artifact.cluster_summary)
        total_records = len(artifact.sanitized_logs)

    flaky_dict: Dict[str, Any] = {}
    if flaky_summary is not None:
        flaky_dict = flaky_summary.as_dict() if hasattr(flaky_summary, "as_dict") else flaky_summary

    return CISummary(
        total_records=total_records,
        high_severity_findings=high_severity,
        anomalies_detected=anomalies_detected,
        compliance_findings=compliance,
        fraud_findings=fraud,
        top_clusters=top_clusters,
        flaky_test_summary=flaky_dict,
    )


def write_summary(summary: CISummary, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(summary.to_dict(), handle, indent=2)


def _summarise_clusters(cluster_summary: Mapping[str, Any]) -> Dict[str, Any]:
    clusters = cluster_summary.get("clusters", {}) if isinstance(cluster_summary, Mapping) else {}
    top_terms = cluster_summary.get("top_terms", {})
    largest_clusters = sorted(clusters.items(), key=lambda item: len(item[1]), reverse=True)[:3]
    return {
        "largest_clusters": [
            {"cluster_id": cluster_id, "count": len(indices), "top_terms": top_terms.get(cluster_id, [])}
            for cluster_id, indices in largest_clusters
        ],
        "total_clusters": len(clusters),
    }

