"""
FastAPI service wrapper for LogMiner-QA.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .ci import generate_summary
from .config import Settings
from .ingestion import load_connectors
from .pipeline import LogMinerPipeline, AnalysisArtifact

_CLUSTER_COLORS = ["#EF4444", "#F97316", "#3B82F6", "#A855F7", "#10B981", "#06B6D4", "#FACC15", "#EC4899"]


def _format_clusters(cluster_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert raw ClusterSummary dict (index lists + top_terms) into display-ready rows."""
    clusters = cluster_summary.get("clusters", {})
    top_terms = cluster_summary.get("top_terms", {})
    result = []
    for cluster_id, indices in clusters.items():
        terms: List[str] = top_terms.get(cluster_id, [])
        count = len(indices) if isinstance(indices, list) else 0
        result.append({
            "id": int(cluster_id),
            "label": " / ".join(terms[:3]) if terms else f"Cluster {cluster_id}",
            "count": count,
            "top_terms": terms,
            "severity": "high" if count > 200 else "medium" if count > 80 else "low" if count > 20 else "none",
            "color": _CLUSTER_COLORS[int(cluster_id) % len(_CLUSTER_COLORS)],
        })
    return sorted(result, key=lambda x: x["count"], reverse=True)


def _format_anomalies(anomaly_summary: Dict[str, Any], sanitized_logs: List[Any]) -> List[Dict[str, Any]]:
    """Convert raw AnomalySummary dict into display-ready rows using sanitized log context."""
    scores: List[float] = anomaly_summary.get("scores", [])
    top_indices: List[int] = anomaly_summary.get("top_indices", [])
    result = []
    for i, idx in enumerate(top_indices[:10]):
        score = float(scores[idx]) if idx < len(scores) else 0.0
        record = sanitized_logs[idx] if idx < len(sanitized_logs) else {}
        if isinstance(record, dict):
            message = record.get("message") or record.get("msg") or record.get("event") or f"Record #{idx}"
            session = record.get("session_id") or record.get("journey_id") or record.get("user_id") or f"idx_{idx}"
            timestamp = str(record.get("timestamp", ""))
        else:
            message = str(record)[:80]
            session = f"idx_{idx}"
            timestamp = ""
        result.append({
            "id": i + 1,
            "score": round(score, 3),
            "session": str(session)[:20],
            "description": str(message)[:90],
            "severity": "high" if score > 0.8 else "medium",
            "timestamp": timestamp,
        })
    return result


def _format_journeys(journey_insights: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert raw JourneyInsights dict into display-ready rows."""
    anomalous_seqs: List[Dict[str, Any]] = journey_insights.get("anomalous_sequences", [])
    next_event_probs: Dict[str, Dict[str, float]] = journey_insights.get("next_event_probabilities", {})
    anomalous_ids = {s["journey_id"] for s in anomalous_seqs}
    result = []
    for i, (journey_id, probs) in enumerate(list(next_event_probs.items())[:10]):
        sorted_events = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        path = [event for event, _ in sorted_events[:6]]
        top_conf = float(sorted_events[0][1]) if sorted_events else 0.0
        anom_sq = next((s for s in anomalous_seqs if s["journey_id"] == journey_id), None)
        is_anom = journey_id in anomalous_ids
        result.append({
            "id": i,
            "path": path,
            "anomalous": is_anom,
            "confidence": round(top_conf, 3),
            "label": (
                f"Predicted: {anom_sq['predicted_next']} | Actual: {anom_sq['actual_last']}"
                if is_anom and anom_sq
                else f"Session: {journey_id[:24]}"
            ),
        })
    return result


class AnalyzeRequest(BaseModel):
    records: Optional[List[Any]] = Field(
        default=None, description="Inline log records (JSON/strings) uploaded from the client."
    )
    connectors: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None, description="Connector config: { 'elk': { endpoint, index, auth }, 'datadog': { api_key, app_key, query } }"
    )
    log_level: Optional[str] = Field(default="INFO")


def create_app() -> FastAPI:
    app = FastAPI(title="LogMiner-QA API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root() -> Dict[str, str]:
        return {
            "service": "LogMiner-QA API",
            "status": "ok",
            "docs": "/docs",
            "health": "/health",
            "analyze": "POST /analyze",
        }

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/analyze")
    async def analyze(request: AnalyzeRequest) -> Dict[str, Any]:
        if not request.records and not request.connectors:
            raise HTTPException(status_code=400, detail="Provide 'records' or 'connectors'.")

        settings = Settings()
        sources: List[Iterable[Any]] = []

        if request.records:
            sources.append(_ensure_message_field(request.records))

        if request.connectors:
            connectors = load_connectors(request.connectors)
            settings.connectors = {
                connector.config.name: dict(connector.config.options) for connector in connectors
            }
            sources.append(_chain_connectors(connectors))

        pipeline = LogMinerPipeline(settings=settings)
        artifact = pipeline.process_logs(_chain_iterables(sources))
        summary = generate_summary(artifact).to_dict()

        return {
            "summary": summary,
            "clusters": _format_clusters(artifact.cluster_summary),
            "anomalies": _format_anomalies(artifact.anomaly_summary, artifact.sanitized_logs),
            "journeys": _format_journeys(artifact.journey_insights),
            "compliance_findings": artifact.compliance_findings,
            "fraud_findings": artifact.fraud_findings,
            "tests": artifact.test_cases,
        }

    return app


def _ensure_message_field(records: List[Any]) -> Iterable[Any]:
    """
    Ensure each record has a message-like field so validation passes.
    Dashboard CSV uploads often have 'event' but no 'message'; copy event -> message when needed.
    """
    _message_keys = ("message", "msg", "text", "log", "body", "content", "description", "summary")
    _fallback_keys = ("event", "event_type", "action")
    for r in records:
        if isinstance(r, dict):
            has_message = any(r.get(k) for k in _message_keys if isinstance(r.get(k), str) and (r.get(k) or "").strip())
            if not has_message:
                for k in _fallback_keys:
                    v = r.get(k)
                    if isinstance(v, str) and v.strip():
                        r = {**r, "message": v}
                        break
            yield r
        else:
            yield r


def _chain_connectors(connectors: Iterable[Any]) -> Iterable[Any]:
    for connector in connectors:
        yield from connector.fetch()


def _chain_iterables(sources: Iterable[Iterable[Any]]) -> Iterable[Any]:
    for source in sources:
        yield from source

