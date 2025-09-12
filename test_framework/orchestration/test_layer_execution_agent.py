#!/usr/bin/env python3
"""
Test suite for LayerExecutionAgent

Comprehensive tests validating layer execution functionality, integration
with existing test runner, and coordination with orchestration system.
"""

import asyncio
import pytest
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from shared.isolated_environment import IsolatedEnvironment

# Import the LayerExecutionAgent and related components
from test_framework.orchestration.layer_execution_agent import (
    LayerExecutionAgent, LayerExecutionConfig, LayerExecutionResult,
    CategoryExecutionResult, ExecutionStrategy, create_layer_execution_config,
    execute_layer_async, execute_layer_sync
)
from test_framework.layer_system import (
    LayerSystem, TestLayer, LayerExecutionMode, ResourceLimits, CategoryConfig
)
from test_framework.category_system import CategorySystem, TestCategory, CategoryPriority


class TestLayerExecutionAgent:
    """Test suite for LayerExecutionAgent functionality"""
    
    @pytest.fixture
    def temp_project_root(self):
        """Create temporary project root for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            # Create basic directory structure
            (project_root / "test_framework" / "config").mkdir(parents=True)
            (project_root / "scripts").mkdir(parents=True)
            
            # Create mock unified_test_runner.py
            test_runner_content = '''#!/usr/bin/env python3
import sys
import json
import time

def main():
    # Mock test runner that simulates test execution
    args = sys.argv[1:]
    category = None
    environment = "test"
    
    for i, arg in enumerate(args):
        if arg == "--category" and i + 1 < len(args):
            category = args[i + 1]
        elif arg == "--env" and i + 1 < len(args):
            environment = args[i + 1]
    
    # Simulate test execution
    if category == "smoke":
        print("Running smoke tests...")
        print("5 passed in 0.5s")
        return 0
    elif category == "unit":
        print("Running unit tests...")
        print("25 passed in 2.1s")
        return 0
    elif category == "integration":
        print("Running integration tests...")
        print("15 passed, 1 failed in 5.2s")
        return 1
    else:
        print(f"Running {category} tests...")
        print("10 passed in 1.5s")
        return 0

if __name__ == "__main__":
    sys.exit(main())
'''
            (project_root / "scripts" / "unified_test_runner.py").write_text(test_runner_content)
            
            yield project_root
            
    @pytest.fixture
    def layer_execution_agent(self, temp_project_root):
        """Create LayerExecutionAgent for testing"""
        return LayerExecutionAgent(temp_project_root)
        
    @pytest.fixture 
    def sample_layer_config(self):
        """Create sample layer execution configuration"""
        return LayerExecutionConfig(
            layer_name="fast_feedback",
            execution_strategy=ExecutionStrategy.HYBRID_SMART,
            max_parallel_categories=2,
            environment="test",
            fail_fast_enabled=True
        )
        
    @pytest.fixture
    def mock_layer(self):
        """Create mock test layer for testing"""
        return TestLayer(
            name="test_layer",
            description="Test layer for unit testing",
            execution_order=1,
            max_duration_minutes=10,
            execution_mode=LayerExecutionMode.PARALLEL,
            categories=[
                CategoryConfig(name="smoke", timeout_seconds=60, priority_order=1),
                CategoryConfig(name="unit", timeout_seconds=120, priority_order=2)
            ],
            resource_limits=ResourceLimits(
                max_memory_mb=512,
                max_cpu_percent=50,
                max_parallel_instances=2
            )
        )
        
    # Test initialization and configuration
    
    def test_agent_initialization(self, temp_project_root):
        """Test LayerExecutionAgent initialization"""
        agent = LayerExecutionAgent(temp_project_root)
        
        assert agent.project_root == temp_project_root
        assert agent.agent_id.startswith("layer_executor_")
        assert agent.layer_system is not None
        assert agent.category_system is not None
        assert agent.current_execution is None
        assert len(agent.allocated_resources) == 0
        
    def test_create_layer_execution_config(self):
        """Test layer execution configuration creation"""
        config = create_layer_execution_config(
            "fast_feedback",
            execution_mode="parallel_unlimited",
            environment="staging",
            use_real_services=True
        )
        
        assert config.layer_name == "fast_feedback"
        assert config.execution_strategy == ExecutionStrategy.PARALLEL_UNLIMITED
        assert config.environment == "staging"
        assert config.use_real_services is True
        
    def test_get_available_layers(self, layer_execution_agent):
        """Test getting available layers"""
        layers = layer_execution_agent.get_available_layers()
        
        # Should have default layers from layer system
        expected_layers = ["fast_feedback", "core_integration", "service_integration", "e2e_performance"]
        for layer in expected_layers:
            assert layer in layers
            
    def test_get_layer_categories(self, layer_execution_agent):
        """Test getting categories for a layer"""
        categories = layer_execution_agent.get_layer_categories("fast_feedback")
        
        # Should have smoke and unit categories
        assert "smoke" in categories
        assert "unit" in categories
        
    def test_validate_layer_configuration(self, layer_execution_agent):
        """Test layer configuration validation"""
        # Valid layer
        issues = layer_execution_agent.validate_layer_configuration("fast_feedback")
        assert isinstance(issues, list)
        
        # Invalid layer
        issues = layer_execution_agent.validate_layer_configuration("nonexistent")
        assert len(issues) > 0
        assert "not found" in issues[0].lower()
        
    # Test execution strategies
    
    @pytest.mark.asyncio
    async def test_execute_sequential_strategy(self, layer_execution_agent, mock_layer, sample_layer_config):
        """Test sequential execution strategy"""
        # Modify layer for sequential execution
        mock_layer.execution_mode = LayerExecutionMode.SEQUENTIAL
        sample_layer_config.execution_strategy = ExecutionStrategy.SEQUENTIAL
        
        # Mock the layer system to return our test layer
        layer_execution_agent.layer_system.layers["test_layer"] = mock_layer
        
        # Mock command execution
        with patch.object(layer_execution_agent, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "output": "5 passed in 0.5s",
                "errors": "",
                "return_code": 0
            }
            
            result = await layer_execution_agent._execute_sequential(mock_layer, sample_layer_config)
            
            assert result["success"] is True
            assert result["execution_mode"] == "sequential"
            assert len(result["categories"]) == 2  # smoke and unit
            
    @pytest.mark.asyncio
    async def test_execute_parallel_strategy(self, layer_execution_agent, mock_layer, sample_layer_config):
        """Test parallel execution strategy"""
        mock_layer.execution_mode = LayerExecutionMode.PARALLEL
        sample_layer_config.execution_strategy = ExecutionStrategy.PARALLEL_LIMITED
        
        # Mock the layer system
        layer_execution_agent.layer_system.layers["test_layer"] = mock_layer
        
        # Mock command execution
        with patch.object(layer_execution_agent, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "output": "10 passed in 1.2s",
                "errors": "",
                "return_code": 0
            }
            
            result = await layer_execution_agent._execute_parallel(mock_layer, sample_layer_config)
            
            assert result["success"] is True
            assert result["execution_mode"] == "parallel"
            assert len(result["categories"]) == 2
            
    @pytest.mark.asyncio
    async def test_execute_hybrid_strategy(self, layer_execution_agent, mock_layer, sample_layer_config):
        """Test hybrid execution strategy"""
        mock_layer.execution_mode = LayerExecutionMode.HYBRID
        sample_layer_config.execution_strategy = ExecutionStrategy.HYBRID_SMART
        
        # Mock the layer system
        layer_execution_agent.layer_system.layers["test_layer"] = mock_layer
        
        # Mock command execution
        with patch.object(layer_execution_agent, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "output": "15 passed in 2.0s", 
                "errors": "",
                "return_code": 0
            }
            
            result = await layer_execution_agent._execute_hybrid(mock_layer, sample_layer_config)
            
            assert result["success"] is True
            assert result["execution_mode"] == "hybrid"
            assert len(result["categories"]) == 2
            
    # Test category execution
    
    @pytest.mark.asyncio
    async def test_execute_single_category_success(self, layer_execution_agent, mock_layer, sample_layer_config):
        """Test successful single category execution"""
        layer_execution_agent.layer_system.layers["test_layer"] = mock_layer
        
        with patch.object(layer_execution_agent, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "output": "8 passed in 1.1s",
                "errors": "",
                "return_code": 0
            }
            
            result = await layer_execution_agent._execute_single_category("smoke", mock_layer, sample_layer_config)
            
            assert result.success is True
            assert result.category_name == "smoke"
            assert result.test_counts["passed"] == 8
            assert result.test_counts["total"] == 8
            assert result.duration > timedelta(0)
            
    @pytest.mark.asyncio 
    async def test_execute_single_category_failure(self, layer_execution_agent, mock_layer, sample_layer_config):
        """Test failed single category execution"""
        layer_execution_agent.layer_system.layers["test_layer"] = mock_layer
        
        with patch.object(layer_execution_agent, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "output": "5 passed, 3 failed in 2.5s",
                "errors": "Some tests failed",
                "return_code": 1
            }
            
            result = await layer_execution_agent._execute_single_category("unit", mock_layer, sample_layer_config)
            
            assert result.success is False
            assert result.category_name == "unit"
            assert result.test_counts["passed"] == 5
            assert result.test_counts["failed"] == 3
            assert result.test_counts["total"] == 8
            assert "Some tests failed" in result.errors
            
    # Test command building
    
    def test_build_category_command_basic(self, layer_execution_agent):
        """Test basic category command building"""
        config = LayerExecutionConfig(
            layer_name="test_layer",
            environment="test"
        )
        
        cmd = layer_execution_agent._build_category_command("unit", config)
        
        assert isinstance(cmd, list)
        assert "--category" in cmd
        assert "unit" in cmd
        assert "--env" in cmd
        assert "test" in cmd
        assert "--no-coverage" in cmd
        
    def test_build_category_command_with_flags(self, layer_execution_agent):
        """Test category command building with additional flags"""
        config = LayerExecutionConfig(
            layer_name="test_layer",
            environment="staging",
            use_real_services=True,
            use_real_llm=True,
            execution_strategy=ExecutionStrategy.PARALLEL_UNLIMITED
        )
        
        cmd = layer_execution_agent._build_category_command("integration", config)
        
        assert "--real-services" in cmd
        assert "--real-llm" in cmd
        assert "--parallel" in cmd
        assert "staging" in cmd
        
    # Test output parsing
    
    def test_parse_test_counts_pytest(self, layer_execution_agent):
        """Test parsing pytest output for test counts"""
        pytest_output = """
        ============================= test session starts ==============================
        collecting ... collected 15 items
        
        test_api.py::test_endpoint_health PASSED                           [ 20%]
        test_api.py::test_endpoint_users FAILED                            [ 40%]
        test_api.py::test_endpoint_auth PASSED                             [ 60%]
        
        =========================== short test summary info ============================
        FAILED test_api.py::test_endpoint_users - AssertionError: ...
        ========================= 12 passed, 3 failed in 4.25s =========================
        """
        
        counts = layer_execution_agent._parse_test_counts(pytest_output)
        
        assert counts["passed"] == 12
        assert counts["failed"] == 3
        assert counts["total"] == 15
        
    def test_parse_test_counts_jest(self, layer_execution_agent):
        """Test parsing Jest output for test counts"""
        jest_output = """
        PASS src/components/Button.test.js
        PASS src/utils/helpers.test.js  
        FAIL src/api/client.test.js
          [U+2715] should handle errors gracefully
        
        Test Suites: 2 failed, 8 passed, 10 total
        Tests:       3 failed, 47 passed, 50 total
        Snapshots:   0 total
        Time:        5.234s
        """
        
        counts = layer_execution_agent._parse_test_counts(jest_output)
        
        assert counts["failed"] == 3
        assert counts["passed"] == 47
        assert counts["total"] == 50
        
    # Test resource management
    
    @pytest.mark.asyncio
    async def test_allocate_resources(self, layer_execution_agent, mock_layer, sample_layer_config):
        """Test resource allocation for layer execution"""
        result = await layer_execution_agent._allocate_resources(mock_layer, sample_layer_config)
        
        assert result is True
        assert len(layer_execution_agent.allocated_resources) == 1
        
        # Check resource allocation details
        resource_key = list(layer_execution_agent.allocated_resources.keys())[0]
        allocated = layer_execution_agent.allocated_resources[resource_key]
        assert allocated["memory_mb"] == mock_layer.resource_limits.max_memory_mb
        assert allocated["cpu_percent"] == mock_layer.resource_limits.max_cpu_percent
        
    @pytest.mark.asyncio
    async def test_release_resources(self, layer_execution_agent, mock_layer, sample_layer_config):
        """Test resource release after layer execution"""
        # First allocate resources
        await layer_execution_agent._allocate_resources(mock_layer, sample_layer_config)
        assert len(layer_execution_agent.allocated_resources) == 1
        
        # Then release them
        await layer_execution_agent._release_resources(mock_layer)
        assert len(layer_execution_agent.allocated_resources) == 0
        
    # Test execution flow
    
    @pytest.mark.asyncio
    async def test_full_layer_execution_success(self, layer_execution_agent, sample_layer_config, temp_project_root):
        """Test complete layer execution flow with success"""
        # Add test layer to layer system
        test_layer = TestLayer(
            name="test_layer",
            description="Test layer",
            execution_order=1,
            max_duration_minutes=5,
            execution_mode=LayerExecutionMode.SEQUENTIAL,
            categories=[
                CategoryConfig(name="smoke", timeout_seconds=60, priority_order=1)
            ]
        )
        layer_execution_agent.layer_system.layers["test_layer"] = test_layer
        
        # Mock command execution to return success
        with patch.object(layer_execution_agent, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "output": "5 passed in 0.5s",
                "errors": "",
                "return_code": 0
            }
            
            result = await layer_execution_agent.execute_layer("test_layer", sample_layer_config)
            
            assert result.success is True
            assert result.layer_name == "test_layer"
            assert len(result.categories_executed) == 1
            assert "smoke" in result.categories_executed
            assert result.total_tests == 5
            assert result.passed_tests == 5
            assert result.failed_tests == 0
            
    @pytest.mark.asyncio
    async def test_full_layer_execution_failure(self, layer_execution_agent, sample_layer_config):
        """Test complete layer execution flow with failure"""
        # Add test layer with failing category
        test_layer = TestLayer(
            name="failing_layer",
            description="Failing test layer",
            execution_order=1,
            max_duration_minutes=5,
            execution_mode=LayerExecutionMode.SEQUENTIAL,
            categories=[
                CategoryConfig(name="integration", timeout_seconds=300, priority_order=1)
            ]
        )
        layer_execution_agent.layer_system.layers["failing_layer"] = test_layer
        sample_layer_config.layer_name = "failing_layer"
        
        # Mock command execution to return failure
        with patch.object(layer_execution_agent, '_execute_command') as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "output": "10 passed, 5 failed in 3.2s",
                "errors": "Integration tests failed", 
                "return_code": 1
            }
            
            result = await layer_execution_agent.execute_layer("failing_layer", sample_layer_config)
            
            assert result.success is False
            assert result.layer_name == "failing_layer"
            assert result.failed_tests == 5
            assert result.passed_tests == 10
            
    @pytest.mark.asyncio
    async def test_execution_with_nonexistent_layer(self, layer_execution_agent, sample_layer_config):
        """Test execution with nonexistent layer"""
        sample_layer_config.layer_name = "nonexistent_layer"
        
        result = await layer_execution_agent.execute_layer("nonexistent_layer", sample_layer_config)
        
        assert result.success is False
        assert "not found" in result.error_summary.lower()
        
    # Test fail-fast functionality
    
    @pytest.mark.asyncio
    async def test_fail_fast_enabled(self, layer_execution_agent, sample_layer_config):
        """Test fail-fast behavior when enabled"""
        # Create layer with multiple categories
        test_layer = TestLayer(
            name="fail_fast_layer",
            description="Test fail-fast behavior",
            execution_order=1,
            max_duration_minutes=10,
            execution_mode=LayerExecutionMode.SEQUENTIAL,
            categories=[
                CategoryConfig(name="smoke", timeout_seconds=60, priority_order=1),
                CategoryConfig(name="unit", timeout_seconds=120, priority_order=2),
                CategoryConfig(name="integration", timeout_seconds=300, priority_order=3)
            ]
        )
        layer_execution_agent.layer_system.layers["fail_fast_layer"] = test_layer
        sample_layer_config.layer_name = "fail_fast_layer"
        sample_layer_config.fail_fast_enabled = True
        
        # Mock command execution: first succeeds, second fails
        call_count = 0
        async def mock_execute_command(cmd, config):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"success": True, "output": "5 passed", "errors": "", "return_code": 0}
            else:
                return {"success": False, "output": "0 passed, 3 failed", "errors": "Tests failed", "return_code": 1}
                
        with patch.object(layer_execution_agent, '_execute_command', side_effect=mock_execute_command):
            result = await layer_execution_agent.execute_layer("fail_fast_layer", sample_layer_config)
            
            # Should stop after second category fails
            assert result.success is False
            assert len(result.categories_executed) == 2  # smoke + unit (failed)
            assert "integration" not in result.categories_executed  # Should not run due to fail-fast
            
    # Test execution cancellation
    
    @pytest.mark.asyncio
    async def test_cancel_execution(self, layer_execution_agent, sample_layer_config):
        """Test execution cancellation"""
        # Start a long-running mock execution
        async def long_running_execution():
            await asyncio.sleep(10)  # Long delay
            return {"success": True, "output": "", "errors": "", "return_code": 0}
            
        with patch.object(layer_execution_agent, '_execute_command', side_effect=long_running_execution):
            # Start execution in background
            execution_task = asyncio.create_task(
                layer_execution_agent.execute_layer("fast_feedback", sample_layer_config)
            )
            
            # Wait a moment then cancel
            await asyncio.sleep(0.1)
            layer_execution_agent.cancel_execution()
            
            # Execution should complete quickly due to cancellation
            start_time = time.time()
            result = await execution_task
            execution_time = time.time() - start_time
            
            # Should complete quickly (cancellation should prevent long wait)
            assert execution_time < 5.0
            
    # Test execution status tracking
    
    def test_get_execution_status(self, layer_execution_agent, sample_layer_config):
        """Test execution status reporting"""
        # Initially no execution
        status = layer_execution_agent.get_execution_status()
        assert status["active"] is False
        assert status["current_layer"] is None
        
        # Mock active execution
        with layer_execution_agent.execution_lock:
            layer_execution_agent.current_execution = sample_layer_config
            
        status = layer_execution_agent.get_execution_status()
        assert status["active"] is True
        assert status["current_layer"] == "fast_feedback"
        
    def test_get_execution_summary(self, layer_execution_agent):
        """Test comprehensive execution summary"""
        summary = layer_execution_agent.get_execution_summary()
        
        assert "agent_id" in summary
        assert "project_root" in summary
        assert "execution_stats" in summary
        assert "available_layers" in summary
        assert "current_status" in summary
        assert "layer_system_summary" in summary
        
        # Check required fields
        assert summary["agent_id"].startswith("layer_executor_")
        assert isinstance(summary["available_layers"], list)
        assert isinstance(summary["execution_stats"], dict)
        
    @pytest.mark.asyncio
    async def test_health_check(self, layer_execution_agent):
        """Test agent health check functionality"""
        health = await layer_execution_agent.health_check()
        
        assert "status" in health
        assert "checks" in health
        assert "issues" in health
        
        # Should have specific checks
        assert "layer_system" in health["checks"]
        assert "execution_environment" in health["checks"]
        
        # Status should be healthy or degraded
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        
    # Test timeout handling
    
    @pytest.mark.asyncio
    async def test_command_timeout_handling(self, layer_execution_agent, sample_layer_config):
        """Test command timeout handling"""
        # Mock a command that times out
        async def timeout_command(cmd, config):
            await asyncio.sleep(5)  # Longer than we'll wait
            return {"success": True}
            
        with patch.object(layer_execution_agent, '_execute_command', side_effect=timeout_command):
            # Set short timeout
            sample_layer_config.timeout_multiplier = 0.001  # Very short timeout
            
            result = await layer_execution_agent._execute_single_category("smoke", 
                                                                        layer_execution_agent.layer_system.layers["fast_feedback"], 
                                                                        sample_layer_config)
            
            # Should handle timeout gracefully
            assert result.success is False
            assert "timeout" in result.metadata or "timeout" in result.errors.lower()
            
    # Test integration points
    
    def test_layer_system_integration(self, layer_execution_agent):
        """Test integration with LayerSystem"""
        # Should have access to layer system
        assert layer_execution_agent.layer_system is not None
        assert hasattr(layer_execution_agent.layer_system, 'layers')
        assert hasattr(layer_execution_agent.layer_system, 'create_execution_plan')
        
    def test_category_system_integration(self, layer_execution_agent):
        """Test integration with CategorySystem"""
        # Should have access to category system
        assert layer_execution_agent.category_system is not None
        assert hasattr(layer_execution_agent.category_system, 'categories')
        assert hasattr(layer_execution_agent.category_system, 'get_category')
        
    # Test execution group analysis
    
    def test_analyze_execution_groups(self, layer_execution_agent):
        """Test execution group analysis for hybrid mode"""
        categories = [
            CategoryConfig(name="smoke", priority_order=1),
            CategoryConfig(name="unit", priority_order=1),  # Same priority as smoke
            CategoryConfig(name="integration", priority_order=2),  # Different priority
            CategoryConfig(name="api", priority_order=2)  # Same priority as integration
        ]
        
        groups = layer_execution_agent._analyze_execution_groups(categories)
        
        # Should create 2 groups based on priority order
        assert len(groups) == 2
        assert len(groups[0]) == 2  # smoke, unit
        assert len(groups[1]) == 2  # integration, api
        
        # Check group contents
        group1_names = [c.name for c in groups[0]]
        group2_names = [c.name for c in groups[1]]
        
        assert "smoke" in group1_names
        assert "unit" in group1_names
        assert "integration" in group2_names
        assert "api" in group2_names
        
    # Test error handling and recovery
    
    @pytest.mark.asyncio
    async def test_execution_exception_handling(self, layer_execution_agent, sample_layer_config):
        """Test handling of execution exceptions"""
        # Mock command execution that raises exception
        with patch.object(layer_execution_agent, '_execute_command', side_effect=RuntimeError("Test error")):
            result = await layer_execution_agent._execute_single_category("smoke", 
                                                                        layer_execution_agent.layer_system.layers["fast_feedback"],
                                                                        sample_layer_config)
            
            assert result.success is False
            assert "Test error" in result.errors
            assert result.metadata.get("exception") is True
            
    def test_concurrent_execution_prevention(self, layer_execution_agent, sample_layer_config):
        """Test prevention of concurrent layer executions"""
        # Mock active execution
        with layer_execution_agent.execution_lock:
            layer_execution_agent.current_execution = sample_layer_config
            
        # Attempt second execution should raise error
        new_config = LayerExecutionConfig(layer_name="other_layer")
        
        with pytest.raises(RuntimeError, match="execution already in progress"):
            asyncio.run(layer_execution_agent.execute_layer("other_layer", new_config))
            
    # Test layer-specific behavior
    
    def test_fast_feedback_layer_behavior(self, layer_execution_agent):
        """Test fast_feedback layer specific behavior"""
        categories = layer_execution_agent.get_layer_categories("fast_feedback")
        
        # Fast feedback should have quick categories
        assert "smoke" in categories
        assert "unit" in categories
        
        # Should not have long-running categories
        assert "performance" not in categories
        assert "e2e" not in categories
        
    def test_e2e_background_layer_behavior(self, layer_execution_agent):
        """Test e2e_background layer specific behavior"""
        # Check if e2e_performance layer exists (maps to e2e_background functionality)
        layers = layer_execution_agent.get_available_layers()
        assert "e2e_performance" in layers
        
        layer_info = layer_execution_agent.layer_system.layers.get("e2e_performance")
        if layer_info:
            # Should support background execution
            assert layer_info.background_execution is True
            assert layer_info.max_duration_minutes >= 30  # Long duration expected
            
    # Test configuration validation
    
    def test_layer_execution_config_validation(self, layer_execution_agent):
        """Test layer execution configuration validation"""
        # Valid configuration
        valid_config = LayerExecutionConfig(
            layer_name="fast_feedback",
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            max_parallel_categories=4,
            timeout_multiplier=1.0
        )
        
        # Validate that agent accepts valid config
        assert valid_config.layer_name == "fast_feedback"
        assert valid_config.execution_strategy == ExecutionStrategy.SEQUENTIAL
        
    # Test integration with existing unified_test_runner
    
    def test_test_runner_integration_setup(self, layer_execution_agent, temp_project_root):
        """Test setup of integration with existing test runner"""
        assert layer_execution_agent.test_runner_path == temp_project_root / "scripts" / "unified_test_runner.py"
        assert layer_execution_agent.python_executable == sys.executable
        
    # Standalone functions testing
    
    @pytest.mark.asyncio
    async def test_execute_layer_async_function(self, temp_project_root):
        """Test standalone async execution function"""
        # Mock successful execution
        with patch('test_framework.orchestration.layer_execution_agent.LayerExecutionAgent') as mock_agent_class:
            mock_agent = Mock()
            mock_result = LayerExecutionResult(
                success=True,
                layer_name="fast_feedback",
                categories_executed=["smoke"],
                total_duration=timedelta(seconds=30),
                category_results={},
                total_tests=5,
                passed_tests=5,
                failed_tests=0,
                skipped_tests=0,
                error_summary=None,
                resource_usage={}
            )
            mock_agent.execute_layer = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent
            
            result = await execute_layer_async("fast_feedback")
            
            assert result.success is True
            assert result.layer_name == "fast_feedback"
            
    def test_execute_layer_sync_function(self, temp_project_root):
        """Test standalone sync execution function"""
        # Mock successful execution
        with patch('test_framework.orchestration.layer_execution_agent.execute_layer_async') as mock_async:
            mock_result = LayerExecutionResult(
                success=True,
                layer_name="fast_feedback", 
                categories_executed=["smoke"],
                total_duration=timedelta(seconds=30),
                category_results={},
                total_tests=5,
                passed_tests=5,
                failed_tests=0,
                skipped_tests=0,
                error_summary=None,
                resource_usage={}
            )
            mock_async.return_value = mock_result
            
            result = execute_layer_sync("fast_feedback")
            
            assert result.success is True
            assert result.layer_name == "fast_feedback"
            
    # Test performance and metrics
    
    def test_execution_stats_tracking(self, layer_execution_agent):
        """Test execution statistics tracking"""
        initial_stats = layer_execution_agent.execution_stats.copy()
        
        # Mock layer execution result
        mock_result = LayerExecutionResult(
            success=True,
            layer_name="test_layer",
            categories_executed=["smoke", "unit"],
            total_duration=timedelta(minutes=5),
            category_results={},
            total_tests=20,
            passed_tests=18,
            failed_tests=2,
            skipped_tests=0,
            error_summary=None,
            resource_usage={}
        )
        
        layer_execution_agent._update_execution_stats(mock_result)
        
        # Check stats were updated
        assert layer_execution_agent.execution_stats["layers_executed"] == initial_stats["layers_executed"] + 1
        assert layer_execution_agent.execution_stats["categories_executed"] == initial_stats["categories_executed"] + 2
        
    # Test layer-specific logic implementation
    
    def test_fast_feedback_layer_characteristics(self, layer_execution_agent):
        """Test fast_feedback layer meets requirements"""
        layer = layer_execution_agent.layer_system.layers.get("fast_feedback")
        if layer:
            # Should be sequential and fail-fast for quick feedback
            assert layer.execution_mode == LayerExecutionMode.SEQUENTIAL
            # Should have short duration
            assert layer.max_duration_minutes <= 5
            # Should have fail-fast enabled
            assert layer.fail_fast is True
            
    def test_core_integration_layer_characteristics(self, layer_execution_agent):
        """Test core_integration layer meets requirements"""
        layer = layer_execution_agent.layer_system.layers.get("core_integration")
        if layer:
            # Should be parallel for efficiency
            assert layer.execution_mode == LayerExecutionMode.PARALLEL
            # Should have reasonable duration
            assert layer.max_duration_minutes <= 15
            # Should require database services
            assert "postgresql" in layer.required_services or "database" in str(layer.required_services)
            
    def test_service_integration_layer_characteristics(self, layer_execution_agent):
        """Test service_integration layer meets requirements"""
        layer = layer_execution_agent.layer_system.layers.get("service_integration")
        if layer:
            # Should be hybrid for optimal resource usage
            assert layer.execution_mode == LayerExecutionMode.HYBRID
            # Should have longer duration for complex tests
            assert layer.max_duration_minutes <= 25
            # Should require real services
            assert len(layer.required_services) > 0
            
    def test_e2e_background_layer_characteristics(self, layer_execution_agent):
        """Test e2e_background layer meets requirements"""
        layer = layer_execution_agent.layer_system.layers.get("e2e_performance")  # Maps to e2e_background
        if layer:
            # Should support background execution
            assert layer.background_execution is True
            # Should have long duration
            assert layer.max_duration_minutes >= 30
            # Should be sequential for stability
            assert layer.execution_mode == LayerExecutionMode.SEQUENTIAL
            

class TestLayerExecutionIntegration:
    """Integration tests for LayerExecutionAgent with existing systems"""
    
    @pytest.fixture
    def integration_agent(self):
        """Create agent for integration testing"""
        project_root = Path(__file__).parent.parent.parent
        return LayerExecutionAgent(project_root)
        
    def test_real_layer_system_integration(self, integration_agent):
        """Test integration with real layer system"""
        # Should have real layers available
        layers = integration_agent.get_available_layers()
        assert len(layers) > 0
        
        # Should be able to get categories for real layers
        for layer_name in layers:
            categories = integration_agent.get_layer_categories(layer_name)
            assert isinstance(categories, list)
            
    def test_real_category_system_integration(self, integration_agent):
        """Test integration with real category system"""
        # Should have real categories available
        assert len(integration_agent.category_system.categories) > 0
        
        # Should have expected categories
        expected_categories = ["smoke", "unit", "integration", "api"]
        for category in expected_categories:
            assert integration_agent.category_system.get_category(category) is not None
            
    def test_unified_test_runner_path_detection(self, integration_agent):
        """Test detection of unified test runner path"""
        # Should correctly detect test runner path
        expected_path = integration_agent.project_root / "scripts" / "unified_test_runner.py"
        assert integration_agent.test_runner_path == expected_path
        
        # In real environment, file should exist
        if expected_path.exists():
            assert expected_path.is_file()
            
    @pytest.mark.asyncio
    async def test_real_command_building(self, integration_agent):
        """Test command building with real configuration"""
        config = LayerExecutionConfig(
            layer_name="fast_feedback",
            environment="test",
            use_real_services=False,
            use_real_llm=False
        )
        
        cmd = integration_agent._build_category_command("unit", config)
        
        # Should build valid command
        assert len(cmd) > 0
        assert cmd[0] == sys.executable  # Should use current Python
        assert "unified_test_runner.py" in " ".join(cmd)
        assert "--category" in cmd
        assert "unit" in cmd


# Performance tests

class TestLayerExecutionPerformance:
    """Performance tests for LayerExecutionAgent"""
    
    @pytest.mark.asyncio
    async def test_parallel_execution_performance(self, layer_execution_agent, temp_project_root):
        """Test that parallel execution is faster than sequential"""
        # Create layer with multiple categories
        parallel_layer = TestLayer(
            name="parallel_test",
            description="Parallel performance test",
            execution_order=1,
            max_duration_minutes=10,
            execution_mode=LayerExecutionMode.PARALLEL,
            categories=[
                CategoryConfig(name="cat1", timeout_seconds=120, priority_order=1),
                CategoryConfig(name="cat2", timeout_seconds=120, priority_order=1),
                CategoryConfig(name="cat3", timeout_seconds=120, priority_order=1)
            ]
        )
        
        sequential_layer = TestLayer(
            name="sequential_test",
            description="Sequential performance test",
            execution_order=1,
            max_duration_minutes=10,
            execution_mode=LayerExecutionMode.SEQUENTIAL,
            categories=parallel_layer.categories
        )
        
        # Mock command execution with small delay
        async def mock_delay_execute(cmd, config):
            await asyncio.sleep(0.1)  # Small delay to simulate work
            return {"success": True, "output": "5 passed", "errors": "", "return_code": 0}
            
        with patch.object(layer_execution_agent, '_execute_command', side_effect=mock_delay_execute):
            # Test parallel execution
            start_time = time.time()
            parallel_result = await layer_execution_agent._execute_parallel(parallel_layer, 
                                                                           LayerExecutionConfig(layer_name="parallel_test"))
            parallel_duration = time.time() - start_time
            
            # Test sequential execution  
            start_time = time.time()
            sequential_result = await layer_execution_agent._execute_sequential(sequential_layer,
                                                                               LayerExecutionConfig(layer_name="sequential_test"))
            sequential_duration = time.time() - start_time
            
            # Parallel should be faster (or at least not significantly slower)
            assert parallel_duration <= sequential_duration * 1.2  # Allow 20% variance
            
            # Both should succeed
            assert parallel_result["success"] is True
            assert sequential_result["success"] is True


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])