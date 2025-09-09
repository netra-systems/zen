"""GCP Client Manager for monitoring and error reporting services.

Manages Google Cloud Platform client connections and authentication
for monitoring, error reporting, and logging services.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone

# Mock google cloud imports for testing environments
try:
    from google.cloud import error_reporting
    from google.cloud import monitoring_v3
    from google.cloud import logging as gcp_logging
    from google.oauth2 import service_account
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    # Fallback for testing/development environments
    GOOGLE_CLOUD_AVAILABLE = False
    error_reporting = None
    monitoring_v3 = None
    gcp_logging = None
    service_account = None

logger = logging.getLogger(__name__)


class GCPCredentials:
    """GCP credentials configuration."""
    
    def __init__(self, project_id: str, service_account_key: Optional[str] = None):
        self.project_id = project_id
        self.service_account_key = service_account_key


class GCPClientManager:
    """Manages GCP client connections for monitoring services."""
    
    def __init__(self, credentials: GCPCredentials):
        self.credentials = credentials
        self._error_reporting_client: Optional[Any] = None
        self._monitoring_client: Optional[Any] = None
        self._logging_client: Optional[Any] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize GCP clients."""
        if self._initialized or not GOOGLE_CLOUD_AVAILABLE:
            return
        
        try:
            # Initialize clients based on available credentials
            if self.credentials.service_account_key:
                creds = service_account.Credentials.from_service_account_info(
                    self.credentials.service_account_key
                )
            else:
                creds = None  # Use default credentials
            
            self._error_reporting_client = error_reporting.Client(
                project=self.credentials.project_id,
                credentials=creds
            )
            
            self._monitoring_client = monitoring_v3.MetricServiceClient(
                credentials=creds
            )
            
            self._logging_client = gcp_logging.Client(
                project=self.credentials.project_id,
                credentials=creds
            )
            
            self._initialized = True
            logger.info(f"GCP clients initialized for project {self.credentials.project_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize GCP clients: {e}")
            raise
    
    def get_error_reporting_client(self):
        """Get error reporting client."""
        if not GOOGLE_CLOUD_AVAILABLE:
            return MockErrorReportingClient()
        
        if not self._initialized:
            raise RuntimeError("GCP clients not initialized")
        
        return self._error_reporting_client
    
    def get_monitoring_client(self):
        """Get monitoring client."""
        if not GOOGLE_CLOUD_AVAILABLE:
            return MockMonitoringClient()
        
        if not self._initialized:
            raise RuntimeError("GCP clients not initialized")
        
        return self._monitoring_client
    
    def get_logging_client(self):
        """Get logging client."""
        if not GOOGLE_CLOUD_AVAILABLE:
            return MockLoggingClient()
        
        if not self._initialized:
            raise RuntimeError("GCP clients not initialized")
        
        return self._logging_client
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on GCP services."""
        if not GOOGLE_CLOUD_AVAILABLE:
            return {
                "status": "mock",
                "available": False,
                "message": "Google Cloud libraries not available"
            }
        
        try:
            if not self._initialized:
                await self.initialize()
            
            # Simple health checks
            return {
                "status": "healthy",
                "project_id": self.credentials.project_id,
                "error_reporting": bool(self._error_reporting_client),
                "monitoring": bool(self._monitoring_client),
                "logging": bool(self._logging_client),
                "timestamp": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            }
    
    async def get_error_reporting_client_async(self):
        """Get error reporting client - async version for integration tests."""
        if not self._initialized:
            await self.initialize()
        return self.get_error_reporting_client()
    
    async def initialize_client(self):
        """Initialize client and return error reporting client for service integration."""
        await self.initialize()
        return self.get_error_reporting_client()


# Mock clients for testing/development
class MockErrorReportingClient:
    """Mock error reporting client for testing."""
    
    def report_exception(self, exception=None, request=None):
        logger.debug(f"Mock error reporting: {exception}")
        return True
    
    def report(self, message: str):
        logger.debug(f"Mock error report: {message}")
        return True


class MockMonitoringClient:
    """Mock monitoring client for testing."""
    
    def create_time_series(self, request=None):
        logger.debug("Mock create time series")
        return True
    
    def list_time_series(self, request=None):
        logger.debug("Mock list time series")
        return []


class MockLoggingClient:
    """Mock logging client for testing."""
    
    def logger(self, name: str):
        return MockLogger(name)
    
    def list_entries(self, filter_=None):
        logger.debug(f"Mock list entries with filter: {filter_}")
        return []


class MockLogger:
    """Mock GCP logger for testing."""
    
    def __init__(self, name: str):
        self.name = name
    
    def log_text(self, text: str, severity: str = "INFO"):
        logger.debug(f"Mock log [{severity}] {self.name}: {text}")
        return True
    
    def log_struct(self, info: Dict[str, Any], severity: str = "INFO"):
        logger.debug(f"Mock log struct [{severity}] {self.name}: {info}")
        return True


# Factory function for easy instantiation
def create_gcp_client_manager(project_id: str, service_account_key: Optional[Dict] = None) -> GCPClientManager:
    """Create GCP client manager with credentials."""
    credentials = GCPCredentials(
        project_id=project_id,
        service_account_key=service_account_key
    )
    return GCPClientManager(credentials)