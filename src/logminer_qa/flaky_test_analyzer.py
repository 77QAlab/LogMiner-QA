"""
Flaky test analysis engine for LogMiner-QA.

Analyses test execution results across multiple CI/CD runs to distinguish
between flaky tests (intermittent, non-deterministic failures) and true
failures (consistent failures indicating actual bugs).

Supported input formats:
- JUnit XML reports
- JSON test result files (custom schema)
- Plain-text log lines with pass/fail patterns
"""
from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns used to extract test outcomes from plain-text CI logs
# ---------------------------------------------------------------------------
# Matches lines like: "PASS  tests/test_auth.py::test_login (0.32s)"
#                  or: "FAIL  tests/test_auth.py::test_login (AssertionError)"
#                  or: "SKIP  tests/test_auth.py::test_login"
_TEXT_RESULT_RE = re.compile(
    r"(?P<status>PASS(?:ED)?|FAIL(?:ED)?|ERROR|SKIP(?:PED)?)"
    r"\s+"
    r"(?P<test_name>\S+)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class TestExecution:
    """A single execution record for one test in one run."""
    test_name: str
    status: str          # "passed", "failed", "error", "skipped"
    run_id: str = ""
    duration_seconds: float = 0.0
    error_message: str = ""
    timestamp: str = ""


@dataclass(slots=True)
class FlakyTestResult:
    """Analysis result for a single test across multiple runs."""
    test_name: str
    total_runs: int
    pass_count: int
    fail_count: int
    error_count: int
    skip_count: int
    flakiness_score: float       # 0.0 = deterministic, 1.0 = maximally flaky
    classification: str          # "flaky", "true_failure", "stable", "always_skipped"
    fail_run_ids: List[str] = field(default_factory=list)
    pass_run_ids: List[str] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "total_runs": self.total_runs,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "error_count": self.error_count,
            "skip_count": self.skip_count,
            "flakiness_score": round(self.flakiness_score, 4),
            "classification": self.classification,
            "fail_run_ids": self.fail_run_ids,
            "pass_run_ids": self.pass_run_ids,
            "error_messages": self.error_messages[:5],
        }


@dataclass(slots=True)
class FlakyTestSummary:
    """Aggregated summary of flaky test analysis."""
    total_tests_analyzed: int
    flaky_tests: List[FlakyTestResult]
    true_failures: List[FlakyTestResult]
    stable_tests: int
    always_skipped: int
    overall_flakiness_rate: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "total_tests_analyzed": self.total_tests_analyzed,
            "flaky_test_count": len(self.flaky_tests),
            "true_failure_count": len(self.true_failures),
            "stable_test_count": self.stable_tests,
            "always_skipped_count": self.always_skipped,
            "overall_flakiness_rate": round(self.overall_flakiness_rate, 4),
            "flaky_tests": [t.as_dict() for t in self.flaky_tests],
            "true_failures": [t.as_dict() for t in self.true_failures],
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class FlakyTestConfig:
    """Configuration for flaky test analysis."""
    flakiness_threshold: float = 0.0
    min_runs_required: int = 2
    true_failure_threshold: float = 1.0


# ---------------------------------------------------------------------------
# Parsers — each returns List[TestExecution]
# ---------------------------------------------------------------------------

def parse_junit_xml(path: Path, run_id: str = "") -> List[TestExecution]:
    """Parse a JUnit XML report into test execution records."""
    executions: List[TestExecution] = []
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        LOGGER.warning("Failed to parse JUnit XML %s: %s", path, exc)
        return executions

    root = tree.getroot()
    # Handle both <testsuites><testsuite>... and standalone <testsuite>
    suites = root.findall(".//testsuite") if root.tag == "testsuites" else [root]
    if root.tag == "testsuite":
        suites = [root]

    for suite in suites:
        suite_name = suite.get("name", "")
        for tc in suite.findall("testcase"):
            name = tc.get("name", "unknown")
            classname = tc.get("classname", "")
            full_name = f"{classname}::{name}" if classname else name
            duration = float(tc.get("time", "0") or "0")

            failure = tc.find("failure")
            error = tc.find("error")
            skipped = tc.find("skipped")

            if failure is not None:
                status = "failed"
                msg = failure.get("message", failure.text or "")
            elif error is not None:
                status = "error"
                msg = error.get("message", error.text or "")
            elif skipped is not None:
                status = "skipped"
                msg = skipped.get("message", "")
            else:
                status = "passed"
                msg = ""

            executions.append(TestExecution(
                test_name=full_name,
                status=status,
                run_id=run_id or path.stem,
                duration_seconds=duration,
                error_message=msg[:500],
            ))
    return executions


