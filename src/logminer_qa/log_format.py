"""
Log format contract: required fields (timestamp, message) and field name aliases/mapping.

Allows the tool to work with different log schemas (e.g. time vs timestamp, msg vs message)
without breaking. Custom mapping can be supplied via config or CLI.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Tuple

# Built-in aliases: any of these keys (first match in record) count as the canonical field.
DEFAULT_TIMESTAMP_ALIASES: Tuple[str, ...] = (
    "timestamp",
    "time",
    "ts",
    "@timestamp",
    "date",
    "datetime",
    "created_at",
    "logged_at",
)
DEFAULT_MESSAGE_ALIASES: Tuple[str, ...] = (
    "message",
    "msg",
    "text",
    "log",
    "body",
    "content",
    "description",
    "summary",
)
DEFAULT_SEVERITY_ALIASES: Tuple[str, ...] = (
    "severity",
    "level",
    "log_level",
    "priority",
    "loglevel",
)


@dataclass(slots=True)
class LogFormatConfig:
    """
    Optional custom field names. If set, only that key is tried first;
    if not present in record, built-in aliases are used.
    """

    timestamp_field: Optional[str] = None
    message_field: Optional[str] = None
    severity_field: Optional[str] = None

    def timestamp_keys(self) -> List[str]:
        """Ordered list of keys to try for timestamp (custom first, then aliases)."""
        keys: List[str] = []
        if self.timestamp_field:
            keys.append(self.timestamp_field)
        keys.extend(k for k in DEFAULT_TIMESTAMP_ALIASES if k not in keys)
        return keys

    def message_keys(self) -> List[str]:
        """Ordered list of keys to try for message (custom first, then aliases)."""
        keys: List[str] = []
        if self.message_field:
            keys.append(self.message_field)
        keys.extend(k for k in DEFAULT_MESSAGE_ALIASES if k not in keys)
        return keys

    def severity_keys(self) -> List[str]:
        """Ordered list of keys to try for severity (custom first, then aliases)."""
        keys: List[str] = []
        if self.severity_field:
            keys.append(self.severity_field)
        keys.extend(k for k in DEFAULT_SEVERITY_ALIASES if k not in keys)
        return keys


def _unwrap_value(v: Any) -> Any:
    """If v is a single-element list or tuple, return that element; else return v."""
    if isinstance(v, (list, tuple)) and len(v) == 1:
        return v[0]
    return v


def _get_first_present(record: Mapping[str, Any], keys: List[str]) -> Tuple[Optional[str], Any]:
    """Return (key_used, value) for the first key in keys that exists in record with non-empty value.
    Single-element array values (e.g. [\"x\"]) are unwrapped to the element for the check."""
    for k in keys:
        if k not in record:
            continue
        v = record[k]
        if v is None:
            continue
        v = _unwrap_value(v)
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return (k, v)
    return (None, None)


def normalize_record(record: Any) -> Any:
    """Return a copy of record with single-element list/tuple values unwrapped.
    Non-dicts are returned as-is. Use so downstream (sanitizer, parser) see scalar values."""
    if not isinstance(record, dict):
        return record
    return {k: _unwrap_value(v) for k, v in record.items()}


def resolve_timestamp_key(record: Mapping[str, Any], config: Optional[LogFormatConfig] = None) -> Optional[str]:
    """Return the key name used for timestamp in this record, or None if missing."""
    keys = (config or LogFormatConfig()).timestamp_keys()
    key_used, _ = _get_first_present(record, keys)
    return key_used


def resolve_message_key(record: Mapping[str, Any], config: Optional[LogFormatConfig] = None) -> Optional[str]:
    """Return the key name used for message in this record, or None if missing."""
    keys = (config or LogFormatConfig()).message_keys()
    key_used, _ = _get_first_present(record, keys)
    return key_used


def has_required_log_fields(
    record: Mapping[str, Any], config: Optional[LogFormatConfig] = None
) -> Tuple[bool, Optional[str]]:
    """
    Check that record has at least one timestamp-like and one message-like field (non-empty).

    Returns:
        (True, None) if valid, (False, error_message) if invalid.
    """
    cfg = config or LogFormatConfig()
    ts_key, ts_val = _get_first_present(record, cfg.timestamp_keys())
    msg_key, msg_val = _get_first_present(record, cfg.message_keys())

    if ts_key is None or ts_val is None:
        return False, "Missing required field: timestamp (or time, ts, @timestamp, date, datetime)"
    if msg_key is None or msg_val is None:
        return False, "Missing required field: message (or msg, text, log, body, content, event)"
    return True, None
