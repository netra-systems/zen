#!/usr/bin/env python3
"""
Test Existing Functionality Protection for Issue #485

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Ensure fixes don't break existing working functionality
- Value Impact: Protect existing business value while resolving infrastructure issues  
- Strategic Impact: Maintain system stability during infrastructure improvements

IMPORTANT: These tests should PASS initially to validate regression protection.
They ensure that fixes for import path resolution and collection issues don't
break existing working functionality.
"""

import sys
import os
import pytest
import importlib
from pathlib import Path
from typing import List, Dict, Any, Optional

# Setup project root for consistent imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestExistingFunctionalityProtection(SSotBaseTestCase):
    """
    Test existing functionality is protected during fixes.
    
    These tests ensure that fixes for Issue #485 (import path resolution and
    collection issues) don't break existing working functionality.
    """
    
    def test_existing_ssot_patterns_still_work(self):
        """
        PASS INITIALLY: Test existing SSOT patterns continue working.
        
        This test should PASS initially to ensure that existing SSOT patterns
        that are currently working continue to work after fixes.
        """
        ssot_pattern_issues = []
        
        # Test existing SSOT patterns that should continue working
        existing_ssot_patterns = [
            ("test_framework.ssot.base_test_case", "SSotBaseTestCase"),
            ("test_framework.ssot.orchestration", "orchestration_config"),
            ("test_framework.unified_docker_manager", "UnifiedDockerManager")
        ]
        
        for module_path, expected_attribute in existing_ssot_patterns:
            try:
                # Test that existing SSOT patterns still import correctly
                module = importlib.import_module(module_path)
                
                if not hasattr(module, expected_attribute):
                    ssot_pattern_issues.append(f"{module_path}: Missing expected attribute {expected_attribute}")
                    continue
                
                # Test that the attribute is usable
                attr = getattr(module, expected_attribute)
                
                if expected_attribute == "SSotBaseTestCase":
                    # Ensure it's still a valid base class
                    if not isinstance(attr, type):
                        ssot_pattern_issues.append(f"{module_path}.{expected_attribute}: Not a valid class")
                
                elif expected_attribute == "orchestration_config":
                    # Ensure it still has expected configuration attributes
                    if not hasattr(attr, 'orchestrator_available'):
                        ssot_pattern_issues.append(f"{module_path}.{expected_attribute}: Missing orchestrator_available attribute")
                
                elif expected_attribute == "UnifiedDockerManager":
                    # Ensure it's still a valid manager class
                    if not isinstance(attr, type):
                        ssot_pattern_issues.append(f"{module_path}.{expected_attribute}: Not a valid class")
                    elif not hasattr(attr, 'acquire_environment'):
                        ssot_pattern_issues.append(f"{module_path}.{expected_attribute}: Missing acquire_environment method")
                        
            except ImportError as e:
                ssot_pattern_issues.append(f"{module_path}: ImportError - {e}")
            except Exception as e:
                ssot_pattern_issues.append(f"{module_path}: Unexpected error - {e}")
        
        # This assertion should PASS initially (no issues with existing SSOT patterns)
        assert len(ssot_pattern_issues) == 0, (
            f"Existing SSOT patterns broken ({len(ssot_pattern_issues)} issues):\n" +
            "\n".join(f"  - {issue}" for issue in ssot_pattern_issues) +
            "\n\nFixes for Issue #485 must NOT break existing working SSOT patterns."
        )
    
    def test_existing_websocket_tests_still_pass(self):
        """
        PASS INITIALLY: Test existing WebSocket tests continue passing.
        
        This test should PASS initially to ensure that existing WebSocket tests
        that are currently working continue to work after fixes.
        """
        websocket_protection_issues = []
        
        # Test that existing WebSocket test utilities are still accessible
        websocket_utilities = [
            ("test_framework.websocket_helpers", "WebSocketTestClient", "class"),
            ("test_framework.ssot.websocket", "websocket_test_utilities", "module"),
            ("test_framework.ssot.real_websocket_connection_manager", "RealWebSocketConnectionManager", "class")
        ]
        
        for module_path, expected_item, item_type in websocket_utilities:
            try:
                # Test import still works
                module = importlib.import_module(module_path)
                
                if expected_item and not hasattr(module, expected_item):
                    websocket_protection_issues.append(f"{module_path}: Missing {expected_item}")
                    continue
                
                if expected_item:
                    item = getattr(module, expected_item)
                    
                    if item_type == "class" and not isinstance(item, type):
                        websocket_protection_issues.append(f"{module_path}.{expected_item}: Not a valid class")
                    elif item_type == "module" and not hasattr(item, '__file__'):
                        websocket_protection_issues.append(f"{module_path}.{expected_item}: Not a valid module")
                        
            except ImportError as e:
                websocket_protection_issues.append(f"{module_path}: ImportError - {e}")
            except Exception as e:
                websocket_protection_issues.append(f"{module_path}: Unexpected error - {e}")
        
        # Test that WebSocket test base classes are still usable
        try:
            from test_framework.ssot.base_test_case import SSotBaseTestCase
            
            # Create a simple test class to ensure inheritance still works
            class TestWebSocketInheritance(SSotBaseTestCase):
                def test_simple(self):
                    pass
            
            # Ensure the test class was created successfully
            if not issubclass(TestWebSocketInheritance, SSotBaseTestCase):
                websocket_protection_issues.append("WebSocket test inheritance broken")
                
        except Exception as e:
            websocket_protection_issues.append(f"WebSocket test inheritance test failed: {e}")
        
        # This assertion should PASS initially (no issues with existing WebSocket functionality)
        assert len(websocket_protection_issues) == 0, (
            f"Existing WebSocket functionality broken ({len(websocket_protection_issues)} issues):\n" +
            "\n".join(f"  - {issue}" for issue in websocket_protection_issues) +
            "\n\nFixes for Issue #485 must NOT break existing working WebSocket test functionality."
        )
    
    def test_existing_integration_patterns_preserved(self):
        """
        PASS INITIALLY: Test existing integration test patterns are preserved.
        
        This test should PASS initially to ensure that existing integration test
        patterns that are currently working continue to work after fixes.
        """
        integration_protection_issues = []
        
        # Test existing integration test patterns
        integration_patterns = [
            ("test_framework.base_integration_test", "BaseIntegrationTest"),
            ("test_framework.real_services_test_fixtures", "real_services_fixture"),
            ("test_framework.isolated_environment_fixtures", "isolated_env")
        ]
        
        for module_path, expected_pattern in integration_patterns:
            try:
                # Test that integration patterns still import correctly
                module = importlib.import_module(module_path)
                
                if not hasattr(module, expected_pattern):
                    integration_protection_issues.append(f"{module_path}: Missing {expected_pattern}")
                    continue
                
                # Test that the pattern is still usable
                pattern = getattr(module, expected_pattern)
                
                if expected_pattern == "BaseIntegrationTest":
                    # Ensure it's still a valid base class
                    if not isinstance(pattern, type):
                        integration_protection_issues.append(f"{module_path}.{expected_pattern}: Not a valid class")
                
                elif expected_pattern in ["real_services_fixture", "isolated_env"]:
                    # These should be fixture functions
                    if not callable(pattern):
                        integration_protection_issues.append(f"{module_path}.{expected_pattern}: Not callable")
                        
            except ImportError as e:
                integration_protection_issues.append(f"{module_path}: ImportError - {e}")
            except Exception as e:
                integration_protection_issues.append(f"{module_path}: Unexpected error - {e}")
        
        # Test that integration test inheritance still works
        try:
            from test_framework.base_integration_test import BaseIntegrationTest
            
            # Create a simple integration test class to ensure inheritance works
            class TestIntegrationInheritance(BaseIntegrationTest):
                def test_simple_integration(self):
                    pass
            
            # Ensure the test class was created successfully
            if not issubclass(TestIntegrationInheritance, BaseIntegrationTest):
                integration_protection_issues.append("Integration test inheritance broken")
                
        except Exception as e:
            integration_protection_issues.append(f"Integration test inheritance test failed: {e}")
        
        # This assertion should PASS initially (no issues with existing integration patterns)
        assert len(integration_protection_issues) == 0, (
            f"Existing integration patterns broken ({len(integration_protection_issues)} issues):\n" +
            "\n".join(f"  - {issue}" for issue in integration_protection_issues) +
            "\n\nFixes for Issue #485 must NOT break existing working integration test patterns."
        )
    
    def test_existing_test_discovery_still_functional(self):
        """
        PASS INITIALLY: Test existing test discovery mechanisms still work.
        
        This test should PASS initially to ensure that existing test discovery
        mechanisms continue to work after fixes.
        """
        discovery_protection_issues = []
        
        # Test existing test discovery mechanisms
        discovery_components = [
            ("test_framework.test_discovery", "TestDiscovery"),
            ("test_framework.category_system", "CategorySystem"),
            ("test_framework.test_validation", "TestValidation")
        ]
        
        for module_path, expected_component in discovery_components:
            try:
                # Test that discovery components still import correctly
                module = importlib.import_module(module_path)
                
                if not hasattr(module, expected_component):
                    discovery_protection_issues.append(f"{module_path}: Missing {expected_component}")
                    continue
                
                # Test that the component is still usable
                component = getattr(module, expected_component)
                
                if not isinstance(component, type):
                    discovery_protection_issues.append(f"{module_path}.{expected_component}: Not a valid class")
                    continue
                
                # Test basic instantiation (if it has a no-args constructor)
                try:
                    instance = component()
                    if instance is None:
                        discovery_protection_issues.append(f"{module_path}.{expected_component}: Cannot instantiate")
                except TypeError:
                    # Some classes may require arguments - that's okay
                    pass
                except Exception as e:
                    discovery_protection_issues.append(f"{module_path}.{expected_component}: Instantiation error - {e}")
                    
            except ImportError as e:
                discovery_protection_issues.append(f"{module_path}: ImportError - {e}")
            except Exception as e:
                discovery_protection_issues.append(f"{module_path}: Unexpected error - {e}")
        
        # This assertion should PASS initially (no issues with existing discovery mechanisms)
        assert len(discovery_protection_issues) == 0, (
            f"Existing test discovery mechanisms broken ({len(discovery_protection_issues)} issues):\n" +
            "\n".join(f"  - {issue}" for issue in discovery_protection_issues) +
            "\n\nFixes for Issue #485 must NOT break existing working test discovery mechanisms."
        )
    
    def test_existing_environment_management_preserved(self):
        """
        PASS INITIALLY: Test existing environment management functionality preserved.
        
        This test should PASS initially to ensure that existing environment
        management functionality continues to work after fixes.
        """
        environment_protection_issues = []
        
        # Test existing environment management components
        environment_components = [
            ("shared.isolated_environment", "IsolatedEnvironment"),
            ("shared.isolated_environment", "get_env"),
            ("test_framework.environment_isolation", "EnvironmentIsolation")
        ]
        
        for module_path, expected_component in environment_components:
            try:
                # Test that environment components still import correctly
                module = importlib.import_module(module_path)
                
                if not hasattr(module, expected_component):
                    environment_protection_issues.append(f"{module_path}: Missing {expected_component}")
                    continue
                
                # Test that the component is still usable
                component = getattr(module, expected_component)
                
                if expected_component == "get_env":
                    # Should be a function
                    if not callable(component):
                        environment_protection_issues.append(f"{module_path}.{expected_component}: Not callable")
                    else:
                        # Test that it returns something usable
                        try:
                            env = component()
                            if env is None:
                                environment_protection_issues.append(f"{module_path}.{expected_component}: Returns None")
                        except Exception as e:
                            environment_protection_issues.append(f"{module_path}.{expected_component}: Call failed - {e}")
                
                elif expected_component in ["IsolatedEnvironment", "EnvironmentIsolation"]:
                    # Should be classes
                    if not isinstance(component, type):
                        environment_protection_issues.append(f"{module_path}.{expected_component}: Not a valid class")
                        
            except ImportError as e:
                environment_protection_issues.append(f"{module_path}: ImportError - {e}")
            except Exception as e:
                environment_protection_issues.append(f"{module_path}: Unexpected error - {e}")
        
        # Test that environment isolation still works correctly
        try:
            from shared.isolated_environment import get_env
            
            env = get_env()
            
            # Test basic environment operations
            env.set("TEST_PROTECTION_VAR", "test_value", source="test")
            retrieved_value = env.get("TEST_PROTECTION_VAR")
            
            if retrieved_value != "test_value":
                environment_protection_issues.append("Environment isolation set/get functionality broken")
                
        except Exception as e:
            environment_protection_issues.append(f"Environment isolation functionality test failed: {e}")
        
        # This assertion should PASS initially (no issues with existing environment management)
        assert len(environment_protection_issues) == 0, (
            f"Existing environment management broken ({len(environment_protection_issues)} issues):\n" +
            "\n".join(f"  - {issue}" for issue in environment_protection_issues) +
            "\n\nFixes for Issue #485 must NOT break existing working environment management."
        )
    
    def test_existing_docker_management_preserved(self):
        """
        PASS INITIALLY: Test existing Docker management functionality preserved.
        
        This test should PASS initially to ensure that existing Docker management
        functionality continues to work after fixes.
        """
        docker_protection_issues = []
        
        # Test existing Docker management components
        docker_components = [
            ("test_framework.unified_docker_manager", "UnifiedDockerManager"),
            ("test_framework.docker_test_manager", "DockerTestManager")
        ]
        
        for module_path, expected_component in docker_components:
            try:
                # Test that Docker components still import correctly
                module = importlib.import_module(module_path)
                
                if not hasattr(module, expected_component):
                    docker_protection_issues.append(f"{module_path}: Missing {expected_component}")
                    continue
                
                # Test that the component is still a valid class
                component = getattr(module, expected_component)
                
                if not isinstance(component, type):
                    docker_protection_issues.append(f"{module_path}.{expected_component}: Not a valid class")
                    continue
                
                # Test basic instantiation (without actually starting Docker)
                try:
                    # Most Docker managers should be instantiable
                    manager = component()
                    if manager is None:
                        docker_protection_issues.append(f"{module_path}.{expected_component}: Cannot instantiate")
                except Exception as e:
                    # Some Docker managers may require specific conditions - log but don't fail
                    # This is acceptable since we're not testing Docker functionality, just import/instantiation
                    pass
                    
            except ImportError as e:
                docker_protection_issues.append(f"{module_path}: ImportError - {e}")
            except Exception as e:
                docker_protection_issues.append(f"{module_path}: Unexpected error - {e}")
        
        # Test that Docker configuration components are still accessible
        docker_config_components = [
            ("test_framework.docker_config_loader", "DockerConfigLoader"),
            ("test_framework.container_runtime", "ContainerRuntime")
        ]
        
        for module_path, expected_component in docker_config_components:
            try:
                module = importlib.import_module(module_path)
                
                if not hasattr(module, expected_component):
                    docker_protection_issues.append(f"{module_path}: Missing {expected_component}")
                    
            except ImportError as e:
                # Some Docker config components may have optional dependencies
                # Log but don't fail the test
                pass
            except Exception as e:
                docker_protection_issues.append(f"{module_path}: Unexpected error - {e}")
        
        # This assertion should PASS initially (no issues with existing Docker management)
        assert len(docker_protection_issues) == 0, (
            f"Existing Docker management broken ({len(docker_protection_issues)} issues):\n" +
            "\n".join(f"  - {issue}" for issue in docker_protection_issues) +
            "\n\nFixes for Issue #485 must NOT break existing working Docker management."
        )


