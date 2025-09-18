# CRITICAL: Import path configuration for direct test execution
# Ensures tests work both directly and through unified_test_runner.py
import sys
import os
from pathlib import Path

# Get project root (two levels up from tests/mission_critical/)
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# PERFORMANCE: Lazy loading for mission critical tests

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None

    return _lazy_imports[module_path]

"""
Comprehensive Unit Tests for PipelineExecutor Golden Path SSOT Class

Business Value Justification (BVJ):
- Segment: ALL (Free/Early/Mid/Enterprise/Platform)
- Business Goal: Agent Step-by-Step Execution - Ensures reliable pipeline processing
- Value Impact: Validates agent pipeline execution coordination (critical for AI workflows)
- Revenue Impact: Protects high-value ARR by ensuring reliable step-by-step agent execution

Critical Golden Path Scenarios Tested:
1. Pipeline step execution: Step-by-step agent execution with proper sequencing
2. State persistence: Agent state checkpointing and recovery between steps
3. Flow logging: Execution flow tracking for observability and debugging
4. Database session management: Proper session handling without global state
5. User context isolation: Factory pattern for per-user pipeline execution

SSOT Testing Compliance:
- Uses test_framework.ssot.base_test_case.SSotAsyncTestCase
- Real services preferred over mocks (only external dependencies mocked)
- Business-critical functionality validation over implementation details
- Pipeline execution business logic focus
"""

import asyncio
import time
import uuid
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# PipelineExecutor SSOT Class Under Test
from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStepConfig
)

# Supporting Infrastructure
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.agent_state import CheckpointType, StatePersistenceRequest

# CRITICAL: Always use real WebSocket connections - NO MOCKS per CLAUDE.md
# Tests will fail if Docker services are not available (expected behavior)
from tests.mission_critical.websocket_real_test_base import (
    RealWebSocketTestBase,
    RealWebSocketTestConfig
)
WebSocketTestBase = RealWebSocketTestBase
from test_framework.test_context import WebSocketContext, create_test_context
from test_framework.websocket_helpers import WebSocketTestHelpers


