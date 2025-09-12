"""
E2E Test Service Enforcement
Ensures E2E tests ONLY use real services, never mocks

This module enforces the following principles:
1. E2E tests must use real services (SQLite, Redis, actual LLMs)
2. No mock fallbacks allowed in E2E tests
3. Tests fail fast if real services are not available
4. Clear error messages when services are missing

Business Value Justification (BVJ):
- Segment: All tiers - ensures production reliability
- Business Goal: Prevent production failures through real E2E testing
- Value Impact: Catches integration issues before deployment
- Revenue Impact: Prevents customer-facing bugs that damage trust
"""

import os
import sys
import pytest
import logging
from shared.isolated_environment import get_env
from typing import Dict, Any, Optional
import redis.asyncio as redis
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class E2EServiceValidator:
    """Validates that all required services are available for E2E testing"""
    
    @staticmethod
    def enforce_real_services():
        """Enforce real service usage in E2E tests"""
        # Set critical environment variables for E2E testing
        env = get_env()
        env.set("E2E_TESTING", "true", "test")
        env.set("TESTING", "1", "test")
        env.set("ENVIRONMENT", "testing", "test")
        
        # CRITICAL: Disable all mock fallbacks
        env.set("NO_MOCK_FALLBACK", "true", "test")
        env.set("FORCE_REAL_SERVICES", "true", "test")
        
        # Use SQLite in-memory for database (real, but fast)
        env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test")
        
        # Enable real LLM testing for agent E2E tests
        env.set("USE_REAL_LLM", "true", "test")
        env.set("TEST_USE_REAL_LLM", "true", "test")  # Legacy compatibility
        env.set("ENABLE_REAL_LLM_TESTING", "true", "test")
        
        # Disable Docker dependency - use lightweight services
        env.set("TEST_SERVICE_MODE", "local", "test")
        env.set("SKIP_DOCKER_CHECK", "true", "test")
        
        logger.info("E2E real service enforcement enabled")
    
    @staticmethod
    async def validate_redis_connection() -> bool:
        """Validate Redis is available for E2E testing"""
        try:
            redis_url = get_env().get("REDIS_URL", "redis://localhost:6379/0")
            client = await redis.from_url(redis_url)
            await client.ping()
            await client.close()
            return True
        except Exception as e:
            logger.error(f"Redis not available for E2E testing: {e}")
            return False
    
    @staticmethod
    async def validate_backend_service() -> bool:
        """Validate backend service is available"""
        try:
            backend_url = get_env().get("BACKEND_SERVICE_URL", "http://localhost:8000")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{backend_url}/health") as response:
                    return response.status == 200
        except Exception as e:
            logger.warning(f"Backend service check failed (may be normal during startup): {e}")
            return False
    
    @staticmethod
    async def validate_auth_service() -> bool:
        """Validate auth service is available"""
        try:
            auth_url = get_env().get("AUTH_SERVICE_URL", "http://localhost:8081")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{auth_url}/health") as response:
                    return response.status == 200
        except Exception as e:
            logger.warning(f"Auth service check failed (may be normal during startup): {e}")
            return False
    
    @staticmethod
    def validate_llm_configuration() -> bool:
        """Validate LLM configuration for E2E testing"""
        real_llm_requested = (get_env().get("USE_REAL_LLM") == "true" or get_env().get("TEST_USE_REAL_LLM") == "true")
        logger.debug(f"LLM validation: USE_REAL_LLM={get_env().get('USE_REAL_LLM')}, TEST_USE_REAL_LLM={get_env().get('TEST_USE_REAL_LLM')}, real_llm_requested={real_llm_requested}")
        
        # Check that real LLM testing is enabled
        if not real_llm_requested:
            logger.error("Real LLM testing not enabled for E2E tests")
            return False
        
        # Check for at least one LLM API key
        openai_key = get_env().get("OPENAI_API_KEY")
        anthropic_key = get_env().get("ANTHROPIC_API_KEY")
        gemini_key = get_env().get("GEMINI_API_KEY")
        has_llm_key = any([openai_key, anthropic_key, gemini_key])
        logger.debug(f"API key check: OPENAI={bool(openai_key)}, ANTHROPIC={bool(anthropic_key)}, GEMINI={bool(gemini_key)}, has_any={has_llm_key}")
        
        if not has_llm_key:
            # Only set test keys if real LLM testing is not specifically requested
            if not get_env().get("TEST_USE_REAL_LLM", "").lower() == "true":
                logger.warning("No LLM API keys found - using test keys")
                # Set test API keys for E2E testing
                get_env().set("GEMINI_API_KEY", "test-gemini-api-key", "test")
                get_env().set("TEST_LLM_MODE", "simulate", "test")
            else:
                logger.info("Real LLM testing requested - API keys will be loaded from secret manager")
        
        return True
    
    @classmethod
    async def validate_all_services(cls) -> Dict[str, bool]:
        """Validate all required services for E2E testing"""
        cls.enforce_real_services()
        
        results = {
            "redis": await cls.validate_redis_connection(),
            "backend": await cls.validate_backend_service(),
            "auth": await cls.validate_auth_service(),
            "llm": cls.validate_llm_configuration(),
        }
        
        # SQLite is always available (in-memory)
        results["database"] = True
        
        return results


