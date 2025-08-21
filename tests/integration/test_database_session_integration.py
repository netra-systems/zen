import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from netra_backend.app.services.state_persistence import StatePersistenceService
from netra_backend.app.services.redis.session_manager import RedisSessionManager
from netra_backend.app.db.session import DatabaseSessionManager
from netra_backend.app.schemas.agent_state import (
    StatePersistenceRequest,
    CheckpointType,
)

# In-memory SQLite database for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def db_engine():
    engine = create_async_engine(DATABASE_URL)
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
    assert loaded_state.key == "value"


async def test_create_and_get_session(redis_session_manager):
    session_id = await redis_session_manager.create_session("test_user", {"foo": "bar"})
    assert session_id is not None

    session_data = await redis_session_manager.get_session(session_id)
    assert session_data["user_id"] == "test_user"
    assert session_data["data"]["foo"] == "bar"


async def test_get_db_session(db_session_manager):
    async with db_session_manager.get_session() as session:
        assert session is not None
