"""
SSOT WebSocket Golden Path Helpers - Single Source of Truth for WebSocket Golden Path Testing

This module provides the CANONICAL helper class for testing the golden path user flow
through WebSocket agent events that deliver 90% of business value ($500K+ ARR).

Business Value Justification (BVJ):
- Segment: Platform/Internal - Core Chat Infrastructure  
- Business Goal: Revenue Protection - Ensure golden path delivers substantive AI chat value
- Value Impact: Validates end-to-end user journey that generates customer conversions
- Strategic Impact: Protects the primary revenue-generating flow through AI chat interactions

GOLDEN PATH DEFINITION:
The "golden path" is the optimal user experience flow:
1. User sends message → WebSocket connection established with authentication
2. Agent starts processing → agent_started event (user sees AI is working)
3. Agent analyzes request → agent_thinking event (real-time progress visibility)
4. Agent executes tools → tool_executing event (demonstrates problem-solving)
5. Tools return results → tool_completed event (actionable insights delivered)
6. Agent synthesizes response → agent_completed event (valuable response ready)
7. User receives complete AI response with insights and actions

This flow represents the CORE VALUE PROPOSITION of the platform.

COMPLIANCE:
@compliance CLAUDE.md - WebSocket events enable substantive chat interactions (Section 6)
@compliance SPEC/core.xml - Single Source of Truth patterns
@compliance SPEC/type_safety.xml - Strongly typed WebSocket testing
"""

import asyncio
import json
import time
import uuid
import websockets
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Set, Optional, Union, AsyncGenerator, Callable, Tuple
from loguru import logger

# Import SSOT dependencies
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.ssot.agent_event_validators import (
    AgentEventValidator, 
    AgentEventValidationResult,
    WebSocketEventMessage,
    CriticalAgentEventType,
    assert_critical_events_received
)


@dataclass 
class GoldenPathTestConfig:
    """Configuration for golden path WebSocket testing."""
    websocket_url: str = "ws://localhost:8000/ws"
    connection_timeout: float = 30.0
    event_timeout: float = 45.0
    max_retries: int = 3
    enable_performance_monitoring: bool = True
    require_all_critical_events: bool = True
    validate_event_sequence: bool = True
    validate_event_timing: bool = True
    validate_business_value: bool = True
    
    @classmethod
    def for_staging(cls) -> 'GoldenPathTestConfig':
        """Create configuration optimized for staging environment."""
        return cls(
            websocket_url="wss://netra-staging.com/ws",
            connection_timeout=45.0,  # Longer timeout for GCP Cloud Run
            event_timeout=60.0,
            max_retries=5,  # More retries for staging flakiness
            enable_performance_monitoring=True,
            require_all_critical_events=True,
            validate_event_sequence=True,
            validate_event_timing=True,
            validate_business_value=True
        )
    
    @classmethod
    def for_environment(cls, environment: str = "test") -> 'GoldenPathTestConfig':
        """Create configuration for specified environment."""
        if environment.lower() == "staging":
            return cls.for_staging()
        return cls()


@dataclass
class GoldenPathExecutionMetrics:
    """Metrics for golden path execution performance."""
    connection_time: float = 0.0
    first_event_time: float = 0.0
    last_event_time: float = 0.0
    total_execution_time: float = 0.0
    events_received_count: int = 0
    critical_events_received_count: int = 0
    business_value_score: float = 0.0
    user_experience_rating: str = "UNKNOWN"  # EXCELLENT, GOOD, FAIR, POOR, FAILED
    throughput_events_per_second: float = 0.0
    error_count: int = 0
    retry_count: int = 0
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.total_execution_time > 0:
            self.throughput_events_per_second = self.events_received_count / self.total_execution_time
        
        # Determine user experience rating based on metrics
        if self.critical_events_received_count >= 5 and self.total_execution_time <= 10.0:
            self.user_experience_rating = "EXCELLENT"
        elif self.critical_events_received_count >= 5 and self.total_execution_time <= 20.0:
            self.user_experience_rating = "GOOD"
        elif self.critical_events_received_count >= 4 and self.total_execution_time <= 30.0:
            self.user_experience_rating = "FAIR"
        elif self.critical_events_received_count >= 3:
            self.user_experience_rating = "POOR"
        else:
            self.user_experience_rating = "FAILED"


