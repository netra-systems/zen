import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.postgres import get_async_db as get_db
from app.db.base import Base
from app.config import settings
from app.services.key_manager import KeyManager
from app.services.security_service import SecurityService

DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

@pytest.fixture(scope="function")
async def db_engine():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def db_session(db_engine):
    connection = await db_engine.connect()
    trans = await connection.begin()
    Session = sessionmaker(bind=connection, class_=AsyncSession)
    session = Session()
    yield session
    await session.close()
    await trans.rollback()
    await connection.close()

@pytest.fixture(scope="function")
async def client(db_session: AsyncSession):
    def override_get_db():
        yield db_session

    key_manager = KeyManager.load_from_settings(settings)
    app.state.key_manager = key_manager
    app.state.security_service = SecurityService(key_manager)

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)