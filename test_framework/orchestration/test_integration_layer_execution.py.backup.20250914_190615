#!/usr/bin/env python3
"""
Integration tests for LayerExecutionAgent with the existing test system

These tests validate that the LayerExecutionAgent integrates properly with:
- Existing unified_test_runner.py
- Layer system configuration
- Category system 
- Real test execution (when available)
"""

import asyncio
import pytest
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

from test_framework.orchestration.layer_execution_agent import (
    LayerExecutionAgent, LayerExecutionConfig, ExecutionStrategy
)


class TestLayerExecutionIntegration:
    """Integration tests for LayerExecutionAgent with existing systems"""
    
    @pytest.fixture
    def project_root(self):
        """Get actual project root for integration testing"""
        return Path(__file__).parent.parent.parent
        
    @pytest.fixture
    def integration_agent(self, project_root):
        """Create agent with real project structure"""
        return LayerExecutionAgent(project_root)
        
    def test_real_layer_system_loading(self, integration_agent):
        """Test that layer system loads real configuration"""
        # Should load layers from configuration
        layers = integration_agent.get_available_layers()
        assert len(layers) > 0
        
        # Should have expected layers from our configuration
        expected_layers = ["fast_feedback", "core_integration", "service_integration"]
        for layer in expected_layers:
            assert layer in layers or f"Expected layer {layer} in {layers}"
            
    def test_layer_category_mapping(self, integration_agent):
        """Test that layers contain expected categories"""
        # Fast feedback should have smoke and unit
        fast_feedback_categories = integration_agent.get_layer_categories("fast_feedback")
        assert "smoke" in fast_feedback_categories
        assert "unit" in fast_feedback_categories
        
        # Core integration should have database, api, websocket, integration
        core_integration_categories = integration_agent.get_layer_categories("core_integration")
        expected_core_categories = ["database", "api", "websocket", "integration"]
        for category in expected_core_categories:
            assert category in core_integration_categories
            
    def test_unified_test_runner_path_detection(self, integration_agent, project_root):
        """Test that unified test runner path is correctly detected"""
        expected_path = project_root / "scripts" / "unified_test_runner.py"
        assert integration_agent.test_runner_path == expected_path
        
        # Check if the actual file exists (it should in the real project)
        if expected_path.exists():
            assert expected_path.is_file()
            
    def test_category_system_integration(self, integration_agent):
        """Test integration with CategorySystem"""
        # Should have categories loaded
        assert len(integration_agent.category_system.categories) > 0
        
        # Should have expected categories
        expected_categories = ["smoke", "unit", "integration", "database", "api"]
        for category in expected_categories:
            cat_obj = integration_agent.category_system.get_category(category)
            assert cat_obj is not None, f"Category {category} not found in category system"
            
    @pytest.mark.asyncio
    async def test_command_building_integration(self, integration_agent):
        """Test that commands are built correctly for real execution"""
        config = LayerExecutionConfig(
            layer_name="fast_feedback",
            environment="test",
            execution_strategy=ExecutionStrategy.SEQUENTIAL
        )
        
        # Build command for smoke tests
        cmd = integration_agent._build_category_command("smoke", config)
        
        # Validate command structure
        assert isinstance(cmd, list)
        assert len(cmd) > 0
        assert cmd[0] == sys.executable
        assert any("unified_test_runner.py" in str(part) for part in cmd)
        assert "--category" in cmd
        assert "smoke" in cmd
        assert "--env" in cmd
        assert "test" in cmd
        
    @pytest.mark.asyncio 
    async def test_layer_configuration_validation(self, integration_agent):
        """Test validation of layer configurations"""
        # Test valid layer
        issues = integration_agent.validate_layer_configuration("fast_feedback")
        # Should either have no issues or only minor ones
        critical_issues = [issue for issue in issues if "not found" in issue.lower()]
        assert len(critical_issues) == 0
        
        # Test invalid layer
        issues = integration_agent.validate_layer_configuration("nonexistent_layer")
        assert len(issues) > 0
        assert any("not found" in issue.lower() for issue in issues)
        
    @pytest.mark.asyncio
    async def test_health_check_integration(self, integration_agent):
        """Test health check with real system components"""
        health = await integration_agent.health_check()
        
        # Should have health status
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        
        # Should perform checks
        assert "layer_system" in health["checks"]
        assert "test_runner_integration" in health["checks"]
        assert "execution_environment" in health["checks"]
        
        # Layer system should be healthy (we have configuration)
        assert health["checks"]["layer_system"] is True
        
        # Test runner integration should be healthy if file exists
        if integration_agent.test_runner_path.exists():
            assert health["checks"]["test_runner_integration"] is True
            
    def test_execution_summary_integration(self, integration_agent):
        """Test comprehensive execution summary"""
        summary = integration_agent.get_execution_summary()
        
        # Should have all required sections
        required_sections = [
            "agent_id", "project_root", "execution_stats", 
            "available_layers", "current_status", "layer_system_summary"
        ]
        
        for section in required_sections:
            assert section in summary, f"Missing section: {section}"
            
        # Validate content types
        assert isinstance(summary["available_layers"], list)
        assert len(summary["available_layers"]) > 0
        assert isinstance(summary["execution_stats"], dict)
        assert isinstance(summary["layer_system_summary"], dict)
        
    def test_layer_system_configuration_integrity(self, integration_agent):
        """Test that layer system configuration is internally consistent"""
        # Test configuration validation
        layer_system = integration_agent.layer_system
        config_issues = layer_system.validate_configuration()
        
        # Should not have critical configuration errors
        critical_issues = [
            issue for issue in config_issues 
            if any(word in issue.lower() for word in ["circular", "dependency", "error"])
        ]
        
        # Log any issues for debugging but don't fail on warnings
        if config_issues:
            print(f"Layer configuration issues (for review): {config_issues}")
            
        # Critical issues should not exist
        assert len(critical_issues) == 0, f"Critical layer configuration issues: {critical_issues}"
        
    def test_category_dependency_resolution(self, integration_agent):
        """Test that category dependencies can be resolved properly"""
        category_system = integration_agent.category_system
        
        # Test creating execution plan with dependencies
        test_categories = ["smoke", "unit", "integration", "database"]
        
        # This should not raise an exception
        try:
            execution_plan = category_system.create_execution_plan(test_categories)
            assert execution_plan is not None
            assert len(execution_plan.execution_order) > 0
        except ValueError as e:
            if "circular dependency" in str(e).lower():
                pytest.fail(f"Circular dependency detected in categories: {e}")
            else:
                raise
                
    @pytest.mark.asyncio
    async def test_resource_allocation_integration(self, integration_agent):
        """Test resource allocation with real layer configurations"""
        # Get a real layer
        layer = integration_agent.layer_system.layers.get("fast_feedback")
        assert layer is not None
        
        config = LayerExecutionConfig(
            layer_name="fast_feedback",
            environment="test"
        )
        
        # Test resource allocation
        allocated = await integration_agent._allocate_resources(layer, config)
        assert allocated is True
        
        # Check that resources were allocated
        assert len(integration_agent.allocated_resources) > 0
        
        # Test resource release
        await integration_agent._release_resources(layer)
        
        # Resources should be cleaned up
        assert len(integration_agent.allocated_resources) == 0
        
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_mock_layer_execution_flow(self, integration_agent):
        """Test complete layer execution flow with mocked test runner"""
        
        # Create configuration for fast_feedback layer
        config = LayerExecutionConfig(
            layer_name="fast_feedback",
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            environment="test",
            timeout_multiplier=0.1,  # Speed up for testing
            fail_fast_enabled=False
        )
        
        # Mock the command execution to avoid running real tests
        async def mock_successful_command(cmd, config):
            """Mock successful test execution"""
            # Simulate brief execution time
            await asyncio.sleep(0.01)
            
            # Return successful result based on category
            category = "unknown"
            for i, arg in enumerate(cmd):
                if arg == "--category" and i + 1 < len(cmd):
                    category = cmd[i + 1]
                    break
                    
            if category == "smoke":
                return {
                    "success": True,
                    "output": "5 passed in 0.5s",
                    "errors": "",
                    "return_code": 0
                }
            elif category == "unit":
                return {
                    "success": True,
                    "output": "25 passed in 2.1s",
                    "errors": "",
                    "return_code": 0
                }
            else:
                return {
                    "success": True,
                    "output": "10 passed in 1.0s",
                    "errors": "",
                    "return_code": 0
                }
                
        with patch.object(integration_agent, '_execute_command', side_effect=mock_successful_command):
            # Execute layer
            result = await integration_agent.execute_layer("fast_feedback", config)
            
            # Validate result
            assert result.success is True
            assert result.layer_name == "fast_feedback"
            assert len(result.categories_executed) >= 2  # Should have smoke and unit
            assert "smoke" in result.categories_executed
            assert "unit" in result.categories_executed
            assert result.total_tests > 0
            assert result.passed_tests > 0
            assert result.failed_tests == 0  # Mock returns all passing
            
    @pytest.mark.asyncio
    @pytest.mark.slow  
    async def test_mock_layer_execution_with_failure(self, integration_agent):
        """Test layer execution with simulated failures"""
        
        config = LayerExecutionConfig(
            layer_name="core_integration",
            execution_strategy=ExecutionStrategy.PARALLEL,
            environment="test",
            timeout_multiplier=0.1,
            fail_fast_enabled=False
        )
        
        # Mock command execution with some failures
        call_count = 0
        async def mock_mixed_results_command(cmd, config):
            nonlocal call_count
            call_count += 1
            
            await asyncio.sleep(0.01)
            
            category = "unknown"
            for i, arg in enumerate(cmd):
                if arg == "--category" and i + 1 < len(cmd):
                    category = cmd[i + 1]
                    break
                    
            # Make database tests fail, others succeed
            if category == "database":
                return {
                    "success": False,
                    "output": "8 passed, 2 failed in 3.2s",
                    "errors": "Database connection tests failed",
                    "return_code": 1
                }
            else:
                return {
                    "success": True,
                    "output": "15 passed in 2.0s",
                    "errors": "",
                    "return_code": 0
                }
                
        with patch.object(integration_agent, '_execute_command', side_effect=mock_mixed_results_command):
            result = await integration_agent.execute_layer("core_integration", config)
            
            # Should have mixed results
            assert result.success is False  # Overall failure due to database tests
            assert result.layer_name == "core_integration"
            assert len(result.categories_executed) >= 2
            assert result.failed_tests > 0  # Should have some failures
            assert result.passed_tests > 0  # Should have some passes
            
    def test_execution_strategy_mapping(self, integration_agent):
        """Test that execution strategies map correctly to layer execution modes"""
        
        # Get layers and check their execution modes align with strategies
        layers = integration_agent.layer_system.layers
        
        # Fast feedback should be sequential (fail-fast)
        if "fast_feedback" in layers:
            layer = layers["fast_feedback"]
            assert layer.execution_mode.value in ["sequential"], f"Fast feedback should be sequential, got {layer.execution_mode}"
            
        # Core integration should be parallel (efficiency)
        if "core_integration" in layers:
            layer = layers["core_integration"]
            assert layer.execution_mode.value in ["parallel"], f"Core integration should be parallel, got {layer.execution_mode}"
            
        # Service integration should be hybrid (smart)
        if "service_integration" in layers:
            layer = layers["service_integration"]
            assert layer.execution_mode.value in ["hybrid"], f"Service integration should be hybrid, got {layer.execution_mode}"
            
    def test_background_execution_layer_detection(self, integration_agent):
        """Test detection of layers that support background execution"""
        
        layers = integration_agent.layer_system.layers
        background_layers = [
            name for name, layer in layers.items() 
            if layer.background_execution
        ]
        
        # Should have at least one background layer
        assert len(background_layers) > 0, "Should have at least one background execution layer"
        
        # E2E/performance layers should support background execution
        background_layer_patterns = ["e2e", "performance", "background"]
        found_background_pattern = any(
            any(pattern in layer_name.lower() for pattern in background_layer_patterns)
            for layer_name in background_layers
        )
        
        assert found_background_pattern, f"Expected background execution layer, found: {background_layers}"
        
    @pytest.mark.asyncio
    async def test_timeout_handling_integration(self, integration_agent):
        """Test timeout handling with realistic scenarios"""
        
        config = LayerExecutionConfig(
            layer_name="fast_feedback",
            timeout_multiplier=0.01,  # Very short timeout
            environment="test"
        )
        
        # Mock a slow command that should timeout
        async def slow_command(cmd, config):
            await asyncio.sleep(1.0)  # 1 second delay (should timeout)
            return {"success": True, "output": "", "errors": "", "return_code": 0}
            
        with patch.object(integration_agent, '_execute_command', side_effect=slow_command):
            # Should handle timeout gracefully
            result = await integration_agent._execute_single_category("smoke", 
                                                                    integration_agent.layer_system.layers["fast_feedback"],
                                                                    config)
            
            # Should complete quickly and report timeout
            assert result.duration.total_seconds() < 2.0  # Should not wait full 1 second
            # Timeout should be reflected in result
            assert not result.success or "timeout" in result.errors.lower()
            
    @pytest.mark.asyncio
    async def test_concurrent_execution_prevention_integration(self, integration_agent):
        """Test that concurrent executions are properly prevented"""
        
        config1 = LayerExecutionConfig(layer_name="fast_feedback", environment="test")
        config2 = LayerExecutionConfig(layer_name="core_integration", environment="test")
        
        # Mock a long-running execution
        async def long_execution(cmd, config):
            await asyncio.sleep(0.5)
            return {"success": True, "output": "", "errors": "", "return_code": 0}
            
        with patch.object(integration_agent, '_execute_command', side_effect=long_execution):
            # Start first execution
            task1 = asyncio.create_task(integration_agent.execute_layer("fast_feedback", config1))
            
            # Wait briefly to ensure first execution starts
            await asyncio.sleep(0.01)
            
            # Attempt second execution - should be rejected
            with pytest.raises(RuntimeError, match="execution already in progress"):
                await integration_agent.execute_layer("core_integration", config2)
                
            # Clean up
            await task1


