"""
Normalize test-failure / stack-trace records into canonical log records (message + timestamp).

Allows ingestion of test run output (error_message, browser, os, selector, screenshot_path)
so the rest of the pipeline can process them like normal logs.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .log_format import has_required_log_fields

# Keys that suggest this dict is a test-failure/stack-trace entry rather than a normal log.
_TEST_FAILURE_KEYS = frozenset({
    "error_message",
    "log_message",
    "selector",
    "screenshot_path",
    "hook_error",
    "browser",
    "os",
    "operating_system",
})

# Regex to extract timestamp from paths like ".../2026-02-12-18-56-39/..." or "...2026-02-12_11-02-31..."
_PATH_TIMESTAMP_PATTERN = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})[-_](\d{2})-(\d{2})-(\d{2})"
)


def _has_test_failure_keys(record: Dict[str, Any]) -> bool:
    """True if record has at least one key that indicates test-failure shape."""
    return bool(_TEST_FAILURE_KEYS & set(record.keys()))


def is_test_failure_record(record: Any) -> bool:
    """
    True if record is a dict that looks like a test failure entry and lacks
    required log fields (timestamp + message), so it should be normalized.
    """
    if not isinstance(record, dict):
        return False
    if not _has_test_failure_keys(record):
        return False
    ok, _ = has_required_log_fields(record, None)
    return not ok


def _extract_timestamp_from_path(path: Optional[str]) -> Optional[str]:
    """If path contains a pattern like 2026-02-12-18-56-39, return ISO timestamp 2026-02-12T18:56:39Z."""
    if not path or not isinstance(path, str):
        return None
    match = _PATH_TIMESTAMP_PATTERN.search(path)
    if not match:
        return None
    y, mo, d, h, mi, s = match.groups()
    try:
        dt = datetime(
            int(y), int(mo), int(d), int(h), int(mi), int(s), tzinfo=timezone.utc
        )
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return None


def _get_message(record: Dict[str, Any]) -> str:
    """Build canonical message from error_message, log_message, message, hook_error, selector."""
    parts: list[str] = []
    for key in ("error_message", "log_message", "message"):
        v = record.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
            break
    if not parts:
        parts.append("Test failure (no message)")
    hook = record.get("hook_error")
    if isinstance(hook, str) and hook.strip() and hook.strip() not in str(parts):
        parts.append(hook.strip())
    sel = record.get("selector")
    if isinstance(sel, str) and sel.strip():
        parts.append(sel.strip())
    return " | ".join(parts)


def _get_timestamp(record: Dict[str, Any]) -> str:
    """Get timestamp from record, screenshot_path, or now()."""
    for key in ("timestamp", "time", "ts", "@timestamp", "event_time", "logged_at"):
        v = record.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    path_ts = _extract_timestamp_from_path(record.get("screenshot_path"))
    if path_ts:
        return path_ts
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_failure_to_canonical(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a test-failure-shaped dict into a canonical log record with message and timestamp.
    Other keys (browser, os, selector, screenshot_path, etc.) are preserved.
    """
    out: Dict[str, Any] = dict(record)
    out["message"] = _get_message(record)
    out["timestamp"] = _get_timestamp(record)
    return out
