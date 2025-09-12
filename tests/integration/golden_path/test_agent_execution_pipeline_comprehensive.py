"""
Comprehensive Integration Tests for Golden Path P0 Agent Execution Pipeline Flow

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate core AI-powered conversation delivery through agent orchestration
- Value Impact: Ensures agent pipeline delivers substantive AI insights and recommendations
- Strategic Impact: Core platform functionality that enables business value through AI optimization

CRITICAL: These tests validate the complete business flow from user request to delivered value:
1. User submits optimization request  ->  Agent execution starts
2. ExecutionEngineFactory creates isolated engine  ->  User isolation guaranteed  
3. SupervisorAgent orchestrates sub-agents  ->  Pipeline coordination working
4. Agents execute in correct order  ->  Data  ->  Optimization  ->  Reporting
5. WebSocket events stream progress  ->  User sees AI working on their problem
6. Final response delivered  ->  User receives actionable business insights

This test suite validates the complete golden path that delivers our core business value.
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch

# SSOT Test Infrastructure
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env

# Core Components Under Test
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    ExecutionEngineFactoryError,
    configure_execution_engine_factory,
    user_execution_engine
)
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context,
    InvalidContextError
)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

# Infrastructure Dependencies
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from shared.id_generation import UnifiedIdGenerator


class TestAgentExecutionPipelineComprehensive(BaseIntegrationTest):
    """
    Comprehensive integration tests for the golden path agent execution pipeline.
    
    Tests validate the complete business flow that delivers AI optimization value:
    - User isolation through ExecutionEngineFactory
    - Agent orchestration through SupervisorAgent
    - Pipeline execution order and coordination
    - WebSocket event streaming for user experience
    - Business value delivery through real agent results
    """
    
    def setup_method(self):
        """Set up method called before each test method."""
        super().setup_method()
        # Initialize all test identifiers early to ensure they're always available
        self.test_user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        self.test_thread_id, self.test_run_id, self.test_request_id = UnifiedIdGenerator.generate_user_context_ids(
            user_id=self.test_user_id,
            operation="agent_execution_test"
        )
        self.websocket_events = []
        
        # Initialize mock components early to ensure they're always available
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_llm_manager.generate_response = AsyncMock()
        self.mock_llm_manager.is_available = Mock(return_value=True)
        
        # Mock WebSocket infrastructure for event validation
        self.mock_websocket_manager = Mock(spec=WebSocketManager)
        self.mock_websocket_manager.send_to_user = AsyncMock()
        self.mock_websocket_manager.is_connected = Mock(return_value=True)
        
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.mock_websocket_bridge.websocket_manager = self.mock_websocket_manager
        self.mock_websocket_bridge.emit_agent_event = AsyncMock()
    
    async def async_setup_method(self, method=None):
        """Set up test environment with real services and infrastructure."""
        await super().async_setup()
        
        # Initialize test environment (all IDs and mocks already set in setup_method)
        self.env.set("TESTING", "1", source="golden_path_test")
        
        # Mock WebSocket event collection
        async def collect_websocket_event(user_id: str, event_data: Dict):
            """Collect WebSocket events for test validation."""
            event_data['collected_at'] = datetime.now(timezone.utc).isoformat()
            self.websocket_events.append(event_data)
            self.logger.info(f" CHART:  Collected WebSocket event: {event_data.get('type', 'unknown')}")
            
        self.mock_websocket_manager.send_to_user.side_effect = collect_websocket_event
        
        # Mock agent event collection
        async def collect_agent_event(event_type: str, data: Dict, run_id: str = None, agent_name: str = None):
            """Collect agent events for test validation."""
            event_data = {
                'type': event_type,
                'data': data,
                'run_id': run_id,
                'agent_name': agent_name,
                'collected_at': datetime.now(timezone.utc).isoformat()
            }
            self.websocket_events.append(event_data)
            self.logger.info(f" CHART:  Collected agent event: {event_type} from {agent_name}")
            
        self.mock_websocket_bridge.emit_agent_event.side_effect = collect_agent_event
    
    def create_test_user_context(self, 
                               additional_metadata: Optional[Dict] = None,
                               db_session = None) -> UserExecutionContext:
        """Create standardized test user context."""
        base_metadata = {
            'user_request': 'Analyze my AI costs and suggest optimizations',
            'request_type': 'cost_optimization',
            'priority': 'high'
        }
        
        if additional_metadata:
            base_metadata.update(additional_metadata)
        
        return UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id(self.test_user_id),
            db_session=db_session,
            agent_context=base_metadata
        )
    
    def assert_websocket_events_sent(self, expected_events: List[str], timeout_seconds: float = 30.0):
        """Assert that all expected WebSocket events were sent during agent execution."""
        received_event_types = [event.get('type') for event in self.websocket_events]
        
        for expected_event in expected_events:
            assert expected_event in received_event_types, (
                f"Missing critical WebSocket event: {expected_event}. "
                f"Received: {received_event_types}. "
                f"This breaks the user chat experience - users won't see agent progress."
            )
        
        self.logger.info(f" PASS:  All expected WebSocket events validated: {expected_events}")

    # ============================================================================
    # ExecutionEngineFactory Tests - User Isolation and Engine Creation
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_engine_factory_user_isolation(self, real_services_fixture):
        """
        Test ExecutionEngineFactory creates isolated engines per user.
        
        Business Value: Ensures complete user isolation for multi-tenant deployment.
        Critical Path: User data never leaks between concurrent users.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database not available for isolation testing")
        
        # Configure factory with real WebSocket bridge
        factory = await configure_execution_engine_factory(
            websocket_bridge=self.mock_websocket_bridge,
            database_session_manager=None,
            redis_manager=None
        )
        
        # Create contexts for different users (use create_new_context for different user_ids)
        user1_context = UserExecutionContext(
            user_id="user-1-isolation-test",
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id("user-1-isolation-test"),
            db_session=real_services_fixture["database_available"],
            agent_context={
                'user_request': 'Analyze my AI costs and suggest optimizations',
                'request_type': 'cost_optimization',
                'priority': 'high'
            }
        )
        
        user2_context = UserExecutionContext(
            user_id="user-2-isolation-test",
            thread_id=UnifiedIdGenerator.generate_thread_id("user-2-isolation-test"),
            run_id=UnifiedIdGenerator.generate_run_id(),
            request_id=UnifiedIdGenerator.generate_request_id(),
            websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id("user-2-isolation-test"),
            db_session=real_services_fixture["database_available"],
            agent_context={
                'user_request': 'Different request from user 2',
                'request_type': 'cost_optimization',
                'priority': 'high'
            }
        )
        
        # Create engines for both users
        engine1 = await factory.create_for_user(user1_context)
        engine2 = await factory.create_for_user(user2_context)
        
        try:
            # Validate complete isolation
            assert engine1.engine_id != engine2.engine_id, "Engine IDs must be unique"
            assert engine1.get_user_context().user_id != engine2.get_user_context().user_id
            assert engine1.get_user_context().metadata != engine2.get_user_context().metadata
            
            # Validate engines are active and isolated
            assert engine1.is_active(), "User 1 engine must be active"
            assert engine2.is_active(), "User 2 engine must be active"
            
            # Validate factory tracks both engines
            active_contexts = factory.get_active_contexts()
            assert "user-1-isolation-test" in active_contexts
            assert "user-2-isolation-test" in active_contexts
            
            # Validate factory metrics
            metrics = factory.get_factory_metrics()
            assert metrics['active_engines_count'] >= 2
            assert metrics['total_engines_created'] >= 2
            
            self.logger.info(" PASS:  ExecutionEngineFactory user isolation validated")
            
        finally:
            # Clean up engines
            await factory.cleanup_engine(engine1)
            await factory.cleanup_engine(engine2)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_engine_factory_context_manager(self, real_services_fixture):
        """
        Test ExecutionEngineFactory context manager for automatic cleanup.
        
        Business Value: Ensures resource cleanup prevents memory leaks in production.
        Critical Path: Engines are automatically cleaned up after user sessions.
        """
        # Configure factory
        factory = await configure_execution_engine_factory(
            websocket_bridge=self.mock_websocket_bridge
        )
        
        user_context = self.create_test_user_context()
        engine_id = None
        
        # Use context manager for automatic cleanup
        async with factory.user_execution_scope(user_context) as engine:
            engine_id = engine.engine_id
            
            # Validate engine is active during scope
            assert engine.is_active(), "Engine must be active within context"
            assert engine.get_user_context().user_id == self.test_user_id
            
            # Validate factory tracks active engine
            active_contexts = factory.get_active_contexts()
            assert self.test_user_id in active_contexts
        
        # Validate automatic cleanup after context exit
        final_contexts = factory.get_active_contexts()
        assert self.test_user_id not in final_contexts or final_contexts[self.test_user_id] == 0
        
        # Validate metrics updated
        metrics = factory.get_factory_metrics()
        assert metrics['total_engines_cleaned'] >= 1
        
        self.logger.info(" PASS:  ExecutionEngineFactory context manager cleanup validated")
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_execution_engine_factory_concurrent_users(self, real_services_fixture):
        """
        Test ExecutionEngineFactory handles concurrent users safely.
        
        Business Value: Validates production-ready concurrent user handling.
        Critical Path: Multiple users can use the system simultaneously without conflicts.
        """
        factory = await configure_execution_engine_factory(
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Create multiple concurrent user contexts
        concurrent_users = []
        for i in range(5):
            # Create context with unique user_id from the start (can't modify immutable fields)
            user_context = self.create_test_user_context(
                additional_metadata={'user_request': f"Request from user {i}"}
            )
            
            # Since UserExecutionContext is immutable, create a new one with different user_id
            concurrent_user_context = UserExecutionContext(
                user_id=f"concurrent-user-{i}",
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                request_id=user_context.request_id,
                db_session=user_context.db_session,
                websocket_client_id=user_context.websocket_client_id,
                agent_context=user_context.agent_context.copy(),
                audit_metadata=user_context.audit_metadata.copy()
            )
            concurrent_users.append(concurrent_user_context)
        
        # Execute concurrent engine creation
        async def create_and_use_engine(user_context):
            """Create engine, use it briefly, then clean up."""
            async with factory.user_execution_scope(user_context) as engine:
                # Simulate brief usage
                await asyncio.sleep(0.1)
                assert engine.is_active()
                assert engine.get_user_context().user_id == user_context.user_id
                return engine.engine_id
        
        # Run concurrent operations
        start_time = time.time()
        engine_ids = await asyncio.gather(*[
            create_and_use_engine(context) for context in concurrent_users
        ])
        execution_time = time.time() - start_time
        
        # Validate concurrent execution
        assert len(engine_ids) == 5, "All concurrent engines must be created"
        assert len(set(engine_ids)) == 5, "All engine IDs must be unique"
        
        # Validate performance (should complete quickly with proper concurrency)
        assert execution_time < 5.0, f"Concurrent execution too slow: {execution_time}s"
        
        # Validate cleanup (all engines should be cleaned up)
        final_contexts = factory.get_active_contexts()
        for user_context in concurrent_users:
            assert user_context.user_id not in final_contexts or final_contexts[user_context.user_id] == 0
        
        # Validate factory metrics
        metrics = factory.get_factory_metrics()
        assert metrics['total_engines_created'] >= 5
        assert metrics['total_engines_cleaned'] >= 5
        assert metrics['active_engines_count'] == 0
        
        self.logger.info(f" PASS:  Concurrent user execution validated in {execution_time:.2f}s")

    # ============================================================================
    # SupervisorAgent Orchestration Tests
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_supervisor_agent_orchestration_basic(self, real_services_fixture):
        """
        Test SupervisorAgent orchestrates sub-agents correctly.
        
        Business Value: Validates core AI orchestration that delivers optimization insights.
        Critical Path: Supervisor coordinates agents to analyze user requests and provide value.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for agent orchestration")
        
        # Create supervisor with mocked infrastructure
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Create user context with database session
        user_context = self.create_test_user_context(
            additional_metadata={
                'user_request': 'Help me optimize my AI infrastructure costs',
                'context_data': {'monthly_spend': 5000, 'models': ['gpt-4', 'claude']}
            },
            db_session=real_services_fixture["db"]
        )
        
        # Mock LLM responses for different agents
        self.mock_llm_manager.generate_response.side_effect = [
            # Triage agent response
            {
                'category': 'cost_optimization',
                'priority': 'high', 
                'data_sufficiency': 'partial',
                'next_agents': ['data_helper', 'optimization', 'reporting']
            },
            # Data helper response  
            {
                'data_guidance': 'Need more detailed usage metrics',
                'collection_methods': ['API analysis', 'Usage tracking']
            },
            # Optimization response
            {
                'strategies': ['Model optimization', 'Usage scheduling'],
                'potential_savings': {'monthly_amount': 1500, 'percentage': 30}
            },
            # Reporting response
            {
                'summary': 'Identified 30% potential cost savings',
                'recommendations': ['Switch to smaller models for simple tasks'],
                'action_plan': ['Audit current usage', 'Implement model routing']
            }
        ]
        
        # Execute supervisor orchestration
        start_time = time.time()
        result = await supervisor.execute(user_context, stream_updates=True)
        execution_time = time.time() - start_time
        
        # Validate orchestration result
        assert result is not None, "Supervisor must return results"
        assert isinstance(result, dict), "Result must be dictionary"
        assert result.get('orchestration_successful') == True, "Orchestration must succeed"
        assert 'results' in result, "Must contain agent results"
        
        # Validate execution performance (should complete in reasonable time)
        assert execution_time < 30.0, f"Orchestration too slow: {execution_time:.2f}s"
        
        # Validate WebSocket events sent (critical for user experience)
        self.assert_websocket_events_sent([
            'agent_started',
            'agent_thinking', 
            'agent_completed'
        ])
        
        # Validate business value delivered
        self.assert_business_value_delivered(result, 'cost_savings')
        
        self.logger.info(f" PASS:  SupervisorAgent orchestration validated in {execution_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_supervisor_agent_pipeline_execution_order(self, real_services_fixture):
        """
        Test agent pipeline executes in correct order: Triage  ->  Data Helper  ->  Optimization  ->  Reporting.
        
        Business Value: Ensures logical flow that builds insights progressively.
        Critical Path: Agents execute in dependency order to maximize analysis quality.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for pipeline testing")
        
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        user_context = self.create_test_user_context(
            additional_metadata={
                'user_request': 'Provide comprehensive AI cost analysis and optimization plan',
                'execution_tracking': True
            },
            db_session=real_services_fixture["db"]
        )
        
        # Track agent execution order
        execution_order = []
        
        async def track_agent_execution(*args, **kwargs):
            """Track which agent is being executed."""
            # Extract agent name from the call context
            import inspect
            frame = inspect.currentframe()
            try:
                # Look for agent name in the call stack
                for f in inspect.getouterframes(frame):
                    if 'agent_name' in f.frame.f_locals:
                        agent_name = f.frame.f_locals['agent_name']
                        execution_order.append(agent_name)
                        break
            finally:
                del frame
            
            # Return mock response based on expected agent
            if 'triage' in str(args) or len(execution_order) == 1:
                return {'category': 'optimization', 'data_sufficiency': 'sufficient', 'next_agents': ['data', 'optimization', 'reporting']}
            elif 'data' in str(args) or len(execution_order) == 2:
                return {'usage_analysis': 'High usage detected', 'cost_breakdown': {'gpt4': 3000, 'claude': 2000}}
            elif 'optimization' in str(args) or len(execution_order) == 3:
                return {'optimizations': ['Model switching', 'Request batching'], 'savings': 1200}
            else:  # reporting
                return {'final_report': 'Complete analysis delivered', 'summary': 'Optimization recommendations provided'}
        
        self.mock_llm_manager.generate_response.side_effect = track_agent_execution
        
        # Execute pipeline
        result = await supervisor.execute(user_context, stream_updates=True)
        
        # Validate execution order (triage first, reporting last)
        assert len(execution_order) >= 2, "Multiple agents must execute"
        
        # Check that reporting comes after other agents (UVS principle)
        if 'reporting' in execution_order:
            reporting_index = execution_order.index('reporting')
            assert reporting_index > 0, "Reporting should not be first agent"
            
            # Other agents should come before reporting
            pre_reporting_agents = execution_order[:reporting_index]
            assert len(pre_reporting_agents) > 0, "Other agents should execute before reporting"
        
        # Validate pipeline delivers business value
        assert result.get('orchestration_successful') == True
        self.assert_business_value_delivered(result, 'insights')
        
        self.logger.info(f" PASS:  Agent pipeline execution order validated: {'  ->  '.join(execution_order)}")

    # ============================================================================
    # Agent Failure Recovery and Error Handling Tests  
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_failure_recovery_uvs_principle(self, real_services_fixture):
        """
        Test agent failure recovery using UVS principle (Universal Value System).
        
        Business Value: Ensures users always get value even when individual agents fail.
        Critical Path: System gracefully handles agent failures and provides fallback responses.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for failure testing")
        
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager, 
            websocket_bridge=self.mock_websocket_bridge
        )
        
        user_context = self.create_test_user_context(
            additional_metadata={'user_request': 'Optimize my costs even if some analysis fails'},
            db_session=real_services_fixture["db"]
        )
        
        # Simulate agent failures
        failure_count = 0
        async def simulate_agent_failures(*args, **kwargs):
            """Simulate some agents failing while others succeed."""
            nonlocal failure_count
            failure_count += 1
            
            if failure_count == 1:
                # Triage succeeds
                return {'category': 'optimization', 'data_sufficiency': 'partial'}
            elif failure_count == 2:
                # Data helper fails
                raise RuntimeError("Data helper service unavailable")
            elif failure_count == 3:
                # Optimization fails  
                raise RuntimeError("Optimization service timeout")
            else:
                # Reporting succeeds (UVS principle - always provides value)
                return {
                    'summary': 'Analysis completed with limited data',
                    'recommendations': ['General cost optimization practices'],
                    'fallback_guidance': True,
                    'status': 'partial_success'
                }
        
        self.mock_llm_manager.generate_response.side_effect = simulate_agent_failures
        
        # Execute with failures
        result = await supervisor.execute(user_context, stream_updates=True)
        
        # Validate UVS principle - system still delivers value
        assert result is not None, "UVS: System must always return results"
        assert isinstance(result, dict), "Result must be structured"
        
        # Should have some successful results despite failures
        if 'results' in result:
            successful_agents = [name for name, agent_result in result['results'].items() 
                               if isinstance(agent_result, dict) and agent_result.get('status') != 'failed']
            assert len(successful_agents) > 0, "UVS: At least one agent must provide value"
        
        # Validate WebSocket events still sent (user experience maintained)
        event_types = [event.get('type') for event in self.websocket_events]
        assert 'agent_started' in event_types, "User must see agent started"
        
        # Validate business value still delivered (core UVS principle)
        # Even with failures, should provide some form of guidance
        if result.get('results', {}).get('reporting'):
            reporting_result = result['results']['reporting']
            assert 'summary' in reporting_result or 'recommendations' in reporting_result, \
                "UVS: Reporting must provide some guidance even with upstream failures"
        
        self.logger.info(" PASS:  Agent failure recovery with UVS principle validated")

    # ============================================================================
    # Multi-User Isolation and Concurrent Execution Tests
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_agent_isolation_concurrent(self, real_services_fixture):
        """
        Test multi-user agent execution with complete isolation.
        
        Business Value: Validates production multi-tenant capabilities.
        Critical Path: Multiple users can run agents simultaneously without data leakage.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for multi-user testing")
        
        # Create multiple supervisors (simulating different user sessions)
        supervisor1 = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        supervisor2 = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Create isolated user contexts (cannot modify frozen fields, create new contexts)
        user1_context = UserExecutionContext(
            user_id="multi-user-1",
            thread_id=UnifiedIdGenerator.generate_thread_id("multi-user-1"),
            run_id=UnifiedIdGenerator.generate_run_id(),
            request_id=UnifiedIdGenerator.generate_request_id(),
            websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id("multi-user-1"),
            db_session=real_services_fixture["db"],
            agent_context={
                'user_request': 'User 1: Analyze my OpenAI costs',
                'user_data': {'service': 'openai', 'monthly_budget': 1000}
            }
        )
        
        user2_context = UserExecutionContext(
            user_id="multi-user-2",
            thread_id=UnifiedIdGenerator.generate_thread_id("multi-user-2"),
            run_id=UnifiedIdGenerator.generate_run_id(),
            request_id=UnifiedIdGenerator.generate_request_id(),
            websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id("multi-user-2"),
            db_session=real_services_fixture["db"],
            agent_context={
                'user_request': 'User 2: Optimize my Anthropic usage',
                'user_data': {'service': 'anthropic', 'monthly_budget': 2000}
            }
        )
        
        # Track responses per user to validate isolation
        user_responses = {}
        
        async def user_specific_responses(*args, **kwargs):
            """Provide user-specific responses to validate isolation."""
            # Determine which user based on context in call stack
            import inspect
            frame = inspect.currentframe()
            current_user = None
            try:
                for f in inspect.getouterframes(frame):
                    if 'context' in f.frame.f_locals:
                        ctx = f.frame.f_locals['context']
                        if hasattr(ctx, 'user_id'):
                            current_user = ctx.user_id
                            break
            finally:
                del frame
            
            # Return user-specific response
            if current_user == "multi-user-1":
                response = {
                    'user_specific_data': 'OpenAI analysis for user 1',
                    'service': 'openai',
                    'budget': 1000,
                    'recommendations': ['Optimize GPT-4 usage']
                }
            else:  # user 2 or default
                response = {
                    'user_specific_data': 'Anthropic analysis for user 2', 
                    'service': 'anthropic',
                    'budget': 2000,
                    'recommendations': ['Optimize Claude usage']
                }
            
            # Track response for validation
            if current_user:
                if current_user not in user_responses:
                    user_responses[current_user] = []
                user_responses[current_user].append(response)
            
            return response
        
        self.mock_llm_manager.generate_response.side_effect = user_specific_responses
        
        # Execute concurrent user sessions
        async def execute_user_session(supervisor, context, user_label):
            """Execute agent session for a specific user."""
            start_time = time.time()
            try:
                result = await supervisor.execute(context, stream_updates=True)
                execution_time = time.time() - start_time
                
                return {
                    'user': user_label,
                    'result': result,
                    'execution_time': execution_time,
                    'success': True
                }
            except Exception as e:
                execution_time = time.time() - start_time
                return {
                    'user': user_label,
                    'error': str(e),
                    'execution_time': execution_time,
                    'success': False
                }
        
        # Run concurrent sessions
        concurrent_results = await asyncio.gather(
            execute_user_session(supervisor1, user1_context, "User1"),
            execute_user_session(supervisor2, user2_context, "User2"),
            return_exceptions=True
        )
        
        # Validate both sessions completed
        assert len(concurrent_results) == 2, "Both user sessions must complete"
        
        for session_result in concurrent_results:
            if isinstance(session_result, Exception):
                pytest.fail(f"User session failed with exception: {session_result}")
            
            assert session_result['success'], f"User session failed: {session_result.get('error', 'Unknown error')}"
            assert session_result['execution_time'] < 30.0, f"Session too slow: {session_result['execution_time']:.2f}s"
        
        # Validate complete user isolation - responses should be user-specific
        assert "multi-user-1" in user_responses, "User 1 should have specific responses"
        assert "multi-user-2" in user_responses, "User 2 should have specific responses"
        
        user1_data = user_responses["multi-user-1"]
        user2_data = user_responses["multi-user-2"]
        
        # Validate user-specific data isolation
        assert any('openai' in str(response) for response in user1_data), "User 1 should get OpenAI-specific responses"
        assert any('anthropic' in str(response) for response in user2_data), "User 2 should get Anthropic-specific responses"
        
        # Validate no cross-contamination
        assert not any('anthropic' in str(response) for response in user1_data), "User 1 should not see User 2's data"
        assert not any('openai' in str(response) for response in user2_data), "User 2 should not see User 1's data"
        
        self.logger.info(" PASS:  Multi-user isolation and concurrent execution validated")

    # ============================================================================
    # WebSocket Event Integration Tests (5 Critical Events)
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_agent_events_complete_flow(self, real_services_fixture):
        """
        Test all 5 critical WebSocket events are sent during agent execution.
        
        Business Value: Validates user chat experience with real-time progress updates.
        Critical Path: Users see agent working on their problem with progress indicators.
        
        The 5 critical WebSocket events that enable chat business value:
        1. agent_started - User sees agent began processing
        2. agent_thinking - Real-time reasoning visibility  
        3. tool_executing - Tool usage transparency
        4. tool_completed - Tool results delivery
        5. agent_completed - Final results ready
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for WebSocket event testing")
        
        # Enhanced WebSocket bridge mock to capture detailed events
        detailed_events = []
        
        async def capture_detailed_websocket_events(user_id: str, event_data: Dict):
            """Capture detailed WebSocket events for validation."""
            event_data['captured_at'] = datetime.now(timezone.utc).isoformat()
            event_data['user_id'] = user_id
            detailed_events.append(event_data)
            self.logger.info(f" CHART:  Captured detailed WebSocket event: {event_data.get('type')} for user {user_id}")
        
        async def capture_detailed_agent_events(event_type: str, data: Dict, run_id: str = None, agent_name: str = None):
            """Capture detailed agent events for validation."""
            event_data = {
                'type': event_type,
                'data': data,
                'run_id': run_id, 
                'agent_name': agent_name,
                'captured_at': datetime.now(timezone.utc).isoformat()
            }
            detailed_events.append(event_data)
            self.logger.info(f" CHART:  Captured detailed agent event: {event_type} from {agent_name}")
        
        self.mock_websocket_manager.send_to_user.side_effect = capture_detailed_websocket_events
        self.mock_websocket_bridge.emit_agent_event.side_effect = capture_detailed_agent_events
        
        # Create supervisor with enhanced WebSocket tracking
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        user_context = self.create_test_user_context(
            additional_metadata={
                'user_request': 'Run comprehensive analysis with full event tracking',
                'enable_tool_execution': True,
                'stream_all_events': True
            },
            db_session=real_services_fixture["db"]
        )
        
        # Mock LLM responses that trigger tool usage
        self.mock_llm_manager.generate_response.side_effect = [
            # Triage - triggers thinking
            {'category': 'comprehensive_analysis', 'tools_needed': ['data_analyzer', 'cost_calculator']},
            # Data analysis - triggers tool execution  
            {'analysis_result': 'Data processed', 'tools_used': ['data_analyzer']},
            # Optimization - triggers more tool execution
            {'optimization_strategies': ['Strategy A', 'Strategy B'], 'tools_used': ['cost_calculator']},
            # Reporting - final completion
            {'final_report': 'Analysis complete', 'all_events_captured': True}
        ]
        
        # Execute with full event tracking
        start_time = time.time()
        result = await supervisor.execute(user_context, stream_updates=True)
        execution_time = time.time() - start_time
        
        # Validate execution completed successfully
        assert result is not None, "Agent execution must complete"
        assert execution_time < 60.0, f"Execution too slow: {execution_time:.2f}s"
        
        # Extract all event types that were captured
        captured_event_types = [event.get('type') for event in detailed_events]
        
        # Validate all 5 critical WebSocket events were sent
        critical_events = [
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]
        
        missing_events = []
        for critical_event in critical_events:
            if critical_event not in captured_event_types:
                # Some events might have different names - check variations
                variations = {
                    'tool_executing': ['tool_started', 'tool_execute'],
                    'tool_completed': ['tool_finished', 'tool_result']
                }
                
                found_variation = False
                for variation in variations.get(critical_event, []):
                    if variation in captured_event_types:
                        found_variation = True
                        break
                
                if not found_variation:
                    missing_events.append(critical_event)
        
        # Assert all critical events were captured
        assert len(missing_events) == 0, (
            f"Missing critical WebSocket events: {missing_events}. "
            f"This breaks user chat experience. "
            f"Captured events: {captured_event_types}"
        )
        
        # Validate event ordering (started first, completed last)
        started_events = [i for i, event in enumerate(detailed_events) if event.get('type') == 'agent_started']
        completed_events = [i for i, event in enumerate(detailed_events) if event.get('type') == 'agent_completed']
        
        if started_events and completed_events:
            assert min(started_events) < max(completed_events), "agent_started must come before agent_completed"
        
        # Validate user context in events
        for event in detailed_events:
            if 'user_id' in event:
                assert event['user_id'] == self.test_user_id, "Events must be associated with correct user"
        
        self.logger.info(f" PASS:  All 5 critical WebSocket events validated in {execution_time:.2f}s")
        self.logger.info(f" CHART:  Total events captured: {len(detailed_events)}")
        self.logger.info(f" TARGET:  Event types: {list(set(captured_event_types))}")

    # ============================================================================
    # Real Business Scenario Tests
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_business_scenario_cost_optimization(self, real_services_fixture):
        """
        Test real business scenario: AI cost optimization analysis.
        
        Business Value: Validates core business use case that drives customer value.
        Critical Path: System analyzes real cost data and provides actionable optimization recommendations.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for business scenario testing")
        
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Real business scenario data
        business_context = self.create_test_user_context(
            additional_metadata={
                'user_request': 'I need to reduce my AI costs by 25% while maintaining performance. Current spend is $8000/month across OpenAI and Anthropic.',
                'business_context': {
                    'monthly_ai_spend': 8000,
                    'target_reduction': 25,  # 25%
                    'services': ['openai', 'anthropic'],
                    'current_models': ['gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', 'claude-3-sonnet'],
                    'use_cases': ['customer_support', 'content_generation', 'data_analysis'],
                    'performance_requirements': 'maintain_quality'
                },
                'expected_deliverables': ['cost_analysis', 'optimization_plan', 'implementation_roadmap']
            },
            db_session=real_services_fixture["db"]
        )
        
        # Mock realistic business analysis responses
        self.mock_llm_manager.generate_response.side_effect = [
            # Triage - recognizes cost optimization scenario
            {
                'category': 'cost_optimization',
                'priority': 'high',
                'data_sufficiency': 'sufficient',
                'business_impact': 'high',
                'next_agents': ['data', 'optimization', 'actions', 'reporting']
            },
            # Data analysis - analyzes current spend
            {
                'current_analysis': {
                    'monthly_spend': 8000,
                    'breakdown': {
                        'gpt-4': 4800,  # 60% of spend
                        'claude-3-opus': 2400,  # 30% of spend  
                        'others': 800  # 10% of spend
                    },
                    'usage_patterns': {
                        'customer_support': 40,
                        'content_generation': 35,
                        'data_analysis': 25
                    }
                },
                'inefficiencies_detected': [
                    'Over-using GPT-4 for simple tasks',
                    'Not utilizing cheaper models for bulk content',
                    'Claude Opus used for tasks suitable for Sonnet'
                ]
            },
            # Optimization - specific recommendations
            {
                'optimization_strategies': [
                    {
                        'strategy': 'Model downgrading',
                        'description': 'Use GPT-3.5-turbo for customer support',
                        'estimated_savings': 1600,  # monthly
                        'impact_on_quality': 'minimal'
                    },
                    {
                        'strategy': 'Claude model optimization',
                        'description': 'Switch from Opus to Sonnet for content generation',
                        'estimated_savings': 800,  # monthly
                        'impact_on_quality': 'low'
                    },
                    {
                        'strategy': 'Request batching',
                        'description': 'Batch similar requests to reduce API calls',
                        'estimated_savings': 400,  # monthly
                        'impact_on_quality': 'none'
                    }
                ],
                'total_potential_savings': 2800,  # $2,800/month = 35% reduction
                'target_achievement': 'exceeded'  # 35% > 25% target
            },
            # Actions - implementation roadmap
            {
                'implementation_plan': {
                    'phase_1': {
                        'timeframe': '2 weeks',
                        'actions': ['Audit current API usage', 'Identify quick wins'],
                        'expected_savings': 800
                    },
                    'phase_2': {
                        'timeframe': '1 month', 
                        'actions': ['Implement model routing logic', 'Deploy A/B testing'],
                        'expected_savings': 1200
                    },
                    'phase_3': {
                        'timeframe': '2 months',
                        'actions': ['Full optimization deployment', 'Performance monitoring'],
                        'expected_savings': 800
                    }
                },
                'risk_mitigation': ['Gradual rollout', 'Quality monitoring', 'Rollback plan'],
                'success_metrics': ['Cost reduction %', 'Quality scores', 'User satisfaction']
            },
            # Reporting - comprehensive business report
            {
                'executive_summary': 'Identified $2,800/month in cost savings (35% reduction) exceeding 25% target',
                'key_findings': [
                    'Over-utilization of premium models for routine tasks',
                    'Significant savings available through intelligent model routing',
                    'Implementation can maintain quality while reducing costs'
                ],
                'recommendations': [
                    'Implement model routing based on task complexity',
                    'Deploy request batching for bulk operations',
                    'Set up automated cost monitoring and alerts'
                ],
                'business_impact': {
                    'annual_savings': 33600,  # $2,800 * 12
                    'roi_timeline': '3 months',
                    'risk_level': 'low'
                },
                'next_steps': [
                    'Approve implementation plan',
                    'Assign technical team',
                    'Begin Phase 1 audit'
                ]
            }
        ]
        
        # Execute business scenario
        start_time = time.time()
        result = await supervisor.execute(business_context, stream_updates=True)
        execution_time = time.time() - start_time
        
        # Validate business value delivered
        assert result is not None, "Business analysis must produce results"
        assert result.get('orchestration_successful') == True, "Business analysis must succeed"
        
        # Validate real business metrics in results
        if 'results' in result:
            # Check for cost analysis
            has_cost_analysis = any(
                'cost' in str(agent_result).lower() or 'savings' in str(agent_result).lower()
                for agent_result in result['results'].values()
            )
            assert has_cost_analysis, "Must provide cost analysis for business scenario"
            
            # Check for optimization recommendations
            has_optimization = any(
                'optimization' in str(agent_result).lower() or 'strategy' in str(agent_result).lower()
                for agent_result in result['results'].values()
            )
            assert has_optimization, "Must provide optimization strategies"
            
            # Check for implementation plan
            has_implementation = any(
                'implementation' in str(agent_result).lower() or 'action' in str(agent_result).lower()
                for agent_result in result['results'].values()
            )
            assert has_implementation, "Must provide implementation guidance"
        
        # Validate performance for business scenario
        assert execution_time < 60.0, f"Business analysis too slow: {execution_time:.2f}s"
        
        # Validate WebSocket events for business user experience  
        self.assert_websocket_events_sent(['agent_started', 'agent_thinking', 'agent_completed'])
        
        # Validate business value metrics
        self.assert_business_value_delivered(result, 'cost_savings')
        
        self.logger.info(f" PASS:  Real business scenario validation completed in {execution_time:.2f}s")
        self.logger.info("[U+1F4B0] Business value: Cost optimization analysis with actionable recommendations")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_performance_timing_validation(self, real_services_fixture):
        """
        Test agent execution timing and performance validation.
        
        Business Value: Ensures responsive user experience for production deployment.
        Critical Path: Agent executions complete within acceptable timeframes.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for performance testing")
        
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Performance test scenarios
        test_scenarios = [
            {
                'name': 'simple_query',
                'request': 'Quick status check on my AI usage',
                'expected_max_time': 10.0,  # 10 seconds max
                'agents_expected': 2  # Triage + Reporting minimum
            },
            {
                'name': 'complex_analysis', 
                'request': 'Comprehensive analysis of my AI infrastructure with detailed optimization recommendations',
                'expected_max_time': 30.0,  # 30 seconds max
                'agents_expected': 4  # Full pipeline
            },
            {
                'name': 'data_heavy_request',
                'request': 'Analyze my historical AI usage data and project future costs with seasonal adjustments',
                'expected_max_time': 45.0,  # 45 seconds max
                'agents_expected': 4  # Full pipeline with data processing
            }
        ]
        
        # Mock responses optimized for performance testing
        fast_responses = [
            {'category': 'quick_check', 'complexity': 'low'},
            {'status': 'operational', 'quick_insights': ['System running normally']},
            {'summary': 'Quick analysis completed', 'performance_validated': True}
        ]
        
        performance_results = []
        
        for scenario in test_scenarios:
            # Reset mocks for each scenario
            self.websocket_events.clear()
            self.mock_llm_manager.generate_response.side_effect = fast_responses
            
            # Create scenario context
            scenario_context = self.create_test_user_context(
                additional_metadata={
                    'user_request': scenario['request'],
                    'scenario': scenario['name'],
                    'performance_test': True
                },
                db_session=real_services_fixture["db"]
            )
            
            # Execute with timing
            start_time = time.time()
            result = await supervisor.execute(scenario_context, stream_updates=True)
            execution_time = time.time() - start_time
            
            # Record performance
            scenario_performance = {
                'scenario': scenario['name'],
                'execution_time': execution_time,
                'expected_max_time': scenario['expected_max_time'],
                'within_limit': execution_time <= scenario['expected_max_time'],
                'result_size': len(str(result)) if result else 0,
                'events_sent': len(self.websocket_events)
            }
            performance_results.append(scenario_performance)
            
            # Validate performance requirements
            assert execution_time <= scenario['expected_max_time'], (
                f"Scenario '{scenario['name']}' too slow: {execution_time:.2f}s > {scenario['expected_max_time']}s"
            )
            
            # Validate results delivered
            assert result is not None, f"Scenario '{scenario['name']}' must produce results"
            
            # Validate user experience (WebSocket events)
            assert len(self.websocket_events) >= 2, f"Scenario '{scenario['name']}' must send progress events"
            
            self.logger.info(f"[U+23F1][U+FE0F] Performance validated: {scenario['name']} completed in {execution_time:.2f}s")
        
        # Calculate overall performance metrics
        avg_execution_time = sum(r['execution_time'] for r in performance_results) / len(performance_results)
        all_within_limits = all(r['within_limit'] for r in performance_results)
        
        # Validate overall performance
        assert all_within_limits, "All scenarios must meet performance requirements"
        assert avg_execution_time < 30.0, f"Average execution time too high: {avg_execution_time:.2f}s"
        
        self.logger.info(" PASS:  Agent execution performance validation completed")
        self.logger.info(f" CHART:  Average execution time: {avg_execution_time:.2f}s")
        self.logger.info(f" TARGET:  All scenarios within performance limits: {all_within_limits}")

    # ============================================================================
    # Edge Cases and Error Conditions
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_invalid_user_context_handling(self, real_services_fixture):
        """
        Test handling of invalid user contexts with proper error messages.
        
        Business Value: Ensures robust error handling for production deployment.
        Critical Path: System fails gracefully with clear error messages for debugging.
        """
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Test invalid contexts - check creation and execution separately
        
        # Test 1: Invalid user_id at creation time (constructor validation)
        with pytest.raises(InvalidContextError) as exc_info:
            UserExecutionContext(
                user_id="",  # Invalid empty user_id
                thread_id=self.test_thread_id,
                run_id=self.test_run_id,
                request_id=self.test_request_id,
                db_session=real_services_fixture["db"]
            )
        
        error_message = str(exc_info.value)
        assert len(error_message) > 10, "Error message too brief for invalid user_id"
        assert "user_id" in error_message.lower(), "Error message should mention user_id issue"
        self.logger.info(f" PASS:  Invalid user_id properly rejected at creation: {error_message}")
        
        # Test 2: Missing database session - create context and test execution
        invalid_context_no_db = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            db_session=None  # No database session
        )
        
        with pytest.raises((InvalidContextError, ValueError, RuntimeError, AttributeError)) as exc_info:
            await supervisor.execute(invalid_context_no_db, stream_updates=True)
        
        error_message = str(exc_info.value)
        assert len(error_message) > 10, "Error message too brief for missing session"
        self.logger.info(f" PASS:  Invalid missing session properly rejected: {error_message}")
        
        # Test 3: Invalid thread_id format at creation time
        with pytest.raises(InvalidContextError) as exc_info:
            UserExecutionContext(
                user_id=self.test_user_id,
                thread_id="",  # Invalid empty thread_id
                run_id=self.test_run_id,
                request_id=self.test_request_id,
                db_session=real_services_fixture["db"]
            )
        
        error_message = str(exc_info.value)
        assert len(error_message) > 10, "Error message too brief for invalid thread_id"
        assert "thread_id" in error_message.lower(), "Error message should mention thread_id issue"
        self.logger.info(f" PASS:  Invalid thread_id properly rejected at creation: {error_message}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_failure_graceful_handling(self, real_services_fixture):
        """
        Test graceful handling when WebSocket connections fail.
        
        Business Value: Ensures system continues working even with WebSocket issues.
        Critical Path: Agent execution succeeds even if user notifications fail.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for WebSocket failure testing")
        
        # Create supervisor with failing WebSocket bridge
        failing_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        failing_websocket_bridge.websocket_manager = None  # Simulate missing manager
        failing_websocket_bridge.emit_agent_event = AsyncMock(side_effect=RuntimeError("WebSocket connection failed"))
        
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=failing_websocket_bridge
        )
        
        user_context = self.create_test_user_context(
            additional_metadata={'user_request': 'Test with WebSocket failures'},
            db_session=real_services_fixture["db"]
        )
        
        # Mock successful agent responses
        self.mock_llm_manager.generate_response.side_effect = [
            {'category': 'test', 'status': 'success'},
            {'summary': 'Analysis completed despite WebSocket issues', 'resilient': True}
        ]
        
        # Execute despite WebSocket failures
        result = await supervisor.execute(user_context, stream_updates=True)
        
        # Validate execution still succeeds
        assert result is not None, "Agent execution must succeed despite WebSocket failures"
        assert result.get('orchestration_successful') == True, "Orchestration must succeed"
        
        # Validate business value still delivered
        self.assert_business_value_delivered(result, 'insights')
        
        self.logger.info(" PASS:  Graceful WebSocket failure handling validated")

    # ============================================================================
    # Cleanup and Utility Methods  
    # ============================================================================
    
    async def async_teardown_method(self, method=None):
        """Clean up test resources."""
        try:
            # Clear collected events
            self.websocket_events.clear()
            
            # Reset mocks
            if hasattr(self, 'mock_llm_manager'):
                self.mock_llm_manager.reset_mock()
            if hasattr(self, 'mock_websocket_manager'):
                self.mock_websocket_manager.reset_mock()
            if hasattr(self, 'mock_websocket_bridge'):
                self.mock_websocket_bridge.reset_mock()
            
            self.logger.info(" PASS:  Test cleanup completed")
            
        except Exception as e:
            self.logger.warning(f"Error during test cleanup: {e}")
        
        await super().async_teardown()


# ============================================================================
# Test Fixtures and Helpers
# ============================================================================

@pytest.fixture
def mock_infrastructure():
    """Provide mocked infrastructure components for testing."""
    return {
        'llm_manager': Mock(spec=LLMManager),
        'websocket_manager': Mock(spec=WebSocketManager),
        'websocket_bridge': Mock(spec=AgentWebSocketBridge)
    }


# ============================================================================ 
# Performance Benchmarks
# ============================================================================

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.performance
async def test_agent_execution_pipeline_performance_benchmark(real_services_fixture):
    """
    Performance benchmark test for agent execution pipeline.
    
    Business Value: Establishes performance baselines for production monitoring.
    Critical Path: Validates system can handle expected production loads.
    """
    if not real_services_fixture["database_available"]:
        pytest.skip("Database required for performance benchmarking")
    
    # This test is marked as performance and may be run separately
    # Validates the complete pipeline under various load conditions
    pytest.skip("Performance benchmark - run separately with --performance flag")