"""
Issue #1116: Agent Instance Factory Singleton Pattern Violations - Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Enterprise - Multi-user production deployment critical for $500K+ ARR
- Business Goal: Security & Compliance - Prevent data leakage and context contamination
- Value Impact: Ensures agent factories create isolated instances with no shared state
- Strategic Impact: Foundation for enterprise-grade multi-tenant deployment

CRITICAL: These tests should FAIL initially to prove the singleton pattern problem exists.
They validate that singleton patterns in agent factory cause user context contamination.

Test Coverage:
1. Agent factory singleton contamination between users
2. WebSocket emitter sharing across user contexts 
3. Execution context state leakage between concurrent requests
4. Tool dispatcher singleton sharing violations
5. LLM manager singleton sharing between users
6. Agent class registry contamination
7. Memory reference sharing between factory instances
8. Configuration state pollution across user contexts

ARCHITECTURE ALIGNMENT:
- Tests prove USER_CONTEXT_ARCHITECTURE.md factory isolation violations
- Validates that singleton patterns break multi-user execution
- Demonstrates enterprise security requirements failures
- Shows $500K+ ARR customer isolation requirement violations
"""

import asyncio
import pytest
import threading
import time
import uuid
import weakref
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT imports following architecture patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import agent factory components to test singleton violations
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory, 
    get_agent_instance_factory,
    configure_agent_instance_factory,
    create_agent_instance_factory
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry

# Mock agent classes for testing
class MockAgent:
    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.llm_manager = None
        self.tool_dispatcher = None
        self.websocket_bridge = None
        self.execution_context = None
        self.state_data = {}
        
    def set_websocket_bridge(self, bridge, run_id):
        self.websocket_bridge = bridge
        self.run_id = run_id


