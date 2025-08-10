import pytest
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator, Generator
import asyncio

os.environ["TESTING"] = "1"
os.environ["REDIS_HOST"] = "localhost"
os.environ["CLICKHOUSE_HOST"] = "localhost"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models_postgres import Base
from app.schemas import User
from app.config import settings

pytest_plugins = ['pytest_asyncio']

@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture
async def async_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()

@pytest.fixture
async def async_session_factory(async_engine):
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

@pytest.fixture
async def async_session(async_session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

@pytest.fixture
def mock_redis_manager():
    mock = MagicMock()
    mock.connect = AsyncMock(return_value=None)
    mock.disconnect = AsyncMock(return_value=None)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=None)
    mock.delete = AsyncMock(return_value=None)
    mock.exists = AsyncMock(return_value=False)
    return mock

@pytest.fixture
def mock_clickhouse_client():
    mock = MagicMock()
    mock.ping = MagicMock(return_value=True)
    mock.execute = AsyncMock(return_value=None)
    mock.close = AsyncMock(return_value=None)
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_llm_manager():
    mock = MagicMock()
    mock.get_llm = MagicMock(return_value=MagicMock())
    return mock

@pytest.fixture
def mock_websocket_manager():
    mock = MagicMock()
    mock.active_connections = {}
    mock.connect = AsyncMock(return_value=None)
    mock.disconnect = AsyncMock(return_value=None)
    mock.send_message = AsyncMock(return_value=None)
    mock.broadcast = AsyncMock(return_value=None)
    mock.shutdown = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_background_task_manager():
    mock = MagicMock()
    mock.shutdown = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_key_manager():
    mock = MagicMock()
    mock.load_from_settings = MagicMock(return_value=mock)
    return mock

@pytest.fixture
def mock_security_service():
    return MagicMock()

@pytest.fixture
def mock_tool_dispatcher():
    return MagicMock()

@pytest.fixture
def mock_agent_supervisor():
    mock = MagicMock()
    mock.shutdown = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_agent_service():
    return MagicMock()

@pytest.fixture
def app(
    async_session_factory,
    mock_redis_manager,
    mock_clickhouse_client,
    mock_llm_manager,
    mock_websocket_manager,
    mock_background_task_manager,
    mock_key_manager,
    mock_security_service,
    mock_tool_dispatcher,
    mock_agent_supervisor,
    mock_agent_service,
):
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db_session_factory = async_session_factory
        app.state.redis_manager = mock_redis_manager
        app.state.clickhouse_client = mock_clickhouse_client
        app.state.llm_manager = mock_llm_manager
        app.state.background_task_manager = mock_background_task_manager
        app.state.key_manager = mock_key_manager
        app.state.security_service = mock_security_service
        app.state.tool_dispatcher = mock_tool_dispatcher
        app.state.agent_supervisor = mock_agent_supervisor
        app.state.agent_service = mock_agent_service
        yield
    
    app = FastAPI(lifespan=lifespan)
    
    from fastapi.middleware.cors import CORSMiddleware
    from starlette.middleware.sessions import SessionMiddleware
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(
        SessionMiddleware,
        secret_key="test-secret-key",
        same_site="lax",
    )
    
    from app.routes.websockets import router as websockets_router
    from app.routes.auth import router as auth_router
    from app.routes.generation import router as generation_router
    from app.routes.agent import router as agent_router
    
    app.include_router(websockets_router)
    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(generation_router, prefix="/api")
    app.include_router(agent_router, prefix="/api")
    
    return app

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.fixture
def test_user():
    return User(
        id="test-user-id",
        email="test@example.com",
        is_active=True,
        is_superuser=False
    )

@pytest.fixture
def auth_headers(test_user):
    from app.auth.auth import create_access_token
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(autouse=True)
def mock_startup_checks():
    with patch("app.startup_checks.run_startup_checks", new_callable=AsyncMock) as mock:
        mock.return_value = None
        yield mock

@pytest.fixture(autouse=True)
def mock_database_validation():
    with patch("app.services.database_env_service.validate_database_environment") as mock:
        mock.return_value = None
        yield mock

@pytest.fixture(autouse=True)
def mock_schema_validation():
    with patch("app.services.schema_validation_service.run_comprehensive_validation", new_callable=AsyncMock) as mock:
        mock.return_value = True
        yield mock

@pytest.fixture(autouse=True)
def mock_migrations():
    with patch("app.main.run_migrations") as mock:
        mock.return_value = None
        yield mock

@pytest.fixture(autouse=True)
def mock_central_logger():
    with patch("app.logging_config.central_logger") as mock:
        logger = MagicMock()
        logger.get_logger = MagicMock(return_value=MagicMock())
        logger.shutdown = AsyncMock(return_value=None)
        logger.clickhouse_db = MagicMock()
        mock.return_value = logger
        yield mock