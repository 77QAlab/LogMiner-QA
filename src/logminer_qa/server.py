"""
FastAPI service wrapper for LogMiner-QA.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .ci import generate_summary
from .config import Settings
from .flaky_test_analyzer import TestExecution
from .ingestion import load_connectors
from .pipeline import LogMinerPipeline


class AnalyzeRequest(BaseModel):
    records: Optional[List[Any]] = Field(
        default=None, description="Inline log records (JSON/strings) to analyse."
    )
    connectors: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None, description="Connector configuration (same schema as CLI JSON)."
    )
    log_level: Optional[str] = Field(default="INFO")


class TestExecutionRecord(BaseModel):
    test_name: str
    status: str
    run_id: str = ""
    duration_seconds: float = 0.0
    error_message: str = ""
    timestamp: str = ""


class AnalyzeTestsRequest(BaseModel):
    test_results: List[TestExecutionRecord] = Field(
        description="List of test execution records across multiple runs."
    )


def create_app() -> FastAPI:
    app = FastAPI(title="LogMiner-QA API", version="0.1.0")

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
            sources.append(request.records)

        if request.connectors:
            connectors = load_connectors(request.connectors)
            settings.connectors = {
                connector.config.name: dict(connector.config.options) for connector in connectors
            }
            sources.append(_chain_connectors(connectors))

        pipeline = LogMinerPipeline(settings=settings)
        artifact = pipeline.process_logs(_chain_iterables(sources))
        summary = generate_summary(artifact).to_dict()
        report = {
            "frequency_report": artifact.frequency_report,
            "cluster_summary": artifact.cluster_summary,
            "anomaly_summary": artifact.anomaly_summary,
            "journey_insights": artifact.journey_insights,
            "compliance_findings": artifact.compliance_findings,
            "fraud_findings": artifact.fraud_findings,
        }
        sanitized_preview = artifact.sanitized_logs[:25]
        return {
            "summary": summary,
            "report": report,
            "tests": artifact.test_cases,
            "sanitized_preview": sanitized_preview,
        }

    @app.post("/analyze-tests")
    async def analyze_tests(request: AnalyzeTestsRequest) -> Dict[str, Any]:
        if not request.test_results:
            raise HTTPException(status_code=400, detail="Provide at least one test result.")

        executions = [
            TestExecution(
                test_name=r.test_name,
                status=r.status,
                run_id=r.run_id,
                duration_seconds=r.duration_seconds,
                error_message=r.error_message,
                timestamp=r.timestamp,
            )
            for r in request.test_results
        ]

        settings = Settings()
        pipeline = LogMinerPipeline(settings=settings)
        summary = pipeline.analyze_test_results(executions=executions)
        return {
            "flaky_test_summary": summary.as_dict(),
            "test_scenarios": pipeline.flaky_analyzer.generate_tests(summary),
        }

    return app


def _chain_connectors(connectors: Iterable[Any]) -> Iterable[Any]:
    for connector in connectors:
        yield from connector.fetch()


def _chain_iterables(sources: Iterable[Iterable[Any]]) -> Iterable[Any]:
    for source in sources:
        yield from source

