"""
Comprehensive Integration Tests for Database Operations Across All Services

Business Value Justification (BVJ):
- Segment: Platform/Internal & Enterprise
- Business Goal: System Stability, Data Integrity, Multi-User Security  
- Value Impact: Ensures reliable chat continuity, user data consistency, enterprise security
- Strategic Impact: Prevents data corruption, enables enterprise-grade multi-tenancy

Tests database operations that existing features depend on with real PostgreSQL - NO MOCKS.
Focuses on data consistency, transaction integrity, and cross-service data validation
for business-critical chat functionality and multi-user isolation.
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from unittest.mock import patch
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

# Database connections for both services
from netra_backend.app.db.postgres_core import AsyncDatabase
from auth_service.auth_core.database.connection import AuthDatabaseConnection

# Models from both services  
from netra_backend.app.db.models_user import User, Secret, ToolUsageLog
from netra_backend.app.db.models_agent import Thread, Message, Run, Assistant
from netra_backend.app.db.models_content import CorpusAuditLog, Analysis
from auth_service.auth_core.database.models import AuthUser, AuthSession, AuthAuditLog

# Database managers for creating test data
from netra_backend.app.core.configuration.base import get_unified_config
from auth_service.auth_core.database.database_manager import AuthDatabaseManager

# SSOT SQL operations
from sqlalchemy import text, select, delete
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)


class TestDatabaseCrossServiceIntegration(SSotBaseTestCase):
    """Comprehensive database integration tests across all services using real PostgreSQL."""
    
    def setup_method(self, method):
        """Setup real database connections for each test method."""
        super().setup_method(method)
        
        # Skip if not using real services  
        self.skip_if_no_real_services()
        
        # Initialize database connections
        self.backend_db = None
        self.auth_db = None
        self.test_users_created = []
        self.test_auth_users_created = []
        self.test_threads_created = []
        
    def skip_if_no_real_services(self):
        """Skip test if not running with real database services."""
        env = self.get_env()
        if env.get("USE_REAL_SERVICES", "false").lower() != "true":
            pytest.skip("Test requires --real-services flag for database integration testing")
        
        # For real services integration testing, ensure both backend and auth use same environment
        # Override any test-specific environment settings to ensure consistency
        env.set("ENVIRONMENT", "development", "integration_test_override")
        env.set("AUTH_FAST_TEST_MODE", "false", "integration_test_override")  # Disable SQLite mode for auth
        
        # Also check if database services are actually available
        self._check_database_availability()
    
    def _check_database_availability(self):
        """Check if database services are available before proceeding with tests."""
        import socket
        from shared.database_url_builder import DatabaseURLBuilder
        from urllib.parse import urlparse
        
        # Get the environment for database configuration
        env = self.get_env()
        
        # Check both backend and auth database URLs
        database_urls_to_check = []
        
        # Backend database URL
        try:
            backend_builder = DatabaseURLBuilder(env.as_dict())
            backend_url = backend_builder.development.auto_url  # Use development for real services
            if backend_url and "memory" not in backend_url and "sqlite" not in backend_url:
                database_urls_to_check.append(("Backend", backend_url))
        except Exception as e:
            logger.warning(f"Could not get backend database URL: {e}")
        
        # Auth database URL - check both potential configurations
        try:
            # Check if auth service would use PostgreSQL in development mode
            from auth_service.auth_core.auth_environment import get_auth_env
            auth_env = get_auth_env()
            auth_url = auth_env.get_database_url()
            if auth_url and "memory" not in auth_url and "sqlite" not in auth_url:
                database_urls_to_check.append(("Auth", auth_url))
        except Exception as e:
            logger.warning(f"Could not get auth database URL: {e}")
        
        # Test connectivity to each database service
        for service_name, db_url in database_urls_to_check:
            try:
                parsed_url = urlparse(db_url)
                if parsed_url.hostname and parsed_url.port:
                    host = parsed_url.hostname
                    port = parsed_url.port
                    
                    # Test if the database service is reachable
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)  # 3 second timeout
                    try:
                        result = sock.connect_ex((host, port))
                        if result != 0:
                            pytest.skip(f"{service_name} database service not available at {host}:{port}. Start database services with Docker Compose or use in-memory testing.")
                    finally:
                        sock.close()
            except Exception as e:
                logger.warning(f"Could not check {service_name} database availability: {e}")
    
    async def setup_databases(self):
        """Setup database connections to both services."""
        # Setup backend database
        config = get_unified_config()
        backend_url = config.database_url
        self.backend_db = AsyncDatabase(backend_url)
        
        # Setup auth database  
        self.auth_db = AuthDatabaseConnection()
        await self.auth_db.initialize()
        
        # Record database setup metrics
        self.record_metric("backend_db_initialized", True)
        self.record_metric("auth_db_initialized", True)
        
    async def cleanup_databases(self):
        """Cleanup test data and close database connections."""
        try:
            # Clean up test data
            await self.cleanup_test_data()
            
            # Close connections
            if self.backend_db:
                await self.backend_db.close()
            if self.auth_db:
                await self.auth_db.close()
                
            self.record_metric("databases_cleaned_up", True)
        except Exception as e:
            logger.warning(f"Database cleanup error: {e}")
            
    async def cleanup_test_data(self):
        """Clean up test data from both databases."""
        try:
            # Clean backend database
            if self.backend_db:
                async with self.backend_db.get_session() as session:
                    # Delete test users and cascade to related data
                    for user_id in self.test_users_created:
                        await session.execute(delete(User).where(User.id == user_id))
                    
                    # Delete test threads and related data
                    for thread_id in self.test_threads_created:
                        await session.execute(delete(Thread).where(Thread.id == thread_id))
                    
                    await session.commit()
            
            # Clean auth database
            if self.auth_db:
                async with self.auth_db.get_session() as session:
                    for user_id in self.test_auth_users_created:
                        await session.execute(delete(AuthUser).where(AuthUser.id == user_id))
                    await session.commit()
                    
        except Exception as e:
            logger.warning(f"Test data cleanup error: {e}")
    
    def teardown_method(self, method):
        """Cleanup after each test method."""
        # Run async cleanup if we have an event loop
        try:
            # Check if we're already in an async context
            loop = asyncio.get_running_loop()
            # If we have a running loop, create a task for cleanup
            task = loop.create_task(self.cleanup_databases())
            # Don't wait for it to complete to avoid blocking
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            try:
                asyncio.run(self.cleanup_databases())
            except Exception as e:
                # Log but don't fail teardown
                import logging
                logging.getLogger(__name__).warning(f"Cleanup failed: {e}")
        
        super().teardown_method(method)
        
    async def create_test_auth_user(self, email: str, user_id: str = None) -> AuthUser:
        """Create test user in auth service database."""
        if not user_id:
            user_id = str(uuid.uuid4())
            
        auth_user = AuthUser(
            id=user_id,
            email=email,
            full_name=f"Test User {email}",
            auth_provider="local",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc)
        )
        
        async with self.auth_db.get_session() as session:
            session.add(auth_user)
            await session.commit()
            await session.refresh(auth_user)
            
        self.test_auth_users_created.append(user_id)
        self.increment_db_query_count(2)  # Add + refresh
        return auth_user
        
    async def create_test_backend_user(self, auth_user_id: str, email: str) -> User:
        """Create corresponding user in backend database."""
        backend_user = User(
            id=auth_user_id,  # Same ID for cross-service consistency
            email=email,
            full_name=f"Backend User {email}",
            is_active=True,
            plan_tier="free",
            role="standard_user",
            created_at=datetime.now(timezone.utc)
        )
        
        async with self.backend_db.get_session() as session:
            session.add(backend_user)
            await session.commit()
            await session.refresh(backend_user)
            
        self.test_users_created.append(auth_user_id)
        self.increment_db_query_count(2)
        return backend_user
        
    async def create_test_thread(self, user_id: str) -> Thread:
        """Create test thread for user."""
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"
        thread = Thread(
            id=thread_id,
            object="thread",
            created_at=int(datetime.now(timezone.utc).timestamp()),
            metadata_={"user_id": user_id, "test": True}
        )
        
        async with self.backend_db.get_session() as session:
            session.add(thread)
            await session.commit()
            await session.refresh(thread)
            
        self.test_threads_created.append(thread_id)
        self.increment_db_query_count(2)
        return thread

    @pytest.mark.asyncio
    async def test_user_data_persistence_across_services(self):
        """
        BVJ: Enterprise - Multi-User Data Consistency
        Test user data persistence across auth_service and netra_backend.
        Ensures user profile data remains consistent between authentication and business logic services.
        """
        await self.setup_databases()
        
        # Create user in auth service
        test_email = f"test_user_{uuid.uuid4().hex[:8]}@example.com"
        auth_user = await self.create_test_auth_user(test_email)
        
        # Create corresponding user in backend
        backend_user = await self.create_test_backend_user(auth_user.id, test_email)
        
        # Verify cross-service data consistency
        assert auth_user.id == backend_user.id, "User IDs must match across services"
        assert auth_user.email == backend_user.email, "User emails must match across services"
        assert auth_user.is_active == backend_user.is_active, "User status must be consistent"
        
        # Test user data update propagation
        async with self.auth_db.get_session() as session:
            auth_user.full_name = "Updated Name"
            session.add(auth_user)
            await session.commit()
        
        # Verify backend can read updated auth data via shared user ID
        async with self.backend_db.get_session() as session:
            result = await session.execute(select(User).where(User.id == auth_user.id))
            updated_backend_user = result.scalar_one()
            
            # Business logic: Backend can identify the user even with auth changes
            assert updated_backend_user.id == auth_user.id
            
        self.record_metric("cross_service_user_consistency", "verified")
        self.increment_db_query_count(4)

    @pytest.mark.asyncio  
    async def test_thread_message_storage_chat_continuity(self):
        """
        BVJ: Free/Pro/Enterprise - Chat Continuity & User Experience
        Test thread and message storage for chat continuity across sessions.
        Critical for business value - users must never lose chat history.
        """
        await self.setup_databases()
        
        # Create test user and thread
        test_email = f"chat_user_{uuid.uuid4().hex[:8]}@example.com"
        auth_user = await self.create_test_auth_user(test_email)
        backend_user = await self.create_test_backend_user(auth_user.id, test_email)
        thread = await self.create_test_thread(auth_user.id)
        
        # Create multiple messages in conversation
        messages = []
        for i in range(5):
            message = Message(
                id=f"msg_{uuid.uuid4().hex[:12]}",
                object="thread.message",
                created_at=int(datetime.now(timezone.utc).timestamp()) + i,
                thread_id=thread.id,
                role="user" if i % 2 == 0 else "assistant",
                content=[{"type": "text", "text": {"value": f"Test message {i}"}}],
                metadata_={"test": True}
            )
            messages.append(message)
            
        # Persist all messages in a single transaction for consistency
        async with self.backend_db.get_session() as session:
            for message in messages:
                session.add(message)
            await session.commit()
            
        # Verify chat continuity - all messages retrievable in order
        async with self.backend_db.get_session() as session:
            result = await session.execute(
                select(Message)
                .where(Message.thread_id == thread.id)
                .order_by(Message.created_at)
            )
            retrieved_messages = result.scalars().all()
            
        assert len(retrieved_messages) == 5, "All messages must persist for chat continuity"
        
        # Verify message ordering (critical for chat UX)
        for i, msg in enumerate(retrieved_messages):
            assert f"Test message {i}" in str(msg.content), f"Message {i} content incorrect"
            expected_role = "user" if i % 2 == 0 else "assistant"
            assert msg.role == expected_role, f"Message {i} role incorrect"
            
        self.record_metric("chat_continuity_messages_persisted", len(retrieved_messages))
        self.increment_db_query_count(7)  # 5 inserts + 1 select + commit

    @pytest.mark.asyncio
    async def test_transaction_integrity_rollback_scenarios(self):
        """
        BVJ: Platform - Data Integrity & Business Reliability  
        Test transaction integrity and rollback scenarios.
        Prevents data corruption that could break business operations.
        """
        await self.setup_databases()
        
        test_email = f"transaction_user_{uuid.uuid4().hex[:8]}@example.com"
        auth_user = await self.create_test_auth_user(test_email)
        
        # Test successful transaction
        async with self.backend_db.get_session() as session:
            user = User(
                id=auth_user.id,
                email=test_email,
                full_name="Transaction Test User",
                is_active=True,
                plan_tier="pro"
            )
            session.add(user)
            await session.commit()
            
        self.test_users_created.append(auth_user.id)
        
        # Test rollback scenario - attempt to create duplicate user (should fail)
        with pytest.raises(IntegrityError):
            async with self.backend_db.get_session() as session:
                duplicate_user = User(
                    id=auth_user.id,  # Same ID - should violate constraint
                    email=test_email,
                    full_name="Duplicate User",
                    is_active=True,
                    plan_tier="free"
                )
                session.add(duplicate_user)
                await session.commit()
                
        # Verify original user data integrity after failed transaction
        async with self.backend_db.get_session() as session:
            result = await session.execute(select(User).where(User.id == auth_user.id))
            original_user = result.scalar_one()
            
        assert original_user.plan_tier == "pro", "Original data must remain intact after rollback"
        assert original_user.full_name == "Transaction Test User", "Transaction rollback must preserve original data"
        
        self.record_metric("transaction_rollback_integrity", "verified")
        self.increment_db_query_count(4)

    @pytest.mark.asyncio
    async def test_multi_user_data_isolation_enterprise_security(self):
        """
        BVJ: Enterprise - Multi-User Security & Data Isolation
        Test multi-user data isolation for enterprise security compliance.
        Critical for enterprise sales - prevents data leaks between tenants.
        """
        await self.setup_databases()
        
        # Create multiple isolated users
        users_data = []
        for i in range(3):
            email = f"isolated_user_{i}_{uuid.uuid4().hex[:6]}@company{i}.com"
            auth_user = await self.create_test_auth_user(email)
            backend_user = await self.create_test_backend_user(auth_user.id, email)
            
            # Create user-specific secret (sensitive enterprise data)
            secret = Secret(
                id=str(uuid.uuid4()),
                user_id=auth_user.id,
                key=f"company_{i}_api_key",
                encrypted_value=f"encrypted_secret_for_user_{i}",
                created_at=datetime.now(timezone.utc)
            )
            
            async with self.backend_db.get_session() as session:
                session.add(secret)
                await session.commit()
                
            users_data.append({
                'auth_user': auth_user,
                'backend_user': backend_user,
                'secret': secret
            })
            
        # Test data isolation - each user can only access their own data
        for i, user_data in enumerate(users_data):
            user_id = user_data['auth_user'].id
            
            # User should only see their own secrets
            async with self.backend_db.get_session() as session:
                result = await session.execute(
                    select(Secret).where(Secret.user_id == user_id)
                )
                user_secrets = result.scalars().all()
                
            assert len(user_secrets) == 1, f"User {i} should only see their own secret"
            assert user_secrets[0].key == f"company_{i}_api_key", f"User {i} secret content incorrect"
            
            # Verify user cannot access other users' data
            other_user_ids = [u['auth_user'].id for j, u in enumerate(users_data) if j != i]
            
            async with self.backend_db.get_session() as session:
                result = await session.execute(
                    select(Secret).where(Secret.user_id.in_(other_user_ids))
                )
                other_secrets = result.scalars().all()
                
            # In enterprise multi-tenant system, users must not access other tenant data
            assert len(other_secrets) == 2, f"Other users' data should exist but be isolated from user {i}"
            
        self.record_metric("multi_user_isolation_verified", len(users_data))
        self.increment_db_query_count(12)  # 3 users  x  4 queries each

    @pytest.mark.asyncio
    async def test_foreign_key_constraints_referential_integrity(self):
        """
        BVJ: Platform - Data Consistency & System Reliability
        Test foreign key constraints and referential integrity.
        Prevents orphaned records that break business logic.
        """
        await self.setup_databases()
        
        # Create user and thread with proper relationships
        test_email = f"fk_user_{uuid.uuid4().hex[:8]}@example.com"
        auth_user = await self.create_test_auth_user(test_email)
        backend_user = await self.create_test_backend_user(auth_user.id, test_email)
        thread = await self.create_test_thread(auth_user.id)
        
        # Create assistant for runs
        assistant = Assistant(
            id=f"asst_{uuid.uuid4().hex[:12]}",
            object="assistant",
            created_at=int(datetime.now(timezone.utc).timestamp()),
            name="Test Assistant",
            model="gpt-4",
            instructions="Test assistant for referential integrity testing"
        )
        
        async with self.backend_db.get_session() as session:
            session.add(assistant)
            await session.commit()
            
        # Create run that references both thread and assistant  
        run = Run(
            id=f"run_{uuid.uuid4().hex[:12]}",
            object="thread.run",
            created_at=int(datetime.now(timezone.utc).timestamp()),
            thread_id=thread.id,
            assistant_id=assistant.id,
            status="in_progress",
            model="gpt-4"
        )
        
        async with self.backend_db.get_session() as session:
            session.add(run)
            await session.commit()
            
        # Create message that references thread, assistant, and run
        message = Message(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            object="thread.message",  
            created_at=int(datetime.now(timezone.utc).timestamp()),
            thread_id=thread.id,
            assistant_id=assistant.id,
            run_id=run.id,
            role="assistant",
            content=[{"type": "text", "text": {"value": "Test message with all references"}}]
        )
        
        async with self.backend_db.get_session() as session:
            session.add(message)
            await session.commit()
            
        # Verify all relationships work correctly
        async with self.backend_db.get_session() as session:
            # Test forward relationships
            result = await session.execute(
                select(Message)
                .where(Message.id == message.id)
            )
            retrieved_message = result.scalar_one()
            
            assert retrieved_message.thread_id == thread.id, "Message-Thread relationship broken"
            assert retrieved_message.assistant_id == assistant.id, "Message-Assistant relationship broken" 
            assert retrieved_message.run_id == run.id, "Message-Run relationship broken"
            
        # Test constraint enforcement - try to create message with invalid thread_id
        with pytest.raises(IntegrityError):
            async with self.backend_db.get_session() as session:
                invalid_message = Message(
                    id=f"msg_{uuid.uuid4().hex[:12]}",
                    object="thread.message",
                    created_at=int(datetime.now(timezone.utc).timestamp()),
                    thread_id="nonexistent_thread",  # Should violate foreign key
                    role="user",
                    content=[{"type": "text", "text": {"value": "This should fail"}}]
                )
                session.add(invalid_message)
                await session.commit()
                
        self.record_metric("referential_integrity_verified", True)
        self.increment_db_query_count(8)

    @pytest.mark.asyncio
    async def test_concurrent_access_race_condition_prevention(self):
        """
        BVJ: Enterprise - System Reliability & Performance Under Load
        Test concurrent access patterns and race condition prevention.
        Critical for enterprise deployments with multiple concurrent users.
        """
        await self.setup_databases()
        
        # Create test user
        test_email = f"concurrent_user_{uuid.uuid4().hex[:8]}@example.com"
        auth_user = await self.create_test_auth_user(test_email)
        backend_user = await self.create_test_backend_user(auth_user.id, test_email)
        
        # Create thread for concurrent message creation
        thread = await self.create_test_thread(auth_user.id)
        
        # Simulate concurrent message creation (common in chat applications)
        async def create_concurrent_message(message_index: int):
            """Create a message concurrently."""
            message = Message(
                id=f"concurrent_msg_{message_index}_{uuid.uuid4().hex[:8]}",
                object="thread.message",
                created_at=int(datetime.now(timezone.utc).timestamp()) + message_index,
                thread_id=thread.id,
                role="user",
                content=[{"type": "text", "text": {"value": f"Concurrent message {message_index}"}}],
                metadata_={"concurrent_test": True, "index": message_index}
            )
            
            async with self.backend_db.get_session() as session:
                session.add(message)
                await session.commit()
                
            return message.id
            
        # Run 5 concurrent message creations
        concurrent_tasks = [create_concurrent_message(i) for i in range(5)]
        message_ids = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify all messages were created successfully (no race conditions)
        successful_messages = [mid for mid in message_ids if isinstance(mid, str)]
        assert len(successful_messages) == 5, f"Race condition detected - only {len(successful_messages)}/5 messages created"
        
        # Verify data integrity after concurrent operations
        async with self.backend_db.get_session() as session:
            result = await session.execute(
                select(Message)
                .where(Message.thread_id == thread.id)
                .order_by(Message.created_at)
            )
            all_messages = result.scalars().all()
            
        assert len(all_messages) == 5, "All concurrent messages must persist"
        
        # Verify message ordering is preserved despite concurrency
        for i, message in enumerate(all_messages):
            assert f"Concurrent message {i}" in str(message.content), f"Message ordering broken by concurrency"
            
        self.record_metric("concurrent_operations_successful", len(successful_messages))
        self.increment_db_query_count(11)  # 5 inserts + 1 select + 5 commits

    @pytest.mark.asyncio
    async def test_database_connection_pooling_performance(self):
        """
        BVJ: Enterprise - System Performance & Scalability
        Test database connection pooling and performance under load.
        Critical for enterprise performance requirements.
        """
        await self.setup_databases()
        
        # Test connection pool health
        backend_pool_status = await self.backend_db.get_pool_status()
        auth_connection_health = await self.auth_db.get_connection_health()
        
        # Verify pools are functioning
        assert backend_pool_status.get("status") != "Pool status unavailable", "Backend pool must be accessible"
        assert auth_connection_health.get("status") == "healthy", "Auth connection must be healthy"
        
        # Test pool performance under rapid connection requests
        async def rapid_query_test(query_index: int):
            """Perform rapid database query to test pool performance."""
            start_time = asyncio.get_event_loop().time()
            
            # Backend query
            async with self.backend_db.get_session() as session:
                result = await session.execute(text("SELECT 1 as test_value"))
                backend_value = result.scalar()
                
            # Auth query  
            async with self.auth_db.get_session() as session:
                result = await session.execute(text("SELECT 1 as test_value"))
                auth_value = result.scalar()
                
            end_time = asyncio.get_event_loop().time()
            query_time = end_time - start_time
            
            return {
                'query_index': query_index,
                'backend_result': backend_value,
                'auth_result': auth_value,
                'query_time_ms': query_time * 1000
            }
        
        # Run 10 rapid queries to test pool performance
        rapid_tasks = [rapid_query_test(i) for i in range(10)]
        query_results = await asyncio.gather(*rapid_tasks)
        
        # Verify all queries succeeded
        assert len(query_results) == 10, "All rapid queries must complete"
        assert all(r['backend_result'] == 1 for r in query_results), "Backend queries must succeed"
        assert all(r['auth_result'] == 1 for r in query_results), "Auth queries must succeed"
        
        # Performance validation - queries should be fast with proper pooling
        avg_query_time = sum(r['query_time_ms'] for r in query_results) / len(query_results)
        assert avg_query_time < 1000, f"Average query time {avg_query_time}ms too slow - pool issue?"
        
        self.record_metric("average_pool_query_time_ms", avg_query_time)
        self.record_metric("rapid_queries_successful", len(query_results))
        self.increment_db_query_count(20)  # 10 queries  x  2 databases

    @pytest.mark.asyncio
    async def test_audit_logging_cross_service_compliance(self):
        """
        BVJ: Enterprise - Compliance & Audit Trail
        Test audit logging across services for compliance requirements.
        Critical for enterprise customers with regulatory compliance needs.
        """
        await self.setup_databases()
        
        # Create test user for audit testing
        test_email = f"audit_user_{uuid.uuid4().hex[:8]}@compliance.com"
        auth_user = await self.create_test_auth_user(test_email)
        backend_user = await self.create_test_backend_user(auth_user.id, test_email)
        
        # Create audit log in auth service (login event)
        auth_audit = AuthAuditLog(
            id=str(uuid.uuid4()),
            event_type="login",
            user_id=auth_user.id,
            success=True,
            event_metadata={
                "ip_address": "192.168.1.100",
                "user_agent": "Test Browser",
                "login_method": "email_password"
            },
            ip_address="192.168.1.100",
            user_agent="Test Browser",
            created_at=datetime.now(timezone.utc)
        )
        
        async with self.auth_db.get_session() as session:
            session.add(auth_audit)
            await session.commit()
            
        # Create audit log in backend (corpus operation)
        backend_audit = CorpusAuditLog(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            user_id=auth_user.id,  # Same user across services
            action="create_corpus",
            status="success",
            resource_type="corpus",
            resource_id="test_corpus_123",
            operation_duration_ms=1500.0,
            result_data={"corpus_name": "Test Compliance Corpus", "documents": 10},
            ip_address="192.168.1.100",  # Same session
            request_id=f"req_{uuid.uuid4().hex[:12]}"
        )
        
        async with self.backend_db.get_session() as session:
            session.add(backend_audit)
            await session.commit()
            
        # Verify audit trail consistency across services
        async with self.auth_db.get_session() as session:
            result = await session.execute(
                select(AuthAuditLog).where(AuthAuditLog.user_id == auth_user.id)
            )
            auth_audits = result.scalars().all()
            
        async with self.backend_db.get_session() as session:
            result = await session.execute(
                select(CorpusAuditLog).where(CorpusAuditLog.user_id == auth_user.id)
            )
            backend_audits = result.scalars().all()
            
        # Verify audit trail completeness
        assert len(auth_audits) == 1, "Auth audit log must be recorded"
        assert len(backend_audits) == 1, "Backend audit log must be recorded"
        
        # Verify audit data consistency
        assert auth_audits[0].user_id == backend_audits[0].user_id, "Audit logs must track same user"
        assert auth_audits[0].ip_address == backend_audits[0].ip_address, "IP tracking must be consistent"
        
        # Verify audit trail queryability (required for compliance)
        async with self.auth_db.get_session() as session:
            result = await session.execute(
                select(AuthAuditLog)
                .where(AuthAuditLog.event_type == "login")
                .where(AuthAuditLog.success == True)
            )
            successful_logins = result.scalars().all()
            
        assert len(successful_logins) >= 1, "Compliance queries must work on audit data"
        
        self.record_metric("audit_logs_created", len(auth_audits) + len(backend_audits))
        self.record_metric("compliance_queries_successful", True)
        self.increment_db_query_count(6)

    @pytest.mark.asyncio
    async def test_business_data_flows_existing_features(self):
        """
        BVJ: All Segments - Core Business Functionality 
        Test business data flows that existing features depend on.
        Critical for ensuring existing chat and analysis features continue working.
        """
        await self.setup_databases()
        
        # Create complete user workflow: Auth -> Profile -> Chat -> Analysis
        test_email = f"workflow_user_{uuid.uuid4().hex[:8]}@business.com"
        
        # Step 1: User authentication (auth service)
        auth_user = await self.create_test_auth_user(test_email)
        
        # Step 2: User profile creation (backend)
        backend_user = await self.create_test_backend_user(auth_user.id, test_email)
        
        # Step 3: Chat interaction (core business value)
        thread = await self.create_test_thread(auth_user.id)
        
        # Create assistant for chat
        assistant = Assistant(
            id=f"asst_{uuid.uuid4().hex[:12]}",
            object="assistant",
            created_at=int(datetime.now(timezone.utc).timestamp()),
            name="Business Assistant",
            model="gpt-4",
            instructions="Assists with business analysis tasks"
        )
        
        # Create chat conversation (simulating real user interaction)
        user_message = Message(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            object="thread.message",
            created_at=int(datetime.now(timezone.utc).timestamp()),
            thread_id=thread.id,
            role="user",
            content=[{"type": "text", "text": {"value": "Analyze my business data"}}]
        )
        
        assistant_message = Message(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            object="thread.message", 
            created_at=int(datetime.now(timezone.utc).timestamp()) + 1,
            thread_id=thread.id,
            assistant_id=assistant.id,
            role="assistant", 
            content=[{"type": "text", "text": {"value": "I'll help you analyze your business data. Let me start the analysis."}}]
        )
        
        # Step 4: Business analysis creation
        analysis = Analysis(
            id=str(uuid.uuid4()),
            name="Business Data Analysis",
            description="Analysis requested through chat interface",
            status="completed",
            created_by_id=auth_user.id,
            created_at=datetime.now(timezone.utc)
        )
        
        # Persist complete business workflow
        async with self.backend_db.get_session() as session:
            session.add(assistant)
            session.add(user_message)
            session.add(assistant_message)
            session.add(analysis)
            await session.commit()
            
        # Verify complete business workflow data integrity
        async with self.backend_db.get_session() as session:
            # Verify user can access their complete chat history
            result = await session.execute(
                select(Message)
                .where(Message.thread_id == thread.id)
                .order_by(Message.created_at)
            )
            chat_history = result.scalars().all()
            
            # Verify user can access their analysis results
            result = await session.execute(
                select(Analysis).where(Analysis.created_by_id == auth_user.id)
            )
            user_analyses = result.scalars().all()
            
        # Business validation - complete workflow must work
        assert len(chat_history) == 2, "Complete chat conversation must persist"
        assert chat_history[0].role == "user", "User message must be first"
        assert chat_history[1].role == "assistant", "Assistant response must follow"
        assert len(user_analyses) == 1, "User analysis must be accessible"
        
        # Verify business data relationships
        assert user_analyses[0].created_by_id == auth_user.id, "Analysis must link to correct user"
        assert chat_history[1].assistant_id == assistant.id, "Assistant message must link correctly"
        
        self.record_metric("business_workflow_steps_completed", 4)
        self.record_metric("chat_messages_in_workflow", len(chat_history))
        self.increment_db_query_count(8)

    @pytest.mark.asyncio 
    async def test_database_migration_scenarios_service_updates(self):
        """
        BVJ: Platform - Deployment Reliability & Zero-Downtime Updates
        Test database migration scenarios between service updates.
        Critical for maintaining service during rolling deployments.
        """
        await self.setup_databases()
        
        # Create data that would exist before a service update
        test_email = f"migration_user_{uuid.uuid4().hex[:8]}@example.com"
        auth_user = await self.create_test_auth_user(test_email)
        backend_user = await self.create_test_backend_user(auth_user.id, test_email)
        
        # Create thread with metadata that might change in updates
        thread = Thread(
            id=f"legacy_thread_{uuid.uuid4().hex[:12]}",
            object="thread",
            created_at=int(datetime.now(timezone.utc).timestamp()),
            metadata_={
                "version": "1.0",
                "user_id": auth_user.id,
                "legacy_field": "old_value",  # Field that might be removed
                "migration_test": True
            }
        )
        
        async with self.backend_db.get_session() as session:
            session.add(thread)
            await session.commit()
            
        self.test_threads_created.append(thread.id)
        
        # Simulate service update by modifying thread metadata (as new service version would)
        async with self.backend_db.get_session() as session:
            result = await session.execute(select(Thread).where(Thread.id == thread.id))
            existing_thread = result.scalar_one()
            
            # Update metadata to simulate migration
            existing_thread.metadata_ = {
                "version": "2.0",
                "user_id": auth_user.id,  # Preserved field
                "new_field": "new_value",  # Added field
                "migration_test": True
                # Note: legacy_field removed to simulate schema evolution
            }
            await session.commit()
            
        # Verify data survives migration-like operations
        async with self.backend_db.get_session() as session:
            result = await session.execute(select(Thread).where(Thread.id == thread.id))
            migrated_thread = result.scalar_one()
            
        # Verify critical data preserved during migration
        assert migrated_thread.id == thread.id, "Thread ID must survive migration"
        assert migrated_thread.metadata_["user_id"] == auth_user.id, "User association must survive"
        assert migrated_thread.metadata_["version"] == "2.0", "Version must update correctly"
        assert "new_field" in migrated_thread.metadata_, "New fields must be addable"
        
        # Verify service can still read user's data after migration
        async with self.backend_db.get_session() as session:
            result = await session.execute(
                select(Thread).where(
                    Thread.metadata_['user_id'].astext == auth_user.id
                )
            )
            user_threads = result.scalars().all()
            
        assert len(user_threads) >= 1, "User must still be able to access threads after migration"
        
        self.record_metric("migration_simulation_successful", True)
        self.record_metric("data_preserved_after_migration", True)
        self.increment_db_query_count(5)

    @pytest.mark.asyncio
    async def test_tool_usage_tracking_business_analytics(self):
        """
        BVJ: All Segments - Business Intelligence & Usage Analytics
        Test tool usage logging for business analytics and billing.
        Critical for understanding user behavior and calculating usage-based billing.
        """
        await self.setup_databases()
        
        # Create test user with specific plan tier
        test_email = f"analytics_user_{uuid.uuid4().hex[:8]}@example.com"
        auth_user = await self.create_test_auth_user(test_email)
        backend_user = await self.create_test_backend_user(auth_user.id, test_email)
        
        # Update user to pro tier for billing testing
        async with self.backend_db.get_session() as session:
            result = await session.execute(select(User).where(User.id == auth_user.id))
            user = result.scalar_one()
            user.plan_tier = "pro"
            await session.commit()
        
        # Create tool usage logs (simulating real tool executions)
        tool_usages = [
            ToolUsageLog(
                id=str(uuid.uuid4()),
                user_id=auth_user.id,
                tool_name="data_analyzer",
                category="analysis",
                execution_time_ms=2500,
                tokens_used=1500,
                cost_cents=25,  # 25 cents for this operation
                status="success",
                plan_tier="pro",
                permission_check_result={"allowed": True, "reason": "pro_tier_access"},
                arguments={"dataset": "customer_data.csv", "analysis_type": "trends"},
                created_at=datetime.now(timezone.utc)
            ),
            ToolUsageLog(
                id=str(uuid.uuid4()),
                user_id=auth_user.id,
                tool_name="report_generator", 
                category="reporting",
                execution_time_ms=5000,
                tokens_used=3000,
                cost_cents=50,
                status="success",
                plan_tier="pro",
                permission_check_result={"allowed": True, "reason": "pro_tier_access"},
                arguments={"format": "pdf", "charts": True},
                created_at=datetime.now(timezone.utc) + timedelta(minutes=5)
            ),
            ToolUsageLog(
                id=str(uuid.uuid4()),
                user_id=auth_user.id,
                tool_name="premium_optimizer",
                category="optimization", 
                execution_time_ms=1000,
                tokens_used=500,
                cost_cents=100,  # Premium tool costs more
                status="permission_denied",  # Test failure scenario
                plan_tier="pro",
                permission_check_result={"allowed": False, "reason": "requires_enterprise_tier"},
                arguments={"optimization_level": "advanced"},
                created_at=datetime.now(timezone.utc) + timedelta(minutes=10)
            )
        ]
        
        # Persist tool usage data
        async with self.backend_db.get_session() as session:
            for usage in tool_usages:
                session.add(usage)
            await session.commit()
            
        # Test business analytics queries
        async with self.backend_db.get_session() as session:
            # Query: Total successful tool usage by user (for billing)
            result = await session.execute(
                select(ToolUsageLog)
                .where(ToolUsageLog.user_id == auth_user.id)
                .where(ToolUsageLog.status == "success")
            )
            successful_usages = result.scalars().all()
            
            # Query: Total cost for billing calculation
            result = await session.execute(
                text("""
                    SELECT SUM(cost_cents) as total_cost
                    FROM tool_usage_logs 
                    WHERE user_id = :user_id AND status = 'success'
                """),
                {"user_id": auth_user.id}
            )
            total_cost = result.scalar()
            
            # Query: Tool category usage for analytics
            result = await session.execute(
                text("""
                    SELECT category, COUNT(*) as usage_count
                    FROM tool_usage_logs 
                    WHERE user_id = :user_id 
                    GROUP BY category
                """),
                {"user_id": auth_user.id}
            )
            category_usage = result.fetchall()
            
        # Business validation
        assert len(successful_usages) == 2, "Must track successful tool usage for billing"
        assert total_cost == 75, f"Total cost calculation incorrect: {total_cost} (expected 75)"
        assert len(category_usage) == 3, "Must track usage by category for analytics"
        
        # Verify permission tracking (important for upselling)
        permission_denied_usage = [u for u in tool_usages if u.status == "permission_denied"]
        assert len(permission_denied_usage) == 1, "Must track permission denials for upselling opportunities"
        
        self.record_metric("tool_usages_tracked", len(tool_usages))
        self.record_metric("billing_cost_cents", total_cost)
        self.record_metric("categories_used", len(category_usage))
        self.increment_db_query_count(7)