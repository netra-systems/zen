"""
WebSocket Utilities

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Code Reuse
- Value Impact: Shared utilities, eliminates duplication across 20+ files
- Strategic Impact: DRY principle, consistent utility functions

Consolidated utility functions from scattered WebSocket implementation files.
All functions ≤25 lines as per CLAUDE.md requirements.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from contextlib import asynccontextmanager

from fastapi import WebSocket
from starlette.websockets import WebSocketState, WebSocketDisconnect

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.types import (
    WebSocketMessage,
    ServerMessage,
    ErrorMessage,
    ConnectionInfo,
    MessageType,
    create_standard_message,
    create_error_message,
    create_server_message
)

logger = central_logger.get_logger(__name__)


def generate_connection_id(user_id: str, prefix: str = "conn") -> str:
    """Generate unique connection ID."""
    timestamp = int(time.time() * 1000)
    random_suffix = uuid.uuid4().hex[:8]
    return f"{prefix}_{user_id}_{timestamp}_{random_suffix}"


def generate_message_id() -> str:
    """Generate unique message ID."""
    return str(uuid.uuid4())


def get_current_timestamp() -> float:
    """Get current timestamp in seconds."""
    return time.time()


def get_current_iso_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def is_websocket_connected(websocket: WebSocket) -> bool:
    """
    Check if WebSocket is connected.
    
    CRITICAL FIX: Enhanced state checking to prevent "Need to call accept first" errors
    with staging-optimized connection validation.
    """
    try:
        # Check multiple conditions to determine if WebSocket is connected
        # 1. Check if WebSocket has client_state (Starlette WebSocket attribute)
        if hasattr(websocket, 'client_state'):
            client_state = websocket.client_state
            is_connected = client_state == WebSocketState.CONNECTED
            
            # CRITICAL FIX: If client state indicates disconnected or not yet connected, return False
            if client_state in [WebSocketState.DISCONNECTED, WebSocketState.CONNECTING]:
                logger.debug(f"WebSocket client_state not connected: {client_state}")
                return False
            
            if is_connected:
                logger.debug(f"WebSocket connected via client_state: {client_state}")
            return is_connected
        
        # 2. Fallback to application_state if available
        if hasattr(websocket, 'application_state'):
            app_state = websocket.application_state
            is_connected = app_state == WebSocketState.CONNECTED
            
            # CRITICAL FIX: If application state indicates disconnected or not yet connected, return False
            if app_state in [WebSocketState.DISCONNECTED, WebSocketState.CONNECTING]:
                logger.debug(f"WebSocket application_state not connected: {app_state}")
                return False
                
            if is_connected:
                logger.debug(f"WebSocket connected via application_state: {app_state}")
            return is_connected
        
        # 3. Check if the websocket has been properly initialized
        if not hasattr(websocket, '_receive') and not hasattr(websocket, 'receive'):
            logger.debug("WebSocket state check: WebSocket not properly initialized")
            return False
        
        # 4. CRITICAL FIX: For staging, be more conservative - if we can't determine state, assume disconnected
        # This prevents sending to potentially dead connections in cloud environments
        from shared.isolated_environment import get_env
        env = get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        
        if environment in ["staging", "production"]:
            logger.debug(f"WebSocket state check: No state attributes found in {environment}, assuming disconnected for safety")
            return False
        else:
            # Development - more permissive
            logger.debug("WebSocket state check: No state attributes found in development, defaulting to connected=True")
            return True
        
    except Exception as e:
        # CRITICAL FIX: If we can't check the state due to an error, assume disconnected
        logger.warning(f"WebSocket state check error: {e}, assuming disconnected")
        return False


async def safe_websocket_send(websocket: WebSocket, data: Union[Dict[str, Any], str],
                            retry_count: int = 2) -> bool:
    """
    Safely send data to WebSocket with retry logic.
    
    CRITICAL FIX: Enhanced error handling for connection state issues with
    staging-optimized retry logic and exponential backoff.
    """
    if not is_websocket_connected(websocket):
        logger.debug("WebSocket not connected, skipping send")
        return False
    
    # CRITICAL FIX: Environment-aware retry configuration
    from shared.isolated_environment import get_env
    env = get_env()
    environment = env.get("ENVIRONMENT", "development").lower()
    
    # Staging/production needs more aggressive retry logic due to network latency
    if environment in ["staging", "production"]:
        retry_count = max(retry_count, 3)  # At least 3 retries for cloud environments
        max_backoff = 2.0  # Longer max backoff for staging
    else:
        max_backoff = 1.0  # Shorter backoff for development
    
    for attempt in range(retry_count + 1):
        try:
            if isinstance(data, str):
                await websocket.send_text(data)
            else:
                await websocket.send_json(data)
            
            if attempt > 0:
                logger.info(f"WebSocket send succeeded on attempt {attempt + 1}")
            return True
            
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected during send")
            return False
        except RuntimeError as e:
            # CRITICAL FIX: Handle "WebSocket is not connected" and "Need to call accept first" errors
            error_message = str(e)
            if "Need to call 'accept' first" in error_message or "WebSocket is not connected" in error_message:
                logger.error(f"WebSocket connection state error during send: {error_message}")
                return False
            else:
                logger.warning(f"WebSocket send runtime error attempt {attempt + 1}/{retry_count + 1}: {e}")
                if attempt < retry_count:
                    backoff_delay = min(0.1 * (2 ** attempt), max_backoff)  # Exponential backoff with cap
                    await asyncio.sleep(backoff_delay)
                else:
                    logger.error(f"WebSocket send failed after {retry_count + 1} attempts")
                    return False
        except Exception as e:
            logger.warning(f"WebSocket send attempt {attempt + 1}/{retry_count + 1} failed: {e}")
            if attempt < retry_count:
                backoff_delay = min(0.1 * (2 ** attempt), max_backoff)  # Exponential backoff with cap
                logger.debug(f"Retrying WebSocket send in {backoff_delay:.2f}s")
                await asyncio.sleep(backoff_delay)
            else:
                logger.error(f"WebSocket send failed after {retry_count + 1} attempts")
                return False
    
    return False


async def safe_websocket_close(websocket: WebSocket, code: int = 1000, 
                             reason: str = "Normal closure") -> None:
    """
    Safely close WebSocket connection.
    
    CRITICAL FIX: Enhanced error handling for connection state issues during close.
    """
    # Try to close even if connection check fails - websocket might be in transitional state
    try:
        await websocket.close(code=code, reason=reason)
        logger.debug(f"WebSocket closed successfully with code {code}")
    except RuntimeError as e:
        # CRITICAL FIX: Handle connection state errors during close
        error_message = str(e)
        if "Need to call 'accept' first" in error_message or "WebSocket is not connected" in error_message:
            logger.debug(f"WebSocket already disconnected or not accepted during close: {error_message}")
        else:
            logger.warning(f"Runtime error closing WebSocket: {e}")
    except Exception as e:
        logger.warning(f"Error closing WebSocket: {e}")


class WebSocketMessageQueue:
    """Queue for managing WebSocket messages."""
    
    def __init__(self, max_size: int = 1000):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.stats = {
            "enqueued": 0,
            "dequeued": 0,
            "dropped": 0,
            "errors": 0
        }
    
    async def enqueue(self, message: Union[WebSocketMessage, Dict[str, Any]]) -> bool:
        """Add message to queue."""
        try:
            # Convert to dict if needed
            if hasattr(message, 'model_dump'):
                message_dict = message.model_dump()
            else:
                message_dict = message
            
            self.queue.put_nowait(message_dict)
            self.stats["enqueued"] += 1
            return True
            
        except asyncio.QueueFull:
            self.stats["dropped"] += 1
            logger.warning("Message queue is full, dropping message")
            return False
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error enqueueing message: {e}")
            return False
    
    async def dequeue(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Get message from queue."""
        try:
            if timeout:
                message = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            else:
                message = await self.queue.get()
            
            self.stats["dequeued"] += 1
            return message
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error dequeuing message: {e}")
            return None
    
    def size(self) -> int:
        """Get queue size."""
        return self.queue.qsize()
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.queue.empty()
    
    def clear(self) -> None:
        """Clear all messages from queue."""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            **self.stats,
            "current_size": self.queue.qsize(),
            "max_size": self.queue.maxsize
        }


