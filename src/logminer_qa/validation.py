"""
Input validation utilities for log records.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .log_format import LogFormatConfig, has_required_log_fields

LOGGER = logging.getLogger(__name__)


def validate_record(
    record: Any,
    strict: bool = False,
    log_format_config: Optional[LogFormatConfig] = None,
) -> tuple[bool, str | None]:
    """
    Validate a log record structure.
    
    Returns:
        (is_valid, error_message)
    """
    if record is None:
        return False, "Record is None"
    
    # Accept dict, str, or list
    if not isinstance(record, (dict, str, list)):
        if strict:
            return False, f"Record must be dict, str, or list, got {type(record).__name__}"
        LOGGER.warning("Record type %s may not be processable", type(record).__name__)
    
    # Check for suspiciously large records (potential DoS)
    if isinstance(record, str) and len(record) > 1_000_000:  # 1MB limit
        return False, f"Record too large: {len(record)} bytes (max 1MB)"
    
    if isinstance(record, dict):
        # Check for excessive nesting (potential DoS)
        if _depth(record) > 20:
            return False, f"Record nesting too deep: {_depth(record)} levels (max 20)"
        
        # Check for suspiciously large dicts
        if len(record) > 10_000:
            return False, f"Record has too many keys: {len(record)} (max 10,000)"
        
        # Require at least timestamp-like and message-like fields (via aliases/mapping)
        ok, err = has_required_log_fields(record, log_format_config)
        if not ok and err:
            return False, err
    
    return True, None


def _depth(obj: Any, current: int = 0, max_depth: int = 20) -> int:
    """Calculate maximum nesting depth of a nested structure."""
    if current > max_depth:
        return current
    if isinstance(obj, dict):
        if not obj:
            return current
        return max(_depth(v, current + 1, max_depth) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        if not obj:
            return current
        return max(_depth(item, current + 1, max_depth) for item in obj)
    return current


def validate_batch(records: List[Any], max_records: int = 1_000_000) -> tuple[bool, str | None]:
    """
    Validate a batch of records.
    
    Returns:
        (is_valid, error_message)
    """
    if len(records) > max_records:
        return False, f"Batch too large: {len(records)} records (max {max_records})"
    
    return True, None

