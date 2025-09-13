"""

Pytest Fixtures for Resource Isolation Testing



Contains pytest fixtures for the resource isolation test suite.

"""



import logging



import pytest

import pytest_asyncio



from tests.e2e.resource_isolation.suite.test_suite_core import (

    TestResourceIsolationSuite,

)



logger = logging.getLogger(__name__)



@pytest_asyncio.fixture

async def resource_isolation_suite():

    """Fixture providing a configured resource isolation test suite."""

    suite = TestResourceIsolationSuite()

    

    try:

        await suite.initialize_test_environment()

        yield suite

    finally:

        await suite.cleanup_test_environment()



@pytest_asyncio.fixture

async def tenant_agents(resource_isolation_suite):

    """Fixture providing connected tenant agents."""

    suite = resource_isolation_suite

    

    # Create 3 tenant agents for most tests

    agents = await suite.create_tenant_agents(count=3)

    connected_agents = await suite.establish_agent_connections(agents)

    

    if len(connected_agents) < 3:

        pytest.skip(f"Could not establish minimum connections: {len(connected_agents)}/3")

    

    return connected_agents

