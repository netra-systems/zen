

import pytest

from sqlalchemy import Column, Integer, String, text

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from sqlalchemy.orm import declarative_base, sessionmaker

from shared.isolated_environment import IsolatedEnvironment



from netra_backend.app.agents.supervisor_ssot import SupervisorAgent

from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler

from netra_backend.app.db.database_manager import DatabaseManager

from netra_backend.app.clients.auth_client_core import AuthServiceClient

from shared.isolated_environment import get_env



# Define a simple model for the test

Base = declarative_base()





class AgentData(Base):

    __tablename__ = "agent_data"

    id = Column(Integer, primary_key=True)

    data = Column(String)





# NOTE: Assuming the agent implementation lives in a path like this.

# This will likely need to be adjusted.





@pytest.mark.asyncio

async def test_database_transaction_rollback_on_agent_failure():

    """

    Tests that database transactions are rolled back if an agent fails mid-workflow.

    """

    # 1. Set up an in-memory SQLite database

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)



    # 2. Create the table for the test model

    async with engine.begin() as conn:

        await conn.run_sync(Base.metadata.create_all)



    # 3. Patch the agent to fail after a database write

    # NOTE: This assumes the agent has a method that takes a session and

    # performs writes.

    original_method = SupervisorAgent.perform_database_write



    def failing_db_write(self, session, data_to_write):

        # First, perform the original write

        original_method(self, session, data_to_write)

        # Then, raise an exception to simulate a failure

        raise ValueError("Simulating agent failure after DB write")



    with patch.object(SupervisorAgent, "perform_database_write", new=failing_db_write):

        agent = SupervisorAgent()



        # 4. Run the agent and assert that it fails

        with pytest.raises(ValueError, match="Simulating agent failure after DB write"):

            async with async_session() as session:

                async with session.begin():

                    # NOTE: This assumes the agent has a method like

                    # `run_workflow` that takes a session.

                    await agent.run_workflow(session=session, data_to_write="some data")



    # 5. Verify that the data was rolled back

    async with async_session() as session:

        result = await session.execute(text("SELECT * FROM agent_data"))

        assert result.first() is None

