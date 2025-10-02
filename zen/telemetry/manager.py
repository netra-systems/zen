"""
Telemetry Manager

Core telemetry management with zen_secrets integration for secure credential handling.
Implements singleton pattern and lazy initialization for optimal performance.
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, Union
from threading import Lock
import json

# OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

# zen_secrets imports
try:
    from zen_secrets import SecretManager, SecretConfig
    ZEN_SECRETS_AVAILABLE = True
except ImportError:
    ZEN_SECRETS_AVAILABLE = False

from .config import TelemetryConfig, get_config

logger = logging.getLogger(__name__)


class NoOpSpan:
    """No-operation span for when telemetry is disabled"""
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def set_status(self, *args, **kwargs):
        pass
    def record_exception(self, *args, **kwargs):
        pass
    def set_attribute(self, *args, **kwargs):
        pass


class TelemetryManager:
    """
    Singleton telemetry manager with zen_secrets integration

    Provides secure, privacy-first telemetry collection with:
    - zen_secrets integration for credential management
    - Automatic GCP project detection
    - Lazy initialization with minimal performance impact
    - Comprehensive error handling and fallback mechanisms
    """

    _instance: Optional["TelemetryManager"] = None
    _lock = Lock()
    _initialized = False

    def __new__(cls) -> "TelemetryManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_init_complete'):
            self._config = get_config()
            self._tracer: Optional["trace.Tracer"] = None
            self._secret_manager: Optional[SecretManager] = None
            self._gcp_credentials: Optional[Dict[str, Any]] = None
            self._init_complete = True

    @classmethod
    def get_instance(cls) -> "TelemetryManager":
        """Get the singleton telemetry manager instance"""
        return cls()

    async def initialize(self) -> bool:
        """
        Initialize telemetry manager

        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        if not self._config.enabled:
            logger.info("Telemetry disabled via configuration")
            self._initialized = True
            return False

        if not OPENTELEMETRY_AVAILABLE:
            logger.warning("OpenTelemetry not available, telemetry disabled")
            self._initialized = True
            return False

        try:
            # Initialize secret manager if available
            await self._setup_secret_manager()

            # Setup GCP credentials
            await self._setup_gcp_credentials()

            # Initialize OpenTelemetry
            await self._setup_opentelemetry()

            self._initialized = True
            logger.info("Telemetry initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize telemetry: {e}")
            self._initialized = True
            return False

    async def _setup_secret_manager(self):
        """Setup zen_secrets integration"""
        if not ZEN_SECRETS_AVAILABLE:
            logger.debug("zen_secrets not available, skipping secret manager setup")
            return

        try:
            # Initialize secret manager with environment-based config
            secret_config = SecretConfig.from_environment()
            self._secret_manager = SecretManager(secret_config)
            logger.debug("Secret manager initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize secret manager: {e}")
            self._secret_manager = None

    async def _setup_gcp_credentials(self):
        """Setup GCP credentials for telemetry including community analytics"""
        try:
            # Check if using community analytics (Path 1)
            if self._config.use_community_analytics:
                from .community_auth import get_community_auth_provider
                community_provider = get_community_auth_provider()
                community_creds = community_provider.get_credentials()

                if community_creds:
                    self._gcp_credentials = community_creds
                    logger.info("Using community analytics (no authentication required)")
                    return

                logger.info("Community analytics not available, falling back to standard auth")

            # Try to get credentials from zen_secrets (for private projects)
            if self._secret_manager:
                try:
                    credentials_json = await self._secret_manager.get_secret(
                        "zen-telemetry-service-account"
                    )
                    if credentials_json:
                        self._gcp_credentials = json.loads(credentials_json.value)
                        logger.debug("GCP credentials loaded from zen_secrets")
                        return
                except Exception as e:
                    logger.debug(f"Failed to load credentials from zen_secrets: {e}")

            # Try environment variable
            creds_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if creds_env and os.path.exists(creds_env):
                logger.debug("Using GCP credentials from GOOGLE_APPLICATION_CREDENTIALS")
                return

            # Try default service account (for GKE/Cloud Run)
            logger.debug("Using default GCP service account")

        except Exception as e:
            logger.warning(f"Failed to setup GCP credentials: {e}")

    async def _setup_opentelemetry(self):
        """Setup OpenTelemetry with GCP integration"""
        try:
            # Create resource with service metadata
            resource = Resource.create(self._config.get_resource_attributes())

            # Setup tracer provider with sampling
            sampler = TraceIdRatioBased(self._config.sample_rate)
            provider = TracerProvider(
                resource=resource,
                sampler=sampler
            )

            # Setup GCP exporter if possible
            await self._setup_gcp_exporter(provider)

            # Set tracer provider
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(__name__)

            logger.debug("OpenTelemetry setup completed")

        except Exception as e:
            logger.error(f"Failed to setup OpenTelemetry: {e}")

    async def _setup_gcp_exporter(self, provider):
        """Setup Google Cloud Trace exporter for community analytics or private projects"""
        try:
            # Get project ID (community project by default)
            gcp_project = self._config.get_gcp_project()

            # Setup exporter with appropriate credentials
            exporter_kwargs = {"project_id": gcp_project}

            # If using community analytics, provide embedded credentials
            if self._config.use_community_analytics and isinstance(self._gcp_credentials, object):
                exporter_kwargs["credentials"] = self._gcp_credentials

            exporter = CloudTraceSpanExporter(**exporter_kwargs)

            # Create batch processor optimized for community analytics
            batch_config = {
                "max_queue_size": self._config.queue_size,
                "max_export_batch_size": self._config.batch_size,
                "schedule_delay_millis": 5000,
                "export_timeout_millis": self._config.export_timeout * 1000,
            }

            # Optimize for community analytics (higher throughput, lower latency)
            if self._config.use_community_analytics:
                batch_config.update({
                    "max_export_batch_size": 256,  # Smaller batches for community
                    "schedule_delay_millis": 3000,  # Faster export
                })

            processor = BatchSpanProcessor(exporter, **batch_config)
            provider.add_span_processor(processor)

            if self._config.use_community_analytics:
                logger.info(f"Community analytics enabled - contributing to public insights (project: {gcp_project})")
            else:
                logger.info(f"Private telemetry configured for project: {gcp_project}")

        except Exception as e:
            logger.warning(f"Failed to setup GCP exporter: {e}")

    async def _detect_gcp_project(self) -> Optional[str]:
        """Detect GCP project from metadata service"""
        try:
            # Try metadata service (works on GCE, GKE, Cloud Run)
            import aiohttp
            metadata_url = "http://metadata.google.internal/computeMetadata/v1/project/project-id"
            headers = {"Metadata-Flavor": "Google"}

            async with aiohttp.ClientSession() as session:
                async with session.get(metadata_url, headers=headers, timeout=5) as response:
                    if response.status == 200:
                        project_id = await response.text()
                        logger.debug(f"Detected GCP project: {project_id}")
                        return project_id

        except Exception as e:
            logger.debug(f"Failed to detect GCP project: {e}")

        return None

    @property
    def tracer(self) -> Optional["trace.Tracer"]:
        """Get tracer instance (lazy initialization)"""
        if self._tracer is None and self.is_enabled():
            # Synchronous initialization for immediate use
            if not self._initialized:
                # Schedule async initialization if event loop is running
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.initialize())
                except RuntimeError:
                    # No event loop running, will initialize later
                    pass

        return self._tracer

    def is_enabled(self) -> bool:
        """Check if telemetry is enabled"""
        return self._config.enabled and OPENTELEMETRY_AVAILABLE

    def disable(self):
        """Programmatically disable telemetry for this session"""
        import os
        os.environ['ZEN_TELEMETRY_DISABLED'] = 'true'
        # Reload config to pick up the change
        self._config = get_config()
        logger.info("Telemetry disabled programmatically")

    def enable(self):
        """Programmatically enable telemetry for this session"""
        import os
        os.environ.pop('ZEN_TELEMETRY_DISABLED', None)
        # Reload config to pick up the change
        self._config = get_config()
        logger.info("Telemetry enabled programmatically")

    def get_config(self) -> TelemetryConfig:
        """Get telemetry configuration"""
        return self._config

    async def shutdown(self):
        """Shutdown telemetry manager"""
        try:
            if OPENTELEMETRY_AVAILABLE and self._tracer:
                provider = trace.get_tracer_provider()
                if hasattr(provider, 'force_flush'):
                    provider.force_flush(timeout_millis=5000)
                if hasattr(provider, 'shutdown'):
                    provider.shutdown()

            logger.info("Telemetry shutdown completed")

        except Exception as e:
            logger.error(f"Error during telemetry shutdown: {e}")

    def create_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a new span"""
        if not self.is_enabled() or self.tracer is None:
            return NoOpSpan()

        return self.tracer.start_as_current_span(
            name,
            attributes=attributes or {}
        )

    def record_exception(self, exception: Exception, span=None):
        """Record an exception in telemetry"""
        if not self.is_enabled():
            return

        try:
            if span:
                span.record_exception(exception)
            else:
                # Get current span if available
                current_span = trace.get_current_span()
                if current_span:
                    current_span.record_exception(exception)
        except Exception as e:
            logger.debug(f"Failed to record exception in telemetry: {e}")


# Global instance - will be initialized when imported
telemetry_manager = TelemetryManager()