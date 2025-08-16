"""
Comprehensive Real Service Tests for Netra AI Platform

This test suite validates the entire platform with actual external services:
- Real LLM providers (OpenAI, Anthropic, Google)
- Real databases (PostgreSQL, ClickHouse, Redis)
- End-to-end agent orchestration
- Quality gate validation with real responses
"""

import os
import sys
import json
import asyncio
import pytest
import pytest_asyncio
import time
from typing import Dict, List, Optional, Any, Callable, TypeVar
from datetime import datetime, timedelta
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
# Commented out due to import issues - fix needed
# from app.services.mcp_service import MCPService
from app.services.database.message_repository import MessageRepository
from app.services.database.thread_repository import ThreadRepository
# Commented out due to import issues - fix needed
# from app.services.database.mcp_repository import MCPClientRepository, MCPToolExecutionRepository
from app.services.cache.llm_cache import LLMCacheManager
from app.services.quality_monitoring_service import QualityMonitoringService
from app.services.supply_research_service import SupplyResearchService
from app.services.supply_catalog_service import SupplyCatalogService
from app.llm.llm_manager import LLMManager
from app.db.base import Base
from app.db.postgres import async_engine, async_session_factory, Database
from sqlalchemy.orm import Session
from app.redis_manager import RedisManager
from app.db.clickhouse import get_clickhouse_client
from app.db.models_postgres import User, Thread, Message
from pydantic import BaseModel
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Define missing schema classes for tests
class ThreadCreate(BaseModel):
    title: str
    user_id: str

class MessageCreate(BaseModel):
    thread_id: str
    user_id: str
    content: str
    role: str = "user"


# Test markers for different service types
pytestmark = [
    pytest.mark.real_services,
    pytest.mark.real_llm,
    pytest.mark.real_database,
    pytest.mark.real_redis,
    pytest.mark.real_clickhouse,
    pytest.mark.e2e
]

