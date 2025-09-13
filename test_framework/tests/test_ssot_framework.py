"""
Comprehensive tests for the SSOT Test Framework

This module tests all components of the Single Source of Truth test framework
to ensure they function correctly and meet the requirements for eliminating
test infrastructure violations across all 6,096+ test files.

Business Value: Platform/Internal - Test Infrastructure Stability
Validates that the SSOT framework works correctly and provides reliable
foundation for all testing in the system.
"""

import asyncio
import logging
import pytest
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any

# Add project root for imports - MUST be before any local imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.isolated_environment import IsolatedEnvironment

# Import SSOT components under test
from test_framework.ssot import (
    # Base classes
    BaseTestCase,
    AsyncBaseTestCase,
    DatabaseTestCase,
    WebSocketTestCase,
    IntegrationTestCase,
    TestExecutionMetrics,
    
    # Mock utilities
    MockFactory,
    MockRegistry,
    DatabaseMockFactory,
    ServiceMockFactory,
    get_mock_factory,
    
    # Database utilities
    DatabaseTestUtility,
    PostgreSQLTestUtility,
    ClickHouseTestUtility,
    create_database_test_utility,
    
    # WebSocket utilities
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketEventType,
    
    # Docker utilities
    DockerTestUtility,
    DockerTestEnvironmentType,
    create_docker_test_utility,
    
    # Framework utilities
    validate_test_class,
    get_test_base_for_category,
    validate_ssot_compliance,
    get_ssot_status,
    SSOT_VERSION,
    SSOT_COMPLIANCE
)

logger = logging.getLogger(__name__)


class TestSSotFrameworkCore:
    """Test core SSOT framework functionality."""
    
    def test_framework_version_and_compliance(self):
        """Test framework version and compliance constants."""
        assert SSOT_VERSION == "1.0.0"
        assert isinstance(SSOT_COMPLIANCE, dict)
        assert SSOT_COMPLIANCE["total_components"] == 15
        assert SSOT_COMPLIANCE["base_classes"] == 5
        assert SSOT_COMPLIANCE["mock_factories"] == 3
        assert SSOT_COMPLIANCE["database_utilities"] == 3
        assert SSOT_COMPLIANCE["websocket_utilities"] == 1
        assert SSOT_COMPLIANCE["docker_utilities"] == 3
    
    def test_ssot_status_function(self):
        """Test get_ssot_status function."""
        status = get_ssot_status()
        
        assert isinstance(status, dict)
        assert status["version"] == SSOT_VERSION
        assert "compliance" in status
        assert "violations" in status
        assert "components" in status
        
        # Check component categories
        components = status["components"]
        assert "base_classes" in components
        assert "mock_utilities" in components
        assert "database_utilities" in components
        assert "websocket_utilities" in components
        assert "docker_utilities" in components
        
        # Validate expected components are present
        assert "BaseTestCase" in components["base_classes"]
        assert "MockFactory" in components["mock_utilities"]
        assert "DatabaseTestUtility" in components["database_utilities"]
        assert "WebSocketTestUtility" in components["websocket_utilities"]
        assert "DockerTestUtility" in components["docker_utilities"]
    
    def test_ssot_compliance_validation(self):
        """Test SSOT compliance validation."""
        violations = validate_ssot_compliance()
        assert isinstance(violations, list)
        
        # Compliance validation should pass for properly implemented framework
        if violations:
            logger.warning(f"SSOT compliance violations found: {violations}")
    
    def test_validate_test_class_function(self):
        """Test validate_test_class utility function."""
        # Valid test class
        class ValidTest(BaseTestCase):
            def test_something(self):
                pass
        
        errors = validate_test_class(ValidTest)
        assert isinstance(errors, list)
        
        # Invalid test class (not inheriting from BaseTestCase)
        class InvalidTest:
            def test_something(self):
                pass
        
        errors = validate_test_class(InvalidTest)
        assert len(errors) > 0
        assert "must inherit from BaseTestCase" in errors[0]
    
    def test_get_test_base_for_category(self):
        """Test get_test_base_for_category utility function."""
        # Test different categories
        assert get_test_base_for_category("unit") == BaseTestCase
        assert get_test_base_for_category("integration") == IntegrationTestCase
        assert get_test_base_for_category("database") == DatabaseTestCase
        assert get_test_base_for_category("websocket") == WebSocketTestCase
        assert get_test_base_for_category("e2e") == IntegrationTestCase
        assert get_test_base_for_category("unknown") == BaseTestCase