class TestRealSystemCompatibility:
    """Test compatibility with real system components (when available)"""
    
    @pytest.fixture
    def project_root(self):
        return Path(__file__).parent.parent.parent
        
    def test_unified_test_runner_compatibility(self, project_root):
        """Test that unified test runner can be invoked (if it exists)"""
        test_runner_path = project_root / "scripts" / "unified_test_runner.py"
        
        if test_runner_path.exists():
            # Test that it can be invoked with --help
            try:
                result = subprocess.run(
                    [sys.executable, str(test_runner_path), "--help"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(project_root)
                )
                
                # Should either succeed or fail gracefully (not crash)
                assert result.returncode in [0, 1, 2], f"Unexpected return code: {result.returncode}"
                
                # Should produce some output
                assert len(result.stdout) > 0 or len(result.stderr) > 0
                
            except subprocess.TimeoutExpired:
                pytest.fail("Unified test runner timed out on --help")
            except Exception as e:
                pytest.fail(f"Error invoking unified test runner: {e}")
                
    def test_layer_system_config_file_validity(self, project_root):
        """Test that layer system configuration file is valid"""
        config_path = project_root / "test_framework" / "config" / "test_layers.yaml"
        
        if config_path.exists():
            # Test that it can be loaded
            try:
                import yaml
                with open(config_path) as f:
                    config_data = yaml.safe_load(f)
                    
                # Should have basic structure
                assert isinstance(config_data, dict)
                assert "layers" in config_data
                assert isinstance(config_data["layers"], dict)
                assert len(config_data["layers"]) > 0
                
                # Should have execution config
                assert "execution_config" in config_data
                
            except Exception as e:
                pytest.fail(f"Error loading layer configuration: {e}")
                
    def test_import_compatibility(self):
        """Test that all required imports work"""
        
        # Test core framework imports
        try:
            from test_framework.orchestration.layer_execution_agent import LayerExecutionAgent
            from test_framework.layer_system import LayerSystem
            from test_framework.category_system import CategorySystem
        except ImportError as e:
            pytest.fail(f"Failed to import required modules: {e}")
            
        # Test that classes can be instantiated
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                agent = LayerExecutionAgent(Path(temp_dir))
                assert agent is not None
        except Exception as e:
            pytest.fail(f"Failed to instantiate LayerExecutionAgent: {e}")
            

if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])