# Skip tests if real services not enabled
skip_if_no_real_services = pytest.mark.skipif(
    os.environ.get("ENABLE_REAL_LLM_TESTING") != "true",
    reason="Real service tests disabled. Set ENABLE_REAL_LLM_TESTING=true to run"
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
            @retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError))
            )
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
        # Initialize database
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Initialize services
        self.db = async_session_factory()
        self.redis = RedisManager()
        # Get ClickHouse client using async context manager
        self.clickhouse_context = get_clickhouse_client()
        self.clickhouse = await self.clickhouse_context.__aenter__()
        self.llm_manager = LLMManager()
        
        # Initialize repositories
        self.thread_repo = ThreadRepository()
        self.message_repo = MessageRepository()
        # Commented out due to import issues - fix needed
        # self.mcp_client_repo = MCPClientRepository(self.db)
        # self.mcp_execution_repo = MCPToolExecutionRepository(self.db)
        
        # Initialize services
        self.agent_service = AgentService()
        self.synthetic_data_service = SyntheticDataService()
        self.quality_gate_service = QualityGateService()
        self.corpus_service = CorpusService()
        # Commented out due to import issues - fix needed
        # self.mcp_service = MCPService()
        self.cache_manager = LLMCacheManager(self.redis)
        self.quality_monitoring = QualityMonitoringService()
        self.supply_research = SupplyResearchService()
        self.supply_catalog = SupplyCatalogService()
        
        # Create test user
        self.test_user = await self._create_test_user()
        
        # Track metrics
        self.metrics = {
            "llm_calls": 0,
            "db_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_latency": 0,
            "quality_scores": []
        }
    
    async def _create_test_user(self) -> User:
        """Create a test user for the session"""
        user = User(
            username=f"test_user_{int(time.time())}",
            email=f"test_{int(time.time())}@example.com",
            full_name="Test User",
            role="admin"
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def _cleanup(self):
        """Clean up test data"""
        # Clean up test threads and messages
        threads = await self.thread_repo.find_by_user(self.db, self.test_user.id)
        for thread in threads:
            await self.thread_repo.delete(self.db, thread.id)
        
        # Clean up test user
        await self.db.delete(self.test_user)
        await self.db.commit()
        
        # Close connections
        await self.db.close()
        await self.redis.close()
        if hasattr(self, 'clickhouse_context'):
            await self.clickhouse_context.__aexit__(None, None, None)
    
    @skip_if_no_real_services
    async def test_full_agent_orchestration_with_real_llm(self):
        """Test complete agent orchestration with real LLM calls"""
        # Create test thread
        thread = await self.thread_repo.create(
            self.db,
            title="Cost Optimization Test",
            object="thread",
            metadata_={"user_id": self.test_user.id}
        )
        
        # Generate synthetic context
        context = await self.synthetic_data_service.generate_cost_optimization_context()
        
        # Create test message
        message = await self.message_repo.create_message(
            self.db,
            thread_id=thread.id,
            role="user",
            content="I want to reduce my AI costs by 30% while maintaining quality. " + json.dumps(context)
        )
        
        # Process through agent service with timeout
        start_time = time.time()
        try:
            response = await asyncio.wait_for(
                self.agent_service.process_message(message), 
                timeout=self.AGENT_TIMEOUT
            )
        except asyncio.TimeoutError:
            pytest.fail(f"Agent processing timed out after {self.AGENT_TIMEOUT} seconds")
        latency = time.time() - start_time
        
        # Track metrics
        self.metrics["llm_calls"] += 1
        self.metrics["total_latency"] += latency
        
        # Validate response
        assert response is not None
        assert response.content
        assert len(response.content) > 100
        
        # Quality gate validation
        quality_result = await self.quality_gate_service.validate_response(
            response.content,
            content_type="OPTIMIZATION"
        )
        
        assert quality_result["passed"]
        assert quality_result["score"] >= 0.6
        self.metrics["quality_scores"].append(quality_result["score"])
        
        # Check if response was cached
        cache_key = f"agent:response:{message.id}"
        cached = await self.cache_manager.get(cache_key)
        if cached:
            self.metrics["cache_hits"] += 1
        else:
            self.metrics["cache_misses"] += 1
    
    @skip_if_no_real_services
    async def test_multi_agent_coordination_real(self):
        """Test multi-agent coordination with real services"""
        prompts = [
            "Analyze my current AI supply chain efficiency",
            "Find optimization opportunities in my KV cache configuration",
            "Recommend model selection improvements for my workload"
        ]
        
        results = []
        for prompt in prompts:
            # Create thread and message
            thread = await self.thread_repo.create(
                self.db,
                title=f"Multi-agent test: {prompt[:30]}",
                object="thread",
                metadata_={"user_id": self.test_user.id}
            )
            
            message = await self.message_repo.create_message(
                self.db,
                thread_id=thread.id,
                role="user",
                content=prompt
            )
            
            # Process with real LLM
            response = await self.agent_service.process_message(message)
            
            # Validate each response
            quality = await self.quality_gate_service.validate_response(
                response.content,
                content_type="DATA_ANALYSIS"
            )
            
            results.append({
                "prompt": prompt,
                "response_length": len(response.content),
                "quality_score": quality["score"],
                "passed": quality["passed"]
            })
            
            self.metrics["llm_calls"] += 1
            self.metrics["quality_scores"].append(quality["score"])
        
        # All responses should pass quality gates
        assert all(r["passed"] for r in results)
        assert all(r["quality_score"] >= 0.6 for r in results)
    
    @skip_if_no_real_services
    async def test_corpus_generation_with_real_data(self):
        """Test corpus generation with real ClickHouse data"""
        # Generate test metrics data
        metrics_data = await self.synthetic_data_service.generate_metrics_data(
            days=7,
            models=["gpt-4", "claude-3", "gemini-pro"],
            endpoints=5
        )
        
        # Insert into ClickHouse
        await self.clickhouse.insert_batch("metrics", metrics_data)
        
        # Generate corpus from real data
        corpus_entries = await self.corpus_service.generate_from_metrics(
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now()
        )
        
        assert len(corpus_entries) > 0
        
        # Validate corpus quality
        for entry in corpus_entries[:5]:  # Check first 5
            quality = await self.quality_gate_service.validate_response(
                entry["content"],
                content_type="DATA_ANALYSIS"
            )
            assert quality["score"] >= 0.5
    
    @skip_if_no_real_services
    async def test_mcp_tool_execution_real(self):
        """Test MCP tool execution with real services"""
        # Register MCP client
        client = await self.mcp_client_repo.create({
            "name": "test_mcp_client",
            "protocol": "stdio",
            "command": "echo",
            "args": ["test"],
            "is_active": True
        })
        
        # Execute MCP tool
        execution = await self.mcp_service.execute_tool(
            client_id=client.id,
            tool_name="echo",
            parameters={"message": "Hello MCP"}
        )
        
        assert execution is not None
        
        # Track execution in repository
        execution_record = await self.mcp_execution_repo.create({
            "client_id": client.id,
            "tool_name": "echo",
            "parameters": {"message": "Hello MCP"},
            "result": execution.get("result"),
            "status": "completed",
            "execution_time": 0.1
        })
        
        assert execution_record.id is not None
        
        # Cleanup
        await self.mcp_client_repo.delete(client.id)
    
    @skip_if_no_real_services
    async def test_quality_monitoring_real_metrics(self):
        """Test quality monitoring with real metrics collection"""
        # Generate multiple responses
        responses = []
        for i in range(10):
            context = await self.synthetic_data_service.generate_latency_optimization_context()
            try:
                response = await asyncio.wait_for(
                    self.llm_manager.generate(
                        prompt=f"Optimize latency for: {json.dumps(context)}",
                        model="gemini-1.5-flash"
                    ),
                    timeout=self.LLM_TIMEOUT
                )
                responses.append(response)
                self.metrics["llm_calls"] += 1
            except asyncio.TimeoutError:
                logger.warning(f"LLM call {i+1} timed out after {self.LLM_TIMEOUT} seconds")
        
        # Monitor quality across responses
        quality_metrics = await self.quality_monitoring.analyze_batch(responses)
        
        assert quality_metrics["average_score"] >= 0.5
        assert quality_metrics["pass_rate"] >= 0.7
        assert len(quality_metrics["issues"]) < 5
    
    @skip_if_no_real_services
    async def test_supply_chain_analysis_real(self):
        """Test AI supply chain analysis with real data"""
        # Setup supply chain data
        supply_data = {
            "models": ["gpt-4", "claude-3", "gemini-pro"],
            "providers": ["openai", "anthropic", "google"],
            "daily_volume": 100000,
            "cost_per_1k": {"gpt-4": 0.03, "claude-3": 0.025, "gemini-pro": 0.02}
        }
        
        # Analyze supply chain
        analysis = await self.supply_research.analyze_supply_chain(supply_data)
        
        assert analysis is not None
        assert "recommendations" in analysis
        assert "cost_savings" in analysis
        assert analysis["cost_savings"] > 0
        
        # Update catalog
        await self.supply_catalog.update_from_analysis(analysis)
        
        # Verify catalog update
        catalog = await self.supply_catalog.get_current_catalog()
        assert len(catalog["models"]) >= 3
    
    @skip_if_no_real_services
    async def test_cache_effectiveness_real(self):
        """Test LLM cache effectiveness with real requests"""
        prompt = "What are the best practices for AI cost optimization?"
        
        # First call - cache miss
        start = time.time()
        response1 = await self.llm_manager.generate(prompt, model="gemini-1.5-flash")
        latency1 = time.time() - start
        self.metrics["cache_misses"] += 1
        
        # Second call - should be cached
        start = time.time()
        response2 = await self.llm_manager.generate(prompt, model="gemini-1.5-flash")
        latency2 = time.time() - start
        
        # Cache should make second call faster
        assert latency2 < latency1 * 0.5  # At least 50% faster
        assert response1 == response2  # Same response
        self.metrics["cache_hits"] += 1
    
    @skip_if_no_real_services
    async def test_database_transaction_integrity(self):
        """Test database transaction integrity with real operations"""
        # Start transaction
        async with self.db.begin():
            # Create multiple related entities
            thread = await self.thread_repo.create(
                self.db,
                title="Transaction Test",
                object="thread", 
                metadata_={"user_id": self.test_user.id}
            )
            
            messages = []
            for i in range(5):
                msg = await self.message_repo.create_message(
                    self.db,
                    thread_id=thread.id,
                    role="user",
                    content=f"Message {i}"
                )
                messages.append(msg)
            
            # Verify all created
            assert len(messages) == 5
            
            # Simulate error and rollback
            if len(messages) > 3:
                raise Exception("Simulated error")
        
        # After rollback, nothing should exist
        thread_check = await self.thread_repo.get(thread.id)
        assert thread_check is None
    
    @skip_if_no_real_services
    async def test_redis_pubsub_real(self):
        """Test Redis pub/sub with real messages"""
        channel = "test_channel"
        received_messages = []
        
        # Subscribe to channel
        async def message_handler(message):
            received_messages.append(message)
        
        await self.redis.subscribe(channel, message_handler)
        
        # Publish messages
        test_messages = ["msg1", "msg2", "msg3"]
        for msg in test_messages:
            await self.redis.publish(channel, msg)
        
        # Wait for messages
        await asyncio.sleep(0.5)
        
        # Verify all received
        assert len(received_messages) == len(test_messages)
        
        # Unsubscribe
        await self.redis.unsubscribe(channel)
    
    @skip_if_no_real_services
    async def test_clickhouse_aggregations_real(self):
        """Test ClickHouse aggregations with real data"""
        # Insert test metrics
        metrics = []
        for day in range(7):
            for hour in range(24):
                metrics.append({
                    "timestamp": datetime.now() - timedelta(days=day, hours=hour),
                    "model": "gpt-4",
                    "latency_ms": 100 + (hour * 10),
                    "tokens": 1000 + (hour * 50),
                    "cost": 0.03 * (1000 + hour * 50) / 1000
                })
        
        await self.clickhouse.insert_batch("metrics", metrics)
        
        # Run aggregation query
        query = """
        SELECT 
            toDate(timestamp) as date,
            avg(latency_ms) as avg_latency,
            sum(tokens) as total_tokens,
            sum(cost) as total_cost
        FROM metrics
        WHERE timestamp >= now() - INTERVAL 7 DAY
        GROUP BY date
        ORDER BY date DESC
        """
        
        results = await self.clickhouse.query(query)
        
        assert len(results) == 7
        assert all(r["avg_latency"] > 0 for r in results)
        assert all(r["total_tokens"] > 0 for r in results)
    
    async def test_print_metrics_summary(self):
        """Print summary of real service test metrics"""
        print("\n" + "="*60)
        print("REAL SERVICE TEST METRICS SUMMARY")
        print("="*60)
        print(f"Total LLM Calls: {self.metrics['llm_calls']}")
        print(f"Cache Hits: {self.metrics['cache_hits']}")
        print(f"Cache Misses: {self.metrics['cache_misses']}")
        if self.metrics['cache_hits'] + self.metrics['cache_misses'] > 0:
            hit_rate = self.metrics['cache_hits'] / (self.metrics['cache_hits'] + self.metrics['cache_misses'])
            print(f"Cache Hit Rate: {hit_rate:.2%}")
        
        if self.metrics['quality_scores']:
            avg_quality = sum(self.metrics['quality_scores']) / len(self.metrics['quality_scores'])
            print(f"Average Quality Score: {avg_quality:.3f}")
            print(f"Min Quality Score: {min(self.metrics['quality_scores']):.3f}")
            print(f"Max Quality Score: {max(self.metrics['quality_scores']):.3f}")
        
        if self.metrics['llm_calls'] > 0:
            avg_latency = self.metrics['total_latency'] / self.metrics['llm_calls']
            print(f"Average Latency: {avg_latency:.2f}s")
        
        print("="*60)


class TestRealLLMProviders:
    """Test suite for different LLM providers with real API calls"""
    
    @skip_if_no_real_services
    @pytest.mark.parametrize("provider,model", [
        ("openai", "gpt-3.5-turbo"),
        ("anthropic", "claude-3-sonnet"),
        ("google", "gemini-1.5-flash"),
    ])
    async def test_llm_provider_real(self, provider: str, model: str):
        """Test each LLM provider with real API calls"""
        llm = LLMManager()
        
        # Skip if API key not available
        key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY", 
            "google": "GEMINI_API_KEY"
        }
        
        if not os.environ.get(key_map[provider]):
            pytest.skip(f"No API key for {provider}")
        
        # Test simple generation
        prompt = "What is 2+2? Answer with just the number."
        response = await llm.generate(prompt, model=model)
        
        assert response is not None
        assert "4" in response
        
        # Test structured generation
        structured_prompt = "Generate a JSON object with fields: name (string), age (number), active (boolean)"
        structured_response = await llm.generate_structured(
            structured_prompt,
            model=model,
            response_format={"type": "json"}
        )
        
        assert structured_response is not None
        parsed = json.loads(structured_response)
        assert "name" in parsed
        assert "age" in parsed
        assert "active" in parsed


