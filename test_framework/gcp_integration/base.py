"""
Base classes and utilities for GCP integration.

Provides common functionality for all GCP service integrations.
"""

import asyncio
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from google.auth import default
from google.auth.exceptions import GoogleAuthError

# Optional GCP imports with graceful fallback
try:
    from google.cloud import logging as gcp_logging
    GCP_LOGGING_AVAILABLE = True
except ImportError:
    gcp_logging = None
    GCP_LOGGING_AVAILABLE = False

try:
    from google.cloud import secretmanager
    GCP_SECRET_MANAGER_AVAILABLE = True
except ImportError:
    secretmanager = None
    GCP_SECRET_MANAGER_AVAILABLE = False

from test_framework.unified.base_interfaces import (
    BaseTestComponent,
    ServiceConfig,
    ServiceStatus,
    TestEnvironment,
)


@dataclass
class GCPConfig:
    """Configuration for GCP services."""
    project_id: str
    region: str = "us-central1"
    service_account_path: Optional[str] = None
    timeout_seconds: int = 30
    retry_count: int = 3
    log_level: str = "INFO"


class GCPBaseClient(BaseTestComponent):
    """Base class for GCP service clients."""
    
    def __init__(self, gcp_config: GCPConfig):
        super().__init__({"gcp": gcp_config.__dict__})
        self.gcp_config = gcp_config
        self._credentials = None
        self._project_id = gcp_config.project_id
        self._region = gcp_config.region
    
    async def initialize(self) -> None:
        """Initialize GCP credentials and clients."""
        await super().initialize()
        try:
            if self.gcp_config.service_account_path:
                import json

                from google.oauth2 import service_account
                with open(self.gcp_config.service_account_path, 'r') as f:
                    sa_info = json.load(f)
                self._credentials = service_account.Credentials.from_service_account_info(sa_info)
            else:
                self._credentials, project = default()
                if not self._project_id:
                    self._project_id = project
        except GoogleAuthError as e:
            raise RuntimeError(f"Failed to initialize GCP credentials: {e}")
    
    async def cleanup(self) -> None:
        """Clean up GCP resources."""
        await super().cleanup()
        self._credentials = None
    
    @property
    def project_id(self) -> str:
        """Get the GCP project ID."""
        return self._project_id
    
    @property
    def region(self) -> str:
        """Get the GCP region."""
        return self._region
    
    async def _retry_operation(
        self,
        operation: callable,
        max_retries: Optional[int] = None
    ) -> Any:
        """Retry an operation with exponential backoff."""
        max_retries = max_retries or self.gcp_config.retry_count
        delay = 1
        
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(delay)
                delay *= 2


@dataclass
class CloudRunService:
    """Representation of a Cloud Run service."""
    name: str
    url: str
    region: str
    project_id: str
    revision: str
    created_at: datetime
    updated_at: datetime
    traffic_percent: float
    max_instances: int
    min_instances: int
    cpu_limit: str
    memory_limit: str
    environment_variables: Dict[str, str]
    labels: Dict[str, str]
    
    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> 'CloudRunService':
        """Create instance from Cloud Run API response."""
        metadata = response.get('metadata', {})
        spec = response.get('spec', {})
        status = response.get('status', {})
        
        return cls(
            name=metadata.get('name', ''),
            url=status.get('url', ''),
            region=metadata.get('labels', {}).get('cloud.googleapis.com/location', ''),
            project_id=metadata.get('namespace', ''),
            revision=status.get('latestReadyRevisionName', ''),
            created_at=datetime.fromisoformat(metadata.get('creationTimestamp', '')),
            updated_at=datetime.fromisoformat(metadata.get('updateTime', '')),
            traffic_percent=status.get('traffic', [{}])[0].get('percent', 100),
            max_instances=spec.get('template', {}).get('metadata', {})
                .get('annotations', {}).get('autoscaling.knative.dev/maxScale', '100'),
            min_instances=spec.get('template', {}).get('metadata', {})
                .get('annotations', {}).get('autoscaling.knative.dev/minScale', '0'),
            cpu_limit=spec.get('template', {}).get('spec', {})
                .get('containers', [{}])[0].get('resources', {})
                .get('limits', {}).get('cpu', '1'),
            memory_limit=spec.get('template', {}).get('spec', {})
                .get('containers', [{}])[0].get('resources', {})
                .get('limits', {}).get('memory', '512Mi'),
            environment_variables={
                env.get('name'): env.get('value', '')
                for env in spec.get('template', {}).get('spec', {})
                    .get('containers', [{}])[0].get('env', [])
            },
            labels=metadata.get('labels', {})
        )


class IGCPServiceClient(ABC):
    """Interface for GCP service-specific clients."""
    
    @abstractmethod
    async def get_service_info(self, service_name: str) -> CloudRunService:
        """Get information about a Cloud Run service."""
        pass
    
    @abstractmethod
    async def list_services(self) -> List[CloudRunService]:
        """List all Cloud Run services in the project."""
        pass
    
    @abstractmethod
    async def get_service_metrics(
        self,
        service_name: str,
        metric_types: List[str],
        duration_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get metrics for a Cloud Run service."""
        pass


@asynccontextmanager
async def gcp_client_session(gcp_config: GCPConfig):
    """Context manager for GCP client sessions."""
    client = GCPBaseClient(gcp_config)
    await client.initialize()
    try:
        yield client
    finally:
        await client.cleanup()


class GCPServiceRegistry:
    """Registry for GCP service endpoints and configurations."""
    
    CLOUD_RUN_API = "https://run.googleapis.com/v2"
    LOGGING_API = "https://logging.googleapis.com/v2"
    SECRET_MANAGER_API = "https://secretmanager.googleapis.com/v1"
    MONITORING_API = "https://monitoring.googleapis.com/v3"
    
    @classmethod
    def get_service_endpoint(cls, service: str, project_id: str, region: str) -> str:
        """Get the endpoint URL for a GCP service."""
        endpoints = {
            "cloud_run": f"{cls.CLOUD_RUN_API}/projects/{project_id}/locations/{region}/services",
            "logging": f"{cls.LOGGING_API}/projects/{project_id}/logs",
            "secrets": f"{cls.SECRET_MANAGER_API}/projects/{project_id}/secrets",
            "metrics": f"{cls.MONITORING_API}/projects/{project_id}/timeSeries"
        }
        return endpoints.get(service, "")


class GCPErrorHandler:
    """Centralized error handling for GCP operations."""
    
    @staticmethod
    def handle_api_error(error: Exception) -> Dict[str, Any]:
        """Convert GCP API errors to structured format."""
        error_info = {
            "error_type": type(error).__name__,
            "message": str(error),
            "recoverable": False,
            "retry_after": None
        }
        
        if isinstance(error, GoogleAuthError):
            error_info["category"] = "authentication"
            error_info["action"] = "Check credentials and permissions"
        elif "quota" in str(error).lower():
            error_info["category"] = "quota"
            error_info["recoverable"] = True
            error_info["retry_after"] = 60
        elif "timeout" in str(error).lower():
            error_info["category"] = "timeout"
            error_info["recoverable"] = True
            error_info["retry_after"] = 5
        else:
            error_info["category"] = "unknown"
        
        return error_info