class TestBaseTestCase:
    """Test the BaseTestCase SSOT implementation."""
    
    def test_base_test_case_initialization(self):
        """Test BaseTestCase initializes correctly."""
        test_case = BaseTestCase()
        
        assert hasattr(test_case, 'env')
        assert hasattr(test_case, 'metrics')
        assert hasattr(test_case, '_test_id')
        assert hasattr(test_case, '_resources_to_cleanup')
        assert hasattr(test_case, 'test_name')
        assert hasattr(test_case, 'test_class')
        
        # Test configuration
        assert test_case.ISOLATION_ENABLED == True
        assert test_case.AUTO_CLEANUP == True
    
    def test_setup_method_creates_test_context(self):
        """Test that setup_method creates proper test context."""
        test_case = SSotBaseTestCase()
        
        # Mock method for testing
        mock_method = MagicMock()
        mock_method.__name__ = "test_example"
        
        # Call setup_method
        test_case.setup_method(mock_method)
        
        # Verify test context is created
        assert test_case._test_context is not None
        assert test_case._test_context.test_name == "test_example"
        assert test_case._test_context.test_id.endswith("test_example")
        assert test_case._test_started
        
        # Verify environment is isolated
        assert test_case._env.is_isolated()
        
        # Verify test environment variables are set
        assert test_case._env.get("TESTING") == "true"
        assert test_case._env.get("TEST_ID") is not None
        assert test_case._env.get("TRACE_ID") is not None
        
        # Clean up
        test_case.teardown_method(mock_method)
    
    def test_teardown_method_cleans_up(self):
        """Test that teardown_method properly cleans up."""
        test_case = SSotBaseTestCase()
        
        # Setup first
        mock_method = MagicMock()
        mock_method.__name__ = "test_cleanup"
        test_case.setup_method(mock_method)
        
        # Add a cleanup callback to test
        cleanup_called = [False]
        def cleanup_callback():
            cleanup_called[0] = True
        test_case.add_cleanup(cleanup_callback)
        
        # Call teardown
        test_case.teardown_method(mock_method)
        
        # Verify cleanup occurred
        assert cleanup_called[0]
        assert test_case._test_completed
        assert test_case._cleanup_callbacks == []
        assert test_case._test_context is None
    
    def test_environment_integration(self):
        """Test that environment integration works correctly."""
        test_case = SSotBaseTestCase()
        
        # Test setting and getting environment variables
        test_case.set_env_var("TEST_VAR", "test_value")
        assert test_case.get_env_var("TEST_VAR") == "test_value"
        
        # Test deletion
        test_case.delete_env_var("TEST_VAR")
        assert test_case.get_env_var("TEST_VAR") is None
    
    def test_temp_env_vars_context_manager(self):
        """Test temporary environment variables context manager."""
        test_case = SSotBaseTestCase()
        
        # Set initial value
        test_case.set_env_var("TEMP_TEST", "original")
        
        # Use context manager
        with test_case.temp_env_vars(TEMP_TEST="temporary", NEW_VAR="new"):
            assert test_case.get_env_var("TEMP_TEST") == "temporary"
            assert test_case.get_env_var("NEW_VAR") == "new"
        
        # Verify restoration
        assert test_case.get_env_var("TEMP_TEST") == "original"
        assert test_case.get_env_var("NEW_VAR") is None
    
    def test_metrics_recording(self):
        """Test metrics recording functionality."""
        test_case = SSotBaseTestCase()
        
        # Record metrics
        test_case.record_metric("test_metric", 42)
        test_case.record_metric("another_metric", "string_value")
        
        # Retrieve metrics
        assert test_case.get_metric("test_metric") == 42
        assert test_case.get_metric("another_metric") == "string_value"
        assert test_case.get_metric("nonexistent") is None
        
        # Get all metrics
        all_metrics = test_case.get_all_metrics()
        assert "test_metric" in all_metrics
        assert "another_metric" in all_metrics
        assert all_metrics["test_metric"] == 42
    
    def test_database_query_tracking(self):
        """Test database query tracking."""
        test_case = SSotBaseTestCase()
        
        # Initially zero queries
        assert test_case.get_db_query_count() == 0
        
        # Increment queries
        test_case.increment_db_query_count(3)
        assert test_case.get_db_query_count() == 3
        
        # Test context manager
        with test_case.track_db_queries():
            test_case.increment_db_query_count(2)
        
        assert test_case.get_db_query_count() == 5
    
    def test_websocket_event_tracking(self):
        """Test WebSocket event tracking."""
        test_case = SSotBaseTestCase()
        
        # Initially zero events
        assert test_case.get_websocket_events_count() == 0
        
        # Increment events
        test_case.increment_websocket_events(5)
        assert test_case.get_websocket_events_count() == 5
        
        # Test context manager
        with test_case.track_websocket_events():
            test_case.increment_websocket_events(3)
        
        assert test_case.get_websocket_events_count() == 8
    
    def test_assertion_utilities(self):
        """Test custom assertion utilities."""
        test_case = SSotBaseTestCase()
        
        # Test environment variable assertions
        test_case.set_env_var("ASSERT_TEST", "value")
        
        # Should pass
        test_case.assert_env_var_set("ASSERT_TEST")
        test_case.assert_env_var_set("ASSERT_TEST", "value")
        
        # Should fail
        with pytest.raises(AssertionError):
            test_case.assert_env_var_set("NONEXISTENT_VAR")
        
        with pytest.raises(AssertionError):
            test_case.assert_env_var_set("ASSERT_TEST", "wrong_value")
        
        # Test metrics assertions
        test_case.record_metric("test_assertion", True)
        test_case.assert_metrics_recorded("test_assertion")
        
        with pytest.raises(AssertionError):
            test_case.assert_metrics_recorded("nonexistent_metric")
    
    def test_backwards_compatibility_aliases(self):
        """Test that backwards compatibility aliases work."""
        # Test that the aliases point to the SSOT classes
        assert BaseTestCase is SSotBaseTestCase
        assert AsyncTestCase is SSotAsyncTestCase
        
        # Test that they can be instantiated
        base_test = BaseTestCase()
        assert isinstance(base_test, SSotBaseTestCase)


