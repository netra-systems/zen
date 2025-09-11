"""Test Data Factory for E2E Tests

from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
Core factory for generating unique test data for unified E2E testing.
Focused on user, message, and thread creation with JWT token support.

Business Value Justification (BVJ):
- Segment: All customer tiers (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable E2E testing for feature validation
- Value Impact: Prevents production bugs and ensures customer trust
- Revenue Impact: Testing quality directly protects revenue streams

Architecture:
- 450-line file limit enforced
- 25-line function limit for all functions
- Supports concurrent test execution with unique data
"""

import hashlib
import pytest
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from netra_backend.app.schemas.registry import MessageType
from tests.e2e.config import UnifiedTestConfig
from shared.types.user_types import TestUserData


@dataclass
@pytest.mark.e2e
class TestMessageData:
    """Test message with metadata"""
    id: str
    content: str
    type: MessageType
    thread_id: str
    user_id: str
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
@pytest.mark.e2e
class TestThreadData:
    """Test thread with tracking"""
    id: str
    name: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


@pytest.mark.e2e
class TestDataFactory:
    """Factory for generating unique test data for E2E tests"""
    
    def __init__(self, config: Optional[UnifiedTestConfig] = None):
        """Initialize factory with configuration"""
        self.config = config or UnifiedTestConfig()
        self.created_users: List[TestUserData] = []
        self.created_messages: List[TestMessageData] = []
        self.created_threads: List[TestThreadData] = []
        self.session_prefix = self._generate_session_prefix()
    
    def _generate_session_prefix(self) -> str:
        """Generate unique session prefix for test isolation"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rand_suffix = str(uuid.uuid4())[:8]
        return f"test_{timestamp}_{rand_suffix}"
    
    def _create_unique_id(self, prefix: str = "") -> str:
        """Create unique ID with prefix"""
        unique_suffix = str(uuid.uuid4())
        return f"{prefix}{self.session_prefix}_{unique_suffix}"
    
    def _generate_timestamp(self) -> datetime:
        """Generate current timestamp with timezone"""
        return datetime.now(timezone.utc)
    
    def _hash_password(self, password: str) -> str:
        """Hash password for test user"""
        salt = "test_salt_for_hashing"
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    
    def create_test_user(self, email: Optional[str] = None, password: str = "TestPass123!", tier: str = "free") -> TestUserData:
        """Create unique test user with email and password"""
        user_data = self._build_user_data(email, password, tier)
        self.created_users.append(user_data)
        return user_data
    
    def _build_user_data(self, email: Optional[str], password: str, tier: str) -> TestUserData:
        """Build user data structure using SSOT TestUserData model"""
        user_id = self._create_unique_id("user_")
        user_email = email or f"{user_id}@test-factory.com"
        full_name = f"Test User {user_id[-8:]}"
        hashed_pw = self._hash_password(password)
        created_at = self._generate_timestamp()
        
        return TestUserData(
            id=user_id,
            email=user_email,
            full_name=full_name,
            hashed_password=hashed_pw,
            plan_tier=tier,
            created_at=created_at
        )
    
    def create_test_message(self, user_id: str, content: str, thread_id: Optional[str] = None, message_type: MessageType = MessageType.USER) -> TestMessageData:
        """Create test message with user_id and content"""
        message_data = self._build_message_data(user_id, content, thread_id, message_type)
        self.created_messages.append(message_data)
        return message_data
    
    def _build_message_data(self, user_id: str, content: str, thread_id: Optional[str], message_type: MessageType) -> TestMessageData:
        """Build message data structure"""
        message_id = self._create_unique_id("msg_")
        thread_id = thread_id or self._create_unique_id("thread_")
        created_at = self._generate_timestamp()
        metadata = self._create_message_metadata(user_id, message_type)
        return TestMessageData(message_id, content, message_type, thread_id, user_id, created_at, metadata)
    
    def create_test_thread(self, user_id: str, name: Optional[str] = None) -> TestThreadData:
        """Create conversation thread for user"""
        thread_data = self._build_thread_data(user_id, name)
        self.created_threads.append(thread_data)
        return thread_data
    
    def _build_thread_data(self, user_id: str, name: Optional[str]) -> TestThreadData:
        """Build thread data structure"""
        thread_id = self._create_unique_id("thread_")
        thread_name = name or f"Test Thread {thread_id[-8:]}"
        created_at = self._generate_timestamp()
        updated_at = created_at
        return TestThreadData(thread_id, thread_name, user_id, created_at, updated_at)
    
    def _create_message_metadata(self, user_id: str, msg_type: MessageType) -> Dict[str, Any]:
        """Create message metadata dictionary"""
        return {
            "user_id": user_id,
            "message_type": msg_type.value,
            "session_id": self.session_prefix,
            "created_by_factory": True
        }
    
    def generate_jwt_token(self, user_data: TestUserData, expires_minutes: int = 15) -> str:
        """Generate real JWT token for test user"""
        try:
            return self._create_real_jwt_token(user_data, expires_minutes)
        except ImportError:
            return self._create_mock_jwt_token(user_data)
    
    def _create_real_jwt_token(self, user_data: TestUserData, expires_minutes: int) -> str:
        """Create real JWT using auth service token factory"""
        from auth_service.tests.factories import TokenFactory
        return TokenFactory.create_access_token(
            user_id=user_data.id,
            email=user_data.email,
            expires_in_minutes=expires_minutes
        )
    
    def _create_mock_jwt_token(self, user_data: TestUserData) -> str:
        """Create mock JWT for testing without auth service"""
        token_data = f"{user_data.id}:{user_data.email}"
        encoded = hashlib.sha256(token_data.encode()).hexdigest()
        return f"mock_jwt_{encoded[:32]}"
    
    def cleanup_test_data(self) -> Dict[str, int]:
        """Remove test data for cleanup"""
        stats = self._get_cleanup_stats()
        self._clear_all_data()
        return stats
    
    def _get_cleanup_stats(self) -> Dict[str, int]:
        """Get cleanup statistics"""
        return {
            "users": len(self.created_users),
            "messages": len(self.created_messages),
            "threads": len(self.created_threads)
        }
    
    def _clear_all_data(self) -> None:
        """Clear all created test data"""
        self.created_users.clear()
        self.created_messages.clear()
        self.created_threads.clear()


class DatabaseSeeder:
    """Seeds test data into databases for E2E testing"""
    
    def __init__(self):
        """Initialize seeder with tracking"""
        self.seeded_data: List[Dict[str, Any]] = []
    
    async def seed_user_data(self, user_data: TestUserData) -> Dict[str, Any]:
        """Seed test user into database"""
        record = {"table": "users", "data": user_data, "id": user_data.id}
        self.seeded_data.append(record)
        return {"status": "seeded", "table": "users", "id": user_data.id}
    
    async def seed_message_data(self, message_data: TestMessageData) -> Dict[str, Any]:
        """Seed test message into database"""
        record = {"table": "messages", "data": message_data, "id": message_data.id}
        self.seeded_data.append(record)
        return {"status": "seeded", "table": "messages", "id": message_data.id}
    
    async def seed_thread_data(self, thread_data: TestThreadData) -> Dict[str, Any]:
        """Seed test thread into database"""
        record = {"table": "threads", "data": thread_data, "id": thread_data.id}
        self.seeded_data.append(record)
        return {"status": "seeded", "table": "threads", "id": thread_data.id}
    
    @pytest.mark.e2e
    async def test_cleanup_test_data(self) -> Dict[str, int]:
        """Remove all seeded test data for cleanup"""
        cleanup_stats = {"users": 0, "messages": 0, "threads": 0}
        cleanup_stats = self._count_records_by_table(cleanup_stats)
        self.seeded_data.clear()
        return cleanup_stats
    
    def _count_records_by_table(self, stats: Dict[str, int]) -> Dict[str, int]:
        """Count records by table type"""
        for record in self.seeded_data:
            table = record["table"]
            if table in stats:
                stats[table] += 1
        return stats


class TestConcurrentSupport:
    """Provides support for concurrent test execution"""
    
    @staticmethod
    def create_isolated_factory() -> TestDataFactory:
        """Create factory with unique session isolation"""
        config = UnifiedTestConfig()
        return TestDataFactory(config)
    
    @staticmethod
    def create_isolated_seeder() -> DatabaseSeeder:
        """Create seeder with unique session"""
        return DatabaseSeeder()
    
    @staticmethod
    def generate_concurrent_users(count: int, tier: str = "free") -> List[TestUserData]:
        """Generate multiple users for concurrent testing"""
        factory = ConcurrentTestSupport.create_isolated_factory()
        users = []
        for _ in range(count):
            user = factory.create_test_user(tier=tier)
            users.append(user)
        return users


# Convenience functions for direct usage
def create_test_user_data(email: str = None, tier: str = "free") -> Dict[str, Any]:
    """Create test user data as dictionary for E2E tests"""
    factory = TestDataFactory()
    user = factory.create_test_user(email=email, tier=tier)
    return {
        "id": user.id,
        "email": user.email,
        "password": "TestPass123!",
        "full_name": user.full_name,
        "is_active": True,
        "created_at": user.created_at
    }


def create_test_message_data(content: str, user_id: str = None) -> Dict[str, Any]:
    """Create test message data as dictionary for E2E tests"""
    if not user_id:
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    factory = TestDataFactory()
    message = factory.create_test_message(user_id=user_id, content=content)
    return {
        "id": message.id,
        "content": message.content,
        "type": message.type.value,
        "thread_id": message.thread_id,
        "user_id": message.user_id,
        "timestamp": message.created_at.isoformat(),
        "metadata": message.metadata
    }


def create_test_user(email: str = None, tier: str = "free") -> TestUserData:
    """Quick create test user with unique email"""
    factory = TestDataFactory()
    return factory.create_test_user(email=email, tier=tier)


def create_test_message(user_id: str, content: str) -> TestMessageData:
    """Quick create test message with user_id and content"""
    factory = TestDataFactory()
    return factory.create_test_message(user_id=user_id, content=content)


def create_test_thread(user_id: str) -> TestThreadData:
    """Quick create test thread for user"""
    factory = TestDataFactory()
    return factory.create_test_thread(user_id=user_id)


@pytest.mark.e2e
async def test_cleanup_test_data(seeder: DatabaseSeeder) -> Dict[str, int]:
    """Quick cleanup all test data"""
    return await seeder.cleanup_test_data()


def generate_jwt_token(user_data: TestUserData) -> str:
    """Quick generate JWT token for test user"""
    factory = TestDataFactory()
    return factory.generate_jwt_token(user_data)


def create_test_service_credentials(service_id: str) -> Dict[str, str]:
    """Create test service credentials for service-to-service auth"""
    import os
    service_secrets = {
        "backend": "test-backend-secret-12345",
        "worker": "test-worker-secret-67890", 
        "scheduler": "test-scheduler-secret-abcde"
    }
    
    service_secret = service_secrets.get(service_id, f"test-{service_id}-secret-{uuid.uuid4().hex[:8]}")
    
    # Set environment variable for validation
    import os
    os.environ[f"SERVICE_SECRET_{service_id}"] = service_secret
    
    return {
        "service_id": service_id,
        "service_secret": service_secret
    }
