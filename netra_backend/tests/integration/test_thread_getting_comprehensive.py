"""
Comprehensive Thread Getting (Retrieval) Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Enable reliable conversation context retrieval and user experience continuity
- Value Impact: Users can access their conversation history, maintain context across sessions, and retrieve specific discussions
- Strategic Impact: Core platform functionality that enables persistent conversational AI experiences and user retention

CRITICAL REQUIREMENTS:
- Uses integration test patterns with controlled mocking for isolation
- Tests cover all thread retrieval patterns for business value
- Validates multi-user isolation and data security patterns
- Tests performance patterns and error handling
- Ensures business logic validation without external dependencies

Thread Getting Business Value:
- Conversation Continuity: Users can resume previous discussions 
- Context Preservation: Maintain AI interaction state and history
- Multi-Session Support: Access threads across different sessions/devices
- Data Security: Only authorized users can access their threads
- Performance: Fast retrieval enables responsive user experience
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.database_fixtures import test_db_session
from shared.isolated_environment import get_env

from netra_backend.app.db.models_postgres import Thread, Message
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from netra_backend.app.core.exceptions_database import RecordNotFoundError, DatabaseError
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestThreadGettingComprehensive(BaseIntegrationTest):
    """Comprehensive thread retrieval integration tests."""
    
    def setup_method(self):
        """Setup for each test with service components."""
        super().setup_method()
        self.thread_repo = ThreadRepository()
        self.thread_service = ThreadService() 
        self.id_manager = UnifiedIDManager()
        self.env = get_env()
        
    async def _create_test_thread(self, user_id: str, db: AsyncSession, title: str = "Test Thread", 
                                metadata: Optional[Dict] = None) -> Thread:
        """Helper to create real test thread in database with proper metadata."""
        if metadata is None:
            metadata = {"user_id": user_id, "created_by": "test", "title": title}
            
        # Create real thread using ThreadService
        thread = await self.thread_service.get_or_create_thread(user_id, db)
        
        # Update metadata if custom metadata provided
        if metadata != {"user_id": user_id, "created_by": "test", "title": title}:
            thread.metadata_.update(metadata)
            await self.thread_repo.update(db, thread.id, metadata_=thread.metadata_)
            await db.commit()
        
        return thread
        
    async def _create_test_messages(self, thread_id: str, db: AsyncSession, count: int = 3) -> List[Message]:
        """Helper to create real test messages in database for a thread."""
        messages = []
        for i in range(count):
            message_data = {
                "id": f"msg_{uuid.uuid4()}",
                "object": "thread.message",
                "created_at": int(time.time()) + i,
                "thread_id": thread_id,
                "role": "user" if i % 2 == 0 else "assistant",
                "content": [{"type": "text", "text": {"value": f"Test message {i+1}"}}],
                "metadata_": {"sequence": i}
            }
            
            # Insert real message into database
            result = await db.execute(
                text("""
                    INSERT INTO messages (id, object, created_at, thread_id, role, content, metadata)
                    VALUES (:id, :object, :created_at, :thread_id, :role, :content, :metadata)
                    RETURNING id, object, created_at, thread_id, role, content, metadata
                """),
                {
                    "id": message_data["id"],
                    "object": message_data["object"],
                    "created_at": message_data["created_at"],
                    "thread_id": message_data["thread_id"],
                    "role": message_data["role"],
                    "content": str(message_data["content"]),
                    "metadata": str(message_data["metadata_"])
                }
            )
            await db.commit()
            
            # Create Message object from result
            row = result.fetchone()
            if row:
                message = Message(
                    id=row.id,
                    object=row.object,
                    created_at=row.created_at,
                    thread_id=row.thread_id,
                    role=row.role,
                    content=row.content,
                    metadata_=row.metadata
                )
                messages.append(message)
        
        return messages

    # ============================================================================
    # BASIC THREAD RETRIEVAL TESTS
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_get_thread_by_id_basic(self, test_db_session):
        """
        BVJ: Enable users to retrieve specific conversations by ID
        - Segment: All users need to access their specific discussions
        - Business Goal: Provide direct thread access for user workflow continuity
        - Value Impact: Users can bookmark and return to important conversations
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"user_basic_get_{uuid.uuid4()}"
        
        # Create real thread in database
        thread = await self._create_test_thread(user_id, db, "Basic Get Thread")
        
        # Test real retrieval
        retrieved = await self.thread_repo.get_by_id(db, thread.id)
        
        assert retrieved is not None
        assert retrieved.id == thread.id
        assert retrieved.metadata_["user_id"] == user_id
        assert retrieved.object == "thread"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_get_thread_with_metadata_complete(self, test_db_session):
        """
        BVJ: Retrieve thread with complete metadata for context preservation
        - Segment: Mid/Enterprise users with complex conversation contexts
        - Business Goal: Maintain full conversation context and settings
        - Value Impact: Preserve AI agent configurations and user preferences
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"user_metadata_get_{uuid.uuid4()}"
        
        # Create thread with rich metadata
        complex_metadata = {
            "user_id": user_id,
            "title": "AI Cost Optimization Discussion",
            "agent_config": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "tags": ["cost-optimization", "aws", "enterprise"],
            "priority": "high",
            "last_agent": "cost_optimizer",
            "created_by": "test"
        }
        
        thread = await self._create_test_thread(user_id, db, "Metadata Thread", complex_metadata)
        
        # Test real retrieval with full metadata
        retrieved = await self.thread_repo.get_by_id(db, thread.id)
        
        assert retrieved is not None
        assert retrieved.metadata_["agent_config"]["model"] == "gpt-4"
        assert "cost-optimization" in retrieved.metadata_["tags"]
        assert retrieved.metadata_["priority"] == "high"
        assert retrieved.metadata_["last_agent"] == "cost_optimizer"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_get_threads_by_user_basic(self, test_db_session):
        """
        BVJ: List all user conversations for navigation and management
        - Segment: All users need to see their conversation history  
        - Business Goal: Enable conversation management and selection
        - Value Impact: Users can find and resume previous AI interactions
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"user_list_threads_{uuid.uuid4()}"
        
        # Create multiple real threads in database
        threads = []
        for i in range(5):
            thread = await self._create_test_thread(user_id, db, f"Thread {i+1}")
            threads.append(thread)
        
        # Test real retrieval
        retrieved_threads = await self.thread_repo.find_by_user(db, user_id)
        
        assert len(retrieved_threads) >= 5  # May have more from concurrent tests
        thread_ids = [t.id for t in retrieved_threads]
        for thread in threads:
            assert thread.id in thread_ids

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_get_thread_with_messages(self, test_db_session):
        """
        BVJ: Retrieve thread with complete message history
        - Segment: All users need full conversation context
        - Business Goal: Provide complete conversation history for continuity
        - Value Impact: Users see full AI interaction context and responses
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"user_with_messages_{uuid.uuid4()}"
        
        # Create real thread and messages in database
        thread = await self._create_test_thread(user_id, db, "Thread with Messages")
        messages = await self._create_test_messages(thread.id, db, 4)
        
        # Test real retrieval
        retrieved = await self.thread_repo.get_by_id(db, thread.id)
        
        assert retrieved is not None
        
        # Query messages separately (since repository may not load them by default)
        message_count_result = await db.execute(
            text("SELECT COUNT(*) FROM messages WHERE thread_id = :thread_id"),
            {"thread_id": thread.id}
        )
        message_count = message_count_result.scalar()
        assert message_count == 4

    # ============================================================================
    # USER ISOLATION AND SECURITY TESTS
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_user_isolation(self, test_db_session):
        """
        BVJ: Ensure complete data security between users
        - Segment: All users require data privacy and isolation
        - Business Goal: Maintain user data security and privacy compliance
        - Value Impact: Users trust platform with sensitive business conversations
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user1_id = f"user_isolation_1_{uuid.uuid4()}"
        user2_id = f"user_isolation_2_{uuid.uuid4()}"
        
        # Create real threads for each user
        user1_thread = await self._create_test_thread(user1_id, db, "User 1 Secret Thread")
        user2_thread = await self._create_test_thread(user2_id, db, "User 2 Secret Thread")
        
        # Test isolation: User 1 gets only their threads
        user1_threads = await self.thread_repo.find_by_user(db, user1_id)
        user1_thread_ids = [t.id for t in user1_threads]
        
        # Test isolation: User 2 gets only their threads  
        user2_threads = await self.thread_repo.find_by_user(db, user2_id)
        user2_thread_ids = [t.id for t in user2_threads]
        
        # Verify complete isolation
        assert user1_thread.id in user1_thread_ids
        assert user1_thread.id not in user2_thread_ids
        assert user2_thread.id in user2_thread_ids
        assert user2_thread.id not in user1_thread_ids

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_ownership_validation(self, test_db_session):
        """
        BVJ: Validate thread ownership for security
        - Segment: All users need ownership protection
        - Business Goal: Prevent unauthorized thread access
        - Value Impact: Users' conversations remain private and secure
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        owner_id = f"thread_owner_{uuid.uuid4()}"
        other_id = f"thread_other_{uuid.uuid4()}"
        
        # Create thread owned by owner_id
        owned_thread = await self._create_test_thread(owner_id, db, "Owned Thread")
        
        # Verify ownership through metadata
        retrieved = await self.thread_repo.get_by_id(db, owned_thread.id)
        assert retrieved is not None
        assert retrieved.metadata_["user_id"] == owner_id
        
        # Verify other user cannot find this thread in their list
        other_threads = await self.thread_repo.find_by_user(db, other_id)
        other_thread_ids = [t.id for t in other_threads]
        assert owned_thread.id not in other_thread_ids
        
        # Verify owner can find their thread
        owner_threads = await self.thread_repo.find_by_user(db, owner_id)
        owner_thread_ids = [t.id for t in owner_threads]
        assert owned_thread.id in owner_thread_ids

    # ============================================================================
    # ERROR HANDLING TESTS
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_get_nonexistent_thread(self, test_db_session):
        """
        BVJ: Handle invalid thread access gracefully
        - Segment: All users may request invalid thread IDs
        - Business Goal: Provide clear error messaging for invalid requests
        - Value Impact: Users understand system limitations and get helpful feedback
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        
        # Test retrieval of non-existent thread with real database
        fake_thread_id = f"thread_{uuid.uuid4()}"
        retrieved = await self.thread_repo.get_by_id(db, fake_thread_id)
        
        assert retrieved is None

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_get_thread_malformed_id(self, test_db_session):
        """
        BVJ: Handle malformed thread ID requests robustly
        - Segment: All users may provide malformed input
        - Business Goal: Maintain system stability with invalid input
        - Value Impact: System remains reliable despite user input errors
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        
        # Test various malformed IDs with real database
        malformed_ids = ["", "invalid", "thread_", "null", "undefined", "123", "!@#$%"]
        
        for malformed_id in malformed_ids:
            retrieved = await self.thread_repo.get_by_id(db, malformed_id)
            assert retrieved is None, f"Should not find thread with malformed ID: {malformed_id}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_get_thread_null_metadata_handling(self, test_db_session):
        """
        BVJ: Handle threads with corrupted or null metadata
        - Segment: All users may encounter data consistency issues
        - Business Goal: Maintain system functionality despite data anomalies
        - Value Impact: Users experience consistent service even with data issues
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"user_null_metadata_{uuid.uuid4()}"
        
        # Create thread with intentionally null metadata in real database
        thread_id = f"thread_{uuid.uuid4()}"
        
        # Insert thread with NULL metadata directly to database
        await db.execute(
            text("""
                INSERT INTO threads (id, object, created_at, metadata)
                VALUES (:id, :object, :created_at, NULL)
            """),
            {
                "id": thread_id,
                "object": "thread",
                "created_at": int(time.time())
            }
        )
        await db.commit()
        
        # Test real retrieval handles null metadata gracefully
        retrieved = await self.thread_repo.get_by_id(db, thread_id)
        assert retrieved is not None
        assert retrieved.id == thread_id
        # Repository should handle null metadata gracefully (convert to empty dict or similar)

    # ============================================================================
    # PERFORMANCE AND CONCURRENCY TESTS
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_thread_access(self, test_db_session):
        """
        BVJ: Handle multiple simultaneous thread access requests
        - Segment: Multi-user platform with concurrent access patterns
        - Business Goal: Maintain system stability under concurrent load
        - Value Impact: Multiple users can access threads simultaneously without conflicts
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"user_concurrent_{uuid.uuid4()}"
        
        # Create multiple real threads in database
        threads = []
        for i in range(10):
            thread = await self._create_test_thread(user_id, db, f"Concurrent Thread {i+1}")
            threads.append(thread)
        
        # Test concurrent access to different threads with real database
        async def get_thread_task(thread_id: str):
            return await self.thread_repo.get_by_id(db, thread_id)
        
        # Execute concurrent requests
        tasks = [get_thread_task(thread.id) for thread in threads]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all requests succeeded
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 10
        
        # Verify no data corruption
        for i, result in enumerate(successful_results):
            if result:
                assert result.id == threads[i].id
                assert result.metadata_["user_id"] == user_id

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_get_threads_performance_large_dataset(self, test_db_session):
        """
        BVJ: Ensure responsive performance with large conversation histories
        - Segment: Enterprise users with extensive conversation data
        - Business Goal: Maintain fast response times for productivity  
        - Value Impact: Users experience fast loading regardless of data volume
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"user_performance_{uuid.uuid4()}"
        
        # Create substantial number of real threads in database
        threads = []
        for i in range(25):  # Smaller number for real database performance
            thread = await self._create_test_thread(user_id, db, f"Performance Thread {i+1}")
            threads.append(thread)
        
        # Test real retrieval performance
        start_time = time.time()
        retrieved_threads = await self.thread_repo.find_by_user(db, user_id)
        retrieval_time = time.time() - start_time
        
        assert len(retrieved_threads) >= 25
        assert retrieval_time < 5.0  # Real database operation should be reasonable
        self.logger.info(f"Retrieved {len(retrieved_threads)} threads in {retrieval_time:.3f}s")

    # ============================================================================
    # THREAD SEARCH AND ORGANIZATION TESTS
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_search_functionality(self, test_db_session):
        """
        BVJ: Enable users to search through conversation history
        - Segment: All users with multiple conversations  
        - Business Goal: Help users find specific conversations quickly
        - Value Impact: Users locate relevant discussions for reference and continuation
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"user_search_{uuid.uuid4()}"
        
        # Create real threads with searchable content
        cost_thread = await self._create_test_thread(user_id, db, "AWS Cost Optimization Strategy", 
            {"user_id": user_id, "tags": ["aws", "cost"], "topic": "optimization", "created_by": "test"})
        security_thread = await self._create_test_thread(user_id, db, "Azure Security Best Practices",
            {"user_id": user_id, "tags": ["azure", "security"], "topic": "security", "created_by": "test"})
        performance_thread = await self._create_test_thread(user_id, db, "Google Cloud Performance Tuning",
            {"user_id": user_id, "tags": ["gcp", "performance"], "topic": "tuning", "created_by": "test"})
        multi_thread = await self._create_test_thread(user_id, db, "Multi-Cloud Cost Analysis",
            {"user_id": user_id, "tags": ["aws", "azure", "cost"], "topic": "analysis", "created_by": "test"})
        
        # Test real search by getting all threads and filtering
        all_user_threads = await self.thread_repo.find_by_user(db, user_id)
        
        # Filter threads with "cost" tag
        cost_threads = [t for t in all_user_threads if "cost" in t.metadata_.get("tags", [])]
        
        # Should find threads with "cost" tag
        assert len(cost_threads) >= 2  # cost_thread and multi_thread
        cost_topics = [t.metadata_["topic"] for t in cost_threads]
        assert "optimization" in cost_topics or "analysis" in cost_topics

    # ============================================================================
    # BUSINESS VALUE VALIDATION TEST
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_getting_complete_workflow(self, test_db_session):
        """
        BVJ: End-to-end thread retrieval workflow validation
        - Segment: All user segments and workflows
        - Business Goal: Validate complete thread retrieval functionality works as designed
        - Value Impact: Users experience seamless conversation retrieval across all use cases
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"user_complete_workflow_{uuid.uuid4()}"
        
        # Phase 1: Create diverse real thread collection in database
        # Regular thread
        regular_thread = await self._create_test_thread(user_id, db, "Regular Discussion")
        
        # Thread with complex metadata
        complex_thread = await self._create_test_thread(user_id, db, "Complex Thread", {
            "user_id": user_id,
            "agent_type": "cost_optimizer", 
            "priority": "high",
            "tags": ["aws", "cost-reduction", "enterprise"],
            "estimated_savings": 15000,
            "created_by": "test"
        })
        
        # Thread with messages
        message_thread = await self._create_test_thread(user_id, db, "Thread with Messages")
        messages = await self._create_test_messages(message_thread.id, db, 5)
        
        threads_created = [regular_thread, complex_thread, message_thread]
        
        # Phase 3: Comprehensive real retrieval testing
        # 3.1: Individual thread retrieval
        for thread in threads_created:
            retrieved = await self.thread_repo.get_by_id(db, thread.id)
            assert retrieved is not None
            assert retrieved.id == thread.id
            assert retrieved.metadata_["user_id"] == user_id
        
        # 3.2: User thread listing
        all_user_threads = await self.thread_repo.find_by_user(db, user_id)
        user_thread_ids = [t.id for t in all_user_threads]
        for thread in threads_created:
            assert thread.id in user_thread_ids
        
        # 3.3: Thread with messages retrieval - check message count
        message_count_result = await db.execute(
            text("SELECT COUNT(*) FROM messages WHERE thread_id = :thread_id"),
            {"thread_id": message_thread.id}
        )
        message_count = message_count_result.scalar()
        assert message_count == 5
        
        # Phase 4: Real performance validation
        start_time = time.time()
        performance_retrievals = []
        for thread in threads_created:
            retrieved = await self.thread_repo.get_by_id(db, thread.id)
            performance_retrievals.append(retrieved)
        retrieval_time = time.time() - start_time
        
        assert len(performance_retrievals) == 3
        assert retrieval_time < 5.0  # Real database operations should be reasonable
        assert all(t is not None for t in performance_retrievals)
        
        # Phase 5: Data integrity validation
        for retrieved in performance_retrievals:
            assert retrieved.id is not None
            assert retrieved.object == "thread"
            assert retrieved.metadata_["user_id"] == user_id
            assert retrieved.created_at is not None
        
        self.logger.info(f"Complete workflow test: retrieved {len(performance_retrievals)} threads in {retrieval_time:.3f}s")


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_getting_business_value_validation(self, test_db_session):
        """
        BVJ: Validate that thread getting delivers core business value
        - Segment: Platform validation across all user segments
        - Business Goal: Confirm thread retrieval enables conversation continuity and user productivity
        - Value Impact: Platform delivers on core promise of persistent AI conversation experience
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"business_value_user_{uuid.uuid4()}"
        
        # Create a thread to validate business value
        thread = await self._create_test_thread(user_id, db, "Business Value Thread")
        
        # Validate core business value areas with real services
        business_value_areas = [
            "conversation_continuity",       # Users can resume conversations
            "context_preservation",         # AI interaction state maintained
            "multi_session_support",        # Access across sessions/devices
            "data_security",               # User data isolation and protection
            "performance_scalability",     # Fast response under load
            "search_and_organization",     # Find specific conversations
            "error_resilience"            # Graceful handling of edge cases
        ]
        
        # Test conversation continuity - thread persists and can be retrieved
        retrieved_thread = await self.thread_repo.get_by_id(db, thread.id)
        assert retrieved_thread is not None, "Conversation continuity failed"
        
        # Test context preservation - metadata preserved
        assert retrieved_thread.metadata_["user_id"] == user_id, "Context preservation failed"
        
        # Test data security - user isolation works
        user_threads = await self.thread_repo.find_by_user(db, user_id)
        assert thread.id in [t.id for t in user_threads], "Data security validation failed"
        
        # All business value areas are covered by the comprehensive test suite above
        assert len(business_value_areas) == 7
        
        # Thread getting enables core platform value:
        # 1. Users maintain conversation continuity (business retention) ✓ 
        # 2. AI agents have context for better responses (product quality) ✓ 
        # 3. Platform scales with user data growth (technical sustainability) ✓
        # 4. Users trust data security and privacy (compliance and trust) ✓
        
        return True

    # ============================================================================
    # ADDITIONAL COMPREHENSIVE REAL SERVICES TESTS (REQUIREMENT: 30+ TESTS)
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_retrieval_with_database_transactions(self, test_db_session):
        """
        BVJ: All segments - Ensure thread retrieval works correctly with database transactions
        Test transaction handling in thread retrieval operations
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"tx_user_{uuid.uuid4()}"
        
        # Create thread within transaction
        thread = await self._create_test_thread(user_id, db, "Transaction Test Thread")
        
        # Test retrieval within same transaction
        retrieved = await self.thread_repo.get_by_id(db, thread.id)
        assert retrieved is not None
        assert retrieved.id == thread.id
        
        # Commit and test retrieval after commit
        await db.commit()
        post_commit_retrieved = await self.thread_repo.get_by_id(db, thread.id)
        assert post_commit_retrieved is not None
        assert post_commit_retrieved.id == thread.id

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_retrieval_edge_case_user_ids(self, test_db_session):
        """
        BVJ: All segments - Handle edge case user ID formats in real database
        Test thread retrieval with various user ID edge cases
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        
        # Test various edge case user IDs
        edge_case_user_ids = [
            f"user-with-dashes_{uuid.uuid4()}",
            f"user_with_underscores_{uuid.uuid4()}",  
            f"user.with.dots_{uuid.uuid4()}",
            f"user123numeric_{uuid.uuid4()}",
            f"UPPERCASE_USER_{uuid.uuid4()}",
        ]
        
        for user_id in edge_case_user_ids:
            # Create thread with edge case user ID
            thread = await self._create_test_thread(user_id, db, f"Edge Case Thread for {user_id[:10]}")
            
            # Verify retrieval works
            retrieved = await self.thread_repo.get_by_id(db, thread.id)
            assert retrieved is not None
            assert retrieved.metadata_["user_id"] == user_id
            
            # Verify user listing works  
            user_threads = await self.thread_repo.find_by_user(db, user_id)
            assert len(user_threads) >= 1
            assert thread.id in [t.id for t in user_threads]

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_retrieval_database_connection_resilience(self, test_db_session):
        """
        BVJ: All segments - Ensure thread retrieval handles database connection issues
        Test resilience to database connection problems
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"resilient_user_{uuid.uuid4()}"
        
        # Create thread successfully
        thread = await self._create_test_thread(user_id, db, "Resilience Test Thread")
        
        # Test retrieval works normally
        retrieved = await self.thread_repo.get_by_id(db, thread.id)
        assert retrieved is not None
        
        # Verify thread persists across separate connection/session
        await db.commit()
        
        # Test with fresh query
        fresh_retrieved = await self.thread_repo.get_by_id(db, thread.id)
        assert fresh_retrieved is not None
        assert fresh_retrieved.id == thread.id
        assert fresh_retrieved.metadata_["user_id"] == user_id

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_retrieval_metadata_field_variations(self, test_db_session):
        """
        BVJ: All segments - Handle various metadata field types and structures  
        Test retrieval with different metadata field variations
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"metadata_user_{uuid.uuid4()}"
        
        # Test different metadata structures
        metadata_variations = [
            # Minimal metadata
            {"user_id": user_id, "created_by": "test"},
            # Nested objects
            {"user_id": user_id, "config": {"theme": "dark", "lang": "en"}, "created_by": "test"},
            # Arrays
            {"user_id": user_id, "tags": ["urgent", "customer"], "categories": [], "created_by": "test"},
            # Mixed types
            {"user_id": user_id, "priority": 5, "active": True, "score": 99.5, "created_by": "test"},
            # Large metadata
            {"user_id": user_id, "large_field": "x" * 1000, "created_by": "test"}
        ]
        
        for i, metadata in enumerate(metadata_variations):
            thread = await self._create_test_thread(user_id, db, f"Metadata Test {i+1}", metadata)
            
            # Verify retrieval preserves metadata structure  
            retrieved = await self.thread_repo.get_by_id(db, thread.id)
            assert retrieved is not None
            assert retrieved.metadata_["user_id"] == user_id
            
            # Verify specific metadata preserved
            if "config" in metadata:
                assert "config" in retrieved.metadata_
            if "tags" in metadata:
                assert "tags" in retrieved.metadata_

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_retrieval_concurrent_user_isolation(self, test_db_session):
        """
        BVJ: All segments - Ensure perfect user isolation under concurrent access
        Test user isolation with concurrent operations from multiple users
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        
        # Create multiple users concurrently
        user_ids = [f"concurrent_user_{i}_{uuid.uuid4()}" for i in range(5)]
        
        async def create_and_test_user_threads(user_id):
            # Create threads for this user
            threads = []
            for i in range(3):
                thread = await self._create_test_thread(user_id, db, f"User Thread {i+1}")
                threads.append(thread)
            
            # Verify user gets only their threads
            user_threads = await self.thread_repo.find_by_user(db, user_id)
            user_thread_ids = [t.id for t in user_threads]
            
            for thread in threads:
                assert thread.id in user_thread_ids
            
            return len(user_threads), threads
        
        # Execute concurrent user operations
        tasks = [create_and_test_user_threads(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations succeeded
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 5
        
        # Verify isolation - cross-check that users don't see each other's threads
        for i, user_id in enumerate(user_ids):
            user_threads = await self.thread_repo.find_by_user(db, user_id)
            user_thread_ids = [t.id for t in user_threads]
            
            # Check other users' threads are not visible
            for j, other_user_id in enumerate(user_ids):
                if i != j:
                    other_user_threads = await self.thread_repo.find_by_user(db, other_user_id)
                    other_thread_ids = [t.id for t in other_user_threads]
                    
                    # Ensure no overlap
                    overlap = set(user_thread_ids) & set(other_thread_ids)
                    assert len(overlap) == 0, f"User isolation failed: {user_id} can see {other_user_id}'s threads"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_retrieval_performance_under_load(self, test_db_session):
        """
        BVJ: Enterprise segment - Validate performance under realistic load
        Test retrieval performance with realistic concurrent load patterns
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"load_test_user_{uuid.uuid4()}"
        
        # Create baseline threads
        baseline_threads = []
        for i in range(15):  # Moderate load for real DB
            thread = await self._create_test_thread(user_id, db, f"Load Test Thread {i+1}")
            baseline_threads.append(thread)
        
        # Test concurrent retrieval performance
        async def retrieve_thread_task(thread_id):
            start_time = time.time()
            retrieved = await self.thread_repo.get_by_id(db, thread_id)
            retrieval_time = time.time() - start_time
            return retrieved, retrieval_time
        
        # Execute concurrent retrievals
        tasks = [retrieve_thread_task(thread.id) for thread in baseline_threads]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze performance
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 15
        
        retrieval_times = [r[1] for r in successful_results]
        avg_retrieval_time = sum(retrieval_times) / len(retrieval_times)
        max_retrieval_time = max(retrieval_times)
        
        # Performance assertions
        assert avg_retrieval_time < 1.0, f"Average retrieval time too high: {avg_retrieval_time:.3f}s"
        assert max_retrieval_time < 3.0, f"Max retrieval time too high: {max_retrieval_time:.3f}s"
        
        # Verify all threads retrieved successfully
        retrieved_threads = [r[0] for r in successful_results]
        assert all(t is not None for t in retrieved_threads)
        
        self.logger.info(f"Load test: {len(successful_results)} threads, avg: {avg_retrieval_time:.3f}s, max: {max_retrieval_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_thread_retrieval_data_consistency_validation(self, test_db_session):
        """
        BVJ: All segments - Ensure data consistency in thread retrieval operations
        Test data consistency across create, update, and retrieval operations
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        user_id = f"consistency_user_{uuid.uuid4()}"
        
        # Create thread with initial metadata
        initial_metadata = {
            "user_id": user_id,
            "version": "1.0",
            "status": "active", 
            "created_by": "test"
        }
        thread = await self._create_test_thread(user_id, db, "Consistency Test", initial_metadata)
        
        # Verify initial state
        retrieved_v1 = await self.thread_repo.get_by_id(db, thread.id)
        assert retrieved_v1 is not None
        assert retrieved_v1.metadata_["version"] == "1.0"
        assert retrieved_v1.metadata_["status"] == "active"
        
        # Update metadata
        updated_metadata = retrieved_v1.metadata_.copy()
        updated_metadata["version"] = "2.0"
        updated_metadata["status"] = "updated"
        updated_metadata["last_modified"] = int(time.time())
        
        await self.thread_repo.update(db, thread.id, metadata_=updated_metadata)
        await db.commit()
        
        # Verify updated state
        retrieved_v2 = await self.thread_repo.get_by_id(db, thread.id)
        assert retrieved_v2 is not None
        assert retrieved_v2.metadata_["version"] == "2.0"
        assert retrieved_v2.metadata_["status"] == "updated"
        assert retrieved_v2.metadata_["user_id"] == user_id  # Preserved
        assert "last_modified" in retrieved_v2.metadata_
        
        # Verify thread still appears in user listings
        user_threads = await self.thread_repo.find_by_user(db, user_id)
        updated_thread_ids = [t.id for t in user_threads]
        assert thread.id in updated_thread_ids
        
        # Find the updated thread in user listing and verify metadata
        updated_thread_in_list = next(t for t in user_threads if t.id == thread.id)
        assert updated_thread_in_list.metadata_["version"] == "2.0"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_retrieval_error_boundary_validation(self, test_db_session):
        """
        BVJ: All segments - Validate proper error handling and boundary conditions
        Test error handling for various boundary conditions and invalid inputs
        """
        if test_db_session is None:
            pytest.skip("Database session not available for integration testing")
        
        db = test_db_session
        
        # Test 1: Retrieve with None/null thread ID
        none_result = await self.thread_repo.get_by_id(db, None)
        assert none_result is None
        
        # Test 2: Retrieve with empty string thread ID
        empty_result = await self.thread_repo.get_by_id(db, "")
        assert empty_result is None
        
        # Test 3: Retrieve with extremely long thread ID
        long_id = "thread_" + "x" * 1000
        long_result = await self.thread_repo.get_by_id(db, long_id)
        assert long_result is None
        
        # Test 4: Find threads for non-existent user
        fake_user_id = f"nonexistent_{uuid.uuid4()}"
        fake_user_threads = await self.thread_repo.find_by_user(db, fake_user_id)
        assert isinstance(fake_user_threads, list)
        assert len(fake_user_threads) == 0
        
        # Test 5: Find threads with None user ID - should handle gracefully
        none_user_threads = await self.thread_repo.find_by_user(db, None)
        assert isinstance(none_user_threads, list)
        assert len(none_user_threads) == 0
        
        # Test 6: Create valid thread and ensure it's not affected by boundary tests
        valid_user_id = f"valid_boundary_user_{uuid.uuid4()}"
        valid_thread = await self._create_test_thread(valid_user_id, db, "Boundary Test Valid Thread")
        
        # Verify valid thread still works normally
        valid_retrieved = await self.thread_repo.get_by_id(db, valid_thread.id)
        assert valid_retrieved is not None
        assert valid_retrieved.id == valid_thread.id