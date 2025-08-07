import pytest
from app.services.deepagents.overall_supervisor import OverallSupervisor
from app.config import get_settings

@pytest.mark.asyncio
async def test_overall_supervisor():
    # This is a placeholder test. A more comprehensive test would mock the LLM and tools.
    # For now, we just test that the graph is created without errors.
    from app.llm.llm_manager import LLMManager
    from app.connection_manager import manager
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    settings = get_settings()
    llm_manager = LLMManager(settings)
    websocket_manager = manager

    async with async_session() as session:
        supervisor = OverallSupervisor(session, llm_manager, websocket_manager)
        assert supervisor.graph is not None