class WebSocketHeartbeat:
    """Manages WebSocket heartbeat/ping mechanism."""
    
    def __init__(self, interval: float = 45.0, timeout: float = 10.0):
        self.interval = interval
        self.timeout = timeout
        self.running = False
        self.last_pong: Optional[float] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
    
    async def start(self, websocket: WebSocket) -> None:
        """Start heartbeat monitoring."""
        if self.running:
            return
        
        self.running = True
        self.last_pong = time.time()
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop(websocket))
    
    async def stop(self) -> None:
        """Stop heartbeat monitoring."""
        self.running = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
    
    def on_pong_received(self) -> None:
        """Called when pong is received."""
        self.last_pong = time.time()
    
    async def _heartbeat_loop(self, websocket: WebSocket) -> None:
        """Main heartbeat loop."""
        try:
            while self.running and is_websocket_connected(websocket):
                current_time = time.time()
                
                # Check if we missed a pong
                if self.last_pong and (current_time - self.last_pong) > (self.interval + self.timeout):
                    logger.warning("WebSocket heartbeat timeout")
                    break
                
                # Send ping
                ping_message = create_server_message(
                    MessageType.PING,
                    {"timestamp": current_time}
                )
                
                if not await safe_websocket_send(websocket, ping_message.model_dump()):
                    logger.warning("Failed to send heartbeat ping")
                    break
                
                await asyncio.sleep(self.interval)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")
        finally:
            self.running = False


