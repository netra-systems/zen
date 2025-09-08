"""
Integration Test Authentication Manager - SSOT for WebSocket Integration Test Auth

Business Value Justification (BVJ):
- Segment: Platform/Internal (Test Infrastructure)
- Business Goal: Enable WebSocket integration testing without breaking SSOT architecture
- Value Impact: Allows real authentication testing while maintaining development velocity
- Strategic Impact: Prevents auth regressions and ensures multi-user isolation works

This manager provides a lightweight auth service specifically for integration tests
that maintains SSOT compliance while enabling real authentication flows.

CRITICAL: This is NOT a mock - it starts the real auth service in test mode
to ensure integration tests use the same auth validation as production.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import aiohttp
import psutil

from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

logger = logging.getLogger(__name__)


class IntegrationAuthServiceManager:
    """
    SSOT Authentication Manager for Integration Tests.
    
    This manager starts and manages a real auth service instance specifically
    for integration testing, ensuring SSOT compliance while enabling
    WebSocket authentication flows.
    
    CRITICAL: This uses the REAL auth service, not mocks, to maintain
    authentication behavior consistency with production.
    """
    
    def __init__(self):
        """Initialize integration auth service manager."""
        self.env = get_env()
        self.auth_process: Optional[subprocess.Popen] = None
        self.auth_port = 8081  # Standard auth service port
        self.auth_url = f"http://localhost:{self.auth_port}"
        self.startup_timeout = 30.0  # seconds
        self.shutdown_timeout = 10.0  # seconds
        self._is_running = False
        
        # Configure test environment for auth service
        self._setup_test_environment()
        
        logger.info("IntegrationAuthServiceManager initialized")
    
    def _setup_test_environment(self):
        """Set up environment variables for test auth service."""
        # Use existing SERVICE_SECRET from environment if available, otherwise set a test one
        existing_service_secret = self.env.get('SERVICE_SECRET')
        test_service_secret = existing_service_secret or "test-service-secret-32-chars-long"
        
        # Set test-specific environment variables
        test_env_vars = {
            "ENVIRONMENT": "test",
            "AUTH_FAST_TEST_MODE": "true",  # Skip database initialization
            "PORT": str(self.auth_port),
            "SERVICE_SECRET": test_service_secret,
            "JWT_SECRET_KEY": "test-jwt-secret-key-unified-testing-32chars",
            "ENABLE_AUTH_LOGGING": "false",  # Reduce log noise
            "POSTGRES_HOST": "localhost",  # Will be ignored in fast test mode
            "POSTGRES_PORT": "5432",
            "POSTGRES_DATABASE": "test_auth",
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "test_pass"
        }
        
        # Store the service secret for use in API calls
        self.service_secret = test_service_secret
        
        for key, value in test_env_vars.items():
            self.env.set(key, value, source="integration_test")
            os.environ[key] = value  # Also set in os.environ for subprocess
        
        logger.debug("Test environment configured for auth service")
    
    async def start_auth_service(self) -> bool:
        """
        Start the auth service for integration testing.
        
        Returns:
            True if service started successfully, False otherwise
        """
        if self._is_running:
            logger.info("Auth service is already running")
            return True
        
        # Check if port is already in use
        if self._is_port_in_use(self.auth_port):
            logger.warning(f"Port {self.auth_port} is already in use")
            # Try to connect to existing service
            if await self._validate_auth_service_health():
                logger.info("Found existing healthy auth service")
                self._is_running = True
                return True
            else:
                logger.error("Port in use but service is not healthy")
                return False
        
        # Start the auth service process
        logger.info(f"Starting auth service on port {self.auth_port}")
        
        try:
            # Get path to auth service main.py
            project_root = Path(__file__).parent.parent.parent
            auth_main_path = project_root / "auth_service" / "main.py"
            
            if not auth_main_path.exists():
                logger.error(f"Auth service main.py not found at: {auth_main_path}")
                return False
            
            # Start auth service process
            self.auth_process = subprocess.Popen(
                [sys.executable, str(auth_main_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=os.environ.copy(),
                cwd=str(project_root)
            )
            
            logger.info(f"Started auth service process (PID: {self.auth_process.pid})")
            
            # Wait for service to be ready
            if await self._wait_for_service_ready():
                self._is_running = True
                logger.info("Auth service is ready for integration tests")
                return True
            else:
                logger.error("Auth service failed to become ready")
                await self.stop_auth_service()
                return False
                
        except Exception as e:
            logger.error(f"Failed to start auth service: {e}")
            await self.stop_auth_service()
            return False
    
    async def stop_auth_service(self):
        """Stop the auth service and clean up."""
        if not self._is_running:
            return
        
        logger.info("Stopping auth service")
        
        try:
            if self.auth_process:
                # Graceful shutdown first
                self.auth_process.terminate()
                
                try:
                    # Wait for graceful shutdown
                    self.auth_process.wait(timeout=self.shutdown_timeout)
                    logger.info("Auth service shut down gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    logger.warning("Auth service did not shut down gracefully, force killing")
                    self.auth_process.kill()
                    self.auth_process.wait(timeout=5)
                
                self.auth_process = None
            
            # Also kill any remaining processes on the port
            await self._kill_processes_on_port(self.auth_port)
            
            self._is_running = False
            logger.info("Auth service stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping auth service: {e}")
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    return True
            return False
        except Exception:
            # Fallback method
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                result = sock.connect_ex(('localhost', port))
                return result == 0
    
    async def _kill_processes_on_port(self, port: int):
        """Kill any processes using the specified port."""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    connections = proc.info['connections']
                    if connections:
                        for conn in connections:
                            if hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == port:
                                logger.info(f"Killing process {proc.info['pid']} ({proc.info['name']}) using port {port}")
                                proc.kill()
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            logger.warning(f"Error killing processes on port {port}: {e}")
    
    async def _wait_for_service_ready(self) -> bool:
        """Wait for auth service to be ready."""
        start_time = time.time()
        
        while time.time() - start_time < self.startup_timeout:
            try:
                # Check if process is still running
                if self.auth_process and self.auth_process.poll() is not None:
                    # Process has terminated
                    stdout, stderr = self.auth_process.communicate()
                    logger.error(f"Auth service process terminated unexpectedly")
                    if stderr:
                        logger.error(f"Auth service stderr: {stderr.decode()}")
                    return False
                
                # Try to connect to the service
                if await self._validate_auth_service_health():
                    return True
                
                # Wait a bit before retrying
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.debug(f"Waiting for auth service ready: {e}")
                await asyncio.sleep(0.5)
        
        logger.error(f"Auth service did not become ready within {self.startup_timeout} seconds")
        return False
    
    async def _validate_auth_service_health(self) -> bool:
        """Validate that the auth service is healthy."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.auth_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("status") == "healthy"
                    return False
        except Exception as e:
            logger.debug(f"Auth service health check failed: {e}")
            return False
    
    async def create_test_token(self, user_id: str = "test-user-123", 
                               email: str = "test@example.com",
                               permissions: list = None) -> Optional[str]:
        """
        Create a test JWT token via the auth service.
        
        Args:
            user_id: User ID for the token
            email: User email
            permissions: User permissions
            
        Returns:
            JWT token string or None if creation fails
        """
        if not self._is_running:
            logger.error("Auth service is not running - cannot create test token")
            return None
        
        permissions = permissions or ["read", "write"]
        
        try:
            async with aiohttp.ClientSession() as session:
                token_data = {
                    "user_id": user_id,
                    "email": email,
                    "permissions": permissions,
                    "expires_in": 3600  # 1 hour
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "X-Service-ID": "netra-backend",
                    "X-Service-Secret": "test-service-secret-32-chars-long"
                }
                
                # Note: create-token endpoint doesn't require service auth headers
                async with session.post(
                    f"{self.auth_url}/auth/create-token", 
                    json=token_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        token = result.get("access_token")
                        if token:
                            logger.debug(f"Created test token for user: {user_id}")
                            return token
                    else:
                        logger.error(f"Token creation failed: {response.status}")
                        error_text = await response.text()
                        logger.error(f"Token creation error: {error_text}")
        except Exception as e:
            logger.error(f"Failed to create test token: {e}")
        
        return None
    
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a JWT token via the auth service.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Validation result dict or None if validation fails
        """
        if not self._is_running:
            logger.error("Auth service is not running - cannot validate token")
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                request_data = {
                    "token": token,
                    "token_type": "access"
                }
                
                # Validate endpoint requires service auth headers
                headers = {
                    "Content-Type": "application/json",
                    "X-Service-ID": "netra-backend", 
                    "X-Service-Secret": self.service_secret
                }
                
                async with session.post(
                    f"{self.auth_url}/auth/validate",
                    json=request_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug("Token validation successful")
                        return result
                    else:
                        logger.warning(f"Token validation failed: {response.status}")
                        error_text = await response.text()
                        logger.warning(f"Token validation error response: {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None
    
    def is_running(self) -> bool:
        """Check if the auth service is running."""
        return self._is_running
    
    def get_auth_url(self) -> str:
        """Get the auth service URL."""
        return self.auth_url
    
    async def __aenter__(self):
        """Async context manager entry."""
        success = await self.start_auth_service()
        if not success:
            raise RuntimeError("Failed to start auth service for integration tests")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_auth_service()


class IntegrationTestAuthHelper(E2EAuthHelper):
    """
    Enhanced E2E Auth Helper for Integration Tests.
    
    This extends the base E2EAuthHelper to work specifically with
    the IntegrationAuthServiceManager for WebSocket integration testing.
    """
    
    def __init__(self, auth_manager: IntegrationAuthServiceManager):
        """Initialize with integration auth service manager."""
        # Initialize base E2E auth helper with test config
        config = self._create_integration_test_config(auth_manager)
        super().__init__(config=config, environment="test")
        
        self.auth_manager = auth_manager
        
        logger.info("IntegrationTestAuthHelper initialized")
    
    def _create_integration_test_config(self, auth_manager: IntegrationAuthServiceManager):
        """Create configuration for integration testing."""
        from test_framework.ssot.e2e_auth_helper import E2EAuthConfig
        
        return E2EAuthConfig(
            auth_service_url=auth_manager.get_auth_url(),
            backend_url="http://localhost:8000",  # Default backend URL for integration tests
            websocket_url="ws://localhost:8000/ws",  # Default WebSocket URL
            test_user_email="integration_test@example.com",
            test_user_password="integration_test_password_123",
            jwt_secret="test-jwt-secret-key-unified-testing-32chars",
            timeout=15.0  # Longer timeout for integration tests
        )
    
    async def create_integration_test_token(
        self,
        user_id: str = "integration-test-user",
        email: Optional[str] = None,
        permissions: Optional[list] = None
    ) -> str:
        """
        Create a token specifically for integration tests.
        
        This method uses the integration auth service to create
        a token that will be properly validated by the backend.
        
        Args:
            user_id: User ID for the token
            email: User email (defaults to config email)
            permissions: User permissions (defaults to read/write)
            
        Returns:
            Valid JWT token string
        """
        email = email or self.config.test_user_email
        permissions = permissions or ["read", "write"]
        
        if not self.auth_manager.is_running():
            raise RuntimeError("Auth service is not running - cannot create integration test token")
        
        # Use the auth manager to create the token
        token = await self.auth_manager.create_test_token(
            user_id=user_id,
            email=email,
            permissions=permissions
        )
        
        if not token:
            raise RuntimeError("Failed to create integration test token")
        
        # Cache the token
        self._cached_token = token
        self._token_expiry = None  # Auth service handles expiry
        
        logger.info(f"Created integration test token for user: {user_id}")
        return token
    
    async def validate_integration_token(self, token: str) -> bool:
        """
        Validate a token using the integration auth service.
        
        Args:
            token: JWT token to validate
            
        Returns:
            True if token is valid
        """
        if not self.auth_manager.is_running():
            logger.error("Auth service is not running - cannot validate token")
            return False
        
        result = await self.auth_manager.validate_token(token)
        return result is not None and result.get("valid", False)
    
    def get_integration_auth_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """
        Get authentication headers for integration test requests.
        
        Args:
            token: JWT token (uses cached if not provided)
            
        Returns:
            Headers dict with Authorization Bearer token
        """
        if not token:
            if not self._cached_token:
                raise RuntimeError("No token available - create integration test token first")
            token = self._cached_token
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Test-Mode": "integration"
        }
    
    def get_integration_websocket_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """
        Get WebSocket authentication headers for integration tests.
        
        Args:
            token: JWT token (uses cached if not provided)
            
        Returns:
            Headers dict for WebSocket authentication
        """
        if not token:
            if not self._cached_token:
                raise RuntimeError("No token available - create integration test token first")
            token = self._cached_token
        
        # Extract user ID from token for header
        import jwt
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded.get("sub", "unknown-user")
        except Exception:
            user_id = "integration-test-user"
        
        return {
            "Authorization": f"Bearer {token}",
            "X-User-ID": user_id,
            "X-Test-Mode": "integration"
        }


# Singleton instance for integration tests
_integration_auth_manager: Optional[IntegrationAuthServiceManager] = None


async def get_integration_auth_manager() -> IntegrationAuthServiceManager:
    """
    Get or create the singleton integration auth service manager.
    
    Returns:
        IntegrationAuthServiceManager instance
    """
    global _integration_auth_manager
    
    if _integration_auth_manager is None:
        _integration_auth_manager = IntegrationAuthServiceManager()
    
    return _integration_auth_manager


async def create_integration_test_helper() -> IntegrationTestAuthHelper:
    """
    Create an integration test auth helper with managed auth service.
    
    Returns:
        IntegrationTestAuthHelper configured for integration testing
    """
    auth_manager = await get_integration_auth_manager()
    
    # Ensure auth service is running
    if not auth_manager.is_running():
        success = await auth_manager.start_auth_service()
        if not success:
            raise RuntimeError("Failed to start auth service for integration tests")
    
    return IntegrationTestAuthHelper(auth_manager)


# Convenience functions for backward compatibility
async def start_integration_auth_service() -> bool:
    """Start the integration auth service."""
    auth_manager = await get_integration_auth_manager()
    return await auth_manager.start_auth_service()


async def stop_integration_auth_service():
    """Stop the integration auth service."""
    global _integration_auth_manager
    
    if _integration_auth_manager:
        await _integration_auth_manager.stop_auth_service()
        _integration_auth_manager = None


async def create_integration_test_token(
    user_id: str = "integration-test-user",
    email: str = "integration_test@example.com",
    permissions: list = None
) -> str:
    """
    Convenience function to create an integration test token.
    
    Args:
        user_id: User ID for the token
        email: User email
        permissions: User permissions
        
    Returns:
        Valid JWT token string
    """
    helper = await create_integration_test_helper()
    return await helper.create_integration_test_token(
        user_id=user_id,
        email=email,
        permissions=permissions
    )


# Export key classes and functions
__all__ = [
    "IntegrationAuthServiceManager",
    "IntegrationTestAuthHelper", 
    "get_integration_auth_manager",
    "create_integration_test_helper",
    "start_integration_auth_service",
    "stop_integration_auth_service",
    "create_integration_test_token"
]