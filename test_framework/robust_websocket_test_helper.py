"""
Robust WebSocket Test Helper

This helper provides WebSocket testing capabilities that work in multiple scenarios:
1. With E2E_OAUTH_SIMULATION_KEY for full staging authentication
2. Without E2E key for basic connectivity testing
3. Mock mode for development and unit testing
4. Fallback modes for different authentication scenarios

Business Value:
- Enables WebSocket testing regardless of environment configuration
- Validates basic WebSocket connectivity and SSL/TLS handling
- Provides debugging capabilities for WebSocket connection issues
"""

import asyncio
import json
import logging
import ssl
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Set, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import websockets
from websockets import WebSocketException, ConnectionClosedError, InvalidURI

# Add project root to path for imports
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Use isolated environment for environment management
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass 
class WebSocketTestConfig:
    """Configuration for WebSocket testing."""
    websocket_url: str
    backend_url: str
    auth_url: str
    environment: str = "development"
    use_ssl: bool = False
    connection_timeout: float = 15.0
    ping_interval: int = 30
    max_retries: int = 3
    test_user_email: str = "test@example.com"
    test_user_name: str = "Test User"


class RobustWebSocketTestHelper:
    """Robust WebSocket test helper that adapts to available authentication."""
    
    def __init__(self, config: Optional[WebSocketTestConfig] = None):
        """Initialize robust WebSocket test helper."""
        self.config = config or self._detect_configuration()
        self.websocket: Optional[websockets.ClientConnection] = None
        self.is_connected = False
        self.received_messages: List[Dict[str, Any]] = []
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.connection_start_time: Optional[datetime] = None
        
        # Authentication state
        self.auth_available = False
        self.current_token: Optional[str] = None
        
        # SSL/TLS setup
        self.ssl_context = self._create_ssl_context()
        
    def _detect_configuration(self) -> WebSocketTestConfig:
        """Detect WebSocket configuration from environment."""
        env = get_env()
        environment = env.get("ENVIRONMENT", "development")
        
        # Determine URLs based on environment
        if environment == "staging":
            websocket_url = "wss://netra-backend-staging-701982941522.us-central1.run.app/ws"
            backend_url = "https://netra-backend-staging-701982941522.us-central1.run.app"
            auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"
            use_ssl = True
        elif environment == "production":
            websocket_url = "wss://api.netrasystems.ai/ws"
            backend_url = "https://api.netrasystems.ai"
            auth_url = "https://auth.netrasystems.ai"
            use_ssl = True
        else:  # development
            websocket_url = env.get("E2E_WEBSOCKET_URL", "ws://localhost:8888/ws")
            backend_url = env.get("E2E_BACKEND_URL", "http://localhost:8888")
            auth_url = env.get("E2E_AUTH_SERVICE_URL", "http://localhost:8001")
            use_ssl = websocket_url.startswith('wss://')
        
        return WebSocketTestConfig(
            websocket_url=websocket_url,
            backend_url=backend_url,
            auth_url=auth_url,
            environment=environment,
            use_ssl=use_ssl,
            test_user_email=env.get("TEST_USER_EMAIL", f"test-{environment}@example.com"),
            test_user_name=env.get("TEST_USER_NAME", f"Test User ({environment})")
        )
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for secure WebSocket connections."""
        if self.config.use_ssl:
            try:
                context = ssl.create_default_context()
                context.check_hostname = True
                context.verify_mode = ssl.CERT_REQUIRED
                return context
            except Exception as e:
                logger.warning(f"Failed to create SSL context: {e}")
                return None
        return None
    
    async def test_authentication(self) -> bool:
        """Test if authentication is available and working."""
        env = get_env()
        
        # Check if we have E2E_OAUTH_SIMULATION_KEY for staging auth
        if env.get("E2E_OAUTH_SIMULATION_KEY"):
            try:
                # Try to import and use staging auth client
                from tests.e2e.staging_auth_client import StagingAuthClient
                
                auth_client = StagingAuthClient()
                tokens = await auth_client.get_auth_token()
                
                if tokens.get("access_token"):
                    self.current_token = tokens["access_token"]
                    self.auth_available = True
                    logger.info("Staging authentication working")
                    return True
                    
            except Exception as e:
                logger.warning(f"Staging auth failed: {e}")
        
        # Check for other auth methods
        direct_token = env.get("WEBSOCKET_TEST_TOKEN")
        if direct_token:
            self.current_token = direct_token
            self.auth_available = True
            logger.info("Using direct token for authentication")
            return True
        
        logger.info("No authentication available - will test without auth")
        return False
    
    async def connect(self, max_retries: Optional[int] = None) -> bool:
        """
        Connect to WebSocket with available authentication.
        
        Args:
            max_retries: Maximum connection attempts
            
        Returns:
            True if connected successfully
        """
        retries = max_retries or self.config.max_retries
        
        # Test authentication first
        await self.test_authentication()
        
        for attempt in range(retries + 1):
            try:
                logger.info(f"Attempting WebSocket connection (attempt {attempt + 1})")
                self.connection_start_time = datetime.now()
                
                # Prepare connection parameters
                connect_kwargs = {
                    'ping_interval': self.config.ping_interval,
                    'ping_timeout': 10,
                    'close_timeout': 10,
                }
                
                # Add authentication headers if available
                if self.auth_available and self.current_token:
                    headers = {
                        "Authorization": f"Bearer {self.current_token}",
                        "X-Environment": self.config.environment,
                        "X-Client-Type": "test-client"
                    }
                    connect_kwargs['additional_headers'] = headers
                    logger.info("Using authenticated connection")
                else:
                    logger.info("Using unauthenticated connection")
                
                # Add SSL context if needed
                if self.ssl_context:
                    connect_kwargs['ssl'] = self.ssl_context
                    logger.info("Using SSL/TLS security")
                
                # Attempt connection
                self.websocket = await asyncio.wait_for(
                    websockets.connect(self.config.websocket_url, **connect_kwargs),
                    timeout=self.config.connection_timeout
                )
                
                self.is_connected = True
                connection_time = (datetime.now() - self.connection_start_time).total_seconds()
                logger.info(f"Connected to WebSocket in {connection_time:.2f}s")
                
                # Start message listener
                asyncio.create_task(self._listen_for_messages())
                
                return True
                
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                
                if attempt < retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
        
        logger.error(f"Failed to connect after {retries + 1} attempts")
        return False
    
    async def _listen_for_messages(self) -> None:
        """Listen for incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.received_messages.append({
                        "data": data,
                        "received_at": time.time(),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    event_type = data.get("type", "unknown")
                    logger.debug(f"Received: {event_type}")
                    
                    # Call registered handlers
                    if event_type in self.event_handlers:
                        for handler in self.event_handlers[event_type]:
                            try:
                                if asyncio.iscoroutinefunction(handler):
                                    await handler(data)
                                else:
                                    handler(data)
                            except Exception as e:
                                logger.error(f"Error in handler for {event_type}: {e}")
                                
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON message: {message[:100]}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except ConnectionClosedError:
            logger.info("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in message listener: {e}")
            self.is_connected = False
    
    def on_message(self, event_type: str, handler: Callable) -> None:
        """Register message handler for specific event type."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def send_message(self, message_type: str, data: Dict[str, Any]) -> bool:
        """Send message through WebSocket."""
        if not self.is_connected:
            logger.error("Cannot send message: not connected")
            return False
        
        try:
            message = {
                "type": message_type,
                "timestamp": datetime.now().isoformat(),
                **data
            }
            
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Sent: {message_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def test_basic_connectivity(self) -> Dict[str, Any]:
        """Test basic WebSocket connectivity without requiring full agent flow."""
        logger.info("Testing basic WebSocket connectivity...")
        
        result = {
            "connection_successful": False,
            "ssl_working": False,
            "message_sending": False,
            "message_receiving": False,
            "connection_time": 0.0,
            "errors": []
        }
        
        try:
            # Test connection
            connected = await self.connect()
            result["connection_successful"] = connected
            result["ssl_working"] = self.config.use_ssl and connected
            
            if connected:
                result["connection_time"] = (
                    (datetime.now() - self.connection_start_time).total_seconds()
                    if self.connection_start_time else 0
                )
                
                # Test message sending
                initial_message_count = len(self.received_messages)
                
                success = await self.send_message("connectivity_test", {
                    "test": "basic_connectivity",
                    "timestamp": time.time()
                })
                result["message_sending"] = success
                
                # Wait briefly for any response
                await asyncio.sleep(2)
                
                # Check if we received any messages (even errors)
                new_message_count = len(self.received_messages)
                result["message_receiving"] = new_message_count > initial_message_count
                
        except Exception as e:
            error_msg = f"Connectivity test failed: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
        
        return result
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.websocket = None
                self.is_connected = False
                logger.info("Disconnected from WebSocket")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test session summary."""
        event_types = {}
        for msg in self.received_messages:
            event_type = msg["data"].get("type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        return {
            "configuration": {
                "environment": self.config.environment,
                "websocket_url": self.config.websocket_url,
                "use_ssl": self.config.use_ssl,
                "auth_available": self.auth_available
            },
            "session": {
                "connected": self.is_connected,
                "messages_received": len(self.received_messages),
                "event_types": event_types,
                "connection_time": (
                    (datetime.now() - self.connection_start_time).total_seconds()
                    if self.connection_start_time else 0
                )
            }
        }


@asynccontextmanager
async def robust_websocket_session(config: Optional[WebSocketTestConfig] = None):
    """Context manager for robust WebSocket testing session."""
    helper = RobustWebSocketTestHelper(config)
    
    try:
        yield helper
    finally:
        await helper.disconnect()


async def validate_websocket_configuration() -> Dict[str, Any]:
    """Validate WebSocket configuration and capabilities."""
    logger.info("Validating WebSocket configuration...")
    
    validation_result = {
        "environment_detected": False,
        "urls_configured": False,
        "auth_available": False,
        "ssl_configured": False,
        "connectivity_possible": False,
        "details": {},
        "recommendations": []
    }
    
    try:
        # Detect configuration
        async with robust_websocket_session() as helper:
            config = helper.config
            
            # Check environment detection
            validation_result["environment_detected"] = bool(config.environment)
            validation_result["details"]["environment"] = config.environment
            
            # Check URL configuration
            validation_result["urls_configured"] = bool(
                config.websocket_url and 
                config.backend_url and 
                config.auth_url
            )
            validation_result["details"]["websocket_url"] = config.websocket_url
            validation_result["details"]["backend_url"] = config.backend_url
            validation_result["details"]["auth_url"] = config.auth_url
            
            # Check authentication
            auth_available = await helper.test_authentication()
            validation_result["auth_available"] = auth_available
            validation_result["details"]["auth_method"] = (
                "staging_oauth" if helper.auth_available else "none"
            )
            
            # Check SSL configuration
            validation_result["ssl_configured"] = config.use_ssl
            validation_result["details"]["ssl_context"] = bool(helper.ssl_context)
            
            # Test basic connectivity
            connectivity_result = await helper.test_basic_connectivity()
            validation_result["connectivity_possible"] = connectivity_result["connection_successful"]
            validation_result["details"]["connectivity"] = connectivity_result
            
        # Generate recommendations
        if not validation_result["auth_available"]:
            validation_result["recommendations"].append(
                "Set E2E_OAUTH_SIMULATION_KEY for staging authentication"
            )
        
        if not validation_result["connectivity_possible"]:
            validation_result["recommendations"].extend([
                "Check WebSocket endpoint accessibility",
                "Verify SSL/TLS configuration if using wss://",
                "Ensure backend service is deployed and healthy"
            ])
        
        return validation_result
        
    except Exception as e:
        validation_result["details"]["error"] = str(e)
        validation_result["recommendations"].append(f"Fix configuration error: {e}")
        return validation_result


async def run_websocket_smoke_test(config: Optional[WebSocketTestConfig] = None) -> bool:
    """Run basic WebSocket smoke test that works with any configuration."""
    logger.info("Running WebSocket smoke test...")
    
    try:
        async with robust_websocket_session(config) as helper:
            # Test basic connectivity
            connectivity_result = await helper.test_basic_connectivity()
            
            if connectivity_result["connection_successful"]:
                logger.info("WebSocket smoke test PASSED")
                logger.info(f"  - Connection time: {connectivity_result['connection_time']:.2f}s")
                logger.info(f"  - SSL/TLS: {'PASS' if connectivity_result['ssl_working'] else 'FAIL'}")
                logger.info(f"  - Message sending: {'PASS' if connectivity_result['message_sending'] else 'FAIL'}")
                return True
            else:
                logger.error("WebSocket smoke test FAILED")
                for error in connectivity_result["errors"]:
                    logger.error(f"  - {error}")
                return False
                
    except Exception as e:
        logger.error(f"Smoke test failed: {e}")
        return False


async def diagnose_websocket_issues(config: Optional[WebSocketTestConfig] = None) -> Dict[str, Any]:
    """Diagnose WebSocket connection issues."""
    logger.info("Diagnosing WebSocket issues...")
    
    diagnosis = {
        "configuration_issues": [],
        "connectivity_issues": [],
        "authentication_issues": [],
        "ssl_issues": [],
        "recommendations": []
    }
    
    try:
        # Validate configuration
        validation_result = await validate_websocket_configuration()
        
        if not validation_result["environment_detected"]:
            diagnosis["configuration_issues"].append("Environment not detected properly")
        
        if not validation_result["urls_configured"]:
            diagnosis["configuration_issues"].append("WebSocket URLs not configured")
        
        if not validation_result["auth_available"]:
            diagnosis["authentication_issues"].append("No authentication method available")
            diagnosis["recommendations"].append("Set E2E_OAUTH_SIMULATION_KEY or WEBSOCKET_TEST_TOKEN")
        
        if not validation_result["ssl_configured"] and "wss://" in validation_result["details"].get("websocket_url", ""):
            diagnosis["ssl_issues"].append("SSL/TLS required but not configured")
        
        if not validation_result["connectivity_possible"]:
            diagnosis["connectivity_issues"].append("Basic WebSocket connection failed")
            
            connectivity_details = validation_result["details"].get("connectivity", {})
            if connectivity_details.get("errors"):
                diagnosis["connectivity_issues"].extend(connectivity_details["errors"])
        
        # Add specific recommendations
        if diagnosis["configuration_issues"]:
            diagnosis["recommendations"].append("Review environment configuration")
        
        if diagnosis["connectivity_issues"]:
            diagnosis["recommendations"].extend([
                "Check that WebSocket endpoint is accessible",
                "Verify backend service is running and healthy",
                "Test network connectivity to staging endpoints"
            ])
        
        if diagnosis["ssl_issues"]:
            diagnosis["recommendations"].extend([
                "Verify SSL certificate is valid",
                "Check TLS configuration",
                "Test with curl or openssl s_client"
            ])
        
        return diagnosis
        
    except Exception as e:
        diagnosis["configuration_issues"].append(f"Diagnosis failed: {e}")
        return diagnosis


async def main():
    """Main entry point for standalone testing."""
    print("Robust WebSocket Test Helper")
    print("=" * 50)
    
    # Run validation
    validation = await validate_websocket_configuration()
    
    print("\nConfiguration Validation:")
    for key, value in validation.items():
        if key not in ["details", "recommendations"]:
            status = "PASS" if value else "FAIL"
            print(f"  {status} {key.replace('_', ' ').title()}: {value}")
    
    # Show details
    if validation["details"]:
        print("\nDetails:")
        for key, value in validation["details"].items():
            if key != "connectivity":
                print(f"  - {key}: {value}")
    
    # Run smoke test
    print("\nRunning smoke test...")
    smoke_passed = await run_websocket_smoke_test()
    
    # Show recommendations if needed
    if validation["recommendations"]:
        print("\nRecommendations:")
        for rec in validation["recommendations"]:
            print(f"  - {rec}")
    
    # Run diagnosis if smoke test failed
    if not smoke_passed:
        print("\nRunning diagnosis...")
        diagnosis = await diagnose_websocket_issues()
        
        for category, issues in diagnosis.items():
            if issues and category != "recommendations":
                print(f"\n{category.replace('_', ' ').title()}:")
                for issue in issues:
                    print(f"  - {issue}")
    
    print(f"\nOverall Result: {'PASS' if smoke_passed else 'FAIL'}")


if __name__ == "__main__":
    # Set event loop policy for Windows compatibility
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())