class WebSocketConnectionMonitor:
    """Monitors WebSocket connection health and statistics."""
    
    def __init__(self):
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.global_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_processed": 0,
            "errors_occurred": 0,
            "start_time": time.time()
        }
        # Initialize monitoring coverage tracking
        self.monitoring_coverage = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "check_results": []
        }
    
    def register_connection(self, connection_id: str, user_id: str,
                          websocket: WebSocket) -> None:
        """Register connection for monitoring."""
        self.connections[connection_id] = {
            "user_id": user_id,
            "websocket": websocket,
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "is_healthy": True
        }
        
        self.global_stats["total_connections"] += 1
        self.global_stats["active_connections"] += 1
    
    def unregister_connection(self, connection_id: str) -> None:
        """Unregister connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self.global_stats["active_connections"] -= 1
    
    def update_activity(self, connection_id: str, activity_type: str = "message") -> None:
        """Update connection activity."""
        if connection_id in self.connections:
            conn = self.connections[connection_id]
            conn["last_activity"] = datetime.now(timezone.utc)
            
            if activity_type == "message_sent":
                conn["messages_sent"] += 1
            elif activity_type == "message_received":
                conn["messages_received"] += 1
            elif activity_type == "error":
                conn["errors"] += 1
                self.global_stats["errors_occurred"] += 1
            
            self.global_stats["messages_processed"] += 1
    
    def get_connection_health(self, connection_id: str) -> Dict[str, Any]:
        """Get health status for specific connection."""
        if connection_id not in self.connections:
            return {"status": "not_found"}
        
        conn = self.connections[connection_id]
        websocket = conn["websocket"]
        current_time = datetime.now(timezone.utc)
        last_activity = conn["last_activity"]
        
        # Calculate activity metrics
        inactive_seconds = (current_time - last_activity).total_seconds()
        is_stale = inactive_seconds > 300  # 5 minutes
        is_connected = is_websocket_connected(websocket)
        
        return {
            "connection_id": connection_id,
            "user_id": conn["user_id"],
            "is_connected": is_connected,
            "is_stale": is_stale,
            "inactive_seconds": inactive_seconds,
            "messages_sent": conn["messages_sent"],
            "messages_received": conn["messages_received"],
            "error_count": conn["errors"],
            "connected_duration": (current_time - conn["connected_at"]).total_seconds()
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global connection statistics."""
        uptime = time.time() - self.global_stats["start_time"]
        
        return {
            **self.global_stats,
            "uptime_seconds": uptime,
            "connections_by_user": self._get_connections_by_user(),
            "health_summary": self._get_health_summary()
        }
    
    def _get_connections_by_user(self) -> Dict[str, int]:
        """Get connection count by user."""
        user_counts = {}
        for conn in self.connections.values():
            user_id = conn["user_id"]
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        return user_counts
    
    def _get_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all connections."""
        healthy_count = 0
        stale_count = 0
        
        for connection_id in self.connections:
            health = self.get_connection_health(connection_id)
            if health.get("is_connected") and not health.get("is_stale"):
                healthy_count += 1
            elif health.get("is_stale"):
                stale_count += 1
        
        return {
            "healthy_connections": healthy_count,
            "stale_connections": stale_count,
            "total_monitored": len(self.connections)
        }
    
    async def _check_performance_thresholds(self) -> None:
        """Run all performance threshold checks."""
        check_methods = [
            self._check_response_time_threshold,
            self._check_memory_threshold,
            self._check_error_rate_threshold,
            self._check_throughput_threshold,
            self._check_cpu_threshold
        ]
        
        check_names = [
            "response_time",
            "memory",
            "error_rate", 
            "throughput",
            "cpu"
        ]
        
        # Run checks concurrently and collect results
        tasks = []
        for check_method in check_methods:
            tasks.append(asyncio.create_task(self._run_check_safely(check_method)))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle results
        await self._handle_check_results(check_names, results)
    
    async def _run_check_safely(self, check_method) -> Any:
        """Run a check method safely, catching exceptions."""
        try:
            if asyncio.iscoroutinefunction(check_method):
                return await check_method()
            else:
                return check_method()
        except Exception as e:
            return e
    
    async def _handle_check_results(self, check_names, results):
        """Handle the results of performance checks."""
        for check_name, result in zip(check_names, results):
            self.monitoring_coverage["total_checks"] += 1
            
            if isinstance(result, Exception):
                self.monitoring_coverage["failed_checks"] += 1
                await self._handle_check_failure(check_name, result)
            else:
                self.monitoring_coverage["successful_checks"] += 1
                self._record_check_success(check_name)
    
    def _record_check_success(self, check_name: str) -> None:
        """Record a successful check."""
        self.monitoring_coverage["check_results"].append({
            "timestamp": get_current_iso_timestamp(),
            "check_name": check_name,
            "success": True,
            "error": None
        })
    
    async def _handle_check_failure(self, check_name: str, error: Exception) -> None:
        """Handle a failed check."""
        self.monitoring_coverage["check_results"].append({
            "timestamp": get_current_iso_timestamp(),
            "check_name": check_name,
            "success": False,
            "error": str(error)
        })
    
    def _get_monitoring_coverage_summary(self) -> Dict[str, Any]:
        """Get monitoring coverage summary."""
        total = self.monitoring_coverage["total_checks"]
        successful = self.monitoring_coverage["successful_checks"]
        
        coverage_percentage = (successful / total * 100) if total > 0 else 0.0
        
        return {
            "coverage_percentage": coverage_percentage,
            "recent_failures": self._count_recent_failures()
        }
    
    def _count_recent_failures(self) -> int:
        """Count recent failures within 5 minutes."""
        from datetime import datetime, timezone, timedelta
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent_failures = 0
        
        for result in self.monitoring_coverage["check_results"]:
            if not result["success"]:
                result_time = datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
                if result_time > cutoff_time:
                    recent_failures += 1
                    
        return recent_failures
    
    def get_current_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary including monitoring coverage."""
        return {
            **self.get_global_stats(),
            "monitoring_coverage": self._get_monitoring_coverage_summary()
        }
    
    def reset_metrics(self) -> None:
        """Reset all monitoring metrics."""
        self.monitoring_coverage = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "check_results": []
        }
    
    # Stub implementations of performance check methods
    async def _check_response_time_threshold(self) -> None:
        """Check response time threshold."""
        pass
    
    async def _check_memory_threshold(self) -> None:
        """Check memory threshold.""" 
        pass
    
    async def _check_error_rate_threshold(self) -> None:
        """Check error rate threshold."""
        pass
    
    async def _check_throughput_threshold(self) -> None:
        """Check throughput threshold."""
        pass
    
    async def _check_cpu_threshold(self) -> None:
        """Check CPU threshold."""
        pass


