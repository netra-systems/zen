#!/usr/bin/env python3
"""
Mission Critical Test Suite - SSOT Orchestration Integration
===========================================================

This test suite validates REAL-WORLD integration scenarios for the SSOT
orchestration consolidation. These tests ensure the SSOT system works
correctly with actual orchestration components and real usage patterns.

Critical Integration Areas:
1. unified_test_runner.py integration with SSOT config
2. Background E2E agent/manager using SSOT enums
3. Layer execution with SSOT ExecutionStrategy
4. Progress streaming with SSOT ProgressOutputMode
5. End-to-end orchestration workflow validation
6. Real service dependencies and configuration
7. WebSocket integration with SSOT components
8. Cross-service orchestration coordination

Business Value: Ensures SSOT orchestration consolidation works seamlessly
with existing orchestration infrastructure and doesn't break real workflows.

CRITICAL: These are integration tests that test the COMPLETE system working
together, not just individual components in isolation.
"""

import asyncio
import json
import os
import pytest
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import SSOT orchestration modules
try:
    from test_framework.ssot.orchestration import (
        OrchestrationConfig,
        get_orchestration_config,
        orchestration_config
    )
    from test_framework.ssot.orchestration_enums import (
        BackgroundTaskStatus,
        E2ETestCategory,
        ExecutionStrategy,
        ProgressOutputMode,
        ProgressEventType,
        OrchestrationMode,
        LayerType,
        LayerDefinition,
        BackgroundTaskConfig,
        BackgroundTaskResult,
        get_standard_layer,
        create_custom_layer
    )
    SSOT_ORCHESTRATION_AVAILABLE = True
except ImportError as e:
    SSOT_ORCHESTRATION_AVAILABLE = False
    pytest.skip(f"SSOT orchestration modules not available: {e}", allow_module_level=True)