def parse_json_results(path: Path, run_id: str = "") -> List[TestExecution]:
    """
    Parse a JSON test result file.

    Expected schema (flexible):
    {
        "test_results": [
            {"name": "test_foo", "status": "passed", "duration": 1.2, "message": ""},
            ...
        ]
    }
    or a plain list of test result objects.
    """
    executions: List[TestExecution] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        LOGGER.warning("Failed to parse JSON results %s: %s", path, exc)
        return executions

    records = data if isinstance(data, list) else data.get("test_results", data.get("tests", []))
    if not isinstance(records, list):
        LOGGER.warning("Unexpected JSON structure in %s", path)
        return executions

    for record in records:
        if not isinstance(record, dict):
            continue
        name = record.get("name") or record.get("test_name") or record.get("testName", "unknown")
        raw_status = str(record.get("status") or record.get("result", "unknown")).lower()
        status = _normalize_status(raw_status)
        executions.append(TestExecution(
            test_name=name,
            status=status,
            run_id=run_id or path.stem,
            duration_seconds=float(record.get("duration", 0) or 0),
            error_message=str(record.get("message") or record.get("error_message", ""))[:500],
            timestamp=str(record.get("timestamp", "")),
        ))
    return executions


def parse_text_log(path: Path, run_id: str = "") -> List[TestExecution]:
    """Extract test results from plain-text CI log output."""
    executions: List[TestExecution] = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        LOGGER.warning("Failed to read log file %s: %s", path, exc)
        return executions

    for match in _TEXT_RESULT_RE.finditer(content):
        raw_status = match.group("status").lower()
        status = _normalize_status(raw_status)
        executions.append(TestExecution(
            test_name=match.group("test_name"),
            status=status,
            run_id=run_id or path.stem,
        ))
    return executions


def _normalize_status(raw: str) -> str:
    raw = raw.strip().lower()
    if raw in ("pass", "passed", "ok", "success"):
        return "passed"
    if raw in ("fail", "failed", "failure"):
        return "failed"
    if raw in ("error", "errored"):
        return "error"
    if raw in ("skip", "skipped", "ignored", "pending"):
        return "skipped"
    return "failed"


def _auto_detect_and_parse(path: Path, run_id: str = "") -> List[TestExecution]:
    """Auto-detect file format and parse accordingly."""
    suffix = path.suffix.lower()
    if suffix == ".xml":
        return parse_junit_xml(path, run_id)
    if suffix == ".json":
        return parse_json_results(path, run_id)
    return parse_text_log(path, run_id)


# ---------------------------------------------------------------------------
# Core analyser
# ---------------------------------------------------------------------------

