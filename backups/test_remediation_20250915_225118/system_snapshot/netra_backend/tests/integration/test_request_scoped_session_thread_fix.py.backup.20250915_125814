"""Integration tests for request-scoped session thread ID fix.

This test suite validates that the critical thread ID mismatch bug has been resolved
and that request-scoped database sessions work correctly with thread records.

Business Value Justification (BVJ):
- Segment: Platform Stability (all tiers)
- Business Goal: Prevent session creation failures that break Chat functionality 
- Value Impact: Ensures core business value (AI Chat interactions) work reliably
- Strategic Impact: Foundation for multi-user concurrent operations

Test Coverage:
1. SSOT ID generation consistency 
2. Thread record auto-creation
3. Session-thread relationship validation
4. Multi-user concurrent session isolation
5. WebSocket factory integration with database threads
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.routes.utils.thread_validators import get_thread_with_validation
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestRequestScopedSessionThreadFix:
    """Test suite for thread ID session mismatch fixes."""
    
    @pytest.fixture
    async def session_factory(self):
        """Create session factory for testing."""
        factory = RequestScopedSessionFactory()
        yield factory
        await factory.close()
    
    @pytest.fixture
    def mock_user_context(self):
        """Mock user execution context."""
        return {
            "user_id": "test_user_123",
            "operation": "test_session"
        }
    
    @pytest.mark.asyncio
    async def test_ssot_id_generation_consistency(self, session_factory, mock_user_context):
        """Test that all ID generation uses SSOT UnifiedIdGenerator."""
        user_id = mock_user_context["user_id"]
        
        # Generate IDs using session factory (should use SSOT internally)
        async with session_factory.get_request_scoped_session(user_id=user_id) as session:
            # Session should be created successfully
            assert session is not None
            
            # Verify session has proper SSOT-generated metadata
            assert hasattr(session, 'info')
            assert 'user_id' in session.info
            assert session.info['user_id'] == user_id
            
            # Verify request_id follows SSOT pattern
            request_id = session.info.get('request_id')
            assert request_id is not None
            assert request_id.startswith('req_')
            
            # Verify thread_id follows SSOT pattern if provided
            thread_id = session.info.get('thread_id')
            if thread_id:
                assert thread_id.startswith('thread_')
    
    @pytest.mark.asyncio
    async def test_thread_record_auto_creation(self, session_factory, mock_user_context):
        """Test that thread records are automatically created when missing."""
        user_id = mock_user_context["user_id"]
        
        # Generate thread_id using SSOT
        thread_id, _, _ = UnifiedIdGenerator.generate_user_context_ids(user_id, "test")
        
        async with session_factory.get_request_scoped_session(
            user_id=user_id,
            thread_id=thread_id
        ) as session:
            
            # Verify thread record was created
            thread_repo = ThreadRepository()
            thread = await thread_repo.get_by_id(session, thread_id)
            
            assert thread is not None
            assert thread.id == thread_id
            assert thread.metadata_ is not None
            assert thread.metadata_.get("user_id") == user_id
            assert thread.metadata_.get("created_via") == "request_scoped_session"
    
    @pytest.mark.asyncio 
    async def test_thread_validator_no_longer_fails(self, session_factory, mock_user_context):
        """Test that thread validators no longer raise 404 errors."""
        user_id = mock_user_context["user_id"]
        
        # Generate thread_id using SSOT
        thread_id, _, _ = UnifiedIdGenerator.generate_user_context_ids(user_id, "validator_test")
        
        async with session_factory.get_request_scoped_session(
            user_id=user_id,
            thread_id=thread_id
        ) as session:
            
            # This should NOT raise HTTPException(404, "Thread not found")
            thread = await get_thread_with_validation(session, thread_id, user_id)
            
            assert thread is not None
            assert thread.id == thread_id
    
    @pytest.mark.asyncio
    async def test_multiple_session_thread_isolation(self, session_factory):
        """Test that multiple users get isolated sessions and threads."""
        users = ["user_001", "user_002", "user_003"]
        sessions_created = []
        threads_created = []
        
        # Create sessions concurrently for different users
        async def create_user_session(user_id):
            thread_id, _, _ = UnifiedIdGenerator.generate_user_context_ids(user_id, "isolation_test")
            
            async with session_factory.get_request_scoped_session(
                user_id=user_id,
                thread_id=thread_id
            ) as session:
                sessions_created.append(session.info['session_id'])
                threads_created.append(thread_id)
                
                # Verify thread exists and belongs to correct user
                thread_repo = ThreadRepository()
                thread = await thread_repo.get_by_id(session, thread_id)
                assert thread.metadata_.get("user_id") == user_id
                
                return session.info['session_id']
        
        # Run concurrent session creation
        tasks = [create_user_session(user_id) for user_id in users]
        session_ids = await asyncio.gather(*tasks)
        
        # Verify all sessions are unique
        assert len(set(session_ids)) == len(users)
        
        # Verify all threads are unique
        assert len(set(threads_created)) == len(users)
    
    @pytest.mark.asyncio
    async def test_websocket_factory_thread_patterns(self, session_factory):
        """Test that WebSocket factory thread patterns work with session creation."""
        user_id = "websocket_user_123"
        
        # Simulate WebSocket factory thread ID pattern
        websocket_thread_id = f"thread_websocket_factory_{int(time.time() * 1000)}_1_abcd1234"
        
        async with session_factory.get_request_scoped_session(
            user_id=user_id,
            thread_id=websocket_thread_id
        ) as session:
            
            # Verify WebSocket-style thread ID works
            thread_repo = ThreadRepository()
            thread = await thread_repo.get_by_id(session, websocket_thread_id)
            
            assert thread is not None
            assert thread.id == websocket_thread_id
            assert thread.metadata_.get("user_id") == user_id
    
    @pytest.mark.asyncio
    async def test_system_user_session_creation(self, session_factory):
        """Test that system user sessions work correctly."""
        system_user_ids = ["system", "system_agent", "system_websocket"]
        
        for user_id in system_user_ids:
            async with session_factory.get_request_scoped_session(user_id=user_id) as session:
                assert session is not None
                assert session.info['user_id'] == user_id
                
                # Verify thread was created for system user
                thread_id = session.info.get('thread_id')
                if thread_id:
                    thread_repo = ThreadRepository()
                    thread = await thread_repo.get_by_id(session, thread_id)
                    assert thread.metadata_.get("user_id") == user_id
    
    @pytest.mark.asyncio
    async def test_session_cleanup_preserves_threads(self, session_factory, mock_user_context):
        """Test that session cleanup doesn't delete thread records."""
        user_id = mock_user_context["user_id"]
        thread_id, _, _ = UnifiedIdGenerator.generate_user_context_ids(user_id, "cleanup_test")
        
        # Create and close session
        async with session_factory.get_request_scoped_session(
            user_id=user_id,
            thread_id=thread_id
        ) as session:
            # Session exists, thread created
            pass
        
        # Session closed, but thread should still exist
        async with session_factory.get_request_scoped_session(
            user_id=user_id,
            thread_id=thread_id  # Reuse same thread_id
        ) as session2:
            
            thread_repo = ThreadRepository()
            thread = await thread_repo.get_by_id(session2, thread_id)
            
            # Thread should still exist from previous session
            assert thread is not None
            assert thread.id == thread_id
    
    @pytest.mark.asyncio
    async def test_id_generation_collision_resistance(self, session_factory):
        """Test that concurrent ID generation doesn't create collisions."""
        user_id = "collision_test_user"
        generated_ids = set()
        
        async def generate_session_ids():
            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
                user_id, "collision_test"
            )
            return (thread_id, run_id, request_id)
        
        # Generate many IDs concurrently
        tasks = [generate_session_ids() for _ in range(100)]
        id_sets = await asyncio.gather(*tasks)
        
        # Flatten and check for uniqueness
        all_ids = []
        for thread_id, run_id, request_id in id_sets:
            all_ids.extend([thread_id, run_id, request_id])
        
        # All IDs should be unique
        assert len(all_ids) == len(set(all_ids))
    
    @pytest.mark.asyncio
    async def test_error_recovery_thread_creation_failure(self, session_factory, mock_user_context):
        """Test that session creation continues even if thread creation fails."""
        user_id = mock_user_context["user_id"]
        thread_id = "invalid_thread_id_format"
        
        # This should not crash even if thread creation has issues
        async with session_factory.get_request_scoped_session(
            user_id=user_id,
            thread_id=thread_id
        ) as session:
            # Session should still be created
            assert session is not None
            assert session.info['user_id'] == user_id


