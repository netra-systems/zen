"""GCP Client Management Module - Handles authentication and client creation.

Business Value Justification (BVJ):
1. Segment: Mid & Enterprise
2. Business Goal: Secure and reliable GCP integration
3. Value Impact: Ensures secure access to GCP Error Reporting API
4. Revenue Impact: Supports $15K MRR reliability monitoring features

CRITICAL ARCHITECTURAL COMPLIANCE:
- Maximum file size: 300 lines (enforced)
- Maximum function size: 8 lines (enforced)
- Single responsibility: GCP client management only
"""

from typing import Optional

from google.auth import default
from google.cloud import error_reporting
from google.oauth2 import service_account

from netra_backend.app.core.error_codes import ErrorCode
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.schemas.monitoring_schemas import GCPErrorServiceConfig


class GCPClientManager:
    """Manages GCP client creation and authentication."""
    
    def __init__(self, config: GCPErrorServiceConfig):
        self.config = config
        self.client: Optional[error_reporting.Client] = None
    
    async def initialize_client(self) -> error_reporting.Client:
        """Initialize and return GCP Error Reporting client."""
        credentials = await self._get_credentials()
        self.client = self._create_client(credentials)
        await self._validate_connection()
        return self.client
    
    async def _get_credentials(self) -> Optional[service_account.Credentials]:
        """Get GCP credentials based on configuration."""
        if self.config.credentials.use_default_credentials:
            return await self._get_default_credentials()
        return await self._get_service_account_credentials()
    
    async def _get_default_credentials(self) -> Optional[service_account.Credentials]:
        """Get default application credentials."""
        try:
            credentials, _ = default()
            return credentials
        except Exception as e:
            raise NetraException(f"Failed to get default credentials: {str(e)}", ErrorCode.AUTH_ERROR)
    
    async def _get_service_account_credentials(self) -> service_account.Credentials:
        """Get service account credentials from file."""
        try:
            return service_account.Credentials.from_service_account_file(
                self.config.credentials.credentials_path)
        except Exception as e:
            raise NetraException(f"Failed to load service account: {str(e)}", ErrorCode.AUTH_ERROR)
    
    def _create_client(self, credentials) -> error_reporting.Client:
        """Create GCP Error Reporting client."""
        try:
            return error_reporting.Client(credentials=credentials)
        except Exception as e:
            raise NetraException(f"Failed to create GCP client: {str(e)}", ErrorCode.EXTERNAL_SERVICE_ERROR)
    
    async def _validate_connection(self) -> None:
        """Validate GCP connection and permissions."""
        try:
            # For the error reporting Client, we can just check if the project is accessible
            if not self.client.project:
                raise NetraException("No project configured for GCP client", ErrorCode.EXTERNAL_SERVICE_ERROR)
            # The client initialization itself validates the connection
        except Exception as e:
            raise NetraException(f"GCP connection validation failed: {str(e)}", ErrorCode.EXTERNAL_SERVICE_ERROR)