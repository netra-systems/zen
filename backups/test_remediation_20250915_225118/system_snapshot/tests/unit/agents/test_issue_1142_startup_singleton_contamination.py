"""
Issue #1142: SSOT Incomplete Migration Agent Factory Singleton Blocking Golden Path - Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Enterprise - Core golden path reliability for $500K+ ARR
- Business Goal: Golden Path Stability - Fix startup singleton contamination blocking user flow
- Value Impact: Ensures startup sequence doesn't contaminate per-request factory isolation
- Strategic Impact: Removes critical blocker for multi-user production deployment

CRITICAL ISSUE DESCRIPTION (Issue #1142):
- Startup singleton contamination breaking per-request factory isolation
- get_agent_instance_factory() singleton created at startup contaminates all subsequent requests
- Golden path blocked because first request contaminates factory for all users
- Expected: Tests should FAIL initially to prove startup contamination exists

Test Coverage:
1. Startup factory singleton contamination during app initialization
2. First request contaminating factory for subsequent users
3. Golden path blocking due to startup state pollution
4. Per-request factory isolation failure due to startup contamination
5. WebSocket emitter contamination from startup factory configuration
6. User context contamination during application startup sequence
7. Configuration state pollution from startup factory initialization
8. Multi-user golden path failure due to startup singleton pattern

ARCHITECTURE ALIGNMENT:
- Tests prove startup sequence violates USER_CONTEXT_ARCHITECTURE.md factory isolation
- Validates that startup singleton patterns break per-request isolation
- Demonstrates golden path blocking issues from startup contamination
- Shows critical $500K+ ARR user flow interruption from startup patterns
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

# Import agent factory components to test startup singleton contamination
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


@pytest.mark.unit
class Issue1142StartupSingletonContaminationTests(SSotAsyncTestCase):
    """
    Unit tests proving startup singleton contamination blocking golden path.

    These tests should FAIL initially, proving that startup singleton contamination
    breaks per-request factory isolation and blocks the golden path.
    Success means the startup contamination problem has been fixed.
    """

    def setup_method(self, method):
        """Set up test environment with clean state."""
        super().setup_method(method)

        # Clear singleton state to simulate clean startup
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        factory_module._factory_instance = None

        # Create test data for multi-user scenarios
        self.startup_user_id = "startup_user_contamination"
        self.golden_path_user1_id = "golden_path_user_1"
        self.golden_path_user2_id = "golden_path_user_2"
        self.thread1_id = "thread_startup_test_1"
        self.thread2_id = "thread_startup_test_2"
        self.run1_id = f"run_startup_test_1_{int(time.time())}"
        self.run2_id = f"run_startup_test_2_{int(time.time())}"

        # Mock infrastructure components
        self.mock_websocket_bridge = MagicMock(spec=AgentWebSocketBridge)
        self.mock_agent_registry = MagicMock(spec=AgentRegistry)
        self.mock_llm_manager = MagicMock()
        self.mock_tool_dispatcher = MagicMock()

    async def test_startup_factory_singleton_contamination_blocks_golden_path(self):
        """
        CRITICAL: Test that startup factory singleton contamination blocks golden path.

        This test should FAIL initially - proving that get_agent_instance_factory()
        called during startup creates contaminated singleton affecting all users.

        Expected FAILURE: Startup factory contamination breaks per-request isolation.
        Expected FIX: Startup should not create singleton factory affecting all requests.
        """
        # SIMULATE STARTUP SEQUENCE: App calls get_agent_instance_factory() during startup
        print("🚨 SIMULATING APPLICATION STARTUP SEQUENCE...")

        # This is what happens during app startup - creates singleton with startup config
        startup_factory = get_agent_instance_factory()

        # Configure factory during startup with startup-specific infrastructure
        startup_factory.configure(
            websocket_bridge=self.mock_websocket_bridge,
            agent_registry=self.mock_agent_registry,
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )

        # Add startup contamination state that shouldn't affect user requests
        startup_factory._startup_contamination_marker = "STARTUP_CONFIGURED"
        startup_factory._startup_user_id = self.startup_user_id

        print("🚨 STARTUP FACTORY CONFIGURED WITH CONTAMINATION STATE")

        # NOW SIMULATE GOLDEN PATH: User 1 requests agent factory
        print("🚨 GOLDEN PATH USER 1 REQUESTING AGENT FACTORY...")

        user1_factory = get_agent_instance_factory()

        # CRITICAL TEST: User 1 should NOT get the startup-contaminated factory
        # This assertion should FAIL initially, proving startup contamination problem
        assert not hasattr(user1_factory, '_startup_contamination_marker'), (
            f"STARTUP CONTAMINATION BLOCKS GOLDEN PATH: User 1 factory has startup contamination marker. "
            f"Factory ID: {id(user1_factory)}. This means startup singleton affects all users."
        )

        # Check if user 1 inherited startup configuration state
        startup_websocket_bridge = getattr(user1_factory, '_websocket_bridge', None)
        assert startup_websocket_bridge is not self.mock_websocket_bridge, (
            f"STARTUP CONFIG CONTAMINATION: User 1 inherited startup WebSocket bridge. "
            f"Bridge ID: {id(startup_websocket_bridge)}. Golden path blocked by startup config."
        )

        # NOW SIMULATE GOLDEN PATH: User 2 requests agent factory
        print("🚨 GOLDEN PATH USER 2 REQUESTING AGENT FACTORY...")

        user2_factory = get_agent_instance_factory()

        # CRITICAL TEST: User 2 should also NOT get startup contamination
        assert not hasattr(user2_factory, '_startup_contamination_marker'), (
            f"STARTUP CONTAMINATION BLOCKS GOLDEN PATH: User 2 factory has startup contamination marker. "
            f"Factory ID: {id(user2_factory)}. Multiple users affected by startup singleton."
        )

        # CRITICAL TEST: Users should get DIFFERENT factory instances (no singleton)
        assert user1_factory is not user2_factory, (
            f"SINGLETON BLOCKS GOLDEN PATH: Same factory instance ({id(user1_factory)}) "
            f"serves multiple users. Golden path requires per-request isolation."
        )

        print("EXPECTED FAILURE: Startup singleton contamination should block golden path initially")

    async def test_first_request_contamination_affects_subsequent_users(self):
        """
        CRITICAL: Test that first request contamination affects subsequent users.

        This test should FAIL initially - proving that the first user request
        contaminates the singleton factory, affecting all subsequent users.

        Expected FAILURE: First request state leaks to all subsequent users.
        Expected FIX: Each request should get isolated factory with no state leakage.
        """
        # Clear singleton to simulate fresh startup
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        factory_module._factory_instance = None

        # FIRST REQUEST: User 1 makes the first request after startup
        print("🚨 FIRST REQUEST AFTER STARTUP - USER 1...")

        user1_factory = get_agent_instance_factory()
        user1_factory.configure(websocket_bridge=self.mock_websocket_bridge)

        # User 1 adds request-specific state that shouldn't leak
        user1_factory._user_specific_state = {
            'user_id': self.golden_path_user1_id,
            'confidential_data': 'user1_private_business_data',
            'session_config': {'privacy_level': 'high', 'data_access': 'restricted'}
        }

        # Create user execution context for user 1
        user1_context = await user1_factory.create_user_execution_context(
            user_id=self.golden_path_user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id,
            metadata={'request_type': 'confidential_analysis'}
        )

        print("🚨 USER 1 STATE ADDED TO FACTORY - CONTAMINATION SOURCE")

        # SECOND REQUEST: User 2 makes subsequent request
        print("🚨 SUBSEQUENT REQUEST - USER 2...")

        user2_factory = get_agent_instance_factory()

        # CRITICAL TEST: User 2 should NOT get a factory contaminated by user 1
        # This assertion should FAIL initially, proving contamination problem
        assert user1_factory is not user2_factory, (
            f"FIRST REQUEST CONTAMINATION: Same factory instance ({id(user1_factory)}) "
            f"serves user 1 and user 2. First request contamination affects subsequent users."
        )

        # Check for state leakage from user 1 to user 2
        user2_contaminated_state = getattr(user2_factory, '_user_specific_state', None)

        if user2_contaminated_state:
            user1_confidential = user2_contaminated_state.get('confidential_data', '')
            assert 'user1_private_business_data' not in user1_confidential, (
                f"CONFIDENTIAL DATA LEAKAGE: User 2 factory contains user 1's confidential data: "
                f"'{user1_confidential}'. First request contamination causes data breach."
            )

        # Create user 2 context and verify isolation
        user2_context = await user2_factory.create_user_execution_context(
            user_id=self.golden_path_user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id,
            metadata={'request_type': 'public_analysis'}
        )

        # Verify user context isolation
        assert user1_context.user_id != user2_context.user_id, (
            "USER CONTEXT CONTAMINATION: User contexts share user_id. "
            "First request contamination affects user context creation."
        )

        print("EXPECTED FAILURE: First request contamination should affect subsequent users initially")

    async def test_golden_path_websocket_emitter_contamination_from_startup(self):
        """
        CRITICAL: Test WebSocket emitter contamination from startup blocking golden path.

        This test should FAIL initially - proving that startup WebSocket configuration
        contaminates emitters for all golden path user requests.

        Expected FAILURE: All users get same WebSocket emitter from startup.
        Expected FIX: Each user should get isolated WebSocket emitter.
        """
        # SIMULATE STARTUP: Configure WebSocket bridge during startup
        startup_factory = get_agent_instance_factory()
        startup_factory.configure(websocket_bridge=self.mock_websocket_bridge)

        # Add startup WebSocket emitter configuration
        startup_emitter_config = {
            'startup_marker': 'STARTUP_WEBSOCKET_CONFIG',
            'broadcast_mode': 'all_users',  # THIS IS THE CONTAMINATION
            'global_events': True
        }

        # Store startup configuration in factory
        startup_factory._startup_websocket_config = startup_emitter_config

        print("🚨 STARTUP WEBSOCKET CONFIGURATION CONTAMINATING FACTORY")

        # GOLDEN PATH: User 1 creates WebSocket emitter
        user1_context = UserExecutionContext.from_request_supervisor(
            user_id=self.golden_path_user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )

        user1_factory = get_agent_instance_factory()  # Gets contaminated startup factory
        user1_emitter_context = await user1_factory.create_user_execution_context(
            user_id=self.golden_path_user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )

        # Check if user 1 inherited startup WebSocket configuration
        startup_config = getattr(user1_factory, '_startup_websocket_config', None)

        # CRITICAL TEST: User 1 should NOT inherit startup WebSocket configuration
        # This assertion should FAIL initially, proving startup contamination
        assert startup_config is None, (
            f"STARTUP WEBSOCKET CONTAMINATION: User 1 inherited startup WebSocket config: "
            f"{startup_config}. Golden path blocked by startup WebSocket contamination."
        )

        # GOLDEN PATH: User 2 creates WebSocket emitter
        user2_context = UserExecutionContext.from_request_supervisor(
            user_id=self.golden_path_user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )

        user2_factory = get_agent_instance_factory()  # Also gets contaminated startup factory
        user2_emitter_context = await user2_factory.create_user_execution_context(
            user_id=self.golden_path_user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )

        # CRITICAL TEST: User 2 should also NOT inherit startup configuration
        startup_config_user2 = getattr(user2_factory, '_startup_websocket_config', None)
        assert startup_config_user2 is None, (
            f"STARTUP WEBSOCKET CONTAMINATION: User 2 inherited startup WebSocket config: "
            f"{startup_config_user2}. Multiple users affected by startup contamination."
        )

        # CRITICAL TEST: Both users should have isolated WebSocket contexts
        assert user1_emitter_context.user_id != user2_emitter_context.user_id, (
            "WEBSOCKET EMITTER CONTAMINATION: Users share WebSocket emitter context. "
            "Startup contamination affects WebSocket event delivery."
        )

        print("EXPECTED FAILURE: Startup WebSocket contamination should block golden path initially")

    async def test_startup_configuration_state_pollution_blocks_per_request_isolation(self):
        """
        CRITICAL: Test startup configuration pollution blocking per-request isolation.

        This test should FAIL initially - proving that startup configuration state
        pollutes all per-request factory instances, breaking isolation.

        Expected FAILURE: Startup config state affects all per-request factories.
        Expected FIX: Per-request factories should have isolated configuration.
        """
        # STARTUP: Configure factory with startup-specific settings
        startup_factory = get_agent_instance_factory()

        # Startup configuration that should NOT affect user requests
        startup_config = {
            'max_concurrent_per_user': 10,  # Startup setting
            'execution_timeout': 300,       # Startup setting
            'enable_debug_mode': True,      # Startup setting
            'startup_environment': 'production',
            'global_rate_limits': {'all_users': 1000}
        }

        # Apply startup configuration to singleton factory
        startup_factory._max_concurrent_per_user = startup_config['max_concurrent_per_user']
        startup_factory._execution_timeout = startup_config['execution_timeout']
        startup_factory._startup_debug_mode = startup_config['enable_debug_mode']
        startup_factory._startup_config_marker = 'STARTUP_CONFIGURED'

        print("🚨 STARTUP CONFIGURATION APPLIED TO SINGLETON FACTORY")

        # USER REQUEST 1: Should get per-request factory with isolated config
        user1_factory = get_agent_instance_factory()

        # CRITICAL TEST: User 1 should NOT inherit startup configuration
        # This assertion should FAIL initially, proving startup pollution
        user1_max_concurrent = getattr(user1_factory, '_max_concurrent_per_user', None)
        startup_max_concurrent = startup_config['max_concurrent_per_user']

        assert user1_max_concurrent != startup_max_concurrent, (
            f"STARTUP CONFIG POLLUTION: User 1 inherited startup max_concurrent setting "
            f"({startup_max_concurrent}). Per-request isolation blocked by startup config."
        )

        # Check for startup marker contamination
        startup_marker = getattr(user1_factory, '_startup_config_marker', None)
        assert startup_marker is None, (
            f"STARTUP MARKER POLLUTION: User 1 factory has startup config marker: "
            f"'{startup_marker}'. This proves startup configuration contamination."
        )

        # USER REQUEST 2: Should also get isolated factory configuration
        user2_factory = get_agent_instance_factory()

        # CRITICAL TEST: User 2 should also NOT inherit startup configuration
        user2_timeout = getattr(user2_factory, '_execution_timeout', None)
        startup_timeout = startup_config['execution_timeout']

        assert user2_timeout != startup_timeout, (
            f"STARTUP TIMEOUT POLLUTION: User 2 inherited startup execution timeout "
            f"({startup_timeout}s). Multiple users affected by startup configuration."
        )

        # Check debug mode contamination
        user2_debug_mode = getattr(user2_factory, '_startup_debug_mode', None)
        assert user2_debug_mode is None, (
            f"STARTUP DEBUG POLLUTION: User 2 inherited startup debug mode. "
            f"This affects user request behavior with startup settings."
        )

        # CRITICAL TEST: Users should get different factory instances
        assert user1_factory is not user2_factory, (
            f"SINGLETON POLLUTION: Same factory instance ({id(user1_factory)}) "
            f"serves multiple users with startup configuration contamination."
        )

        print("EXPECTED FAILURE: Startup configuration pollution should block per-request isolation initially")

    async def test_concurrent_golden_path_users_affected_by_startup_singleton(self):
        """
        CRITICAL: Test concurrent golden path users affected by startup singleton.

        This test should FAIL initially - proving that multiple concurrent users
        in the golden path are all affected by the same startup singleton factory.

        Expected FAILURE: All concurrent users share startup singleton factory.
        Expected FIX: Each concurrent user should get isolated factory instance.
        """
        # Clear singleton and configure startup factory
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        factory_module._factory_instance = None

        # STARTUP: Create and configure singleton factory
        startup_factory = get_agent_instance_factory()
        startup_factory.configure(
            websocket_bridge=self.mock_websocket_bridge,
            llm_manager=self.mock_llm_manager
        )

        # Add concurrent request tracking to startup factory
        startup_factory._concurrent_request_counter = 0
        startup_factory._concurrent_users = set()

        print("🚨 STARTUP SINGLETON FACTORY CONFIGURED FOR CONCURRENT TESTING")

        async def simulate_concurrent_golden_path_user(user_id: str, thread_id: str, run_id: str):
            """Simulate a concurrent user in the golden path."""
            print(f"🚨 CONCURRENT USER {user_id} ENTERING GOLDEN PATH...")

            # User gets factory (should be isolated, but currently singleton)
            user_factory = get_agent_instance_factory()

            # Track this user in the factory
            user_factory._concurrent_request_counter += 1
            user_factory._concurrent_users.add(user_id)

            # Create user context
            user_context = await user_factory.create_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )

            return {
                'user_id': user_id,
                'factory_id': id(user_factory),
                'request_counter': user_factory._concurrent_request_counter,
                'concurrent_users': user_factory._concurrent_users.copy(),
                'context': user_context
            }

        # Launch concurrent golden path users
        user_tasks = [
            simulate_concurrent_golden_path_user(
                f"golden_path_user_{i}",
                f"thread_concurrent_{i}",
                f"run_concurrent_{i}_{int(time.time())}"
            )
            for i in range(1, 4)  # 3 concurrent users
        ]

        # Execute all concurrent users simultaneously
        concurrent_results = await asyncio.gather(*user_tasks)

        print("🚨 CONCURRENT GOLDEN PATH USERS EXECUTED")

        # CRITICAL TEST: Each user should get DIFFERENT factory instances
        factory_ids = [result['factory_id'] for result in concurrent_results]
        unique_factory_ids = set(factory_ids)

        # This assertion should FAIL initially, proving singleton contamination
        assert len(unique_factory_ids) == len(concurrent_results), (
            f"CONCURRENT SINGLETON CONTAMINATION: {len(concurrent_results)} users share "
            f"{len(unique_factory_ids)} factory instances. Factory IDs: {factory_ids}. "
            f"Golden path requires isolated factories for concurrent users."
        )

        # Check concurrent user contamination
        for i, result in enumerate(concurrent_results):
            user_id = result['user_id']
            concurrent_users = result['concurrent_users']

            # Each user should only see themselves, not other concurrent users
            other_users = concurrent_users - {user_id}
            assert len(other_users) == 0, (
                f"CONCURRENT USER CONTAMINATION: User {user_id} sees other concurrent users: "
                f"{other_users}. Singleton factory shares state between concurrent golden path users."
            )

        # Check request counter contamination
        for i, result in enumerate(concurrent_results):
            request_counter = result['request_counter']
            expected_counter = 1  # Each user should see only their own request

            # This will fail if users share the singleton factory
            assert request_counter == expected_counter, (
                f"REQUEST COUNTER CONTAMINATION: User sees request counter {request_counter}, "
                f"expected {expected_counter}. Singleton factory accumulates concurrent user requests."
            )

        print("EXPECTED FAILURE: Concurrent golden path users should be affected by startup singleton initially")

    async def test_memory_reference_contamination_from_startup_factory(self):
        """
        CRITICAL: Test memory reference contamination from startup factory.

        This test should FAIL initially - proving that startup factory creates
        shared memory references affecting all subsequent user requests.

        Expected FAILURE: Users share memory references from startup factory.
        Expected FIX: Each user should get completely isolated memory references.
        """
        # STARTUP: Create factory with shared memory references
        startup_factory = get_agent_instance_factory()

        # Create shared objects during startup (THE CONTAMINATION SOURCE)
        shared_memory_objects = {
            'agent_cache': {},
            'user_sessions': {},
            'global_config': {
                'database_pool': MagicMock(),
                'redis_connection': MagicMock(),
                'llm_client': MagicMock()
            }
        }

        # Store shared objects in startup factory
        startup_factory._shared_memory_objects = shared_memory_objects
        startup_factory._global_object_cache = {}

        print("🚨 STARTUP FACTORY CONFIGURED WITH SHARED MEMORY OBJECTS")

        # USER 1: Golden path request gets contaminated factory
        user1_factory = get_agent_instance_factory()

        # User 1 uses factory and creates objects
        user1_context = await user1_factory.create_user_execution_context(
            user_id=self.golden_path_user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )

        # Add user 1's data to shared objects (simulating real usage)
        user1_shared_objects = getattr(user1_factory, '_shared_memory_objects', {})
        if 'user_sessions' in user1_shared_objects:
            user1_shared_objects['user_sessions'][self.golden_path_user1_id] = {
                'confidential_session_data': 'user1_private_session_info',
                'business_data': {'revenue': 500000, 'client_list': ['confidential_client_1']}
            }

        print("🚨 USER 1 DATA ADDED TO SHARED MEMORY OBJECTS")

        # USER 2: Golden path request gets same contaminated factory
        user2_factory = get_agent_instance_factory()

        # CRITICAL TEST: User 2 should NOT get same memory objects as user 1
        user2_shared_objects = getattr(user2_factory, '_shared_memory_objects', {})

        # This assertion should FAIL initially, proving memory contamination
        assert user1_shared_objects is not user2_shared_objects, (
            f"MEMORY REFERENCE CONTAMINATION: User 2 shares memory objects with user 1. "
            f"Object ID: {id(user1_shared_objects)}. This causes memory state contamination."
        )

        # Check for specific data contamination
        if user2_shared_objects and 'user_sessions' in user2_shared_objects:
            user1_session_data = user2_shared_objects['user_sessions'].get(self.golden_path_user1_id)

            assert user1_session_data is None, (
                f"SESSION DATA CONTAMINATION: User 2 can access user 1's session data: "
                f"{user1_session_data}. Shared memory references cause data leakage."
            )

        # Check global config contamination
        user1_global_config = user1_shared_objects.get('global_config', {})
        user2_global_config = user2_shared_objects.get('global_config', {})

        if user1_global_config and user2_global_config:
            # Users should NOT share the same database pool instance
            user1_db_pool = user1_global_config.get('database_pool')
            user2_db_pool = user2_global_config.get('database_pool')

            assert user1_db_pool is not user2_db_pool, (
                f"DATABASE POOL CONTAMINATION: Users share database pool instance. "
                f"Pool ID: {id(user1_db_pool)}. This causes database session contamination."
            )

        # Test weak reference isolation
        if user1_shared_objects:
            user1_weak_ref = weakref.ref(user1_shared_objects)
            user2_weak_ref = weakref.ref(user2_shared_objects) if user2_shared_objects else None

            if user2_weak_ref:
                assert user1_weak_ref() is not user2_weak_ref(), (
                    "WEAK REFERENCE CONTAMINATION: Users share the same memory object references. "
                    "This prevents proper garbage collection and memory isolation."
                )

        print("EXPECTED FAILURE: Memory reference contamination should affect all users initially")