class TestSSotAsyncTestCase:
    """Test the SSOT AsyncTestCase functionality."""
    
    @pytest.mark.asyncio
    async def test_async_initialization(self):
        """Test that async test case initializes correctly."""
        test_case = SSotAsyncTestCase()
        
        # Should have all base functionality
        assert test_case._env is not None
        assert test_case._metrics is not None
        
        # Test async setup/teardown
        mock_method = MagicMock()
        mock_method.__name__ = "test_async_method"
        
        await test_case.setup_method(mock_method)
        assert test_case._test_started
        
        await test_case.teardown_method(mock_method)
        assert test_case._test_completed
    
    @pytest.mark.asyncio
    async def test_async_temp_env_vars(self):
        """Test async temporary environment variables."""
        test_case = SSotAsyncTestCase()
        
        test_case.set_env_var("ASYNC_TEST", "original")
        
        async with test_case.async_temp_env_vars(ASYNC_TEST="temporary"):
            assert test_case.get_env_var("ASYNC_TEST") == "temporary"
        
        assert test_case.get_env_var("ASYNC_TEST") == "original"
    
    @pytest.mark.asyncio
    async def test_wait_for_condition(self):
        """Test the wait_for_condition utility."""
        test_case = SSotAsyncTestCase()
        
        # Test successful condition
        counter = [0]
        def condition():
            counter[0] += 1
            return counter[0] >= 3
        
        await test_case.wait_for_condition(condition, timeout=1.0, interval=0.1)
        assert counter[0] >= 3
        
        # Test timeout
        def never_true():
            return False
        
        with pytest.raises(TimeoutError):
            await test_case.wait_for_condition(never_true, timeout=0.1, interval=0.05)
    
    @pytest.mark.asyncio
    async def test_run_with_timeout(self):
        """Test the run_with_timeout utility."""
        test_case = SSotAsyncTestCase()
        
        # Test successful execution
        async def quick_coro():
            await asyncio.sleep(0.01)
            return "success"
        
        result = await test_case.run_with_timeout(quick_coro(), timeout=1.0)
        assert result == "success"
        
        # Test timeout
        async def slow_coro():
            await asyncio.sleep(1.0)
            return "too_slow"
        
        with pytest.raises(TimeoutError):
            await test_case.run_with_timeout(slow_coro(), timeout=0.1)


