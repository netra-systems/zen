"""
Comprehensive real service tests for Netra AI Platform.
All functions ≤8 lines per requirements.
"""

import os
import sys
import asyncio
import pytest
import time
from typing import Dict, Any, Callable, TypeVar
from pathlib import Path
import functools
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

T = TypeVar('T')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.agent_service import AgentService
from app.services.synthetic_data_service import SyntheticDataService
from app.services.quality_gate_service import QualityGateService
from app.services.corpus_service import CorpusService
from app.services.database.message_repository import MessageRepository
from app.services.database.thread_repository import ThreadRepository
from app.services.cache.llm_cache import LLMCacheManager
from app.services.quality_monitoring_service import QualityMonitoringService
from app.services.supply_research_service import SupplyResearchService
from app.services.supply_catalog_service import SupplyCatalogService
from app.llm.llm_manager import LLMManager
from app.db.base import Base
from app.db.postgres import async_engine, async_session_factory
from app.redis_manager import RedisManager
from app.db.clickhouse import get_clickhouse_client
from app.db.models_postgres import User, Thread, Message
from .real_services_test_fixtures import (
    ThreadCreate, MessageCreate, skip_if_no_real_services,
    get_test_user_id, get_test_thread_data, get_test_message_data
)


class TestRealServicesComprehensive:
    """Comprehensive test suite for real service integration"""
    
    # Timeout configurations for different service types
    LLM_TIMEOUT = 60  # seconds
    DATABASE_TIMEOUT = 30  # seconds 
    REDIS_TIMEOUT = 10  # seconds
    CLICKHOUSE_TIMEOUT = 30  # seconds
    AGENT_TIMEOUT = 120  # seconds for full agent processing
    
    @staticmethod
    def with_retry_and_timeout(timeout: int = 30, max_attempts: int = 3):
        """Decorator to add retry logic and timeout to service calls"""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            retry_decorator = _create_retry_decorator(max_attempts)
            
            @retry_decorator
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            return wrapper
        return decorator
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment with real services"""
        # Run async setup in sync context
        asyncio.run(self._async_setup())
        
        yield
        
        # Cleanup
        asyncio.run(self._cleanup())
    
    async def _async_setup(self):
        """Async setup method"""
        await self._init_database()
        await self._init_services()
        await self._init_repositories()
        await self._init_business_services()
        self.test_user = await self._create_test_user()
        self.metrics = _init_metrics()
    
    async def _init_database(self):
        """Initialize database"""
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def _init_services(self):
        """Initialize core services"""
        self.db = async_session_factory()
        self.redis = RedisManager()
        self.clickhouse_context = get_clickhouse_client()
        self.clickhouse = await self.clickhouse_context.__aenter__()
        self.llm_manager = LLMManager()
    
    async def _init_repositories(self):
        """Initialize repositories"""
        self.thread_repo = ThreadRepository()
        self.message_repo = MessageRepository()
    
    async def _init_business_services(self):
        """Initialize business services"""
        self.agent_service = AgentService()
        self.synthetic_data_service = SyntheticDataService()
        self.quality_gate_service = QualityGateService()
        self.corpus_service = CorpusService()
        self._init_additional_services()
    
    def _init_additional_services(self):
        """Initialize additional services"""
        self.cache_manager = LLMCacheManager(self.redis)
        self.quality_monitoring = QualityMonitoringService()
        self.supply_research = SupplyResearchService()
        self.supply_catalog = SupplyCatalogService()
    
    async def _create_test_user(self) -> User:
        """Create a test user for the session"""
        user = User(
            username=f"test_user_{int(time.time())}",
            email=f"test_{int(time.time())}@example.com",
            full_name="Test User",
            role="admin"
        )
        return await self._save_user(user)
    
    async def _save_user(self, user: User) -> User:
        """Save user to database"""
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def _cleanup(self):
        """Clean up test data"""
        await self._cleanup_threads()
        await self._cleanup_database()
        await self._cleanup_services()
    
    async def _cleanup_threads(self):
        """Clean up test threads and messages"""
        threads = await self.thread_repo.find_by_user(self.db, self.test_user.id)
        for thread in threads:
            await self._delete_thread_messages(thread)
            await self.thread_repo.delete(self.db, thread.id)
    
    async def _delete_thread_messages(self, thread: Thread):
        """Delete messages for a thread"""
        messages = await self.message_repo.find_by_thread(self.db, thread.id)
        for message in messages:
            await self.message_repo.delete(self.db, message.id)
    
    async def _cleanup_database(self):
        """Clean up database connections"""
        await self.db.close()
    
    async def _cleanup_services(self):
        """Clean up external services"""
        await self.clickhouse_context.__aexit__(None, None, None)
        await self.redis.close()
    
    @skip_if_no_real_services
    async def test_full_agent_orchestration_e2e(self):
        """Test complete agent orchestration end-to-end"""
        thread_data = get_test_thread_data()
        thread = await self._create_test_thread(thread_data)
        
        message_data = get_test_message_data(thread.id)
        result = await self._process_agent_message(message_data)
        
        await self._verify_agent_orchestration(result, thread.id)
    
    async def _create_test_thread(self, thread_data: dict) -> Thread:
        """Create test thread"""
        thread_create = ThreadCreate(**thread_data)
        return await self.thread_repo.create(
            self.db, 
            title=thread_create.title,
            user_id=thread_create.user_id
        )
    
    async def _process_agent_message(self, message_data: dict) -> dict:
        """Process message through agent service"""
        message_create = MessageCreate(**message_data)
        return await self.agent_service.process_message(
            thread_id=message_create.thread_id,
            user_id=message_create.user_id,
            content=message_create.content
        )
    
    async def _verify_agent_orchestration(self, result: dict, thread_id: str):
        """Verify agent orchestration results"""
        assert result is not None
        assert "response" in result
        
        # Verify message was stored
        messages = await self.message_repo.find_by_thread(self.db, thread_id)
        assert len(messages) >= 1


def _create_retry_decorator(max_attempts: int):
    """Create retry decorator with specified attempts"""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError))
    )


def _init_metrics() -> Dict[str, Any]:
    """Initialize metrics tracking dictionary"""
    return {
        "llm_calls": 0,
        "db_queries": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "total_latency": 0,
        "quality_scores": []
    }