@dataclass
class GoldenPathTestResult:
    """Complete result of a golden path test execution."""
    success: bool
    user_context: StronglyTypedUserExecutionContext
    validation_result: AgentEventValidationResult
    execution_metrics: GoldenPathExecutionMetrics
    events_received: List[WebSocketEventMessage] = field(default_factory=list)
    errors_encountered: List[str] = field(default_factory=list)
    warnings_generated: List[str] = field(default_factory=list)
    test_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    environment: str = "test"
    
    @property
    def revenue_impact_assessment(self) -> str:
        """Assess potential revenue impact of test result."""
        if self.success and self.execution_metrics.user_experience_rating in ["EXCELLENT", "GOOD"]:
            return "NO_IMPACT"  # Golden path working optimally
        elif self.success and self.execution_metrics.user_experience_rating == "FAIR":
            return "LOW_IMPACT"  # Some performance degradation
        elif self.execution_metrics.user_experience_rating == "POOR":
            return "MEDIUM_IMPACT"  # Noticeable UX issues
        else:
            return "HIGH_IMPACT"  # Major failures affecting revenue


class WebSocketGoldenPathHelper:
    """
    SSOT Helper class for testing WebSocket golden path user flows.
    
    This helper provides comprehensive testing of the end-to-end golden path
    that delivers 90% of platform business value through AI chat interactions.
    
    Key Features:
    - Authenticated WebSocket connection management  
    - Golden path flow execution and validation
    - Real-time event capture and validation
    - Performance metrics and business value scoring
    - Multi-user concurrent testing support
    - Comprehensive error handling and retries
    
    CRITICAL: This helper validates the PRIMARY REVENUE-GENERATING FLOW.
    If golden path tests fail, the core platform value proposition is broken.
    """
    
    def __init__(self, 
                 config: Optional[GoldenPathTestConfig] = None,
                 environment: str = "test"):
        """
        Initialize WebSocket golden path helper.
        
        Args:
            config: Optional golden path test configuration
            environment: Test environment ('test', 'staging', etc.)
        """
        self.environment = environment
        self.config = config or GoldenPathTestConfig.for_environment(environment)
        self.env = get_env()
        
        # Authentication helper
        self.auth_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Event validation
        self.event_validator: Optional[AgentEventValidator] = None
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.connection_start_time: Optional[float] = None
        
        # Event capture
        self.captured_events: List[WebSocketEventMessage] = []
        self.event_capture_start_time: Optional[float] = None
        
        # Performance tracking
        self.metrics = GoldenPathExecutionMetrics()
        
        logger.info(f"WebSocketGoldenPathHelper initialized for {environment} environment")
    
    @asynccontextmanager
    async def authenticated_websocket_connection(
        self, 
        user_context: Optional[StronglyTypedUserExecutionContext] = None
    ) -> AsyncGenerator['WebSocketGoldenPathHelper', None]:
        """
        Context manager for authenticated WebSocket connection.
        
        Args:
            user_context: Optional user execution context
            
        Yields:
            Self with established WebSocket connection
        """
        connection_start = time.time()
        
        try:
            # Establish authenticated connection
            await self._establish_authenticated_connection(user_context)
            self.metrics.connection_time = time.time() - connection_start
            
            # Initialize event validation
            self.event_validator = AgentEventValidator(
                user_context=user_context,
                strict_mode=self.config.require_all_critical_events,
                timeout_seconds=self.config.event_timeout
            )
            
            # Start event capture
            self.event_capture_start_time = time.time()
            
            logger.success(f"Authenticated WebSocket connection established in {self.metrics.connection_time:.2f}s")
            yield self
            
        except Exception as e:
            logger.error(f"Failed to establish authenticated WebSocket connection: {e}")
            self.metrics.error_count += 1
            raise
        finally:
            await self._cleanup_connection()
    
    async def _establish_authenticated_connection(
        self, 
        user_context: Optional[StronglyTypedUserExecutionContext] = None
    ) -> None:
        """Establish authenticated WebSocket connection."""
        self.connection_start_time = time.time()
        
        # Get authentication headers
        headers = self.auth_helper.get_websocket_headers()
        
        # Add user context headers if provided
        if user_context:
            headers.update({
                "X-User-ID": str(user_context.user_id),
                "X-Thread-ID": str(user_context.thread_id),
                "X-Request-ID": str(user_context.request_id),
                "X-Run-ID": str(user_context.run_id)
            })
            if user_context.websocket_client_id:
                headers["X-WebSocket-Client-ID"] = str(user_context.websocket_client_id)
        
        # Connect with timeout and retry logic
        retry_count = 0
        while retry_count <= self.config.max_retries:
            try:
                logger.info(f"Connecting to WebSocket (attempt {retry_count + 1}/{self.config.max_retries + 1})")
                
                self.websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.config.websocket_url,
                        additional_headers=headers,
                        ping_interval=20,
                        ping_timeout=10,
                        close_timeout=5
                    ),
                    timeout=self.config.connection_timeout
                )
                
                self.is_connected = True
                logger.success("WebSocket connection established with authentication")
                return
                
            except asyncio.TimeoutError:
                retry_count += 1
                self.metrics.retry_count = retry_count
                if retry_count > self.config.max_retries:
                    raise TimeoutError(f"WebSocket connection timeout after {retry_count} attempts")
                
                logger.warning(f"Connection attempt {retry_count} timed out, retrying...")
                await asyncio.sleep(min(retry_count * 2, 10))  # Exponential backoff
                
            except Exception as e:
                retry_count += 1
                self.metrics.retry_count = retry_count
                if retry_count > self.config.max_retries:
                    raise
                
                logger.warning(f"Connection attempt {retry_count} failed: {e}, retrying...")
                await asyncio.sleep(min(retry_count * 2, 10))
    
    async def _cleanup_connection(self) -> None:
        """Clean up WebSocket connection."""
        if self.websocket and self.is_connected:
            try:
                await self.websocket.close()
                logger.debug("WebSocket connection closed")
            except Exception as e:
                logger.warning(f"Error closing WebSocket connection: {e}")
        
        self.is_connected = False
        self.websocket = None
    
    async def send_golden_path_request(
        self, 
        user_message: str = "Please help me with a test request that involves data analysis",
        user_context: Optional[StronglyTypedUserExecutionContext] = None
    ) -> Dict[str, Any]:
        """
        Send a request that triggers the golden path agent flow.
        
        Args:
            user_message: User message to send
            user_context: Optional user execution context
            
        Returns:
            The message that was sent
        """
        if not self.is_connected or not self.websocket:
            raise RuntimeError("WebSocket connection not established")
        
        # Create golden path request message
        message = {
            "type": "message",
            "content": user_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message_id": f"golden_path_{uuid.uuid4().hex[:8]}"
        }
        
        # Add user context if provided
        if user_context:
            message.update({
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id),
                "request_id": str(user_context.request_id),
                "run_id": str(user_context.run_id)
            })
        
        # Send message
        try:
            await self.websocket.send(json.dumps(message))
            logger.info(f"Golden path request sent: {message['message_id']}")
            return message
            
        except Exception as e:
            logger.error(f"Failed to send golden path request: {e}")
            self.metrics.error_count += 1
            raise
    
    async def capture_events_with_timeout(
        self, 
        timeout: Optional[float] = None,
        required_events: Optional[Set[str]] = None
    ) -> List[WebSocketEventMessage]:
        """
        Capture WebSocket events with timeout.
        
        Args:
            timeout: Timeout in seconds (uses config default if not provided)
            required_events: Set of required event types to wait for
            
        Returns:
            List of captured WebSocketEventMessage instances
        """
        timeout = timeout or self.config.event_timeout
        required_events = required_events or {
            CriticalAgentEventType.AGENT_STARTED.value,
            CriticalAgentEventType.AGENT_THINKING.value,
            CriticalAgentEventType.TOOL_EXECUTING.value,
            CriticalAgentEventType.TOOL_COMPLETED.value,
            CriticalAgentEventType.AGENT_COMPLETED.value
        }
        
        if not self.is_connected or not self.websocket:
            raise RuntimeError("WebSocket connection not established")
        
        capture_start = time.time()
        captured_events = []
        received_event_types = set()
        first_event_received = False
        
        logger.info(f"Starting event capture (timeout: {timeout}s, required: {len(required_events)} events)")
        
        try:
            while time.time() - capture_start < timeout:
                try:
                    # Wait for message with short timeout to allow checking overall timeout
                    raw_message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=1.0
                    )
                    
                    # Parse message
                    try:
                        message_data = json.loads(raw_message)
                        event = WebSocketEventMessage.from_dict(message_data)
                        
                        # Record timing for first event
                        if not first_event_received:
                            self.metrics.first_event_time = time.time() - capture_start
                            first_event_received = True
                        
                        # Store event
                        captured_events.append(event)
                        self.captured_events.append(event)
                        received_event_types.add(event.event_type)
                        
                        # Record in validator
                        if self.event_validator:
                            self.event_validator.record_event(event)
                        
                        # Check if we have all required events
                        if required_events.issubset(received_event_types):
                            logger.success(f"All {len(required_events)} required events received!")
                            break
                        
                        logger.debug(f"Event received: {event.event_type} ({len(received_event_types)}/{len(required_events)})")
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON in WebSocket message: {e}")
                        continue
                    
                except asyncio.TimeoutError:
                    # Short timeout expired, continue checking overall timeout
                    continue
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed during event capture")
                    break
        
        except Exception as e:
            logger.error(f"Error during event capture: {e}")
            self.metrics.error_count += 1
        
        # Update metrics
        capture_duration = time.time() - capture_start
        self.metrics.last_event_time = capture_duration
        self.metrics.total_execution_time = capture_duration
        self.metrics.events_received_count = len(captured_events)
        self.metrics.critical_events_received_count = len(
            [e for e in captured_events if e.event_type in required_events]
        )
        
        # Check for missing events
        missing_events = required_events - received_event_types
        if missing_events:
            logger.warning(f"Missing required events after {timeout}s: {missing_events}")
        
        logger.info(f"Event capture completed: {len(captured_events)} events in {capture_duration:.2f}s")
        return captured_events
    
    async def execute_golden_path_flow(
        self,
        user_message: str = "Please analyze some sample data and provide insights",
        user_context: Optional[StronglyTypedUserExecutionContext] = None,
        timeout: Optional[float] = None
    ) -> GoldenPathTestResult:
        """
        Execute complete golden path flow and validate results.
        
        Args:
            user_message: User message to trigger flow
            user_context: Optional user execution context
            timeout: Optional timeout override
            
        Returns:
            GoldenPathTestResult with complete validation and metrics
        """
        flow_start = time.time()
        errors = []
        warnings = []
        
        try:
            # Send golden path request
            sent_message = await self.send_golden_path_request(user_message, user_context)
            
            # Capture events
            captured_events = await self.capture_events_with_timeout(timeout)
            
            # Perform validation
            if self.event_validator:
                validation_result = self.event_validator.perform_full_validation()
            else:
                # Fallback validation if validator not initialized
                from test_framework.ssot.agent_event_validators import validate_agent_events
                validation_result = validate_agent_events(
                    [event.to_dict() for event in captured_events],
                    user_context=user_context,
                    strict_mode=self.config.require_all_critical_events
                )
            
            # Update final metrics
            self.metrics.total_execution_time = time.time() - flow_start
            self.metrics.business_value_score = validation_result.business_value_score
            
            # Determine success
            success = (
                validation_result.is_valid and 
                self.metrics.error_count == 0 and
                len(captured_events) > 0
            )
            
            # Create result
            result = GoldenPathTestResult(
                success=success,
                user_context=user_context or StronglyTypedUserExecutionContext(
                    user_id=UserID("test-user"),
                    thread_id=ThreadID("test-thread"),
                    run_id=RunID("test-run"),
                    request_id=RequestID("test-request")
                ),
                validation_result=validation_result,
                execution_metrics=self.metrics,
                events_received=captured_events,
                errors_encountered=errors,
                warnings_generated=warnings,
                environment=self.environment
            )
            
            # Log result summary
            if success:
                logger.success(
                    f"Golden path execution SUCCESS - "
                    f"UX Rating: {self.metrics.user_experience_rating}, "
                    f"Business Value: {validation_result.business_value_score:.1f}%, "
                    f"Duration: {self.metrics.total_execution_time:.2f}s"
                )
            else:
                logger.error(
                    f"Golden path execution FAILED - "
                    f"Revenue Impact: {validation_result.revenue_impact}, "
                    f"Missing Events: {validation_result.missing_critical_events}, "
                    f"Error Count: {self.metrics.error_count}"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Golden path execution failed with exception: {e}")
            errors.append(str(e))
            self.metrics.error_count += 1
            
            # Create failure result
            return GoldenPathTestResult(
                success=False,
                user_context=user_context or StronglyTypedUserExecutionContext(
                    user_id=UserID("test-user"),
                    thread_id=ThreadID("test-thread"), 
                    run_id=RunID("test-run"),
                    request_id=RequestID("test-request")
                ),
                validation_result=AgentEventValidationResult(
                    is_valid=False,
                    error_message=f"Golden path execution exception: {e}"
                ),
                execution_metrics=self.metrics,
                events_received=self.captured_events,
                errors_encountered=errors,
                warnings_generated=warnings,
                environment=self.environment
            )
    
    async def test_concurrent_golden_paths(
        self,
        user_count: int = 5,
        timeout_per_user: Optional[float] = None
    ) -> List[GoldenPathTestResult]:
        """
        Test concurrent golden path executions to validate multi-user support.
        
        Args:
            user_count: Number of concurrent users to simulate
            timeout_per_user: Timeout per user (uses config default if not provided)
            
        Returns:
            List of GoldenPathTestResult instances for each user
        """
        logger.info(f"Testing {user_count} concurrent golden path executions")
        
        # Create user contexts
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        id_generator = UnifiedIdGenerator()
        
        user_contexts = []
        for i in range(user_count):
            user_id = f"golden_path_user_{i+1}_{uuid.uuid4().hex[:6]}"
            thread_id, run_id, request_id = id_generator.generate_user_context_ids(
                user_id=user_id, 
                operation="golden_path_test"
            )
            websocket_client_id = id_generator.generate_websocket_client_id(user_id=user_id)
            
            context = StronglyTypedUserExecutionContext(
                user_id=UserID(user_id),
                thread_id=ThreadID(thread_id),
                run_id=RunID(run_id),
                request_id=RequestID(request_id),
                websocket_client_id=WebSocketID(websocket_client_id),
                agent_context={
                    "test_mode": True,
                    "golden_path_test": True,
                    "concurrent_user_index": i+1
                }
            )
            user_contexts.append(context)
        
        # Execute concurrent golden paths
        async def execute_user_golden_path(user_context: StronglyTypedUserExecutionContext) -> GoldenPathTestResult:
            """Execute golden path for a single user."""
            user_helper = WebSocketGoldenPathHelper(
                config=self.config,
                environment=self.environment
            )
            
            async with user_helper.authenticated_websocket_connection(user_context):
                return await user_helper.execute_golden_path_flow(
                    user_message=f"Concurrent test request from {user_context.user_id}",
                    user_context=user_context,
                    timeout=timeout_per_user
                )
        
        # Run all user flows concurrently
        concurrent_start = time.time()
        results = await asyncio.gather(
            *[execute_user_golden_path(ctx) for ctx in user_contexts],
            return_exceptions=True
        )
        concurrent_duration = time.time() - concurrent_start
        
        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"User {i+1} golden path failed with exception: {result}")
                failed_result = GoldenPathTestResult(
                    success=False,
                    user_context=user_contexts[i],
                    validation_result=AgentEventValidationResult(
                        is_valid=False,
                        error_message=f"Concurrent execution exception: {result}"
                    ),
                    execution_metrics=GoldenPathExecutionMetrics(),
                    errors_encountered=[str(result)],
                    environment=self.environment
                )
                final_results.append(failed_result)
            else:
                final_results.append(result)
        
        # Log concurrent test summary
        successful_count = sum(1 for r in final_results if r.success)
        logger.info(
            f"Concurrent golden path test completed: "
            f"{successful_count}/{user_count} successful in {concurrent_duration:.2f}s"
        )
        
        return final_results


