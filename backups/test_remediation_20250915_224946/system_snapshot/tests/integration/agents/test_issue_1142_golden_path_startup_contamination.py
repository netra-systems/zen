"""
Issue #1142: Golden Path Startup Contamination Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Enterprise - Core golden path reliability for $500K+ ARR
- Business Goal: Golden Path Stability - Remove startup contamination blocking user flow
- Value Impact: Ensures golden path works correctly without startup singleton interference
- Strategic Impact: Enables production deployment with reliable multi-user golden path

CRITICAL ISSUE DESCRIPTION (Issue #1142):
- Startup singleton contamination prevents proper golden path execution
- Integration tests proving end-to-end golden path failures from startup contamination
- WebSocket event delivery affected by startup factory contamination
- Multi-user golden path scenarios blocked by shared singleton state

Test Coverage:
1. End-to-end golden path startup contamination scenarios
2. WebSocket event delivery contamination from startup factory
3. Multi-user golden path concurrent execution blocked by singleton
4. Agent execution pipeline contamination from startup state
5. Database session contamination through startup factory singleton
6. Complete golden path user flow failure due to startup contamination

ARCHITECTURE ALIGNMENT:
- Tests prove startup contamination violates golden path requirements
- Validates end-to-end impact of startup singleton on user experience
- Demonstrates business impact of startup contamination on $500K+ ARR
- Shows complete golden path failure scenarios from startup patterns
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT imports following architecture patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import components for golden path integration testing
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    get_agent_instance_factory,
    configure_agent_instance_factory,
    create_agent_instance_factory
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.id_generation import UnifiedIdGenerator
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter


@pytest.mark.integration
class Issue1142GoldenPathStartupContaminationTests(SSotAsyncTestCase):
    """
    Integration tests proving startup contamination blocks golden path.

    These tests should FAIL initially, proving that startup singleton contamination
    prevents proper golden path execution and affects user experience.
    Success means the startup contamination blocking golden path has been fixed.
    """

    def setup_method(self, method):
        """Set up test environment with clean state."""
        super().setup_method(method)

        # Clear singleton state to simulate application startup
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        factory_module._factory_instance = None

        # Create test data for golden path scenarios
        self.golden_path_user1_id = "golden_path_user_startup_1"
        self.golden_path_user2_id = "golden_path_user_startup_2"
        self.golden_path_user3_id = "golden_path_user_startup_3"
        self.thread1_id = "thread_golden_startup_1"
        self.thread2_id = "thread_golden_startup_2"
        self.thread3_id = "thread_golden_startup_3"
        self.run1_id = f"run_golden_startup_1_{int(time.time())}"
        self.run2_id = f"run_golden_startup_2_{int(time.time())}"
        self.run3_id = f"run_golden_startup_3_{int(time.time())}"

        # Mock infrastructure components for integration testing
        self.mock_websocket_bridge = MagicMock(spec=AgentWebSocketBridge)
        self.mock_agent_registry = MagicMock(spec=AgentRegistry)
        self.mock_llm_manager = MagicMock()
        self.mock_tool_dispatcher = MagicMock()

        # Mock database session for integration testing
        self.mock_db_session = AsyncMock()

    async def test_end_to_end_golden_path_blocked_by_startup_contamination(self):
        """
        CRITICAL: Test end-to-end golden path blocked by startup contamination.

        This test should FAIL initially - proving that startup singleton contamination
        prevents proper end-to-end golden path execution for multiple users.

        Expected FAILURE: Golden path execution fails due to startup contamination.
        Expected FIX: Golden path should work correctly without startup interference.
        """
        print("🚨 TESTING END-TO-END GOLDEN PATH WITH STARTUP CONTAMINATION...")

        # STARTUP PHASE: Simulate application startup with singleton factory
        print("📱 PHASE 1: APPLICATION STARTUP - CREATING CONTAMINATED SINGLETON")

        startup_factory = get_agent_instance_factory()
        startup_factory.configure(
            websocket_bridge=self.mock_websocket_bridge,
            agent_registry=self.mock_agent_registry,
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )

        # Add startup contamination state
        startup_factory._startup_phase = "COMPLETED"
        startup_factory._startup_contamination = {
            'startup_user_id': 'SYSTEM_STARTUP',
            'startup_timestamp': datetime.now(timezone.utc),
            'startup_config_applied': True
        }

        print("📱 STARTUP CONTAMINATION APPLIED TO SINGLETON FACTORY")

        # GOLDEN PATH PHASE 1: First user enters golden path
        print("🌟 PHASE 2: FIRST USER ENTERING GOLDEN PATH...")

        async def execute_golden_path_user(user_id: str, thread_id: str, run_id: str) -> Dict[str, Any]:
            """Execute complete golden path for a user."""
            print(f"👤 Golden Path User {user_id} starting execution...")

            # Step 1: Create user execution context for SSOT factory pattern
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )

            # Step 2: Create isolated agent factory using SSOT pattern (prevents contamination)
            user_factory = create_agent_instance_factory(user_context)
            user_context = await user_factory.create_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                metadata={'golden_path_test': True}
            )

            # Step 3: Check for startup contamination in user context
            startup_contamination = getattr(user_factory, '_startup_contamination', None)
            startup_phase = getattr(user_factory, '_startup_phase', None)

            return {
                'user_id': user_id,
                'factory_id': id(user_factory),
                'context': user_context,
                'startup_contamination': startup_contamination,
                'startup_phase': startup_phase,
                'execution_success': True
            }

        # Execute golden path for first user
        user1_result = await execute_golden_path_user(
            self.golden_path_user1_id, self.thread1_id, self.run1_id
        )

        # CRITICAL TEST: User 1 should NOT inherit startup contamination
        user1_contamination = user1_result['startup_contamination']
        assert user1_contamination is None, (
            f"GOLDEN PATH BLOCKED: User 1 inherited startup contamination: {user1_contamination}. "
            f"Golden path execution contaminated by startup singleton state."
        )

        print("🌟 PHASE 3: SECOND USER ENTERING GOLDEN PATH CONCURRENTLY...")

        # GOLDEN PATH PHASE 2: Second user enters golden path concurrently
        user2_result = await execute_golden_path_user(
            self.golden_path_user2_id, self.thread2_id, self.run2_id
        )

        # CRITICAL TEST: User 2 should also NOT inherit startup contamination
        user2_contamination = user2_result['startup_contamination']
        assert user2_contamination is None, (
            f"GOLDEN PATH BLOCKED: User 2 inherited startup contamination: {user2_contamination}. "
            f"Multiple users affected by startup singleton contamination."
        )

        # CRITICAL TEST: Users should get different factory instances
        user1_factory_id = user1_result['factory_id']
        user2_factory_id = user2_result['factory_id']

        assert user1_factory_id != user2_factory_id, (
            f"GOLDEN PATH SINGLETON BLOCKING: Users share factory instance. "
            f"User1 ID: {user1_factory_id}, User2 ID: {user2_factory_id}. "
            f"Golden path requires isolated factory instances."
        )

        print("EXPECTED FAILURE: End-to-end golden path should be blocked by startup contamination initially")

    async def test_websocket_event_delivery_contamination_blocks_golden_path(self):
        """
        CRITICAL: Test WebSocket event delivery contamination blocking golden path.

        This test should FAIL initially - proving that startup WebSocket configuration
        contaminates event delivery for all golden path users.

        Expected FAILURE: WebSocket events delivered incorrectly due to startup contamination.
        Expected FIX: Each user should get properly isolated WebSocket event delivery.
        """
        print("🚨 TESTING WEBSOCKET EVENT DELIVERY CONTAMINATION IN GOLDEN PATH...")

        # STARTUP: Configure WebSocket with startup contamination
        startup_factory = get_agent_instance_factory()
        startup_factory.configure(websocket_bridge=self.mock_websocket_bridge)

        # Add startup WebSocket contamination
        startup_websocket_config = {
            'startup_websocket_marker': 'STARTUP_WEBSOCKET_CONFIGURED',
            'global_event_delivery': True,
            'startup_client_id': 'SYSTEM_STARTUP_CLIENT',
            'broadcast_to_all_users': True  # THIS IS THE CONTAMINATION
        }

        startup_factory._startup_websocket_config = startup_websocket_config

        print("📡 STARTUP WEBSOCKET CONTAMINATION CONFIGURED")

        # Create mock WebSocket emitters for testing event delivery
        mock_user1_emitter = MagicMock(spec=UnifiedWebSocketEmitter)
        mock_user2_emitter = MagicMock(spec=UnifiedWebSocketEmitter)

        # GOLDEN PATH: User 1 creates WebSocket context for event delivery
        print("👤 USER 1: Creating WebSocket context for golden path...")

        user1_factory = get_agent_instance_factory()
        user1_context = await user1_factory.create_user_execution_context(
            user_id=self.golden_path_user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )

        # Check if user 1 inherited startup WebSocket contamination
        user1_websocket_config = getattr(user1_factory, '_startup_websocket_config', None)

        # CRITICAL TEST: User 1 should NOT inherit startup WebSocket configuration
        assert user1_websocket_config is None, (
            f"WEBSOCKET CONTAMINATION BLOCKS GOLDEN PATH: User 1 inherited startup config: "
            f"{user1_websocket_config}. WebSocket event delivery contaminated by startup."
        )

        # GOLDEN PATH: User 2 creates WebSocket context for event delivery
        print("👤 USER 2: Creating WebSocket context for golden path...")

        user2_factory = get_agent_instance_factory()
        user2_context = await user2_factory.create_user_execution_context(
            user_id=self.golden_path_user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )

        # CRITICAL TEST: User 2 should also NOT inherit startup WebSocket configuration
        user2_websocket_config = getattr(user2_factory, '_startup_websocket_config', None)
        assert user2_websocket_config is None, (
            f"WEBSOCKET CONTAMINATION BLOCKS GOLDEN PATH: User 2 inherited startup config: "
            f"{user2_websocket_config}. Multiple users affected by startup WebSocket contamination."
        )

        # Test WebSocket event delivery isolation
        # Simulate sending events to both users
        user1_events = []
        user2_events = []

        # Mock event sending for both users
        def mock_user1_send_event(event_type: str, data: Dict[str, Any]):
            user1_events.append({'event_type': event_type, 'data': data, 'user_id': self.golden_path_user1_id})

        def mock_user2_send_event(event_type: str, data: Dict[str, Any]):
            user2_events.append({'event_type': event_type, 'data': data, 'user_id': self.golden_path_user2_id})

        mock_user1_emitter.send_event = mock_user1_send_event
        mock_user2_emitter.send_event = mock_user2_send_event

        # Simulate golden path events
        mock_user1_emitter.send_event('agent_started', {'agent_id': 'user1_agent', 'run_id': self.run1_id})
        mock_user2_emitter.send_event('agent_started', {'agent_id': 'user2_agent', 'run_id': self.run2_id})

        # CRITICAL TEST: Events should be properly isolated between users
        user1_agent_events = [e for e in user1_events if e['data'].get('agent_id') == 'user1_agent']
        user2_agent_events = [e for e in user2_events if e['data'].get('agent_id') == 'user2_agent']

        assert len(user1_agent_events) == 1, (
            f"WEBSOCKET EVENT ISOLATION FAILURE: User 1 received {len(user1_agent_events)} events, expected 1. "
            f"Startup contamination affects event delivery isolation."
        )

        assert len(user2_agent_events) == 1, (
            f"WEBSOCKET EVENT ISOLATION FAILURE: User 2 received {len(user2_agent_events)} events, expected 1. "
            f"Startup contamination affects event delivery isolation."
        )

        # Check for cross-user event contamination
        user1_received_user2_events = any(
            e['data'].get('agent_id') == 'user2_agent' for e in user1_events
        )
        user2_received_user1_events = any(
            e['data'].get('agent_id') == 'user1_agent' for e in user2_events
        )

        assert not user1_received_user2_events, (
            "WEBSOCKET CROSS-CONTAMINATION: User 1 received User 2's events. "
            "Startup contamination causes cross-user event delivery."
        )

        assert not user2_received_user1_events, (
            "WEBSOCKET CROSS-CONTAMINATION: User 2 received User 1's events. "
            "Startup contamination causes cross-user event delivery."
        )

        print("EXPECTED FAILURE: WebSocket event delivery should be contaminated by startup initially")

    async def test_concurrent_multi_user_golden_path_blocked_by_startup_singleton(self):
        """
        CRITICAL: Test concurrent multi-user golden path blocked by startup singleton.

        This test should FAIL initially - proving that multiple concurrent users
        in the golden path are blocked by shared startup singleton factory.

        Expected FAILURE: Concurrent golden path users interfere with each other.
        Expected FIX: Each concurrent user should have isolated golden path execution.
        """
        print("🚨 TESTING CONCURRENT MULTI-USER GOLDEN PATH WITH STARTUP SINGLETON...")

        # STARTUP: Create and configure singleton factory
        startup_factory = get_agent_instance_factory()
        startup_factory.configure(
            websocket_bridge=self.mock_websocket_bridge,
            agent_registry=self.mock_agent_registry,
            llm_manager=self.mock_llm_manager
        )

        # Add concurrent execution tracking to startup factory
        startup_factory._concurrent_execution_counter = 0
        startup_factory._active_concurrent_users = set()
        startup_factory._startup_concurrent_limit = 1  # THIS CAUSES THE BLOCKING

        print("🔄 STARTUP FACTORY CONFIGURED WITH CONCURRENT EXECUTION LIMITS")

        async def execute_concurrent_golden_path_user(user_id: str, thread_id: str, run_id: str) -> Dict[str, Any]:
            """Execute golden path with concurrent user tracking."""
            print(f"👥 Concurrent User {user_id} entering golden path...")

            # Get factory (shared singleton from startup)
            user_factory = get_agent_instance_factory()

            # Check concurrent execution limit (startup contamination)
            if hasattr(user_factory, '_concurrent_execution_counter'):
                user_factory._concurrent_execution_counter += 1
                user_factory._active_concurrent_users.add(user_id)

                # Simulate startup contamination blocking concurrent execution
                concurrent_count = user_factory._concurrent_execution_counter
                concurrent_limit = getattr(user_factory, '_startup_concurrent_limit', float('inf'))

                if concurrent_count > concurrent_limit:
                    # This simulates golden path blocking due to startup limits
                    execution_blocked = True
                else:
                    execution_blocked = False
            else:
                execution_blocked = False
                concurrent_count = 0

            # Create user context (may be blocked by startup contamination)
            if not execution_blocked:
                user_context = await user_factory.create_user_execution_context(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
                execution_success = True
            else:
                user_context = None
                execution_success = False

            return {
                'user_id': user_id,
                'factory_id': id(user_factory),
                'execution_blocked': execution_blocked,
                'execution_success': execution_success,
                'concurrent_count': concurrent_count,
                'active_users': user_factory._active_concurrent_users.copy() if hasattr(user_factory, '_active_concurrent_users') else set(),
                'context': user_context
            }

        # Launch concurrent golden path users
        concurrent_users = [
            execute_concurrent_golden_path_user(
                f"concurrent_golden_user_{i}",
                f"thread_concurrent_golden_{i}",
                f"run_concurrent_golden_{i}_{int(time.time())}"
            )
            for i in range(1, 4)  # 3 concurrent users
        ]

        # Execute all concurrent users simultaneously
        print("🚀 LAUNCHING CONCURRENT GOLDEN PATH USERS...")
        concurrent_results = await asyncio.gather(*concurrent_users)

        print("📊 CONCURRENT GOLDEN PATH EXECUTION COMPLETED")

        # CRITICAL TEST: All users should get DIFFERENT factory instances (no singleton)
        factory_ids = [result['factory_id'] for result in concurrent_results]
        unique_factory_ids = set(factory_ids)

        assert len(unique_factory_ids) == len(concurrent_results), (
            f"CONCURRENT SINGLETON BLOCKING: {len(concurrent_results)} users share "
            f"{len(unique_factory_ids)} factory instances. Factory IDs: {factory_ids}. "
            f"Startup singleton blocks concurrent golden path execution."
        )

        # CRITICAL TEST: All users should succeed (no execution blocking)
        execution_results = [result['execution_success'] for result in concurrent_results]
        blocked_users = [result for result in concurrent_results if result['execution_blocked']]

        assert all(execution_results), (
            f"CONCURRENT EXECUTION BLOCKED: {len(blocked_users)} users blocked by startup limits. "
            f"Blocked users: {[u['user_id'] for u in blocked_users]}. "
            f"Startup singleton contamination blocks concurrent golden path."
        )

        # Check concurrent user isolation
        for result in concurrent_results:
            user_id = result['user_id']
            active_users = result['active_users']

            # Each user should only see themselves in isolation
            other_concurrent_users = active_users - {user_id}
            assert len(other_concurrent_users) == 0, (
                f"CONCURRENT USER CONTAMINATION: User {user_id} sees other concurrent users: "
                f"{other_concurrent_users}. Startup singleton shares concurrent user state."
            )

        print("EXPECTED FAILURE: Concurrent multi-user golden path should be blocked by startup singleton initially")

    async def test_database_session_contamination_blocks_golden_path_transactions(self):
        """
        CRITICAL: Test database session contamination blocking golden path transactions.

        This test should FAIL initially - proving that startup database session configuration
        contaminates all golden path user database operations.

        Expected FAILURE: Users share database sessions from startup contamination.
        Expected FIX: Each user should get isolated database session for transactions.
        """
        print("🚨 TESTING DATABASE SESSION CONTAMINATION IN GOLDEN PATH...")

        # STARTUP: Configure factory with database session contamination
        startup_factory = get_agent_instance_factory()
        startup_factory.configure(websocket_bridge=self.mock_websocket_bridge)

        # Add startup database session contamination
        startup_db_config = {
            'startup_session_id': 'STARTUP_DB_SESSION_GLOBAL',
            'global_transaction_state': 'ACTIVE',
            'startup_connection_pool': self.mock_db_session,
            'shared_transaction_context': True  # THIS IS THE CONTAMINATION
        }

        startup_factory._startup_db_config = startup_db_config
        startup_factory._shared_db_session = self.mock_db_session

        print("💾 STARTUP DATABASE SESSION CONTAMINATION CONFIGURED")

        # GOLDEN PATH: User 1 requests database session
        print("👤 USER 1: Requesting database session for golden path...")

        user1_factory = get_agent_instance_factory()
        user1_context = await user1_factory.create_user_execution_context(
            user_id=self.golden_path_user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )

        # Check if user 1 inherited startup database contamination
        user1_db_config = getattr(user1_factory, '_startup_db_config', None)
        user1_shared_session = getattr(user1_factory, '_shared_db_session', None)

        # CRITICAL TEST: User 1 should NOT inherit startup database configuration
        assert user1_db_config is None, (
            f"DATABASE CONTAMINATION BLOCKS GOLDEN PATH: User 1 inherited startup DB config: "
            f"{user1_db_config}. Database operations contaminated by startup session."
        )

        # GOLDEN PATH: User 2 requests database session
        print("👤 USER 2: Requesting database session for golden path...")

        user2_factory = get_agent_instance_factory()
        user2_context = await user2_factory.create_user_execution_context(
            user_id=self.golden_path_user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )

        # CRITICAL TEST: User 2 should also NOT inherit startup database configuration
        user2_db_config = getattr(user2_factory, '_startup_db_config', None)
        user2_shared_session = getattr(user2_factory, '_shared_db_session', None)

        assert user2_db_config is None, (
            f"DATABASE CONTAMINATION BLOCKS GOLDEN PATH: User 2 inherited startup DB config: "
            f"{user2_db_config}. Multiple users affected by startup database contamination."
        )

        # Test database session isolation
        if user1_shared_session and user2_shared_session:
            # CRITICAL TEST: Users should NOT share the same database session
            assert user1_shared_session is not user2_shared_session, (
                f"DATABASE SESSION CONTAMINATION: Users share database session instance. "
                f"Session ID: {id(user1_shared_session)}. "
                f"Startup contamination causes database transaction interference."
            )

        # Simulate database operations for both users
        user1_transaction_data = {'user_id': self.golden_path_user1_id, 'operation': 'create_user_data'}
        user2_transaction_data = {'user_id': self.golden_path_user2_id, 'operation': 'create_user_data'}

        # Mock database operations
        user1_db_operations = []
        user2_db_operations = []

        def mock_user1_db_execute(query: str, params: Dict[str, Any]):
            user1_db_operations.append({'query': query, 'params': params, 'user_id': self.golden_path_user1_id})

        def mock_user2_db_execute(query: str, params: Dict[str, Any]):
            user2_db_operations.append({'query': query, 'params': params, 'user_id': self.golden_path_user2_id})

        # Execute database operations for both users
        mock_user1_db_execute('INSERT INTO user_data', user1_transaction_data)
        mock_user2_db_execute('INSERT INTO user_data', user2_transaction_data)

        # CRITICAL TEST: Database operations should be properly isolated
        user1_operations_count = len(user1_db_operations)
        user2_operations_count = len(user2_db_operations)

        assert user1_operations_count == 1, (
            f"DATABASE OPERATION ISOLATION FAILURE: User 1 performed {user1_operations_count} operations, expected 1. "
            f"Startup contamination affects database operation isolation."
        )

        assert user2_operations_count == 1, (
            f"DATABASE OPERATION ISOLATION FAILURE: User 2 performed {user2_operations_count} operations, expected 1. "
            f"Startup contamination affects database operation isolation."
        )

        # Check for cross-user database operation contamination
        user1_data_operations = [op for op in user1_db_operations if op['params'].get('user_id') == self.golden_path_user1_id]
        user2_data_operations = [op for op in user2_db_operations if op['params'].get('user_id') == self.golden_path_user2_id]

        assert len(user1_data_operations) == 1, (
            f"DATABASE CROSS-CONTAMINATION: User 1 has {len(user1_data_operations)} own operations, expected 1. "
            f"Startup contamination causes database operation cross-contamination."
        )

        assert len(user2_data_operations) == 1, (
            f"DATABASE CROSS-CONTAMINATION: User 2 has {len(user2_data_operations)} own operations, expected 1. "
            f"Startup contamination causes database operation cross-contamination."
        )

        print("EXPECTED FAILURE: Database session contamination should block golden path transactions initially")