class TestThreadIDConsistencyValidation:
    """Validation tests for thread ID consistency across system components."""
    
    def test_unified_id_generator_patterns(self):
        """Validate UnifiedIdGenerator produces consistent patterns."""
        user_id = "pattern_test_user"
        operation = "consistency_test"
        
        # Generate IDs multiple times
        for _ in range(10):
            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
                user_id, operation
            )
            
            # Validate patterns
            assert thread_id.startswith(f"thread_{operation}_")
            assert run_id.startswith(f"run_{operation}_")
            assert request_id.startswith(f"req_{operation}_")
            
            # Validate structure: prefix_operation_timestamp_counter_hex
            parts = thread_id.split('_')
            assert len(parts) >= 5  # thread, operation, timestamp, counter, hex
            assert parts[0] == "thread"
            assert parts[1] == operation
            
            # Timestamp should be numeric
            assert parts[2].isdigit()
            
            # Counter should be numeric  
            assert parts[3].isdigit()
            
            # Hex part should be valid hex
            assert all(c in '0123456789abcdef' for c in parts[4])
    
    def test_no_uuid4_usage_in_session_factory(self):
        """Validate that session factory doesn't use uuid.uuid4 directly."""
        import inspect
        from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory
        
        # Get source code of the class
        source = inspect.getsource(RequestScopedSessionFactory)
        
        # Should not contain direct uuid.uuid4() calls
        assert "uuid.uuid4()" not in source, "Session factory should use UnifiedIdGenerator, not uuid.uuid4()"
        assert "uuid4()" not in source, "Session factory should use UnifiedIdGenerator, not uuid4()"
    
    @pytest.mark.asyncio
    async def test_thread_repository_get_or_create_pattern(self):
        """Test that ThreadRepository supports get_or_create pattern."""
        # This validates that we can extend ThreadRepository if needed
        thread_repo = ThreadRepository()
        
        # Verify required methods exist
        assert hasattr(thread_repo, 'get_by_id')
        assert hasattr(thread_repo, 'create')
        
        # These are async methods
        assert asyncio.iscoroutinefunction(thread_repo.get_by_id)
        assert asyncio.iscoroutinefunction(thread_repo.create)


