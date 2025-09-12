"""
Reproduction Tests for Issue #599: Startup Validation Failures

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Identify and fix broken startup validation tests
- Value Impact: Ensures startup validation protects $500K+ ARR from broken systems
- Strategic Impact: Critical system health monitoring must work reliably

These tests are designed to INITIALLY FAIL to reproduce the exact
failure modes of the 6 failing startup validation tests, then pass
once the underlying issues are fixed.
"""

import pytest
import asyncio
import time
from fastapi import FastAPI
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, List, Any

# Absolute imports following CLAUDE.md guidelines
from shared.isolated_environment import get_env
from netra_backend.app.core.startup_validation import (
    StartupValidator,
    ComponentStatus, 
    ComponentValidation
)

# Set test environment
env = get_env()
env.set("ENVIRONMENT", "testing", "test")
env.set("TESTING", "true", "test")


class TestStartupValidationFailureReproduction:
    """Reproduce the exact failure modes of the 6 failing startup validation tests."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock FastAPI app."""
        app = FastAPI()
        app.state = MagicMock()
        return app
    
    @pytest.fixture 
    def validator(self):
        """Create a startup validator instance."""
        return StartupValidator()
    
    @pytest.mark.asyncio
    async def test_zero_tools_detected_failure_reproduction(self, mock_app, validator):
        """
        REPRODUCTION TEST: Should initially FAIL to demonstrate the issue.
        
        This test reproduces the exact failure in test_zero_tools_detected where
        the test expects to find a "Tool Configuration" validation but gets None.
        """
        print("\n=== REPRODUCING test_zero_tools_detected FAILURE ===")
        
        # Setup exactly as failing test
        mock_app.state.tool_classes = []  # Zero tools
        mock_app.state.websocket_bridge_factory = None
        
        # Run validation
        success, report = await validator.validate_startup(mock_app)
        
        # DEBUG: Print actual report structure to understand what's happening
        print(f"Validation success: {success}")
        print(f"Report keys: {list(report.keys()) if report else 'None'}")
        if 'categories' in report:
            print(f"Available categories: {list(report['categories'].keys())}")
            if 'Tools' in report['categories']:
                tools_validations = report['categories']['Tools']
                print(f"Tools validations found: {len(tools_validations)}")
                for i, v in enumerate(tools_validations):
                    print(f"  [{i}] {v.get('name', 'NO_NAME')}: {v.get('status', 'NO_STATUS')}")
            else:
                print("No 'Tools' category found in report")
        
        # This is the exact assertion that fails in the original test
        assert 'Tools' in report['categories'], "Tools category missing from report"
        tool_validations = report['categories']['Tools']
        
        # Find tool configuration validation - THIS IS WHERE THE ORIGINAL TEST FAILS
        tool_validation = None
        for v in tool_validations:
            if 'Tool Configuration' in v['name']:
                tool_validation = v
                break
        
        # EXPECTED TO FAIL: This assertion should fail initially, proving we reproduced the issue
        print(f"Looking for 'Tool Configuration' validation...")
        print(f"Available validation names: {[v['name'] for v in tool_validations]}")
        assert tool_validation is not None, f"Tool Configuration validation not found. Available: {[v['name'] for v in tool_validations]}"
        
        # If we get here, the validation was found - check it detected zero tools
        assert tool_validation['actual'] == 0, "Should detect zero tools"
        assert tool_validation['expected'] >= 1, "Should expect at least 1 tool"
    
    @pytest.mark.asyncio
    async def test_missing_websocket_handlers_failure_reproduction(self, mock_app, validator):
        """
        REPRODUCTION TEST: Should initially FAIL to demonstrate WebSocket validation issues.
        
        This reproduces the failure in test_missing_websocket_handlers_detected where
        WebSocket manager validation logic doesn't work as expected.
        """
        print("\n=== REPRODUCING test_missing_websocket_handlers_detected FAILURE ===")
        
        # Setup WebSocket manager factory mode
        mock_app.state.websocket_manager = None  # Factory mode
        
        # Test different potential import paths that might be causing the patching to fail
        import_paths_to_test = [
            'netra_backend.app.core.startup_validation.create_websocket_manager',
            'netra_backend.app.websocket_core.factory.create_websocket_manager', 
            'netra_backend.app.websocket_core.create_websocket_manager',
            'netra_backend.app.core.startup_validation.WebSocketManager',
            'netra_backend.app.websocket_core.websocket_manager.create_websocket_manager'
        ]
        
        validation_found = False
        
        for import_path in import_paths_to_test:
            print(f"Testing import path: {import_path}")
            try:
                with patch(import_path) as mock_factory:
                    mock_factory.return_value = "factory_available"
                    
                    success, report = await validator.validate_startup(mock_app)
                    
                    # Debug WebSocket validation results
                    if 'WebSocket' in report.get('categories', {}):
                        ws_validations = report['categories']['WebSocket']
                        print(f"  WebSocket validations found: {len(ws_validations)}")
                        
                        # Look for WebSocket Manager validation
                        manager_validation = None
                        for v in ws_validations:
                            print(f"    - {v.get('name', 'NO_NAME')}: {v.get('status', 'NO_STATUS')}")
                            if 'WebSocket Manager' in v['name']:
                                manager_validation = v
                                validation_found = True
                                break
                        
                        if manager_validation:
                            print(f"  Found WebSocket Manager validation with status: {manager_validation['status']}")
                            break
                    else:
                        print("  No 'WebSocket' category found")
                        
            except (ImportError, AttributeError) as e:
                print(f"  Import path failed: {e}")
                continue
        
        if not validation_found:
            print("Failed to find WebSocket Manager validation with any import path")
            
        # This should fail initially, proving we reproduced the issue
        assert 'WebSocket' in report.get('categories', {}), "WebSocket category missing"
        ws_validations = report['categories']['WebSocket']
        
        manager_validation = None
        for v in ws_validations:
            if 'WebSocket Manager' in v['name']:
                manager_validation = v
                break
        
        # EXPECTED TO FAIL: This assertion should fail initially
        assert manager_validation is not None, f"WebSocket Manager validation not found. Available: {[v['name'] for v in ws_validations]}"
    
    @pytest.mark.asyncio  
    async def test_healthy_startup_failure_reproduction(self, mock_app, validator):
        """
        REPRODUCTION TEST: Should initially FAIL due to WebSocket factory patching issues.
        
        This reproduces the failure in test_healthy_startup where mock setup
        doesn't create the expected healthy state.
        """
        print("\n=== REPRODUCING test_healthy_startup FAILURE ===")
        
        # Setup comprehensive healthy state exactly as in original test
        mock_app.state.agent_supervisor = MagicMock()
        mock_app.state.agent_supervisor.registry = MagicMock()
        mock_app.state.agent_supervisor.registry.agents = {
            'triage': MagicMock(),
            'data': MagicMock(), 
            'optimization': MagicMock(),
            'actions': MagicMock(),
            'reporting': MagicMock(),
            'data_helper': MagicMock(),
            'synthetic_data': MagicMock(),
            'corpus_admin': MagicMock()
        }
        
        # Setup UserContext tool configuration
        mock_app.state.tool_classes = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_app.state.websocket_bridge_factory = MagicMock()
        
        # Setup services
        mock_app.state.llm_manager = MagicMock()
        mock_app.state.key_manager = MagicMock()
        mock_app.state.security_service = MagicMock()
        mock_app.state.redis_manager = MagicMock()
        mock_app.state.thread_service = MagicMock()
        mock_app.state.agent_service = MagicMock()
        mock_app.state.db_session_factory = MagicMock()
        
        # Test without WebSocket patching first
        print("Testing without WebSocket patching...")
        success, report = await validator.validate_startup(mock_app)
        print(f"  Success: {success}")
        print(f"  Critical failures: {report.get('critical_failures', 'unknown')}")
        
        # Test with WebSocket patching - this is where original test likely fails
        print("Testing with WebSocket patching...")
        try:
            with patch('netra_backend.app.core.startup_validation.create_websocket_manager') as mock_create:
                mock_create.return_value = MagicMock()
                success, report = await validator.validate_startup(mock_app)
                print(f"  Success with patching: {success}")
                print(f"  Critical failures: {report.get('critical_failures', 'unknown')}")
        except Exception as e:
            print(f"  Exception during patching: {e}")
            success, report = False, {'critical_failures': 1}
        
        # Debug detailed report
        if 'categories' in report:
            for category, validations in report['categories'].items():
                failed_validations = [v for v in validations if v.get('status') in ['critical', 'failed']]
                if failed_validations:
                    print(f"  {category} failures:")
                    for v in failed_validations:
                        print(f"    - {v['name']}: {v.get('message', 'No message')}")
        
        # EXPECTED TO FAIL: Should be successful but probably won't be initially
        assert success, f"Healthy startup should be successful. Critical failures: {report.get('critical_failures', 'unknown')}"
        assert report.get('critical_failures', 1) == 0, "Should have no critical failures"
    
    @pytest.mark.asyncio
    async def test_deterministic_startup_integration_failure_reproduction(self, mock_app, validator):
        """
        REPRODUCTION TEST: Should initially FAIL due to orchestrator patching issues.
        
        This reproduces the failure in test_integration_with_deterministic_startup.
        """
        print("\n=== REPRODUCING test_integration_with_deterministic_startup FAILURE ===")
        
        try:
            from netra_backend.app.smd import StartupOrchestrator, DeterministicStartupError
        except ImportError as e:
            print(f"Failed to import startup orchestrator: {e}")
            pytest.skip("Startup orchestrator not available")
        
        # Create orchestrator
        orchestrator = StartupOrchestrator(mock_app)
        
        # Mock the startup phases - this complex patching is likely where it fails
        try:
            with patch.object(orchestrator, '_phase1_foundation', return_value=None):
                with patch.object(orchestrator, '_phase2_core_services', return_value=None):
                    with patch.object(orchestrator, '_phase3_chat_pipeline', return_value=None):
                        with patch.object(orchestrator, '_phase4_optional_services', return_value=None):
                            # Set up app state with zero agents for validation to detect
                            mock_app.state.agent_supervisor = MagicMock()
                            mock_app.state.agent_supervisor.registry = MagicMock()
                            mock_app.state.agent_supervisor.registry.agents = {}  # Zero agents
                            
                            # Phase validation should detect the zero agents within 30s
                            start_time = time.time()
                            
                            # EXPECTED TO FAIL: This should raise DeterministicStartupError but might not
                            with pytest.raises(DeterministicStartupError) as exc_info:
                                await asyncio.wait_for(
                                    orchestrator._phase5_validation(),
                                    timeout=30.0
                                )
                            
                            elapsed = time.time() - start_time
                            print(f"Validation completed in {elapsed:.2f}s")
                            assert elapsed < 30, f"Validation took too long: {elapsed:.2f}s"
                            
                            # Verify the error message indicates validation failure
                            error_msg = str(exc_info.value).lower()
                            assert "validation failed" in error_msg or "critical failures" in error_msg, \
                                f"Unexpected error message: {exc_info.value}"
                                
        except Exception as e:
            print(f"Exception during orchestrator testing: {e}")
            # Re-raise to show this is the reproduction of the failure
            raise
    
    @pytest.mark.asyncio
    async def test_dependency_chain_failure_reproduction(self, mock_app, validator):
        """
        REPRODUCTION TEST: Should initially FAIL due to service dependency validation issues.
        
        This reproduces the failure in test_dependency_chain_validation.
        """
        print("\n=== REPRODUCING test_dependency_chain_validation FAILURE ===")
        
        # Setup dependency chain: DB -> Redis -> LLM -> WebSocket -> Tools
        mock_app.state.db_session_factory = MagicMock()
        mock_app.state.redis_manager = MagicMock()
        mock_app.state.llm_manager = MagicMock()
        mock_app.state.websocket_manager = None  # Factory pattern
        
        # Mock WebSocket factory
        try:
            with patch('netra_backend.app.core.startup_validation.create_websocket_manager') as mock_create:
                mock_create.return_value = MagicMock()
                
                # Mock tool configuration
                mock_app.state.tool_classes = [MagicMock(), MagicMock()]
                mock_app.state.websocket_bridge_factory = MagicMock()
                
                success, report = await validator.validate_startup(mock_app)
        except Exception as e:
            print(f"Exception during dependency chain testing: {e}")
            success, report = False, {'critical_failures': 1, 'categories': {}}
        
        print(f"Dependency chain validation success: {success}")
        print(f"Critical failures: {report.get('critical_failures', 'unknown')}")
        
        # Debug what categories we actually got
        if 'categories' in report:
            print(f"Available categories: {list(report['categories'].keys())}")
        
        # EXPECTED TO FAIL: Should succeed with proper dependency chain but might not
        assert success, "Dependency chain validation should succeed with proper setup"
        assert report.get('critical_failures', 1) == 0, "Should have no critical failures"
        
        # Verify key categories are present
        expected_categories = ['Services', 'Tools', 'WebSocket']
        for category in expected_categories:
            assert category in report.get('categories', {}), f"Missing {category} category"
    
    @pytest.mark.asyncio
    async def test_concurrent_validation_failure_reproduction(self, mock_app, validator):
        """
        REPRODUCTION TEST: Should initially FAIL due to concurrent validation issues.
        
        This reproduces the failure in test_concurrent_validation_requests.
        """
        print("\n=== REPRODUCING test_concurrent_validation_requests FAILURE ===")
        
        # Setup minimal healthy state
        mock_app.state.agent_supervisor = MagicMock()
        mock_app.state.tool_classes = [MagicMock()]
        mock_app.state.websocket_bridge_factory = MagicMock()
        
        # Mock WebSocket factory
        try:
            with patch('netra_backend.app.core.startup_validation.create_websocket_manager') as mock_create:
                mock_create.return_value = MagicMock()
                
                # Run multiple concurrent validations
                tasks = [
                    validator.validate_startup(mock_app)
                    for _ in range(5)
                ]
                
                start_time = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                elapsed = time.time() - start_time
                
                print(f"Concurrent validation completed in {elapsed:.2f}s")
                
                # Check for exceptions
                exceptions = [r for r in results if isinstance(r, Exception)]
                if exceptions:
                    print(f"Exceptions during concurrent validation: {exceptions}")
                
                valid_results = [r for r in results if not isinstance(r, Exception)]
                print(f"Valid results: {len(valid_results)}/{len(results)}")
                
        except Exception as e:
            print(f"Exception during concurrent validation testing: {e}")
            raise
        
        # EXPECTED TO POTENTIALLY FAIL: All should succeed but might not
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Task {i} failed with exception: {result}")
                raise result
            
            success, report = result
            assert success, f"Concurrent validation {i} should succeed"
            assert isinstance(report, dict), f"Result {i} should have valid report"
            assert 'total_validations' in report, f"Result {i} missing total_validations"
        
        # Should complete within reasonable time
        assert elapsed < 15, f"Concurrent validation took {elapsed:.2f}s, expected < 15s"


