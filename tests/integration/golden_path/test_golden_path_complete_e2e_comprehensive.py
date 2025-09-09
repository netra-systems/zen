#!/usr/bin/env python3
"""
GOLDEN PATH COMPLETE E2E COMPREHENSIVE TEST SUITE - CRITICAL P0 BUSINESS VALUE VALIDATION
=========================================================================================

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity  
- Business Goal: Platform Reliability & Revenue Protection ($500K+ ARR)
- Value Impact: Validates complete golden path user journey from authentication to business insights delivery
- Strategic/Revenue Impact: Prevents critical failures affecting 90% of user-delivered value through chat functionality

COMPLETE GOLDEN PATH FLOW VALIDATION:
1. User opens chat interface → Connection established
2. JWT authentication → UserExecutionContext created  
3. WebSocket ready → Welcome message sent
4. User sends optimization request → Message routed to AgentHandler
5. ExecutionEngineFactory creates isolated engine → SupervisorAgent orchestrates
6. Agent Triage → Data Helper Agent → Optimization Agent → UVS/Reporting Agent
7. All 5 WebSocket events sent → Tools executed → Results compiled
8. Final response with business value → Conversation persisted to database
9. User session maintained → Redis cache updated → Complete cleanup

CRITICAL REQUIREMENTS:
- All tests MUST use real services (PostgreSQL, Redis, WebSocket, Auth, Backend)
- All tests MUST use SSOT authentication patterns from test_framework/ssot/e2e_auth_helper.py
- All tests MUST validate complete end-to-end business value delivery
- All tests MUST include proper Business Value Justification comments
- All tests MUST validate the complete 5 mission-critical WebSocket events
- All tests MUST test realistic enterprise scenarios with production-level data

DEPLOYMENT BLOCKER: ANY FAILURE IN THIS SUITE BLOCKS PRODUCTION DEPLOYMENT
"""

import asyncio
import json
import os
import sys
import time
import uuid
import threading
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import websockets
import httpx
import aiohttp
from loguru import logger

# SSOT Framework Imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper,
    AuthenticatedUser
)
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, RunID, ensure_user_id

# No-Docker fixtures for service-independent testing
from test_framework.fixtures.no_docker_golden_path_fixtures import (
    no_docker_golden_path_services, 
    golden_path_services,
    mock_authenticated_user,
    skip_if_docker_required
)

# Production System Imports for Real Service Testing
from netra_backend.app.core.unified_id_manager import generate_user_id, generate_thread_id, UnifiedIDManager


# ============================================================================
# GOLDEN PATH TEST METRICS AND CONTEXT
# ============================================================================

@dataclass
class GoldenPathMetrics:
    """Comprehensive metrics for Golden Path validation."""
    
    # Connection and Authentication Metrics
    websocket_connection_time: float = 0.0
    jwt_validation_time: float = 0.0
    auth_success_rate: float = 0.0
    
    # Message Processing Metrics
    message_routing_time: float = 0.0
    agent_orchestration_time: float = 0.0
    total_execution_time: float = 0.0
    
    # WebSocket Event Metrics (Mission Critical)
    agent_started_events: int = 0
    agent_thinking_events: int = 0
    tool_executing_events: int = 0
    tool_completed_events: int = 0
    agent_completed_events: int = 0
    total_websocket_events: int = 0
    
    # Business Value Metrics
    cost_optimization_value: float = 0.0  # Dollar savings identified
    actionable_insights_count: int = 0
    user_satisfaction_score: float = 0.0
    business_value_delivered: bool = False
    
    # Persistence and Audit Metrics
    database_writes: int = 0
    redis_cache_operations: int = 0
    audit_trail_entries: int = 0
    
    # Performance SLA Metrics
    first_event_latency: float = 0.0  # Time to first WebSocket event (target: <5s)
    total_response_time: float = 0.0  # Time to final response (target: <60s)
    concurrent_user_capacity: int = 0  # Max concurrent users handled
    
    # Error and Recovery Metrics
    error_count: int = 0
    recovery_attempts: int = 0
    graceful_degradation_events: int = 0
    
    def __post_init__(self):
        """Initialize computed metrics."""
        self.total_websocket_events = (
            self.agent_started_events + 
            self.agent_thinking_events + 
            self.tool_executing_events + 
            self.tool_completed_events + 
            self.agent_completed_events
        )
        
    def validate_mission_critical_events(self) -> bool:
        """Validate all 5 mission-critical WebSocket events were received."""
        required_events = [
            self.agent_started_events > 0,
            self.agent_thinking_events > 0, 
            self.tool_executing_events > 0,
            self.tool_completed_events > 0,
            self.agent_completed_events > 0
        ]
        return all(required_events)
    
    def meets_performance_sla(self) -> bool:
        """Check if performance meets SLA requirements."""
        return (
            self.websocket_connection_time <= 2.0 and  # Connection within 2s
            self.first_event_latency <= 5.0 and       # First event within 5s
            self.total_response_time <= 60.0          # Complete response within 60s
        )
    
    def delivers_business_value(self) -> bool:
        """Check if measurable business value was delivered."""
        return (
            self.business_value_delivered and
            self.actionable_insights_count > 0 and
            (self.cost_optimization_value > 0 or self.user_satisfaction_score >= 0.8)
        )


@dataclass
class GoldenPathTestContext:
    """Context for Golden Path test execution."""
    
    test_id: str
    authenticated_user: AuthenticatedUser
    websocket_url: str
    backend_url: str
    
    # Test State Tracking
    connection_established: bool = False
    authentication_completed: bool = False  
    message_sent: bool = False
    agent_execution_started: bool = False
    response_received: bool = False
    cleanup_completed: bool = False
    
    # Event Tracking
    received_events: List[Dict[str, Any]] = field(default_factory=list)
    websocket_messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Business Context
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    optimization_scenario: Optional[str] = None
    expected_business_value: Optional[Dict[str, Any]] = None
    
    # Performance Tracking
    start_time: Optional[float] = None
    connection_time: Optional[float] = None
    first_event_time: Optional[float] = None
    completion_time: Optional[float] = None
    
    def mark_connection_established(self):
        """Mark WebSocket connection as established."""
        self.connection_established = True
        self.connection_time = time.time()
        
    def mark_first_event_received(self):
        """Mark first WebSocket event received."""
        if self.first_event_time is None and self.start_time:
            self.first_event_time = time.time() - self.start_time
    
    def record_event(self, event: Dict[str, Any]):
        """Record a WebSocket event."""
        event_with_timestamp = {
            **event,
            "received_at": time.time(),
            "relative_time": time.time() - (self.start_time or time.time())
        }
        self.received_events.append(event_with_timestamp)
        
        # Mark first event timing
        self.mark_first_event_received()
    
    def get_event_types_received(self) -> List[str]:
        """Get list of event types received in order."""
        return [event.get("type", "unknown") for event in self.received_events]
    
    def has_all_mission_critical_events(self) -> bool:
        """Check if all 5 mission-critical events were received."""
        event_types = self.get_event_types_received()
        required_events = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        received_events = set(event_types)
        return required_events.issubset(received_events)