class FlakyTestAnalyzer:
    """
    Analyses test execution data across multiple runs to classify tests as
    flaky, true failures, or stable.

    Flakiness score formula:
        score = 2 * min(pass_rate, fail_rate)
    where pass_rate = passes / effective_runs and fail_rate = failures / effective_runs.
    This yields 0.0 for deterministic tests and 1.0 for 50/50 pass/fail.
    """

    def __init__(self, config: Optional[FlakyTestConfig] = None) -> None:
        self.config = config or FlakyTestConfig()

    def load_results_from_directory(self, directory: Path) -> List[TestExecution]:
        """
        Scan a directory for test result files and parse them all.

        Directory layout can be flat or organised by run:
            results_dir/
              run_001/report.xml
              run_002/report.xml
            or
            results_dir/
              report_001.xml
              report_002.json
        """
        all_executions: List[TestExecution] = []
        if not directory.is_dir():
            LOGGER.warning("Test results directory does not exist: %s", directory)
            return all_executions

        # Check for sub-directories (each = one run)
        subdirs = sorted([d for d in directory.iterdir() if d.is_dir()])
        if subdirs:
            for subdir in subdirs:
                run_id = subdir.name
                for file_path in sorted(subdir.iterdir()):
                    if file_path.is_file() and file_path.suffix.lower() in (".xml", ".json", ".log", ".txt"):
                        all_executions.extend(_auto_detect_and_parse(file_path, run_id))
        else:
            # Flat directory: infer run_id from filename
            for file_path in sorted(directory.iterdir()):
                if file_path.is_file() and file_path.suffix.lower() in (".xml", ".json", ".log", ".txt"):
                    all_executions.extend(_auto_detect_and_parse(file_path))

        LOGGER.info("Loaded %d test executions from %s", len(all_executions), directory)
        return all_executions

    def analyze(self, executions: Sequence[TestExecution]) -> FlakyTestSummary:
        """Analyse a collection of test executions and classify each test."""
        if not executions:
            return FlakyTestSummary(
                total_tests_analyzed=0,
                flaky_tests=[],
                true_failures=[],
                stable_tests=0,
                always_skipped=0,
                overall_flakiness_rate=0.0,
            )

        # Group by test name
        grouped: Dict[str, List[TestExecution]] = defaultdict(list)
        for ex in executions:
            grouped[ex.test_name].append(ex)

        results: List[FlakyTestResult] = []
        for test_name, execs in grouped.items():
            result = self._classify_test(test_name, execs)
            results.append(result)

        flaky = sorted(
            [r for r in results if r.classification == "flaky"],
            key=lambda r: r.flakiness_score,
            reverse=True,
        )
        true_failures = [r for r in results if r.classification == "true_failure"]
        stable = sum(1 for r in results if r.classification == "stable")
        always_skipped = sum(1 for r in results if r.classification == "always_skipped")

        total = len(results)
        flakiness_rate = len(flaky) / total if total > 0 else 0.0

        run_ids = {ex.run_id for ex in executions if ex.run_id}
        return FlakyTestSummary(
            total_tests_analyzed=total,
            flaky_tests=flaky,
            true_failures=true_failures,
            stable_tests=stable,
            always_skipped=always_skipped,
            overall_flakiness_rate=flakiness_rate,
            metadata={
                "total_executions": len(executions),
                "unique_runs": len(run_ids),
                "config": {
                    "flakiness_threshold": self.config.flakiness_threshold,
                    "min_runs_required": self.config.min_runs_required,
                    "true_failure_threshold": self.config.true_failure_threshold,
                },
            },
        )

    def generate_tests(self, summary: FlakyTestSummary) -> List[str]:
        """Generate Gherkin scenarios for flaky and failing tests."""
        scenarios: List[str] = []
        for test in summary.flaky_tests:
            scenario = (
                f"Feature: Flaky test {test.test_name}\n"
                f"  Scenario: Stabilise flaky test {test.test_name}\n"
                f"  Given the test \"{test.test_name}\" has a flakiness score of {test.flakiness_score:.2f}\n"
                f"  And it passed {test.pass_count}/{test.total_runs} runs and failed {test.fail_count}/{test.total_runs} runs\n"
                f"  When the test is executed in isolation with deterministic inputs\n"
                f"  Then it should produce a consistent result"
            )
            scenarios.append(scenario)

        for test in summary.true_failures:
            error_hint = test.error_messages[0][:120] if test.error_messages else "unknown error"
            scenario = (
                f"Feature: True failure {test.test_name}\n"
                f"  Scenario: Fix consistently failing test {test.test_name}\n"
                f"  Given the test \"{test.test_name}\" fails in {test.fail_count}/{test.total_runs} runs\n"
                f"  And the most recent error is \"{error_hint}\"\n"
                f"  When the underlying bug is fixed\n"
                f"  Then the test should pass consistently"
            )
            scenarios.append(scenario)

        return scenarios

    def _classify_test(self, test_name: str, execs: List[TestExecution]) -> FlakyTestResult:
        """Classify a single test based on its execution history."""
        pass_count = sum(1 for e in execs if e.status == "passed")
        fail_count = sum(1 for e in execs if e.status == "failed")
        error_count = sum(1 for e in execs if e.status == "error")
        skip_count = sum(1 for e in execs if e.status == "skipped")
        total_runs = len(execs)

        fail_run_ids = list({e.run_id for e in execs if e.status in ("failed", "error") and e.run_id})
        pass_run_ids = list({e.run_id for e in execs if e.status == "passed" and e.run_id})
        error_messages = list({e.error_message for e in execs if e.error_message})

        # Effective runs = runs that were not skipped
        effective_runs = pass_count + fail_count + error_count
        combined_fails = fail_count + error_count

        if effective_runs == 0:
            classification = "always_skipped"
            flakiness_score = 0.0
        elif effective_runs < self.config.min_runs_required:
            # Not enough data — classify based on what we have but flag low confidence
            if combined_fails == effective_runs:
                classification = "true_failure"
            elif combined_fails == 0:
                classification = "stable"
            else:
                classification = "flaky"
            fail_rate = combined_fails / effective_runs
            pass_rate = pass_count / effective_runs
            flakiness_score = 2 * min(pass_rate, fail_rate)
        else:
            fail_rate = combined_fails / effective_runs
            pass_rate = pass_count / effective_runs
            flakiness_score = 2 * min(pass_rate, fail_rate)

            if fail_rate >= self.config.true_failure_threshold:
                classification = "true_failure"
            elif flakiness_score > self.config.flakiness_threshold and combined_fails > 0 and pass_count > 0:
                classification = "flaky"
            else:
                classification = "stable"

        return FlakyTestResult(
            test_name=test_name,
            total_runs=total_runs,
            pass_count=pass_count,
            fail_count=fail_count,
            error_count=error_count,
            skip_count=skip_count,
            flakiness_score=flakiness_score,
            classification=classification,
            fail_run_ids=fail_run_ids,
            pass_run_ids=pass_run_ids,
            error_messages=error_messages,
        )
