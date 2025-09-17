"""
Base Agent Factory Patterns & SSOT Compliance Tests - Foundation Coverage Phase 1

Business Value: Platform/Internal - System Architecture Compliance & Migration Validation
Tests factory method patterns, SSOT compliance validation, migration status,
and UserExecutionContext pattern adoption that ensures proper multi-user isolation.

SSOT Compliance: Uses SSotAsyncTestCase, tests real factory patterns,
validates SSOT compliance per CLAUDE.md architectural requirements.

Coverage Target: BaseAgent factory methods, SSOT compliance, migration validation
Current BaseAgent Factory/Compliance Coverage: ~1% -> Target: 12%+

Critical Patterns Tested:
- Factory method patterns (create_with_context, create_agent_with_context)
- SSOT compliance validation and reporting
- Migration status and completeness validation
- UserExecutionContext pattern adoption
- Legacy pattern detection and warnings
- Session isolation validation

GitHub Issue: #714 Agents Module Unit Tests - Phase 1 Foundation
"""

import pytest
import asyncio
import warnings
from unittest.mock import Mock, AsyncMock, patch, call
from typing import Dict, Any, Optional, List

# ABSOLUTE IMPORTS - SSOT compliance
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import target classes
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.schemas.agent import SubAgentLifecycle


class FactoryTestAgent(BaseAgent):
    """Agent implementation for testing factory patterns and SSOT compliance."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_type = "factory_test_agent"
        self.creation_metadata = {
            "created_via": "direct_constructor",
            "creation_timestamp": None
        }

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Modern implementation for UserExecutionContext pattern testing."""
        return {
            "status": "success",
            "result": "factory pattern test completed",
            "agent_type": self.agent_type,
            "has_user_context": self.user_context is not None,
            "context_user_id": context.user_id,
            "creation_metadata": self.creation_metadata
        }

    @classmethod
    def create_via_factory(cls, context: UserExecutionContext, **kwargs):
        """Custom factory method for testing."""
        agent = cls.create_with_context(context, **kwargs)
        agent.creation_metadata["created_via"] = "custom_factory"
        return agent