@pytest.mark.unit
class AgentInstanceFactorySingletonViolations1116Tests(SSotAsyncTestCase):
    """
    Unit tests proving singleton pattern violations in AgentInstanceFactory.
    
    These tests should FAIL initially, proving the singleton contamination problem.
    Success means the singleton problem has been fixed.
    """
    
    def setup_method(self, method):
        """Set up test environment with clean state."""
        super().setup_method(method)
        
        # Clear any singleton state to ensure clean testing
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        factory_module._factory_instance = None
        
        # Create test data
        self.user1_id = "user_singleton_test_1"
        self.user2_id = "user_singleton_test_2"
        self.thread1_id = "thread_singleton_test_1"
        self.thread2_id = "thread_singleton_test_2"
        self.run1_id = f"run_singleton_test_1_{int(time.time())}"
        self.run2_id = f"run_singleton_test_2_{int(time.time())}"
        
        # Mock infrastructure components that would normally be singletons
        self.mock_websocket_bridge = MagicMock(spec=AgentWebSocketBridge)
        self.mock_agent_registry = MagicMock(spec=AgentRegistry)
        self.mock_llm_manager = MagicMock()
        self.mock_tool_dispatcher = MagicMock()
        
    async def test_singleton_factory_contamination_between_users(self):
        """
        CRITICAL: Test that singleton factory causes user contamination.
        
        This test should FAIL initially - proving that using get_agent_instance_factory()
        creates a singleton that shares state between different users.
        
        Expected FAILURE: Same factory instance serves multiple users, causing contamination.
        Expected FIX: Each user should get isolated factory instances.
        """
        # Get singleton factory for user 1
        factory1 = get_agent_instance_factory()
        
        # Configure factory with user 1's infrastructure
        factory1.configure(
            websocket_bridge=self.mock_websocket_bridge,
            agent_registry=self.mock_agent_registry,
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )
        
        # Get singleton factory for user 2 (should be SAME instance - THE PROBLEM)
        factory2 = get_agent_instance_factory()
        
        # CRITICAL TEST: These should be DIFFERENT instances for proper isolation
        # This assertion should FAIL initially, proving the singleton problem
        assert factory1 is not factory2, (
            f"SINGLETON VIOLATION: Same factory instance ({id(factory1)}) "
            f"serves multiple users - this causes user context contamination. "
            f"Each user must have isolated factory instances."
        )
        
        # Additional validation: Configuration from user1 should not affect user2
        assert factory2._websocket_bridge is None, (
            "SINGLETON VIOLATION: User 2 factory inherits user 1's WebSocket bridge - "
            "this causes WebSocket event mis-delivery between users"
        )
        
        print("EXPECTED FAILURE: Singleton factory contamination test should fail initially")

    async def test_websocket_emitter_sharing_violation(self):
        """
        CRITICAL: Test WebSocket emitter sharing between users via singleton factory.
        
        This test should FAIL initially - proving that WebSocket emitters are shared
        through singleton factory patterns, causing event mis-delivery.
        
        Expected FAILURE: Same WebSocket emitter serves multiple users.
        Expected FIX: Each user should get isolated WebSocket emitters.
        """
        # Create user contexts
        context1 = UserExecutionContext.from_request_supervisor(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )
        context2 = UserExecutionContext.from_request_supervisor(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )
        
        # Get singleton factory
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create contexts for both users using same factory
        user1_context = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )
        user2_context = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )
        
        # Check WebSocket emitter isolation
        emitter1_key = f"{self.user1_id}_{self.thread1_id}_{self.run1_id}_emitter"
        emitter2_key = f"{self.user2_id}_{self.thread2_id}_{self.run2_id}_emitter"
        
        if hasattr(factory, '_websocket_emitters'):
            emitter1 = factory._websocket_emitters.get(emitter1_key)
            emitter2 = factory._websocket_emitters.get(emitter2_key)
            
            if emitter1 and emitter2:
                # CRITICAL TEST: Emitters should be DIFFERENT instances
                # This assertion should FAIL initially, proving shared emitter problem
                assert emitter1 is not emitter2, (
                    f"WEBSOCKET VIOLATION: Same emitter instance ({id(emitter1)}) "
                    f"serves multiple users - this causes event mis-delivery. "
                    f"Each user must have isolated WebSocket emitters."
                )
                
                # Validate user isolation in emitters
                assert getattr(emitter1, 'user_id', None) != getattr(emitter2, 'user_id', None), (
                    "WEBSOCKET VIOLATION: WebSocket emitters share user_id - "
                    "this causes events to be delivered to wrong users"
                )
        
        print("EXPECTED FAILURE: WebSocket emitter sharing test should fail initially")

    async def test_execution_context_state_leakage(self):
        """
        CRITICAL: Test execution context state leakage through singleton factory.
        
        This test should FAIL initially - proving that execution contexts leak
        state between users through shared factory instances.
        
        Expected FAILURE: User 2 sees state from user 1's execution context.
        Expected FIX: Complete state isolation between user contexts.
        """
        # Get singleton factory
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create context for user 1 and add some state
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id,
            metadata={"secret_data": "user1_confidential", "session_state": {"page": 1}}
        )
        
        # Store user 1's state in factory (simulating real usage)
        if not hasattr(factory, '_user_state_data'):
            factory._user_state_data = {}
        
        factory._user_state_data[self.user1_id] = {
            "confidential_info": "user1_private_data",
            "execution_history": ["action1", "action2"],
            "memory_references": {"cached_objects": [MockAgent("user1_agent")]}
        }
        
        # Create context for user 2
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id,
            metadata={"public_data": "user2_normal"}
        )
        
        # CRITICAL TEST: User 2 should NOT see user 1's state
        # This assertion should FAIL initially if state is shared
        user2_state = factory._user_state_data.get(self.user2_id, {})
        user1_confidential = factory._user_state_data.get(self.user1_id, {}).get("confidential_info")
        
        assert user1_confidential not in str(user2_state), (
            f"STATE LEAKAGE VIOLATION: User 2 can access user 1's confidential data: "
            f"'{user1_confidential}' found in user 2's state. "
            f"This is a critical security violation."
        )
        
        # Check for memory reference contamination
        user1_objects = factory._user_state_data.get(self.user1_id, {}).get("memory_references", {})
        if user1_objects:
            # User 2 should not have references to user 1's objects
            for obj_list in user1_objects.values():
                for obj in obj_list:
                    # Check if the object is somehow accessible to user 2
                    # This would be a critical memory contamination issue
                    user2_can_access = hasattr(obj, 'agent_id') and 'user1' in getattr(obj, 'agent_id', '')
                    
                    assert not user2_can_access or obj not in user2_state.get("memory_references", {}).get("cached_objects", []), (
                        f"MEMORY CONTAMINATION: User 2 has access to user 1's object references. "
                        f"This causes cross-user data contamination."
                    )
        
        print("EXPECTED FAILURE: Execution context state leakage test should fail initially")

    async def test_tool_dispatcher_singleton_sharing_violation(self):
        """
        CRITICAL: Test tool dispatcher singleton sharing between users.
        
        This test should FAIL initially - proving that tool dispatcher singleton
        is shared between users, causing tool execution contamination.
        
        Expected FAILURE: Same tool dispatcher serves multiple users.
        Expected FIX: Each user should get isolated tool dispatcher context.
        """
        # Configure singleton factory with shared tool dispatcher
        factory = get_agent_instance_factory()
        
        # Create mock tool dispatcher with user-specific state
        mock_tool_dispatcher = MagicMock()
        mock_tool_dispatcher.user_context = None
        mock_tool_dispatcher.execution_state = {}
        
        factory.configure(
            websocket_bridge=self.mock_websocket_bridge,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Create contexts for both users
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )
        
        # Create agents for both users - they should get the SAME tool dispatcher (THE PROBLEM)
        agent1 = MockAgent("user1_agent")
        agent2 = MockAgent("user2_agent")
        
        # Simulate agent creation process that would set tool dispatcher
        if hasattr(factory, '_tool_dispatcher'):
            agent1.tool_dispatcher = factory._tool_dispatcher
            agent2.tool_dispatcher = factory._tool_dispatcher
        
        # CRITICAL TEST: Tool dispatchers should be DIFFERENT instances for isolation
        # This assertion should FAIL initially, proving the shared dispatcher problem
        assert agent1.tool_dispatcher is not agent2.tool_dispatcher, (
            f"TOOL DISPATCHER VIOLATION: Same tool dispatcher instance "
            f"({id(agent1.tool_dispatcher)}) serves multiple users. "
            f"This causes tool execution contamination between users."
        )
        
        # Test tool execution isolation
        if agent1.tool_dispatcher and agent2.tool_dispatcher:
            # Set user-specific state in tool dispatchers
            agent1.tool_dispatcher.execution_state['user_data'] = 'user1_tools'
            
            # User 2's tool dispatcher should not see user 1's state
            user2_tool_state = getattr(agent2.tool_dispatcher, 'execution_state', {})
            assert 'user1_tools' not in str(user2_tool_state), (
                "TOOL ISOLATION VIOLATION: User 2's tool dispatcher contains user 1's state - "
                "this causes tool execution cross-contamination"
            )
        
        print("EXPECTED FAILURE: Tool dispatcher singleton sharing test should fail initially")

    async def test_llm_manager_singleton_sharing_violation(self):
        """
        CRITICAL: Test LLM manager singleton sharing between users.
        
        This test should FAIL initially - proving that LLM manager singleton
        is shared between users, causing AI conversation contamination.
        
        Expected FAILURE: Same LLM manager serves multiple users with shared context.
        Expected FIX: Each user should get isolated LLM manager context.
        """
        # Configure singleton factory with shared LLM manager
        factory = get_agent_instance_factory()
        
        # Create mock LLM manager with conversation state
        mock_llm_manager = MagicMock()
        mock_llm_manager.conversation_history = []
        mock_llm_manager.user_preferences = {}
        mock_llm_manager.context_memory = {}
        
        factory.configure(
            websocket_bridge=self.mock_websocket_bridge,
            llm_manager=mock_llm_manager
        )
        
        # Create contexts for both users
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )
        
        # Create agents for both users - they should get the SAME LLM manager (THE PROBLEM)
        agent1 = MockAgent("user1_agent")
        agent2 = MockAgent("user2_agent")
        
        # Simulate agent creation process that would set LLM manager
        if hasattr(factory, '_llm_manager'):
            agent1.llm_manager = factory._llm_manager
            agent2.llm_manager = factory._llm_manager
        
        # CRITICAL TEST: LLM managers should be DIFFERENT instances for isolation
        # This assertion should FAIL initially, proving the shared LLM manager problem
        assert agent1.llm_manager is not agent2.llm_manager, (
            f"LLM MANAGER VIOLATION: Same LLM manager instance "
            f"({id(agent1.llm_manager)}) serves multiple users. "
            f"This causes AI conversation contamination between users."
        )
        
        # Test conversation isolation
        if agent1.llm_manager and agent2.llm_manager:
            # Add user 1's conversation to LLM manager
            agent1.llm_manager.conversation_history.append({
                'user_id': self.user1_id,
                'message': 'user1_confidential_conversation',
                'context': 'private_business_data'
            })
            
            # User 2's LLM manager should not see user 1's conversation
            user2_conversations = getattr(agent2.llm_manager, 'conversation_history', [])
            user1_private_data = any(
                'user1_confidential' in str(conv) 
                for conv in user2_conversations
            )
            
            assert not user1_private_data, (
                "LLM CONVERSATION VIOLATION: User 2's LLM manager contains user 1's "
                "confidential conversation data - this causes AI response contamination"
            )
        
        print("EXPECTED FAILURE: LLM manager singleton sharing test should fail initially")

    async def test_agent_class_registry_contamination(self):
        """
        CRITICAL: Test agent class registry contamination between users.
        
        This test should FAIL initially - proving that agent class registry
        shares state between users, causing agent creation contamination.
        
        Expected FAILURE: User-specific agent configurations leak between users.
        Expected FIX: Agent registry should maintain user-specific isolation.
        """
        # Create mock agent class registry with user-specific state
        mock_registry = MagicMock(spec=AgentClassRegistry)
        mock_registry.user_agent_configs = {}
        mock_registry.agent_instances_cache = {}
        
        # Configure singleton factory
        factory = get_agent_instance_factory()
        factory.configure(
            agent_class_registry=mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Simulate user 1 registering custom agent configuration
        user1_config = {
            'agent_type': 'DataAgent',
            'custom_settings': {'privacy_level': 'high', 'data_access': 'restricted'},
            'user_preferences': {'language': 'en', 'complexity': 'advanced'}
        }
        
        if hasattr(factory, '_agent_class_registry'):
            factory._agent_class_registry.user_agent_configs[self.user1_id] = user1_config
        
        # Create contexts for both users
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )
        
        # CRITICAL TEST: User 2 should NOT see user 1's agent configurations
        if hasattr(factory, '_agent_class_registry'):
            user2_should_not_have_config = factory._agent_class_registry.user_agent_configs.get(self.user2_id)
            user1_config_data = factory._agent_class_registry.user_agent_configs.get(self.user1_id, {})
            
            # This assertion should FAIL initially if configurations are shared
            assert user1_config_data not in [user2_should_not_have_config], (
                f"AGENT REGISTRY VIOLATION: User 2 has access to user 1's agent configuration: "
                f"{user1_config_data}. This causes agent behavior contamination."
            )
            
            # Check for configuration bleeding
            user1_privacy_level = user1_config.get('custom_settings', {}).get('privacy_level')
            user2_config = factory._agent_class_registry.user_agent_configs.get(self.user2_id, {})
            
            if user2_config and user1_privacy_level:
                user2_privacy = user2_config.get('custom_settings', {}).get('privacy_level')
                assert user2_privacy != user1_privacy_level, (
                    f"AGENT CONFIG BLEEDING: User 2 inherited user 1's privacy settings - "
                    f"this causes security configuration contamination"
                )
        
        print("EXPECTED FAILURE: Agent class registry contamination test should fail initially")

    async def test_memory_reference_sharing_violation(self):
        """
        CRITICAL: Test memory reference sharing between factory instances.
        
        This test should FAIL initially - proving that memory references are shared
        through singleton factory, causing object contamination between users.
        
        Expected FAILURE: Same object instances serve multiple users.
        Expected FIX: Each user should get completely isolated object instances.
        """
        # Get singleton factory
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create shared object that might be reused (THE PROBLEM)
        shared_config_object = {
            'database_settings': {'host': 'prod-db', 'user': 'admin'},
            'api_keys': {'openai': 'secret_key_123'},
            'cached_data': {'user_profiles': {}}
        }
        
        # Simulate factory storing this object for reuse
        if not hasattr(factory, '_shared_objects'):
            factory._shared_objects = {}
        
        factory._shared_objects['config'] = shared_config_object
        
        # Create contexts for both users
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )
        
        # Both users get references to the same object (THE PROBLEM)
        user1_config = factory._shared_objects.get('config')
        user2_config = factory._shared_objects.get('config')
        
        # CRITICAL TEST: Users should get DIFFERENT object instances
        # This assertion should FAIL initially, proving shared reference problem
        assert user1_config is not user2_config, (
            f"MEMORY SHARING VIOLATION: Same object instance ({id(user1_config)}) "
            f"is shared between users. This causes object state contamination."
        )
        
        # Test object mutation isolation
        if user1_config and user2_config:
            # User 1 modifies their config
            user1_config['cached_data']['user_profiles'][self.user1_id] = {
                'confidential': 'user1_private_profile'
            }
            
            # User 2 should NOT see user 1's modifications
            user2_profiles = user2_config.get('cached_data', {}).get('user_profiles', {})
            user1_private_data = user2_profiles.get(self.user1_id)
            
            assert user1_private_data is None, (
                f"OBJECT MUTATION VIOLATION: User 2 can see user 1's private profile data: "
                f"{user1_private_data}. This is caused by shared object references."
            )
        
        # Test weak reference isolation
        user1_weak_ref = weakref.ref(user1_config) if user1_config else None
        user2_weak_ref = weakref.ref(user2_config) if user2_config else None
        
        if user1_weak_ref and user2_weak_ref:
            # Weak references should point to DIFFERENT objects
            assert user1_weak_ref() is not user2_weak_ref(), (
                "WEAK REFERENCE VIOLATION: Users share the same underlying object - "
                "this prevents proper garbage collection and memory isolation"
            )
        
        print("EXPECTED FAILURE: Memory reference sharing test should fail initially")

    async def test_configuration_state_pollution_violation(self):
        """
        CRITICAL: Test configuration state pollution between user contexts.
        
        This test should FAIL initially - proving that configuration state
        is polluted between users through singleton factory patterns.
        
        Expected FAILURE: User 2 inherits configuration state from user 1.
        Expected FIX: Each user should have isolated configuration state.
        """
        # Get singleton factory
        factory = get_agent_instance_factory()
        
        # Create user 1 with specific configuration state
        user1_config = {
            'execution_timeout': 120,
            'max_concurrent_agents': 5,
            'enable_debug_mode': True,
            'api_rate_limits': {'openai': 100, 'claude': 50}
        }
        
        # Configure factory with user 1's settings (simulates real configuration)
        factory._max_concurrent_per_user = user1_config['max_concurrent_agents']
        factory._execution_timeout = user1_config['execution_timeout']
        
        if not hasattr(factory, '_user_configurations'):
            factory._user_configurations = {}
        
        factory._user_configurations[self.user1_id] = user1_config
        
        # Create context for user 1
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )
        
        # Create context for user 2 (should have default config, not user 1's)
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )
        
        # CRITICAL TEST: User 2 should NOT inherit user 1's configuration
        # This assertion should FAIL initially if configuration state is shared
        
        # Check factory-level configuration pollution
        user2_max_concurrent = factory._max_concurrent_per_user
        user1_max_concurrent = user1_config['max_concurrent_agents']
        
        # If user 2 gets user 1's configuration, this indicates pollution
        user2_inherited_user1_config = (user2_max_concurrent == user1_max_concurrent)
        
        # User 2 should get default configuration, not user 1's
        assert not user2_inherited_user1_config, (
            f"CONFIGURATION POLLUTION: User 2 inherited user 1's max_concurrent setting "
            f"({user1_max_concurrent}). User 2 should have default configuration."
        )
        
        # Check user-specific configuration isolation
        user2_config = factory._user_configurations.get(self.user2_id, {})
        user1_api_limits = user1_config.get('api_rate_limits', {})
        
        if user2_config:
            user2_api_limits = user2_config.get('api_rate_limits', {})
            config_contamination = any(
                limit in user2_api_limits.values() 
                for limit in user1_api_limits.values()
            )
            
            assert not config_contamination, (
                f"API LIMIT POLLUTION: User 2's API limits contain user 1's settings: "
                f"User1: {user1_api_limits}, User2: {user2_api_limits}. "
                f"This causes rate limiting cross-contamination."
            )
        
        # Check execution timeout pollution
        user2_timeout = factory._execution_timeout
        user1_timeout = user1_config['execution_timeout']
        
        assert user2_timeout != user1_timeout or user2_timeout == 60, (  # 60 is default
            f"TIMEOUT POLLUTION: User 2 inherited user 1's execution timeout "
            f"({user1_timeout}s). User 2 should have default timeout."
        )
        
        print("EXPECTED FAILURE: Configuration state pollution test should fail initially")