"""
Shared Fixtures for Unified System Testing.

Business Value: Consistent test infrastructure across all unified tests.
Provides standardized fixtures for services, users, databases, and WebSocket clients.
"""

import asyncio
import pytest
import websockets
from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.config import settings
from .test_harness import UnifiedTestHarness
from .mock_services import ServiceRegistry, MockOAuthProvider, MockLLMService, MockWebSocketServer


@dataclass
class TestUser:
    """Test user data structure."""
    user_id: str
    email: str
    username: str
    access_token: Optional[str] = None
    is_authenticated: bool = False


@dataclass
class WebSocketClient:
    """WebSocket client for testing."""
    connection: websockets.WebSocketServerProtocol
    url: str
    is_connected: bool = True


@pytest.fixture(scope="function")
async def unified_services() -> AsyncGenerator[Dict[str, Any], None]:
    """Provide unified test environment with all services."""
    harness = UnifiedTestHarness()
    service_registry = ServiceRegistry()
    
    try:
        # Setup mock services
        await _setup_mock_services(service_registry)
        
        # Start real services
        service_ports = await harness.start_all_services()
        
        # Wait for health checks
        await harness.wait_for_health_checks()
        
        # Get service URLs
        service_urls = harness.get_service_urls()
        
        yield {
            "harness": harness,
            "registry": service_registry,
            "ports": service_ports,
            "urls": service_urls
        }
    
    finally:
        await harness.stop_all_services()
        await service_registry.stop_all_services()


@pytest.fixture(scope="function")
def test_user() -> TestUser:
    """Provide test user for authentication flows."""
    return TestUser(
        user_id="test-user-123",
        email="test@example.com",
        username="testuser"
    )


@pytest.fixture(scope="function")
async def test_database() -> AsyncGenerator[AsyncSession, None]:
    """Provide isolated test database session."""
    engine = create_async_engine(settings.database_url, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        yield session
    
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def websocket_client(unified_services) -> AsyncGenerator[WebSocketClient, None]:
    """Provide WebSocket client for testing real-time features."""
    service_urls = unified_services["urls"]
    backend_url = service_urls["backend"]
    websocket_url = backend_url.replace("http://", "ws://") + "/ws"
    
    connection = await websockets.connect(websocket_url)
    client = WebSocketClient(connection=connection, url=websocket_url)
    
    try:
        yield client
    finally:
        if client.is_connected:
            await connection.close()


@pytest.fixture(scope="function")
async def authenticated_user(test_user, unified_services) -> TestUser:
    """Provide authenticated test user with valid token."""
    oauth_provider = unified_services["registry"].get_service("oauth_google")
    
    # Generate auth code and exchange for token
    auth_code = oauth_provider.generate_auth_code(test_user.user_id, test_user.email)
    token_data = oauth_provider.exchange_code_for_token(auth_code)
    
    # Update user with authentication data
    test_user.access_token = token_data["access_token"]
    test_user.is_authenticated = True
    
    return test_user


@pytest.fixture(scope="function")
async def mock_llm_responses() -> Dict[str, Any]:
    """Provide mock LLM responses for consistent testing."""
    return {
        "chat_response": "Hello! I'm here to help with your AI optimization needs.",
        "analysis_response": "Based on the data, I recommend optimizing your model parameters.",
        "error_response": "I encountered an issue processing your request.",
        "streaming_chunks": [
            "Hello! ",
            "I'm here ",
            "to help ",
            "with your ",
            "request."
        ]
    }


@pytest.fixture(scope="function")
async def test_conversation_history() -> List[Dict[str, Any]]:
    """Provide test conversation history for user journey tests."""
    return [
        {
            "role": "user",
            "content": "What is AI optimization?",
            "timestamp": "2025-08-19T10:00:00Z"
        },
        {
            "role": "assistant", 
            "content": "AI optimization involves tuning model parameters and infrastructure to improve performance and reduce costs.",
            "timestamp": "2025-08-19T10:00:02Z"
        },
        {
            "role": "user",
            "content": "How can I reduce my LLM costs?",
            "timestamp": "2025-08-19T10:01:00Z"
        },
        {
            "role": "assistant",
            "content": "You can reduce LLM costs through prompt optimization, model selection, caching, and batching requests.",
            "timestamp": "2025-08-19T10:01:03Z"
        }
    ]


async def _setup_mock_services(registry: ServiceRegistry) -> None:
    """Setup all mock services in the registry."""
    # OAuth providers
    google_oauth = MockOAuthProvider("google")
    registry.register_oauth_provider("google", google_oauth)
    
    github_oauth = MockOAuthProvider("github") 
    registry.register_oauth_provider("github", github_oauth)
    
    # LLM services
    gpt_service = MockLLMService("gpt-4")
    registry.register_llm_service("openai", gpt_service)
    
    gemini_service = MockLLMService("gemini-pro")
    registry.register_llm_service("google", gemini_service)
    
    # WebSocket server
    ws_server = MockWebSocketServer("localhost", 8765)
    registry.register_websocket_server("main", ws_server)
    
    # Start all services
    await registry.start_all_services()


@pytest.fixture(scope="function")
async def real_http_client():
    """Provide HTTP client for making real API requests."""
    import httpx
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture(scope="function")
def service_timeouts() -> Dict[str, int]:
    """Provide timeout configurations for service operations."""
    return {
        "startup_timeout": 60,
        "health_check_timeout": 10,
        "request_timeout": 30,
        "websocket_connect_timeout": 10,
        "test_execution_timeout": 120
    }


@pytest.fixture(scope="function") 
async def clean_database_state(test_database):
    """Ensure clean database state before and after tests."""
    # Clean before test
    await _clean_all_tables(test_database)
    
    yield test_database
    
    # Clean after test
    await _clean_all_tables(test_database)


async def _clean_all_tables(session: AsyncSession) -> None:
    """Clean all tables in the test database."""
    table_names = [
        "users", "threads", "messages", "workload_events",
        "llm_metrics", "corpus_content", "supply_data"
    ]
    
    for table_name in table_names:
        await _truncate_table(session, table_name)


async def _truncate_table(session: AsyncSession, table_name: str) -> None:
    """Truncate a specific table."""
    try:
        await session.execute(f"TRUNCATE TABLE {table_name} CASCADE")
        await session.commit()
    except Exception:
        # Table might not exist, continue
        await session.rollback()


@pytest.fixture(scope="function")
def test_environment_config() -> Dict[str, str]:
    """Provide test environment configuration."""
    return {
        "TESTING": "1",
        "ENVIRONMENT": "testing", 
        "LOG_LEVEL": "ERROR",
        "DATABASE_URL": settings.database_url,
        "ENABLE_REAL_LLM_TESTING": "false",
        "DISABLE_RATE_LIMITING": "true",
        "TEST_MODE_FAST_STARTUP": "true"
    }