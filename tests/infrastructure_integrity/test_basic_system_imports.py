"""
Infrastructure Integrity Tests - Basic System Imports

These tests are designed to FAIL if the basic infrastructure claims are false.
They test whether the system can actually perform basic operations without
Python path workarounds or infrastructure hacks.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Infrastructure Integrity
- Value Impact: Ensures basic system operations work without workarounds
- Strategic Impact: Protects $500K+ ARR by validating core infrastructure claims
"""

import pytest
import sys
import importlib
import logging
from pathlib import Path
from io import StringIO
from typing import List, Dict, Any


class TestBasicSystemImports:
    """Test that basic system imports work without workarounds."""
    
    def test_websocket_core_imports_without_pythonpath_workaround(self):
        """Test WebSocket core imports work without PYTHONPATH manipulation.
        
        This test WILL FAIL if the system requires Python path workarounds
        to import basic functionality, exposing infrastructure problems.
        
        Expected to FAIL initially - proves test is validating real infrastructure.
        """
        # Clear any existing imports to test fresh import capability
        modules_to_clear = [
            module for module in sys.modules.keys() 
            if 'netra_backend' in module or 'test_framework' in module
        ]
        
        # Store original PYTHONPATH to ensure clean test
        original_path = sys.path.copy()
        
        try:
            # Remove project-specific paths to test clean imports
            project_paths = [p for p in sys.path if 'netra-apex' in str(p)]
            for path in project_paths:
                if path in sys.path:
                    sys.path.remove(path)
            
            # Clear module cache
            for module in modules_to_clear:
                if module in sys.modules:
                    del sys.modules[module]
            
            # Attempt clean import without PYTHONPATH manipulation
            from netra_backend.app.websocket_core.manager import UnifiedWebSocketManager
            from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
            from netra_backend.app.routes.websocket import WebSocketRoute
            
            # If we get here, imports work without workarounds
            assert True, "WebSocket imports successful without PYTHONPATH workarounds"
            
        except ModuleNotFoundError as e:
            # EXPECTED FAILURE - this proves the test is validating real infrastructure
            pytest.fail(
                f"INFRASTRUCTURE BROKEN: WebSocket imports failed without PYTHONPATH workarounds. "
                f"Error: {e}. This proves system requires infrastructure hacks to function."
            )
        except ImportError as e:
            pytest.fail(
                f"INFRASTRUCTURE BROKEN: Import structure invalid. "
                f"Error: {e}. This indicates fundamental import system issues."
            )
        finally:
            # Restore original path
            sys.path = original_path
    
    def test_mission_critical_test_framework_accessible(self):
        """Test that mission critical test framework is accessible.
        
        This test WILL FAIL if test_framework imports require workarounds.
        This validates that testing infrastructure itself is functional.
        
        Expected to FAIL initially - proves test infrastructure claims are false.
        """
        try:
            from test_framework.websocket_helpers import WebSocketTestHelpers
            from test_framework.base_integration_test import BaseIntegrationTest
            from test_framework.real_services_test_fixtures import real_services_fixture
            
            # Test that classes are actually instantiable
            helpers = WebSocketTestHelpers()
            assert helpers is not None, "WebSocket test helpers should be instantiable"
            
            # Test framework should be ready for use
            assert hasattr(helpers, 'create_websocket_connection'), \
                "Test framework missing core functionality"
                
        except ModuleNotFoundError as e:
            # EXPECTED FAILURE - exposes test infrastructure issues
            pytest.fail(
                f"TEST INFRASTRUCTURE BROKEN: Test framework inaccessible without workarounds. "
                f"Error: {e}. This proves test infrastructure claims are false."
            )
        except AttributeError as e:
            pytest.fail(
                f"TEST INFRASTRUCTURE INCOMPLETE: Test framework missing expected functionality. "
                f"Error: {e}. This indicates partial or broken test infrastructure."
            )
    
    def test_ssot_compliance_imports_functional(self):
        """Test SSOT compliance imports work correctly.
        
        This test WILL FAIL if SSOT warnings indicate real infrastructure issues.
        Captures and validates that SSOT compliance is genuine, not just documented.
        
        Expected to FAIL initially - exposes false SSOT compliance claims.
        """
        # Setup log capture to detect SSOT warnings
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger()
        logger.addHandler(handler)
        original_level = logger.level
        logger.setLevel(logging.WARNING)
        
        ssot_warnings = []
        
        try:
            # Import SSOT-critical modules and capture warnings
            from netra_backend.app.websocket_core import manager
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            
            log_output = log_capture.getvalue()
            
            # Check for SSOT violations
            if "SSOT WARNING" in log_output:
                ssot_warnings.append("SSOT WARNING detected")
            if "WARNING" in log_output and "SSOT" in log_output:
                ssot_warnings.append("SSOT-related warnings found")
            if "violation" in log_output.lower():
                ssot_warnings.append("SSOT violations detected")
            
            # Check for import instability indicators
            if "fallback" in log_output.lower():
                ssot_warnings.append("Import fallback patterns detected")
            if "deprecated" in log_output.lower():
                ssot_warnings.append("Deprecated import patterns in use")
            
            # If warnings detected, SSOT compliance is false
            if ssot_warnings:
                pytest.fail(
                    f"SSOT COMPLIANCE FALSE: SSOT warnings detected during imports. "
                    f"Warnings: {ssot_warnings}. "
                    f"Full log: {log_output}. "
                    f"This proves SSOT compliance claims are inaccurate."
                )
            
            # Additional validation: check for singleton patterns (SSOT violation)
            manager_instance1 = manager.get_unified_websocket_manager()
            manager_instance2 = manager.get_unified_websocket_manager()
            
            if manager_instance1 is manager_instance2:
                pytest.fail(
                    f"SSOT VIOLATION: Singleton pattern detected in WebSocket manager. "
                    f"This violates factory pattern requirements and user isolation."
                )
            
        except Exception as e:
            pytest.fail(
                f"SSOT INFRASTRUCTURE BROKEN: Failed to validate SSOT compliance. "
                f"Error: {e}. This indicates SSOT implementation is non-functional."
            )
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)
    
    def test_core_service_imports_without_errors(self):
        """Test core service imports work without errors or warnings.
        
        This test validates that core services can be imported and instantiated
        without errors, warnings, or configuration issues.
        
        Expected to FAIL initially - exposes service import instability.
        """
        import warnings
        
        # Capture warnings during imports
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            
            try:
                # Import core services
                from netra_backend.app.core.configuration.base import ConfigurationManager
                from netra_backend.app.db.database_manager import DatabaseManager
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                from netra_backend.app.agents.registry import AgentRegistry
                
                # Test basic instantiation
                config_manager = ConfigurationManager()
                assert config_manager is not None, "Configuration manager should be instantiable"
                
                db_manager = DatabaseManager()
                assert db_manager is not None, "Database manager should be instantiable"
                
                agent_registry = AgentRegistry()
                assert agent_registry is not None, "Agent registry should be instantiable"
                
                # Check for import warnings
                import_warnings = [w for w in warning_list if 'import' in str(w.message).lower()]
                deprecation_warnings = [w for w in warning_list if 'deprecat' in str(w.message).lower()]
                
                if import_warnings:
                    pytest.fail(
                        f"IMPORT INSTABILITY: Import warnings detected. "
                        f"Warnings: {[str(w.message) for w in import_warnings]}. "
                        f"This indicates unstable import infrastructure."
                    )
                
                if deprecation_warnings:
                    pytest.fail(
                        f"DEPRECATED IMPORTS: Deprecated import patterns in use. "
                        f"Warnings: {[str(w.message) for w in deprecation_warnings]}. "
                        f"This indicates technical debt affecting stability."
                    )
                
            except Exception as e:
                pytest.fail(
                    f"CORE SERVICE IMPORTS BROKEN: Core services cannot be imported or instantiated. "
                    f"Error: {e}. This proves core infrastructure is non-functional."
                )
    
    def test_agent_execution_imports_without_dependency_errors(self):
        """Test agent execution pipeline imports work without dependency errors.
        
        This test validates the agent execution pipeline can be imported and
        basic components created without missing dependencies or circular imports.
        
        Expected to FAIL initially - exposes agent infrastructure issues.
        """
        try:
            # Import agent execution pipeline components
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor
            from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
            
            # Test execution engine creation
            execution_engine = ExecutionEngine()
            assert execution_engine is not None, "Execution engine should be creatable"
            
            # Test that essential methods exist
            required_methods = ['execute_agent', 'create_agent_context']
            for method_name in required_methods:
                assert hasattr(execution_engine, method_name), \
                    f"Execution engine missing required method: {method_name}"
            
            # Test pipeline executor creation with minimal dependencies
            from unittest.mock import Mock
            mock_engine = Mock()
            mock_websocket = Mock()
            mock_context = Mock()
            
            pipeline_executor = PipelineExecutor(
                engine=mock_engine,
                websocket_manager=mock_websocket,
                user_context=mock_context
            )
            assert pipeline_executor is not None, "Pipeline executor should be creatable"
            
        except ImportError as e:
            pytest.fail(
                f"AGENT INFRASTRUCTURE BROKEN: Agent execution imports failed. "
                f"Error: {e}. This proves agent infrastructure claims are false."
            )
        except Exception as e:
            pytest.fail(
                f"AGENT EXECUTION SETUP BROKEN: Agent components cannot be instantiated. "
                f"Error: {e}. This indicates agent execution infrastructure is broken."
            )