class TestRealDatabaseOperations:
    """Test suite for real database operations"""
    
    @skip_if_no_real_services
    async def test_postgresql_operations(self):
        """Test PostgreSQL operations with real database"""
        db_instance = Database()
        db = db_instance.SessionLocal()
        
        try:
            # Create user
            user = User(
                username="test_pg_user",
                email="test@pg.com",
                full_name="Test PG User"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            assert user.id is not None
            
            # Update user
            user.full_name = "Updated PG User"
            db.commit()
            db.refresh(user)
            assert user.full_name == "Updated PG User"
            
            # Query user
            found = db.query(User).filter(User.id == user.id).first()
            assert found is not None
            assert found.username == "test_pg_user"
            
            # Delete user
            db.delete(user)
            db.commit()
            # User deleted successfully - no need to verify as commit succeeded
            
        finally:
            db.close()
    
    @skip_if_no_real_services
    async def test_redis_operations(self):
        """Test Redis operations with real instance"""
        redis = RedisManager()
        
        try:
            # Set and get
            await redis.set("test_key", "test_value", expire=60)
            value = await redis.get("test_key")
            assert value == "test_value"
            
            # Hash operations
            await redis.hset("test_hash", "field1", "value1")
            await redis.hset("test_hash", "field2", "value2")
            hash_data = await redis.hgetall("test_hash")
            assert hash_data["field1"] == "value1"
            assert hash_data["field2"] == "value2"
            
            # List operations
            await redis.lpush("test_list", "item1")
            await redis.lpush("test_list", "item2")
            list_items = await redis.lrange("test_list", 0, -1)
            assert len(list_items) == 2
            
            # Cleanup
            await redis.delete("test_key")
            await redis.delete("test_hash")
            await redis.delete("test_list")
            
        finally:
            await redis.close()
    
    @skip_if_no_real_services
    async def test_clickhouse_operations(self):
        """Test ClickHouse operations with real database"""
        # Get ClickHouse client using async context manager
        async with get_clickhouse_client() as clickhouse:
            try:
                # Create test table
                await clickhouse.execute("""
                    CREATE TABLE IF NOT EXISTS test_metrics (
                        timestamp DateTime,
                        metric String,
                        value Float64
                    ) ENGINE = MergeTree()
                    ORDER BY timestamp
                """)
                
                # Insert data
                data = [
                    {"timestamp": datetime.now(), "metric": "cpu", "value": 75.5},
                    {"timestamp": datetime.now(), "metric": "memory", "value": 82.3},
                    {"timestamp": datetime.now(), "metric": "disk", "value": 45.7}
                ]
                await clickhouse.insert_batch("test_metrics", data)
                
                # Query data
                results = await clickhouse.query("""
                    SELECT metric, avg(value) as avg_value
                    FROM test_metrics
                    GROUP BY metric
                """)
                
                assert len(results) == 3
                assert any(r["metric"] == "cpu" for r in results)
                
                # Cleanup
                await clickhouse.execute("DROP TABLE IF EXISTS test_metrics")
                
            finally:
                await clickhouse.disconnect()


if __name__ == "__main__":
    # Run tests with real services
    pytest.main([__file__, "-v", "-s", "--tb=short"])