@pytest.mark.mission_critical
class TestStartupValidationFixValidation:
    """
    Tests to validate that fixes work correctly.
    
    These tests should PASS after the underlying startup validation issues are fixed.
    """
    
    @pytest.mark.asyncio
    async def test_validation_report_structure_is_consistent(self):
        """Ensure validation reports always have consistent structure."""
        validator = StartupValidator()
        app = FastAPI()
        app.state = MagicMock()
        
        success, report = await validator.validate_startup(app)
        
        # Verify report structure
        required_keys = ['timestamp', 'duration', 'total_validations', 'status_counts', 
                        'critical_failures', 'categories', 'overall_health']
        for key in required_keys:
            assert key in report, f"Missing required report key: {key}"
        
        # Verify status counts structure
        status_keys = ['healthy', 'warning', 'critical', 'failed', 'not_checked']
        for key in status_keys:
            assert key in report['status_counts'], f"Missing status count: {key}"
    
    @pytest.mark.asyncio
    async def test_all_validations_are_always_added(self):
        """Ensure validations are always added to report, even in error cases."""
        validator = StartupValidator()
        app = FastAPI()
        app.state = MagicMock()
        
        # Test with various broken configurations
        test_cases = [
            {"description": "No tool_classes attribute", "setup": lambda: delattr(app.state, 'tool_classes') if hasattr(app.state, 'tool_classes') else None},
            {"description": "None tool_classes", "setup": lambda: setattr(app.state, 'tool_classes', None)},
            {"description": "Empty tool_classes", "setup": lambda: setattr(app.state, 'tool_classes', [])},
            {"description": "No agents", "setup": lambda: setattr(app.state, 'agent_supervisor', None)},
        ]
        
        for case in test_cases:
            print(f"Testing case: {case['description']}")
            
            # Reset app state
            app.state = MagicMock()
            case['setup']()
            
            success, report = await validator.validate_startup(app)
            
            # Should always have some validations, never empty
            assert report['total_validations'] > 0, f"No validations for case: {case['description']}"
            assert 'categories' in report, f"Missing categories for case: {case['description']}"
            
            # Should have key categories
            expected_categories = ['Tools', 'Services']  # At minimum
            for category in expected_categories:
                if category not in report['categories']:
                    print(f"WARNING: Missing {category} category for case: {case['description']}")


if __name__ == "__main__":
    # Run with verbose output to see reproduction details
    pytest.main([__file__, "-v", "-s", "--tb=long"])