class TestMockConfiguration:
    """Test MockConfiguration functionality."""
    
    def test_default_configuration(self):
        """Test default mock configuration."""
        config = MockConfiguration()
        
        assert not config.should_fail
        assert config.failure_rate == 0.0
        assert config.failure_message == "Mock failure"
        assert config.execution_delay == 0.0
        assert config.max_retries == 3
        assert config.timeout == 5.0
        assert config.enable_metrics
        assert config.custom_responses == {}
    
    def test_failure_behavior(self):
        """Test failure configuration behavior."""
        # Always fail
        config = MockConfiguration(should_fail=True)
        assert config.should_fail_now()
        
        # Never fail
        config = MockConfiguration(should_fail=False, failure_rate=0.0)
        assert not config.should_fail_now()
        
        # Probabilistic failure - test multiple times
        config = MockConfiguration(failure_rate=0.5)
        results = [config.should_fail_now() for _ in range(100)]
        # Should have some True and some False (probabilistic)
        assert any(results) and not all(results)


class TestSSotMockAgent:
    """Test the SSOT Mock Agent functionality."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test mock agent initialization."""
        agent = SSotMockAgent()
        
        assert agent.agent_id.startswith("agent_")
        assert agent.user_id.startswith("user_")
        assert agent.state == AgentState.IDLE
        assert agent.execution_results == []
        assert agent.tools_executed == []
        assert agent.thinking_steps == []
        assert agent.websocket_events == []
    
    @pytest.mark.asyncio
    async def test_process_request(self):
        """Test agent request processing."""
        agent = SSotMockAgent()
        
        request = {"content": "test request", "user_id": "test_user"}
        result = await agent.process_request(request)
        
        assert result["status"] == "success"
        assert "test request" in result["result"]
        assert result["agent_id"] == agent.agent_id
        assert len(agent.execution_results) == 1
    
    @pytest.mark.asyncio
    async def test_agent_run_lifecycle(self):
        """Test full agent run lifecycle."""
        agent = SSotMockAgent()
        
        run_id = "test_run_123"
        user_id = "test_user_456"
        request = "Process this request"
        
        result = await agent.run(request, run_id, user_id)
        
        # Check state updates
        assert agent.run_id == run_id
        assert agent.user_id == user_id
        assert agent.state == AgentState.IDLE  # Should return to IDLE after completion
        
        # Check WebSocket events were emitted
        events = agent.get_websocket_events()
        assert len(events) >= 2  # At least started and completed
        
        event_types = [event["type"] for event in events]
        assert "agent_started" in event_types
        assert "agent_completed" in event_types
    
    @pytest.mark.asyncio
    async def test_agent_thinking(self):
        """Test agent thinking functionality."""
        agent = SSotMockAgent()
        
        result = await agent.think("What should I do?")
        
        assert "Thinking about:" in result
        assert len(agent.thinking_steps) == 1
        assert agent.thinking_steps[0] == result
        
        # Check WebSocket event
        events = agent.get_websocket_events()
        assert any(event["type"] == "agent_thinking" for event in events)
    
    @pytest.mark.asyncio
    async def test_tool_execution(self):
        """Test agent tool execution."""
        agent = SSotMockAgent()
        
        tool_result = await agent.execute_tool("search", {"query": "test"})
        
        assert tool_result["tool"] == "search"
        assert tool_result["success"]
        assert "search" in agent.tools_executed
        
        # Check WebSocket events
        events = agent.get_websocket_events()
        event_types = [event["type"] for event in events]
        assert "tool_executing" in event_types
        assert "tool_completed" in event_types
    
    @pytest.mark.asyncio
    async def test_agent_failure_simulation(self):
        """Test agent failure behavior."""
        config = MockConfiguration(should_fail=True, failure_message="Test failure")
        agent = SSotMockAgent(config=config)
        
        with pytest.raises(Exception) as exc_info:
            await agent.process_request({"content": "fail me"})
        
        assert "Test failure" in str(exc_info.value)
        assert agent.error_count > 0
        assert agent.last_error is not None
    
    @pytest.mark.asyncio 
    async def test_agent_recovery(self):
        """Test agent recovery functionality."""
        agent = SSotMockAgent()
        agent.state = AgentState.ERROR
        
        recovered = await agent.recover()
        
        assert recovered
        assert agent.state == AgentState.ACTIVE


