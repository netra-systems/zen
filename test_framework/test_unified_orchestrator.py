#!/usr/bin/env python
"""
Test Unified Orchestrator Components

Simple validation tests for the unified orchestrator functionality.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from .unified_orchestrator import (
    ServiceManager, 
    TestExecutor,
    ResultAggregator,
    UnifiedOrchestrator
)

class TestServiceManager:
    """Test ServiceManager functionality"""
    
    def test_initialization(self):
        """Test ServiceManager initializes correctly"""
        project_root = Path.cwd()
        service_manager = ServiceManager(project_root)
        
        assert service_manager.project_root == project_root
        assert service_manager.services == {}
        assert service_manager.startup_order == ["auth", "backend", "frontend"]
        assert "auth" in service_manager.service_configs
        assert "backend" in service_manager.service_configs
        assert "frontend" in service_manager.service_configs
    
    def test_service_config_structure(self):
        """Test service configurations have required fields"""
        service_manager = ServiceManager(Path.cwd())
        
        for service_name, config in service_manager.service_configs.items():
            assert "port" in config
            assert "path" in config
            assert "cmd" in config
            assert isinstance(config["cmd"], list)

class TestTestExecutor:
    """Test TestExecutor functionality"""
    
    def test_initialization(self):
        """Test TestExecutor initializes correctly"""
        project_root = Path.cwd()
        test_executor = TestExecutor(project_root)
        
        assert test_executor.project_root == project_root
        assert test_executor.results == {}
    
    @patch('subprocess.run')
    def test_run_python_tests_success(self, mock_subprocess):
        """Test successful Python test execution"""
        mock_subprocess.return_value = Mock(returncode=0, stdout="All tests passed", stderr="")
        
        test_executor = TestExecutor(Path.cwd())
        result = test_executor.run_python_tests()
        
        assert result["language"] == "python"
        assert result["success"] is True
        assert result["exit_code"] == 0
        assert "duration" in result
    
    @patch('subprocess.run')
    def test_run_python_tests_failure(self, mock_subprocess):
        """Test failed Python test execution"""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="Tests failed")
        
        test_executor = TestExecutor(Path.cwd())
        result = test_executor.run_python_tests()
        
        assert result["language"] == "python"
        assert result["success"] is False
        assert result["exit_code"] == 1

class TestResultAggregator:
    """Test ResultAggregator functionality"""
    
    def test_initialization(self):
        """Test ResultAggregator initializes correctly"""
        project_root = Path.cwd()
        result_aggregator = ResultAggregator(project_root)
        
        assert result_aggregator.project_root == project_root
        assert result_aggregator.reports_dir == project_root / "test_reports"
    
    def test_calculate_summary(self):
        """Test summary calculation"""
        result_aggregator = ResultAggregator(Path.cwd())
        
        test_results = {
            "python": {"success": True, "duration": 10.5},
            "javascript": {"success": False, "duration": 5.2},
            "integration": {"success": True, "duration": 15.3}
        }
        
        summary = result_aggregator._calculate_summary(test_results)
        
        assert summary["total_tests"] == 3
        assert summary["passed_tests"] == 2
        assert summary["failed_tests"] == 1
        assert summary["total_duration"] == 31.0
        assert summary["success_rate"] == 66.67
    
    def test_determine_overall_success(self):
        """Test overall success determination"""
        result_aggregator = ResultAggregator(Path.cwd())
        
        # All successful
        test_results = {"python": {"success": True}, "js": {"success": True}}
        service_results = {"auth": True, "backend": True}
        assert result_aggregator._determine_overall_success(test_results, service_results) is True
        
        # Test failure
        test_results = {"python": {"success": False}, "js": {"success": True}}
        service_results = {"auth": True, "backend": True}
        assert result_aggregator._determine_overall_success(test_results, service_results) is False
        
        # Service failure
        test_results = {"python": {"success": True}, "js": {"success": True}}
        service_results = {"auth": False, "backend": True}
        assert result_aggregator._determine_overall_success(test_results, service_results) is False

class TestUnifiedOrchestrator:
    """Test UnifiedOrchestrator integration"""
    
    def test_initialization(self):
        """Test UnifiedOrchestrator initializes correctly"""
        orchestrator = UnifiedOrchestrator()
        
        assert orchestrator.project_root == Path.cwd()
        assert hasattr(orchestrator, 'service_manager')
        assert hasattr(orchestrator, 'test_executor')
        assert hasattr(orchestrator, 'result_aggregator')
    
    def test_create_failure_result(self):
        """Test failure result creation"""
        orchestrator = UnifiedOrchestrator()
        
        result = orchestrator._create_failure_result("Test error", {"auth": False})
        
        assert result["error"] == "Test error"
        assert result["service_startup"] == {"auth": False}
        assert result["overall_success"] is False
        assert "timestamp" in result
        assert result["orchestration_duration"] == 0
    
    def test_run_tests_sequential(self):
        """Test sequential test execution"""
        orchestrator = UnifiedOrchestrator()
        
        # Mock the test executor methods
        orchestrator.test_executor.run_python_tests = Mock(return_value={"success": True})
        orchestrator.test_executor.run_javascript_tests = Mock(return_value={"success": True})
        orchestrator.test_executor.run_integration_tests = Mock(return_value={"success": True})
        
        results = orchestrator._run_tests_sequential()
        
        assert "python" in results
        assert "javascript" in results
        assert "integration" in results
        assert all(result["success"] for result in results.values())

@pytest.mark.asyncio
async def test_run_tests_parallel():
    """Test parallel test execution"""
    orchestrator = UnifiedOrchestrator()
    
    # Mock the test executor methods
    orchestrator.test_executor.run_python_tests = Mock(return_value={"success": True})
    orchestrator.test_executor.run_javascript_tests = Mock(return_value={"success": True})  
    orchestrator.test_executor.run_integration_tests = Mock(return_value={"success": True})
    
    results = await orchestrator._run_tests_parallel()
    
    assert "python" in results
    assert "javascript" in results
    assert "integration" in results
    assert all(result["success"] for result in results.values())

def test_orchestrator_cleanup():
    """Test orchestrator cleanup functionality"""
    orchestrator = UnifiedOrchestrator()
    
    # Mock service manager stop method
    orchestrator.service_manager.stop_all_services = Mock()
    
    # Should not raise exception
    orchestrator.cleanup()
    
    # Verify service manager cleanup was called
    orchestrator.service_manager.stop_all_services.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])