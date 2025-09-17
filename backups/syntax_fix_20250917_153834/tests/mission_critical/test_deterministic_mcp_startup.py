'''
Test Deterministic MCP Startup

Verifies MCP service initialization during startup is deterministic.
'''

import sys
import os
import json
import asyncio
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.corpus_service import CorpusService
from netra_backend.app.services.security_service import SecurityService
from netra_backend.app.services.supply_catalog_service import SupplyCatalogService
from netra_backend.app.services.synthetic_data_service import SyntheticDataService
from netra_backend.app.services.mcp_service import MCPService


def test_mcp_service_deterministic_creation():
"""Test that MCP service can be created deterministically with all required services."""

    Create mock services (in real app these come from app.state)
class MockAgentService:
    def __init__(self):
        self.name = "MockAgent"

class MockService:
    def __init__(self, name):
        self.name = name

    # Create all required services
        agent_service = MockAgentService()
        thread_service = MockService("thread")
        corpus_service = MockService("corpus")
        synthetic_data_service = MockService("synthetic")
        security_service = MockService("security")
        supply_catalog_service = MockService("supply")

    # Create MCP service with all dependencies
        mcp_service = MCPService( )
        agent_service=agent_service,
        thread_service=thread_service,
        corpus_service=corpus_service,
        synthetic_data_service=synthetic_data_service,
        security_service=security_service,
        supply_catalog_service=supply_catalog_service,
        llm_manager=None
    

    # Verify all services are properly assigned
        assert mcp_service.agent_service == agent_service
        assert mcp_service.thread_service == thread_service
        assert mcp_service.corpus_service == corpus_service
        assert mcp_service.synthetic_data_service == synthetic_data_service
        assert mcp_service.security_service == security_service
        assert mcp_service.supply_catalog_service == supply_catalog_service

    # Verify MCP server is created
        assert hasattr(mcp_service, 'mcp_server')
        assert mcp_service.mcp_server is not None

    # Verify repositories are initialized
        assert hasattr(mcp_service, 'client_repository')
        assert hasattr(mcp_service, 'execution_repository')

        print("[PASS] MCP service created successfully with all dependencies")
        print("[PASS] All services properly assigned")
        print("[PASS] MCP server initialized")
        print("[PASS] Repositories initialized")

        return True


    def test_mcp_service_factory_validation():
        """Test that MCP service factory properly validates agent_service requirement."""

        from netra_backend.app.services.service_factory import _create_mcp_service

    # Test that creation without agent_service raises error
        try:
        _create_mcp_service(agent_service=None)
        print("[FAIL] Factory should have raised error for missing agent_service")
        return False
        except ValueError as e:
        if "agent_service is required" in str(e):
        print("[PASS] Factory correctly validates agent_service requirement")
        else:
        print("formatted_string")
        return False

                    # Test that creation with mock agent_service works
class MockAgentService:
        pass

        mock_agent = MockAgentService()

        try:
        mcp_service = _create_mcp_service(agent_service=mock_agent)
        print("[PASS] Factory creates MCP service with provided agent_service")
        assert isinstance(mcp_service, MCPService)
        print("[PASS] Created service is proper MCPService instance")
        return True
        except Exception as e:
        print("formatted_string")
        return False


    def main():
        """Run all tests."""
        print("=" * 60)
        print("Testing Deterministic MCP Service Initialization")
        print("=" * 60)

        results = []

    # Test 1: Direct MCP service creation
        print("")
        Test 1: Direct MCP Service Creation")
        print("-" * 40)
        results.append(test_mcp_service_deterministic_creation())

    # Test 2: Service factory validation
        print("")
        Test 2: Service Factory Validation")
        print("-" * 40)
        results.append(test_mcp_service_factory_validation())

    # Summary
        print("")
        " + "=" * 60)
        print("Test Summary")
        print("=" * 60)

        passed = sum(results)
        total = len(results)

        if passed == total:
        print("formatted_string")
        print("[SUCCESS] MCP service initialization is deterministic and stable")
        return 0
        else:
        print("formatted_string")
        return 1


        if __name__ == "__main__":
        exit(main())
        pass
