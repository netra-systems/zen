"""
Staging WebSocket Testing Utilities

Provides comprehensive utilities for testing WebSocket functionality in staging environment.
Includes connection management, event validation, retry logic, and authentication handling.

Business Value:
- Ensures WebSocket reliability in production-like staging environment
- Validates agent event flows work correctly before production deployment
- Prevents production issues that could cost $50K+ MRR
"""

import asyncio
import json
import logging
import ssl
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Set, Callable, AsyncGenerator
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import websockets
from websockets.exceptions import WebSocketException, ConnectionClosedError

from tests.e2e.staging_config import get_staging_config
from tests.e2e.staging_auth_client import StagingAuthClient

logger = logging.getLogger(__name__)


@dataclass
class WebSocketTestSession:
    """Tracks a WebSocket test session with comprehensive metrics."""
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    messages_sent: List[Dict[str, Any]] = field(default_factory=list)
    connection_attempts: int = 0
    successful_connections: int = 0
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> float:
        """Get session duration in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Get connection success rate."""
        if self.connection_attempts == 0:
            return 0.0
        return self.successful_connections / self.connection_attempts


class StagingWebSocketTester:
    """Comprehensive WebSocket tester for staging environment."""
    
    def __init__(self, session_id: Optional[str] = None):
        """Initialize staging WebSocket tester."""
        self.config = get_staging_config()
        self.auth_client = StagingAuthClient()
        self.session = WebSocketTestSession(
            session_id=session_id or f"test-{int(time.time())}"
        )
        
        # Connection state
        self.websocket: Optional[websockets.ClientConnection] = None
        self.is_connected = False
        self.current_token: Optional[str] = None
        
        # Event tracking
        self.event_callbacks: Dict[str, List[Callable]] = {}
        self.event_waiter_tasks: List[asyncio.Task] = []
        
        # Performance metrics
        self.connection_times: List[float] = []
        self.message_latencies: Dict[str, float] = {}
        
    async def setup_authenticated_connection(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> bool:
        """
        Setup authenticated WebSocket connection with retry logic.
        
        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retry attempts
            
        Returns:
            True if connection established successfully
        """
        for attempt in range(max_retries + 1):
            self.session.connection_attempts += 1
            
            try:
                start_time = time.time()
                
                # Get fresh authentication token
                tokens = await self.auth_client.get_auth_token(
                    email=self.config.test_user_email,
                    force_refresh=(attempt > 0)  # Refresh token on retries
                )
                self.current_token = tokens["access_token"]
                
                # Create SSL context for secure connections
                ssl_context = None
                if self.config.urls.websocket_url.startswith('wss://'):
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = True
                    ssl_context.verify_mode = ssl.CERT_REQUIRED
                
                # Attempt WebSocket connection
                headers = self.config.get_websocket_headers(self.current_token)
                
                connect_kwargs = {
                    'additional_headers': headers,
                    'ping_interval': self.config.ws_heartbeat_interval,
                    'ping_timeout': 10,
                    'close_timeout': 10,
                }
                
                if ssl_context:
                    connect_kwargs['ssl'] = ssl_context
                
                self.websocket = await asyncio.wait_for(
                    websockets.connect(self.config.urls.websocket_url, **connect_kwargs),
                    timeout=15.0
                )
                
                connection_time = time.time() - start_time
                self.connection_times.append(connection_time)
                self.is_connected = True
                self.session.successful_connections += 1
                
                logger.info(f" PASS:  Connected to staging WebSocket on attempt {attempt + 1} ({connection_time:.2f}s)")
                
                # Start message listener
                asyncio.create_task(self._message_listener())
                
                return True
                
            except Exception as e:
                error_msg = f"Connection attempt {attempt + 1} failed: {str(e)}"
                logger.warning(error_msg)
                self.session.errors.append(error_msg)
                
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
        
        logger.error(f" FAIL:  Failed to establish WebSocket connection after {max_retries + 1} attempts")
        return False
    
    async def _message_listener(self) -> None:
        """Listen for WebSocket messages and dispatch to handlers."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    # Record event
                    self.session.events_received.append({
                        "data": data,
                        "timestamp": time.time(),
                        "received_at": datetime.now().isoformat()
                    })
                    
                    # Dispatch to event handlers
                    event_type = data.get("type", "unknown")
                    if event_type in self.event_callbacks:
                        for callback in self.event_callbacks[event_type]:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(data)
                                else:
                                    callback(data)
                            except Exception as e:
                                logger.error(f"Error in event callback for {event_type}: {e}")
                    
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
    
    def on_event(self, event_type: str, callback: Callable) -> None:
        """Register callback for specific event type."""
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        self.event_callbacks[event_type].append(callback)
    
    async def send_test_message(
        self,
        message_type: str,
        data: Dict[str, Any],
        thread_id: Optional[str] = None,
        track_latency: bool = True
    ) -> bool:
        """
        Send test message with latency tracking.
        
        Args:
            message_type: Type of message to send
            data: Message data
            thread_id: Thread ID for the message
            track_latency: Whether to track message latency
            
        Returns:
            True if message sent successfully
        """
        if not self.is_connected:
            logger.error("Cannot send message: not connected")
            return False
        
        try:
            send_time = time.time()
            thread_id = thread_id or f"test-{int(send_time)}"
            
            message = {
                "type": message_type,
                "timestamp": datetime.now().isoformat(),
                "thread_id": thread_id,
                "send_time": send_time,
                **data
            }
            
            await self.websocket.send(json.dumps(message))
            
            # Record sent message
            self.session.messages_sent.append({
                "message": message,
                "sent_at": send_time
            })
            
            if track_latency:
                self.message_latencies[f"{message_type}-{thread_id}"] = send_time
            
            logger.debug(f"[U+1F4E4] Sent {message_type} to thread {thread_id}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to send {message_type}: {e}"
            logger.error(error_msg)
            self.session.errors.append(error_msg)
            return False
    
    async def test_agent_flow_comprehensive(
        self,
        query: str,
        agent_type: str = "supervisor",
        timeout: float = 120.0
    ) -> Dict[str, Any]:
        """
        Test complete agent flow with comprehensive validation.
        
        Args:
            query: Query to send to agent
            agent_type: Type of agent to request
            timeout: Maximum time to wait for completion
            
        Returns:
            Comprehensive flow results
        """
        thread_id = f"agent-flow-{int(time.time())}"
        flow_start = time.time()
        
        logger.info(f"[U+1F916] Starting agent flow test: {query[:50]}...")
        
        # Track events for this flow
        flow_events = []
        
        def track_flow_event(data):
            if data.get("thread_id") == thread_id:
                flow_events.append({
                    "type": data.get("type"),
                    "timestamp": time.time(),
                    "data": data
                })
                logger.info(f"  [U+1F4E8] Flow event: {data.get('type')}")
        
        # Register event tracking
        required_events = [
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed"
        ]
        
        for event_type in required_events:
            self.on_event(event_type, track_flow_event)
        
        # Send agent request
        success = await self.send_test_message(
            "agent_request",
            {
                "query": query,
                "agent_type": agent_type,
                "test_flow": True
            },
            thread_id=thread_id
        )
        
        if not success:
            return {
                "success": False,
                "error": "Failed to send agent request",
                "events": flow_events
            }
        
        # Wait for flow completion
        completion_deadline = flow_start + timeout
        
        while time.time() < completion_deadline:
            # Check if we have completion event
            completion_events = [e for e in flow_events if e["type"] in ["agent_completed", "agent_error"]]
            if completion_events:
                break
                
            await asyncio.sleep(0.5)
        
        flow_duration = time.time() - flow_start
        
        # Analyze results
        event_types = {e["type"] for e in flow_events}
        missing_events = set(required_events) - event_types
        has_completion = bool(event_types & {"agent_completed", "agent_error"})
        
        return {
            "success": has_completion and len(missing_events) == 0,
            "duration": flow_duration,
            "events": flow_events,
            "event_types": list(event_types),
            "missing_events": list(missing_events),
            "total_events": len(flow_events),
            "thread_id": thread_id
        }
    
    async def disconnect(self) -> None:
        """Disconnect and cleanup."""
        # Cancel any waiting tasks
        for task in self.event_waiter_tasks:
            if not task.done():
                task.cancel()
        
        # Close WebSocket connection
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.websocket = None
                self.is_connected = False
        
        # Update session end time
        self.session.end_time = datetime.now()
        
        logger.info(f"[U+1F50C] Disconnected from staging WebSocket")
    
    def get_session_report(self) -> Dict[str, Any]:
        """Get comprehensive session report."""
        event_types = {}
        for event_record in self.session.events_received:
            event_type = event_record["data"].get("type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        return {
            "session_id": self.session.session_id,
            "duration": self.session.duration,
            "connection_attempts": self.session.connection_attempts,
            "successful_connections": self.session.successful_connections,
            "success_rate": self.session.success_rate,
            "events_received": len(self.session.events_received),
            "messages_sent": len(self.session.messages_sent),
            "event_types": event_types,
            "average_connection_time": (
                sum(self.connection_times) / len(self.connection_times)
                if self.connection_times else 0
            ),
            "errors": self.session.errors,
            "is_connected": self.is_connected
        }


@asynccontextmanager
async def staging_websocket_session(
    email: Optional[str] = None,
    name: Optional[str] = None,
    session_id: Optional[str] = None
) -> AsyncGenerator[StagingWebSocketTester, None]:
    """
    Context manager for staging WebSocket test session.
    
    Args:
        email: User email for authentication
        name: User name for authentication
        session_id: Optional session ID for tracking
        
    Yields:
        Configured and connected StagingWebSocketTester
    """
    tester = StagingWebSocketTester(session_id)
    
    try:
        # Setup authenticated connection
        connected = await tester.setup_authenticated_connection()
        if not connected:
            raise ConnectionError("Failed to establish staging WebSocket connection")
        
        yield tester
        
    finally:
        await tester.disconnect()


async def validate_staging_websocket_events(
    query: str = "Test WebSocket events in staging",
    timeout: float = 90.0,
    required_events: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    Validate WebSocket events in staging environment.
    
    Args:
        query: Query to send to agent
        timeout: Maximum time to wait
        required_events: Set of required event types
        
    Returns:
        Validation results
    """
    required_events = required_events or {
        "agent_started", "agent_thinking", "tool_executing", 
        "tool_completed", "agent_completed"
    }
    
    logger.info(f" SEARCH:  Validating staging WebSocket events with query: {query}")
    
    async with staging_websocket_session() as tester:
        # Test comprehensive agent flow
        flow_result = await tester.test_agent_flow_comprehensive(
            query=query,
            timeout=timeout
        )
        
        # Get session report
        session_report = tester.get_session_report()
        
        # Validate results
        validation_result = {
            "flow_success": flow_result["success"],
            "events_validated": set(flow_result["event_types"]) >= required_events,
            "missing_events": list(required_events - set(flow_result["event_types"])),
            "flow_duration": flow_result["duration"],
            "total_events": flow_result["total_events"],
            "session_report": session_report,
            "staging_ready": False
        }
        
        # Overall staging readiness
        validation_result["staging_ready"] = (
            flow_result["success"] and
            validation_result["events_validated"] and
            session_report["success_rate"] >= 0.8 and
            len(session_report["errors"]) == 0
        )
        
        return validation_result


async def run_staging_websocket_smoke_test() -> bool:
    """
    Run quick smoke test for staging WebSocket functionality.
    
    Returns:
        True if smoke test passes
    """
    logger.info(" FIRE:  Running staging WebSocket smoke test...")
    
    try:
        # Quick validation
        result = await validate_staging_websocket_events(
            query="Quick smoke test for staging WebSocket",
            timeout=45.0
        )
        
        if result["staging_ready"]:
            logger.info(" PASS:  Staging WebSocket smoke test PASSED")
            logger.info(f"  - Flow duration: {result['flow_duration']:.2f}s")
            logger.info(f"  - Events received: {result['total_events']}")
            logger.info(f"  - Connection success: {result['session_report']['success_rate']:.1%}")
            return True
        else:
            logger.error(" FAIL:  Staging WebSocket smoke test FAILED")
            if result["missing_events"]:
                logger.error(f"  - Missing events: {result['missing_events']}")
            if result["session_report"]["errors"]:
                logger.error(f"  - Errors: {result['session_report']['errors']}")
            return False
            
    except Exception as e:
        logger.error(f" FAIL:  Smoke test failed with exception: {e}")
        return False


async def debug_staging_websocket_connection() -> Dict[str, Any]:
    """
    Debug staging WebSocket connection issues.
    
    Returns:
        Debug information about connection
    """
    logger.info("[U+1F527] Debugging staging WebSocket connection...")
    
    debug_info = {
        "config_valid": False,
        "auth_working": False,
        "websocket_connectable": False,
        "ssl_valid": False,
        "headers_correct": False,
        "error_details": []
    }
    
    try:
        # Test configuration
        config = get_staging_config()
        debug_info["config_valid"] = config.validate_configuration()
        
        if not debug_info["config_valid"]:
            debug_info["error_details"].append("Staging configuration validation failed")
            return debug_info
        
        # Test authentication
        auth_client = StagingAuthClient()
        try:
            tokens = await auth_client.get_auth_token()
            debug_info["auth_working"] = bool(tokens.get("access_token"))
            
            if debug_info["auth_working"]:
                # Test WebSocket headers
                headers = config.get_websocket_headers(tokens["access_token"])
                debug_info["headers_correct"] = (
                    "Authorization" in headers and
                    headers["Authorization"].startswith("Bearer ")
                )
        except Exception as e:
            debug_info["error_details"].append(f"Authentication failed: {e}")
        
        # Test SSL/TLS for wss:// connections
        ws_url = config.urls.websocket_url
        if ws_url.startswith('wss://'):
            try:
                ssl_context = ssl.create_default_context()
                debug_info["ssl_valid"] = True
            except Exception as e:
                debug_info["error_details"].append(f"SSL context creation failed: {e}")
        else:
            debug_info["ssl_valid"] = True  # Not needed for ws://
        
        # Test WebSocket connection
        if debug_info["auth_working"] and debug_info["headers_correct"]:
            try:
                async with staging_websocket_session() as tester:
                    debug_info["websocket_connectable"] = tester.is_connected
            except Exception as e:
                debug_info["error_details"].append(f"WebSocket connection failed: {e}")
        
        return debug_info
        
    except Exception as e:
        debug_info["error_details"].append(f"Debug process failed: {e}")
        return debug_info


if __name__ == "__main__":
    # Run tests when executed directly
    async def main():
        print("[U+1F9EA] Testing Staging WebSocket Utilities")
        print("=" * 50)
        
        # Run debug first
        debug_info = await debug_staging_websocket_connection()
        print("\n[U+1F527] Debug Results:")
        for key, value in debug_info.items():
            if key != "error_details":
                status = " PASS: " if value else " FAIL: "
                print(f"  {status} {key}: {value}")
        
        if debug_info["error_details"]:
            print("\n FAIL:  Errors:")
            for error in debug_info["error_details"]:
                print(f"  - {error}")
        
        # Run smoke test if basic connectivity works
        if debug_info["websocket_connectable"]:
            print("\n FIRE:  Running smoke test...")
            smoke_passed = await run_staging_websocket_smoke_test()
            print(f"\n{' PASS: ' if smoke_passed else ' FAIL: '} Smoke test {'PASSED' if smoke_passed else 'FAILED'}")
        else:
            print("\n WARNING: [U+FE0F] Skipping smoke test due to connection issues")
    
    asyncio.run(main())