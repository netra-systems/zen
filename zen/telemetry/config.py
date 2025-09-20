"""
Telemetry Configuration Management

Handles configuration for telemetry with emphasis on privacy and user control.
Implements opt-out mechanism and secure configuration management.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TelemetryLevel(Enum):
    """Telemetry collection levels"""
    DISABLED = "disabled"
    BASIC = "basic"
    DETAILED = "detailed"


@dataclass
class TelemetryConfig:
    """
    Telemetry configuration with privacy-first defaults and community analytics

    Path 1 Implementation: Anonymous Public Telemetry
    - Uses embedded service account for netra-telemetry-public
    - No user authentication required
    - Contributes to community analytics
    - Completely anonymous and aggregated

    Attributes:
        enabled: Whether telemetry is enabled (respects ZEN_TELEMETRY_DISABLED)
        level: Level of telemetry collection
        service_name: Service name for telemetry
        service_version: Service version
        gcp_project: Google Cloud project for telemetry export
        sample_rate: Sampling rate for traces (0.0 to 1.0)
        max_attributes: Maximum number of attributes per span
        export_timeout: Timeout for telemetry export in seconds
        batch_size: Batch size for span export
        queue_size: Queue size for span processor
        use_community_analytics: Use Netra's community telemetry project
    """

    # Community analytics configuration
    COMMUNITY_PROJECT = "netra-telemetry-public"
    COMMUNITY_SESSION_PREFIX = "zen_community_"

    enabled: bool = field(default_factory=lambda: not TelemetryConfig._is_disabled())
    level: TelemetryLevel = TelemetryLevel.BASIC
    service_name: str = "zen-orchestrator"
    service_version: str = "1.0.3"
    gcp_project: Optional[str] = None
    sample_rate: float = 0.1  # 10% sampling by default
    max_attributes: int = 32
    export_timeout: int = 30
    batch_size: int = 512
    queue_size: int = 2048
    use_community_analytics: bool = True  # Default to community analytics

    @staticmethod
    def _is_disabled() -> bool:
        """Check if telemetry is explicitly disabled"""
        disabled_env = os.getenv("ZEN_TELEMETRY_DISABLED", "").lower()
        return disabled_env in ("true", "1", "yes", "on")

    @staticmethod
    def is_enabled() -> bool:
        """Check if telemetry is enabled"""
        return not TelemetryConfig._is_disabled()

    @classmethod
    def from_environment(cls) -> "TelemetryConfig":
        """Create configuration from environment variables"""
        config = cls()

        # Override with environment variables if present
        config.enabled = not cls._is_disabled()

        # Telemetry level
        level_str = os.getenv("ZEN_TELEMETRY_LEVEL", "basic").lower()
        try:
            config.level = TelemetryLevel(level_str)
        except ValueError:
            logger.warning(f"Invalid telemetry level '{level_str}', using 'basic'")
            config.level = TelemetryLevel.BASIC

        # Service configuration
        config.service_name = os.getenv("ZEN_SERVICE_NAME", config.service_name)
        config.service_version = os.getenv("ZEN_SERVICE_VERSION", config.service_version)

        # GCP project - can be set via environment or will be auto-detected
        config.gcp_project = os.getenv("ZEN_TELEMETRY_GCP_PROJECT")

        # Sampling configuration
        try:
            sample_rate = float(os.getenv("ZEN_TELEMETRY_SAMPLE_RATE", config.sample_rate))
            config.sample_rate = max(0.0, min(1.0, sample_rate))
        except ValueError:
            logger.warning("Invalid sample rate, using default 0.1")

        # Performance tuning
        try:
            config.max_attributes = int(os.getenv("ZEN_TELEMETRY_MAX_ATTRIBUTES", config.max_attributes))
            config.export_timeout = int(os.getenv("ZEN_TELEMETRY_EXPORT_TIMEOUT", config.export_timeout))
            config.batch_size = int(os.getenv("ZEN_TELEMETRY_BATCH_SIZE", config.batch_size))
            config.queue_size = int(os.getenv("ZEN_TELEMETRY_QUEUE_SIZE", config.queue_size))
        except ValueError as e:
            logger.warning(f"Invalid telemetry configuration value: {e}")

        return config

    def get_service_name(self) -> str:
        """Get service name for telemetry"""
        return self.service_name

    def get_service_version(self) -> str:
        """Get service version for telemetry"""
        return self.service_version

    def get_gcp_project(self) -> str:
        """
        Get GCP project for telemetry export

        Returns community project by default for Path 1 implementation
        """
        if self.use_community_analytics:
            return self.COMMUNITY_PROJECT
        return self.gcp_project or self.COMMUNITY_PROJECT

    def should_sample(self) -> bool:
        """Determine if current operation should be sampled"""
        import random
        return random.random() < self.sample_rate

    def get_resource_attributes(self) -> Dict[str, Any]:
        """Get resource attributes for telemetry including community analytics tags"""
        import uuid
        import platform

        attributes = {
            "service.name": self.service_name,
            "service.version": self.service_version,
            "telemetry.sdk.language": "python",
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.level": self.level.value,
        }

        if self.use_community_analytics:
            # Add community analytics attributes (anonymous)
            session_id = f"{self.COMMUNITY_SESSION_PREFIX}{uuid.uuid4().hex[:8]}"
            attributes.update({
                "zen.analytics.type": "community",
                "zen.analytics.session": session_id,
                "zen.platform.os": platform.system(),
                "zen.platform.python": platform.python_version(),
                "zen.project.type": "public",
                "zen.differentiator": "community_analytics",  # What makes Zen different from Apex
            })

        return attributes

    def validate(self) -> bool:
        """Validate configuration"""
        if not self.enabled:
            return True

        # Validate sample rate
        if not (0.0 <= self.sample_rate <= 1.0):
            logger.error(f"Invalid sample rate: {self.sample_rate}")
            return False

        # Validate numeric values
        if self.max_attributes <= 0:
            logger.error(f"Invalid max_attributes: {self.max_attributes}")
            return False

        if self.export_timeout <= 0:
            logger.error(f"Invalid export_timeout: {self.export_timeout}")
            return False

        if self.batch_size <= 0:
            logger.error(f"Invalid batch_size: {self.batch_size}")
            return False

        if self.queue_size <= 0:
            logger.error(f"Invalid queue_size: {self.queue_size}")
            return False

        return True


# Global configuration instance
_config: Optional[TelemetryConfig] = None


def get_config() -> TelemetryConfig:
    """Get global telemetry configuration"""
    global _config
    if _config is None:
        _config = TelemetryConfig.from_environment()
        if not _config.validate():
            logger.error("Invalid telemetry configuration, disabling telemetry")
            _config.enabled = False
    return _config


def reset_config():
    """Reset global configuration (for testing)"""
    global _config
    _config = None