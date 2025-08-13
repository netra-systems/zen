"""
Tests for SyntheticDataService initialization and setup
"""

import pytest
from unittest.mock import MagicMock

from app.services.synthetic_data_service import SyntheticDataService


@pytest.fixture
def service():
    """Create fresh SyntheticDataService instance"""
    return SyntheticDataService()


class TestServiceInitialization:
    """Test service initialization and setup"""
    
    def test_initialization(self, service):
        """Test service initializes correctly with default values"""
        assert service.active_jobs == {}
        assert service.corpus_cache == {}
        assert hasattr(service, 'default_tools')
        assert len(service.default_tools) > 0
        
    def test_default_tools_structure(self, service):
        """Test default tools have required structure"""
        for tool in service.default_tools:
            assert "name" in tool
            assert "type" in tool
            assert "latency_ms_range" in tool
            assert "failure_rate" in tool
            assert isinstance(tool["latency_ms_range"], tuple)
            assert len(tool["latency_ms_range"]) == 2
            assert 0 <= tool["failure_rate"] <= 1


class TestWorkloadTypeSelection:
    """Test workload type selection and distribution"""
    
    def test_select_workload_type(self, service):
        """Test workload type selection returns valid types"""
        # Test multiple selections for distribution
        types = set()
        for _ in range(100):
            workload_type = service._select_workload_type()
            types.add(workload_type)
            assert workload_type in [
                "simple_queries", "tool_orchestration", "data_analysis",
                "optimization_workflows", "error_scenarios"
            ]
        
        # Should select multiple different types over 100 iterations
        assert len(types) > 1
    
    def test_select_agent_type(self, service):
        """Test agent type selection for different workload types"""
        test_cases = [
            ("simple_queries", "triage"),
            ("tool_orchestration", "supervisor"),
            ("data_analysis", "data_analysis"),
            ("optimization_workflows", "optimization"),
            ("error_scenarios", "triage"),
            ("unknown_type", "general")
        ]
        
        for workload_type, expected_agent in test_cases:
            agent = service._select_agent_type(workload_type)
            assert agent == expected_agent