# SSOT Convenience Functions

async def test_websocket_golden_path(
    user_message: str = "Please help me analyze data and provide insights",
    environment: str = "test",
    config: Optional[GoldenPathTestConfig] = None,
    user_context: Optional[StronglyTypedUserExecutionContext] = None
) -> GoldenPathTestResult:
    """
    SSOT function to test WebSocket golden path flow.
    
    Args:
        user_message: User message to send
        environment: Test environment
        config: Optional test configuration
        user_context: Optional user execution context
        
    Returns:
        GoldenPathTestResult with complete test results
    """
    helper = WebSocketGoldenPathHelper(config=config, environment=environment)
    
    async with helper.authenticated_websocket_connection(user_context):
        return await helper.execute_golden_path_flow(
            user_message=user_message,
            user_context=user_context
        )


async def assert_golden_path_success(
    user_message: str = "Please help me analyze data and provide insights",
    environment: str = "test",
    config: Optional[GoldenPathTestConfig] = None,
    user_context: Optional[StronglyTypedUserExecutionContext] = None,
    custom_error_message: Optional[str] = None
) -> GoldenPathTestResult:
    """
    Assert that golden path execution succeeds - raises AssertionError if not.
    
    This is the SSOT assertion function for golden path tests.
    
    Args:
        user_message: User message to send
        environment: Test environment  
        config: Optional test configuration
        user_context: Optional user execution context
        custom_error_message: Optional custom error message
        
    Returns:
        GoldenPathTestResult if successful
        
    Raises:
        AssertionError: If golden path fails
    """
    result = await test_websocket_golden_path(
        user_message=user_message,
        environment=environment,
        config=config,
        user_context=user_context
    )
    
    if not result.success:
        error_msg = custom_error_message or (
            f"GOLDEN PATH EXECUTION FAILED - Revenue Impact: {result.revenue_impact_assessment}\n"
            f"User Experience Rating: {result.execution_metrics.user_experience_rating}\n"
            f"Business Value Score: {result.execution_metrics.business_value_score:.1f}%\n"
            f"Missing Events: {result.validation_result.missing_critical_events}\n"
            f"Errors: {result.errors_encountered}\n"
            f"This failure breaks the core platform value proposition!"
        )
        raise AssertionError(error_msg)
    
    return result


# SSOT Exports
__all__ = [
    "GoldenPathTestConfig",
    "GoldenPathExecutionMetrics", 
    "GoldenPathTestResult",
    "WebSocketGoldenPathHelper",
    "test_websocket_golden_path",
    "assert_golden_path_success"
]