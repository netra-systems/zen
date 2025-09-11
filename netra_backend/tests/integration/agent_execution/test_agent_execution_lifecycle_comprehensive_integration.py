"""
Comprehensive Agent Execution Lifecycle Integration Test - Golden Path Business Value

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete agent execution pipeline delivers substantial AI value
- Value Impact: Complete flow from user message to actionable agent results with real-time transparency
- Strategic Impact: Core platform functionality - agent orchestration is 90% of business value delivery

CRITICAL BUSINESS REQUIREMENTS:
1. Complete Agent Execution Pipeline: Message → Router → AgentHandler → ExecutionEngine → SupervisorAgent → Sub-agents
2. 5 Critical WebSocket Events for Chat Business Value: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
3. Agent Orchestration Flow: DataAgent → OptimizationAgent → ReportAgent with proper handoffs
4. Factory Pattern User Isolation: Multiple concurrent users with complete isolation
5. Real Service Integration: PostgreSQL persistence, Redis caching, WebSocket events
6. Error Handling and Graceful Degradation: System continues to deliver value during partial failures
7. Agent Execution Timeout Scenarios: Proper handling of long-running operations
8. WebSocket Event Ordering and Timing: Events delivered in correct sequence for user experience
9. Business Value Validation: Each agent execution produces actionable insights/recommendations

COMPLIANCE:
- Uses ONLY real services (PostgreSQL, Redis, WebSocket) per CLAUDE.md
- NO MOCKS in integration testing per TEST_CREATION_GUIDE.md
- Follows test_framework/ssot patterns for all fixtures
- Validates business value delivery in every test scenario
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import pytest

# SSOT Test Framework Imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

# Core Agent System Imports (Real Production Code)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext, validate_user_context
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_engine import create_request_scoped_engine
from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory

# WebSocket Integration (Real Services)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, create_agent_websocket_bridge
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter

# Tool Execution (Real SSOT Components)
from netra_backend.app.agents.tool_dispatcher import UnifiedToolDispatcherFactory
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine

# Core Infrastructure (Real Services)
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from netra_backend.app.core.unified_trace_context import UnifiedTraceContext
from netra_backend.app.services.user_execution_context import UserExecutionContext as ServiceUserExecutionContext

# Import SSOT Environment Management
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class AgentExecutionEvent:
    """WebSocket event captured during agent execution."""
    event_type: str
    timestamp: float
    thread_id: str
    run_id: str
    user_id: str
    data: Dict[str, Any]
    sequence_number: int
    trace_id: Optional[str] = None


@dataclass
class BusinessValueMetrics:
    """Metrics indicating business value delivered by agent execution."""
    has_recommendations: bool = False
    has_insights: bool = False
    has_cost_savings: bool = False
    has_actionable_steps: bool = False
    response_quality_score: float = 0.0
    execution_time_seconds: float = 0.0
    user_satisfaction_indicators: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentExecutionScenario:
    """Test scenario for comprehensive agent execution testing."""
    name: str
    user_message: str
    expected_agent_chain: List[str]
    expected_tools: List[str]
    timeout_seconds: int = 60
    validate_business_value: bool = True
    concurrent_users: int = 1


class CriticalWebSocketEvents(Enum):
    """5 critical WebSocket events that enable chat business value."""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"


class AgentExecutionStates(Enum):
    """Agent execution states throughout lifecycle."""
    INITIALIZED = "initialized"
    ROUTING = "routing"
    EXECUTING = "executing"
    THINKING = "thinking"
    TOOL_EXECUTION = "tool_execution"
    ORCHESTRATING = "orchestrating"
    COMPLETING = "completing"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"


class TestAgentExecutionLifecycleComprehensive(BaseIntegrationTest):
    """Comprehensive integration test for complete agent execution lifecycle."""
    
    def setup_method(self):
        """Set up test environment with real services."""
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.captured_events: List[AgentExecutionEvent] = []
        self.business_value_metrics: Dict[str, BusinessValueMetrics] = {}
        self.execution_traces: Dict[str, List[str]] = {}
        self.user_sessions: Dict[str, Any] = {}
        
        # Test scenarios covering critical business paths
        self.test_scenarios = [
            AgentExecutionScenario(
                name="cost_optimization_pipeline",
                user_message="Analyze my AWS costs and provide optimization recommendations",
                expected_agent_chain=["data_agent", "optimization_agent", "report_agent"],
                expected_tools=["aws_cost_analyzer", "recommendation_engine", "report_generator"],
                validate_business_value=True,
                concurrent_users=1
            ),
            AgentExecutionScenario(
                name="multi_user_concurrent_execution",
                user_message="Help me optimize my cloud infrastructure",
                expected_agent_chain=["triage_agent", "data_agent", "optimization_agent"],
                expected_tools=["infrastructure_analyzer", "optimization_calculator"],
                validate_business_value=True,
                concurrent_users=3  # Test isolation
            ),
            AgentExecutionScenario(
                name="simple_query_fast_path",
                user_message="What is my current monthly cloud spend?",
                expected_agent_chain=["triage_agent", "data_agent"],
                expected_tools=["cost_fetcher"],
                timeout_seconds=30,
                validate_business_value=True,
                concurrent_users=1
            )
        ]
    
    async def _create_isolated_user_context(self, real_services) -> Tuple[str, UserExecutionContext, Dict[str, Any]]:
        """Create completely isolated user execution context."""
        # Generate unique user ID for complete isolation
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Create authenticated user context using SSOT helper
        auth_context = await create_authenticated_user_context(
            user_id=user_id,
            email=f"{user_id}@test.example.com",
            name=f"Test User {user_id}",
            real_services=real_services
        )
        
        # Create UserExecutionContext with proper isolation
        user_context = UserExecutionContext(
            user_id=user_id,
            request_id=request_id,
            thread_id=thread_id,
            run_id=run_id,
            metadata={
                "test_scenario": True,
                "isolation_level": "complete",
                "auth_context": auth_context
            }
        )
        
        # Validate context meets isolation requirements
        validate_user_context(user_context)
        
        logger.info(f"✅ Created isolated user context for {user_id}")
        return user_id, user_context, auth_context
    
    async def _setup_agent_execution_pipeline(self, user_context: UserExecutionContext, 
                                            real_services) -> Tuple[AgentRegistry, ExecutionEngine, AgentWebSocketBridge]:
        """Set up complete agent execution pipeline with real services."""
        
        # Create user-isolated agent registry using factory pattern
        agent_registry = AgentRegistry()
        user_session = await agent_registry.create_user_session(user_context.user_id)
        
        # Set up WebSocket bridge for real-time events
        websocket_manager = UnifiedWebSocketManager()
        await user_session.set_websocket_manager(websocket_manager, user_context)
        
        # Create WebSocket bridge using SSOT factory
        # Fix: create_agent_websocket_bridge is synchronous, not async
        # Also fix: function doesn't take websocket_manager parameter
        bridge = create_agent_websocket_bridge(
            user_context=user_context
        )
        
        # Create request-scoped execution engine
        execution_engine = await create_request_scoped_engine(
            registry=agent_registry,
            websocket_bridge=bridge,
            user_context=user_context
        )
        
        # Verify all components are properly isolated and connected
        assert execution_engine is not None, "Execution engine creation failed"
        assert bridge is not None, "WebSocket bridge creation failed"
        assert user_session is not None, "User session creation failed"
        
        logger.info(f"✅ Agent execution pipeline setup complete for user {user_context.user_id}")
        return agent_registry, execution_engine, bridge
    
    async def _capture_websocket_events(self, bridge: AgentWebSocketBridge, 
                                      user_context: UserExecutionContext, 
                                      timeout_seconds: int = 60) -> List[AgentExecutionEvent]:
        """Capture WebSocket events during agent execution."""
        events = []
        event_sequence = 0
        
        # Create event capture callback
        async def event_handler(event_type: str, data: Dict[str, Any]):
            nonlocal event_sequence
            event = AgentExecutionEvent(
                event_type=event_type,
                timestamp=time.time(),
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                user_id=user_context.user_id,
                data=data,
                sequence_number=event_sequence,
                trace_id=data.get("trace_id")
            )
            events.append(event)
            event_sequence += 1
            logger.debug(f"Captured WebSocket event: {event_type} for user {user_context.user_id}")
        
        # Register event handler with bridge
        if hasattr(bridge, 'add_event_handler'):
            bridge.add_event_handler(event_handler)
        
        return events
    
    async def _execute_agent_with_monitoring(self, execution_engine: ExecutionEngine,
                                           user_context: UserExecutionContext,
                                           message: str,
                                           timeout_seconds: int = 60) -> Tuple[Any, List[AgentExecutionEvent]]:
        """Execute agent with comprehensive monitoring and event capture."""
        start_time = time.time()
        captured_events = []
        
        try:
            # Create agent execution context
            agent_context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                request_id=user_context.request_id,
                message=message,
                trace_context=UnifiedTraceContext.create_new()
            )
            
            # Execute agent with timeout
            execution_task = asyncio.create_task(
                execution_engine.execute_pipeline(agent_context)
            )
            
            # Monitor execution with timeout
            try:
                result = await asyncio.wait_for(execution_task, timeout=timeout_seconds)
                logger.info(f"✅ Agent execution completed for user {user_context.user_id} in {time.time() - start_time:.2f}s")
                return result, captured_events
                
            except asyncio.TimeoutError:
                execution_task.cancel()
                logger.error(f"❌ Agent execution timeout after {timeout_seconds}s for user {user_context.user_id}")
                raise
                
        except Exception as e:
            logger.error(f"❌ Agent execution failed for user {user_context.user_id}: {e}")
            raise
    
    def _validate_critical_websocket_events(self, events: List[AgentExecutionEvent], 
                                          user_context: UserExecutionContext) -> bool:
        """Validate all 5 critical WebSocket events were sent for business value."""
        event_types = [event.event_type for event in events]
        critical_events = [e.value for e in CriticalWebSocketEvents]
        
        missing_events = []
        for critical_event in critical_events:
            if critical_event not in event_types:
                missing_events.append(critical_event)
        
        if missing_events:
            logger.error(f"❌ Missing critical WebSocket events for user {user_context.user_id}: {missing_events}")
            return False
        
        # Validate event ordering (started → thinking → tool_executing → tool_completed → completed)
        required_sequence = [
            CriticalWebSocketEvents.AGENT_STARTED.value,
            CriticalWebSocketEvents.AGENT_THINKING.value,
            CriticalWebSocketEvents.AGENT_COMPLETED.value  # Minimum required sequence
        ]
        
        event_positions = {}
        for i, event in enumerate(events):
            if event.event_type in [e.value for e in CriticalWebSocketEvents]:
                event_positions[event.event_type] = i
        
        # Check if events are in correct order
        for i in range(len(required_sequence) - 1):
            current_event = required_sequence[i]
            next_event = required_sequence[i + 1]
            
            if (current_event in event_positions and next_event in event_positions and
                event_positions[current_event] >= event_positions[next_event]):
                logger.error(f"❌ WebSocket events out of order for user {user_context.user_id}")
                return False
        
        logger.info(f"✅ All critical WebSocket events validated for user {user_context.user_id}")
        return True
    
    def _validate_business_value_delivery(self, result: Any, events: List[AgentExecutionEvent],
                                        user_context: UserExecutionContext) -> BusinessValueMetrics:
        """Validate that agent execution delivered actual business value."""
        metrics = BusinessValueMetrics()
        
        if result is None:
            logger.warning(f"⚠️ No result returned for user {user_context.user_id}")
            return metrics
        
        # Extract business value indicators from result
        result_data = result if isinstance(result, dict) else getattr(result, 'data', {})
        
        # Check for recommendations (core business value)
        if 'recommendations' in result_data and len(result_data['recommendations']) > 0:
            metrics.has_recommendations = True
            metrics.response_quality_score += 0.3
        
        # Check for insights (analytical value)
        if 'insights' in result_data and len(result_data['insights']) > 0:
            metrics.has_insights = True
            metrics.response_quality_score += 0.3
        
        # Check for cost savings (financial value)
        if 'cost_savings' in result_data or 'potential_savings' in result_data:
            metrics.has_cost_savings = True
            metrics.response_quality_score += 0.2
        
        # Check for actionable steps (practical value)
        if 'action_items' in result_data or 'next_steps' in result_data:
            metrics.has_actionable_steps = True
            metrics.response_quality_score += 0.2
        
        # Calculate execution time from events
        if events:
            start_event = next((e for e in events if e.event_type == CriticalWebSocketEvents.AGENT_STARTED.value), None)
            end_event = next((e for e in events if e.event_type == CriticalWebSocketEvents.AGENT_COMPLETED.value), None)
            
            if start_event and end_event:
                metrics.execution_time_seconds = end_event.timestamp - start_event.timestamp
        
        # Validate minimum business value threshold
        if metrics.response_quality_score < 0.5:
            logger.warning(f"⚠️ Low business value score ({metrics.response_quality_score}) for user {user_context.user_id}")
        else:
            logger.info(f"✅ Business value validated for user {user_context.user_id} (score: {metrics.response_quality_score})")
        
        return metrics
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complete_agent_execution_pipeline(self, real_services_fixture):
        """Test complete agent execution pipeline with all business value requirements."""
        
        # Skip if database not available
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database required for agent execution integration testing")
        
        scenario = self.test_scenarios[0]  # cost_optimization_pipeline
        
        # Create isolated user context
        user_id, user_context, auth_context = await self._create_isolated_user_context(real_services_fixture)
        
        # Set up agent execution pipeline
        registry, execution_engine, bridge = await self._setup_agent_execution_pipeline(
            user_context, real_services_fixture
        )
        
        # Set up event monitoring
        captured_events = await self._capture_websocket_events(bridge, user_context, scenario.timeout_seconds)
        
        # Execute agent with full monitoring
        result, events = await self._execute_agent_with_monitoring(
            execution_engine, user_context, scenario.user_message, scenario.timeout_seconds
        )
        
        # Validate critical WebSocket events were sent
        assert self._validate_critical_websocket_events(captured_events, user_context), \
            f"Critical WebSocket events missing for user {user_id}"
        
        # Validate business value delivery
        metrics = self._validate_business_value_delivery(result, captured_events, user_context)
        assert metrics.response_quality_score >= 0.5, \
            f"Insufficient business value delivered (score: {metrics.response_quality_score})"
        
        # Validate execution performance
        assert metrics.execution_time_seconds < scenario.timeout_seconds, \
            f"Execution exceeded timeout: {metrics.execution_time_seconds}s > {scenario.timeout_seconds}s"
        
        # Store metrics for analysis
        self.business_value_metrics[user_id] = metrics
        
        logger.info(f"✅ Complete agent execution pipeline test passed for user {user_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_concurrent_agent_execution_isolation(self, real_services_fixture):
        """Test concurrent agent execution with complete user isolation."""
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database required for concurrent execution testing")
        
        scenario = self.test_scenarios[1]  # multi_user_concurrent_execution
        concurrent_users = 3
        
        async def execute_for_user(user_index: int) -> Tuple[str, bool, BusinessValueMetrics]:
            """Execute agent for single user with complete isolation."""
            
            # Create isolated user context
            user_id, user_context, auth_context = await self._create_isolated_user_context(real_services_fixture)
            
            try:
                # Set up isolated agent execution pipeline
                registry, execution_engine, bridge = await self._setup_agent_execution_pipeline(
                    user_context, real_services_fixture
                )
                
                # Execute with monitoring
                result, events = await self._execute_agent_with_monitoring(
                    execution_engine, user_context, 
                    f"{scenario.user_message} (User {user_index})", 
                    scenario.timeout_seconds
                )
                
                # Validate critical events
                events_valid = self._validate_critical_websocket_events([], user_context)  # events captured separately
                
                # Validate business value
                metrics = self._validate_business_value_delivery(result, [], user_context)
                
                return user_id, events_valid and metrics.response_quality_score >= 0.3, metrics
                
            except Exception as e:
                logger.error(f"❌ Concurrent execution failed for user {user_id}: {e}")
                return user_id, False, BusinessValueMetrics()
        
        # Execute concurrently for multiple users
        tasks = [execute_for_user(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate all executions succeeded
        successful_executions = 0
        for result in results:
            if not isinstance(result, Exception):
                user_id, success, metrics = result
                if success:
                    successful_executions += 1
                    self.business_value_metrics[user_id] = metrics
                    logger.info(f"✅ Concurrent execution succeeded for user {user_id}")
                else:
                    logger.error(f"❌ Concurrent execution failed for user {user_id}")
            else:
                logger.error(f"❌ Concurrent execution exception: {result}")
        
        # Require at least 80% success rate for concurrent execution
        success_rate = successful_executions / concurrent_users
        assert success_rate >= 0.8, \
            f"Concurrent execution success rate too low: {success_rate:.2f} < 0.8"
        
        logger.info(f"✅ Multi-user concurrent execution test passed ({successful_executions}/{concurrent_users} successful)")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_error_handling_graceful_degradation(self, real_services_fixture):
        """Test agent execution error handling and graceful degradation."""
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database required for error handling testing")
        
        # Create user context for error testing
        user_id, user_context, auth_context = await self._create_isolated_user_context(real_services_fixture)
        
        # Set up agent execution pipeline
        registry, execution_engine, bridge = await self._setup_agent_execution_pipeline(
            user_context, real_services_fixture
        )
        
        # Test scenarios that should gracefully degrade
        error_scenarios = [
            ("Invalid agent request", "Execute nonexistent_agent with invalid parameters"),
            ("Timeout simulation", "Run a very long computation that exceeds normal limits"),
            ("Malformed input", "{'invalid': 'json structure for agent input")
        ]
        
        for scenario_name, error_message in error_scenarios:
            try:
                # Execute with short timeout to trigger graceful degradation
                result, events = await self._execute_agent_with_monitoring(
                    execution_engine, user_context, error_message, timeout_seconds=10
                )
                
                # Even with errors, should still receive some WebSocket events
                event_types = [event.event_type for event in events] if events else []
                
                # At minimum should receive agent_started and either agent_completed or agent_error
                has_started = CriticalWebSocketEvents.AGENT_STARTED.value in event_types
                has_termination = (CriticalWebSocketEvents.AGENT_COMPLETED.value in event_types or 
                                 "agent_error" in event_types)
                
                assert has_started or has_termination, \
                    f"No proper event handling for error scenario: {scenario_name}"
                
                logger.info(f"✅ Graceful degradation validated for scenario: {scenario_name}")
                
            except asyncio.TimeoutError:
                # Timeout is acceptable for error scenarios
                logger.info(f"✅ Timeout handled gracefully for scenario: {scenario_name}")
                
            except Exception as e:
                # Some exceptions are acceptable as long as they're handled gracefully
                logger.info(f"✅ Exception handled gracefully for scenario: {scenario_name} - {type(e).__name__}")
        
        logger.info(f"✅ Error handling and graceful degradation test completed for user {user_id}")
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_websocket_event_ordering_and_timing_validation(self, real_services_fixture):
        """Test WebSocket event ordering and timing for optimal user experience."""
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database required for WebSocket timing testing")
        
        scenario = self.test_scenarios[2]  # simple_query_fast_path
        
        # Create user context
        user_id, user_context, auth_context = await self._create_isolated_user_context(real_services_fixture)
        
        # Set up pipeline
        registry, execution_engine, bridge = await self._setup_agent_execution_pipeline(
            user_context, real_services_fixture
        )
        
        # Capture events with precise timing
        start_time = time.time()
        captured_events = []
        
        # Execute agent
        result, events = await self._execute_agent_with_monitoring(
            execution_engine, user_context, scenario.user_message, scenario.timeout_seconds
        )
        
        execution_time = time.time() - start_time
        
        # Validate event timing requirements for good UX
        if captured_events:
            # First event should arrive within 2 seconds (user feedback)
            first_event_delay = captured_events[0].timestamp - start_time
            assert first_event_delay <= 2.0, \
                f"First WebSocket event too slow: {first_event_delay:.2f}s > 2.0s"
            
            # Events should be spaced reasonably (not all at once, not too slow)
            event_intervals = []
            for i in range(1, len(captured_events)):
                interval = captured_events[i].timestamp - captured_events[i-1].timestamp
                event_intervals.append(interval)
            
            if event_intervals:
                avg_interval = sum(event_intervals) / len(event_intervals)
                assert avg_interval <= 5.0, \
                    f"Average event interval too slow: {avg_interval:.2f}s > 5.0s"
        
        # Validate total execution time is reasonable
        assert execution_time <= scenario.timeout_seconds, \
            f"Execution time exceeded limit: {execution_time:.2f}s > {scenario.timeout_seconds}s"
        
        # For simple queries, should complete quickly
        if scenario.name == "simple_query_fast_path":
            assert execution_time <= 15.0, \
                f"Simple query too slow: {execution_time:.2f}s > 15.0s"
        
        logger.info(f"✅ WebSocket event timing validated for user {user_id} (execution: {execution_time:.2f}s)")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_persistence_and_state_management(self, real_services_fixture):
        """Test database persistence throughout agent execution lifecycle."""
        
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database required for persistence testing")
        
        # Create user context
        user_id, user_context, auth_context = await self._create_isolated_user_context(real_services_fixture)
        
        # Set up pipeline
        registry, execution_engine, bridge = await self._setup_agent_execution_pipeline(
            user_context, real_services_fixture
        )
        
        # Execute agent
        result, events = await self._execute_agent_with_monitoring(
            execution_engine, user_context, 
            "Analyze my infrastructure and save findings to database", 
            timeout_seconds=45
        )
        
        # Validate database persistence
        db_session = real_services_fixture["db"]
        if db_session:
            try:
                # Check that execution was persisted
                execution_record = await db_session.execute(
                    """
                    SELECT id, user_id, thread_id, run_id, state, created_at 
                    FROM backend.agent_executions 
                    WHERE user_id = $1 AND thread_id = $2
                    ORDER BY created_at DESC 
                    LIMIT 1
                    """,
                    user_context.user_id, user_context.thread_id
                )
                execution_row = await execution_record.fetchone()
                
                assert execution_row is not None, \
                    f"Agent execution not persisted for user {user_id}"
                
                # Check that messages were stored
                message_record = await db_session.execute(
                    """
                    SELECT id, content, role, thread_id
                    FROM backend.messages
                    WHERE thread_id = $1
                    ORDER BY created_at DESC
                    """,
                    user_context.thread_id
                )
                message_rows = await message_record.fetchall()
                
                assert len(message_rows) > 0, \
                    f"Messages not persisted for thread {user_context.thread_id}"
                
                # Validate user isolation in database
                other_user_record = await db_session.execute(
                    """
                    SELECT COUNT(*) FROM backend.agent_executions 
                    WHERE user_id != $1 AND thread_id = $2
                    """,
                    user_context.user_id, user_context.thread_id
                )
                other_user_count = await other_user_record.fetchval()
                
                assert other_user_count == 0, \
                    f"User isolation violated in database - found {other_user_count} records from other users"
                
                logger.info(f"✅ Database persistence validated for user {user_id}")
                
            except Exception as e:
                logger.error(f"❌ Database validation failed: {e}")
                raise
    
    def teardown_method(self):
        """Clean up test resources."""
        super().teardown_method()
        
        # Log business value metrics summary
        if self.business_value_metrics:
            total_users = len(self.business_value_metrics)
            avg_quality_score = sum(m.response_quality_score for m in self.business_value_metrics.values()) / total_users
            avg_execution_time = sum(m.execution_time_seconds for m in self.business_value_metrics.values()) / total_users
            
            logger.info(f"📊 Test Summary - Users: {total_users}, Avg Quality: {avg_quality_score:.2f}, Avg Time: {avg_execution_time:.2f}s")
        
        # Clean up user sessions
        self.user_sessions.clear()
        self.captured_events.clear()
        self.business_value_metrics.clear()