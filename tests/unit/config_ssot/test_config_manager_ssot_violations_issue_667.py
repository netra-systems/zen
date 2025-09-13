"""
UNIT TEST: Configuration Manager SSOT Violations Detection - Issue #667

Business Value Justification (BVJ):
- Segment: Platform/Internal - Developer Experience  
- Business Goal: Detect and prevent configuration SSOT violations that affect Golden Path authentication
- Value Impact: Prevents authentication failures and protects $500K+ ARR from configuration conflicts
- Strategic Impact: Ensures single source of truth for configuration management

CRITICAL DETECTION TESTS:
This test suite is designed to FAIL initially to prove the existence of 3 configuration managers
with conflicting method signatures that affect Golden Path authentication flow.

Expected Failures (proving violations exist):
1. Multiple configuration manager classes detected
2. Conflicting method signatures between managers
3. Import path inconsistencies affecting authentication

These failures prove Issue #667 violations exist and require SSOT consolidation.
"""

import unittest
import importlib
import inspect
from typing import Dict, List, Set, Tuple, Any
from pathlib import Path
import sys

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestConfigManagerSSOTViolationsIssue667(SSotBaseTestCase, unittest.TestCase):
    """Unit tests to detect configuration manager SSOT violations for Issue #667."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.detected_managers = []
        self.violation_details = {}
    
    def test_multiple_configuration_manager_classes_exist(self):
        """
        CRITICAL TEST: Detect multiple configuration manager classes (SHOULD FAIL INITIALLY).
        
        This test is designed to FAIL to prove Issue #667 violations exist.
        Detects the 3 configuration managers with conflicting interfaces.
        """
        # Known configuration manager classes from investigation
        manager_classes = [
            {
                'name': 'UnifiedConfigManager',
                'path': 'netra_backend.app.core.configuration.base',
                'class_name': 'UnifiedConfigManager'
            },
            {
                'name': 'ConfigManager (config.py)',
                'path': 'netra_backend.app.config',
                'function_name': 'get_config'  # Main interface function
            },
            {
                'name': 'UnifiedConfigurationManager',
                'path': 'netra_backend.app.core.managers.unified_configuration_manager',
                'class_name': 'UnifiedConfigurationManager'
            }
        ]
        
        detected_managers = []
        import_failures = []
        
        for manager_info in manager_classes:
            try:
                module = importlib.import_module(manager_info['path'])
                
                if 'class_name' in manager_info:
                    if hasattr(module, manager_info['class_name']):
                        class_obj = getattr(module, manager_info['class_name'])
                        detected_managers.append({
                            'name': manager_info['name'],
                            'path': manager_info['path'],
                            'class': class_obj,
                            'type': 'class'
                        })
                
                if 'function_name' in manager_info:
                    if hasattr(module, manager_info['function_name']):
                        func_obj = getattr(module, manager_info['function_name'])
                        detected_managers.append({
                            'name': manager_info['name'],
                            'path': manager_info['path'],
                            'function': func_obj,
                            'type': 'function'
                        })
                        
            except ImportError as e:
                import_failures.append({
                    'manager': manager_info['name'],
                    'path': manager_info['path'],
                    'error': str(e)
                })
        
        self.detected_managers = detected_managers
        
        # Store detailed violation information
        self.violation_details['multiple_managers'] = {
            'detected_count': len(detected_managers),
            'detected_managers': [m['name'] for m in detected_managers],
            'import_failures': import_failures
        }
        
        # EXPECTED FAILURE: This should fail to prove violations exist
        self.assertEqual(
            len(detected_managers), 1,
            f"SSOT VIOLATION DETECTED: Found {len(detected_managers)} configuration managers instead of 1. "
            f"Detected: {[m['name'] for m in detected_managers]}. "
            f"This proves Issue #667 violations exist and require consolidation. "
            f"Import failures: {import_failures}"
        )
    
    def test_configuration_method_signature_conflicts(self):
        """
        CRITICAL TEST: Detect conflicting method signatures (SHOULD FAIL INITIALLY).
        
        Tests the 3 configuration managers have different method signatures
        that affect Golden Path authentication.
        """
        if not self.detected_managers:
            self.test_multiple_configuration_manager_classes_exist()
        
        method_signatures = {}
        signature_conflicts = []
        
        # Analyze method signatures for each detected manager
        for manager in self.detected_managers:
            if manager['type'] == 'class':
                class_obj = manager['class']
                methods = {}
                
                # Check key methods that affect authentication
                key_methods = ['get_config', 'get', 'validate_config_integrity', '__init__']
                
                for method_name in key_methods:
                    if hasattr(class_obj, method_name):
                        method = getattr(class_obj, method_name)
                        if callable(method):
                            try:
                                signature = inspect.signature(method)
                                methods[method_name] = {
                                    'signature': str(signature),
                                    'parameters': list(signature.parameters.keys())
                                }
                            except (ValueError, TypeError):
                                methods[method_name] = {'signature': 'unable_to_inspect', 'parameters': []}
                
                method_signatures[manager['name']] = methods
            
            elif manager['type'] == 'function':
                func_obj = manager['function']
                try:
                    signature = inspect.signature(func_obj)
                    method_signatures[manager['name']] = {
                        'get_config': {
                            'signature': str(signature),
                            'parameters': list(signature.parameters.keys())
                        }
                    }
                except (ValueError, TypeError):
                    method_signatures[manager['name']] = {
                        'get_config': {'signature': 'unable_to_inspect', 'parameters': []}
                    }
        
        # Detect signature conflicts for get_config method
        get_config_signatures = {}
        for manager_name, methods in method_signatures.items():
            if 'get_config' in methods:
                sig = methods['get_config']['signature']
                if sig in get_config_signatures:
                    get_config_signatures[sig].append(manager_name)
                else:
                    get_config_signatures[sig] = [manager_name]
        
        # Check for conflicts
        for signature, managers in get_config_signatures.items():
            if len(managers) > 1:
                signature_conflicts.append({
                    'signature': signature,
                    'managers': managers,
                    'method': 'get_config'
                })
        
        # Store detailed violation information
        self.violation_details['signature_conflicts'] = {
            'method_signatures': method_signatures,
            'conflicts': signature_conflicts,
            'unique_signatures': len(get_config_signatures)
        }
        
        # EXPECTED FAILURE: Should have conflicts proving violations exist
        self.assertEqual(
            len(get_config_signatures), 1,
            f"SSOT VIOLATION: Found {len(get_config_signatures)} different get_config signatures. "
            f"Signatures: {list(get_config_signatures.keys())}. "
            f"This proves Issue #667 method signature conflicts affecting Golden Path authentication. "
            f"Conflicts: {signature_conflicts}"
        )
    
    def test_configuration_import_path_inconsistencies(self):
        """
        CRITICAL TEST: Detect import path inconsistencies (SHOULD FAIL INITIALLY).
        
        Tests that configuration imports are inconsistent across the codebase,
        affecting Golden Path authentication flow reliability.
        """
        # Known import patterns that should be unified
        import_patterns = [
            'from netra_backend.app.config import get_config',
            'from netra_backend.app.core.configuration.base import get_config',
            'from netra_backend.app.core.configuration.base import get_unified_config',
            'from netra_backend.app.core.managers.unified_configuration_manager import get_configuration_manager'
        ]
        
        detected_imports = []
        import_conflicts = []
        
        for pattern in import_patterns:
            try:
                # Parse the import to test if it's valid
                parts = pattern.split(' import ')
                if len(parts) == 2:
                    module_path = parts[0].replace('from ', '')
                    import_name = parts[1]
                    
                    module = importlib.import_module(module_path)
                    if hasattr(module, import_name):
                        detected_imports.append({
                            'pattern': pattern,
                            'module': module_path,
                            'function': import_name,
                            'callable': callable(getattr(module, import_name))
                        })
            except ImportError:
                # Import doesn't work - this is expected for some
                pass
        
        # Check for multiple ways to get configuration
        config_getters = [imp for imp in detected_imports if 'get_config' in imp['pattern'] or 'get_unified_config' in imp['pattern']]
        
        if len(config_getters) > 1:
            import_conflicts.append({
                'type': 'multiple_config_getters',
                'count': len(config_getters),
                'imports': [imp['pattern'] for imp in config_getters]
            })
        
        # Store detailed violation information
        self.violation_details['import_inconsistencies'] = {
            'detected_imports': detected_imports,
            'conflicts': import_conflicts,
            'config_getter_count': len(config_getters)
        }
        
        # EXPECTED FAILURE: Should have multiple import paths proving violations
        self.assertEqual(
            len(config_getters), 1,
            f"SSOT VIOLATION: Found {len(config_getters)} different configuration import patterns. "
            f"Patterns: {[imp['pattern'] for imp in config_getters]}. "
            f"This proves Issue #667 import inconsistencies affecting Golden Path authentication. "
            f"All imports: {[imp['pattern'] for imp in detected_imports]}"
        )
    
    def test_configuration_manager_interface_compatibility(self):
        """
        CRITICAL TEST: Detect interface compatibility issues (SHOULD FAIL INITIALLY).
        
        Tests that the 3 configuration managers have incompatible interfaces
        that could cause authentication failures in Golden Path.
        """
        if not self.detected_managers:
            self.test_multiple_configuration_manager_classes_exist()
        
        interface_analysis = {}
        compatibility_issues = []
        
        # Define expected interface for SSOT configuration manager
        expected_interface = {
            'get_config': {'required': True, 'type': 'method'},
            'get': {'required': False, 'type': 'method'},
            'reload_config': {'required': False, 'type': 'method'},
            'validate_config_integrity': {'required': False, 'type': 'method'}
        }
        
        for manager in self.detected_managers:
            manager_name = manager['name']
            interface_compliance = {}
            
            if manager['type'] == 'class':
                class_obj = manager['class']
                
                for interface_name, requirements in expected_interface.items():
                    has_method = hasattr(class_obj, interface_name)
                    is_callable = callable(getattr(class_obj, interface_name, None))
                    
                    interface_compliance[interface_name] = {
                        'exists': has_method,
                        'callable': is_callable,
                        'compliant': has_method and is_callable
                    }
                    
                    if requirements['required'] and not (has_method and is_callable):
                        compatibility_issues.append({
                            'manager': manager_name,
                            'issue': f"Missing required method: {interface_name}",
                            'severity': 'critical'
                        })
            
            elif manager['type'] == 'function':
                # For function-based managers, check if they provide config access
                func_name = manager.get('function').__name__
                interface_compliance['get_config'] = {
                    'exists': func_name in ['get_config', 'get_unified_config'],
                    'callable': True,
                    'compliant': True
                }
            
            interface_analysis[manager_name] = interface_compliance
        
        # Check for interface inconsistencies between managers
        if len(interface_analysis) > 1:
            method_support = {}
            for method_name in expected_interface.keys():
                supporters = []
                for manager_name, compliance in interface_analysis.items():
                    if compliance.get(method_name, {}).get('compliant', False):
                        supporters.append(manager_name)
                method_support[method_name] = supporters
            
            # Find methods not supported by all managers
            inconsistent_methods = []
            for method_name, supporters in method_support.items():
                if len(supporters) != len(interface_analysis):
                    inconsistent_methods.append({
                        'method': method_name,
                        'supporters': supporters,
                        'non_supporters': [m for m in interface_analysis.keys() if m not in supporters]
                    })
                    
                    compatibility_issues.append({
                        'manager': 'cross_manager',
                        'issue': f"Method {method_name} not supported by all managers",
                        'severity': 'high',
                        'details': {
                            'supporters': supporters,
                            'non_supporters': [m for m in interface_analysis.keys() if m not in supporters]
                        }
                    })
        
        # Store detailed violation information
        self.violation_details['interface_compatibility'] = {
            'interface_analysis': interface_analysis,
            'compatibility_issues': compatibility_issues,
            'inconsistent_methods': inconsistent_methods if 'inconsistent_methods' in locals() else []
        }
        
        # EXPECTED FAILURE: Should have compatibility issues proving violations
        self.assertEqual(
            len(compatibility_issues), 0,
            f"SSOT VIOLATION: Found {len(compatibility_issues)} interface compatibility issues. "
            f"Issues: {[issue['issue'] for issue in compatibility_issues]}. "
            f"This proves Issue #667 interface incompatibilities affecting Golden Path authentication. "
            f"Interface analysis: {interface_analysis}"
        )
    
    def test_configuration_manager_initialization_conflicts(self):
        """
        CRITICAL TEST: Detect initialization conflicts (SHOULD FAIL INITIALLY).
        
        Tests that the 3 configuration managers have different initialization
        requirements that could cause Golden Path authentication startup failures.
        """
        if not self.detected_managers:
            self.test_multiple_configuration_manager_classes_exist()
        
        initialization_analysis = {}
        initialization_conflicts = []
        
        for manager in self.detected_managers:
            if manager['type'] == 'class':
                class_obj = manager['class']
                manager_name = manager['name']
                
                try:
                    # Analyze __init__ signature
                    init_method = getattr(class_obj, '__init__', None)
                    if init_method:
                        signature = inspect.signature(init_method)
                        parameters = list(signature.parameters.keys())
                        
                        # Remove 'self' parameter
                        if parameters and parameters[0] == 'self':
                            parameters = parameters[1:]
                        
                        # Analyze parameter requirements
                        required_params = []
                        optional_params = []
                        
                        for param_name, param in signature.parameters.items():
                            if param_name != 'self':
                                if param.default == inspect.Parameter.empty:
                                    required_params.append(param_name)
                                else:
                                    optional_params.append(param_name)
                        
                        initialization_analysis[manager_name] = {
                            'signature': str(signature),
                            'all_parameters': parameters,
                            'required_parameters': required_params,
                            'optional_parameters': optional_params,
                            'total_params': len(parameters)
                        }
                        
                        # Check for potential conflicts
                        if required_params:
                            initialization_conflicts.append({
                                'manager': manager_name,
                                'issue': f"Requires initialization parameters: {required_params}",
                                'severity': 'medium'
                            })
                
                except (ValueError, TypeError) as e:
                    initialization_analysis[manager_name] = {
                        'signature': 'unable_to_inspect',
                        'error': str(e)
                    }
                    initialization_conflicts.append({
                        'manager': manager_name,
                        'issue': f"Cannot inspect initialization: {e}",
                        'severity': 'high'
                    })
        
        # Check for initialization signature conflicts
        if len(initialization_analysis) > 1:
            signature_variations = {}
            for manager_name, analysis in initialization_analysis.items():
                if 'signature' in analysis and analysis['signature'] != 'unable_to_inspect':
                    sig = analysis['signature']
                    if sig in signature_variations:
                        signature_variations[sig].append(manager_name)
                    else:
                        signature_variations[sig] = [manager_name]
            
            if len(signature_variations) > 1:
                initialization_conflicts.append({
                    'manager': 'cross_manager',
                    'issue': f"Multiple initialization signatures detected: {list(signature_variations.keys())}",
                    'severity': 'critical',
                    'details': signature_variations
                })
        
        # Store detailed violation information
        self.violation_details['initialization_conflicts'] = {
            'initialization_analysis': initialization_analysis,
            'conflicts': initialization_conflicts,
            'signature_variations': len(signature_variations) if 'signature_variations' in locals() else 0
        }
        
        # EXPECTED FAILURE: Should have initialization conflicts proving violations
        self.assertEqual(
            len(initialization_conflicts), 0,
            f"SSOT VIOLATION: Found {len(initialization_conflicts)} initialization conflicts. "
            f"Conflicts: {[conf['issue'] for conf in initialization_conflicts]}. "
            f"This proves Issue #667 initialization incompatibilities affecting Golden Path authentication startup. "
            f"Analysis: {initialization_analysis}"
        )
    
    def tearDown(self):
        """Clean up and report detailed violation information."""
        if hasattr(self, 'violation_details') and self.violation_details:
            print("\n" + "="*80)
            print("CONFIGURATION MANAGER SSOT VIOLATIONS DETECTED - Issue #667")
            print("="*80)
            
            for violation_type, details in self.violation_details.items():
                print(f"\n{violation_type.upper()}:")
                if isinstance(details, dict):
                    for key, value in details.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"  {details}")
            
            print("\n" + "="*80)
            print("RECOMMENDATION: Consolidate to single configuration manager (SSOT)")
            print("="*80)
        
        super().tearDown()


if __name__ == '__main__':
    unittest.main()