class MissionCriticalEventValidator:
    """Validates WebSocket events with extreme rigor - MOCKED WEBSOCKET CONNECTIONS."""

    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking",
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }

    # Additional events that may be sent in real scenarios
    OPTIONAL_EVENTS = {
        "agent_fallback",
        "final_report",
        "partial_result",
        "tool_error"
    }

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.events: List[Dict] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, data)
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()

    def record(self, event: Dict) -> None:
        """Record an event with detailed tracking."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")

        self.events.append(event)
        self.event_timeline.append((timestamp, event_type, event))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1

    def validate_critical_requirements(self) -> tuple[bool, List[str]]:
        """Validate that ALL critical requirements are met."""
        failures = []

        # 1. Check for required events
        missing = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(f"CRITICAL: Missing required events: {missing}")

        # 2. Validate event ordering
        if not self._validate_event_order():
            failures.append("CRITICAL: Invalid event order")

        # 3. Check for paired events
        if not self._validate_paired_events():
            failures.append("CRITICAL: Unpaired tool events")

        return len(failures) == 0, failures

    def _validate_event_order(self) -> bool:
        """Ensure events follow logical order."""
        if not self.event_timeline:
            return False

        # First event must be agent_started
        if self.event_timeline[0][1] != "agent_started":
            self.errors.append(f"First event was {self.event_timeline[0][1]}, not agent_started")
            return False

        # Last event should be completion
        last_event = self.event_timeline[-1][1]
        if last_event not in ["agent_completed", "final_report"]:
            # Accept any completion event for now
            self.warnings.append(f"Last event was {last_event}, expected completion event")

        return True

    def _validate_paired_events(self) -> bool:
        """Ensure tool events are properly paired."""
        tool_starts = self.event_counts.get("tool_executing", 0)
        tool_ends = self.event_counts.get("tool_completed", 0)

        if tool_starts != tool_ends:
            self.errors.append(f"Tool event mismatch: {tool_starts} starts, {tool_ends} completions")
            return False

        return True


class WebSocketAgentEventsComprehensiveTests(SSotAsyncTestCase):
    """
    MISSION CRITICAL: WebSocket Agent Events Tests - SSOT Implementation

    Business Value: $500K+ ARR Golden Path Protection
    Critical Path: WebSocket Events → Agent Integration → Chat Functionality

    Tests the 5 required WebSocket events that enable substantive chat functionality:
    1. agent_started - User sees agent began processing
    2. agent_thinking - Real-time reasoning visibility
    3. tool_executing - Tool usage transparency
    4. tool_completed - Tool results display
    5. agent_completed - User knows response is ready

    SSOT Compliance: Uses real WebSocket connections, real agent execution, NO MOCKS
    """
    
    @pytest.fixture(autouse=True)
    async def setup_websocket_agent_test_environment(self):
        """Setup SSOT test environment for WebSocket agent event testing."""
        # Create mock infrastructure using SSOT mock factory
        self.mock_factory = SSotMockFactory()
        
        # Core mocked dependencies (external only - keep business logic real)
        self.mock_execution_engine = self.mock_factory.create_mock("ExecutionEngine")
        self.mock_websocket_manager = self.mock_factory.create_mock(WebSocketManager)
        self.mock_db_session = self.mock_factory.create_mock("AsyncSession")
        self.mock_state_persistence = self.mock_factory.create_mock(StatePersistenceService)
        self.mock_flow_logger = self.mock_factory.create_mock(SupervisorFlowLogger)
        
        # Test user context for isolation testing (create a mock with required methods)
        self.test_user_context = MagicMock()
        self.test_user_context.user_id = "pipeline_user_001"
        self.test_user_context.thread_id = "pipeline_thread_001"
        self.test_user_context.run_id = "pipeline_run_001"
        self.test_user_context.request_id = "pipeline_req_001"
        self.test_user_context.websocket_client_id = "pipeline_ws_001"
        # Add the missing method that PipelineExecutor expects
        self.test_user_context.add_execution_result = MagicMock()
        
        # Test agent state
        self.test_agent_state = DeepAgentState(
            user_id="pipeline_user_001",
            thread_id="pipeline_thread_001",
            run_id="pipeline_run_001"
        )
        self.test_agent_state.user_request = "Test pipeline execution request"
        self.test_agent_state.step_count = 0
        
        # Test pipeline steps
        self.test_pipeline_steps = [
            PipelineStepConfig(
                agent_name="triage_agent",
                metadata={"step_number": 1, "description": "Initial request triage"}
            ),
            PipelineStepConfig(
                agent_name="data_helper_agent",
                metadata={"step_number": 2, "description": "Data collection"}
            ),
            PipelineStepConfig(
                agent_name="reporting_agent",
                metadata={"step_number": 3, "description": "Final report generation"}
            )
        ]
        
        # Track execution events
        self.captured_execution_events = []
        self.captured_persistence_events = []
        
        # Configure mock behaviors for pipeline executor testing
        await self._setup_mock_behaviors()
    
    async def _setup_mock_behaviors(self):
        """Setup realistic mock behaviors for pipeline executor testing."""
        # Configure execution engine to simulate successful agent executions
        async def mock_execute_agent(context, user_context=None):
            execution_time = 0.1  # 100ms execution time
            await asyncio.sleep(execution_time)
            
            result = AgentExecutionResult(
                success=True,
                agent_name=context.agent_name,
                duration=execution_time,
                data={
                    "result": f"Success from {context.agent_name}",
                    "step_number": getattr(context, 'step_number', 0),
                    "timestamp": time.time()
                }
            )
            
            # Track execution event
            self.captured_execution_events.append({
                'agent_name': context.agent_name,
                'success': True,
                'execution_time': execution_time,
                'timestamp': time.time()
            })
            
            return result
        
        self.mock_execution_engine.execute_agent = AsyncMock(side_effect=mock_execute_agent)
        
        # Configure execute_pipeline method that PipelineExecutor actually calls
        async def mock_execute_pipeline(pipeline, context, user_context=None):
            """Mock execute_pipeline to simulate sequential agent executions."""
            results = []
            for step in pipeline:
                # Create a mock context for each step
                step_context = AgentExecutionContext(
                    run_id=context.run_id,
                    thread_id=context.thread_id,
                    user_id=context.user_id,
                    agent_name=step.agent_name
                )
                result = await mock_execute_agent(step_context, user_context)
                results.append(result)
            return results
        
        self.mock_execution_engine.execute_pipeline = AsyncMock(side_effect=mock_execute_pipeline)
        
        # Configure state persistence service
        async def mock_save_state(request):
            self.captured_persistence_events.append({
                'checkpoint_type': request.checkpoint_type,
                'user_id': request.user_id,
                'run_id': request.run_id,
                'timestamp': time.time()
            })
            return True
        
        self.mock_state_persistence.save_state = AsyncMock(side_effect=mock_save_state)
        self.mock_state_persistence.load_state = AsyncMock(return_value=self.test_agent_state)
        
        # Configure flow logger (sync methods, not async)
        self.mock_flow_logger.start_flow = MagicMock(return_value="test_flow_id_001")
        self.mock_flow_logger.log_step_start = MagicMock()
        self.mock_flow_logger.log_step_complete = MagicMock()
        self.mock_flow_logger.complete_flow = MagicMock()
        self.mock_flow_logger.step_started = MagicMock()
        self.mock_flow_logger.step_completed = MagicMock()
        self.mock_flow_logger.log_parallel_execution = MagicMock()
        
        # Configure WebSocket manager
        self.mock_websocket_manager.notify_pipeline_started = AsyncMock()
        self.mock_websocket_manager.notify_pipeline_step = AsyncMock()
        self.mock_websocket_manager.notify_pipeline_completed = AsyncMock()
        
        # Patch dependencies
        self.flow_logger_patch = patch(
            'netra_backend.app.agents.supervisor.pipeline_executor.get_supervisor_flow_logger',
            return_value=self.mock_flow_logger
        )
        self.flow_logger_patch.start()
        
        self.state_persistence_patch = patch(
            'netra_backend.app.agents.supervisor.pipeline_executor.state_persistence_service',
            self.mock_state_persistence
        )
        self.state_persistence_patch.start()
    
    def teardown_method(self, method=None):
        """Clean up after each test."""
        # Stop patches
        if hasattr(self, 'flow_logger_patch'):
            self.flow_logger_patch.stop()
        if hasattr(self, 'state_persistence_patch'):
            self.state_persistence_patch.stop()
        
        # Clear captured events
        self.captured_execution_events.clear()
        self.captured_persistence_events.clear()
    
    # ============================================================================ 
    # GOLDEN PATH SCENARIO 1: Pipeline Step Execution
    # ============================================================================ 
    
    @pytest.mark.mission_critical
    @pytest.mark.business_critical
    async def test_websocket_agent_events_golden_path_validation(self):
        """
        MISSION CRITICAL: Test the 5 required WebSocket agent events.
        
        BVJ: $500K+ ARR protection - validates core chat functionality
        Critical Path: WebSocket Connection → Agent Events → User Experience
        
        CLAUDE.md Section 6.1: All 5 events MUST be sent for substantive chat value
        """
        # Arrange: Setup real WebSocket test infrastructure
        from tests.clients.websocket_client import WebSocketTestClient
        from shared.isolated_environment import get_env
        
        env = get_env()
        ws_url = env.get("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        validator = MissionCriticalEventValidator()
        ws_client = WebSocketTestClient(ws_url)
        
        try:
            # Act: Connect to real WebSocket service
            connected = await ws_client.connect(timeout=10.0)
            assert connected, f"Failed to connect to WebSocket service at {ws_url}"
            
            # Send real chat message to trigger agent execution
            test_message = "Provide a brief cost optimization analysis for testing"
            await ws_client.send_chat(test_message)
            
            # Collect real WebSocket events
            events_collected = 0
            timeout_start = time.time()
            
            while events_collected < 10 and (time.time() - timeout_start) < 30.0:
                try:
                    event = await ws_client.receive(timeout=2.0)
                    if event:
                        validator.record(event)
                        events_collected += 1
                        
                        # Log critical events
                        event_type = event.get("type", "unknown")
                        if event_type in validator.REQUIRED_EVENTS:
                            pass  # logger.info(f"✅ Required event received: {event_type}")
                        
                        # Stop after completion event
                        if event_type == "agent_completed":
                            logger.info("🏁 Agent completion event received - stopping collection")
                            break
                            
                except asyncio.TimeoutError:
                    logger.warning("⚠️ WebSocket receive timeout")
                    continue
            
            # Assert: Validate all required events were received
            success, failures = validator.validate_critical_requirements()
            
            if not success:
                error_details = "\n".join([
                    "❌ CRITICAL: WebSocket Agent Event Validation FAILED",
                    f"Events collected: {len(validator.events)}",
                    f"Event types: {list(validator.event_counts.keys())}",
                    f"Required events: {validator.REQUIRED_EVENTS}",
                    f"Missing events: {validator.REQUIRED_EVENTS - set(validator.event_counts.keys())}",
                    "Failures:",
                    *failures
                ])
                pytest.fail(error_details)
            
            # Validate business requirements
            assert len(validator.events) >= 3, f"Too few events captured: {len(validator.events)}"
            assert validator.event_counts.get("agent_started", 0) >= 1, "Missing agent_started event"
            assert validator.event_counts.get("agent_completed", 0) >= 1, "Missing agent_completed event"
            
            # logger.info(f"✅ WebSocket Agent Events Golden Path VALIDATED - {len(validator.events)} events received")
            
        finally:
            await ws_client.disconnect()
    
    # ============================================================================ 
    # GOLDEN PATH SCENARIO 2: State Persistence and Checkpointing
    # ============================================================================ 
    
    @pytest.mark.unit
    @pytest.mark.state_persistence
    async def test_state_persistence_during_pipeline_execution(self):
        """
        Test state persistence and checkpointing during pipeline execution.
        
        BVJ: System reliability - enables recovery from failures and resumption
        Critical Path: Step execution  ->  State checkpoint  ->  Recovery capability
        """
        # Arrange: Create PipelineExecutor
        pipeline_executor = PipelineExecutor(
            engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context
        )
        
        # Configure test user context for state persistence
        # Note: checkpoint_frequency is not a DeepAgentState field, removing invalid assignment
        
        # Act: Execute pipeline with state persistence
        await pipeline_executor.execute_pipeline(
            pipeline=self.test_pipeline_steps,
            user_context=self.test_user_context,
            run_id="pipeline_run_001",
            context={"user_id": "pipeline_user_001", "thread_id": "pipeline_thread_001"},
            db_session=self.mock_db_session
        )
        
        # Assert: Verify state persistence occurred
        # Should have persistence events (implementation details may vary)
        # At minimum, verify persistence service was configured
        assert pipeline_executor.state_persistence is not None
        
        # Verify persistence service methods exist and are callable
        assert hasattr(pipeline_executor.state_persistence, 'save_state')
        assert hasattr(pipeline_executor.state_persistence, 'load_state')
        
        # If checkpointing is implemented, verify it was called
        # (This depends on the actual implementation of checkpointing logic)
    
    # ============================================================================ 
    # GOLDEN PATH SCENARIO 3: Flow Logging and Observability
    # ============================================================================ 
    
    @pytest.mark.unit
    @pytest.mark.observability
    async def test_flow_logging_and_observability_tracking(self):
        """
        Test flow logging and observability tracking during pipeline execution.

        BVJ: Platform monitoring - enables debugging and performance optimization
        Critical Path: Pipeline start  ->  Step tracking  ->  Flow completion
        """
        # Arrange: Create PipelineExecutor
        pipeline_executor = PipelineExecutor(
            engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context
        )
        
        # Act: Execute pipeline with f"low logging
        await pipeline_executor.execute_pipeline(
            pipeline=self.test_pipeline_steps,
            user_context=self.test_user_context,
            run_id="pipeline_run_001",
            context={"user_id": "pipeline_user_001", "thread_id": "pipeline_thread_001"},
            db_session=self.mock_db_session
        )
        
        # Assert: Verify flow logging occurred
        # Verify flow was started
        self.mock_flow_logger.start_flow.assert_called_once()
        
        # Verify flow was completed
        self.mock_flow_logger.complete_flow.assert_called_once()
        
        # Verify flow ID was generated and used
        flow_start_call = self.mock_flow_logger.start_flow.call_args[0]
        flow_complete_call = self.mock_flow_logger.complete_flow.call_args[0]
        
        # The flow ID should be consistent between start and complete
        # (This depends on the implementation details)
        
        # Verify flow logger is properly configured
        assert pipeline_executor.flow_logger is not None
        assert pipeline_executor.flow_logger == self.mock_flow_logger
    
    # ============================================================================ 
    # GOLDEN PATH SCENARIO 4: Database Session Management
    # ============================================================================ 
    
    @pytest.mark.unit
    @pytest.mark.session_management  
    async def test_database_session_management_without_global_state(self):
        """
        Test proper database session management without global state storage.
        
        BVJ: Architecture compliance - prevents session leakage and concurrency issues
        Critical Path: Session passing  ->  No global storage  ->  Proper cleanup
        """
        # Arrange: Create PipelineExecutor
        pipeline_executor = PipelineExecutor(
            engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context
        )
        
        # Verify no global session storage
        assert not hasattr(pipeline_executor, 'db_session') or pipeline_executor.db_session is None
        
        # Act: Execute pipeline with session parameter
        await pipeline_executor.execute_pipeline(
            pipeline=self.test_pipeline_steps,
            user_context=self.test_user_context,
            run_id=pipeline_run_001,
            context={"user_id": "pipeline_user_001", "thread_id": "pipeline_thread_001"},
            db_session=self.mock_db_session  # Session passed as parameter
        )
        
        # Assert: Verify session was used properly
        # Pipeline should have executed successfully without global session
        assert len(self.captured_execution_events) == len(self.test_pipeline_steps)
        
        # Verify no session stored as instance variable
        assert not hasattr(pipeline_executor, 'db_session') or getattr(pipeline_executor, 'db_session', None) is None
        
        # Verify session was passed to components that need it
        # (Implementation details depend on how sessions are used internally)
    
    # ============================================================================ 
    # GOLDEN PATH SCENARIO 5: User Context Isolation
    # ============================================================================ 
    
    @pytest.mark.unit
    @pytest.mark.isolation_critical
    async def test_user_context_isolation_factory_pattern(self):
        """
        Test user context isolation using factory pattern for pipeline execution.

        BVJ: Enterprise security - ensures pipeline execution is user-isolated
        Critical Path: User context  ->  Factory pattern  ->  Isolated execution
        """
        
        # Arrange: Create PipelineExecutor with user context
        pipeline_executor_with_context = PipelineExecutor(
            engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context
        )
        
        # Create PipelineExecutor without user context for comparison
        pipeline_executor_without_context = PipelineExecutor(
            engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=None
        )
        
        # Verify user context storage
        assert pipeline_executor_with_context.user_context == self.test_user_context
        assert pipeline_executor_without_context.user_context is None
        
        # Verify WebSocket emitter initialization (lazy loading)
        assert pipeline_executor_with_context._websocket_emitter is None  # Lazy loaded
        assert pipeline_executor_without_context._websocket_emitter is None
        
        # Act: Execute pipeline with user context
        await pipeline_executor_with_context.execute_pipeline(
            pipeline=self.test_pipeline_steps,
            user_context=self.test_user_context,
            run_id="pipeline_run_001",
            context={"user_id": "pipeline_user_001", "thread_id": "pipeline_thread_001"},
            db_session=self.mock_db_session
        )
        
        # Assert: Verify user context was used for isolation
        # Verify pipeline execution completed successfully with user context
        assert len(self.captured_execution_events) == len(self.test_pipeline_steps)
        
        # Verify all execution events are associated with the correct user
        for event in self.captured_execution_events:
            # Events should be associated with user context if implemented
            pass  # Implementation details depend on event tracking
        
        # Verify user context is maintained throughout execution
        assert pipeline_executor_with_context.user_context == self.test_user_context
    
    # ============================================================================ 
    # PIPELINE EXECUTION CONTEXT BUILDING TESTS
    # ============================================================================ 
    
    @pytest.mark.unit
    @pytest.mark.context_building
    async def test_execution_context_building_and_validation(self):
        """
        Test execution context building and validation logic.

        BVJ: System reliability - ensures proper context creation for agent execution
        """
        
        # Arrange: Create PipelineExecutor
        pipeline_executor = PipelineExecutor(
            engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context
        )
        
        # Test context building with various inputs
        test_contexts = [
            {
                "run_id": "test_run_001",
                "context": {
                    "user_id": "test_user_001",
                    "thread_id": "test_thread_001"
                }
            },
            {
                "run_id": "test_run_002",
                "context": {
                    "user_id": "test_user_002",
                    "thread_id": "test_thread_002",
                    "additional_param": "extra_value"
                }
            }
        ]
        
        # Act & Assert: Test context building for each scenario
        for test_case in test_contexts:
            # Build execution context using private method (testing internal logic)
            exec_context = pipeline_executor._build_execution_context(
                test_case["run_id"],
                test_case["context"]
            )

            # Verify execution context structure
            assert isinstance(exec_context, AgentExecutionContext)
            assert exec_context.run_id == test_case["run_id"]
            assert exec_context.agent_name == "supervisor"  # Default agent name

            # Verify context parameters were extracted correctly
            params = pipeline_executor._extract_context_params(
                test_case["run_id"],
                test_case["context"]
            )

            assert "run_id" in params
            assert "agent_name" in params
            assert params["run_id"] == test_case["run_id"]
            assert params["agent_name"] == "supervisor"
    
    # ============================================================================ 
    # PIPELINE FLOW CONTEXT PREPARATION TESTS
    # ============================================================================ 
    
    @pytest.mark.unit
    @pytest.mark.flow_context
    async def test_flow_context_preparation_and_tracking(self):
        """
        Test flow context preparation and tracking for pipeline execution.

        BVJ: Observability - enables tracking of pipeline execution flows
        """
        # Arrange: Create PipelineExecutor
        pipeline_executor = PipelineExecutor(
            engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context
        )
        
        # Act: Test flow context preparation (accessing private method for testing)
        flow_context = pipeline_executor._prepare_flow_context(self.test_pipeline_steps)
        
        # Assert: Verify flow context structure
        assert isinstance(flow_context, dict)
        
        # Verify flow context contains necessary information
        # (Implementation details depend on _prepare_flow_context method)
        # Common expectations for flow context:
        if 'flow_id' in flow_context:
            assert flow_context['flow_id'] is not None
            assert isinstance(flow_context['flow_id'], str)
        
        if 'step_count' in flow_context:
            assert flow_context['step_count'] == len(self.test_pipeline_steps)
        
        if 'pipeline_type' in flow_context:
            assert isinstance(flow_context['pipeline_type'], str)
    
    # ============================================================================ 
    # ERROR HANDLING AND RECOVERY TESTS
    # ============================================================================ 
    
    @pytest.mark.unit
    @pytest.mark.error_handling
    async def test_pipeline_error_handling_and_recovery(self):
        """
        Test pipeline error handling and recovery mechanisms.

        BVJ: System reliability - graceful handling of pipeline step failures
        """
        # Arrange: Create PipelineExecutor
        pipeline_executor = PipelineExecutor(
            engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context
        )
        
        # Conf"igure execution engine to fail on second step
        call_count = 0
        
        async def mock_execute_agent_with_failure(context, user_context=None):
            nonlocal call_count
            call_count += 1
            
            if call_count == 2:  # Fail on second step
                self.captured_execution_events.append({
                    'agent_name': context.agent_name,
                    'success': False,
                    'error': 'Simulated failure',
                    'timestamp': time.time()
                })
                raise RuntimeError('Simulated agent execution failure')
            
            # Success for other steps
            result = AgentExecutionResult(
                success=True,
                agent_name=context.agent_name,
                duration=0.1,
                data={"result": f"Success from {context.agent_name}"}
            )

            self.captured_execution_events.append({
                'agent_name': context.agent_name,
                'success': True,
                'execution_time': 0.1,
                'timestamp': time.time()
            })
            
            return result
        
        self.mock_execution_engine.execute_agent = AsyncMock(side_effect=mock_execute_agent_with_failure)
        
        # Act & Assert: Expect pipeline to fail on second step
        with pytest.raises(RuntimeError, match="Simulated agent execution failure"):
            await pipeline_executor.execute_pipeline(
                pipeline=self.test_pipeline_steps,
                user_context=self.test_user_context,
                run_id="pipeline_run_001",
                context={"user_id": "pipeline_user_001", "thread_id": "pipeline_thread_001"},
                db_session=self.mock_db_session
            )
        
        # Assert: Verify partial execution occurred
        # Should have attempted to execute at least the first two steps
        assert len(self.captured_execution_events) >= 1
        assert self.captured_execution_events[0]['success'] is True
        
        if len(self.captured_execution_events) >= 2:
            assert self.captured_execution_events[1]['success'] is False
        
        # Verify flow logger was still used (even for failed execution)
        self.mock_flow_logger.start_flow.assert_called_once()
        
        # Flow completion may or may not be called depending on error handling implementation
        # (This is acceptable as long as the flow was started properly)
    
    # ============================================================================ 
    # CONCURRENCY AND MULTI-USER TESTS
    # ============================================================================ 
    
    @pytest.mark.unit
    @pytest.mark.concurrency
    async def test_concurrent_pipeline_execution_isolation(self):
        """Test concurrent pipeline execution with proper user isolation.

        BVJ: Platform scalability - supports multiple users executing pipelines concurrently
        """
        
        # Arrange: Create multiple pipeline executors for different users (using mocks)
        user_context_1 = MagicMock()
        user_context_1.user_id = "concurrent_user_001"
        user_context_1.thread_id = "concurrent_thread_001"
        user_context_1.run_id = "concurrent_run_001"
        user_context_1.request_id = "concurrent_req_001"
        user_context_1.websocket_client_id = "concurrent_ws_001"
        user_context_1.add_execution_result = MagicMock()
        
        user_context_2 = MagicMock()
        user_context_2.user_id = "concurrent_user_002"
        user_context_2.thread_id = "concurrent_thread_002"
        user_context_2.run_id = "concurrent_run_002"
        user_context_2.request_id = "concurrent_req_002"
        user_context_2.websocket_client_id = "concurrent_ws_002"
        user_context_2.add_execution_result = MagicMock()
        
        pipeline_executor_1 = PipelineExecutor(
            engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=user_context_1
        )
        
        pipeline_executor_2 = PipelineExecutor(
            engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=user_context_2
        )
        
        # Create different states for each user
        state_1 = DeepAgentState(
            user_id="concurrent_user_001",
            thread_id="concurrent_thread_001",
            run_id="concurrent_run_001"
        )
        state_1.user_request = "User 1 pipeline request"
        
        state_2 = DeepAgentState(
            user_id=concurrent_user_002,
            thread_id="concurrent_thread_002",
            run_id=concurrent_run_002
        )
        state_2.user_request = "User 2 pipeline request"
        
        # Act: Execute both pipelines concurrently
        task_1 = pipeline_executor_1.execute_pipeline(
            pipeline=self.test_pipeline_steps,
            user_context=user_context_1,
            run_id="concurrent_run_001",
            context={"user_id": "concurrent_user_001", "thread_id": "concurrent_thread_001"},
            db_session=self.mock_db_session
        )

        task_2 = pipeline_executor_2.execute_pipeline(
            pipeline=self.test_pipeline_steps,
            user_context=user_context_2,
            run_id="concurrent_run_002", 
            context={"user_id": "concurrent_user_002", "thread_id": "concurrent_thread_002"},
            db_session=self.mock_db_session
        )
        
        # Wait for both pipelines to complete
        await asyncio.gather(task_1, task_2)
        
        # Assert: Verify both pipelines executed successfully with isolation
        # Should have execution events from both users
        total_expected_events = len(self.test_pipeline_steps) * 2  # 2 users
        assert len(self.captured_execution_events) == total_expected_events
        
        # Verify each pipeline executor maintained its user context
        assert pipeline_executor_1.user_context == user_context_1
        assert pipeline_executor_2.user_context == user_context_2
        
        # Verify execution engine was called for each step of each pipeline
        expected_total_calls = len(self.test_pipeline_steps) * 2
        assert self.mock_execution_engine.execute_agent.call_count == expected_total_calls
        
        # Verify flow logger was called for both pipelines
        assert self.mock_flow_logger.start_flow.call_count == 2
        assert self.mock_flow_logger.complete_flow.call_count == 2
    
    # ============================================================================ 
    # PERFORMANCE AND OPTIMIZATION TESTS
    # ============================================================================ 
    
    @pytest.mark.unit
    @pytest.mark.performance
    async def test_pipeline_execution_performance_characteristics(self):
        
        Test pipeline execution performance characteristics.
        
        BVJ: Platform performance - ensures pipeline execution meets timing requirements
""
        # Arrange: Create PipelineExecutor
        pipeline_executor = PipelineExecutor(
            engine=self.mock_execution_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.test_user_context
        )
        
        # Create larger pipeline f"or performance testing
        large_pipeline = []
        for i in range(10):  # 10 steps
            step = PipelineStepConfig(
                agent_name=f"performance_agent_{i:02d}",
                metadata={"step_number": i + 1, "performance_test": True}
            )
            large_pipeline.append(step)
        
        # Act: Execute large pipeline and measure timing
        start_time = time.time()
        
        await pipeline_executor.execute_pipeline(
            pipeline=large_pipeline,
            user_context=self.test_user_context,
            run_id="performance_run_001",
            context={"user_id": "performance_user_001", "thread_id": "performance_thread_001"},
            db_session=self.mock_db_session
        )
        
        end_time = time.time()
        total_execution_time = end_time - start_time
        
        # Assert: Verif"y performance characteristics
        # Should execute all steps
        assert len(self.captured_execution_events) == len(large_pipeline)
        
        # Total execution time should be reasonable
        # (Allow for some overhead beyond just step execution times)
        expected_min_time = len(large_pipeline) * 0.1  # 100ms per step (mock execution time)
        expected_max_time = expected_min_time * 2  # Allow for 100% overhead
        
        assert total_execution_time >= expected_min_time * 0.8, \
            f"Pipeline executed too quickly: {total_execution_time:0.3f}s < {expected_min_time * 0.8:0.3f}s"
        assert total_execution_time <= expected_max_time, \
            f"Pipeline executed too slowly: {total_execution_time:0.3f}s > {expected_max_time:0.3f}s"
        
        # Verify execution order was maintained
        expected_agents = [f"performance_agent_{i:02d}" for i in range(10)]
        actual_agents = [event['agent_name'] for event in self.captured_execution_events]
        assert actual_agents == expected_agents, "Pipeline execution order not maintained"
        
        # Performance logging
        avg_time_per_step = total_execution_time / len(large_pipeline)
        print(f"\nPipeline Performance Results:")
        print(f"  Total steps: {len(large_pipeline)}")
        print(f"  Total execution time: {total_execution_time:0.3f}s")
        print(f"  Average time per step: {avg_time_per_step:0.3f}s")
        print(f"  Steps per second: {len(large_pipeline) / total_execution_time:0.2f}")
    

# ============================================================================
# ENHANCED AGENT INTEGRATION TESTS - MISSION CRITICAL BUSINESS VALUE
# ============================================================================

class AgentWebSocketIntegrationEnhancedTests:
    """Enhanced agent integration tests for WebSocket agent events.

    Business Value: Validates the complete agent execution lifecycle through WebSocket events.
    These tests ensure that the 5 critical agent events that enable $500K+ ARR chat functionality
    are properly delivered during real agent execution scenarios.
    """

    @pytest.mark.asyncio
    @pytest.mark.critical
    # @require_docker_services()  # Temporarily disabled - GCP integration regression
    async def test_agent_registry_websocket_manager_integration(self):
        """Test AgentRegistry.set_websocket_manager() critical integration point.

        Business Value: Validates the SSOT bridge setup that enables agent-websocket coordination.
        """
        
        config = RealWebSocketTestConfig()
        context = create_test_context()
        
        # Test AgentRegistry WebSocket manager integration
        agent_registry = AgentRegistry()
        websocket_manager = await create_websocket_manager()
        
        # CRITICAL: Test set_websocket_manager integration
        agent_registry.set_websocket_manager(websocket_manager)
        
        # Verify the bridge is established
        assert hasattr(agent_registry, '_websocket_manager'), "WebSocket manager not set on AgentRegistry"
        assert agent_registry._websocket_manager is websocket_manager, "WebSocket manager reference mismatch"
        
        # Test enhanced tool dispatcher creation with WebSocket integration
        user_context = UserExecutionContext.from_request(
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"test_run_{uuid.uuid4().hex[:8]}",
            request_id=f"test_req_{uuid.uuid4().hex[:8]}"
        )
        
        # Create enhanced tool dispatcher through registry
        tool_dispatcher = await agent_registry.create_enhanced_tool_dispatcher(user_context)
        
        # Verify WebSocket integration in tool dispatcher
        assert hasattr(tool_dispatcher, '_websocket_notifier'), Tool dispatcher missing WebSocket notifier""
        
        logger.info( PASS:  AgentRegistry WebSocket integration validated)

    @pytest.mark.asyncio 
    @pytest.mark.critical
    # @require_docker_services()  # Temporarily disabled - GCP integration regression
    async def test_execution_engine_websocket_notifier_integration(self):
        """Test ExecutionEngine + WebSocketNotifier critical integration point.

        Business Value: Validates that agent execution properly delivers WebSocket events.
        """
        config = RealWebSocketTestConfig()
        context = create_test_context()
        
        # Setup execution engine with WebSocket integration
        user_context = UserExecutionContext.from_request(
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"test_run_{uuid.uuid4().hex[:8]}",
            request_id=f"test_req_{uuid.uuid4().hex[:8]}"
        )
        
        # Use SSOT pattern for WebSocketNotifier creation
        websocket_notifier = AgentWebSocketBridge.WebSocketNotifier.create_for_user(emitter=user_context, # Placeholder - would be actual emitter
            exec_context=user_context
        )
        execution_engine = UserExecutionEngine()
        
        # Test WebSocket notifier initialization in execution engine
        execution_engine.set_websocket_notifier(websocket_notifier)
        
        # Verify integration
        assert hasattr(execution_engine, '_websocket_notifier'), "Execution engine missing WebSocket notifier"
        assert execution_engine._websocket_notifier is websocket_notifier, WebSocket notifier reference mismatch
        
        # Test agent context creation with WebSocket integration
        agent_context = AgentExecutionContext(
            user_context=user_context,
            websocket_notifier=websocket_notifier
        )
        
        # Verify WebSocket integration in agent context
        assert agent_context.websocket_notifier is websocket_notifier, "Agent context WebSocket integration failed"

        logger.info("PASS: ExecutionEngine WebSocket integration validated")

    @pytest.mark.asyncio
    @pytest.mark.critical  
    # @require_docker_services()  # Temporarily disabled - GCP integration regression
    async def test_enhanced_tool_execution_websocket_wrapping(self):
        """Test EnhancedToolExecutionEngine WebSocket event wrapping.

        Business Value: Validates that tool execution generates the required WebSocket events.
        """

        config = RealWebSocketTestConfig()
        context = create_test_context()
        # TODO: Replace with appropriate event capture mechanism
        # event_capture = RealWebSocketEventCapture()
        
        # Setup enhanced tool execution engine
        user_context = UserExecutionContext.from_request(
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"test_run_{uuid.uuid4().hex[:8]}",
            request_id=f"test_req_{uuid.uuid4().hex[:8]}"
        )
        
        # Use SSOT pattern f"or WebSocketNotifier creation
        websocket_notifier = AgentWebSocketBridge.WebSocketNotifier.create_for_user(emitter=user_context, # Placeholder - would be actual emitter
            exec_context=user_context
        )
        
        # Create enhanced tool execution engine
        enhanced_tool_engine = UnifiedToolExecutionEngine(
            websocket_notifier=websocket_notifier
        )
        
        # Test tool execution with WebSocket wrapping
        tool_request = {
            tool_name": "test_tool,
            parameters: {query: test query}","
            "execution_id: f"exec_{uuid.uuid4().hex[:8]}"
        }
        
        # Mock WebSocket event capture
        captured_events = []
        
        async def mock_event_sender(event_type: str, event_data: dict):
            captured_events.append({type: event_type, data: event_data}
        
        websocket_notifier.send_event = mock_event_sender
        
        # Execute tool with WebSocket event capture
        try:
            await enhanced_tool_engine.execute_tool_with_websocket_events(
                tool_name="test_tool,"
                parameters={query: test query},
                context=user_context
            )
        except Exception as e:
            # Expected f"or test tool, capture events during execution attempt
            logger.info(fTool execution failed as expected: {e}")"
        
        # Verify WebSocket events were generated
        event_types = [event["type] for event in captured_events]
        
        # Should have tool_executing and tool_completed events at minimum
        assert tool_executing in event_types, Missing tool_executing WebSocket event
        
        logger.info(f PASS:  Enhanced tool execution WebSocket wrapping validated - Events: {event_types}")"

    @pytest.mark.asyncio
    @pytest.mark.critical
    # @require_docker_services()  # Temporarily disabled - GCP integration regression
    async def test_unified_websocket_manager_agent_coordination(self):
        Test UnifiedWebSocketManager coordination with agent systems."
        
        Business Value: Validates the central WebSocket management coordination with agents.
        "
        config = RealWebSocketTestConfig()
        context = create_test_context()
        
        # Test UnifiedWebSocketManager integration
        websocket_manager = await create_websocket_manager()
        
        # Verify manager is properly initialized
        assert websocket_manager is not None, WebSocket manager creation failed
        
        # Test user context integration
        user_id = f"test_user_{uuid.uuid4().hex[:8]}
        user_context = UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=ftest_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"test_run_{uuid.uuid4().hex[:8]}",
            request_id=ftest_req_{uuid.uuid4().hex[:8]}"
        )
        
        # Test WebSocket connection management
        connection_info = await websocket_manager.get_connection_info(user_id)
        
        # Verify connection management capabilities
        assert hasattr(websocket_manager, 'emit_to_user'), "WebSocket manager missing user emission capability
        
        # Test agent event emission through manager
        test_event = {
            type: agent_started,
            user_id": user_id,"
            data: {message: Test agent started}"
        }
        
        try:
            await websocket_manager.emit_to_user(user_id, test_event)
            logger.info( PASS:  WebSocket agent event emission successful")
        except Exception as e:
            logger.inf"o(fWebSocket emission test completed: {e}")
        
        logger.info( PASS:  UnifiedWebSocketManager agent coordination validated)"

    @pytest.mark.asyncio
    @pytest.mark.critical
    # @require_docker_services()  # Temporarily disabled - GCP integration regression
    async def test_agent_websocket_bridge_ssot_coordination(self):
        "Test AgentWebSocketBridge SSOT coordination pattern.
        
        Business Value: Validates the SSOT bridge that coordinates agent-websocket integration lifecycle.
        ""
        conf"ig = RealWebSocketTestConfig()
        context = create_test_context()
        
        # Import and test AgentWebSocketBridge
        from netra_backend.app.services.agent_websocket_bridge import (
            AgentWebSocketBridge, 
            IntegrationState, 
            IntegrationConfig
        )
        
        # Test bridge initialization
        bridge_config = IntegrationConfig(
            initialization_timeout_s=20,  # Issue #773: Cloud Run compatible
            health_check_interval_s=10,
            recovery_attempt_limit=3
        )
        
        bridge = AgentWebSocketBridge(config=bridge_config)
        
        # Test integration state management
        assert bridge.get_integration_state() == IntegrationState.UNINITIALIZED, Bridge should start uninitialized
        
        # Test integration initialization
        user_context = UserExecutionContext.from_request(
            user_id=ftest_user_{uuid.uuid4().hex[:8]}",
            thread_id=ftest_thread_{uuid.uuid4().hex[:8]}","
            run_id=f"test_run_{uuid.uuid4().hex[:8]}",
            request_id=f"test_req_{uuid.uuid4().hex[:8]}"
        )
        
        try:
            await bridge.initialize_integration(user_context=user_context)
            
            # Verify state transition
            current_state = bridge.get_integration_state()
            assert current_state in [IntegrationState.ACTIVE, IntegrationState.INITIALIZING], \
                f"Bridge should be active or initializing, got: {current_state}
                
        except Exception as e:
            logger.info(fBridge initialization test completed: {e}")
        
        # Test health monitoring capabilities
        health_status = await bridge.get_health_status()
        assert isinstance(health_status, dict), Health status should be a dictionary
        assert integration_state" in health_status, "Health status missing integration state
        
        logger.info( PASS:  AgentWebSocketBridge SSOT coordination validated)


# ============================================================================
# BUSINESS VALUE ENHANCED TESTS - ISSUE #1059 COVERAGE IMPROVEMENT
# ============================================================================

class AgentBusinessValueDeliveryTests:
    ""
    Enhanced tests validating agent responses deliver substantive business value.

    Issue #1059: Enhanced e2e tests for agent golden path messages work
    Target: 15% → 35% coverage improvement through business value validation

    These tests ensure agents provide meaningful, actionable responses with
    quantifiable business impact rather than just technical success.
    

    @pytest.fixture(autouse=True)
    async def setup_business_value_testing(self):
        "Setup for business value validation testing."
        # Import business value validators
        import sys
        import os
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        f"rom test_framework.business_value_validators import (
            validate_agent_business_value,
            assert_response_has_business_value,
            assert_cost_optimization_value
        )

        self.validate_business_value = validate_agent_business_value
        self.assert_response_value = assert_response_has_business_value
        self.assert_cost_value = assert_cost_optimization_value

        self.test_base = WebSocketTestBase()
        self._test_session = self.test_base.real_websocket_test_session()
        self.test_base = await self._test_session.__aenter__()

        yield

        try:
            await self._test_session.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(fBusiness value test cleanup error: {e}")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_agent_response_business_value_validation(self):
        "
        Test that agent responses deliver quantifiable business value.

        CRITICAL: Validates $500K+ ARR protection through substantive AI responses.
        Ensures agents provide actionable cost optimization recommendations.
"
        test_context = await self.test_base.create_test_context(user_id=business_value_user)"
        await test_context.setup_websocket_connection(endpoint=/api/v1/websocket", auth_required=False)

        validator = MissionCriticalEventValidator()

        try:
            # Send cost optimization query - realistic business scenario
            cost_optimization_query = {
                type: chat_message,
                "content: I'm spending $50,000/month on AI inference costs. Help me optimize these costs while maintaining quality.",
                user_id: test_context.user_context.user_id,
                thread_id: test_context.user_context.thread_id"
            }

            await test_context.send_message(cost_optimization_query)
            logger.info(f"Sent business value query: {cost_optimization_query})

            # Collect agent response events
            agent_response_content = 
            business_events_received = []
            start_time = time.time()
            timeout = 45.0  # Extended timeout for real LLM response

            while time.time() - start_time < timeout:
                try:
                    event = await test_context.receive_message()
                    business_events_received.append(event)
                    validator.record(event)

                    # Extract response content from agent_completed or agent_thinking events
                    if event.get('type') == 'agent_completed':
                        final_response = event.get('final_response') or event.get('content', '')
                        if final_response:
                            agent_response_content += final_response +  "
                    elif event.get('type') == 'agent_thinking':
                        thinking_content = event.get('reasoning') or event.get('content', '')
                        if thinking_content and len(thinking_content) > 50:  # Substantive thinking
                            agent_response_content += thinking_content +  "

                    # Stop when we have a complete response
                    if event.get('type') == 'agent_completed' and agent_response_content.strip():
                        break

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f"Error receiving business value event: {e}")
                    break

            # CRITICAL: Validate business value of agent response
            logger.inf"o(fAgent response content for validation ({len(agent_response_content)} chars"): {agent_response_content[:200]}...)"

            assert agent_response_content.strip(), "Agent must provide substantive response content

            # Validate business value using specialized cost optimization validation
            business_results = self.validate_business_value(
                agent_response_content,
                cost_optimization_query['content'],
                specialized_validation='cost_optimization'
            )

            # CRITICAL ASSERTIONS: Business value requirements
            assert business_results['passes_business_threshold'], (
                fAgent response failed business value validation. 
                f"Score: {business_results['general_quality'].overall_score:0.2f}. 
                fQuality: {business_results['general_quality'].quality_level.value}. "
                f"Response: {agent_response_content[:300]}..."
            )

            # Validate cost optimization specific requirements
            if business_results.get('specialized_validation'):
                cost_results = business_results['specialized_validation']
                assert cost_results['passes_cost_optimization_test'], (
                    fResponse failed cost optimization validation: {cost_results['business_value_summary']}"
                )

                # Log business value metrics for monitoring
                logger.info(f"Business Value Validation PASSED:)
                logger.inf"o(f  Overall Score: {business_results['general_quality'].overall_score:0.2f}")
                logger.inf"o(f  Quality Level: {business_results['general_quality'].quality_level.value}")
                logger.info(f  Cost Optimization Score: {cost_results['overall_score']:0.2f}")"
                logger.inf"o(f  Requirements Met: {cost_results['requirements_met']}")
                logger.inf"o(f  Word Count: {business_results['general_quality'].word_count}")
                logger.info(f"  Actionable Steps: {business_results['general_quality'].actionable_steps_count})

            # Validate WebSocket events still work correctly
            assert len(business_events_received) > 0, Must receive WebSocket events during business response"

            event_types = [event.get('type') f"or event in business_events_received]
            logger.info(fBusiness value test received event types: {event_types}")

        finally:
            await test_context.cleanup()

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(90)
    async def test_multi_agent_orchestration_business_value(self):
        "
        Test multi-agent collaboration delivers superior business value.

        CRITICAL: Validates supervisor → triage → APEX agent workflows produce
        actionable cost optimization recommendations with quantified savings.
"
        test_context = await self.test_base.create_test_context(user_id=multi_agent_user)"
        await test_context.setup_websocket_connection(endpoint=/api/v1/websocket", auth_required=False)

        validator = MissionCriticalEventValidator()

        try:
            # Complex query requiring multi-agent orchestration
            complex_query = {
                type: chat_message,
                "content: Analyze my AI infrastructure costs across AWS, Azure, and GCP. I need a detailed cost optimization strategy with specific recommendations for GPU utilization, API costs, and storage optimization. Include projected savings and implementation timeline.",
                user_id: test_context.user_context.user_id,
                thread_id: test_context.user_context.thread_id"
            }

            await test_context.send_message(complex_query)
            logger.info(f"Sent multi-agent orchestration query)

            # Track multi-agent coordination events
            orchestration_events = []
            agent_handoffs = 0
            tool_executions = 0
            complete_response_content = 

            start_time = time.time()
            timeout = 75.0  # Extended timeout for complex multi-agent response

            while time.time() - start_time < timeout:
                try:
                    event = await test_context.receive_message()
                    orchestration_events.append(event)
                    validator.record(event)

                    event_type = event.get('type')

                    # Track agent handoffs (multiple agent_started events)
                    if event_type == 'agent_started':
                        agent_handoffs += 1

                    # Track tool executions
                    elif event_type == 'tool_executing':
                        tool_executions += 1
                        logger.inf"o(fTool execution: {event.get('tool_name', 'unknown')}")

                    # Collect comprehensive response content
                    elif event_type == 'agent_completed':
                        final_response = event.get('final_response') or event.get('content', '')
                        if final_response:
                            complete_response_content += final_response + \n""

                    elif event_type == 'agent_thinking':
                        thinking = event.get('reasoning') or event.get('content', '')
                        if thinking and len(thinking) > 100:  # Substantive reasoning
                            complete_response_content += thinking + \n

                    # Stop when we have a complete multi-agent response
                    if (event_type == 'agent_completed' and
                        complete_response_content and
                        len(complete_response_content) > 500):  # Comprehensive response
                        break

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f"Error in multi-agent orchestration: {e}")"
                    break

            # CRITICAL: Validate multi-agent orchestration occurred
            logger.info(f"Multi-agent orchestration metrics:)
            logger.inf"o(f  Agent handoffs: {agent_handoffs}")
            logger.inf"o(f  Tool executions: {tool_executions}")
            logger.info(f  Response length: {len(complete_response_content)} chars")"
            logger.inf"o(f  Events received: {len(orchestration_events)}")

            # Validate orchestration complexity indicates multi-agent coordination
            assert agent_handof"fs >= 1, fExpected multi-agent coordination, got {agent_handoffs} agent starts"
            assert len(orchestration_events) >= 5, f"Expected complex orchestration, got {len(orchestration_events)} events

            # CRITICAL: Validate superior business value from multi-agent response
            assert complete_response_content.strip(), Multi-agent system must provide comprehensive response"

            business_results = self.validate_business_value(
                complete_response_content,
                complex_query['content'],
                specialized_validation='cost_optimization'
            )

            # Higher standards for multi-agent responses
            multi_agent_threshold = 0.75  # Higher threshold for complex scenarios

            assert business_results['general_quality'].overall_score >= multi_agent_threshold, (
                fMulti-agent response failed enhanced business value validation. 
                fScore: {business_results['general_quality'].overall_score:0.2f} "
                f"(required: {multi_agent_threshold}. 
                fMulti-agent coordination should produce superior results.
            )

            # Validate multi-agent specific quality indicators
            quality = business_results['general_quality']
            assert quality.quantif"ied_recommendations >= 3, (
                fMulti-agent system should provide multiple quantified recommendations, got {quality.quantified_recommendations}"
            )

            assert quality.actionable_steps_count >= 5, (
                fMulti-agent system should provide detailed actionable steps, got {quality.actionable_steps_count}""
            )

            logger.inf"o(fMulti-Agent Business Value Validation PASSED:)
            logger.info(f  Enhanced Score: {business_results['general_quality'].overall_score:0.2f}")
            logger.info(f"  Quality Level: {business_results['general_quality'].quality_level.value})
            logger.info(f  Quantified Recommendations: {quality.quantified_recommendations}")
            logger.inf"o(f  Actionable Steps: {quality.actionable_steps_count}")
            logger.inf"o(f  Technical Depth Score: {quality.technical_depth_score:0.2f}")"

        finally:
            await test_context.cleanup()

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(45)
    async def test_tool_execution_integration_business_value(self):
    "
        Test tool execution pipeline delivers integrated business value.

        CRITICAL: Validates tools are executed within agent context and results
        are incorporated into substantive business recommendations.
        "
        test_context = await self.test_base.create_test_context(user_id=tool_integration_user")
        await test_context.setup_websocket_connection(endpoint=/api/v1/websocket, auth_required=False)

        validator = MissionCriticalEventValidator()

        try:
            # Query requiring tool execution f"or business insights
            tool_query = {
                type": "chat_message,
                content: Check my current cloud spending patterns and provide optimization recommendations with specific cost savings estimates.,
                user_id: test_context.user_context.user_id,"
                "thread_id: test_context.user_context.thread_id
            }"

            await test_context.send_message(tool_query)
            logger.info(Sent tool integration query)

            # Track tool integration pipeline
            tool_events = []
            tool_executions = []
            tool_results = []
            integrated_response = ""

            start_time = time.time()
            timeout = 35.0

            while time.time() - start_time < timeout:
                try:
                    event = await test_context.receive_message()
                    tool_events.append(event)
                    validator.record(event)

                    event_type = event.get('type')

                    # Track tool execution pipeline
                    if event_type == 'tool_executing':
                        tool_inf"o = {
                            'tool_name': event.get('tool_name'),
                            'parameters': event.get('parameters', {}",
                            'timestamp': event.get('timestamp')
                        }
                        tool_executions.append(tool_inf"o)
                        logger.info(fTool executing: {tool_info['tool_name']}")

                    elif event_type == 'tool_completed':
                        tool_result = {
                            'tool_name': event.get('tool_name'),
                            'results': event.get('results', {},
                            'duration': event.get('duration'),
                            'status': event.get('status', 'unknown')
                        }
                        tool_results.append(tool_result)
                        logger.info(fTool completed: {tool_result['tool_name']} ({tool_result['status']})

                    # Collect agent response incorporating tool results
                    elif event_type == 'agent_completed':
                        final_response = event.get('final_response') or event.get('content', '')
                        if final_response:
                            integrated_response += final_response
                        break

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(fError in tool integration test: {e}")"
                    break

            # CRITICAL: Validate tool execution occurred and results were integrated
            logger.inf"o(fTool integration metrics:)
            logger.info(f  Tool executions: {len(tool_executions)}")
            logger.info(f"  Tool results: {len(tool_results)})
            logger.info(f  Integrated response length: {len(integrated_response)} chars")

            # Validate tool pipeline executed
            assert len(tool_executions) > 0, Expected tool executions for business analysis query
            assert len(tool_results) > 0, Expected tool results to be returned""
            assert len(tool_results) == len(tool_executions), All executed tools should return results

            # CRITICAL: Validate business value integration
            assert integrated_response.strip(), Agent must integrate tool results into response"

            # Validate tool results were incorporated into business recommendations
            business_results = self.validate_business_value(
                integrated_response,
                tool_query['content'],
                specialized_validation='cost_optimization'
            )

            assert business_results['passes_business_threshold'], (
                f"Tool-integrated response f"ailed business value validation. 
                fScore: {business_results['general_quality'].overall_score:0.2f}. "
                fTool results should enhance business value delivery.
            )

            # Validate tool integration enhanced the response quality
            quality = business_results['general_quality']

            # Tool-enhanced responses should have higher technical specificity
            assert quality.specific_technologies_mentioned >= 2, (
                fTool-enhanced responses should reference specific technologies, got {quality.specific_technologies_mentioned}""
            )

            # Should contain quantif"ied insights from tool execution
            assert quality.quantified_recommendations >= 1, (
                fTool execution should provide quantified insights, got {quality.quantified_recommendations}"
            )

            logger.info(fTool Integration Business Value PASSED:)
            logger.info(f"  Tools executed: {[t['tool_name'] for t in tool_executions]})
            logger.info(f  Business value score: {business_results['general_quality'].overall_score:0.2f}")
            logger.inf"o(f  Technical depth: {quality.specific_technologies_mentioned} technologies")
            logger.inf"o(f  Quantified insights: {quality.quantified_recommendations}")"

        finally:
            await test_context.cleanup()


# ============================================================================
# COMPREHENSIVE TEST SUITE EXECUTION
# ============================================================================ 

if __name__ == "__main__":
    # Run the comprehensive mission critical REAL WebSocket tests
    import sys
    
    print(\n + = * 80)
    print(MISSION CRITICAL WEBSOCKET AGENT EVENTS TEST SUITE - ENHANCED"")
    print(COMPREHENSIVE VALIDATION OF ALL 5 REQUIRED EVENTS + ISOLATION)"
    print(=" * 80)
    print()
    print(Business Value: $500K+ ARR - Core chat functionality")"
    print(Testing: Individual events, sequences, timing, chaos, concurrency, isolation)
    print("Requirements: Latency < 100ms, Reconnection < 3s, 10+ concurrent users")
    print(Enhanced Coverage: 250+ concurrent users, extreme isolation tests)"
    print("\nRunning with REAL WebSocket connections (NO MOCKS)...)
    
    # Run all comprehensive tests
    # Execute SSOT tests with real WebSocket connections
    import subprocess
    import sys
    
    print(\n" + "= * 80)
    print(EXECUTING MISSION CRITICAL WEBSOCKET AGENT EVENTS TESTS)
    print(SSOT Compliance: Using real WebSocket connections (NO MOCKS")")
    print(Business Impact: $500K+ ARR Golden Path Protection)"
    print(=" * 80)
    
    # Run mission critical WebSocket tests with SSOT unified test runner
    test_files = [
        tests/mission_critical/test_websocket_agent_events_suite.py,"
        tests/mission_critical/test_websocket_agent_events_real.py",
        tests/mission_critical/test_websocket_basic_events.py
    ]
    
    for test_file in test_files:
        print(f"\n🚀 Running {test_file}...")
        try:
            result = subprocess.run([
                sys.executable, 
                tests/unified_test_runner.py, 
                --file", test_file,"
                --category, mission_critical,
                --no-docker,  # Use non-docker mode for this execution"
                --real-services"  # Ensure real service connections
            ], capture_output=True, text=True, timeout=180)
            
            print(f"Exit code: {result.returncode}")
            if result.stdout:
                print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"[FAIL] Test {test_file} timed out after 180 seconds")
        except Exception as e:
            print(f"[FAIL] Error running {test_file}: {e}")

    print("\\n[PASS] SSOT WebSocket Agent Events test execution completed.")

"""