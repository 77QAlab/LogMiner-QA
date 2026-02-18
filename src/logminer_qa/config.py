"""
Centralised configuration for the LogMiner-QA tool.

The settings object is intentionally lightweight to keep deployment surfaces
small for on-premise banking environments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .log_format import LogFormatConfig


@dataclass(slots=True)
class SanitizerConfig:
    """Configuration options for the sanitization layer."""

    enable_ner: bool = True
    ner_model_name: str = "en_core_web_sm"
    custom_entity_patterns: Optional[Path] = None
    token_prefix: str = "[TOKEN_"
    token_suffix: str = "]"
    hash_algorithm: str = "sha256"
    hashing_secret_env: str = "LOGMINER_HASH_SECRET"
    referential_store_path: Optional[Path] = None
    pii_entity_types: List[str] = field(
        default_factory=lambda: [
            "PERSON",
            "ORG",
            "GPE",
            "LOC",
            "DATE",
            "CARDINAL",
            "ACCOUNT_ID",
            "IBAN",
            "EMAIL",
            "PHONE",
        ]
    )


@dataclass(slots=True)
class PrivacyConfig:
    """Configuration options for the differential privacy layer."""

    epsilon: float = 1.0
    delta: float = 1e-5
    aggregation_window_seconds: int = 300
    enable_dp: bool = True


@dataclass(slots=True)
class Settings:
    """Application-wide configuration."""

    sanitizer: SanitizerConfig = field(default_factory=SanitizerConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    cache_dir: Path = Path("./.cache")
    model_registry_dir: Path = Path("./models")
    enable_async_processing: bool = True
    max_workers: int = 4
    log_level: str = "INFO"
    streamlit_enabled: bool = False
    connectors: Dict[str, Dict[str, str]] = field(default_factory=dict)
    # Performance optimizations
    chunk_size: int = 1000  # Process records in chunks for memory efficiency
    enable_streaming: bool = True  # Use streaming for large datasets
    validate_inputs: bool = True  # Validate input data before processing
    # Log format: optional custom field names for timestamp / message / severity
    log_format: LogFormatConfig = field(default_factory=LogFormatConfig)


DEFAULT_SETTINGS = Settings()
