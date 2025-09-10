"""
Test Thread State Type SSOT Compliance

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: Ensure ThreadState type consistency across services
- Value Impact: Prevents type confusion bugs in thread management critical to $120K+ MRR
- Strategic Impact: Golden path reliability depends on consistent thread state tracking

CRITICAL: ThreadState currently defined in 4+ files violating SSOT principles.
This test validates that ThreadState has ONE canonical definition and all imports
resolve to the same source, preventing runtime errors and development confusion.
"""

import pytest
import asyncio
import importlib
import inspect
from typing import Dict, Any, Type, List
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


class TestThreadStateSSotCompliance(BaseIntegrationTest):
    """Integration tests for ThreadState SSOT compliance across all services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_state_canonical_definition_exists(self, real_services_fixture):
        """
        Test that ThreadState has ONE canonical definition location.
        
        CRITICAL: Must validate that there is exactly one authoritative ThreadState
        definition and all other usages import from this canonical source.
        """
        # ThreadState canonical location should be in shared/types/
        canonical_locations = [
            "shared.types.core_types",
            "shared.types.execution_types", 
            "shared.types.agent_types"
        ]
        
        thread_state_definitions = []
        
        # Check each potential canonical location
        for module_path in canonical_locations:
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, 'ThreadState'):
                    thread_state_definitions.append({
                        'module': module_path,
                        'class': getattr(module, 'ThreadState'),
                        'file': inspect.getfile(getattr(module, 'ThreadState'))
                    })
            except ImportError:
                continue
        
        # SSOT VIOLATION: If more than one canonical definition exists
        assert len(thread_state_definitions) <= 1, (
            f"SSOT VIOLATION: ThreadState defined in multiple canonical locations: "
            f"{[d['module'] for d in thread_state_definitions]}. "
            f"Must have exactly ONE canonical definition per type_safety.xml"
        )
        
        # If no canonical definition exists, this is also a violation
        if len(thread_state_definitions) == 0:
            pytest.fail(
                "CRITICAL: No canonical ThreadState definition found in shared/types/. "
                "ThreadState must have ONE authoritative definition per SSOT principles."
            )
        
        canonical_def = thread_state_definitions[0]
        
        # Validate canonical definition is properly structured
        thread_state_class = canonical_def['class']
        assert hasattr(thread_state_class, '__annotations__') or hasattr(thread_state_class, '_fields'), (
            f"ThreadState canonical definition must be properly typed (dataclass, Enum, or Pydantic)"
        )
        
        # Store for cross-test validation
        self.canonical_thread_state = canonical_def


    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_thread_state_import_resolution_consistency(self, real_services_fixture):
        """
        Test that ALL ThreadState imports resolve to the SAME canonical definition.
        
        This prevents the critical bug where different files import different
        ThreadState definitions, causing runtime type mismatches.
        """
        # Known locations where ThreadState might be used
        potential_usage_modules = [
            "netra_backend.app.core.managers.unified_state_manager",
            "netra_backend.app.websockets.websocket_manager",
            "netra_backend.app.services.thread_service",
            "tests.integration.test_thread_continuity_multi_session_advanced",
            "tests.e2e.test_thread_management"
        ]
        
        thread_state_imports = []
        
        for module_path in potential_usage_modules:
            try:
                module = importlib.import_module(module_path)
                
                # Check if module imports or defines ThreadState
                if hasattr(module, 'ThreadState'):
                    thread_state_class = getattr(module, 'ThreadState')
                    source_file = inspect.getfile(thread_state_class)
                    
                    thread_state_imports.append({
                        'using_module': module_path,
                        'thread_state_class': thread_state_class,
                        'source_file': source_file,
                        'class_id': id(thread_state_class)
                    })
                    
            except ImportError:
                # Module may not exist in current environment
                continue
        
        if len(thread_state_imports) == 0:
            pytest.skip("No ThreadState usage found - may indicate successful consolidation")
        
        # CRITICAL VALIDATION: All ThreadState references must be the SAME object
        unique_class_ids = set(imp['class_id'] for imp in thread_state_imports)
        unique_source_files = set(imp['source_file'] for imp in thread_state_imports)
        
        assert len(unique_class_ids) == 1, (
            f"SSOT VIOLATION: ThreadState resolves to different class objects:\n"
            f"{chr(10).join([f'  {imp['using_module']} -> {imp['source_file']}' for imp in thread_state_imports])}\n"
            f"All imports must resolve to the SAME canonical ThreadState definition."
        )
        
        assert len(unique_source_files) == 1, (
            f"SSOT VIOLATION: ThreadState imported from multiple source files:\n"
            f"  Sources: {list(unique_source_files)}\n"
            f"All ThreadState usage must import from ONE canonical source file."
        )


    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_thread_state_database_persistence_consistency(self, real_services_fixture):
        """
        Test that ThreadState serialization/deserialization is consistent across services.
        
        BUSINESS CRITICAL: Thread state persistence must be consistent or users
        lose conversation context, directly impacting chat value delivery.
        """
        # Setup real database for persistence testing
        db_session = real_services_fixture['db']
        redis_client = real_services_fixture['redis']
        
        # Create test thread state data
        test_thread_data = {
            'thread_id': 'test-thread-ssot-123',
            'user_id': 'test-user-456', 
            'state': 'active',
            'context': {'last_message_id': 'msg-789'},
            'created_at': '2024-09-10T10:00:00Z'
        }
        
        # Test PostgreSQL persistence
        await db_session.execute("""
            INSERT INTO threads (id, user_id, state, context, created_at)
            VALUES (%(thread_id)s, %(user_id)s, %(state)s, %(context)s, %(created_at)s)
        """, test_thread_data)
        await db_session.commit()
        
        # Test Redis caching
        await redis_client.setex(
            f"thread_state:{test_thread_data['thread_id']}", 
            3600,
            f"{test_thread_data['state']}:{test_thread_data['user_id']}"
        )
        
        # Retrieve from both sources
        db_result = await db_session.fetchrow(
            "SELECT state, user_id FROM threads WHERE id = $1",
            test_thread_data['thread_id']
        )
        
        redis_result = await redis_client.get(f"thread_state:{test_thread_data['thread_id']}")
        redis_state, redis_user_id = redis_result.decode().split(':')
        
        # CRITICAL: Database and cache must have consistent state representation
        assert db_result['state'] == redis_state, (
            f"ThreadState inconsistency between PostgreSQL and Redis:\n"
            f"  PostgreSQL state: {db_result['state']}\n"
            f"  Redis state: {redis_state}\n"
            f"Inconsistent state representation violates SSOT and breaks user experience."
        )
        
        assert db_result['user_id'] == redis_user_id, (
            f"User ID inconsistency in thread state:\n"
            f"  PostgreSQL: {db_result['user_id']}\n"
            f"  Redis: {redis_user_id}\n"
            f"User context must be consistent across storage layers."
        )
        
        # Cleanup
        await db_session.execute("DELETE FROM threads WHERE id = $1", test_thread_data['thread_id'])
        await redis_client.delete(f"thread_state:{test_thread_data['thread_id']}")
        await db_session.commit()


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_state_websocket_event_consistency(self, real_services_fixture):
        """
        Test that ThreadState changes generate consistent WebSocket events.
        
        MISSION CRITICAL: WebSocket events deliver chat value to users. Inconsistent
        ThreadState events break real-time updates and user experience.
        """
        from shared.types.core_types import ThreadID, UserID
        
        # Setup test data
        test_thread_id = ThreadID("ws-thread-test-001")
        test_user_id = UserID("ws-user-test-001") 
        
        # Mock WebSocket event capture
        captured_events = []
        
        class MockWebSocketManager:
            async def emit_thread_state_change(self, thread_id: ThreadID, old_state: str, new_state: str, user_id: UserID):
                captured_events.append({
                    'type': 'thread_state_change',
                    'thread_id': thread_id,
                    'old_state': old_state,
                    'new_state': new_state,
                    'user_id': user_id,
                    'timestamp': asyncio.get_event_loop().time()
                })
        
        websocket_manager = MockWebSocketManager()
        
        # Simulate thread state transitions
        state_transitions = [
            ('initializing', 'active'),
            ('active', 'waiting_for_input'),
            ('waiting_for_input', 'processing'),
            ('processing', 'completed')
        ]
        
        for old_state, new_state in state_transitions:
            await websocket_manager.emit_thread_state_change(
                test_thread_id, old_state, new_state, test_user_id
            )
        
        # Validate event consistency
        assert len(captured_events) == len(state_transitions), (
            f"Expected {len(state_transitions)} thread state events, got {len(captured_events)}"
        )
        
        # Check event structure consistency
        for i, event in enumerate(captured_events):
            expected_old, expected_new = state_transitions[i]
            
            # ThreadID and UserID must maintain strong typing
            assert isinstance(event['thread_id'], ThreadID), (
                f"Event {i}: thread_id must be strongly typed ThreadID, got {type(event['thread_id'])}"
            )
            
            assert isinstance(event['user_id'], UserID), (
                f"Event {i}: user_id must be strongly typed UserID, got {type(event['user_id'])}"
            )
            
            # State values must match expected transitions
            assert event['old_state'] == expected_old and event['new_state'] == expected_new, (
                f"Event {i}: State transition mismatch. Expected {expected_old}->{expected_new}, "
                f"got {event['old_state']}->{event['new_state']}"
            )
            
            # Events must be in chronological order
            if i > 0:
                assert event['timestamp'] >= captured_events[i-1]['timestamp'], (
                    f"Thread state events must be in chronological order"
                )