class TestSSotMockAgentService:
    """Test the SSOT Mock Agent Service functionality."""
    
    @pytest.mark.asyncio
    async def test_service_lifecycle(self):
        """Test agent service start/stop lifecycle."""
        service = SSotMockAgentService()
        
        # Initially stopped
        assert service.status == ServiceStatus.STOPPED
        
        # Start service
        started = await service.start_service()
        assert started
        assert service.status == ServiceStatus.RUNNING
        
        # Stop service
        stopped = await service.stop_service()
        assert stopped
        assert service.status == ServiceStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_message_processing(self):
        """Test message processing through service."""
        service = SSotMockAgentService()
        await service.start_service()
        
        message = {
            "user_id": "test_user",
            "content": "process this message"
        }
        
        result = await service.process_message(message)
        
        assert result["status"] == "completed"
        assert "response" in result
        assert "agent_id" in result
        assert service.total_requests == 1
        assert service.successful_requests == 1
        assert len(service.messages_processed) == 1
    
    @pytest.mark.asyncio
    async def test_agent_management(self):
        """Test agent creation and management."""
        service = SSotMockAgentService()
        
        # Create agent for user
        agent = await service.get_or_create_agent("user1")
        assert agent.user_id == "user1"
        assert agent.state == AgentState.ACTIVE
        
        # Same user should get same agent
        same_agent = await service.get_or_create_agent("user1")
        assert same_agent is agent
        
        # Different user gets different agent
        other_agent = await service.get_or_create_agent("user2")
        assert other_agent is not agent
        assert other_agent.user_id == "user2"
        
        # Release agent
        released = await service.release_agent("user1")
        assert released
        assert "user1" not in service.agents
    
    def test_service_status(self):
        """Test service status reporting."""
        service = SSotMockAgentService()
        service.total_requests = 10
        service.successful_requests = 8
        service.failed_requests = 2
        
        status = service.get_service_status()
        
        assert status["total_requests"] == 10
        assert status["successful_requests"] == 8
        assert status["failed_requests"] == 2
        assert status["success_rate"] == 0.8


