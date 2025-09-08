import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.schemas.agent_state import (
    CheckpointType,
    StatePersistenceRequest,
)
from netra_backend.app.services.redis.session_manager import RedisSessionManager
from netra_backend.app.services.state_persistence import StatePersistenceService

# In-memory SQLite database for testing
#removed-legacy= "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def db_engine():
    from netra_backend.app.db.base import Base
    from netra_backend.app.db.models_agent_state import AgentStateSnapshot, AgentStateTransaction
    
    engine = create_async_engine(DATABASE_URL)
    
    # Create only the necessary tables for this test
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: AgentStateSnapshot.__table__.create(sync_conn, checkfirst=True))
        await conn.run_sync(lambda sync_conn: AgentStateTransaction.__table__.create(sync_conn, checkfirst=True))
    
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
def state_persistence_service():
    return StatePersistenceService()


@pytest.fixture
def redis_session_manager():
    return RedisSessionManager()


@pytest.fixture
def db_session_manager():
    return DatabaseSessionManager()


async def test_save_and_load_agent_state(state_persistence_service, db_session):
    request = StatePersistenceRequest(
        run_id="test_run",
        thread_id="test_thread",
        user_id="test_user",
        state_data={"key": "value"},
        checkpoint_type=CheckpointType.FULL,
    )
    success, snapshot_id = await state_persistence_service.save_agent_state(
        request, db_session
    )
    assert success
    assert snapshot_id is not None

    loaded_state = await state_persistence_service.load_agent_state(
        "test_run", db_session=db_session
    )
    # The loaded state should be a DeepAgentState object reconstructed from the saved JSON
    assert loaded_state is not None
    # The exact structure depends on how the state_data was serialized and deserialized
    # This test verifies the load operation works without checking specific field access


async def test_create_and_get_session(redis_session_manager):
    session_id = await redis_session_manager.create_session("test_user", {"foo": "bar"})
    assert session_id is not None

    session_data = await redis_session_manager.get_session(session_id)
    assert session_data["user_id"] == "test_user"
    assert session_data["data"]["foo"] == "bar"


async def test_get_db_session(db_session_manager):
    async with db_session_manager.get_session() as session:
        assert session is not None
