"""
E2E Staging Tests: WebSocket Real-Time Events
============================================

This module tests WebSocket real-time event delivery and communication in staging environment.
Tests REAL WebSocket connections, event streaming, and real-time user experience features.

Business Value:
- Validates real-time communication delivers superior user experience
- Ensures WebSocket events provide immediate feedback and engagement
- Tests mission-critical agent event notifications work in production
- Validates real-time features justify premium pricing

CRITICAL E2E REQUIREMENTS:
- MUST use real authentication (JWT/OAuth) for WebSocket connections
- MUST test actual WebSocket event streaming and delivery
- MUST validate complete real-time user experience workflows
- MUST test with real staging environment WebSocket infrastructure
- NO MOCKS ALLOWED - uses real WebSocket connections and event flows

Test Coverage:
1. Agent execution real-time event streaming
2. WebSocket connection resilience and reconnection
3. Real-time progress updates during long operations
4. Multi-user WebSocket event isolation
5. WebSocket error handling and recovery flows
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple, Set

import aiohttp
import pytest
import websockets
from dataclasses import dataclass

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper, 
    E2EAuthConfig,
    create_authenticated_user_context
)
from tests.e2e.staging_config import get_staging_config, StagingTestConfig
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID

logger = logging.getLogger(__name__)

# Test configuration
STAGING_CONFIG = get_staging_config()


@dataclass
class WebSocketEventTestResult:
    """Result of a WebSocket event test."""
    success: bool
    user_id: str
    connection_id: str
    events_received: List[Dict[str, Any]]
    event_types: List[str]
    event_timing: Dict[str, float]
    execution_time: float
    business_value_delivered: bool
    real_time_quality_score: float
    error_message: Optional[str] = None


@dataclass
class WebSocketConnectionMetrics:
    """Metrics for WebSocket connection quality."""
    connection_time: float
    first_event_time: float
    total_events: int
    event_frequency: float
    connection_stable: bool
    reconnection_attempts: int
    error_count: int


class TestWebSocketRealTimeEvents:
    """
    Complete E2E WebSocket real-time event tests for staging environment.
    
    CRITICAL: All tests use REAL WebSocket connections and event streaming.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_staging_environment(self):
        """Set up staging environment for all tests."""
        # Validate staging configuration
        assert STAGING_CONFIG.validate_configuration(), "Staging configuration invalid"
        STAGING_CONFIG.log_configuration()
        
        # Create auth helpers for staging
        self.auth_config = E2EAuthConfig.for_staging()
        self.auth_helper = E2EAuthHelper(config=self.auth_config, environment="staging")
        self.ws_helper = E2EWebSocketAuthHelper(config=self.auth_config, environment="staging")
        
        # Verify staging services are accessible
        await self._verify_staging_services_health()
        
        # Create authenticated user context for tests
        self.test_user_email = f"websocket-test-{uuid.uuid4().hex[:8]}@staging-test.com"
        self.test_user_context = await create_authenticated_user_context(
            user_email=self.test_user_email,
            environment="staging",
            permissions=["read", "write", "agent_execution", "websocket_access"],
            websocket_enabled=True
        )
        
        # Get JWT token for WebSocket authentication
        self.jwt_token = await self.auth_helper.get_staging_token_async(email=self.test_user_email)
        
        # Track WebSocket connections for cleanup
        self.active_websockets: List[Any] = []
        
        yield
        
        # Cleanup after tests
        await self._cleanup_websocket_connections()
    
    async def _verify_staging_services_health(self):
        """Verify all staging services are healthy before testing."""
        health_endpoints = STAGING_CONFIG.urls.health_endpoints
        
        async with aiohttp.ClientSession() as session:
            for service, endpoint in health_endpoints.items():
                try:
                    async with session.get(endpoint, timeout=15) as resp:
                        assert resp.status == 200, f"Staging {service} service unhealthy: {resp.status}"
                        logger.info(f" PASS:  Staging {service} service healthy")
                except Exception as e:
                    pytest.fail(f" FAIL:  Staging {service} service unavailable: {e}")
    
    async def _cleanup_websocket_connections(self):
        """Clean up all WebSocket connections created during testing."""
        for websocket in self.active_websockets:
            try:
                if not websocket.closed:
                    await websocket.close()
            except:
                pass
        logger.info(f"Cleaned up {len(self.active_websockets)} WebSocket connections")
    
    async def _create_authenticated_websocket_connection(self, timeout: float = 20.0) -> Any:
        """Create an authenticated WebSocket connection."""
        ws_headers = self.ws_helper.get_websocket_headers(self.jwt_token)
        
        websocket = await asyncio.wait_for(
            websockets.connect(
                self.auth_config.websocket_url,
                additional_headers=ws_headers,
                open_timeout=timeout
            ),
            timeout=timeout + 5.0
        )
        
        self.active_websockets.append(websocket)
        return websocket
    
    async def _monitor_websocket_events(
        self,
        websocket: Any,
        duration: float,
        expected_event_types: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], WebSocketConnectionMetrics]:
        """Monitor WebSocket events for a specified duration."""
        events = []
        start_time = time.time()
        first_event_time = None
        error_count = 0
        
        expected_event_types = expected_event_types or [
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed", "agent_response"
        ]
        
        while time.time() - start_time < duration:
            try:
                # Wait for event with timeout
                event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                event = json.loads(event_data)
                events.append(event)
                
                if first_event_time is None:
                    first_event_time = time.time() - start_time
                
                event_type = event.get("type", "unknown")
                logger.info(f"[U+1F4E5] Received WebSocket event: {event_type}")
                
                # Check for completion events
                if event_type in ["agent_completed", "error", "connection_closed"]:
                    logger.info(f"[U+1F3C1] Received completion event: {event_type}")
                    break
                    
            except asyncio.TimeoutError:
                # Timeout is expected during monitoring - continue
                continue
            except websockets.exceptions.ConnectionClosed:
                logger.warning("[U+1F50C] WebSocket connection closed during monitoring")
                break
            except Exception as e:
                error_count += 1
                logger.warning(f" WARNING: [U+FE0F] Error during WebSocket monitoring: {e}")
                if error_count > 5:  # Too many errors
                    break
        
        # Calculate metrics
        total_time = time.time() - start_time
        metrics = WebSocketConnectionMetrics(
            connection_time=0.0,  # Will be set by caller
            first_event_time=first_event_time or total_time,
            total_events=len(events),
            event_frequency=len(events) / total_time if total_time > 0 else 0,
            connection_stable=not websocket.closed if hasattr(websocket, 'closed') else True,
            reconnection_attempts=0,  # Will be tracked by caller if needed
            error_count=error_count
        )
        
        return events, metrics
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_agent_execution_real_time_event_streaming(self):
        """
        Test 1: Agent execution real-time event streaming.
        
        Business Value:
        - Validates users receive immediate feedback during AI processing
        - Ensures real-time communication creates engaging user experience
        - Tests core value proposition of responsive AI interaction
        
        Workflow:
        1. Establish WebSocket connection with authentication
        2. Trigger agent execution that generates multiple events
        3. Monitor real-time event streaming during execution
        4. Validate event sequence and timing quality
        5. Assess real-time user experience value
        """
        start_time = time.time()
        
        try:
            # Step 1: Establish authenticated WebSocket connection
            connection_start = time.time()
            websocket = await self._create_authenticated_websocket_connection(timeout=25.0)
            connection_time = time.time() - connection_start
            
            logger.info(f"[U+1F50C] WebSocket connected in {connection_time:.2f}s")
            
            # Step 2: Send message that triggers agent execution with events
            agent_request = {
                "type": "chat_message",
                "message": (
                    "Please help me create a comprehensive system optimization plan. "
                    "I need you to: 1) Analyze current system performance, "
                    "2) Research best practices and tools, 3) Create implementation steps, "
                    "4) Estimate timelines and resources. Please provide regular updates "
                    "as you work through each step so I can follow your progress."
                ),
                "user_id": str(self.test_user_context.user_id),
                "thread_id": str(self.test_user_context.thread_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_real_time_updates": True
            }
            
            await websocket.send(json.dumps(agent_request))
            logger.info(f"[U+1F4E4] Sent agent execution request")
            
            # Step 3: Monitor real-time event streaming
            expected_events = [
                "agent_started", "agent_thinking", "tool_executing", 
                "tool_completed", "agent_completed", "agent_response"
            ]
            
            events, metrics = await self._monitor_websocket_events(
                websocket=websocket,
                duration=120.0,  # 2 minutes for comprehensive agent execution
                expected_event_types=expected_events
            )
            
            await websocket.close()
            
            # Step 4: Analyze event streaming quality
            event_types_received = [event.get("type", "unknown") for event in events]
            event_type_counts = {event_type: event_types_received.count(event_type) for event_type in set(event_types_received)}
            
            # Analyze event timing and sequence
            event_timing = {}
            agent_lifecycle_events = []
            
            for i, event in enumerate(events):
                event_type = event.get("type", "unknown")
                timestamp = event.get("timestamp", "")
                
                if event_type not in event_timing:
                    event_timing[event_type] = []
                event_timing[event_type].append(i)
                
                # Track agent lifecycle progression
                if event_type in expected_events:
                    agent_lifecycle_events.append(event_type)
            
            # Calculate real-time quality metrics
            real_time_quality_indicators = {
                "immediate_response": metrics.first_event_time < 10.0,  # First event within 10s
                "regular_updates": metrics.event_frequency >= 0.1,  # At least 1 event per 10s
                "agent_lifecycle_complete": len(set(agent_lifecycle_events)) >= 3,  # Multiple lifecycle events
                "substantial_communication": len(events) >= 5,  # At least 5 events
                "connection_stable": metrics.connection_stable
            }
            
            real_time_quality_score = sum(real_time_quality_indicators.values()) / len(real_time_quality_indicators)
            
            # Step 5: Evaluate business value of real-time experience
            execution_time = time.time() - start_time
            
            business_value_indicators = []
            
            # Check for business value in event content
            for event in events:
                content = (
                    event.get("response", "") or 
                    event.get("message", "") or 
                    event.get("content", "") or
                    event.get("description", "")
                )
                
                if isinstance(content, str):
                    if any(keyword in content.lower() for keyword in [
                        "analyzing", "researching", "creating", "optimizing"
                    ]):
                        business_value_indicators.append("progress_communication")
                    
                    if any(keyword in content.lower() for keyword in [
                        "recommendation", "best practice", "implementation", "strategy"
                    ]):
                        business_value_indicators.append("valuable_content")
                    
                    if len(content) > 100:  # Substantial content
                        business_value_indicators.append("substantial_response")
            
            business_value_delivered = (
                real_time_quality_score >= 0.8 and  # High real-time quality
                len(set(business_value_indicators)) >= 2 and  # Multiple value indicators
                execution_time < 150.0 and  # Completed within reasonable time
                len(events) >= 3  # Minimum event communication
            )
            
            result = WebSocketEventTestResult(
                success=True,
                user_id=str(self.test_user_context.user_id),
                connection_id=str(self.test_user_context.websocket_client_id or "websocket-test"),
                events_received=events,
                event_types=list(set(event_types_received)),
                event_timing=event_timing,
                execution_time=execution_time,
                business_value_delivered=business_value_delivered,
                real_time_quality_score=real_time_quality_score
            )
            
            # Assertions for test success
            assert len(events) >= 3, f"Insufficient WebSocket events received: {len(events)}"
            assert metrics.first_event_time < 15.0, f"First event too slow: {metrics.first_event_time:.1f}s"
            assert real_time_quality_score >= 0.6, f"Real-time quality too low: {real_time_quality_score:.1%}"
            assert result.business_value_delivered, "Real-time event streaming failed to deliver business value"
            
            logger.info(f" PASS:  BUSINESS VALUE: Real-time event streaming delivers engaging user experience")
            logger.info(f"   Events received: {len(events)}")
            logger.info(f"   Event types: {', '.join(set(event_types_received))}")
            logger.info(f"   First event time: {metrics.first_event_time:.1f}s")
            logger.info(f"   Event frequency: {metrics.event_frequency:.2f} events/sec")
            logger.info(f"   Real-time quality: {real_time_quality_score:.1%}")
            logger.info(f"   Business indicators: {', '.join(set(business_value_indicators))}")
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f" FAIL:  Agent execution event streaming test failed: {e}")
            pytest.fail(f"Agent execution real-time event streaming failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_websocket_connection_resilience_and_reconnection(self):
        """
        Test 2: WebSocket connection resilience and reconnection.
        
        Business Value:
        - Ensures reliable real-time communication under network issues
        - Validates user experience remains smooth during connection problems
        - Tests system robustness for enterprise deployment
        
        Workflow:
        1. Establish initial WebSocket connection
        2. Test connection stability under various conditions
        3. Simulate connection interruptions and recovery
        4. Validate automatic reconnection capabilities
        5. Assess overall connection reliability
        """
        start_time = time.time()
        
        try:
            # Step 1: Establish initial connection and test stability
            logger.info(f" CYCLE:  Testing WebSocket connection resilience and reconnection")
            
            # Test 1: Basic connection stability
            websocket_1 = await self._create_authenticated_websocket_connection(timeout=25.0)
            
            # Send keepalive messages to test stability
            stability_test_duration = 30.0
            stability_start = time.time()
            keepalive_count = 0
            stability_errors = 0
            
            while time.time() - stability_start < stability_test_duration:
                try:
                    keepalive_message = {
                        "type": "keepalive",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "test_id": f"stability_{keepalive_count}"
                    }
                    
                    await websocket_1.send(json.dumps(keepalive_message))
                    keepalive_count += 1
                    
                    # Wait for potential response or just test sending capability
                    try:
                        response = await asyncio.wait_for(websocket_1.recv(), timeout=2.0)
                        # Got a response, that's good
                    except asyncio.TimeoutError:
                        # No response is fine for keepalive
                        pass
                    
                    await asyncio.sleep(3.0)  # 3 second intervals
                    
                except Exception as e:
                    stability_errors += 1
                    logger.warning(f" WARNING: [U+FE0F] Stability test error {stability_errors}: {e}")
                    if stability_errors > 3:
                        break
            
            stability_success_rate = (keepalive_count - stability_errors) / keepalive_count if keepalive_count > 0 else 0
            
            await websocket_1.close()
            
            # Test 2: Multiple sequential connections (simulating reconnection scenarios)
            reconnection_results = []
            
            for reconnect_attempt in range(3):
                reconnect_start = time.time()
                
                try:
                    websocket = await self._create_authenticated_websocket_connection(timeout=20.0)
                    
                    # Test connection with a simple message
                    test_message = {
                        "type": "connection_test",
                        "reconnect_attempt": reconnect_attempt,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Try to receive response or confirmation
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        response_received = True
                    except asyncio.TimeoutError:
                        response_received = False  # No response is acceptable for some message types
                    
                    reconnect_time = time.time() - reconnect_start
                    
                    reconnection_results.append({
                        "attempt": reconnect_attempt,
                        "success": True,
                        "connection_time": reconnect_time,
                        "response_received": response_received
                    })
                    
                    await websocket.close()
                    
                    # Brief pause between connections
                    await asyncio.sleep(2.0)
                    
                    logger.info(f" PASS:  Reconnection attempt {reconnect_attempt + 1} successful: {reconnect_time:.2f}s")
                    
                except Exception as e:
                    reconnect_time = time.time() - reconnect_start
                    reconnection_results.append({
                        "attempt": reconnect_attempt,
                        "success": False,
                        "connection_time": reconnect_time,
                        "error": str(e)
                    })
                    logger.warning(f" WARNING: [U+FE0F] Reconnection attempt {reconnect_attempt + 1} failed: {e}")
            
            # Test 3: Concurrent connection handling
            concurrent_connections = []
            concurrent_connection_start = time.time()
            
            async def create_concurrent_connection(conn_id: int) -> Dict[str, Any]:
                try:
                    ws = await self._create_authenticated_websocket_connection(timeout=15.0)
                    
                    # Send identification message
                    id_message = {
                        "type": "concurrent_test",
                        "connection_id": conn_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await ws.send(json.dumps(id_message))
                    
                    # Keep connection open briefly
                    await asyncio.sleep(5.0)
                    
                    await ws.close()
                    
                    return {"connection_id": conn_id, "success": True}
                    
                except Exception as e:
                    return {"connection_id": conn_id, "success": False, "error": str(e)}
            
            # Create 3 concurrent connections
            concurrent_tasks = [create_concurrent_connection(i) for i in range(3)]
            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            concurrent_connection_time = time.time() - concurrent_connection_start
            successful_concurrent = sum(1 for r in concurrent_results if isinstance(r, dict) and r.get("success", False))
            
            # Step 4: Evaluate connection resilience
            successful_reconnections = sum(1 for r in reconnection_results if r.get("success", False))
            reconnection_success_rate = successful_reconnections / len(reconnection_results)
            
            average_reconnection_time = sum(
                r.get("connection_time", 0) for r in reconnection_results if r.get("success", False)
            ) / max(successful_reconnections, 1)
            
            resilience_metrics = {
                "stability_success_rate": stability_success_rate,
                "keepalive_messages_sent": keepalive_count,
                "stability_errors": stability_errors,
                "reconnection_success_rate": reconnection_success_rate,
                "successful_reconnections": successful_reconnections,
                "average_reconnection_time": average_reconnection_time,
                "concurrent_connections_successful": successful_concurrent,
                "concurrent_success_rate": successful_concurrent / 3
            }
            
            execution_time = time.time() - start_time
            
            # Step 5: Assess business value of connection reliability
            reliability_indicators = {
                "stable_connections": resilience_metrics["stability_success_rate"] >= 0.8,
                "reliable_reconnection": resilience_metrics["reconnection_success_rate"] >= 0.67,
                "fast_reconnection": resilience_metrics["average_reconnection_time"] < 15.0,
                "concurrent_handling": resilience_metrics["concurrent_success_rate"] >= 0.67,
                "minimal_errors": resilience_metrics["stability_errors"] <= 2
            }
            
            business_value_delivered = sum(reliability_indicators.values()) >= 4
            
            result = WebSocketEventTestResult(
                success=True,
                user_id=str(self.test_user_context.user_id),
                connection_id="resilience-test",
                events_received=[],  # Not applicable for this test
                event_types=["keepalive", "connection_test", "concurrent_test"],
                event_timing={},
                execution_time=execution_time,
                business_value_delivered=business_value_delivered,
                real_time_quality_score=sum(reliability_indicators.values()) / len(reliability_indicators)
            )
            
            # Assertions for test success
            assert stability_success_rate >= 0.7, f"Connection stability too low: {stability_success_rate:.1%}"
            assert reconnection_success_rate >= 0.6, f"Reconnection success rate too low: {reconnection_success_rate:.1%}"
            assert successful_concurrent >= 2, f"Too few successful concurrent connections: {successful_concurrent}/3"
            assert result.business_value_delivered, "Connection resilience failed to deliver business value"
            
            logger.info(f" PASS:  BUSINESS VALUE: WebSocket connections demonstrate enterprise-grade reliability")
            logger.info(f"   Stability success rate: {stability_success_rate:.1%}")
            logger.info(f"   Reconnection success rate: {reconnection_success_rate:.1%}")
            logger.info(f"   Average reconnection time: {average_reconnection_time:.1f}s")
            logger.info(f"   Concurrent connections: {successful_concurrent}/3")
            logger.info(f"   Reliability score: {result.real_time_quality_score:.1%}")
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f" FAIL:  WebSocket resilience test failed: {e}")
            pytest.fail(f"WebSocket connection resilience and reconnection failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_real_time_progress_updates_during_long_operations(self):
        """
        Test 3: Real-time progress updates during long operations.
        
        Business Value:
        - Validates users stay engaged during lengthy AI processing
        - Ensures progress communication prevents user abandonment
        - Tests real-time feedback for complex business workflows
        
        Workflow:
        1. Initiate long-running operation requiring progress updates
        2. Monitor continuous progress event streaming
        3. Validate progress communication quality and frequency
        4. Verify user engagement maintenance throughout operation
        5. Assess long-operation user experience value
        """
        start_time = time.time()
        
        try:
            # Step 1: Establish WebSocket and initiate long operation
            websocket = await self._create_authenticated_websocket_connection(timeout=25.0)
            logger.info(f"[U+1F50C] WebSocket connected for long operation test")
            
            # Send request for comprehensive long-running analysis
            long_operation_request = {
                "type": "chat_message",
                "message": (
                    "I need a comprehensive business analysis and strategic planning session. "
                    "Please work through these tasks systematically and keep me updated on your progress: "
                    "1) Analyze market trends and competitive landscape, "
                    "2) Review our current business model and identify optimization opportunities, "
                    "3) Research industry best practices and emerging technologies, "
                    "4) Develop strategic recommendations with implementation timelines, "
                    "5) Create risk assessment and mitigation strategies, "
                    "6) Prepare executive summary with actionable insights. "
                    "Please provide detailed progress updates as you work through each step "
                    "so I can follow your analytical process."
                ),
                "user_id": str(self.test_user_context.user_id),
                "thread_id": str(self.test_user_context.thread_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_detailed_progress": True,
                "expected_duration": "long"
            }
            
            await websocket.send(json.dumps(long_operation_request))
            logger.info(f"[U+1F4E4] Sent long operation request")
            
            # Step 2: Monitor progress updates over extended period
            progress_events = []
            progress_timeline = []
            engagement_metrics = {
                "progress_updates_received": 0,
                "substantial_updates": 0,
                "user_engagement_maintained": True,
                "progress_frequency": 0.0,
                "content_quality_score": 0
            }
            
            monitoring_start = time.time()
            last_progress_time = monitoring_start
            max_gap_between_updates = 0.0
            
            # Monitor for up to 3 minutes for comprehensive analysis
            while time.time() - monitoring_start < 180.0:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    event = json.loads(event_data)
                    progress_events.append(event)
                    
                    current_time = time.time()
                    gap_since_last = current_time - last_progress_time
                    max_gap_between_updates = max(max_gap_between_updates, gap_since_last)
                    last_progress_time = current_time
                    
                    event_type = event.get("type", "unknown")
                    
                    # Track progress indicators
                    if event_type in ["agent_thinking", "tool_executing", "agent_started"]:
                        engagement_metrics["progress_updates_received"] += 1
                        progress_timeline.append({
                            "time": current_time - monitoring_start,
                            "type": event_type,
                            "description": event.get("description", "")
                        })
                        logger.info(f" CHART:  Progress update: {event_type}")
                    
                    # Analyze content for engagement quality
                    content = (
                        event.get("response", "") or 
                        event.get("message", "") or 
                        event.get("content", "") or
                        event.get("description", "")
                    )
                    
                    if isinstance(content, str) and len(content) > 50:
                        engagement_metrics["substantial_updates"] += 1
                        
                        # Check for progress communication quality
                        if any(keyword in content.lower() for keyword in [
                            "analyzing", "reviewing", "working on", "step", "progress", "currently"
                        ]):
                            engagement_metrics["content_quality_score"] += 1
                        
                        if any(keyword in content.lower() for keyword in [
                            "found", "identified", "discovered", "completed", "finished"
                        ]):
                            engagement_metrics["content_quality_score"] += 1
                    
                    # Check for completion
                    if event_type in ["agent_completed", "agent_response"] and len(content) > 200:
                        logger.info(f"[U+1F3C1] Long operation completed with substantial response")
                        break
                        
                except asyncio.TimeoutError:
                    # Gap in communication - check if too long
                    gap_duration = time.time() - last_progress_time
                    if gap_duration > 30.0:  # More than 30 seconds without update
                        engagement_metrics["user_engagement_maintained"] = False
                        logger.warning(f" WARNING: [U+FE0F] Long gap in progress updates: {gap_duration:.1f}s")
                    continue
                except Exception as e:
                    logger.warning(f" WARNING: [U+FE0F] Error during progress monitoring: {e}")
                    break
            
            await websocket.close()
            
            # Step 3: Analyze progress communication effectiveness
            total_monitoring_time = time.time() - monitoring_start
            engagement_metrics["progress_frequency"] = engagement_metrics["progress_updates_received"] / total_monitoring_time
            
            # Evaluate progress update quality
            progress_quality_indicators = {
                "regular_updates": engagement_metrics["progress_updates_received"] >= 5,
                "substantial_communication": engagement_metrics["substantial_updates"] >= 3,
                "engagement_maintained": engagement_metrics["user_engagement_maintained"],
                "reasonable_frequency": engagement_metrics["progress_frequency"] >= 0.05,  # At least 1 per 20 seconds
                "content_quality": engagement_metrics["content_quality_score"] >= 3,
                "manageable_gaps": max_gap_between_updates < 45.0  # No more than 45s gaps
            }
            
            progress_quality_score = sum(progress_quality_indicators.values()) / len(progress_quality_indicators)
            
            # Step 4: Evaluate user experience during long operation
            user_experience_metrics = {
                "total_progress_events": len(progress_events),
                "progress_timeline_length": len(progress_timeline),
                "max_gap_between_updates": max_gap_between_updates,
                "average_update_frequency": engagement_metrics["progress_frequency"],
                "content_richness": engagement_metrics["substantial_updates"] / max(len(progress_events), 1)
            }
            
            execution_time = time.time() - start_time
            
            # Step 5: Assess business value of long-operation support
            business_value_delivered = (
                progress_quality_score >= 0.67 and  # Good progress quality
                engagement_metrics["user_engagement_maintained"] and  # User stayed engaged
                engagement_metrics["progress_updates_received"] >= 4 and  # Sufficient updates
                max_gap_between_updates < 60.0 and  # Reasonable communication gaps
                execution_time < 210.0  # Completed within reasonable time
            )
            
            result = WebSocketEventTestResult(
                success=True,
                user_id=str(self.test_user_context.user_id),
                connection_id="long-operation-test",
                events_received=progress_events,
                event_types=list(set([e.get("type", "unknown") for e in progress_events])),
                event_timing={},
                execution_time=execution_time,
                business_value_delivered=business_value_delivered,
                real_time_quality_score=progress_quality_score
            )
            
            # Assertions for test success
            assert engagement_metrics["progress_updates_received"] >= 3, f"Too few progress updates: {engagement_metrics['progress_updates_received']}"
            assert max_gap_between_updates < 60.0, f"Progress gaps too long: {max_gap_between_updates:.1f}s"
            assert engagement_metrics["user_engagement_maintained"], "User engagement not maintained during long operation"
            assert result.business_value_delivered, "Long operation progress updates failed to deliver business value"
            
            logger.info(f" PASS:  BUSINESS VALUE: Real-time progress updates maintain user engagement during long operations")
            logger.info(f"   Progress updates received: {engagement_metrics['progress_updates_received']}")
            logger.info(f"   Update frequency: {engagement_metrics['progress_frequency']:.3f} updates/sec")
            logger.info(f"   Max gap between updates: {max_gap_between_updates:.1f}s")
            logger.info(f"   Substantial updates: {engagement_metrics['substantial_updates']}")
            logger.info(f"   Progress quality score: {progress_quality_score:.1%}")
            logger.info(f"   User engagement maintained: {engagement_metrics['user_engagement_maintained']}")
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f" FAIL:  Long operation progress test failed: {e}")
            pytest.fail(f"Real-time progress updates during long operations failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_multi_user_websocket_event_isolation(self):
        """
        Test 4: Multi-user WebSocket event isolation.
        
        Business Value:
        - Ensures users only receive their own WebSocket events
        - Validates real-time communication scales securely
        - Tests WebSocket isolation prevents data leakage
        
        Workflow:
        1. Create multiple concurrent WebSocket connections
        2. Send user-specific messages simultaneously
        3. Verify each user receives only their own events
        4. Validate WebSocket event isolation boundaries
        5. Assess multi-user real-time communication security
        """
        start_time = time.time()
        
        try:
            # Step 1: Create multiple users with WebSocket connections
            num_concurrent_users = 4
            user_connections = []
            
            logger.info(f"[U+1F50C] Creating {num_concurrent_users} concurrent WebSocket connections for isolation test")
            
            for user_index in range(num_concurrent_users):
                # Create unique user context
                user_email = f"ws-isolation-{user_index}-{uuid.uuid4().hex[:8]}@staging-test.com"
                user_context = await create_authenticated_user_context(
                    user_email=user_email,
                    environment="staging",
                    permissions=["read", "write", "websocket_access"],
                    websocket_enabled=True
                )
                
                # Get JWT token and create WebSocket connection
                jwt_token = await self.auth_helper.get_staging_token_async(email=user_email)
                ws_helper = E2EWebSocketAuthHelper(config=self.auth_config, environment="staging")
                
                try:
                    ws_headers = ws_helper.get_websocket_headers(jwt_token)
                    websocket = await asyncio.wait_for(
                        websockets.connect(
                            self.auth_config.websocket_url,
                            additional_headers=ws_headers,
                            open_timeout=20.0
                        ),
                        timeout=25.0
                    )
                    
                    user_connections.append({
                        "user_index": user_index,
                        "user_id": str(user_context.user_id),
                        "email": user_email,
                        "websocket": websocket,
                        "user_context": user_context,
                        "events_received": [],
                        "user_specific_data": f"secret-data-user-{user_index}-{uuid.uuid4().hex[:8]}"
                    })
                    
                    self.active_websockets.append(websocket)
                    logger.info(f" PASS:  User {user_index} WebSocket connected")
                    
                except Exception as e:
                    logger.warning(f" WARNING: [U+FE0F] Failed to connect WebSocket for user {user_index}: {e}")
            
            assert len(user_connections) >= 3, f"Too few WebSocket connections: {len(user_connections)}/4"
            
            # Step 2: Send user-specific messages simultaneously
            async def send_user_specific_message_and_collect_events(connection: Dict[str, Any]) -> Dict[str, Any]:
                user_index = connection["user_index"]
                user_id = connection["user_id"]
                websocket = connection["websocket"]
                user_specific_data = connection["user_specific_data"]
                
                # Send message with user-specific identifiers
                user_message = {
                    "type": "isolation_test_message",
                    "message": (
                        f"This is user {user_index} with ID {user_id}. "
                        f"My secret data is: {user_specific_data}. "
                        f"Please respond only to user {user_index} and include my ID {user_id} "
                        f"and my secret data in your response for verification."
                    ),
                    "user_id": user_id,
                    "user_index": user_index,
                    "secret_data": user_specific_data,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                try:
                    await websocket.send(json.dumps(user_message))
                    
                    # Collect events for this user
                    events = []
                    collect_start = time.time()
                    
                    while time.time() - collect_start < 45.0:  # 45 seconds to collect events
                        try:
                            event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            event = json.loads(event_data)
                            events.append(event)
                            
                            # Check for completion or substantial response
                            if event.get("type") in ["agent_completed", "agent_response"]:
                                content = event.get("response", "") or event.get("message", "")
                                if isinstance(content, str) and len(content) > 50:
                                    break
                                    
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            logger.warning(f"Event collection error for user {user_index}: {e}")
                            break
                    
                    return {
                        "user_index": user_index,
                        "user_id": user_id,
                        "secret_data": user_specific_data,
                        "events": events,
                        "success": len(events) > 0
                    }
                    
                except Exception as e:
                    return {
                        "user_index": user_index,
                        "user_id": user_id,
                        "secret_data": user_specific_data,
                        "events": [],
                        "success": False,
                        "error": str(e)
                    }
            
            # Execute concurrent messaging and event collection
            concurrent_tasks = [
                send_user_specific_message_and_collect_events(conn) for conn in user_connections
            ]
            
            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Close all WebSocket connections
            for connection in user_connections:
                try:
                    await connection["websocket"].close()
                except:
                    pass
            
            # Step 3: Analyze event isolation
            successful_results = [
                result for result in concurrent_results 
                if isinstance(result, dict) and result.get("success", False)
            ]
            
            isolation_violations = []
            cross_contamination_checks = []
            
            # Check for cross-user event contamination
            for result_a in successful_results:
                user_a_id = result_a["user_id"]
                user_a_secret = result_a["secret_data"]
                user_a_events = result_a["events"]
                
                # Check if this user's events contain their own data
                user_a_data_found = False
                
                for event in user_a_events:
                    content = str(event.get("response", "") or event.get("message", "") or event.get("content", ""))
                    
                    if user_a_id in content or user_a_secret in content:
                        user_a_data_found = True
                    
                    # Check for other users' data in this user's events (contamination)
                    for result_b in successful_results:
                        if result_b["user_id"] != user_a_id:
                            user_b_id = result_b["user_id"]
                            user_b_secret = result_b["secret_data"]
                            
                            if user_b_id in content or user_b_secret in content:
                                isolation_violations.append(
                                    f"User {user_a_id} received data from user {user_b_id}"
                                )
                
                cross_contamination_checks.append({
                    "user_id": user_a_id,
                    "own_data_found": user_a_data_found,
                    "events_count": len(user_a_events)
                })
            
            # Step 4: Evaluate isolation quality
            isolation_metrics = {
                "users_with_successful_communication": len(successful_results),
                "users_receiving_own_data": sum(1 for check in cross_contamination_checks if check["own_data_found"]),
                "isolation_violations": len(isolation_violations),
                "cross_contamination_rate": len(isolation_violations) / max(len(successful_results), 1),
                "isolation_success_rate": 1.0 - (len(isolation_violations) / max(len(successful_results), 1))
            }
            
            execution_time = time.time() - start_time
            
            # Step 5: Assess multi-user security business value
            security_indicators = {
                "successful_multi_user_communication": isolation_metrics["users_with_successful_communication"] >= 3,
                "no_isolation_violations": isolation_metrics["isolation_violations"] == 0,
                "users_receive_own_data": isolation_metrics["users_receiving_own_data"] >= len(successful_results) * 0.67,
                "high_isolation_success": isolation_metrics["isolation_success_rate"] >= 0.95,
                "reasonable_performance": execution_time < 90.0
            }
            
            business_value_delivered = sum(security_indicators.values()) >= 4
            
            result = WebSocketEventTestResult(
                success=True,
                user_id="multi-user-isolation-test",
                connection_id="isolation-test",
                events_received=[],  # Combined events not meaningful for this test
                event_types=["isolation_test_message"],
                event_timing={},
                execution_time=execution_time,
                business_value_delivered=business_value_delivered,
                real_time_quality_score=isolation_metrics["isolation_success_rate"]
            )
            
            # Assertions for test success
            assert len(successful_results) >= 3, f"Too few successful multi-user communications: {len(successful_results)}"
            assert isolation_metrics["isolation_violations"] == 0, f"WebSocket isolation violations: {isolation_violations}"
            assert isolation_metrics["isolation_success_rate"] >= 0.9, f"Isolation success rate too low: {isolation_metrics['isolation_success_rate']:.1%}"
            assert result.business_value_delivered, "Multi-user WebSocket isolation failed to deliver business value"
            
            logger.info(f" PASS:  BUSINESS VALUE: WebSocket events maintain strict multi-user isolation")
            logger.info(f"   Successful multi-user communications: {len(successful_results)}/{num_concurrent_users}")
            logger.info(f"   Users receiving own data: {isolation_metrics['users_receiving_own_data']}/{len(successful_results)}")
            logger.info(f"   Isolation violations: {isolation_metrics['isolation_violations']}")
            logger.info(f"   Isolation success rate: {isolation_metrics['isolation_success_rate']:.1%}")
            logger.info(f"   Cross-contamination rate: {isolation_metrics['cross_contamination_rate']:.1%}")
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f" FAIL:  Multi-user WebSocket isolation test failed: {e}")
            pytest.fail(f"Multi-user WebSocket event isolation failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_websocket_error_handling_and_recovery_flows(self):
        """
        Test 5: WebSocket error handling and recovery flows.
        
        Business Value:
        - Ensures robust error handling maintains user trust
        - Validates graceful degradation under error conditions
        - Tests system resilience for production deployment
        
        Workflow:
        1. Test WebSocket behavior under various error conditions
        2. Validate graceful error handling and user communication
        3. Test recovery mechanisms and fallback strategies
        4. Verify error reporting and system diagnostics
        5. Assess overall error resilience business value
        """
        start_time = time.time()
        
        try:
            # Step 1: Test normal operation baseline
            websocket = await self._create_authenticated_websocket_connection(timeout=25.0)
            
            # Send normal message to establish baseline
            baseline_message = {
                "type": "error_test_baseline",
                "message": "This is a baseline test to ensure normal operation before error testing.",
                "user_id": str(self.test_user_context.user_id),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(baseline_message))
            
            # Collect baseline response
            baseline_events = []
            try:
                for _ in range(3):  # Collect up to 3 baseline events
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    baseline_events.append(json.loads(event_data))
            except asyncio.TimeoutError:
                pass  # Baseline collection timeout is acceptable
            
            baseline_success = len(baseline_events) > 0
            await websocket.close()
            
            # Step 2: Test error scenarios and recovery
            error_test_scenarios = [
                {
                    "name": "malformed_message",
                    "test_data": "{invalid_json: malformed}",
                    "expected_behavior": "graceful_handling"
                },
                {
                    "name": "oversized_message",
                    "test_data": json.dumps({
                        "type": "oversized_test",
                        "large_content": "x" * 10000,  # Large content
                        "user_id": str(self.test_user_context.user_id)
                    }),
                    "expected_behavior": "size_limit_handling"
                },
                {
                    "name": "rapid_messages",
                    "test_data": "rapid_message_test",
                    "expected_behavior": "rate_limiting_or_queuing"
                }
            ]
            
            error_handling_results = []
            
            for scenario in error_test_scenarios:
                scenario_start = time.time()
                
                try:
                    # Create new connection for each error test
                    test_websocket = await self._create_authenticated_websocket_connection(timeout=20.0)
                    
                    if scenario["name"] == "malformed_message":
                        # Send malformed JSON
                        await test_websocket.send(scenario["test_data"])
                        
                    elif scenario["name"] == "oversized_message":
                        # Send oversized message
                        await test_websocket.send(scenario["test_data"])
                        
                    elif scenario["name"] == "rapid_messages":
                        # Send multiple rapid messages
                        for i in range(5):
                            rapid_message = {
                                "type": "rapid_test",
                                "message": f"Rapid message {i}",
                                "user_id": str(self.test_user_context.user_id),
                                "rapid_index": i
                            }
                            await test_websocket.send(json.dumps(rapid_message))
                            await asyncio.sleep(0.1)  # Very rapid sending
                    
                    # Collect error handling responses
                    error_responses = []
                    error_collect_start = time.time()
                    
                    while time.time() - error_collect_start < 20.0:
                        try:
                            response_data = await asyncio.wait_for(test_websocket.recv(), timeout=3.0)
                            response = json.loads(response_data)
                            error_responses.append(response)
                            
                            # Check for error handling indicators
                            if response.get("type") in ["error", "warning", "rate_limit"]:
                                break
                                
                        except asyncio.TimeoutError:
                            break
                        except websockets.exceptions.ConnectionClosed:
                            # Connection closed might be expected for some error scenarios
                            break
                        except Exception as e:
                            # JSON parsing errors are expected for malformed message tests
                            if scenario["name"] == "malformed_message":
                                error_responses.append({"type": "json_parse_error", "error": str(e)})
                            break
                    
                    await test_websocket.close()
                    
                    scenario_time = time.time() - scenario_start
                    
                    # Analyze error handling quality
                    error_handling_quality = {
                        "connection_maintained": not (hasattr(test_websocket, 'closed') and test_websocket.closed),
                        "error_communicated": any(r.get("type") in ["error", "warning"] for r in error_responses),
                        "graceful_handling": len(error_responses) > 0,  # Some response received
                        "reasonable_response_time": scenario_time < 30.0
                    }
                    
                    error_handling_results.append({
                        "scenario": scenario["name"],
                        "success": True,
                        "responses": error_responses,
                        "handling_quality": error_handling_quality,
                        "scenario_time": scenario_time
                    })
                    
                    logger.info(f" PASS:  Error scenario '{scenario['name']}' completed: {scenario_time:.1f}s")
                    
                except Exception as e:
                    error_handling_results.append({
                        "scenario": scenario["name"],
                        "success": False,
                        "error": str(e),
                        "scenario_time": time.time() - scenario_start
                    })
                    logger.warning(f" WARNING: [U+FE0F] Error scenario '{scenario['name']}' failed: {e}")
                
                # Brief pause between error scenarios
                await asyncio.sleep(2.0)
            
            # Step 3: Test recovery after errors
            recovery_start = time.time()
            
            try:
                # Test that system can recover to normal operation after errors
                recovery_websocket = await self._create_authenticated_websocket_connection(timeout=20.0)
                
                recovery_message = {
                    "type": "recovery_test",
                    "message": "Testing system recovery after error scenarios. Please respond normally.",
                    "user_id": str(self.test_user_context.user_id),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await recovery_websocket.send(json.dumps(recovery_message))
                
                # Collect recovery response
                recovery_events = []
                try:
                    for _ in range(3):
                        event_data = await asyncio.wait_for(recovery_websocket.recv(), timeout=15.0)
                        recovery_events.append(json.loads(event_data))
                except asyncio.TimeoutError:
                    pass
                
                await recovery_websocket.close()
                
                recovery_time = time.time() - recovery_start
                recovery_success = len(recovery_events) > 0
                
                logger.info(f" PASS:  System recovery test: {recovery_success} ({recovery_time:.1f}s)")
                
            except Exception as e:
                recovery_success = False
                recovery_time = time.time() - recovery_start
                logger.warning(f" WARNING: [U+FE0F] System recovery test failed: {e}")
            
            # Step 4: Evaluate error handling effectiveness
            successful_error_scenarios = sum(1 for r in error_handling_results if r.get("success", False))
            
            error_handling_metrics = {
                "baseline_operation_success": baseline_success,
                "error_scenarios_completed": successful_error_scenarios,
                "error_scenario_success_rate": successful_error_scenarios / len(error_test_scenarios),
                "system_recovery_success": recovery_success,
                "total_error_handling_time": sum(r.get("scenario_time", 0) for r in error_handling_results)
            }
            
            # Analyze overall error resilience
            resilience_indicators = {
                "baseline_works": baseline_success,
                "handles_malformed_input": any(r.get("scenario") == "malformed_message" and r.get("success") for r in error_handling_results),
                "handles_oversized_input": any(r.get("scenario") == "oversized_message" and r.get("success") for r in error_handling_results),
                "handles_rapid_input": any(r.get("scenario") == "rapid_messages" and r.get("success") for r in error_handling_results),
                "recovers_after_errors": recovery_success,
                "reasonable_error_handling_time": error_handling_metrics["total_error_handling_time"] < 120.0
            }
            
            execution_time = time.time() - start_time
            
            # Step 5: Assess business value of error resilience
            business_value_delivered = sum(resilience_indicators.values()) >= 4
            
            result = WebSocketEventTestResult(
                success=True,
                user_id=str(self.test_user_context.user_id),
                connection_id="error-handling-test",
                events_received=baseline_events + recovery_events,
                event_types=["error_test_baseline", "recovery_test"],
                event_timing={},
                execution_time=execution_time,
                business_value_delivered=business_value_delivered,
                real_time_quality_score=sum(resilience_indicators.values()) / len(resilience_indicators)
            )
            
            # Assertions for test success
            assert baseline_success, "Baseline WebSocket operation failed"
            assert successful_error_scenarios >= 2, f"Too few error scenarios handled: {successful_error_scenarios}/3"
            assert recovery_success, "System failed to recover after error scenarios"
            assert result.business_value_delivered, "WebSocket error handling failed to deliver business value"
            
            logger.info(f" PASS:  BUSINESS VALUE: WebSocket error handling demonstrates production readiness")
            logger.info(f"   Baseline operation: {baseline_success}")
            logger.info(f"   Error scenarios handled: {successful_error_scenarios}/{len(error_test_scenarios)}")
            logger.info(f"   System recovery: {recovery_success}")
            logger.info(f"   Error resilience score: {result.real_time_quality_score:.1%}")
            logger.info(f"   Total error handling time: {error_handling_metrics['total_error_handling_time']:.1f}s")
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f" FAIL:  WebSocket error handling test failed: {e}")
            pytest.fail(f"WebSocket error handling and recovery flows failed: {e}")


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v", "--tb=short"])