class LegacyPatternAgent(BaseAgent):
    """Agent that still uses some legacy patterns for testing detection."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_type = "legacy_pattern_agent"
        # Simulate legacy pattern - storing user_id as instance variable
        self.user_id = kwargs.get('user_id', 'test-user-legacy')

    # Missing _execute_with_user_context implementation to test migration status


class BaseAgentFactoryPatternsTests(SSotAsyncTestCase):
    """Test BaseAgent factory patterns and SSOT compliance."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

        # Create mock dependencies
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="Mock response")

        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.emit_agent_event = AsyncMock()

        # Create test context for factory methods
        self.test_context = UserExecutionContext(
            user_id="factory-test-user-001",
            thread_id="factory-test-thread-001",
            run_id="factory-test-run-001",
            request_id="factory-test-request-001",
            agent_context={
                "user_request": "factory pattern test",
                "test_factory_creation": True
            }
        ).with_db_session(AsyncMock())

    def test_agent_create_with_context_factory_method(self):
        """Test BaseAgent.create_with_context factory method."""
        # Create agent via factory method
        agent = FactoryTestAgent.create_with_context(
            context=self.test_context,
            agent_config={"custom_setting": "test_value"}
        )

        # Verify: Agent was created correctly
        assert isinstance(agent, FactoryTestAgent)
        assert agent.agent_type == "factory_test_agent"

        # Verify: Agent has user context set internally
        assert hasattr(agent, '_user_context')
        assert agent._user_context is self.test_context

        # Verify: user_context property is properly set by factory method
        assert agent.user_context is self.test_context

        # Verify: Configuration was applied for existing attributes only
        # The factory method only applies config to existing attributes
        # Let's test with an existing attribute like max_retries
        agent2 = FactoryTestAgent.create_with_context(
            context=self.test_context,
            agent_config={"max_retries": 7}
        )
        assert agent2.max_retries == 7

    def test_agent_create_agent_with_context_factory_method(self):
        """Test BaseAgent.create_agent_with_context factory method (preferred)."""
        # Create agent via preferred factory method
        agent = BaseAgent.create_agent_with_context(self.test_context)

        # Verify: Agent was created correctly
        assert isinstance(agent, BaseAgent)

        # Verify: Agent has user context properly set
        assert agent.user_context is self.test_context

        # Verify: Agent name reflects class
        assert "BaseAgent" in agent.name

        # Verify: Agent has proper description
        assert "user context isolation" in agent.description

        # Verify: Agent was configured for user context pattern
        # Note: These are private attributes in BaseAgent
        assert agent._enable_reliability is True
        assert agent._enable_execution_engine is True

    def test_agent_factory_method_context_validation(self):
        """Test factory methods validate UserExecutionContext properly."""
        # Test with None context - should raise error
        with pytest.raises((ValueError, TypeError)):
            BaseAgent.create_agent_with_context(None)

        # Test with invalid context type - should raise error
        with pytest.raises((ValueError, TypeError)):
            BaseAgent.create_agent_with_context("invalid_context")

        # Test with valid context - should succeed
        agent = BaseAgent.create_agent_with_context(self.test_context)
        assert agent.user_context is self.test_context

    def test_agent_factory_creates_isolated_instances(self):
        """Test factory methods create properly isolated agent instances."""
        # Create multiple agents from same context
        agent1 = FactoryTestAgent.create_with_context(self.test_context)
        agent2 = FactoryTestAgent.create_with_context(self.test_context)

        # Verify: Agents are separate instances
        assert agent1 is not agent2
        assert id(agent1) != id(agent2)

        # Verify: Agents have separate timing collectors
        assert agent1.timing_collector is not agent2.timing_collector

        # Verify: Agents have separate execution monitors
        assert agent1.execution_monitor is not agent2.execution_monitor

        # Verify: Agents have separate reliability managers
        assert agent1.reliability_manager is not agent2.reliability_manager

        # Verify: Both agents have the context internally stored
        # Note: user_context property is None until explicitly set
        # The factory method stores context in _user_context internally
        assert hasattr(agent1, '_user_context')
        assert hasattr(agent2, '_user_context')
        assert agent1._user_context is self.test_context
        assert agent2._user_context is self.test_context

    def test_agent_legacy_factory_with_warnings(self):
        """Test legacy factory method issues proper warnings."""
        # Capture warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Create agent via legacy factory method
            agent = BaseAgent.create_legacy_with_warnings(
                llm_manager=self.llm_manager,
                tool_dispatcher=None,
                redis_manager=None
            )

            # Verify: Warning was issued
            assert len(w) >= 1
            warning_messages = [str(warning.message) for warning in w]
            deprecation_warnings = [msg for msg in warning_messages if "DEPRECATED" in msg]
            assert len(deprecation_warnings) >= 1

            # Verify: Warning mentions the preferred method
            assert any("create_with_context" in msg for msg in warning_messages)

        # Verify: Agent was still created
        assert isinstance(agent, BaseAgent)

    async def test_agent_validate_modern_implementation(self):
        """Test agent modern implementation validation."""
        # Test with modern agent (has _execute_with_user_context)
        modern_agent = FactoryTestAgent.create_with_context(self.test_context)
        validation = modern_agent.validate_modern_implementation()

        # Verify: Modern agent passes validation
        assert validation["compliant"] is True
        assert validation["pattern"] == "modern"
        assert len(validation["errors"]) == 0

        # Test with legacy agent (missing _execute_with_user_context)
        legacy_agent = LegacyPatternAgent(llm_manager=self.llm_manager)
        legacy_validation = legacy_agent.validate_modern_implementation()

        # Verify: Legacy agent fails validation
        assert legacy_validation["compliant"] is False
        assert legacy_validation["pattern"] == "none"
        assert len(legacy_validation["errors"]) > 0

    def test_agent_assert_user_execution_context_pattern(self):
        """Test agent UserExecutionContext pattern assertions."""
        # Test with compliant modern agent
        modern_agent = FactoryTestAgent.create_with_context(self.test_context)

        # Should not raise error
        modern_agent.assert_user_execution_context_pattern()

        # Test with legacy agent that has violations
        legacy_agent = LegacyPatternAgent(llm_manager=self.llm_manager)

        # Should raise RuntimeError for critical violations
        with pytest.raises(RuntimeError, match="CRITICAL COMPLIANCE VIOLATIONS"):
            legacy_agent.assert_user_execution_context_pattern()

    def test_agent_get_migration_status_comprehensive(self):
        """Test comprehensive migration status reporting."""
        # Test modern agent migration status
        modern_agent = FactoryTestAgent.create_with_context(self.test_context)
        modern_status = modern_agent.get_migration_status()

        # Verify: Migration status structure
        assert isinstance(modern_status, dict)
        required_fields = [
            "agent_name", "agent_class", "migration_status", "execution_pattern",
            "user_isolation_safe", "warnings_count", "errors_count", "recommendations_count",
            "validation_timestamp", "compliance_details"
        ]

        for field in required_fields:
            assert field in modern_status

        # Verify: Modern agent shows compliant status
        assert modern_status["migration_status"] == "compliant"
        assert modern_status["execution_pattern"] == "modern"
        assert modern_status["user_isolation_safe"] is True
        assert modern_status["errors_count"] == 0

        # Test legacy agent migration status
        legacy_agent = LegacyPatternAgent(llm_manager=self.llm_manager)
        legacy_status = legacy_agent.get_migration_status()

        # Verify: Legacy agent shows needs_migration status
        assert legacy_status["migration_status"] == "needs_migration"
        assert legacy_status["user_isolation_safe"] is False
        assert legacy_status["errors_count"] > 0 or legacy_status["warnings_count"] > 0

    async def test_agent_validate_migration_completeness(self):
        """Test DeepAgentState migration completeness validation."""
        modern_agent = FactoryTestAgent.create_with_context(self.test_context)
        validation = modern_agent.validate_migration_completeness()

        # Verify: Validation structure
        assert isinstance(validation, dict)
        assert "migration_complete" in validation
        assert "agent_name" in validation
        assert "violations" in validation
        assert "warnings" in validation
        assert "validation_timestamp" in validation

        # Verify: Modern agent passes migration validation
        assert validation["migration_complete"] is True
        assert len(validation["violations"]) == 0

        # Agent should have modern implementation
        assert hasattr(modern_agent, '_execute_with_user_context')
        assert callable(getattr(modern_agent, '_execute_with_user_context'))

    async def test_agent_session_isolation_validation(self):
        """Test agent session isolation validation."""
        agent = FactoryTestAgent.create_with_context(self.test_context)

        # Session isolation validation should pass (called during initialization)
        # If it fails, initialization would have raised an exception

        # Verify: Agent doesn't store database sessions as instance variables
        assert not hasattr(agent, 'db_session')
        assert not hasattr(agent, '_db_session')

        # Verify: Agent can get session manager through context
        session_manager = agent._get_session_manager(self.test_context)
        assert session_manager is not None

    async def test_agent_factory_with_custom_configuration(self):
        """Test factory methods with custom agent configuration."""
        custom_config = {
            "max_retries": 5,
            "custom_timeout": 30,
            "test_setting": "custom_value"
        }

        agent = FactoryTestAgent.create_with_context(
            context=self.test_context,
            agent_config=custom_config
        )

        # Verify: Custom configuration applied
        assert hasattr(agent, 'max_retries')
        assert agent.max_retries == 5
        assert hasattr(agent, 'custom_timeout')
        assert agent.custom_timeout == 30
        assert hasattr(agent, 'test_setting')
        assert agent.test_setting == "custom_value"

        # Verify: Agent still has user context
        assert agent.user_context is self.test_context

    async def test_agent_factory_execution_integration(self):
        """Test factory-created agents integrate properly with execution patterns."""
        agent = FactoryTestAgent.create_via_factory(self.test_context)
        agent.set_websocket_bridge(self.websocket_bridge, "factory-execution-001")

        # Execute agent
        result = await agent.execute_with_context(self.test_context, stream_updates=False)

        # Verify: Execution successful
        assert result["status"] == "success"
        assert result["has_user_context"] is True
        assert result["context_user_id"] == "factory-test-user-001"
        assert result["creation_metadata"]["created_via"] == "custom_factory"

    def test_agent_factory_memory_isolation(self):
        """Test factory-created agents maintain memory isolation."""
        # Create agents for different users
        context1 = UserExecutionContext(
            user_id="factory-isolation-user-1",
            thread_id="factory-isolation-thread-1",
            run_id="factory-isolation-run-1",
            agent_context={"user_data": "user1_secret"}
        ).with_db_session(AsyncMock())

        context2 = UserExecutionContext(
            user_id="factory-isolation-user-2",
            thread_id="factory-isolation-thread-2",
            run_id="factory-isolation-run-2",
            agent_context={"user_data": "user2_secret"}
        ).with_db_session(AsyncMock())

        agent1 = FactoryTestAgent.create_with_context(context1)
        agent2 = FactoryTestAgent.create_with_context(context2)

        # Verify: Agents have isolated contexts
        assert agent1.user_context.user_id == "factory-isolation-user-1"
        assert agent2.user_context.user_id == "factory-isolation-user-2"

        # Verify: Agent contexts don't leak between instances
        assert agent1.user_context.agent_context["user_data"] == "user1_secret"
        assert agent2.user_context.agent_context["user_data"] == "user2_secret"

        # Verify: Modifying one agent doesn't affect another
        agent1.test_attribute = "agent1_value"
        assert not hasattr(agent2, 'test_attribute')

    async def test_agent_factory_concurrent_creation(self):
        """Test factory methods work correctly with concurrent agent creation."""
        # Create multiple contexts for concurrent testing
        contexts = []
        for i in range(5):
            context = UserExecutionContext(
                user_id=f"concurrent-factory-user-{i}",
                thread_id=f"concurrent-factory-thread-{i}",
                run_id=f"concurrent-factory-run-{i}",
                agent_context={"user_index": i, "concurrent_test": True}
            ).with_db_session(AsyncMock())
            contexts.append(context)

        # Create agents concurrently
        def create_agent_for_context(context):
            return FactoryTestAgent.create_with_context(context)

        # Use asyncio to simulate concurrent creation
        agents = await asyncio.gather(*[
            asyncio.get_event_loop().run_in_executor(None, create_agent_for_context, ctx)
            for ctx in contexts
        ])

        # Verify: All agents created successfully
        assert len(agents) == 5
        for i, agent in enumerate(agents):
            assert isinstance(agent, FactoryTestAgent)
            assert agent.user_context.user_id == f"concurrent-factory-user-{i}"
            assert agent.user_context.agent_context["user_index"] == i

        # Verify: All agents are separate instances
        agent_ids = [id(agent) for agent in agents]
        assert len(set(agent_ids)) == 5  # All unique

    def test_agent_factory_error_handling(self):
        """Test factory method error handling and validation."""
        # Test with invalid context types
        invalid_contexts = [
            None,
            "string_context",
            123,
            {"dict": "context"},
            []
        ]

        for invalid_context in invalid_contexts:
            with pytest.raises((ValueError, TypeError, AttributeError)):
                FactoryTestAgent.create_with_context(invalid_context)

        # Test factory method doesn't fail on valid context
        agent = FactoryTestAgent.create_with_context(self.test_context)
        assert isinstance(agent, FactoryTestAgent)

    def test_agent_ssot_compliance_reporting(self):
        """Test SSOT compliance features and reporting."""
        agent = FactoryTestAgent.create_with_context(self.test_context)

        # Verify: Agent follows SSOT patterns
        # 1. Uses SSot base classes and mixins
        assert hasattr(agent, '_websocket_adapter')

        # 2. Has unified reliability handler (SSOT pattern)
        assert hasattr(agent, 'unified_reliability_handler')
        unified_handler = agent.unified_reliability_handler
        if unified_handler:
            assert hasattr(unified_handler, 'service_name')
            assert unified_handler.service_name.startswith('agent_')

        # 3. Uses proper execution patterns
        assert hasattr(agent, '_execute_with_user_context')
        assert callable(getattr(agent, '_execute_with_user_context'))

        # 4. Follows WebSocket SSOT patterns
        assert hasattr(agent, 'emit_thinking')
        assert hasattr(agent, 'emit_tool_executing')
        assert hasattr(agent, 'emit_agent_completed')

    def test_agent_backward_compatibility_validation(self):
        """Test agent maintains backward compatibility where needed."""
        agent = FactoryTestAgent.create_with_context(self.test_context)

        # Golden Path compatibility methods
        compatibility_methods = [
            'execute_with_retry',
            'execute_with_fallback',
            'cleanup',
            'enable_websocket_test_mode'
        ]

        for method_name in compatibility_methods:
            assert hasattr(agent, method_name)
            assert callable(getattr(agent, method_name))

        # Legacy properties for test compatibility
        assert hasattr(agent, 'websocket_emitter')  # Property exists

        # Health status methods
        assert hasattr(agent, 'get_health_status')
        assert hasattr(agent, 'get_circuit_breaker_status')

        health = agent.get_health_status()
        assert isinstance(health, dict)
        assert "agent_name" in health