class TestDocumentationVsRealityGaps:
    """Test that documentation claims match actual system capabilities."""
    
    def test_mission_critical_test_decorators_not_disabled(self):
        """Test that mission critical tests don't have disabled decorators.
        
        This test WILL FAIL if mission critical tests have been systematically
        disabled to maintain false green CI status.
        
        Expected to FAIL initially - exposes systematic test disabling.
        """
        import ast
        from pathlib import Path
        
        # Find mission critical test files
        test_dirs = [
            Path("tests/mission_critical"),
            Path("netra_backend/tests/critical"),
            Path("tests/e2e")
        ]
        
        disabled_decorators = []
        
        for test_dir in test_dirs:
            if test_dir.exists():
                for test_file in test_dir.rglob("*.py"):
                    try:
                        with open(test_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Check for commented out decorators
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            line_stripped = line.strip()
                            
                            # Look for commented require_docker_services decorators
                            if (line_stripped.startswith('# @require_docker_services') or
                                line_stripped.startswith('#@require_docker_services')):
                                disabled_decorators.append({
                                    'file': str(test_file),
                                    'line': i + 1,
                                    'content': line_stripped
                                })
                            
                            # Look for temporarily disabled patterns
                            if ('temporarily disabled' in line.lower() and 
                                '@' in line and '#' in line):
                                disabled_decorators.append({
                                    'file': str(test_file),
                                    'line': i + 1,
                                    'content': line_stripped
                                })
                    
                    except Exception:
                        continue  # Skip files that can't be read
        
        # If disabled decorators found, test infrastructure is compromised
        if disabled_decorators:
            disabled_summary = '\n'.join([
                f"  {item['file']}:{item['line']} - {item['content']}"
                for item in disabled_decorators[:10]  # Show first 10
            ])
            
            pytest.fail(
                f"TEST INFRASTRUCTURE COMPROMISED: {len(disabled_decorators)} disabled test decorators found. "
                f"This proves mission critical tests have been systematically disabled to maintain false green CI status.\n"
                f"Examples:\n{disabled_summary}\n"
                f"Total violations: {len(disabled_decorators)}"
            )
    
    def test_health_status_claims_match_reality(self):
        """Test that health status claims match actual system health.
        
        This test attempts to validate the "99% system health" claim by testing
        basic system operations.
        
        Expected to FAIL initially - exposes false health claims.
        """
        health_checks = []
        
        # Test 1: WebSocket system health
        try:
            from netra_backend.app.websocket_core.manager import UnifiedWebSocketManager
            manager = UnifiedWebSocketManager()
            health_checks.append(("WebSocket Manager Creation", True))
        except Exception as e:
            health_checks.append(("WebSocket Manager Creation", False, str(e)))
        
        # Test 2: Database configuration health
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            health_checks.append(("Database Manager Creation", True))
        except Exception as e:
            health_checks.append(("Database Manager Creation", False, str(e)))
        
        # Test 3: Agent system health
        try:
            from netra_backend.app.agents.registry import AgentRegistry
            registry = AgentRegistry()
            health_checks.append(("Agent Registry Creation", True))
        except Exception as e:
            health_checks.append(("Agent Registry Creation", False, str(e)))
        
        # Test 4: Configuration system health
        try:
            from netra_backend.app.core.configuration.base import ConfigurationManager
            config = ConfigurationManager()
            health_checks.append(("Configuration Manager Creation", True))
        except Exception as e:
            health_checks.append(("Configuration Manager Creation", False, str(e)))
        
        # Calculate actual health percentage
        successful_checks = sum(1 for check in health_checks if len(check) == 2 and check[1])
        total_checks = len(health_checks)
        actual_health_percentage = (successful_checks / total_checks) * 100
        
        # Test against claimed 99% health
        claimed_health = 99.0
        
        if actual_health_percentage < claimed_health:
            failed_checks = [
                f"{check[0]}: {check[2] if len(check) > 2 else 'Failed'}"
                for check in health_checks if len(check) > 2 or not check[1]
            ]
            
            pytest.fail(
                f"HEALTH CLAIMS FALSE: Actual health {actual_health_percentage:.1f}% vs claimed {claimed_health}%. "
                f"Failed checks ({len(failed_checks)}/{total_checks}): {failed_checks}. "
                f"This proves '99% system health' claims are inaccurate."
            )


if __name__ == "__main__":
    # Run infrastructure integrity tests
    pytest.main([__file__, "-v", "--tb=short", "--no-docker"])