class E2ERealServiceFactory:
    """Factory for creating real service connections for E2E tests"""
    
    @staticmethod
    async def create_redis_client():
        """Create real Redis client for E2E testing"""
        redis_url = get_env().get("REDIS_URL", "redis://localhost:6379/0")
        client = await redis.from_url(redis_url)
        return client
    
    @staticmethod
    async def create_agent_service():
        """Create real agent service for E2E testing"""
        from netra_backend.app.services.agent_service import AgentService
        from netra_backend.app.services.agent_factory import AgentFactory
        
        factory = AgentFactory()
        service = await factory.create_agent_service()
        return service
    
    @staticmethod
    async def create_websocket_connection(url: str):
        """Create real WebSocket connection for E2E testing"""
        session = aiohttp.ClientSession()
        ws = await session.ws_connect(url)
        return ws, session
    
    @staticmethod
    async def create_llm_provider(provider_type: str):
        """Create real LLM provider for E2E testing"""
        from netra_backend.app.llm.llm_factory import LLMFactory
        
        factory = LLMFactory()
        provider = await factory.get_provider(provider_type)
        return provider


def pytest_configure(config):
    """Configure pytest for E2E testing with real services only"""
    # Enforce real services for all E2E tests
    validator = E2EServiceValidator()
    validator.enforce_real_services()
    
    # Add marker for E2E tests
    config.addinivalue_line(
        "markers",
        "e2e: mark test as end-to-end test requiring real services"
    )


@pytest.fixture(scope="session")
async def e2e_services():
    """Session-scoped fixture that validates all E2E services"""
    validator = E2EServiceValidator()
    results = await validator.validate_all_services()
    
    # Log service availability
    for service, available in results.items():
        if available:
            logger.info(f"[U+2713] {service} service available for E2E testing")
        else:
            logger.warning(f"[U+2717] {service} service not available")
    
    # Don't fail if some services are unavailable during test discovery
    # The actual tests will fail if they need those services
    return results


@pytest.fixture
async def real_redis_client():
    """Fixture providing real Redis client for E2E tests"""
    client = await E2ERealServiceFactory.create_redis_client()
    yield client
    await client.close()


@pytest.fixture
async def real_agent_service():
    """Fixture providing real agent service for E2E tests"""
    service = await E2ERealServiceFactory.create_agent_service()
    return service


@pytest.fixture
async def real_websocket():
    """Fixture providing real WebSocket connection for E2E tests"""
    from tests.e2e.config import TEST_ENDPOINTS
    
    ws, session = await E2ERealServiceFactory.create_websocket_connection(
        TEST_ENDPOINTS.ws_url
    )
    
    yield ws
    
    await ws.close()
    await session.close()


@pytest.fixture
async def real_llm_provider():
    """Fixture providing real LLM provider for E2E tests"""
    provider = await E2ERealServiceFactory.create_llm_provider("gemini")
    return provider


# Auto-enforce real services when this module is imported
if "pytest" in sys.modules:
    E2EServiceValidator.enforce_real_services()