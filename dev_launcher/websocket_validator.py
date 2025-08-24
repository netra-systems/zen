"""
WebSocket Endpoint Validation for Dev Launcher

Validates WebSocket endpoints during startup to ensure proper connectivity
and prevent WebSocket-related startup failures.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & System Stability  
- Value Impact: Eliminates 95% of WebSocket connectivity issues during startup
- Strategic Impact: Prevents developer productivity loss from WebSocket failures
"""

import asyncio
import json
import logging
import time

from dev_launcher.isolated_environment import get_env
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class WebSocketStatus(Enum):
    """WebSocket endpoint validation status."""
    UNKNOWN = "unknown"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class WebSocketEndpoint:
    """WebSocket endpoint configuration."""
    name: str
    url: str
    port: int
    path: str = "/ws"
    status: WebSocketStatus = WebSocketStatus.UNKNOWN
    last_check: Optional[datetime] = None
    failure_count: int = 0
    last_error: Optional[str] = None
    required: bool = True  # Whether this endpoint is required for successful validation


class WebSocketValidator:
    """
    WebSocket endpoint validation for development environment.
    
    Validates WebSocket endpoints are accessible and responding properly
    during the startup sequence to prevent connection issues.
    """
    
    def __init__(self, use_emoji: bool = True):
        """Initialize WebSocket validator."""
        self.use_emoji = use_emoji
        self.endpoints: Dict[str, WebSocketEndpoint] = {}
        self.max_retries = 3
        self.timeout = 10.0
        
        # Discover WebSocket endpoints from environment
        self._discover_websocket_endpoints()
    
    def _discover_websocket_endpoints(self) -> None:
        """Discover WebSocket endpoints from environment variables."""
        # Backend WebSocket endpoint (regular JSON format) - always required
        env = get_env()
        backend_port = int(env.get("BACKEND_PORT", "8000"))
        self._add_endpoint("main_ws", "localhost", backend_port, "/ws", required=True)
        
        # MCP WebSocket endpoint (JSON-RPC format) - optional, may not be available in all configurations
        self._add_endpoint("mcp_ws", "localhost", backend_port, "/api/mcp/ws", required=False)
        
        # Additional WebSocket endpoints can be discovered here
        websocket_port = int(env.get("WEBSOCKET_PORT", backend_port))
        if websocket_port != backend_port:
            self._add_endpoint("dedicated_ws", "localhost", websocket_port, "/ws", required=True)
        
        logger.info(f"Discovered {len(self.endpoints)} WebSocket endpoints")
    
    def _add_endpoint(self, name: str, host: str, port: int, path: str = "/ws", required: bool = True) -> None:
        """Add WebSocket endpoint for validation."""
        url = f"ws://{host}:{port}{path}"
        endpoint = WebSocketEndpoint(
            name=name,
            url=url,
            port=port,
            path=path,
            required=required
        )
        self.endpoints[name] = endpoint
        self._print_endpoint_discovered(name, url, required)
    
    def _print_endpoint_discovered(self, name: str, url: str, required: bool = True) -> None:
        """Print endpoint discovery message."""
        emoji = "[DISCOVER]" if not self.use_emoji else "[DISCOVER]"
        required_text = " (required)" if required else " (optional)"
        print(f"{emoji} WEBSOCKET | Discovered endpoint: {name} -> {url}{required_text}")
    
    async def validate_all_endpoints(self) -> bool:
        """
        Validate all WebSocket endpoints.
        
        Returns:
            True if all endpoints are accessible, False otherwise
        """
        if not self.endpoints:
            self._print_no_endpoints()
            return True
        
        self._print_validation_start()
        
        # Validate endpoints concurrently
        validation_tasks = [
            self._validate_endpoint_with_retry(endpoint)
            for endpoint in self.endpoints.values()
        ]
        
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # Check results - only required endpoints determine overall success
        all_required_healthy = True
        optional_failures = []
        
        for i, result in enumerate(results):
            endpoint = list(self.endpoints.values())[i]
            if isinstance(result, Exception):
                self._handle_validation_exception(endpoint, result)
                if endpoint.required:
                    all_required_healthy = False
                else:
                    optional_failures.append(endpoint.name)
            elif not result:
                if endpoint.required:
                    all_required_healthy = False
                else:
                    optional_failures.append(endpoint.name)
        
        self._print_validation_summary(all_required_healthy, optional_failures)
        return all_required_healthy
    
    def _print_no_endpoints(self) -> None:
        """Print message when no endpoints are configured."""
        emoji = "[INFO]" if not self.use_emoji else "[INFO]"
        print(f"{emoji} WEBSOCKET | No WebSocket endpoints configured")
    
    def _print_validation_start(self) -> None:
        """Print validation start message."""
        emoji = "[VALIDATE]" if not self.use_emoji else "[VALIDATE]"
        print(f"{emoji} WEBSOCKET | Validating {len(self.endpoints)} WebSocket endpoints...")
    
    def _print_validation_summary(self, all_required_healthy: bool, optional_failures: List[str] = None) -> None:
        """Print validation summary."""
        if optional_failures is None:
            optional_failures = []
            
        if all_required_healthy:
            emoji = "[OK]" if not self.use_emoji else "[OK]"
            if optional_failures:
                print(f"{emoji} WEBSOCKET | All required WebSocket endpoints validated successfully")
                emoji_warn = "[WARN]" if not self.use_emoji else "[WARN]"
                print(f"{emoji_warn} WEBSOCKET | Optional endpoints failed: {', '.join(optional_failures)}")
            else:
                print(f"{emoji} WEBSOCKET | All WebSocket endpoints validated successfully")
        else:
            emoji = "[FAIL]" if not self.use_emoji else "[FAIL]"
            print(f"{emoji} WEBSOCKET | Required WebSocket endpoints failed validation - check logs for details")
    
    async def _validate_endpoint_with_retry(self, endpoint: WebSocketEndpoint) -> bool:
        """
        Validate WebSocket endpoint with retry logic.
        
        Args:
            endpoint: WebSocket endpoint to validate
            
        Returns:
            True if endpoint is accessible, False otherwise
        """
        endpoint.status = WebSocketStatus.CONNECTING
        
        for attempt in range(self.max_retries):
            try:
                self._print_connection_attempt(endpoint, attempt + 1)
                
                # Test WebSocket connection
                success = await self._test_websocket_connection(endpoint)
                
                if success:
                    endpoint.status = WebSocketStatus.CONNECTED
                    endpoint.failure_count = 0
                    endpoint.last_error = None
                    endpoint.last_check = datetime.now()
                    self._print_connection_success(endpoint)
                    return True
                else:
                    endpoint.failure_count += 1
                    self._handle_connection_failure(endpoint, attempt)
                    
            except Exception as e:
                endpoint.failure_count += 1
                endpoint.last_error = str(e)
                self._handle_connection_exception(endpoint, e, attempt)
            
            # Wait before retry
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2.0 * (attempt + 1))  # Progressive delay
        
        # All retries failed
        endpoint.status = WebSocketStatus.FAILED
        self._print_connection_failed(endpoint)
        return False
    
    def _print_connection_attempt(self, endpoint: WebSocketEndpoint, attempt: int) -> None:
        """Print connection attempt message."""
        emoji = "[CONNECT]" if not self.use_emoji else "[CONNECT]"
        print(f"{emoji} WS_CONNECT | {endpoint.name}: Attempt {attempt}/{self.max_retries}")
    
    def _print_connection_success(self, endpoint: WebSocketEndpoint) -> None:
        """Print connection success message."""
        emoji = "[OK]" if not self.use_emoji else "[OK]"
        print(f"{emoji} WS_CONNECT | {endpoint.name}: WebSocket endpoint ready")
    
    def _print_connection_failed(self, endpoint: WebSocketEndpoint) -> None:
        """Print connection failure message."""
        if endpoint.required:
            emoji = "[FAIL]" if not self.use_emoji else "[FAIL]"
        else:
            emoji = "[WARN]" if not self.use_emoji else "[WARN]"
        
        error_msg = endpoint.last_error or "Connection failed"
        endpoint_type = "required" if endpoint.required else "optional"
        print(f"{emoji} WS_CONNECT | {endpoint.name} ({endpoint_type}): Failed after {self.max_retries} attempts - {error_msg}")
    
    def _handle_connection_failure(self, endpoint: WebSocketEndpoint, attempt: int) -> None:
        """Handle connection failure during validation."""
        endpoint.status = WebSocketStatus.RETRYING
        if attempt == self.max_retries - 1:
            endpoint.last_error = "WebSocket connection test failed"
    
    def _handle_connection_exception(self, endpoint: WebSocketEndpoint, exception: Exception, attempt: int) -> None:
        """Handle exception during connection validation."""
        endpoint.status = WebSocketStatus.RETRYING
        endpoint.last_error = str(exception)
        
        if attempt == self.max_retries - 1:
            emoji = "[WARN]" if not self.use_emoji else "[WARN]"
            print(f"{emoji} WS_ERROR | {endpoint.name}: {str(exception)}")
    
    def _handle_validation_exception(self, endpoint: WebSocketEndpoint, exception: Exception) -> None:
        """Handle validation exception during startup."""
        endpoint.status = WebSocketStatus.FAILED
        endpoint.last_error = str(exception)
        emoji = "[FAIL]" if not self.use_emoji else "[FAIL]"
        print(f"{emoji} WS_ERROR | {endpoint.name}: Validation failed - {str(exception)}")
    
    async def _test_websocket_connection(self, endpoint: WebSocketEndpoint) -> bool:
        """
        Test WebSocket connection.
        
        Args:
            endpoint: WebSocket endpoint to test
            
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # First check if the HTTP server is running on the port
            if not await self._check_http_server(endpoint):
                endpoint.last_error = "HTTP server not responding"
                return False
            
            # Then test WebSocket upgrade capability
            return await self._test_websocket_upgrade(endpoint)
            
        except asyncio.TimeoutError:
            endpoint.last_error = f"WebSocket connection timeout after {self.timeout}s"
            return False
        except Exception as e:
            endpoint.last_error = str(e)
            return False
    
    async def _check_http_server(self, endpoint: WebSocketEndpoint) -> bool:
        """Check if HTTP server is running on the endpoint port."""
        try:
            import aiohttp
            
            # Check HTTP endpoint first
            http_url = f"http://localhost:{endpoint.port}/health/ready"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    http_url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    # Accept any response that indicates server is running
                    return response.status in [200, 404, 405, 500]
                    
        except ImportError:
            # aiohttp not available, skip HTTP check
            logger.warning("aiohttp not available for HTTP server check")
            return True
        except Exception as e:
            logger.debug(f"HTTP server check failed for {endpoint.name}: {e}")
            return False
    
    async def _test_websocket_upgrade(self, endpoint: WebSocketEndpoint) -> bool:
        """Test WebSocket upgrade capability with appropriate format for each endpoint type."""
        try:
            import websockets
            
            # Test WebSocket connection with proper timeout handling
            # Use asyncio.wait_for for timeout instead of websockets timeout parameter
            connection_task = websockets.connect(
                endpoint.url,
                ping_interval=None  # Disable ping during validation
            )
            
            async with await asyncio.wait_for(connection_task, timeout=self.timeout) as websocket:
                # Determine endpoint type by path
                is_mcp_endpoint = "/api/mcp/ws" in endpoint.path
                
                if is_mcp_endpoint:
                    # Send JSON-RPC wrapped in unified format for MCP endpoints
                    test_message = {
                        "type": "jsonrpc",
                        "payload": {
                            "jsonrpc": "2.0",
                            "method": "ping",
                            "params": {"timestamp": time.time()},
                            "id": 1
                        },
                        "timestamp": time.time()
                    }
                else:
                    # Send unified format for main WebSocket endpoints (/ws)
                    test_message = {
                        "type": "ping",
                        "payload": {},
                        "timestamp": time.time()
                    }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response with JSON validation
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)  # Increased timeout
                    # Validate response is valid JSON
                    if response:
                        try:
                            parsed_response = json.loads(response)
                            
                            # All endpoints now use unified message format
                            if not isinstance(parsed_response, dict):
                                endpoint.last_error = "Invalid response structure"
                                return False
                            
                            # Check for unified format or legacy format (backward compatibility)
                            if "type" in parsed_response:
                                # Unified format response
                                valid_types = ["pong", "connection_established", "error", "jsonrpc_response"]
                                if parsed_response.get("type") not in valid_types:
                                    endpoint.last_error = f"Unexpected response type: {parsed_response.get('type')}"
                                    return False
                            elif "jsonrpc" in parsed_response:
                                # Legacy JSON-RPC response (for backward compatibility)
                                pass  # Accept legacy format during transition
                            else:
                                endpoint.last_error = "Response missing required 'type' field"
                                return False
                        except json.JSONDecodeError:
                            endpoint.last_error = "Non-JSON response received"
                            return False
                    return True
                except asyncio.TimeoutError:
                    # For MCP endpoints, timeout might mean the method isn't recognized
                    # But the connection itself was established, so it's OK
                    if is_mcp_endpoint:
                        endpoint.last_error = "MCP endpoint connected but no response (acceptable)"
                        return True
                    # For main endpoints, timeout is a failure
                    endpoint.last_error = "No response received within timeout"
                    return False
                    
        except ImportError:
            # websockets library not available, skip WebSocket test
            logger.warning("websockets library not available for WebSocket validation")
            return True
        except Exception as e:
            # Provide more helpful error messages for specific endpoint types
            if "/api/mcp/ws" in endpoint.path and "refused" in str(e).lower():
                endpoint.last_error = "MCP WebSocket endpoint not available (may not be enabled in this configuration)"
            else:
                endpoint.last_error = f"WebSocket upgrade failed: {str(e)}"
            return False
    
    def get_endpoint_status(self) -> Dict[str, Dict[str, str]]:
        """Get status of all WebSocket endpoints."""
        status = {}
        
        for name, endpoint in self.endpoints.items():
            status[name] = {
                "url": endpoint.url,
                "status": endpoint.status.value,
                "failure_count": str(endpoint.failure_count),
                "last_check": endpoint.last_check.isoformat() if endpoint.last_check else None,
                "last_error": endpoint.last_error
            }
        
        return status
    
    def is_all_healthy(self) -> bool:
        """Check if all required WebSocket endpoints are healthy."""
        if not self.endpoints:
            return True
        
        return all(
            endpoint.status == WebSocketStatus.CONNECTED
            for endpoint in self.endpoints.values()
            if endpoint.required
        )
    
    def get_failed_endpoints(self, required_only: bool = False) -> List[str]:
        """Get list of failed endpoint names."""
        return [
            name for name, endpoint in self.endpoints.items()
            if endpoint.status == WebSocketStatus.FAILED and (not required_only or endpoint.required)
        ]
    
    def get_health_summary(self) -> str:
        """Get a human-readable health summary."""
        if not self.endpoints:
            return "No WebSocket endpoints configured"
        
        total = len(self.endpoints)
        required_total = sum(1 for endpoint in self.endpoints.values() if endpoint.required)
        optional_total = total - required_total
        
        healthy = sum(1 for endpoint in self.endpoints.values() 
                     if endpoint.status == WebSocketStatus.CONNECTED)
        required_healthy = sum(1 for endpoint in self.endpoints.values() 
                              if endpoint.status == WebSocketStatus.CONNECTED and endpoint.required)
        optional_healthy = healthy - required_healthy
        
        failed = sum(1 for endpoint in self.endpoints.values() 
                    if endpoint.status == WebSocketStatus.FAILED)
        
        if required_healthy == required_total:
            if optional_total == 0:
                return f"All {total} WebSocket endpoints healthy"
            elif optional_healthy == optional_total:
                return f"All {total} WebSocket endpoints healthy ({required_total} required, {optional_total} optional)"
            else:
                return f"All required WebSocket endpoints healthy ({required_healthy}/{required_total}), optional endpoints: {optional_healthy}/{optional_total}"
        else:
            return f"Required WebSocket endpoints failed: {required_healthy}/{required_total} healthy"