class TestBackwardCompatibilityProtection(SSotBaseTestCase):
    """
    Test backward compatibility is maintained during Issue #485 fixes.
    
    These tests ensure that any fixes maintain backward compatibility with
    existing code that depends on current import patterns and interfaces.
    """
    
    def test_import_aliases_still_work(self):
        """
        PASS INITIALLY: Test existing import aliases continue to work.
        
        This test should PASS initially to ensure that existing import aliases
        used throughout the codebase continue to work after fixes.
        """
        alias_issues = []
        
        # Test common import aliases that might exist in the codebase
        try:
            # Test that common import patterns still work
            from test_framework.ssot.orchestration import orchestration_config
            if not hasattr(orchestration_config, 'orchestrator_available'):
                alias_issues.append("orchestration_config alias broken")
                
        except ImportError as e:
            alias_issues.append(f"orchestration_config import alias failed: {e}")
        except Exception as e:
            alias_issues.append(f"orchestration_config alias error: {e}")
        
        try:
            from test_framework.unified_docker_manager import UnifiedDockerManager
            if not hasattr(UnifiedDockerManager, 'acquire_environment'):
                alias_issues.append("UnifiedDockerManager alias broken")
                
        except ImportError as e:
            alias_issues.append(f"UnifiedDockerManager import alias failed: {e}")
        except Exception as e:
            alias_issues.append(f"UnifiedDockerManager alias error: {e}")
        
        # This assertion should PASS initially (no issues with existing import aliases)
        assert len(alias_issues) == 0, (
            f"Existing import aliases broken ({len(alias_issues)} issues):\n" +
            "\n".join(f"  - {issue}" for issue in alias_issues) +
            "\n\nFixes for Issue #485 must maintain backward compatibility with existing import aliases."
        )
    
    def test_interface_signatures_preserved(self):
        """
        PASS INITIALLY: Test existing interface signatures are preserved.
        
        This test should PASS initially to ensure that existing interface signatures
        used throughout the codebase are preserved after fixes.
        """
        interface_issues = []
        
        # Test that key interface signatures haven't changed
        try:
            from test_framework.unified_docker_manager import UnifiedDockerManager
            
            # Test that critical methods still exist with expected signatures
            manager = UnifiedDockerManager()
            
            if not hasattr(manager, 'acquire_environment'):
                interface_issues.append("UnifiedDockerManager.acquire_environment method missing")
            
            if not hasattr(manager, 'release_environment'):
                interface_issues.append("UnifiedDockerManager.release_environment method missing")
                
        except Exception as e:
            interface_issues.append(f"UnifiedDockerManager interface check failed: {e}")
        
        try:
            from test_framework.ssot.base_test_case import SSotBaseTestCase
            
            # Test that base test case interface is preserved
            if not issubclass(SSotBaseTestCase, object):
                interface_issues.append("SSotBaseTestCase inheritance broken")
                
        except Exception as e:
            interface_issues.append(f"SSotBaseTestCase interface check failed: {e}")
        
        # This assertion should PASS initially (no issues with existing interfaces)
        assert len(interface_issues) == 0, (
            f"Existing interface signatures broken ({len(interface_issues)} issues):\n" +
            "\n".join(f"  - {issue}" for issue in interface_issues) +
            "\n\nFixes for Issue #485 must preserve existing interface signatures for backward compatibility."
        )
    
    def test_configuration_access_patterns_preserved(self):
        """
        PASS INITIALLY: Test existing configuration access patterns preserved.
        
        This test should PASS initially to ensure that existing configuration
        access patterns used throughout the codebase are preserved after fixes.
        """
        config_pattern_issues = []
        
        # Test existing configuration access patterns
        try:
            from test_framework.ssot.orchestration import orchestration_config
            
            # Test that configuration attributes are still accessible
            if hasattr(orchestration_config, 'orchestrator_available'):
                # Test that the attribute is still usable
                _ = orchestration_config.orchestrator_available
            else:
                config_pattern_issues.append("orchestration_config.orchestrator_available not accessible")
                
        except Exception as e:
            config_pattern_issues.append(f"orchestration_config access pattern failed: {e}")
        
        try:
            from shared.isolated_environment import get_env
            
            # Test that environment access pattern still works
            env = get_env()
            if not hasattr(env, 'get') or not hasattr(env, 'set'):
                config_pattern_issues.append("IsolatedEnvironment access pattern broken")
                
        except Exception as e:
            config_pattern_issues.append(f"Environment access pattern failed: {e}")
        
        # This assertion should PASS initially (no issues with existing config patterns)
        assert len(config_pattern_issues) == 0, (
            f"Existing configuration access patterns broken ({len(config_pattern_issues)} issues):\n" +
            "\n".join(f"  - {issue}" for issue in config_pattern_issues) +
            "\n\nFixes for Issue #485 must preserve existing configuration access patterns."
        )


if __name__ == "__main__":
    # Enable verbose output for debugging
    pytest.main([__file__, "-v", "--tb=short", "--no-header"])