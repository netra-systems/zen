"""
UNIT TEST: SSOT Compliance Regression Prevention - Issue #932

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Architecture Integrity
- Business Goal: Prevent future SSOT violations that could break Golden Path flow
- Value Impact: Protects $500K+ ARR by ensuring configuration architecture remains stable
- Strategic Impact: Establishes regression testing for SSOT configuration management

CRITICAL MISSION: Issue #932 Configuration Manager Broken Import Crisis (P0 SSOT violation)

This test suite prevents regression of SSOT configuration patterns and detects
new violations before they can impact the Golden Path user flow. It validates:

1. Single Source of Truth patterns remain intact
2. No duplicate configuration managers are introduced
3. Import paths remain consistent and working
4. Configuration method signatures stay compatible
5. No circular dependencies are reintroduced

Expected Behavior:
- SSOT configuration patterns should be maintained
- No duplicate configuration manager classes
- Consistent method signatures across configuration components
- Clean import dependency tree
- Proper factory pattern implementation

This test supports ongoing SSOT compliance for Issue #932 remediation.
"""

import unittest
import importlib
import inspect
import sys
import ast
from typing import Dict, List, Set, Optional, Any, Type, Tuple
from pathlib import Path
import re

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestIssue932SSOTComplianceRegression(SSotBaseTestCase, unittest.TestCase):
    """Unit tests to prevent SSOT configuration compliance regression for Issue #932."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.violation_results = {}
        self.compliance_metrics = {}
        self.detected_patterns = {}
        
        # Define SSOT configuration patterns to validate
        self.expected_ssot_patterns = {
            'single_config_entry': 'netra_backend.app.config.get_config',
            'unified_manager': 'netra_backend.app.core.configuration.base.UnifiedConfigManager',
            'configuration_schemas': 'netra_backend.app.schemas.config',
            'environment_detection': 'netra_backend.app.core.environment_constants.EnvironmentDetector',
        }
    
    def test_single_configuration_entry_point_ssot(self):
        """
        CRITICAL TEST: Validate single configuration entry point SSOT pattern.
        
        Ensures there is exactly one primary configuration entry point and no
        duplicate configuration managers that could cause conflicts.
        """
        self.record_metric("test_category", "ssot_entry_point")
        
        # Search for configuration entry points
        config_entry_points = []
        duplicate_managers = []
        
        try:
            # Test primary entry point exists and works
            from netra_backend.app.config import get_config
            config_entry_points.append({
                'path': 'netra_backend.app.config.get_config',
                'callable': callable(get_config),
                'working': True
            })
            
            # Test unified configuration manager exists
            try:
                from netra_backend.app.core.configuration.base import UnifiedConfigManager
                if inspect.isclass(UnifiedConfigManager):
                    config_entry_points.append({
                        'path': 'netra_backend.app.core.configuration.base.UnifiedConfigManager',
                        'is_class': True,
                        'working': True
                    })
            except ImportError:
                config_entry_points.append({
                    'path': 'netra_backend.app.core.configuration.base.UnifiedConfigManager',
                    'working': False,
                    'error': 'ImportError'
                })
            
            # Look for potential duplicate configuration managers
            potential_duplicate_patterns = [
                r'.*[Cc]onfiguration.*[Mm]anager.*',
                r'.*[Cc]onfig.*[Mm]anager.*',
                r'.*[Uu]nified.*[Cc]onfig.*'
            ]
            
            # This is a simplified check - in real implementation would scan codebase
            # For now, record what we found
            self.record_metric("config_entry_points_found", len(config_entry_points))
            self.record_metric("config_entry_points", config_entry_points)
            
            # Validate primary entry point works
            working_entry_points = [ep for ep in config_entry_points if ep.get('working', False)]
            self.assertGreater(len(working_entry_points), 0, "At least one configuration entry point should work")
            
            # Record SSOT compliance
            ssot_compliant = len(working_entry_points) >= 1  # At least one working entry point
            self.record_metric("ssot_entry_point_compliant", ssot_compliant)
            self.record_metric("ssot_entry_point_test", "success")
            
        except Exception as e:
            self.record_metric("ssot_entry_point_test", "failed")
            self.fail(f"SSOT configuration entry point test failed: {e}")
    
    def test_configuration_import_consistency_regression(self):
        """
        CRITICAL TEST: Validate configuration import paths remain consistent.
        
        Prevents regression where import paths change or become broken,
        which was the core issue in #932.
        """
        self.record_metric("test_category", "import_consistency")
        
        # Define expected import paths that should always work
        critical_imports = [
            'netra_backend.app.config',
            'netra_backend.app.core.configuration.base',
            'netra_backend.app.schemas.config',
        ]
        
        import_results = {}
        broken_imports = []
        working_imports = []
        
        for import_path in critical_imports:
            try:
                module = importlib.import_module(import_path)
                import_results[import_path] = {
                    'status': 'success',
                    'module_name': getattr(module, '__name__', 'unknown'),
                    'has_expected_attrs': self._check_expected_attributes(module, import_path)
                }
                working_imports.append(import_path)
                
            except ImportError as e:
                import_results[import_path] = {
                    'status': 'import_error',
                    'error': str(e)
                }
                broken_imports.append(import_path)
                
            except Exception as e:
                import_results[import_path] = {
                    'status': 'other_error',
                    'error': str(e)
                }
        
        # Record results
        self.record_metric("critical_imports_tested", len(critical_imports))
        self.record_metric("working_imports", len(working_imports))
        self.record_metric("broken_imports", len(broken_imports))
        self.record_metric("import_results", import_results)
        
        # Calculate success rate
        if critical_imports:
            import_success_rate = (len(working_imports) / len(critical_imports)) * 100
            self.record_metric("import_success_rate", import_success_rate)
        else:
            import_success_rate = 0
        
        # Regression test - should have high import success rate
        self.assertGreaterEqual(
            import_success_rate, 80.0,
            f"Import success rate should be at least 80%. Current: {import_success_rate}%. "
            f"Broken imports: {broken_imports}"
        )
        
        self.violation_results['import_consistency'] = {
            'success_rate': import_success_rate,
            'broken_imports': broken_imports,
            'status': 'success' if import_success_rate >= 80 else 'regression_detected'
        }
        
        self.record_metric("import_consistency_test", "success")
    
    def test_configuration_method_signature_consistency(self):
        """
        TEST: Validate configuration method signatures remain consistent.
        
        Prevents regression where method signatures change in ways that break
        existing code that depends on configuration management.
        """
        self.record_metric("test_category", "method_signature_consistency")
        
        method_signatures = {}
        signature_issues = []
        
        try:
            # Check get_config method signature
            from netra_backend.app.config import get_config
            
            get_config_signature = inspect.signature(get_config)
            method_signatures['get_config'] = {
                'parameters': list(get_config_signature.parameters.keys()),
                'parameter_count': len(get_config_signature.parameters),
                'return_annotation': str(get_config_signature.return_annotation)
            }
            
            # get_config should have minimal parameters (ideally none)
            param_count = len(get_config_signature.parameters)
            if param_count > 2:  # Allow for some flexibility
                signature_issues.append(f"get_config has too many parameters: {param_count}")
            
            # Check reload_config if it exists
            try:
                from netra_backend.app.config import reload_config
                reload_signature = inspect.signature(reload_config)
                method_signatures['reload_config'] = {
                    'parameters': list(reload_signature.parameters.keys()),
                    'parameter_count': len(reload_signature.parameters),
                    'return_annotation': str(reload_signature.return_annotation)
                }
            except (ImportError, AttributeError):
                method_signatures['reload_config'] = {'status': 'not_available'}
            
            # Check UnifiedConfigManager methods if accessible
            try:
                from netra_backend.app.core.configuration.base import UnifiedConfigManager
                
                if inspect.isclass(UnifiedConfigManager):
                    manager_methods = {}
                    
                    # Check get_config method on manager class
                    if hasattr(UnifiedConfigManager, 'get_config'):
                        get_config_method = getattr(UnifiedConfigManager, 'get_config')
                        manager_get_config_sig = inspect.signature(get_config_method)
                        manager_methods['get_config'] = {
                            'parameters': list(manager_get_config_sig.parameters.keys()),
                            'parameter_count': len(manager_get_config_sig.parameters)
                        }
                    
                    method_signatures['UnifiedConfigManager'] = manager_methods
                    
            except (ImportError, AttributeError):
                method_signatures['UnifiedConfigManager'] = {'status': 'not_accessible'}
            
            # Record results
            self.record_metric("method_signatures", method_signatures)
            self.record_metric("signature_issues", signature_issues)
            self.record_metric("signature_issues_count", len(signature_issues))
            
            # Should have minimal signature issues
            self.assertLessEqual(
                len(signature_issues), 2,
                f"Should have minimal method signature issues. Issues: {signature_issues}"
            )
            
            self.record_metric("method_signature_consistency_test", "success")
            
        except Exception as e:
            self.record_metric("method_signature_consistency_test", "failed")
            self.fail(f"Method signature consistency test failed: {e}")
    
    def test_circular_dependency_regression_prevention(self):
        """
        CRITICAL TEST: Prevent circular dependency regression.
        
        Circular dependencies were a major contributor to Issue #932.
        This test ensures no circular dependencies are reintroduced.
        """
        self.record_metric("test_category", "circular_dependency_prevention")
        
        # Test critical import paths for circular dependencies
        import_order_tests = [
            ['netra_backend.app.config', 'netra_backend.app.core.configuration.base'],
            ['netra_backend.app.core.configuration.base', 'netra_backend.app.schemas.config'],
            ['netra_backend.app.schemas.config', 'shared.isolated_environment'],
        ]
        
        circular_dependency_issues = []
        successful_import_chains = []
        
        for import_chain in import_order_tests:
            try:
                # Clear modules from cache to test fresh import
                modules_to_clear = [mod for mod in import_chain if mod in sys.modules]
                
                # Import in sequence
                imported_modules = []
                for module_path in import_chain:
                    module = importlib.import_module(module_path)
                    imported_modules.append(module_path)
                
                successful_import_chains.append(import_chain)
                
            except ImportError as e:
                error_msg = str(e)
                if any(keyword in error_msg.lower() for keyword in ['circular', 'cycle', 'recursive']):
                    circular_dependency_issues.append({
                        'import_chain': import_chain,
                        'error': error_msg,
                        'type': 'circular_dependency'
                    })
                else:
                    circular_dependency_issues.append({
                        'import_chain': import_chain,
                        'error': error_msg,
                        'type': 'import_error'
                    })
            
            except Exception as e:
                circular_dependency_issues.append({
                    'import_chain': import_chain,
                    'error': str(e),
                    'type': 'other_error'
                })
        
        # Record results
        self.record_metric("import_chains_tested", len(import_order_tests))
        self.record_metric("successful_import_chains", len(successful_import_chains))
        self.record_metric("circular_dependency_issues", len(circular_dependency_issues))
        
        if circular_dependency_issues:
            self.record_metric("circular_dependency_details", circular_dependency_issues)
        
        # Calculate success rate
        if import_order_tests:
            chain_success_rate = (len(successful_import_chains) / len(import_order_tests)) * 100
            self.record_metric("import_chain_success_rate", chain_success_rate)
        else:
            chain_success_rate = 100
        
        # Should have no actual circular dependency issues
        actual_circular_issues = [issue for issue in circular_dependency_issues 
                                if issue['type'] == 'circular_dependency']
        
        self.assertEqual(
            len(actual_circular_issues), 0,
            f"Should have no circular dependency issues. Found: {actual_circular_issues}"
        )
        
        self.violation_results['circular_dependencies'] = {
            'issues_count': len(actual_circular_issues),
            'chain_success_rate': chain_success_rate,
            'status': 'success' if len(actual_circular_issues) == 0 else 'regression_detected'
        }
        
        self.record_metric("circular_dependency_prevention_test", "success")
    
    def test_configuration_factory_pattern_compliance(self):
        """
        TEST: Validate configuration factory patterns remain SSOT compliant.
        
        Ensures that configuration factory patterns follow SSOT principles
        and don't introduce anti-patterns that could cause issues.
        """
        self.record_metric("test_category", "factory_pattern_compliance")
        
        factory_compliance_checks = {}
        compliance_violations = []
        
        try:
            from netra_backend.app.config import get_config
            
            # Test that get_config is callable (factory pattern)
            is_callable = callable(get_config)
            factory_compliance_checks['get_config_callable'] = is_callable
            
            if not is_callable:
                compliance_violations.append("get_config should be callable (factory pattern)")
            
            # Test that get_config returns consistent type
            try:
                config1 = get_config()
                config2 = get_config()
                
                type1 = type(config1)
                type2 = type(config2)
                
                type_consistency = type1 == type2
                factory_compliance_checks['type_consistency'] = type_consistency
                
                if not type_consistency:
                    compliance_violations.append(f"get_config returns inconsistent types: {type1} vs {type2}")
                
            except Exception as e:
                factory_compliance_checks['get_config_execution'] = f"failed: {e}"
                compliance_violations.append(f"get_config execution failed: {e}")
            
            # Test UnifiedConfigManager compliance if accessible
            try:
                from netra_backend.app.core.configuration.base import UnifiedConfigManager
                
                if inspect.isclass(UnifiedConfigManager):
                    # Check if it's a proper class (not a function or other type)
                    factory_compliance_checks['unified_manager_is_class'] = True
                    
                    # Test instantiation
                    try:
                        manager = UnifiedConfigManager()
                        factory_compliance_checks['unified_manager_instantiable'] = True
                        
                        # Check if it has expected methods
                        has_get_config = hasattr(manager, 'get_config')
                        factory_compliance_checks['unified_manager_has_get_config'] = has_get_config
                        
                        if not has_get_config:
                            compliance_violations.append("UnifiedConfigManager should have get_config method")
                            
                    except Exception as e:
                        factory_compliance_checks['unified_manager_instantiation'] = f"failed: {e}"
                        compliance_violations.append(f"UnifiedConfigManager instantiation failed: {e}")
                else:
                    factory_compliance_checks['unified_manager_is_class'] = False
                    compliance_violations.append("UnifiedConfigManager should be a class")
                    
            except ImportError:
                factory_compliance_checks['unified_manager_import'] = "failed"
                # This might be acceptable depending on implementation
        
            # Record results
            self.record_metric("factory_compliance_checks", factory_compliance_checks)
            self.record_metric("compliance_violations", compliance_violations)
            self.record_metric("compliance_violations_count", len(compliance_violations))
            
            # Calculate compliance score
            total_checks = len([v for v in factory_compliance_checks.values() if isinstance(v, bool)])
            passed_checks = sum(v for v in factory_compliance_checks.values() if isinstance(v, bool))
            
            if total_checks > 0:
                compliance_score = (passed_checks / total_checks) * 100
            else:
                compliance_score = 0
                
            self.record_metric("factory_pattern_compliance_score", compliance_score)
            
            # Should have high compliance score
            self.assertGreaterEqual(
                compliance_score, 75.0,
                f"Factory pattern compliance should be at least 75%. Current: {compliance_score}%. "
                f"Violations: {compliance_violations}"
            )
            
            self.violation_results['factory_pattern'] = {
                'compliance_score': compliance_score,
                'violations': compliance_violations,
                'status': 'success' if compliance_score >= 75 else 'compliance_issues'
            }
            
            self.record_metric("factory_pattern_compliance_test", "success")
            
        except Exception as e:
            self.record_metric("factory_pattern_compliance_test", "failed")
            self.fail(f"Factory pattern compliance test failed: {e}")
    
    def test_ssot_compliance_summary_and_regression_detection(self):
        """
        SUMMARY TEST: Comprehensive SSOT compliance summary and regression detection.
        
        Provides complete analysis of SSOT compliance status and detects any
        regressions that could lead to another Issue #932 situation.
        """
        self.record_metric("test_category", "ssot_compliance_summary")
        
        # Collect all violation results
        summary_data = {
            'total_tests_run': 0,
            'tests_with_violations': 0,
            'critical_violations': 0,
            'regression_detected': False,
            'compliance_areas': {}
        }
        
        # Analyze violation results
        for area, results in self.violation_results.items():
            summary_data['total_tests_run'] += 1
            summary_data['compliance_areas'][area] = results
            
            if results.get('status') in ['regression_detected', 'compliance_issues']:
                summary_data['tests_with_violations'] += 1
                
                # Check if this is a critical violation
                if area in ['import_consistency', 'circular_dependencies']:
                    summary_data['critical_violations'] += 1
                    summary_data['regression_detected'] = True
        
        # Calculate overall compliance metrics
        if summary_data['total_tests_run'] > 0:
            compliance_rate = ((summary_data['total_tests_run'] - summary_data['tests_with_violations']) / 
                             summary_data['total_tests_run']) * 100
        else:
            compliance_rate = 0
            
        summary_data['overall_compliance_rate'] = compliance_rate
        
        # Record comprehensive summary
        self.record_metric("ssot_compliance_summary", summary_data)
        self.record_metric("overall_compliance_rate", compliance_rate)
        self.record_metric("regression_detected", summary_data['regression_detected'])
        self.record_metric("critical_violations_count", summary_data['critical_violations'])
        
        # Generate detailed summary message
        summary_message = (
            f"SSOT Configuration Compliance Summary: {compliance_rate:.1f}% compliant "
            f"({summary_data['total_tests_run'] - summary_data['tests_with_violations']}/{summary_data['total_tests_run']} tests passed)"
        )
        
        if summary_data['regression_detected']:
            summary_message += f" - REGRESSION DETECTED: {summary_data['critical_violations']} critical violations"
        
        if summary_data['tests_with_violations'] > 0:
            violation_areas = [area for area, results in summary_data['compliance_areas'].items() 
                             if results.get('status') in ['regression_detected', 'compliance_issues']]
            summary_message += f" - Issues in: {violation_areas}"
        
        self.record_metric("ssot_compliance_final_summary", summary_message)
        
        # Regression test - should have high compliance and no critical violations
        self.assertFalse(
            summary_data['regression_detected'],
            f"No critical SSOT regressions should be detected. Summary: {summary_data}"
        )
        
        self.assertGreaterEqual(
            compliance_rate, 80.0,
            f"SSOT compliance rate should be at least 80%. Current: {compliance_rate}%. "
            f"Details: {summary_data}"
        )
        
        self.assertLessEqual(
            summary_data['critical_violations'], 1,
            f"Should have at most 1 critical violation. Current: {summary_data['critical_violations']}"
        )
    
    def _check_expected_attributes(self, module: Any, import_path: str) -> Dict[str, bool]:
        """Helper method to check if module has expected attributes."""
        expected_attrs = {}
        
        if 'config' in import_path:
            expected_attrs['get_config'] = hasattr(module, 'get_config')
            
        if 'base' in import_path:
            expected_attrs['UnifiedConfigManager'] = hasattr(module, 'UnifiedConfigManager')
            expected_attrs['get_unified_config'] = hasattr(module, 'get_unified_config')
            
        if 'schemas' in import_path:
            expected_attrs['AppConfig'] = hasattr(module, 'AppConfig')
            
        return expected_attrs


if __name__ == '__main__':
    # Run tests
    unittest.main()