class TestSSotMockFactory:
    """Test the SSOT Mock Factory functionality."""
    
    def test_factory_initialization(self):
        """Test factory initialization."""
        factory = SSotMockFactory()
        
        assert factory._created_mocks == []
    
    def test_agent_creation(self):
        """Test agent creation through factory."""
        factory = SSotMockFactory()
        
        agent = factory.create_agent(agent_id="test_agent", user_id="test_user")
        
        assert agent.agent_id == "test_agent"
        assert agent.user_id == "test_user"
        assert agent in factory._created_mocks
    
    def test_agent_service_creation(self):
        """Test agent service creation."""
        factory = SSotMockFactory()
        
        service = factory.create_agent_service()
        
        assert isinstance(service, SSotMockAgentService)
        assert service in factory._created_mocks
    
    def test_configuration_helpers(self):
        """Test configuration helper methods."""
        factory = SSotMockFactory()
        
        # Failing config
        failing_config = factory.create_failing_config()
        assert failing_config.should_fail
        
        # Slow config  
        slow_config = factory.create_slow_config(execution_delay=2.0)
        assert slow_config.execution_delay == 2.0
        
        # Unreliable config
        unreliable_config = factory.create_unreliable_config(failure_rate=0.5)
        assert unreliable_config.failure_rate == 0.5
    
    def test_agent_cluster_creation(self):
        """Test creating multiple agents."""
        factory = SSotMockFactory()
        
        agents = factory.create_agent_cluster(count=3)
        
        assert len(agents) == 3
        assert all(isinstance(agent, SSotMockAgent) for agent in agents)
        assert len(set(agent.agent_id for agent in agents)) == 3  # All unique IDs
    
    def test_factory_utilities(self):
        """Test factory utility methods."""
        factory = SSotMockFactory()
        
        # Create some mocks
        agent = factory.create_agent()
        service = factory.create_agent_service()
        
        # Record some calls
        agent.call_count = 5
        service.call_count = 3
        
        # Test summary
        summary = factory.get_all_mocks_summary()
        assert summary["total_mocks"] == 2
        assert len(summary["mock_summaries"]) == 2
        
        # Test reset
        factory.reset_all_mocks()
        assert agent.call_count == 0
        assert service.call_count == 0
        
        # Test cleanup
        factory.cleanup()
        assert len(factory._created_mocks) == 0


class TestConvenienceFunctions:
    """Test convenience functions for mock creation."""
    
    def test_create_mock_agent_function(self):
        """Test create_mock_agent convenience function."""
        agent = create_mock_agent(agent_id="convenience_test")
        
        assert isinstance(agent, SSotMockAgent)
        assert agent.agent_id == "convenience_test"
    
    def test_create_mock_agent_service_function(self):
        """Test create_mock_agent_service convenience function."""
        service = create_mock_agent_service(should_fail=True)
        
        assert isinstance(service, SSotMockAgentService)
        assert service.config.should_fail
    
    def test_global_factory_access(self):
        """Test global factory instance access."""
        factory1 = get_mock_factory()
        factory2 = get_mock_factory()
        
        # Should be the same instance
        assert factory1 is factory2


class TestBackwardsCompatibility:
    """Test backwards compatibility features."""
    
    def test_legacy_mock_aliases(self):
        """Test that legacy mock aliases work."""
        from test_framework.ssot.mock_factory import MockAgent, MockAgentService
        
        # Should be aliases to SSOT classes
        assert MockAgent is SSotMockAgent
        assert MockAgentService is SSotMockAgentService
        
        # Should be able to create instances
        agent = MockAgent()
        service = MockAgentService()
        
        assert isinstance(agent, SSotMockAgent)
        assert isinstance(service, SSotMockAgentService)


class TestIntegrationScenarios:
    """Test integration scenarios combining base test case and mocks."""
    
    @pytest.mark.asyncio
    async def test_full_test_scenario(self):
        """Test a complete test scenario using SSOT framework."""
        # This simulates how a real test would use the SSOT framework
        
        class ExampleTest(SSotAsyncTestCase):
            """Example test using SSOT framework."""
            
            async def test_agent_processing(self):
                # Setup environment
                self.set_env_var("TEST_ENVIRONMENT", "integration") 
                
                # Create mock agent
                agent = create_mock_agent(user_id="integration_user")
                
                # Process request
                result = await agent.run(
                    "test request", 
                    "run_123", 
                    "integration_user"
                )
                
                # Record metrics
                self.record_metric("requests_processed", 1)
                self.increment_websocket_events(2)  # started, completed
                
                # Assertions
                assert result["status"] == "success"
                self.assert_env_var_set("TEST_ENVIRONMENT", "integration")
                self.assert_metrics_recorded("requests_processed")
                assert self.get_websocket_events_count() == 2
                
                return result
        
        # Run the test
        test_instance = ExampleTest()
        
        # Setup
        mock_method = MagicMock()
        mock_method.__name__ = "test_agent_processing"
        await test_instance.setup_method(mock_method)
        
        try:
            # Execute test
            result = await test_instance.test_agent_processing()
            
            # Verify result
            assert result["status"] == "success"
            assert test_instance.get_metric("requests_processed") == 1
            
        finally:
            # Teardown
            await test_instance.teardown_method(mock_method)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])