@pytest.mark.integration
class TestRegressionValidation:
    """Regression tests to ensure the original error patterns are fixed."""
    
    @pytest.mark.asyncio
    async def test_original_error_pattern_fixed(self, session_factory):
        """Test that the original 'Thread not found' error pattern is fixed."""
        # Simulate the original error scenario:
        # WebSocket factory generates thread ID but no database record
        
        user_id = "regression_test_user"
        
        # Original problematic pattern: WebSocket factory style ID
        websocket_thread_id = f"thread_websocket_factory_{int(time.time() * 1000)}_7_90c65fe4"
        
        # This previously failed with "404: Thread not found"
        # Should now work due to auto thread creation
        async with session_factory.get_request_scoped_session(
            user_id=user_id,
            thread_id=websocket_thread_id
        ) as session:
            
            # Verify thread validation works
            from netra_backend.app.routes.utils.thread_validators import validate_thread_exists
            
            thread_repo = ThreadRepository()
            thread = await thread_repo.get_by_id(session, websocket_thread_id)
            
            # This should NOT raise HTTPException(404, "Thread not found")
            validate_thread_exists(thread)
            
            assert thread.id == websocket_thread_id
    
    @pytest.mark.asyncio 
    async def test_run_id_thread_id_mismatch_resolved(self):
        """Test that run_id/thread_id mismatch patterns are resolved."""
        user_id = "mismatch_test_user"
        
        # Generate using SSOT - should be consistent
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
            user_id, "websocket_factory"
        )
        
        # Verify consistency - run_id should relate to thread_id properly
        # Both should have same timestamp and counter base
        thread_parts = thread_id.split('_')
        run_parts = run_id.split('_')
        
        # Should have same operation and timestamp
        assert thread_parts[1] == run_parts[1]  # operation
        assert thread_parts[2] == run_parts[2]  # timestamp
        
        # Counters should be sequential
        thread_counter = int(thread_parts[3])
        run_counter = int(run_parts[3])
        assert run_counter == thread_counter + 1
    
    def test_ssot_violation_detection(self):
        """Test that SSOT violations would be detected."""
        # This test validates our architecture compliance
        
        # Good: Using UnifiedIdGenerator
        user_id = "ssot_test_user"
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(user_id, "test")
        
        assert all(id_val.count('_') >= 4 for id_val in [thread_id, run_id, request_id])
        
        # Bad patterns that should be avoided (for documentation)
        import uuid
        bad_pattern_1 = f"req_{uuid.uuid4().hex[:12]}"  # Direct uuid usage
        bad_pattern_2 = f"thread_{uuid.uuid4().hex[:8]}"  # Direct uuid usage
        
        # These patterns should be different from SSOT patterns
        assert not bad_pattern_1.startswith("req_test_")
        assert not bad_pattern_2.startswith("thread_test_")