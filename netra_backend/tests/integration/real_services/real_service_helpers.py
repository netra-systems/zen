from shared.isolated_environment import get_env
"""
Real Service Test Helpers

Utility functions and classes for real service integration testing.
Provides common patterns for service connection, cleanup, and validation.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Testing infrastructure
- Business Goal: Development Velocity - Reduce test setup time by 60%
- Value Impact: Standardizes real service test patterns across the codebase
- Strategic Impact: Enables consistent integration testing practices
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

import psycopg2
import redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Absolute imports as per CLAUDE.md requirements
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.db.postgres_core import AsyncDatabase
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.utils.exceptions import (
    DatabaseConnectionError,
    RedisConnectionError,
    LLMProviderError
)

logger = logging.getLogger(__name__)


class RealServiceManager:
    """Manager for real service connections and lifecycle."""
    
    def __init__(self):
        self.postgres_db: Optional[AsyncDatabase] = None
        self.redis_client: Optional[redis.Redis] = None
        self.llm_service: Optional[LLMService] = None
        self._cleanup_keys: List[str] = []
        self._cleanup_agents: List[str] = []
        
    async def setup_postgres(self, database_url: str) -> AsyncDatabase:
        """Setup PostgreSQL connection with test schema."""
        if not database_url:
            raise ValueError("DATABASE_URL not provided")
            
        self.postgres_db = AsyncDatabase()
        await self.postgres_db.connect()
        
        # Create test tables
        async with self.postgres_db.get_session() as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS test_agent_states (
                    id SERIAL PRIMARY KEY,
                    agent_id VARCHAR(255) UNIQUE NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    data JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS test_messages (
                    id SERIAL PRIMARY KEY,
                    message_id VARCHAR(255) UNIQUE NOT NULL,
                    agent_id VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    message_type VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS test_coordination (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    coordinator_id VARCHAR(255) NOT NULL,
                    participant_id VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    data JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            await session.commit()
            
        logger.info("PostgreSQL test schema created successfully")
        return self.postgres_db
    
    def setup_redis(self, redis_url: str) -> redis.Redis:
        """Setup Redis connection with test namespace."""
        if not redis_url:
            raise ValueError("REDIS_URL not provided")
            
        self.redis_client = redis.from_url(redis_url)
        
        # Test connection
        try:
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
        except redis.ConnectionError as e:
            raise RedisConnectionError(f"Failed to connect to Redis: {str(e)}")
            
        return self.redis_client
    
    def setup_llm_service(self, openai_key: str = None, anthropic_key: str = None) -> LLMManager:
        """Setup LLM service with real API keys."""
        if not openai_key and not anthropic_key:
            raise ValueError("At least one LLM provider API key required")
            
        config = get_unified_config()
        
        if openai_key:
            config.openai_api_key = openai_key
        if anthropic_key:
            config.anthropic_api_key = anthropic_key
            
        self.llm_service = LLMManager(config)
        logger.info("LLM service configured successfully")
        return self.llm_service
    
    async def cleanup(self):
        """Clean up all test resources."""
        # Clean up Redis keys
        if self.redis_client:
            for key in self._cleanup_keys:
                try:
                    self.redis_client.delete(key)
                except Exception as e:
                    logger.warning(f"Failed to delete Redis key {key}: {str(e)}")
                    
            # Clean up test namespace
            for key in self.redis_client.scan_iter(match="test:*"):
                try:
                    self.redis_client.delete(key)
                except Exception as e:
                    logger.warning(f"Failed to delete Redis key {key}: {str(e)}")
        
        # Clean up PostgreSQL test data
        if self.postgres_db:
            try:
                async with self.postgres_db.get_session() as session:
                    for agent_id in self._cleanup_agents:
                        await session.execute(
                            text("DELETE FROM test_agent_states WHERE agent_id LIKE :pattern"),
                            {"pattern": f"{agent_id}%"}
                        )
                    
                    # Clean up all test data
                    await session.execute(text("DELETE FROM test_agent_states WHERE agent_id LIKE 'test_%'"))
                    await session.execute(text("DELETE FROM test_messages WHERE agent_id LIKE 'test_%'"))
                    await session.execute(text("DELETE FROM test_coordination WHERE session_id LIKE 'test_%'"))
                    await session.commit()
                    
                await self.postgres_db.disconnect()
            except Exception as e:
                logger.warning(f"Failed to cleanup PostgreSQL: {str(e)}")
        
        logger.info("Real service cleanup completed")
    
    def register_cleanup_key(self, key: str):
        """Register a Redis key for cleanup."""
        self._cleanup_keys.append(key)
    
    def register_cleanup_agent(self, agent_id: str):
        """Register an agent ID for cleanup."""
        self._cleanup_agents.append(agent_id)


class TestDataGenerator:
    """Generator for test data patterns."""
    
    @staticmethod
    def create_test_agent_state(
        agent_id: str = None,
        status: str = "active",
        custom_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create test agent state data."""
        if not agent_id:
            agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
            
        base_data = {
            "task_type": "optimization",
            "priority": "normal",
            "created_at": time.time(),
            "metadata": {
                "test_run": True,
                "generator": "TestDataGenerator"
            }
        }
        
        if custom_data:
            base_data.update(custom_data)
            
        return {
            "agent_id": agent_id,
            "status": status,
            "data": base_data
        }
    
    @staticmethod
    def create_test_message(
        agent_id: str = None,
        content: str = None,
        message_type: str = "user_request"
    ) -> Dict[str, Any]:
        """Create test message data."""
        if not agent_id:
            agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
            
        if not content:
            content = "Test optimization request for GPU workload analysis"
            
        return {
            "message_id": f"msg_{uuid.uuid4().hex[:8]}",
            "agent_id": agent_id,
            "content": content,
            "message_type": message_type,
            "timestamp": time.time()
        }
    
    @staticmethod
    def create_coordination_scenario(
        num_agents: int = 3,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Create multi-agent coordination scenario."""
        if not session_id:
            session_id = f"test_session_{uuid.uuid4().hex[:8]}"
            
        coordinator_id = f"supervisor_{session_id}"
        participants = [f"agent_{session_id}_{i}" for i in range(num_agents)]
        
        return {
            "session_id": session_id,
            "coordinator_id": coordinator_id,
            "participants": participants,
            "scenario_type": "optimization_workflow",
            "expected_duration": 30,  # seconds
            "tasks": [
                {"agent": participants[0], "task": "workload_analysis"},
                {"agent": participants[1], "task": "optimization_recommendations"},
                {"agent": participants[2], "task": "validation_and_reporting"}
            ]
        }


class RealServiceValidator:
    """Validator for real service integration scenarios."""
    
    @staticmethod
    async def validate_database_consistency(
        db: AsyncDatabase,
        expected_records: List[Dict[str, Any]]
    ) -> bool:
        """Validate database state matches expected records."""
        async with db.get_session() as session:
            for record in expected_records:
                result = await session.execute(
                    text("SELECT data FROM test_agent_states WHERE agent_id = :agent_id"),
                    {"agent_id": record["agent_id"]}
                )
                
                row = result.fetchone()
                if not row:
                    logger.error(f"Missing database record for agent {record['agent_id']}")
                    return False
                    
                stored_data = json.loads(row[0]) if row[0] else {}
                expected_data = record.get("data", {})
                
                # Check key fields match
                for key, expected_value in expected_data.items():
                    if key not in stored_data:
                        logger.error(f"Missing key {key} in stored data for agent {record['agent_id']}")
                        return False
                    if stored_data[key] != expected_value:
                        logger.error(f"Data mismatch for {key}: expected {expected_value}, got {stored_data[key]}")
                        return False
        
        return True
    
    @staticmethod
    def validate_redis_consistency(
        redis_client: redis.Redis,
        expected_keys: Dict[str, Any]
    ) -> bool:
        """Validate Redis state matches expected keys and values."""
        for key, expected_value in expected_keys.items():
            try:
                stored_value = redis_client.get(key)
                if not stored_value:
                    logger.error(f"Missing Redis key: {key}")
                    return False
                    
                if isinstance(expected_value, dict):
                    stored_data = json.loads(stored_value.decode())
                    for field, field_value in expected_value.items():
                        if field not in stored_data:
                            logger.error(f"Missing field {field} in Redis key {key}")
                            return False
                        if stored_data[field] != field_value:
                            logger.error(f"Redis data mismatch for {key}.{field}: expected {field_value}, got {stored_data[field]}")
                            return False
                else:
                    if stored_value.decode() != str(expected_value):
                        logger.error(f"Redis value mismatch for {key}: expected {expected_value}, got {stored_value.decode()}")
                        return False
                        
            except Exception as e:
                logger.error(f"Error validating Redis key {key}: {str(e)}")
                return False
        
        return True
    
    @staticmethod
    async def validate_llm_response_quality(
        llm_service: LLMManager,
        test_cases: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Validate LLM response quality across test cases."""
        results = []
        
        for test_case in test_cases:
            prompt = test_case["prompt"]
            expected_keywords = test_case.get("expected_keywords", [])
            max_response_time = test_case.get("max_response_time", 30)
            
            start_time = time.time()
            
            try:
                response = await llm_service.ask_llm_full(
                    prompt=prompt,
                    llm_config_name=test_case.get("llm_config_name", "default")
                )
                
                response_time = time.time() - start_time
                content = getattr(response, 'content', "").lower()
                
                # Validate response quality
                quality_score = 0
                issues = []
                
                # Check response time
                if response_time <= max_response_time:
                    quality_score += 25
                else:
                    issues.append(f"Response time {response_time:.2f}s exceeds limit {max_response_time}s")
                
                # Check content exists
                if len(content) > 0:
                    quality_score += 25
                else:
                    issues.append("Empty response content")
                
                # Check expected keywords
                if expected_keywords:
                    keyword_matches = sum(1 for keyword in expected_keywords if keyword.lower() in content)
                    keyword_score = (keyword_matches / len(expected_keywords)) * 25
                    quality_score += keyword_score
                    
                    if keyword_matches < len(expected_keywords):
                        missing_keywords = [kw for kw in expected_keywords if kw.lower() not in content]
                        issues.append(f"Missing keywords: {missing_keywords}")
                else:
                    quality_score += 25
                
                # Check token usage
                token_usage = getattr(response, 'usage', {}).get('total_tokens', 0) if hasattr(response, 'usage') else 0
                if token_usage > 0:
                    quality_score += 25
                else:
                    # Token usage might not be available in all configurations
                    quality_score += 20
                
                results.append({
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    "response_time": response_time,
                    "quality_score": quality_score,
                    "issues": issues,
                    "token_usage": token_usage,
                    "success": len(issues) == 0
                })
                
            except Exception as e:
                results.append({
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    "response_time": time.time() - start_time,
                    "quality_score": 0,
                    "issues": [f"LLM call failed: {str(e)}"],
                    "token_usage": 0,
                    "success": False
                })
        
        return results


@asynccontextmanager
async def real_service_test_context(
    postgres_url: str = None,
    redis_url: str = None,
    openai_key: str = None,
    anthropic_key: str = None
):
    """Context manager for real service testing."""
    manager = RealServiceManager()
    
    try:
        # Setup services
        services = {}
        
        if postgres_url:
            services["postgres"] = await manager.setup_postgres(postgres_url)
        
        if redis_url:
            services["redis"] = manager.setup_redis(redis_url)
        
        if openai_key or anthropic_key:
            services["llm"] = manager.setup_llm_service(openai_key, anthropic_key)
        
        services["manager"] = manager
        
        yield services
        
    finally:
        await manager.cleanup()


def get_service_config() -> Dict[str, Optional[str]]:
    """Get service configuration from environment variables."""
    return {
        "postgres_url": get_env().get("DATABASE_URL"),
        "redis_url": get_env().get("REDIS_URL", "redis://localhost:6379"),
        "openai_key": get_env().get("OPENAI_API_KEY"),
        "anthropic_key": get_env().get("ANTHROPIC_API_KEY"),
        "auth_service_url": get_env().get("AUTH_SERVICE_URL", "http://localhost:8001")
    }


def check_service_availability() -> Dict[str, bool]:
    """Check which real services are available for testing."""
    config = get_service_config()
    
    availability = {
        "postgres": bool(config["postgres_url"]),
        "redis": bool(config["redis_url"]),
        "openai": bool(config["openai_key"]),
        "anthropic": bool(config["anthropic_key"]),
        "auth_service": bool(config["auth_service_url"])
    }
    
    logger.info(f"Service availability: {availability}")
    return availability


# Export main classes and functions
__all__ = [
    "RealServiceManager",
    "TestDataGenerator", 
    "RealServiceValidator",
    "real_service_test_context",
    "get_service_config",
    "check_service_availability"
]