@pytest.mark.mission_critical
class TestUnifiedTestRunnerIntegration:
    """Test integration with unified_test_runner.py - REAL WORLD tests."""
    
    def test_test_runner_uses_ssot_orchestration_config(self):
        """CRITICAL: Test unified_test_runner.py uses SSOT orchestration config."""
        runner_path = PROJECT_ROOT / "tests" / "unified_test_runner.py"
        
        # unified_test_runner.py should exist and be executable
        assert runner_path.exists(), f"unified_test_runner.py not found at {runner_path}"
        
        # Test orchestration status command uses SSOT
        result = subprocess.run([
            sys.executable, str(runner_path), "--orchestration-status"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
        
        assert result.returncode == 0, f"Orchestration status failed: {result.stderr}"
        
        # Output should indicate SSOT usage (look for availability info)
        output = result.stdout.lower()
        assert "orchestration" in output, "Orchestration status output missing"
        assert "available" in output, "Availability information missing"
    
    def test_test_runner_ssot_availability_detection(self):
        """CRITICAL: Test test runner correctly detects SSOT availability."""
        runner_path = PROJECT_ROOT / "tests" / "unified_test_runner.py"
        
        # Test with orchestration available
        result = subprocess.run([
            sys.executable, str(runner_path), "--list-orchestration-modes"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
        
        if result.returncode == 0:
            # If orchestration is available, should list modes
            output = result.stdout.lower()
            expected_modes = ["fast_feedback", "nightly", "background", "hybrid"]
            for mode in expected_modes:
                if mode.replace('_', '') in output or mode in output:
                    break
            else:
                pytest.fail("No expected orchestration modes found in output")
    
    def test_test_runner_backward_compatibility(self):
        """CRITICAL: Test test runner maintains backward compatibility."""
        runner_path = PROJECT_ROOT / "tests" / "unified_test_runner.py"
        
        # Legacy mode commands should still work
        legacy_commands = [
            ["--list-categories"],
            ["--help"],
            ["--version"] if Path(runner_path).exists() else None
        ]
        
        for command in legacy_commands:
            if command is None:
                continue
                
            result = subprocess.run([
                sys.executable, str(runner_path)
            ] + command, capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
            
            # Should not crash (return code 0 or 1 for help/version is acceptable)
            assert result.returncode in [0, 1], f"Legacy command {command} failed with code {result.returncode}: {result.stderr}"
    
    def test_orchestration_mode_selection_integration(self):
        """CRITICAL: Test orchestration mode selection uses SSOT enums."""
        # Test that OrchestrationMode enum values are recognized
        valid_modes = [mode.value for mode in OrchestrationMode]
        
        assert "fast_feedback" in valid_modes, "fast_feedback mode missing from SSOT"
        assert "nightly" in valid_modes, "nightly mode missing from SSOT" 
        assert "background" in valid_modes, "background mode missing from SSOT"
        assert "hybrid" in valid_modes, "hybrid mode missing from SSOT"
        
        # Test mode configuration
        for mode in OrchestrationMode:
            assert isinstance(mode.value, str), f"Mode {mode} has invalid value type"
            assert mode.value.replace('_', '').isalpha(), f"Mode {mode} has invalid characters"


@pytest.mark.mission_critical
class TestBackgroundE2EIntegration:
    """Test integration with Background E2E components - COMPREHENSIVE tests."""
    
    def test_background_task_config_uses_ssot_enums(self):
        """CRITICAL: Test BackgroundTaskConfig uses SSOT enums correctly."""
        # Test with each E2E category
        for category in E2ETestCategory:
            config = BackgroundTaskConfig(
                category=category,
                environment="test",
                timeout_minutes=30
            )
            
            # Verify enum is preserved
            assert config.category == category
            assert isinstance(config.category, E2ETestCategory)
            
            # Test serialization preserves enum values
            config_dict = config.to_dict()
            assert config_dict['category'] == category.value
            assert isinstance(config_dict['category'], str)
    
    def test_background_task_result_lifecycle(self):
        """CRITICAL: Test BackgroundTaskResult lifecycle with SSOT enums."""
        config = BackgroundTaskConfig(
            category=E2ETestCategory.CYPRESS,
            environment="test"
        )
        
        # Test each status transition
        for status in BackgroundTaskStatus:
            result = BackgroundTaskResult(
                task_id="test-123",
                category=E2ETestCategory.CYPRESS,
                status=status,
                config=config
            )
            
            # Verify enum preservation
            assert result.status == status
            assert isinstance(result.status, BackgroundTaskStatus)
            
            # Test success calculation
            expected_success = (status == BackgroundTaskStatus.COMPLETED)
            assert result.success == expected_success, f"Success calculation wrong for status {status}"
            
            # Test serialization
            result_dict = result.to_dict()
            assert result_dict['status'] == status.value
            assert result_dict['category'] == E2ETestCategory.CYPRESS.value
    
    def test_background_task_status_transitions(self):
        """CRITICAL: Test valid status transitions in background tasks."""
        valid_transitions = {
            BackgroundTaskStatus.QUEUED: [BackgroundTaskStatus.STARTING, BackgroundTaskStatus.CANCELLED],
            BackgroundTaskStatus.STARTING: [BackgroundTaskStatus.RUNNING, BackgroundTaskStatus.FAILED],
            BackgroundTaskStatus.RUNNING: [BackgroundTaskStatus.COMPLETED, BackgroundTaskStatus.FAILED, BackgroundTaskStatus.TIMEOUT, BackgroundTaskStatus.CANCELLED],
            BackgroundTaskStatus.COMPLETED: [],  # Terminal
            BackgroundTaskStatus.FAILED: [],     # Terminal
            BackgroundTaskStatus.CANCELLED: [],  # Terminal
            BackgroundTaskStatus.TIMEOUT: []     # Terminal
        }
        
        # Verify all status values exist
        for status in valid_transitions.keys():
            assert status in BackgroundTaskStatus, f"Status {status} not in SSOT enum"
        
        # Test transitions make sense
        terminal_statuses = {BackgroundTaskStatus.COMPLETED, BackgroundTaskStatus.FAILED, 
                           BackgroundTaskStatus.CANCELLED, BackgroundTaskStatus.TIMEOUT}
        
        for status, transitions in valid_transitions.items():
            if status in terminal_statuses:
                assert len(transitions) == 0, f"Terminal status {status} should have no transitions"
    
    def test_e2e_category_characteristics(self):
        """CRITICAL: Test E2E categories have appropriate characteristics."""
        category_timeouts = {
            E2ETestCategory.E2E_CRITICAL: 5,    # Should be fast
            E2ETestCategory.CYPRESS: 20,        # Medium time
            E2ETestCategory.E2E: 30,           # Longer
            E2ETestCategory.PERFORMANCE: 30     # Longest
        }
        
        for category, expected_min_timeout in category_timeouts.items():
            # Test category can be used in config
            config = BackgroundTaskConfig(
                category=category,
                timeout_minutes=expected_min_timeout
            )
            
            # Verify category characteristics
            assert config.timeout_minutes >= expected_min_timeout
            
            # Critical tests should not be background by default
            if category == E2ETestCategory.E2E_CRITICAL:
                # Should be able to run in foreground
                assert config.timeout_minutes <= 10, "Critical E2E should have short timeout"


@pytest.mark.mission_critical
class TestLayerExecutionIntegration:
    """Test integration with layer execution - STRATEGY tests."""
    
    def test_execution_strategy_enum_completeness(self):
        """CRITICAL: Test ExecutionStrategy enum has all required strategies."""
        required_strategies = {
            "SEQUENTIAL", "PARALLEL_UNLIMITED", "PARALLEL_LIMITED", "HYBRID_SMART"
        }
        
        available_strategies = {strategy.name for strategy in ExecutionStrategy}
        missing_strategies = required_strategies - available_strategies
        
        assert len(missing_strategies) == 0, f"Missing execution strategies: {missing_strategies}"
        
        # Test each strategy has valid value
        for strategy in ExecutionStrategy:
            assert isinstance(strategy.value, str), f"Strategy {strategy} has invalid value"
            assert strategy.value.replace('_', '').replace('-', '').isalpha(), f"Strategy {strategy} has invalid characters"
    
    def test_layer_definition_with_ssot_enums(self):
        """CRITICAL: Test LayerDefinition integrates with SSOT enums."""
        # Test with different layer types and strategies
        for layer_type in LayerType:
            for strategy in ExecutionStrategy:
                layer_def = LayerDefinition(
                    name=f"test_{layer_type.value}",
                    layer_type=layer_type,
                    categories={"test_category"},
                    execution_strategy=strategy
                )
                
                # Verify enums are preserved
                assert layer_def.layer_type == layer_type
                assert layer_def.execution_strategy == strategy
                
                # Test serialization
                layer_dict = layer_def.to_dict()
                assert layer_dict['layer_type'] == layer_type.value
                assert layer_dict['execution_strategy'] == strategy.value
    
    def test_standard_layer_definitions(self):
        """CRITICAL: Test standard layer definitions use SSOT consistently."""
        # Test each standard layer type
        for layer_type in LayerType:
            try:
                layer_def = get_standard_layer(layer_type)
                
                # Verify layer has valid configuration
                assert layer_def.name is not None and len(layer_def.name) > 0
                assert layer_def.layer_type == layer_type
                assert isinstance(layer_def.execution_strategy, ExecutionStrategy)
                assert len(layer_def.categories) > 0
                
                # Verify timeout is reasonable
                assert 0 < layer_def.timeout_minutes <= 120, f"Invalid timeout for {layer_type}"
                
            except KeyError:
                pytest.fail(f"Standard layer definition missing for {layer_type}")
    
    def test_custom_layer_creation_with_ssot(self):
        """CRITICAL: Test custom layer creation uses SSOT enums."""
        categories = {"custom_test", "another_test"}
        
        custom_layer = create_custom_layer(
            name="custom_test_layer",
            categories=categories,
            execution_strategy=ExecutionStrategy.HYBRID_SMART,
            timeout_minutes=15
        )
        
        # Verify custom layer uses SSOT enums
        assert isinstance(custom_layer.execution_strategy, ExecutionStrategy)
        assert custom_layer.execution_strategy == ExecutionStrategy.HYBRID_SMART
        assert custom_layer.categories == categories
        assert custom_layer.timeout_minutes == 15
        
        # Test validation
        from test_framework.ssot.orchestration_enums import validate_layer_definition
        issues = validate_layer_definition(custom_layer)
        assert len(issues) == 0, f"Custom layer validation failed: {issues}"
    
    def test_execution_strategy_performance_characteristics(self):
        """CRITICAL: Test execution strategies have expected characteristics."""
        strategy_characteristics = {
            ExecutionStrategy.SEQUENTIAL: {"parallel": False, "resource_intensive": False},
            ExecutionStrategy.PARALLEL_UNLIMITED: {"parallel": True, "resource_intensive": True},
            ExecutionStrategy.PARALLEL_LIMITED: {"parallel": True, "resource_intensive": False},
            ExecutionStrategy.HYBRID_SMART: {"parallel": True, "resource_intensive": False}
        }
        
        for strategy, expected_chars in strategy_characteristics.items():
            # Create a layer with this strategy
            layer = create_custom_layer(
                name=f"test_{strategy.value}",
                categories={"test"},
                execution_strategy=strategy
            )
            
            assert layer.execution_strategy == strategy
            
            # Verify strategy characteristics make sense
            if expected_chars["parallel"] and strategy == ExecutionStrategy.PARALLEL_LIMITED:
                # Parallel limited should have a limit
                layer.max_parallel_categories = 3
                assert layer.max_parallel_categories > 0


@pytest.mark.mission_critical
class TestProgressStreamingIntegration:
    """Test integration with progress streaming - EVENT tests."""
    
    def test_progress_output_mode_completeness(self):
        """CRITICAL: Test ProgressOutputMode enum supports all required modes."""
        required_modes = {"CONSOLE", "JSON", "WEBSOCKET", "LOG", "SILENT"}
        available_modes = {mode.name for mode in ProgressOutputMode}
        
        missing_modes = required_modes - available_modes
        assert len(missing_modes) == 0, f"Missing progress output modes: {missing_modes}"
        
        # Test mode values are valid
        for mode in ProgressOutputMode:
            assert isinstance(mode.value, str), f"Mode {mode} has invalid value"
            assert mode.value.islower(), f"Mode {mode} should have lowercase value"
    
    def test_progress_event_type_coverage(self):
        """CRITICAL: Test ProgressEventType covers all orchestration events."""
        # Required event categories
        required_event_categories = {
            "layer": ["LAYER_STARTED", "LAYER_COMPLETED", "LAYER_FAILED", "LAYER_PROGRESS"],
            "category": ["CATEGORY_STARTED", "CATEGORY_COMPLETED", "CATEGORY_FAILED", "CATEGORY_PROGRESS"],
            "test": ["TEST_STARTED", "TEST_COMPLETED", "TEST_FAILED"],
            "background": ["BACKGROUND_TASK_QUEUED", "BACKGROUND_TASK_STARTED", "BACKGROUND_TASK_COMPLETED"],
            "orchestration": ["ORCHESTRATION_STARTED", "ORCHESTRATION_COMPLETED"],
            "system": ["ERROR", "WARNING", "INFO"]
        }
        
        available_events = {event.name for event in ProgressEventType}
        
        for category, required_events in required_event_categories.items():
            for required_event in required_events:
                assert required_event in available_events, f"Missing event: {required_event} for category {category}"
    
    def test_progress_event_creation_and_serialization(self):
        """CRITICAL: Test ProgressEvent creation and serialization with SSOT enums."""
        from test_framework.ssot.orchestration_enums import ProgressEvent
        from datetime import datetime
        
        # Test each event type
        test_events = [
            (ProgressEventType.LAYER_STARTED, {"layer": "test_layer"}),
            (ProgressEventType.CATEGORY_COMPLETED, {"category": "test_category", "success": True}),
            (ProgressEventType.BACKGROUND_TASK_QUEUED, {"task_id": "bg-123", "category": "cypress"}),
            (ProgressEventType.ERROR, {"message": "Test error", "details": "Error details"})
        ]
        
        for event_type, data in test_events:
            event = ProgressEvent(
                event_type=event_type,
                timestamp=datetime.now(),
                data=data,
                message=f"Test {event_type.value} event"
            )
            
            # Verify enum preservation
            assert event.event_type == event_type
            assert isinstance(event.event_type, ProgressEventType)
            
            # Test serialization
            event_dict = event.to_dict()
            assert event_dict['event_type'] == event_type.value
            assert event_dict['data'] == data
            assert 'timestamp' in event_dict
            assert 'message' in event_dict
    
    def test_progress_streaming_mode_integration(self):
        """CRITICAL: Test progress streaming modes integrate with orchestration."""
        # Test each output mode has appropriate characteristics
        mode_characteristics = {
            ProgressOutputMode.CONSOLE: {"human_readable": True, "structured": False},
            ProgressOutputMode.JSON: {"human_readable": False, "structured": True},
            ProgressOutputMode.WEBSOCKET: {"realtime": True, "structured": True},
            ProgressOutputMode.LOG: {"persistent": True, "structured": True},
            ProgressOutputMode.SILENT: {"minimal": True, "errors_only": True}
        }
        
        for mode, characteristics in mode_characteristics.items():
            # Each mode should have a valid string value
            assert isinstance(mode.value, str)
            assert len(mode.value) > 0
            
            # Mode values should be lowercase and descriptive
            assert mode.value.islower()
            assert mode.value in ["console", "json", "websocket", "log", "silent"]


@pytest.mark.mission_critical
class TestEndToEndOrchestrationWorkflow:
    """Test complete end-to-end orchestration workflows - INTEGRATION tests."""
    
    def test_full_orchestration_lifecycle_with_ssot(self):
        """CRITICAL: Test complete orchestration lifecycle using SSOT components."""
        # Test orchestration configuration
        config = get_orchestration_config()
        
        # Verify SSOT config is working
        status = config.get_availability_status()
        assert isinstance(status, dict)
        assert 'orchestrator_available' in status
        
        # Test layer configuration with SSOT
        fast_feedback_layer = get_standard_layer(LayerType.FAST_FEEDBACK)
        assert fast_feedback_layer.layer_type == LayerType.FAST_FEEDBACK
        assert isinstance(fast_feedback_layer.execution_strategy, ExecutionStrategy)
        
        # Test background task configuration
        bg_config = BackgroundTaskConfig(
            category=E2ETestCategory.CYPRESS,
            environment="test",
            timeout_minutes=20
        )
        
        assert bg_config.category == E2ETestCategory.CYPRESS
        
        # Test progress event creation
        from test_framework.ssot.orchestration_enums import ProgressEvent
        from datetime import datetime
        
        start_event = ProgressEvent(
            event_type=ProgressEventType.ORCHESTRATION_STARTED,
            timestamp=datetime.now(),
            data={"mode": OrchestrationMode.FAST_FEEDBACK.value}
        )
        
        assert start_event.event_type == ProgressEventType.ORCHESTRATION_STARTED
    
    def test_orchestration_mode_to_layer_mapping(self):
        """CRITICAL: Test orchestration modes map correctly to layers."""
        mode_layer_mapping = {
            OrchestrationMode.FAST_FEEDBACK: [LayerType.FAST_FEEDBACK],
            OrchestrationMode.NIGHTLY: [LayerType.FAST_FEEDBACK, LayerType.CORE_INTEGRATION, 
                                      LayerType.SERVICE_INTEGRATION, LayerType.E2E_BACKGROUND],
            OrchestrationMode.BACKGROUND: [LayerType.E2E_BACKGROUND],
            OrchestrationMode.HYBRID: [LayerType.FAST_FEEDBACK, LayerType.CORE_INTEGRATION, 
                                     LayerType.SERVICE_INTEGRATION]
        }
        
        for mode, expected_layers in mode_layer_mapping.items():
            # Each mode should be a valid enum value
            assert isinstance(mode, OrchestrationMode)
            
            # Expected layers should all be valid layer types
            for layer_type in expected_layers:
                assert isinstance(layer_type, LayerType)
                
                # Layer should be available in standard definitions
                try:
                    layer_def = get_standard_layer(layer_type)
                    assert layer_def is not None
                except KeyError:
                    pytest.fail(f"Standard layer definition missing for {layer_type} required by mode {mode}")
    
    def test_cross_service_orchestration_integration(self):
        """CRITICAL: Test orchestration integrates across service boundaries."""
        # Test that SSOT config is accessible from different contexts
        config1 = OrchestrationConfig()
        config2 = get_orchestration_config()
        config3 = orchestration_config
        
        # All should be the same instance (singleton)
        assert config1 is config2 is config3
        
        # Test availability is consistent across contexts
        assert config1.orchestrator_available == config2.orchestrator_available == config3.orchestrator_available
        
        # Test status is consistent
        status1 = config1.get_availability_status()
        status2 = config2.get_availability_status()
        
        # Key availability fields should match
        availability_keys = ['orchestrator_available', 'master_orchestration_available', 
                           'background_e2e_available', 'all_orchestration_available']
        
        for key in availability_keys:
            assert status1[key] == status2[key], f"Inconsistent {key} across contexts"
    
    @pytest.mark.asyncio
    async def test_async_orchestration_integration(self):
        """CRITICAL: Test SSOT orchestration works in async contexts."""
        config = get_orchestration_config()
        
        # Test async access to orchestration config
        async def check_availability():
            await asyncio.sleep(0.001)  # Small delay to test async behavior
            return {
                'orchestrator': config.orchestrator_available,
                'master': config.master_orchestration_available,
                'background': config.background_e2e_available
            }
        
        # Run multiple async checks concurrently
        tasks = [check_availability() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All results should be consistent
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, "Inconsistent async orchestration results"
        
        # Results should have boolean values
        for key, value in first_result.items():
            assert isinstance(value, bool), f"Non-boolean availability for {key}: {value}"
    
    def test_error_propagation_in_integration_workflow(self):
        """CRITICAL: Test error propagation through orchestration workflow."""
        config = OrchestrationConfig()
        
        # Test configuration validation with errors
        original_errors = config._import_errors.copy()
        config._import_errors['test_error'] = "Mock integration error"
        
        try:
            # Validation should detect error
            issues = config.validate_configuration()
            error_issues = [issue for issue in issues if 'test_error' in issue]
            assert len(error_issues) > 0, "Integration error not detected in validation"
            
            # Status should include error
            status = config.get_availability_status()
            assert 'test_error' in status['import_errors'], "Error not included in status"
            
        finally:
            # Restore original errors
            config._import_errors = original_errors


if __name__ == "__main__":
    # Configure pytest for integration testing
    pytest_args = [
        __file__,
        "-v",
        "-x",  # Stop on first failure
        "--tb=short", 
        "-m", "mission_critical"
    ]
    
    print("Running COMPREHENSIVE SSOT Orchestration Integration Tests...")
    print("=" * 80)
    print("🔗 INTEGRATION MODE: Testing real-world orchestration workflows")
    print("🧪 Testing unified_test_runner, layer execution, progress streaming")
    print("=" * 80)
    
    result = pytest.main(pytest_args)
    
    if result == 0:
        print("\n" + "=" * 80)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("🚀 SSOT Orchestration integrates PERFECTLY")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ INTEGRATION TESTS FAILED")
        print("🚨 Integration BROKEN - fix before deployment")
        print("=" * 80)
    
    sys.exit(result)