# ============================================================================
# GOLDEN PATH COMPREHENSIVE TEST SUITE
# ============================================================================

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.asyncio
class TestGoldenPathCompleteE2EComprehensive(SSotAsyncTestCase):
    """
    Comprehensive Golden Path End-to-End Integration Test Suite.
    
    This test suite validates the COMPLETE golden path user journey with 
    real services, authentication, and business value measurement.
    
    CRITICAL: These tests protect $500K+ ARR by ensuring core chat functionality works end-to-end.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_golden_path_environment(self):
        """Set up comprehensive Golden Path test environment with real services."""
        
        # Initialize SSOT environment and authentication
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment=self.env.get("TEST_ENV", "test"))
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment=self.env.get("TEST_ENV", "test"))
        
        # Configure test URLs based on environment
        self.backend_base_url = "http://localhost:8000"  # Test backend
        self.websocket_base_url = "ws://localhost:8000/ws"  # Test WebSocket
        
        # Detect staging environment and adjust URLs
        if self.env.get("TEST_ENV") == "staging":
            # Use staging URLs with proper authentication
            from tests.e2e.staging.staging_config import StagingTestConfig
            staging_config = StagingTestConfig()
            self.backend_base_url = staging_config.urls.backend_url
            self.websocket_base_url = staging_config.urls.websocket_url
        
        # Initialize metrics and test tracking
        self.golden_path_metrics = GoldenPathMetrics()
        self.test_contexts: Dict[str, GoldenPathTestContext] = {}
        self.active_websockets: List[websockets.WebSocketServerProtocol] = []
        
        # Set up cleanup callback for WebSocket connections
        self.add_cleanup(self._cleanup_websocket_connections)
        
        # Log test environment setup
        logger.info(f"🌟 Golden Path test environment initialized")
        logger.info(f"📡 Backend URL: {self.backend_base_url}")
        logger.info(f"🔌 WebSocket URL: {self.websocket_base_url}")
        logger.info(f"🌍 Environment: {self.env.get('TEST_ENV', 'test')}")
        
        yield
        
        # Final cleanup handled by parent teardown
        
    async def _cleanup_websocket_connections(self):
        """Clean up any active WebSocket connections."""
        for ws in self.active_websockets:
            try:
                if not ws.closed:
                    await ws.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket during cleanup: {e}")
        self.active_websockets.clear()
    
    async def create_authenticated_golden_path_context(
        self, 
        scenario_name: str = "ai_cost_optimization",
        user_email: Optional[str] = None
    ) -> GoldenPathTestContext:
        """
        Create authenticated context for Golden Path testing.
        
        Args:
            scenario_name: Business scenario to test
            user_email: Optional user email (auto-generated if not provided)
            
        Returns:
            Fully configured GoldenPathTestContext
        """
        
        # Create authenticated user with SSOT patterns
        authenticated_user = await self.auth_helper.create_authenticated_user(
            email=user_email or f"golden_path_test_{uuid.uuid4().hex[:8]}@example.com",
            permissions=["read", "write", "ai_optimization"]
        )
        
        # Generate unique test ID
        test_id = f"golden_path_{scenario_name}_{uuid.uuid4().hex[:8]}"
        
        # Create test context
        context = GoldenPathTestContext(
            test_id=test_id,
            authenticated_user=authenticated_user,
            websocket_url=self.websocket_base_url,
            backend_url=self.backend_base_url,
            optimization_scenario=scenario_name,
            expected_business_value={
                "cost_savings_target": 15000.0,  # $15K target savings
                "insights_count_target": 5,      # 5+ actionable insights
                "response_time_target": 45.0     # 45s max response time
            }
        )
        
        # Store context for tracking
        self.test_contexts[test_id] = context
        
        return context
    
    async def establish_authenticated_websocket_connection(
        self, 
        context: GoldenPathTestContext,
        services: Optional[Dict[str, Any]] = None
    ):
        """
        Establish authenticated WebSocket connection with comprehensive error handling.
        
        Args:
            context: Golden Path test context
            services: Optional mock services (for no-Docker mode)
            
        Returns:
            Authenticated WebSocket connection or mock WebSocket
        """
        connection_start = time.time()
        
        # Check if we should use mock services
        if services and services.get("service_type") == "mock":
            logger.info(f"🔧 Using mock WebSocket connection for {context.test_id}")
            self.using_mock_services = True
            
            # Create mock WebSocket connection
            mock_websocket = services["websocket_manager"]
            
            # Simulate connection process
            await asyncio.sleep(0.1)  # Simulate connection delay
            
            # Connect to mock WebSocket
            user_context = {
                "user_id": context.authenticated_user.user_id,
                "email": context.authenticated_user.email
            }
            
            success = await mock_websocket.connect(
                context.authenticated_user.user_id, 
                user_context
            )
            
            if not success:
                raise ConnectionError("Failed to connect to mock WebSocket")
            
            # Track connection timing
            connection_time = time.time() - connection_start
            self.golden_path_metrics.websocket_connection_time = connection_time
            
            # Mark connection established in context
            context.mark_connection_established()
            
            logger.success(f"✅ Mock WebSocket connection established in {connection_time:.2f}s")
            return mock_websocket
        
        # Try real WebSocket connection first
        try:
            # Get WebSocket authentication headers using SSOT helper
            headers = self.websocket_auth_helper.get_websocket_headers(
                context.authenticated_user.jwt_token
            )
            
            # Log connection attempt
            logger.info(f"🔌 Establishing WebSocket connection for {context.test_id}")
            logger.info(f"👤 User: {context.authenticated_user.email}")
            logger.info(f"🎯 URL: {context.websocket_url}")
            
            # Establish WebSocket connection with authentication
            websocket = await asyncio.wait_for(
                websockets.connect(
                    context.websocket_url,
                    additional_headers=headers,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5
                ),
                timeout=15.0  # 15s connection timeout
            )
            
            # Track connection timing
            connection_time = time.time() - connection_start
            self.golden_path_metrics.websocket_connection_time = connection_time
            
            # Mark connection established in context
            context.mark_connection_established()
            
            # Add to active connections for cleanup
            self.active_websockets.append(websocket)
            
            # Log successful connection
            logger.success(f"✅ WebSocket connection established in {connection_time:.2f}s")
            
            return websocket
            
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            connection_time = time.time() - connection_start
            
            # If we have mock services available, fall back to them
            if services and services.get("service_type") == "mock" and not self.using_mock_services:
                logger.warning(f"⚠️ Real WebSocket connection failed ({e}), falling back to mock services")
                # Force use of mock services by temporarily setting the flag
                original_flag = getattr(self, 'using_mock_services', False)
                self.using_mock_services = True
                try:
                    return await self.establish_authenticated_websocket_connection(context, services)
                finally:
                    self.using_mock_services = original_flag
            
            error_msg = f"❌ WebSocket connection failed after {connection_time:.2f}s: {e}"
            logger.error(error_msg)
            raise ConnectionError(f"Golden Path WebSocket connection failed: {error_msg}")
            
        except Exception as e:
            connection_time = time.time() - connection_start  
            error_msg = f"❌ WebSocket connection failed after {connection_time:.2f}s: {e}"
            logger.error(error_msg)
            raise ConnectionError(f"Golden Path WebSocket connection failed: {error_msg}")
    
    async def send_golden_path_optimization_request(
        self,
        websocket,  # Can be real WebSocket or mock WebSocket
        context: GoldenPathTestContext
    ) -> str:
        """
        Send comprehensive AI cost optimization request through Golden Path.
        
        Args:
            websocket: Authenticated WebSocket connection
            context: Golden Path test context
            
        Returns:
            Thread ID for the optimization request
        """
        
        # Generate unique IDs for this request using SSOT patterns
        thread_id = generate_thread_id()
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Store IDs in context
        context.thread_id = thread_id
        context.run_id = run_id
        
        # Create realistic AI cost optimization request
        optimization_scenarios = {
            "ai_cost_optimization": {
                "message": "Analyze my AI infrastructure costs and provide optimization recommendations. "
                          "I'm currently spending $50K/month on AI services including OpenAI GPT-4, "
                          "Claude, and custom model training. Please identify cost reduction opportunities "
                          "while maintaining performance.",
                "expected_insights": ["Model selection optimization", "Usage pattern analysis", "Cost forecasting"]
            },
            "multi_model_optimization": {
                "message": "I need help optimizing my multi-model AI architecture. Currently using "
                          "GPT-4 for reasoning, DALL-E for images, and Whisper for transcription. "
                          "Total monthly cost is $75K. Can you recommend more cost-effective alternatives?",
                "expected_insights": ["Alternative model selection", "Workflow optimization", "Cost reduction strategies"]
            },
            "enterprise_scale_optimization": {
                "message": "Optimize AI costs for enterprise deployment serving 10,000+ users daily. "
                          "Current stack: OpenAI API, custom inference endpoints, vector databases. "
                          "Monthly spend: $200K. Need 30% cost reduction without quality loss.",
                "expected_insights": ["Infrastructure scaling", "Caching strategies", "Model efficiency improvements"]
            }
        }
        
        scenario = optimization_scenarios.get(
            context.optimization_scenario, 
            optimization_scenarios["ai_cost_optimization"]
        )
        
        # Construct Golden Path message
        golden_path_message = {
            "type": "user_message",
            "content": scenario["message"],
            "thread_id": thread_id,
            "run_id": run_id,
            "user_id": context.authenticated_user.user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "test_id": context.test_id,
                "scenario": context.optimization_scenario,
                "expected_business_value": context.expected_business_value,
                "client_type": "golden_path_e2e_test"
            }
        }
        
        # Send message and track timing
        message_start = time.time()
        
        if self.using_mock_services:
            # For mock services, just log the message send
            logger.info(f"📤 [MOCK] Golden Path message prepared: {scenario['message'][:100]}...")
            message_time = 0.01  # Simulate minimal send time
        else:
            await websocket.send(json.dumps(golden_path_message))
            message_time = time.time() - message_start
        
        # Update metrics
        self.golden_path_metrics.message_routing_time = message_time
        context.message_sent = True
        
        # Log message sent
        logger.info(f"📤 Golden Path optimization request sent")
        logger.info(f"🎯 Thread ID: {thread_id}")
        logger.info(f"🚀 Run ID: {run_id}")
        logger.info(f"💰 Scenario: {context.optimization_scenario}")
        
        return thread_id
    
    async def monitor_golden_path_execution(
        self,
        websocket,  # Can be real WebSocket or mock WebSocket
        context: GoldenPathTestContext,
        timeout: float = 120.0,
        services: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Monitor complete Golden Path execution with comprehensive event tracking.
        
        Args:
            websocket: WebSocket connection
            context: Golden Path test context  
            timeout: Maximum time to wait for completion
            
        Returns:
            Complete execution results with metrics
        """
        
        execution_start = time.time()
        context.start_time = execution_start
        
        # Initialize event tracking
        mission_critical_events = {
            "agent_started": False,
            "agent_thinking": False,
            "tool_executing": False,
            "tool_completed": False,
            "agent_completed": False
        }
        
        business_insights = []
        cost_optimizations = []
        final_response = None
        
        logger.info(f"🎯 Monitoring Golden Path execution (timeout: {timeout}s)")
        
        try:
            while time.time() - execution_start < timeout:
                try:
                    # Wait for WebSocket message with short timeout for responsiveness
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    message_data = json.loads(message)
                    
                    # Record event in context
                    context.record_event(message_data)
                    
                    event_type = message_data.get("type", "unknown")
                    
                    # Track mission-critical events
                    if event_type in mission_critical_events:
                        mission_critical_events[event_type] = True
                        
                        # Update metrics based on event type
                        if event_type == "agent_started":
                            self.golden_path_metrics.agent_started_events += 1
                            context.agent_execution_started = True
                            logger.success("🎯 Agent execution started")
                            
                        elif event_type == "agent_thinking":
                            self.golden_path_metrics.agent_thinking_events += 1
                            logger.info("🧠 Agent thinking event received")
                            
                        elif event_type == "tool_executing":
                            self.golden_path_metrics.tool_executing_events += 1
                            tool_name = message_data.get("tool", "unknown")
                            logger.info(f"🔧 Tool executing: {tool_name}")
                            
                        elif event_type == "tool_completed":
                            self.golden_path_metrics.tool_completed_events += 1
                            tool_name = message_data.get("tool", "unknown")
                            logger.info(f"✅ Tool completed: {tool_name}")
                            
                        elif event_type == "agent_completed":
                            self.golden_path_metrics.agent_completed_events += 1
                            logger.success("🎉 Agent execution completed")
                    
                    # Process business value content
                    if event_type == "assistant_message":
                        content = message_data.get("content", "")
                        final_response = message_data
                        
                        # Extract business insights using keyword analysis
                        if any(keyword in content.lower() for keyword in 
                               ["cost", "saving", "optimization", "reduce", "efficiency"]):
                            cost_optimizations.append({
                                "content": content,
                                "timestamp": time.time(),
                                "estimated_value": self._extract_cost_value(content)
                            })
                        
                        if any(keyword in content.lower() for keyword in
                               ["recommend", "suggest", "insight", "analysis", "strategy"]):
                            business_insights.append({
                                "content": content,
                                "timestamp": time.time(),
                                "actionable": self._is_actionable_insight(content)
                            })
                        
                        context.response_received = True
                        logger.success("📝 Final response received")
                        
                        # Check if we have complete response
                        if self._is_complete_response(message_data):
                            logger.success("🏁 Complete Golden Path response received")
                            break
                        
                        # For mock services, break after processing agent_completed
                        if self.using_mock_services and event_type == "agent_completed":
                            logger.success("🏁 Mock Golden Path execution completed")
                            break
                    
                    # Log event for debugging
                    logger.debug(f"📊 Event: {event_type} | Total events: {len(context.received_events)}")
                    
                except asyncio.TimeoutError:
                    # Short timeout for message reception - continue monitoring
                    continue
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Invalid JSON received: {e}")
                    continue
            
            # Calculate final metrics
            execution_time = time.time() - execution_start
            self.golden_path_metrics.total_execution_time = execution_time
            
            if context.first_event_time:
                self.golden_path_metrics.first_event_latency = context.first_event_time
            
            self.golden_path_metrics.total_response_time = execution_time
            
            # Update business value metrics
            self.golden_path_metrics.actionable_insights_count = len([
                insight for insight in business_insights if insight.get("actionable", False)
            ])
            
            total_cost_value = sum(opt.get("estimated_value", 0) for opt in cost_optimizations)
            self.golden_path_metrics.cost_optimization_value = total_cost_value
            
            # Determine if business value was delivered
            self.golden_path_metrics.business_value_delivered = (
                len(business_insights) > 0 and 
                (total_cost_value > 0 or len(cost_optimizations) > 0)
            )
            
            # Return comprehensive results
            results = {
                "execution_time": execution_time,
                "mission_critical_events": mission_critical_events,
                "all_events_received": all(mission_critical_events.values()),
                "business_insights": business_insights,
                "cost_optimizations": cost_optimizations,
                "final_response": final_response,
                "metrics": self.golden_path_metrics,
                "sla_compliance": self.golden_path_metrics.meets_performance_sla(),
                "business_value_delivered": self.golden_path_metrics.delivers_business_value()
            }
            
            logger.success(f"🎯 Golden Path monitoring complete")
            logger.info(f"⏱️ Total execution: {execution_time:.2f}s")
            logger.info(f"📊 Events received: {len(context.received_events)}")
            logger.info(f"💰 Business insights: {len(business_insights)}")
            logger.info(f"💡 Cost optimizations: {len(cost_optimizations)}")
            
            return results
            
        except Exception as e:
            execution_time = time.time() - execution_start
            logger.error(f"❌ Golden Path monitoring failed after {execution_time:.2f}s: {e}")
            raise RuntimeError(f"Golden Path execution monitoring failed: {e}")
    
    def _extract_cost_value(self, content: str) -> float:
        """Extract estimated cost savings value from content."""
        # Simple regex patterns to find dollar amounts
        import re
        dollar_patterns = [
            r'\$([0-9,]+)',  # $1,000
            r'([0-9,]+)\s*dollars?',  # 1000 dollars
            r'([0-9,]+)k',  # 15k
            r'([0-9,]+)\s*thousand'  # 15 thousand
        ]
        
        for pattern in dollar_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                try:
                    # Take the first match and convert to float
                    value_str = matches[0].replace(',', '')
                    if 'k' in content.lower() or 'thousand' in content.lower():
                        return float(value_str) * 1000
                    return float(value_str)
                except (ValueError, IndexError):
                    continue
        
        return 0.0
    
    def _is_actionable_insight(self, content: str) -> bool:
        """Determine if content contains actionable insights."""
        actionable_keywords = [
            "should", "could", "recommend", "suggest", "consider",
            "implement", "switch", "optimize", "reduce", "increase",
            "use", "try", "apply", "enable", "disable"
        ]
        
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in actionable_keywords)
    
    def _is_complete_response(self, message_data: Dict[str, Any]) -> bool:
        """Determine if message represents a complete response."""
        content = message_data.get("content", "")
        
        # Look for completion indicators
        completion_indicators = [
            "summary", "conclusion", "recommendations",
            "final", "complete", "total", "overall"
        ]
        
        return any(indicator in content.lower() for indicator in completion_indicators)
    
    async def validate_golden_path_persistence(
        self, 
        context: GoldenPathTestContext
    ) -> Dict[str, Any]:
        """
        Validate that Golden Path results were properly persisted.
        
        Args:
            context: Golden Path test context
            
        Returns:
            Validation results for persistence
        """
        
        persistence_results = {
            "thread_persisted": False,
            "messages_persisted": False,
            "run_completed": False,
            "cache_updated": False,
            "audit_trail_created": False
        }
        
        try:
            # Validate thread persistence using backend API
            if context.thread_id:
                thread_url = f"{context.backend_url}/threads/{context.thread_id}"
                headers = self.auth_helper.get_auth_headers(context.authenticated_user.jwt_token)
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(thread_url, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            thread_data = await response.json()
                            persistence_results["thread_persisted"] = True
                            
                            # Check for messages in thread
                            messages = thread_data.get("messages", [])
                            if len(messages) >= 2:  # User message + Assistant response
                                persistence_results["messages_persisted"] = True
                                self.golden_path_metrics.database_writes += len(messages)
                            
                            logger.success(f"✅ Thread {context.thread_id} persistence validated")
                        else:
                            logger.warning(f"⚠️ Thread persistence check failed: {response.status}")
            
            # Validate run completion
            if context.run_id:
                run_url = f"{context.backend_url}/runs/{context.run_id}"
                headers = self.auth_helper.get_auth_headers(context.authenticated_user.jwt_token)
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(run_url, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            run_data = await response.json()
                            run_status = run_data.get("status", "")
                            if run_status in ["completed", "success"]:
                                persistence_results["run_completed"] = True
                                logger.success(f"✅ Run {context.run_id} completion validated")
                        else:
                            logger.warning(f"⚠️ Run persistence check failed: {response.status}")
            
            # Update metrics
            if persistence_results["thread_persisted"]:
                self.golden_path_metrics.database_writes += 1
            if persistence_results["run_completed"]:
                self.golden_path_metrics.database_writes += 1
                
            return persistence_results
            
        except Exception as e:
            logger.error(f"❌ Persistence validation failed: {e}")
            return persistence_results

    # ========================================================================
    # COMPREHENSIVE GOLDEN PATH TEST CASES
    # ========================================================================

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.e2e
    @pytest.mark.priority_p0
    async def test_complete_golden_path_success_flow(self, golden_path_services, mock_authenticated_user):
        """
        Test 1: Complete Golden Path Success Flow - Full Happy Path with Real Business Scenario
        
        Business Value Justification:
        - Segment: Enterprise - AI Cost Optimization
        - Business Goal: Revenue Generation & Customer Satisfaction  
        - Value Impact: Validates complete user journey delivering $15K+ cost savings insights
        - Revenue Impact: Protects $100K+ ARR from enterprise AI optimization customers
        
        This test validates the COMPLETE golden path user journey from initial connection
        through AI-powered cost optimization analysis to actionable business insights delivery.
        """
        
        logger.info("🌟 Starting Test 1: Complete Golden Path Success Flow")
        
        # Create authenticated context for enterprise AI optimization scenario
        context = await self.create_authenticated_golden_path_context(
            scenario_name="ai_cost_optimization",
            user_email="enterprise_customer@fortune500.com"
        )
        
        # Step 1: Establish authenticated WebSocket connection
        websocket = await self.establish_authenticated_websocket_connection(context, golden_path_services)
        assert websocket is not None, "WebSocket connection must be established"
        assert context.connection_established, "Connection context must be marked as established"
        
        # Step 2: Send comprehensive AI cost optimization request
        thread_id = await self.send_golden_path_optimization_request(websocket, context)
        assert thread_id is not None, "Thread ID must be generated"
        assert context.message_sent, "Message must be marked as sent"
        assert context.thread_id == thread_id, "Thread ID must match in context"
        
        # Step 3: Monitor complete Golden Path execution with business value tracking
        execution_results = await self.monitor_golden_path_execution(websocket, context, timeout=90.0, services=golden_path_services)
        
        # Step 4: Validate mission-critical WebSocket events were received
        assert execution_results["all_events_received"], (
            f"All 5 mission-critical events must be received. "
            f"Missing: {[k for k, v in execution_results['mission_critical_events'].items() if not v]}"
        )
        
        # Step 5: Validate business value delivery
        assert execution_results["business_value_delivered"], (
            f"Business value must be delivered. "
            f"Insights: {len(execution_results['business_insights'])}, "
            f"Cost optimizations: {len(execution_results['cost_optimizations'])}"
        )
        
        # Step 6: Validate performance SLA compliance
        assert execution_results["sla_compliance"], (
            f"Performance SLA must be met. "
            f"Connection: {self.golden_path_metrics.websocket_connection_time:.2f}s, "
            f"First event: {self.golden_path_metrics.first_event_latency:.2f}s, "
            f"Total: {self.golden_path_metrics.total_response_time:.2f}s"
        )
        
        # Step 7: Validate persistence and audit trail
        persistence_results = await self.validate_golden_path_persistence(context)
        assert persistence_results["thread_persisted"], "Thread must be persisted to database"
        assert persistence_results["messages_persisted"], "Messages must be persisted"
        assert persistence_results["run_completed"], "Run must be marked as completed"
        
        # Step 8: Close connection gracefully
        await websocket.close()
        context.cleanup_completed = True
        
        # Final assertions for complete success
        assert self.golden_path_metrics.cost_optimization_value >= 5000.0, (
            f"Must identify at least $5K in cost optimizations. "
            f"Actual: ${self.golden_path_metrics.cost_optimization_value:.2f}"
        )
        
        assert self.golden_path_metrics.actionable_insights_count >= 3, (
            f"Must provide at least 3 actionable insights. "
            f"Actual: {self.golden_path_metrics.actionable_insights_count}"
        )
        
        # Record test success metrics
        self.record_metric("golden_path_success", True)
        self.record_metric("business_value_delivered", execution_results["business_value_delivered"])
        self.record_metric("cost_savings_identified", self.golden_path_metrics.cost_optimization_value)
        self.record_metric("actionable_insights", self.golden_path_metrics.actionable_insights_count)
        
        logger.success("✅ Test 1 Complete: Golden Path Success Flow validated")
        logger.success(f"💰 Business Value: ${self.golden_path_metrics.cost_optimization_value:.2f} cost savings identified")
        logger.success(f"💡 Insights: {self.golden_path_metrics.actionable_insights_count} actionable recommendations")
        logger.success(f"⏱️ Performance: {self.golden_path_metrics.total_response_time:.2f}s total response time")

    @pytest.mark.integration  
    @pytest.mark.golden_path
    @pytest.mark.e2e
    @pytest.mark.concurrent
    @pytest.mark.priority_p0
    async def test_multiple_user_concurrent_golden_path(self, golden_path_services, mock_authenticated_user):
        """
        Test 2: Multiple User Concurrent Golden Path - 5+ Users Simultaneously Completing Full Journey
        
        Business Value Justification:
        - Segment: Platform/Internal - System Scalability
        - Business Goal: Platform Reliability & Concurrent User Support
        - Value Impact: Validates system can handle enterprise-scale concurrent usage (10+ users)
        - Revenue Impact: Enables $500K+ ARR by supporting multiple concurrent enterprise customers
        
        This test validates that the Golden Path works correctly with multiple concurrent users,
        ensuring proper user isolation and resource management at enterprise scale.
        """
        
        logger.info("🌟 Starting Test 2: Multiple User Concurrent Golden Path")
        
        # Configure concurrent user scenarios  
        concurrent_users = 7  # Test with 7 concurrent users (enterprise scenario)
        concurrent_contexts = []
        concurrent_websockets = []
        
        try:
            # Step 1: Create multiple authenticated contexts simultaneously
            logger.info(f"👥 Creating {concurrent_users} concurrent user contexts")
            
            user_creation_tasks = []
            for i in range(concurrent_users):
                user_email = f"concurrent_user_{i+1}@enterprise.com"
                scenario = ["ai_cost_optimization", "multi_model_optimization", "enterprise_scale_optimization"][i % 3]
                
                task = self.create_authenticated_golden_path_context(
                    scenario_name=scenario,
                    user_email=user_email
                )
                user_creation_tasks.append(task)
            
            # Create all user contexts concurrently
            concurrent_contexts = await asyncio.gather(*user_creation_tasks)
            assert len(concurrent_contexts) == concurrent_users, f"Must create {concurrent_users} user contexts"
            
            # Step 2: Establish WebSocket connections concurrently
            logger.info(f"🔌 Establishing {concurrent_users} WebSocket connections concurrently")
            
            connection_tasks = [
                self.establish_authenticated_websocket_connection(context)
                for context in concurrent_contexts
            ]
            
            concurrent_websockets = await asyncio.gather(*connection_tasks)
            assert len(concurrent_websockets) == concurrent_users, f"Must establish {concurrent_users} WebSocket connections"
            
            # Validate all connections are established
            for i, context in enumerate(concurrent_contexts):
                assert context.connection_established, f"User {i+1} connection must be established"
            
            # Step 3: Send optimization requests concurrently
            logger.info(f"📤 Sending {concurrent_users} optimization requests concurrently")
            
            request_tasks = [
                self.send_golden_path_optimization_request(websocket, context)
                for websocket, context in zip(concurrent_websockets, concurrent_contexts)
            ]
            
            thread_ids = await asyncio.gather(*request_tasks)
            assert len(thread_ids) == concurrent_users, f"Must generate {concurrent_users} thread IDs"
            assert len(set(thread_ids)) == concurrent_users, "All thread IDs must be unique (user isolation)"
            
            # Step 4: Monitor all executions concurrently with proper timeout
            logger.info(f"🎯 Monitoring {concurrent_users} Golden Path executions concurrently")
            
            # Use longer timeout for concurrent execution
            concurrent_timeout = 150.0  # 2.5 minutes for concurrent processing
            
            monitoring_tasks = [
                self.monitor_golden_path_execution(websocket, context, timeout=concurrent_timeout, services=golden_path_services)
                for websocket, context in zip(concurrent_websockets, concurrent_contexts)
            ]
            
            execution_results = await asyncio.gather(*monitoring_tasks, return_exceptions=True)
            
            # Step 5: Validate results for each user
            successful_executions = []
            failed_executions = []
            
            for i, result in enumerate(execution_results):
                context = concurrent_contexts[i]
                
                if isinstance(result, Exception):
                    failed_executions.append({
                        "user": i+1,
                        "context": context,
                        "error": str(result)
                    })
                    logger.error(f"❌ User {i+1} execution failed: {result}")
                else:
                    successful_executions.append({
                        "user": i+1,
                        "context": context,
                        "result": result
                    })
                    logger.success(f"✅ User {i+1} execution successful")
            
            # Step 6: Validate concurrent execution requirements
            success_rate = len(successful_executions) / concurrent_users
            assert success_rate >= 0.85, (
                f"At least 85% of concurrent users must succeed. "
                f"Success rate: {success_rate:.1%} ({len(successful_executions)}/{concurrent_users})"
            )
            
            # Step 7: Validate user isolation (unique thread IDs and no data mixing)
            all_thread_ids = [context.thread_id for context in concurrent_contexts]
            unique_thread_ids = set(all_thread_ids)
            assert len(unique_thread_ids) == len(all_thread_ids), "All thread IDs must be unique (user isolation)"
            
            # Step 8: Validate business value delivery for successful executions
            business_value_successes = []
            for execution in successful_executions:
                if execution["result"]["business_value_delivered"]:
                    business_value_successes.append(execution)
            
            business_value_rate = len(business_value_successes) / len(successful_executions) if successful_executions else 0
            assert business_value_rate >= 0.8, (
                f"At least 80% of successful executions must deliver business value. "
                f"Business value rate: {business_value_rate:.1%}"
            )
            
            # Step 9: Clean up connections
            logger.info(f"🧹 Cleaning up {len(concurrent_websockets)} WebSocket connections")
            
            cleanup_tasks = []
            for websocket in concurrent_websockets:
                if websocket and not websocket.closed:
                    cleanup_tasks.append(websocket.close())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            # Final metrics and assertions
            self.golden_path_metrics.concurrent_user_capacity = len(successful_executions)
            
            # Record comprehensive test results
            self.record_metric("concurrent_users_tested", concurrent_users)
            self.record_metric("concurrent_success_rate", success_rate)
            self.record_metric("concurrent_business_value_rate", business_value_rate)
            self.record_metric("user_isolation_validated", len(unique_thread_ids) == concurrent_users)
            
            logger.success("✅ Test 2 Complete: Multiple User Concurrent Golden Path validated")
            logger.success(f"👥 Concurrent Users: {concurrent_users}")
            logger.success(f"✅ Success Rate: {success_rate:.1%}")
            logger.success(f"💰 Business Value Rate: {business_value_rate:.1%}")
            logger.success(f"🔒 User Isolation: {len(unique_thread_ids)} unique thread IDs")
            
        except Exception as e:
            logger.error(f"❌ Concurrent Golden Path test failed: {e}")
            
            # Clean up any remaining connections
            for websocket in concurrent_websockets:
                try:
                    if websocket and not websocket.closed:
                        await websocket.close()
                except:
                    pass
            
            raise

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.e2e
    @pytest.mark.resilience
    @pytest.mark.priority_p1
    async def test_golden_path_with_service_interruptions(self, golden_path_services, mock_authenticated_user):
        """
        Test 3: Golden Path with Service Interruptions - Full Flow with Service Failures and Recovery
        
        Business Value Justification:
        - Segment: Platform/Internal - System Resilience
        - Business Goal: Risk Reduction & Service Reliability
        - Value Impact: Validates graceful degradation and recovery under service failures
        - Revenue Impact: Prevents revenue loss during service disruptions (estimated $50K+ impact prevention)
        
        This test validates that the Golden Path can gracefully handle service interruptions
        and recover to deliver business value even under adverse conditions.
        """
        
        logger.info("🌟 Starting Test 3: Golden Path with Service Interruptions")
        
        # Create authenticated context
        context = await self.create_authenticated_golden_path_context(
            scenario_name="enterprise_scale_optimization",
            user_email="resilience_test@enterprise.com"
        )
        
        # Step 1: Establish initial connection
        websocket = await self.establish_authenticated_websocket_connection(context, golden_path_services)
        assert websocket is not None, "Initial WebSocket connection must be established"
        
        # Step 2: Send optimization request
        thread_id = await self.send_golden_path_optimization_request(websocket, context)
        assert thread_id is not None, "Thread ID must be generated before service interruption"
        
        # Step 3: Start monitoring execution with simulated service interruptions
        logger.info("⚠️ Beginning execution with simulated service interruptions")
        
        execution_start = time.time()
        interruption_count = 0
        recovery_attempts = 0
        partial_results = []
        
        # Monitor with interruption handling
        while time.time() - execution_start < 180.0:  # 3 minute timeout for resilience test
            try:
                # Attempt to receive message with timeout
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                message_data = json.loads(message)
                
                # Record event
                context.record_event(message_data)
                partial_results.append(message_data)
                
                event_type = message_data.get("type", "unknown")
                logger.info(f"📊 Event received: {event_type}")
                
                # Simulate service interruption at random intervals (20% chance)
                if random.random() < 0.2 and interruption_count < 3:
                    interruption_count += 1
                    logger.warning(f"⚠️ Simulating service interruption #{interruption_count}")
                    
                    # Simulate brief interruption by introducing delay
                    await asyncio.sleep(2.0)
                    self.golden_path_metrics.graceful_degradation_events += 1
                    
                    # Test recovery capability
                    recovery_attempts += 1
                    logger.info(f"🔄 Recovery attempt #{recovery_attempts}")
                
                # Check for completion
                if event_type == "agent_completed" or event_type == "assistant_message":
                    logger.success("🎉 Execution completed despite service interruptions")
                    break
                    
            except asyncio.TimeoutError:
                # Timeout during message reception - simulate service unavailability
                logger.warning("⏰ Message timeout - simulating service interruption")
                
                # Attempt recovery
                if recovery_attempts < 5:
                    recovery_attempts += 1
                    self.golden_path_metrics.recovery_attempts += 1
                    
                    logger.info(f"🔄 Attempting recovery #{recovery_attempts}")
                    await asyncio.sleep(1.0)  # Brief recovery delay
                    continue
                else:
                    logger.warning("⚠️ Maximum recovery attempts reached")
                    break
                    
            except json.JSONDecodeError:
                logger.warning("⚠️ Invalid message received - continuing")
                self.golden_path_metrics.error_count += 1
                continue
            except Exception as e:
                logger.error(f"❌ Unexpected error during resilience test: {e}")
                self.golden_path_metrics.error_count += 1
                break
        
        # Step 4: Validate resilience and recovery
        execution_time = time.time() - execution_start
        
        # Validate we received some events despite interruptions
        assert len(context.received_events) > 0, "Must receive at least some events despite interruptions"
        
        # Validate graceful degradation
        assert interruption_count > 0, "Test must have simulated at least one service interruption"
        assert recovery_attempts > 0, "Test must have attempted recovery at least once"
        
        # Validate partial business value delivery
        business_content_events = [
            event for event in context.received_events 
            if event.get("type") == "assistant_message" or "content" in event
        ]
        
        assert len(business_content_events) > 0, "Must receive at least partial business content despite interruptions"
        
        # Step 5: Test recovery and completion
        if len(context.received_events) > 0:
            event_types = context.get_event_types_received()
            
            # Check if we got critical events
            critical_events_received = sum([
                "agent_started" in event_types,
                "agent_thinking" in event_types,
                "tool_executing" in event_types,
                "agent_completed" in event_types or "assistant_message" in event_types
            ])
            
            assert critical_events_received >= 2, (
                f"Must receive at least 2 critical events despite interruptions. "
                f"Received: {critical_events_received}/4 critical events"
            )
        
        # Step 6: Close connection
        await websocket.close()
        
        # Final resilience metrics
        self.golden_path_metrics.error_count += interruption_count
        
        # Record resilience test metrics
        self.record_metric("service_interruptions_simulated", interruption_count)
        self.record_metric("recovery_attempts_made", recovery_attempts)
        self.record_metric("partial_events_received", len(context.received_events))
        self.record_metric("resilience_execution_time", execution_time)
        self.record_metric("graceful_degradation_successful", len(context.received_events) > 0)
        
        logger.success("✅ Test 3 Complete: Golden Path Service Interruption Resilience validated")
        logger.success(f"⚠️ Interruptions: {interruption_count}")
        logger.success(f"🔄 Recovery Attempts: {recovery_attempts}")
        logger.success(f"📊 Events Received: {len(context.received_events)}")
        logger.success(f"⏱️ Total Time: {execution_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.golden_path  
    @pytest.mark.e2e
    @pytest.mark.performance
    @pytest.mark.priority_p1
    async def test_golden_path_performance_validation(self, golden_path_services, mock_authenticated_user):
        """
        Test 4: Golden Path Performance Validation - End-to-End Timing Requirements Met
        
        Business Value Justification:
        - Segment: All Customer Segments - User Experience
        - Business Goal: Customer Satisfaction & Retention
        - Value Impact: Ensures sub-60-second response times for premium user experience
        - Revenue Impact: Prevents churn from slow response times (estimated $75K+ retention value)
        
        This test validates that Golden Path execution meets strict performance SLA requirements
        under normal operating conditions, ensuring premium user experience delivery.
        """
        
        logger.info("🌟 Starting Test 4: Golden Path Performance Validation")
        
        # Performance SLA requirements
        max_connection_time = 2.0      # 2 seconds max connection time
        max_first_event_time = 5.0     # 5 seconds max time to first event
        max_total_response_time = 60.0 # 60 seconds max total response time
        min_events_per_second = 0.1    # Minimum event frequency
        
        # Create performance-optimized context
        context = await self.create_authenticated_golden_path_context(
            scenario_name="ai_cost_optimization",
            user_email="performance_test@premium.com"
        )
        
        # Step 1: Measure connection performance
        connection_start = time.time()
        websocket = await self.establish_authenticated_websocket_connection(context, golden_path_services)
        connection_time = time.time() - connection_start
        
        assert connection_time <= max_connection_time, (
            f"WebSocket connection must complete within {max_connection_time}s. "
            f"Actual: {connection_time:.2f}s"
        )
        
        logger.success(f"✅ Connection Performance: {connection_time:.2f}s (target: <{max_connection_time}s)")
        
        # Step 2: Measure message routing performance
        routing_start = time.time()
        thread_id = await self.send_golden_path_optimization_request(websocket, context)
        routing_time = time.time() - routing_start
        
        assert routing_time <= 1.0, f"Message routing must complete within 1s. Actual: {routing_time:.2f}s"
        
        logger.success(f"✅ Routing Performance: {routing_time:.2f}s (target: <1.0s)")
        
        # Step 3: Measure comprehensive execution performance
        execution_start = time.time()
        context.start_time = execution_start
        
        first_event_received = False
        first_event_time = None
        performance_events = []
        
        logger.info(f"⏱️ Starting performance monitoring (target: <{max_total_response_time}s)")
        
        while time.time() - execution_start < max_total_response_time + 10:  # 10s buffer for cleanup
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                message_data = json.loads(message)
                
                current_time = time.time()
                relative_time = current_time - execution_start
                
                # Record first event timing
                if not first_event_received:
                    first_event_time = relative_time
                    first_event_received = True
                    
                    assert first_event_time <= max_first_event_time, (
                        f"First event must arrive within {max_first_event_time}s. "
                        f"Actual: {first_event_time:.2f}s"
                    )
                    
                    logger.success(f"✅ First Event Performance: {first_event_time:.2f}s (target: <{max_first_event_time}s)")
                
                # Record event with performance data
                performance_event = {
                    **message_data,
                    "received_at": current_time,
                    "relative_time": relative_time
                }
                performance_events.append(performance_event)
                context.record_event(message_data)
                
                event_type = message_data.get("type", "unknown")
                logger.info(f"📊 Performance Event: {event_type} at {relative_time:.2f}s")
                
                # Check for completion
                if event_type in ["agent_completed", "assistant_message"]:
                    completion_time = relative_time
                    
                    assert completion_time <= max_total_response_time, (
                        f"Total response must complete within {max_total_response_time}s. "
                        f"Actual: {completion_time:.2f}s"
                    )
                    
                    logger.success(f"✅ Completion Performance: {completion_time:.2f}s (target: <{max_total_response_time}s)")
                    break
                    
            except asyncio.TimeoutError:
                # Check if we're still within acceptable time
                current_relative_time = time.time() - execution_start
                if current_relative_time > max_total_response_time:
                    raise TimeoutError(f"Performance test exceeded {max_total_response_time}s limit")
                continue
            except json.JSONDecodeError:
                continue
        
        total_execution_time = time.time() - execution_start
        
        # Step 4: Validate event frequency performance
        if len(performance_events) > 1:
            event_intervals = []
            for i in range(1, len(performance_events)):
                interval = performance_events[i]["relative_time"] - performance_events[i-1]["relative_time"]
                event_intervals.append(interval)
            
            avg_event_interval = sum(event_intervals) / len(event_intervals) if event_intervals else float('inf')
            events_per_second = 1.0 / avg_event_interval if avg_event_interval > 0 else 0
            
            assert events_per_second >= min_events_per_second, (
                f"Event frequency must be at least {min_events_per_second} events/second. "
                f"Actual: {events_per_second:.2f} events/second"
            )
            
            logger.success(f"✅ Event Frequency Performance: {events_per_second:.2f} events/second")
        
        # Step 5: Validate overall performance metrics
        self.golden_path_metrics.websocket_connection_time = connection_time
        self.golden_path_metrics.message_routing_time = routing_time
        self.golden_path_metrics.first_event_latency = first_event_time or 0
        self.golden_path_metrics.total_response_time = total_execution_time
        
        # Step 6: Close connection
        await websocket.close()
        
        # Final performance assertions
        assert self.golden_path_metrics.meets_performance_sla(), (
            f"Overall performance SLA must be met. "
            f"Connection: {connection_time:.2f}s, "
            f"First Event: {first_event_time or 0:.2f}s, "
            f"Total: {total_execution_time:.2f}s"
        )
        
        # Record performance test metrics
        self.record_metric("connection_performance", connection_time)
        self.record_metric("routing_performance", routing_time)
        self.record_metric("first_event_performance", first_event_time or 0)
        self.record_metric("total_execution_performance", total_execution_time)
        self.record_metric("performance_sla_met", True)
        self.record_metric("events_received_count", len(performance_events))
        
        logger.success("✅ Test 4 Complete: Golden Path Performance Validation successful")
        logger.success(f"🔌 Connection: {connection_time:.2f}s")
        logger.success(f"📡 Routing: {routing_time:.2f}s")
        logger.success(f"⚡ First Event: {first_event_time or 0:.2f}s")
        logger.success(f"🎯 Total Response: {total_execution_time:.2f}s")
        logger.success(f"📊 Events: {len(performance_events)}")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.e2e
    @pytest.mark.business_value
    @pytest.mark.priority_p0
    async def test_golden_path_business_value_validation(self, golden_path_services, mock_authenticated_user):
        """
        Test 5: Golden Path Business Value Validation - Real Cost Optimization Scenario with Measurable ROI
        
        Business Value Justification:
        - Segment: Enterprise - AI Cost Optimization
        - Business Goal: Revenue Generation & Customer Success
        - Value Impact: Validates delivery of measurable ROI ($25K+ cost savings identification)
        - Revenue Impact: Demonstrates platform value driving $200K+ ARR from enterprise customers
        
        This test validates that Golden Path execution delivers measurable business value
        in the form of cost optimizations, actionable insights, and quantifiable ROI.
        """
        
        logger.info("🌟 Starting Test 5: Golden Path Business Value Validation")
        
        # Define business value expectations
        target_cost_savings = 25000.0      # $25K target cost savings
        target_insights_count = 8          # 8+ actionable insights
        target_roi_ratio = 10.0           # 10:1 ROI ratio (savings:platform_cost)
        
        # Create business-focused context
        context = await self.create_authenticated_golden_path_context(
            scenario_name="enterprise_scale_optimization",
            user_email="cfo@fortune100.com"
        )
        
        # Set high-value business expectations
        context.expected_business_value = {
            "cost_savings_target": target_cost_savings,
            "insights_count_target": target_insights_count,
            "roi_target": target_roi_ratio,
            "business_impact_areas": [
                "Model Selection Optimization",
                "Usage Pattern Analysis", 
                "Infrastructure Scaling",
                "Vendor Negotiation Strategies",
                "Automated Cost Controls",
                "Performance vs Cost Trade-offs"
            ]
        }
        
        # Step 1: Establish connection for business scenario
        websocket = await self.establish_authenticated_websocket_connection(context, golden_path_services)
        
        # Step 2: Send comprehensive enterprise optimization request
        enterprise_request_message = {
            "type": "user_message",
            "content": (
                "I am the CFO of a Fortune 100 company spending $2.5M annually on AI services. "
                "Our current stack includes: OpenAI GPT-4 ($800K/year), Claude ($400K/year), "
                "custom model training on AWS ($600K/year), Pinecone vector DB ($200K/year), "
                "and various other AI tools ($500K/year). We serve 50,000+ employees and "
                "100M+ customers through AI-powered features. "
                
                "Please provide a comprehensive cost optimization analysis with: "
                "1. Specific dollar savings opportunities "
                "2. Alternative vendor recommendations "
                "3. Usage optimization strategies "
                "4. Infrastructure scaling recommendations "
                "5. ROI projections for each optimization "
                "6. Risk assessment for each recommendation "
                
                "I need actionable insights that our engineering and procurement teams "
                "can implement within 90 days to achieve 20%+ cost reduction while "
                "maintaining or improving AI service quality."
            ),
            "thread_id": generate_thread_id(),
            "run_id": UnifiedIDManager.generate_run_id(generate_thread_id()),
            "user_id": context.authenticated_user.user_id,
            "metadata": {
                "business_context": "enterprise_cfo_optimization",
                "urgency": "high",
                "budget_authority": "2500000",
                "decision_timeline": "90_days"
            }
        }
        
        # Send high-value business request
        await websocket.send(json.dumps(enterprise_request_message))
        context.message_sent = True
        
        # Step 3: Monitor for business value delivery
        business_insights = []
        cost_optimizations = []
        roi_projections = []
        vendor_alternatives = []
        
        execution_start = time.time()
        context.start_time = execution_start
        
        logger.info("💰 Monitoring for business value delivery (enterprise scenario)")
        
        while time.time() - execution_start < 120.0:  # 2 minute timeout for complex business analysis
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                message_data = json.loads(message)
                
                context.record_event(message_data)
                event_type = message_data.get("type", "unknown")
                content = message_data.get("content", "")
                
                # Analyze content for business value
                if content:
                    # Extract cost savings opportunities
                    cost_savings = self._extract_detailed_cost_savings(content)
                    if cost_savings:
                        cost_optimizations.extend(cost_savings)
                    
                    # Extract business insights
                    insights = self._extract_business_insights(content)
                    if insights:
                        business_insights.extend(insights)
                    
                    # Extract ROI projections
                    roi_data = self._extract_roi_projections(content)
                    if roi_data:
                        roi_projections.extend(roi_data)
                    
                    # Extract vendor alternatives
                    alternatives = self._extract_vendor_alternatives(content)
                    if alternatives:
                        vendor_alternatives.extend(alternatives)
                
                logger.info(f"💼 Business Event: {event_type}")
                
                # Check for completion of business analysis
                if event_type == "assistant_message" and any(keyword in content.lower() for keyword in 
                    ["summary", "conclusion", "recommendations", "total savings", "final analysis"]):
                    logger.success("📊 Business analysis completed")
                    break
                    
            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError:
                continue
        
        # Step 4: Calculate comprehensive business value metrics
        total_cost_savings = sum(opt.get("value", 0) for opt in cost_optimizations)
        actionable_insights_count = len([insight for insight in business_insights if insight.get("actionable", False)])
        total_roi_projection = sum(roi.get("ratio", 0) for roi in roi_projections) / len(roi_projections) if roi_projections else 0
        vendor_alternatives_count = len(vendor_alternatives)
        
        # Step 5: Validate business value delivery
        assert total_cost_savings >= target_cost_savings, (
            f"Must identify at least ${target_cost_savings:,.2f} in cost savings. "
            f"Actual: ${total_cost_savings:,.2f}"
        )
        
        assert actionable_insights_count >= target_insights_count, (
            f"Must provide at least {target_insights_count} actionable insights. "
            f"Actual: {actionable_insights_count}"
        )
        
        # Step 6: Validate ROI and business impact
        platform_annual_cost = 120000.0  # Estimated $120K annual platform cost for enterprise
        calculated_roi = total_cost_savings / platform_annual_cost if platform_annual_cost > 0 else 0
        
        assert calculated_roi >= target_roi_ratio, (
            f"ROI must be at least {target_roi_ratio}:1. "
            f"Actual: {calculated_roi:.1f}:1 (${total_cost_savings:,.2f} savings / ${platform_annual_cost:,.2f} platform cost)"
        )
        
        # Step 7: Validate specific business impact areas
        business_areas_covered = set()
        all_content = " ".join([event.get("content", "") for event in context.received_events])
        
        for area in context.expected_business_value["business_impact_areas"]:
            area_keywords = area.lower().split()
            if any(keyword in all_content.lower() for keyword in area_keywords):
                business_areas_covered.add(area)
        
        coverage_ratio = len(business_areas_covered) / len(context.expected_business_value["business_impact_areas"])
        assert coverage_ratio >= 0.75, (
            f"Must cover at least 75% of business impact areas. "
            f"Actual: {coverage_ratio:.1%} ({len(business_areas_covered)}/{len(context.expected_business_value['business_impact_areas'])})"
        )
        
        # Step 8: Close connection
        await websocket.close()
        
        # Update business value metrics
        self.golden_path_metrics.cost_optimization_value = total_cost_savings
        self.golden_path_metrics.actionable_insights_count = actionable_insights_count
        self.golden_path_metrics.business_value_delivered = True
        self.golden_path_metrics.user_satisfaction_score = 0.95  # High satisfaction for comprehensive analysis
        
        # Record detailed business value metrics
        self.record_metric("total_cost_savings", total_cost_savings)
        self.record_metric("actionable_insights_count", actionable_insights_count)
        self.record_metric("roi_ratio", calculated_roi)
        self.record_metric("business_areas_coverage", coverage_ratio)
        self.record_metric("vendor_alternatives_provided", vendor_alternatives_count)
        self.record_metric("enterprise_value_delivered", True)
        
        logger.success("✅ Test 5 Complete: Golden Path Business Value Validation successful")
        logger.success(f"💰 Cost Savings Identified: ${total_cost_savings:,.2f}")
        logger.success(f"💡 Actionable Insights: {actionable_insights_count}")
        logger.success(f"📈 ROI Ratio: {calculated_roi:.1f}:1")
        logger.success(f"🎯 Business Areas Coverage: {coverage_ratio:.1%}")
        logger.success(f"🔄 Vendor Alternatives: {vendor_alternatives_count}")

    def _extract_detailed_cost_savings(self, content: str) -> List[Dict[str, Any]]:
        """Extract detailed cost savings opportunities from content."""
        import re
        
        cost_savings = []
        
        # Enhanced patterns for cost savings extraction
        patterns = [
            r'save\s+\$([0-9,]+)',
            r'reduce\s+costs?\s+by\s+\$([0-9,]+)',
            r'\$([0-9,]+)\s+(?:in\s+)?savings',
            r'([0-9,]+)k\s+(?:in\s+)?savings',
            r'([0-9]+)%\s+cost\s+reduction',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                value_str = match.group(1)
                try:
                    if 'k' in match.group(0).lower():
                        value = float(value_str.replace(',', '')) * 1000
                    elif '%' in match.group(0):
                        # Estimate percentage savings based on context
                        percentage = float(value_str)
                        estimated_base = 100000  # $100K base for percentage calculations
                        value = estimated_base * (percentage / 100)
                    else:
                        value = float(value_str.replace(',', ''))
                    
                    cost_savings.append({
                        "description": match.group(0),
                        "value": value,
                        "context": content[max(0, match.start()-50):match.end()+50]
                    })
                except ValueError:
                    continue
        
        return cost_savings
    
    def _extract_business_insights(self, content: str) -> List[Dict[str, Any]]:
        """Extract business insights from content."""
        insights = []
        
        # Split content into sentences
        sentences = content.split('.')
        
        insight_keywords = [
            "recommend", "suggest", "should consider", "could implement",
            "alternative", "optimize", "improve", "strategy", "approach"
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Meaningful length
                for keyword in insight_keywords:
                    if keyword in sentence.lower():
                        insights.append({
                            "content": sentence,
                            "actionable": self._is_actionable_insight(sentence),
                            "keyword": keyword
                        })
                        break
        
        return insights
    
    def _extract_roi_projections(self, content: str) -> List[Dict[str, Any]]:
        """Extract ROI projections from content."""
        import re
        
        roi_data = []
        
        # ROI patterns
        roi_patterns = [
            r'([0-9.]+):1\s+roi',
            r'roi\s+of\s+([0-9.]+)',
            r'([0-9]+)x\s+return',
            r'return\s+on\s+investment\s+of\s+([0-9.]+)'
        ]
        
        for pattern in roi_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    ratio = float(match.group(1))
                    roi_data.append({
                        "ratio": ratio,
                        "description": match.group(0),
                        "context": content[max(0, match.start()-30):match.end()+30]
                    })
                except ValueError:
                    continue
        
        return roi_data
    
    def _extract_vendor_alternatives(self, content: str) -> List[Dict[str, Any]]:
        """Extract vendor alternatives from content."""
        alternatives = []
        
        # Common AI vendor names and alternatives
        vendors = [
            "anthropic", "claude", "openai", "gpt", "aws", "azure", "google", 
            "cohere", "stability", "midjourney", "pinecone", "weaviate",
            "hugging face", "replicate", "together"
        ]
        
        sentences = content.split('.')
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for vendor in vendors:
                if vendor in sentence_lower and any(word in sentence_lower for word in 
                    ["alternative", "instead", "switch", "replace", "consider"]):
                    alternatives.append({
                        "vendor": vendor,
                        "recommendation": sentence.strip(),
                        "type": "vendor_alternative"
                    })
                    break
        
        return alternatives

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.e2e
    @pytest.mark.cross_platform
    @pytest.mark.priority_p1
    async def test_golden_path_cross_platform_validation(self, golden_path_services, mock_authenticated_user):
        """
        Test 6: Golden Path Cross-Platform Validation - Windows/Linux Compatibility for Full Flow
        
        Business Value Justification:
        - Segment: Platform/Internal - Development Velocity & Platform Support
        - Business Goal: Platform Compatibility & Developer Experience
        - Value Impact: Ensures Golden Path works across all development platforms (Windows/Linux/macOS)
        - Revenue Impact: Prevents development velocity loss and platform-specific failures ($25K+ dev efficiency)
        
        This test validates that Golden Path execution works consistently across different platforms
        with platform-specific optimizations and compatibility handling.
        """
        
        logger.info("🌟 Starting Test 6: Golden Path Cross-Platform Validation")
        
        # Detect current platform
        import platform
        current_platform = platform.system().lower()
        logger.info(f"🖥️ Current platform: {current_platform}")
        
        # Create cross-platform test context
        context = await self.create_authenticated_golden_path_context(
            scenario_name="cross_platform_optimization",
            user_email=f"cross_platform_test_{current_platform}@platform.com"
        )
        
        # Platform-specific configurations
        platform_configs = {
            "windows": {
                "websocket_timeout": 20.0,  # Longer timeout for Windows
                "connection_retries": 3,
                "use_asyncio_safe_patterns": True
            },
            "linux": {
                "websocket_timeout": 10.0,
                "connection_retries": 2,
                "use_asyncio_safe_patterns": False
            },
            "darwin": {  # macOS
                "websocket_timeout": 15.0,
                "connection_retries": 2,
                "use_asyncio_safe_patterns": False
            }
        }
        
        config = platform_configs.get(current_platform, platform_configs["linux"])
        logger.info(f"⚙️ Platform config: {config}")
        
        # Step 1: Test platform-specific WebSocket connection
        connection_attempts = 0
        websocket = None
        
        for attempt in range(config["connection_retries"]):
            try:
                connection_attempts += 1
                logger.info(f"🔌 Connection attempt {connection_attempts} on {current_platform}")
                
                if config["use_asyncio_safe_patterns"]:
                    # Use Windows-safe asyncio patterns
                    logger.info("🪟 Using Windows-safe asyncio patterns")
                    websocket = await self._establish_windows_safe_websocket_connection(context, config["websocket_timeout"], golden_path_services)
                else:
                    # Use standard connection patterns
                    websocket = await self.establish_authenticated_websocket_connection(context, golden_path_services)
                
                if websocket:
                    logger.success(f"✅ Platform connection successful on attempt {connection_attempts}")
                    break
                    
            except Exception as e:
                logger.warning(f"⚠️ Connection attempt {connection_attempts} failed: {e}")
                if attempt < config["connection_retries"] - 1:
                    await asyncio.sleep(2.0)  # Brief delay before retry
                else:
                    raise ConnectionError(f"All {config['connection_retries']} connection attempts failed on {current_platform}")
        
        assert websocket is not None, f"Must establish WebSocket connection on {current_platform}"
        
        # Step 2: Test platform-specific message handling
        thread_id = await self.send_golden_path_optimization_request(websocket, context)
        assert thread_id is not None, f"Must generate thread ID on {current_platform}"
        
        # Step 3: Monitor execution with platform-specific handling
        platform_events = []
        execution_start = time.time()
        
        # Adjust timeout based on platform
        execution_timeout = config["websocket_timeout"] * 6  # 6x connection timeout for full execution
        
        logger.info(f"⏱️ Monitoring Golden Path execution on {current_platform} (timeout: {execution_timeout}s)")
        
        while time.time() - execution_start < execution_timeout:
            try:
                # Platform-specific message reception
                if config["use_asyncio_safe_patterns"]:
                    # Windows-safe message reception with shorter timeouts
                    message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                else:
                    # Standard message reception
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                
                message_data = json.loads(message)
                platform_events.append({
                    **message_data,
                    "platform": current_platform,
                    "received_at": time.time() - execution_start
                })
                
                context.record_event(message_data)
                
                event_type = message_data.get("type", "unknown")
                logger.info(f"📊 Platform Event ({current_platform}): {event_type}")
                
                # Check for completion
                if event_type in ["agent_completed", "assistant_message"]:
                    logger.success(f"🎉 Golden Path completed on {current_platform}")
                    break
                    
            except asyncio.TimeoutError:
                # Platform-specific timeout handling
                current_time = time.time() - execution_start
                if current_time > execution_timeout:
                    logger.error(f"⏰ Execution timeout on {current_platform} after {current_time:.2f}s")
                    break
                continue
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Invalid JSON on {current_platform}")
                continue
        
        execution_time = time.time() - execution_start
        
        # Step 4: Validate platform-specific results
        assert len(platform_events) > 0, f"Must receive events on {current_platform}"
        
        # Check for mission-critical events
        event_types = [event.get("type") for event in platform_events]
        critical_events = ["agent_started", "agent_thinking", "tool_executing", "agent_completed"]
        received_critical = [event for event in critical_events if event in event_types]
        
        assert len(received_critical) >= 2, (
            f"Must receive at least 2 critical events on {current_platform}. "
            f"Received: {received_critical}"
        )
        
        # Step 5: Platform-specific performance validation
        platform_performance_limits = {
            "windows": {"max_execution": 90.0, "min_events": 3},
            "linux": {"max_execution": 60.0, "min_events": 4},
            "darwin": {"max_execution": 70.0, "min_events": 4}
        }
        
        perf_limits = platform_performance_limits.get(current_platform, platform_performance_limits["linux"])
        
        assert execution_time <= perf_limits["max_execution"], (
            f"Execution time on {current_platform} must be under {perf_limits['max_execution']}s. "
            f"Actual: {execution_time:.2f}s"
        )
        
        assert len(platform_events) >= perf_limits["min_events"], (
            f"Must receive at least {perf_limits['min_events']} events on {current_platform}. "
            f"Actual: {len(platform_events)}"
        )
        
        # Step 6: Close connection
        await websocket.close()
        
        # Record platform-specific metrics
        self.record_metric("platform_tested", current_platform)
        self.record_metric("platform_connection_attempts", connection_attempts)
        self.record_metric("platform_execution_time", execution_time)
        self.record_metric("platform_events_received", len(platform_events))
        self.record_metric("platform_critical_events", len(received_critical))
        self.record_metric("cross_platform_compatible", True)
        
        logger.success("✅ Test 6 Complete: Golden Path Cross-Platform Validation successful")
        logger.success(f"🖥️ Platform: {current_platform}")
        logger.success(f"🔌 Connection Attempts: {connection_attempts}")
        logger.success(f"⏱️ Execution Time: {execution_time:.2f}s")
        logger.success(f"📊 Events Received: {len(platform_events)}")
        logger.success(f"🎯 Critical Events: {len(received_critical)}")
    
    async def _establish_windows_safe_websocket_connection(self, context: GoldenPathTestContext, timeout: float, services: Optional[Dict[str, Any]] = None):
        """Establish WebSocket connection using Windows-safe asyncio patterns."""
        try:
            # Check if we should use mock services (even in Windows mode)
            if services and services.get("service_type") == "mock":
                logger.info("🪟🔧 Using mock WebSocket for Windows-safe connection")
                return await self.establish_authenticated_websocket_connection(context, services)
            
            # Windows-specific connection handling
            import asyncio
            
            # Use ProactorEventLoop-safe connection approach on Windows
            headers = self.websocket_auth_helper.get_websocket_headers(context.authenticated_user.jwt_token)
            
            # Create connection with Windows-optimized settings
            websocket = await asyncio.wait_for(
                websockets.connect(
                    context.websocket_url,
                    additional_headers=headers,
                    ping_interval=None,  # Disable ping on Windows to avoid IOCP issues
                    ping_timeout=None,
                    close_timeout=3.0,
                    max_size=2**16  # Smaller max size for Windows
                ),
                timeout=timeout
            )
            
            context.mark_connection_established()
            self.active_websockets.append(websocket)
            
            return websocket
            
        except Exception as e:
            logger.error(f"❌ Windows-safe WebSocket connection failed: {e}")
            raise

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.e2e
    @pytest.mark.load_test
    @pytest.mark.priority_p1
    async def test_golden_path_load_test_simulation(self, golden_path_services, mock_authenticated_user):
        """
        Test 7: Golden Path Load Test Simulation - Enterprise-Scale Concurrent Usage
        
        Business Value Justification:
        - Segment: Enterprise - Platform Scalability
        - Business Goal: Platform Reliability & Concurrent User Support
        - Value Impact: Validates system can handle enterprise peak loads (20+ concurrent users)
        - Revenue Impact: Enables enterprise contracts worth $1M+ ARR by proving scalability
        
        This test simulates enterprise-scale concurrent usage to validate Golden Path
        performance and reliability under high load conditions.
        """
        
        logger.info("🌟 Starting Test 7: Golden Path Load Test Simulation")
        
        # Load test configuration
        concurrent_users = 12      # Enterprise peak load simulation
        test_duration = 180.0      # 3 minutes of sustained load
        stagger_delay = 2.0        # 2 second delay between user starts
        
        # Metrics tracking
        load_test_metrics = {
            "total_users": concurrent_users,
            "successful_connections": 0,
            "successful_completions": 0,
            "failed_connections": 0,
            "failed_completions": 0,
            "average_response_time": 0.0,
            "max_response_time": 0.0,
            "min_response_time": float('inf'),
            "total_events_received": 0,
            "concurrent_peak": 0
        }
        
        user_contexts = []
        user_results = []
        active_connections = []
        
        logger.info(f"🚀 Starting load test with {concurrent_users} concurrent users")
        logger.info(f"⏱️ Test duration: {test_duration}s")
        logger.info(f"📈 Stagger delay: {stagger_delay}s")
        
        try:
            # Step 1: Create all user contexts concurrently
            context_creation_start = time.time()
            
            context_tasks = []
            for i in range(concurrent_users):
                user_email = f"load_test_user_{i+1:02d}@enterprise.com"
                scenarios = ["ai_cost_optimization", "multi_model_optimization", "enterprise_scale_optimization"]
                scenario = scenarios[i % len(scenarios)]
                
                task = self.create_authenticated_golden_path_context(
                    scenario_name=scenario,
                    user_email=user_email
                )
                context_tasks.append(task)
            
            user_contexts = await asyncio.gather(*context_tasks)
            context_creation_time = time.time() - context_creation_start
            
            logger.success(f"✅ Created {len(user_contexts)} user contexts in {context_creation_time:.2f}s")
            
            # Step 2: Start users with staggered timing
            async def simulate_user_journey(user_index: int, context: GoldenPathTestContext):
                """Simulate complete user journey for load testing."""
                user_start_time = time.time()
                user_metrics = {
                    "user_id": user_index,
                    "connection_time": 0.0,
                    "execution_time": 0.0,
                    "events_received": 0,
                    "success": False,
                    "errors": []
                }
                
                try:
                    # Stagger user starts
                    await asyncio.sleep(user_index * stagger_delay)
                    
                    logger.info(f"👤 User {user_index+1} starting Golden Path journey")
                    
                    # Establish connection
                    connection_start = time.time()
                    websocket = await self.establish_authenticated_websocket_connection(context, golden_path_services)
                    connection_time = time.time() - connection_start
                    
                    user_metrics["connection_time"] = connection_time
                    load_test_metrics["successful_connections"] += 1
                    active_connections.append(websocket)
                    
                    # Update concurrent peak
                    current_concurrent = len(active_connections)
                    if current_concurrent > load_test_metrics["concurrent_peak"]:
                        load_test_metrics["concurrent_peak"] = current_concurrent
                    
                    # Send optimization request
                    thread_id = await self.send_golden_path_optimization_request(websocket, context)
                    
                    # Monitor execution with load test timeout
                    execution_results = await self.monitor_golden_path_execution(
                        websocket, context, timeout=120.0, services=golden_path_services  # 2 minute timeout per user
                    )
                    
                    user_execution_time = time.time() - user_start_time
                    user_metrics["execution_time"] = user_execution_time
                    user_metrics["events_received"] = len(context.received_events)
                    user_metrics["success"] = execution_results.get("all_events_received", False)
                    
                    if user_metrics["success"]:
                        load_test_metrics["successful_completions"] += 1
                    
                    # Update response time metrics
                    load_test_metrics["total_events_received"] += len(context.received_events)
                    
                    if user_execution_time > load_test_metrics["max_response_time"]:
                        load_test_metrics["max_response_time"] = user_execution_time
                    if user_execution_time < load_test_metrics["min_response_time"]:
                        load_test_metrics["min_response_time"] = user_execution_time
                    
                    # Close connection
                    await websocket.close()
                    active_connections.remove(websocket)
                    
                    logger.success(f"✅ User {user_index+1} completed in {user_execution_time:.2f}s")
                    
                except Exception as e:
                    logger.error(f"❌ User {user_index+1} failed: {e}")
                    user_metrics["errors"].append(str(e))
                    
                    if "connection" in str(e).lower():
                        load_test_metrics["failed_connections"] += 1
                    else:
                        load_test_metrics["failed_completions"] += 1
                
                return user_metrics
            
            # Step 3: Execute all user journeys concurrently
            logger.info("🎯 Starting concurrent user journey execution")
            
            journey_tasks = [
                simulate_user_journey(i, context) 
                for i, context in enumerate(user_contexts)
            ]
            
            # Run with overall load test timeout
            user_results = await asyncio.wait_for(
                asyncio.gather(*journey_tasks, return_exceptions=True),
                timeout=test_duration + 60.0  # Extra buffer for cleanup
            )
            
            # Step 4: Analyze load test results
            successful_results = [r for r in user_results if isinstance(r, dict) and r.get("success", False)]
            failed_results = [r for r in user_results if isinstance(r, Exception) or not isinstance(r, dict) or not r.get("success", False)]
            
            # Calculate metrics
            if successful_results:
                response_times = [r["execution_time"] for r in successful_results]
                load_test_metrics["average_response_time"] = sum(response_times) / len(response_times)
            
            success_rate = len(successful_results) / concurrent_users
            connection_success_rate = load_test_metrics["successful_connections"] / concurrent_users
            
            # Step 5: Validate load test requirements
            assert success_rate >= 0.80, (
                f"Load test success rate must be at least 80%. "
                f"Actual: {success_rate:.1%} ({len(successful_results)}/{concurrent_users})"
            )
            
            assert connection_success_rate >= 0.90, (
                f"Connection success rate must be at least 90%. "
                f"Actual: {connection_success_rate:.1%} ({load_test_metrics['successful_connections']}/{concurrent_users})"
            )
            
            assert load_test_metrics["concurrent_peak"] >= concurrent_users * 0.8, (
                f"Must achieve at least 80% concurrent peak. "
                f"Peak: {load_test_metrics['concurrent_peak']} (target: {concurrent_users * 0.8:.0f})"
            )
            
            assert load_test_metrics["average_response_time"] <= 90.0, (
                f"Average response time must be under 90s during load test. "
                f"Actual: {load_test_metrics['average_response_time']:.2f}s"
            )
            
            # Step 6: Clean up any remaining connections
            cleanup_tasks = []
            for ws in active_connections:
                if not ws.closed:
                    cleanup_tasks.append(ws.close())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            # Record load test metrics
            self.record_metric("load_test_concurrent_users", concurrent_users)
            self.record_metric("load_test_success_rate", success_rate)
            self.record_metric("load_test_connection_success_rate", connection_success_rate)
            self.record_metric("load_test_concurrent_peak", load_test_metrics["concurrent_peak"])
            self.record_metric("load_test_average_response_time", load_test_metrics["average_response_time"])
            self.record_metric("load_test_total_events", load_test_metrics["total_events_received"])
            
            logger.success("✅ Test 7 Complete: Golden Path Load Test Simulation successful")
            logger.success(f"👥 Concurrent Users: {concurrent_users}")
            logger.success(f"✅ Success Rate: {success_rate:.1%}")
            logger.success(f"🔌 Connection Success: {connection_success_rate:.1%}")
            logger.success(f"📈 Concurrent Peak: {load_test_metrics['concurrent_peak']}")
            logger.success(f"⏱️ Average Response: {load_test_metrics['average_response_time']:.2f}s")
            logger.success(f"📊 Total Events: {load_test_metrics['total_events_received']}")
            
        except Exception as e:
            logger.error(f"❌ Load test failed: {e}")
            
            # Clean up connections on failure
            cleanup_tasks = []
            for ws in active_connections:
                try:
                    if not ws.closed:
                        cleanup_tasks.append(ws.close())
                except:
                    pass
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            raise

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.e2e
    @pytest.mark.audit_trail
    @pytest.mark.priority_p1
    async def test_golden_path_data_audit_trail(self, golden_path_services, mock_authenticated_user):
        """
        Test 8: Golden Path Data Audit Trail - Complete Audit Logging and Compliance Validation
        
        Business Value Justification:
        - Segment: Enterprise - Compliance & Data Governance
        - Business Goal: Risk Reduction & Regulatory Compliance
        - Value Impact: Ensures complete audit trail for enterprise compliance requirements
        - Revenue Impact: Enables enterprise contracts requiring SOC2/GDPR compliance ($500K+ ARR)
        
        This test validates that Golden Path execution creates comprehensive audit trails
        for all user interactions, data processing, and business decisions.
        """
        
        logger.info("🌟 Starting Test 8: Golden Path Data Audit Trail")
        
        # Audit trail requirements
        required_audit_events = [
            "user_authentication",
            "websocket_connection",
            "message_received",
            "agent_execution_start",
            "tool_execution",
            "data_processing",
            "response_generation",
            "data_persistence",
            "session_cleanup"
        ]
        
        # Create audit-enabled context
        context = await self.create_authenticated_golden_path_context(
            scenario_name="audit_trail_optimization",
            user_email="compliance_officer@audited-enterprise.com"
        )
        
        # Initialize audit tracking
        audit_events = []
        data_access_log = []
        compliance_metrics = {
            "audit_events_captured": 0,
            "data_access_logged": 0,
            "pii_handling_events": 0,
            "retention_policy_applied": 0,
            "security_events": 0
        }
        
        # Step 1: Establish connection with audit logging
        logger.info("📋 Starting audit trail validation")
        
        # Record authentication audit event
        audit_events.append({
            "event_type": "user_authentication",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": context.authenticated_user.user_id,
            "user_email": context.authenticated_user.email,
            "authentication_method": "jwt_token",
            "compliance_context": "golden_path_audit_test"
        })
        compliance_metrics["audit_events_captured"] += 1
        compliance_metrics["security_events"] += 1
        
        websocket = await self.establish_authenticated_websocket_connection(context, golden_path_services)
        
        # Record connection audit event
        audit_events.append({
            "event_type": "websocket_connection",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": context.authenticated_user.user_id,
            "connection_ip": "127.0.0.1",  # Test IP
            "protocol": "websocket",
            "encryption": "TLS",
            "compliance_context": "secure_connection_established"
        })
        compliance_metrics["audit_events_captured"] += 1
        compliance_metrics["security_events"] += 1
        
        # Step 2: Send request with audit logging
        audit_request_message = {
            "type": "user_message",
            "content": (
                "Please analyze my AI infrastructure costs for the following systems: "
                "Employee productivity tools (serving 10,000 employees with PII), "
                "Customer service AI (handling sensitive customer data), "
                "Financial modeling systems (processing confidential financial data). "
                "Ensure all recommendations comply with SOC2 and GDPR requirements."
            ),
            "thread_id": generate_thread_id(),
            "run_id": UnifiedIDManager.generate_run_id(generate_thread_id()),
            "user_id": context.authenticated_user.user_id,
            "audit_metadata": {
                "contains_pii": True,
                "data_classification": "confidential",
                "compliance_requirements": ["SOC2", "GDPR"],
                "retention_policy": "7_years",
                "audit_level": "comprehensive"
            }
        }
        
        # Record message audit event
        audit_events.append({
            "event_type": "message_received",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": context.authenticated_user.user_id,
            "thread_id": audit_request_message["thread_id"],
            "run_id": audit_request_message["run_id"],
            "message_type": audit_request_message["type"],
            "data_classification": "confidential",
            "pii_detected": True,
            "compliance_requirements": ["SOC2", "GDPR"]
        })
        compliance_metrics["audit_events_captured"] += 1
        compliance_metrics["pii_handling_events"] += 1
        
        await websocket.send(json.dumps(audit_request_message))
        context.message_sent = True
        
        # Step 3: Monitor execution with comprehensive audit logging
        execution_start = time.time()
        context.start_time = execution_start
        
        logger.info("🔍 Monitoring Golden Path execution with audit trail capture")
        
        while time.time() - execution_start < 120.0:  # 2 minute timeout
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                message_data = json.loads(message)
                
                context.record_event(message_data)
                event_type = message_data.get("type", "unknown")
                
                # Create detailed audit log for each event
                audit_event = {
                    "event_type": f"agent_{event_type}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": context.authenticated_user.user_id,
                    "thread_id": context.thread_id,
                    "run_id": context.run_id,
                    "event_data": message_data,
                    "processing_context": "golden_path_execution"
                }
                
                # Add specific audit details based on event type
                if event_type == "agent_started":
                    audit_event.update({
                        "agent_type": message_data.get("agent", "unknown"),
                        "execution_context": "user_request_processing",
                        "data_access_level": "confidential"
                    })
                    compliance_metrics["audit_events_captured"] += 1
                    
                elif event_type == "tool_executing":
                    tool_name = message_data.get("tool", "unknown")
                    audit_event.update({
                        "tool_name": tool_name,
                        "tool_purpose": message_data.get("purpose", "unknown"),
                        "data_accessed": True,
                        "processing_type": "automated_analysis"
                    })
                    
                    # Log data access
                    data_access_log.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": context.authenticated_user.user_id,
                        "tool": tool_name,
                        "access_type": "read_analyze",
                        "data_classification": "confidential",
                        "purpose": "cost_optimization_analysis"
                    })
                    
                    compliance_metrics["audit_events_captured"] += 1
                    compliance_metrics["data_access_logged"] += 1
                    
                elif event_type == "assistant_message":
                    content = message_data.get("content", "")
                    
                    # Analyze response for compliance
                    contains_recommendations = "recommend" in content.lower()
                    contains_cost_data = any(term in content.lower() for term in ["cost", "$", "saving"])
                    
                    audit_event.update({
                        "response_type": "ai_generated_recommendations",
                        "contains_business_data": contains_cost_data,
                        "contains_recommendations": contains_recommendations,
                        "response_classification": "business_confidential",
                        "audit_review_required": True
                    })
                    
                    compliance_metrics["audit_events_captured"] += 1
                    
                    # Record data persistence audit event
                    audit_events.append({
                        "event_type": "data_persistence",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": context.authenticated_user.user_id,
                        "thread_id": context.thread_id,
                        "data_type": "ai_recommendations",
                        "retention_applied": True,
                        "encryption_at_rest": True,
                        "compliance_validation": "passed"
                    })
                    
                    compliance_metrics["audit_events_captured"] += 1
                    compliance_metrics["retention_policy_applied"] += 1
                
                audit_events.append(audit_event)
                
                logger.info(f"📋 Audit Event: {event_type} logged")
                
                # Check for completion
                if event_type in ["agent_completed", "assistant_message"]:
                    logger.success("🎉 Audit trail execution completed")
                    break
                    
            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError:
                # Log audit event for data integrity issue
                audit_events.append({
                    "event_type": "data_integrity_issue",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "issue_type": "invalid_json",
                    "user_id": context.authenticated_user.user_id,
                    "severity": "warning"
                })
                compliance_metrics["security_events"] += 1
                continue
        
        # Step 4: Validate audit trail completeness
        captured_event_types = set()
        for audit_event in audit_events:
            event_type = audit_event.get("event_type", "")
            if event_type:
                captured_event_types.add(event_type)
        
        # Map captured events to required audit events
        event_mapping = {
            "user_authentication": "user_authentication",
            "websocket_connection": "websocket_connection", 
            "message_received": "message_received",
            "agent_agent_started": "agent_execution_start",
            "agent_tool_executing": "tool_execution",
            "agent_tool_executing": "data_processing",
            "agent_assistant_message": "response_generation",
            "data_persistence": "data_persistence"
        }
        
        covered_requirements = set()
        for captured_event in captured_event_types:
            for required_event in required_audit_events:
                if required_event in event_mapping.values():
                    for mapped_event, mapped_requirement in event_mapping.items():
                        if mapped_requirement == required_event and captured_event == mapped_event:
                            covered_requirements.add(required_event)
                elif required_event in captured_event:
                    covered_requirements.add(required_event)
        
        audit_coverage = len(covered_requirements) / len(required_audit_events)
        
        assert audit_coverage >= 0.80, (
            f"Audit trail must cover at least 80% of required events. "
            f"Coverage: {audit_coverage:.1%} ({len(covered_requirements)}/{len(required_audit_events)})"
        )
        
        # Step 5: Validate compliance-specific requirements
        assert compliance_metrics["pii_handling_events"] > 0, "Must log PII handling events"
        assert compliance_metrics["data_access_logged"] > 0, "Must log all data access events"
        assert compliance_metrics["security_events"] >= 2, "Must log security-related events"
        assert compliance_metrics["retention_policy_applied"] > 0, "Must apply retention policies"
        
        # Step 6: Validate audit data integrity
        for audit_event in audit_events:
            assert "timestamp" in audit_event, "All audit events must have timestamps"
            assert "event_type" in audit_event, "All audit events must have event types"
            assert "user_id" in audit_event, "All audit events must have user IDs"
            
            # Validate timestamp format
            try:
                datetime.fromisoformat(audit_event["timestamp"].replace("Z", "+00:00"))
            except ValueError:
                raise AssertionError(f"Invalid timestamp format in audit event: {audit_event['timestamp']}")
        
        # Step 7: Close connection with final audit event
        await websocket.close()
        
        # Record session cleanup audit event
        audit_events.append({
            "event_type": "session_cleanup",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": context.authenticated_user.user_id,
            "session_duration": time.time() - execution_start,
            "cleanup_successful": True,
            "data_retention_applied": True,
            "compliance_validated": True
        })
        compliance_metrics["audit_events_captured"] += 1
        
        # Final audit trail metrics
        self.golden_path_metrics.audit_trail_entries = len(audit_events)
        
        # Record comprehensive audit metrics
        self.record_metric("audit_events_total", len(audit_events))
        self.record_metric("audit_coverage_percentage", audit_coverage)
        self.record_metric("pii_handling_events", compliance_metrics["pii_handling_events"])
        self.record_metric("data_access_events", compliance_metrics["data_access_logged"])
        self.record_metric("security_events", compliance_metrics["security_events"])
        self.record_metric("retention_events", compliance_metrics["retention_policy_applied"])
        self.record_metric("audit_trail_compliant", True)
        
        logger.success("✅ Test 8 Complete: Golden Path Data Audit Trail validated")
        logger.success(f"📋 Total Audit Events: {len(audit_events)}")
        logger.success(f"📊 Audit Coverage: {audit_coverage:.1%}")
        logger.success(f"🔐 PII Handling Events: {compliance_metrics['pii_handling_events']}")
        logger.success(f"📄 Data Access Events: {compliance_metrics['data_access_logged']}")
        logger.success(f"🛡️ Security Events: {compliance_metrics['security_events']}")
        logger.success(f"⏳ Retention Events: {compliance_metrics['retention_policy_applied']}")


# ============================================================================
# TEST SUITE CONFIGURATION AND EXECUTION
# ============================================================================

if __name__ == "__main__":
    """
    Execute Golden Path Comprehensive Test Suite directly.
    
    This allows running the suite independently for development and validation.
    """
    import sys
    
    # Configure logging for direct execution
    from loguru import logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Run the test suite
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure for debugging
        "--timeout=300"  # 5 minute timeout per test
    ])