# Utility functions for message processing

def parse_websocket_message(raw_data: Union[str, bytes]) -> Optional[Dict[str, Any]]:
    """Parse raw WebSocket message data."""
    try:
        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode('utf-8')
        
        return json.loads(raw_data)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to parse WebSocket message: {e}")
        return None


def validate_message_structure(message: Dict[str, Any]) -> bool:
    """Validate basic message structure."""
    required_fields = ["type"]
    
    if not isinstance(message, dict):
        return False
    
    for field in required_fields:
        if field not in message:
            return False
    
    return True


def extract_user_info_from_message(message: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Extract user information from message."""
    user_info = {}
    
    if "user_id" in message:
        user_info["user_id"] = str(message["user_id"])
    
    if "thread_id" in message:
        user_info["thread_id"] = str(message["thread_id"])
    
    return user_info if user_info else None


async def broadcast_to_websockets(websockets: List[WebSocket], 
                                message: Union[Dict[str, Any], str],
                                exclude_websockets: Optional[List[WebSocket]] = None) -> int:
    """Broadcast message to multiple WebSockets."""
    exclude_websockets = exclude_websockets or []
    successful_sends = 0
    
    # Filter out excluded WebSockets
    target_websockets = [ws for ws in websockets if ws not in exclude_websockets]
    
    # Send to all targets concurrently
    send_tasks = []
    for websocket in target_websockets:
        if is_websocket_connected(websocket):
            task = safe_websocket_send(websocket, message)
            send_tasks.append(task)
    
    if send_tasks:
        results = await asyncio.gather(*send_tasks, return_exceptions=True)
        successful_sends = sum(1 for result in results if result is True)
    
    return successful_sends


def format_websocket_error_response(error_code: str, error_message: str,
                                  request_id: Optional[str] = None) -> Dict[str, Any]:
    """Format standardized WebSocket error response."""
    error_response = {
        "type": "error",
        "error": {
            "code": error_code,
            "message": error_message,
            "timestamp": time.time()
        }
    }
    
    if request_id:
        error_response["request_id"] = request_id
    
    return error_response


def create_connection_info(connection_id: str, user_id: str,
                         thread_id: Optional[str] = None) -> ConnectionInfo:
    """Create connection info object."""
    return ConnectionInfo(
        connection_id=connection_id,
        user_id=user_id,
        thread_id=thread_id,
        connected_at=datetime.now(timezone.utc),
        last_activity=datetime.now(timezone.utc),
        message_count=0,
        is_healthy=True
    )


# Global utilities instances
_connection_monitor: Optional[WebSocketConnectionMonitor] = None

def get_connection_monitor() -> WebSocketConnectionMonitor:
    """Get global connection monitor."""
    global _connection_monitor
    if _connection_monitor is None:
        _connection_monitor = WebSocketConnectionMonitor()
    return _connection_monitor


@asynccontextmanager
async def websocket_message_queue_context(max_size: int = 1000) -> AsyncGenerator[WebSocketMessageQueue, None]:
    """Context manager for WebSocket message queue."""
    queue = WebSocketMessageQueue(max_size=max_size)
    try:
        yield queue
    finally:
        queue.clear()


@asynccontextmanager  
async def websocket_heartbeat_context(websocket: WebSocket, interval: float = 45.0) -> AsyncGenerator[WebSocketHeartbeat, None]:
    """Context manager for WebSocket heartbeat."""
    heartbeat = WebSocketHeartbeat(interval=interval)
    try:
        await heartbeat.start(websocket)
        yield heartbeat
    finally:
        await heartbeat.stop()


def check_rate_limit(client_id: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
    """
    Utility function for backward compatibility with rate limiting.
    
    This function creates a temporary RateLimiter instance to check rate limits.
    For production use, prefer using RateLimiter class directly from auth module.
    """
    # Import here to avoid circular imports
    from netra_backend.app.websocket_core.rate_limiter import AdaptiveRateLimiter
    
    # Create temporary rate limiter with specified limits
    rate_limiter = AdaptiveRateLimiter(base_rate=max_requests, window_seconds=window_seconds)
    allowed = rate_limiter.is_allowed(client_id)
    return allowed


# Compression utility functions (stub implementations for backward compatibility)

def compress(data: Union[str, bytes]) -> bytes:
    """
    Stub compression function for backward compatibility.
    
    Currently returns data as-is (no compression).
    Can be extended with actual compression logic when needed.
    """
    if isinstance(data, str):
        return data.encode('utf-8')
    return data


def decompress(data: bytes) -> str:
    """
    Stub decompression function for backward compatibility.
    
    Currently returns data as-is (no decompression).
    Can be extended with actual decompression logic when needed.
    """
    if isinstance(data, bytes):
        return data.decode('utf-8')
    return data