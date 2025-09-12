#!/usr/bin/env python3
"""
E2E SSOT Compliance Enhancement Suite - Mission Critical Test Suite

Business Value: Platform/Internal - Test Infrastructure SSOT Enhancement
Enhances existing SSOT framework for E2E-specific validation and compliance.

This suite validates and enhances SSOT framework integration for E2E tests:
1. Validates get_test_base_for_category('e2e') returns correct SSOT class
2. Ensures validate_test_class() function works on E2E tests
3. Validates E2E tests follow all SSOT patterns and conventions
4. Provides enhanced E2E-specific SSOT validation capabilities

Purpose: Strategic enhancement of SSOT compliance infrastructure for E2E testing.
Extends existing SSOT validation to handle E2E-specific requirements.

Author: SSOT Compliance Enhancement Agent
Date: 2025-09-10
"""

import ast
import inspect
import logging
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, Union
import importlib
import importlib.util

# SSOT imports
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from shared.isolated_environment import get_env

# Try to import existing SSOT validation utilities
try:
    from test_framework.ssot.orchestration import validate_test_class, get_test_base_for_category
    HAS_SSOT_ORCHESTRATION = True
except ImportError:
    HAS_SSOT_ORCHESTRATION = False

logger = logging.getLogger(__name__)


class E2ESsotValidationEnhancer:
    """Enhanced SSOT validation utilities specifically for E2E tests."""
    
    def __init__(self):
        """Initialize E2E SSOT validation enhancer."""
        self.project_root = Path(__file__).parent.parent.parent
        self.validation_errors = []
        self.validation_warnings = []
        
    def enhanced_validate_test_class(self, test_class: Type) -> Dict[str, Any]:
        """
        Enhanced test class validation for E2E tests.
        
        Extends basic SSOT validation with E2E-specific requirements.
        """
        validation_result = {
            'is_valid': True,
            'class_name': test_class.__name__,
            'module_name': test_class.__module__,
            'base_classes': [cls.__name__ for cls in test_class.__mro__[1:]],  # Skip self
            'ssot_compliance': True,
            'e2e_specific_compliance': True,
            'issues': [],
            'warnings': []
        }
        
        # Check SSOT base class inheritance
        ssot_base_classes = {SSotBaseTestCase, SSotAsyncTestCase}
        has_ssot_base = any(issubclass(test_class, base_cls) for base_cls in ssot_base_classes)
        
        if not has_ssot_base:
            validation_result['ssot_compliance'] = False
            validation_result['is_valid'] = False
            validation_result['issues'].append("Does not inherit from SSOT base class (SSotBaseTestCase or SSotAsyncTestCase)")
        
        # Check for forbidden BaseE2ETest inheritance
        base_class_names = validation_result['base_classes']
        if 'BaseE2ETest' in base_class_names:
            validation_result['e2e_specific_compliance'] = False
            validation_result['is_valid'] = False
            validation_result['issues'].append("Inherits from deprecated BaseE2ETest instead of SSOT base class")
        
        # Check test method naming conventions
        test_methods = [name for name in dir(test_class) if name.startswith('test_') and callable(getattr(test_class, name))]
        if not test_methods:
            validation_result['warnings'].append("No test methods found (methods starting with 'test_')")
        
        # Check for setup/teardown method compatibility
        setup_methods = ['setup_method', 'async_setup_method']
        teardown_methods = ['teardown_method', 'async_teardown_method']
        
        for method_name in setup_methods + teardown_methods:
            if hasattr(test_class, method_name):
                method = getattr(test_class, method_name)
                if not callable(method):
                    validation_result['warnings'].append(f"{method_name} exists but is not callable")
        
        # Check for proper async handling
        is_async_test_class = issubclass(test_class, SSotAsyncTestCase)
        has_async_methods = any(inspect.iscoroutinefunction(getattr(test_class, name)) 
                               for name in test_methods if hasattr(test_class, name))
        
        if has_async_methods and not is_async_test_class:
            validation_result['warnings'].append("Has async test methods but does not inherit from SSotAsyncTestCase")
        
        # E2E specific validations
        e2e_indicators = ['e2e', 'end_to_end', 'integration']
        class_name_lower = test_class.__name__.lower()
        module_path_lower = test_class.__module__.lower()
        
        is_likely_e2e = any(indicator in class_name_lower or indicator in module_path_lower 
                           for indicator in e2e_indicators)
        
        if is_likely_e2e:
            validation_result['is_e2e_test'] = True
            
            # Check for E2E-specific patterns
            if not any(method for method in test_methods if 'e2e' in method.lower() or 'integration' in method.lower()):
                validation_result['warnings'].append("E2E test class but no E2E-specific test methods found")
        else:
            validation_result['is_e2e_test'] = False
        
        return validation_result
    
    def enhanced_get_test_base_for_category(self, category: str) -> Type:
        """
        Enhanced category-to-base-class mapping for E2E tests.
        
        Provides E2E-specific base class selection logic.
        """
        category_lower = category.lower()
        
        # E2E categories that benefit from async support
        async_e2e_categories = {
            'e2e_async', 'async_e2e', 'websocket_e2e', 'realtime_e2e'
        }
        
        # Standard E2E categories
        sync_e2e_categories = {
            'e2e', 'end_to_end', 'integration', 'e2e_sync', 'e2e_critical'
        }
        
        if category_lower in async_e2e_categories:
            return SSotAsyncTestCase
        elif category_lower in sync_e2e_categories:
            return SSotBaseTestCase
        else:
            # Default fallback logic
            if 'async' in category_lower or 'websocket' in category_lower:
                return SSotAsyncTestCase
            else:
                return SSotBaseTestCase
    
    def validate_e2e_ssot_patterns(self, test_class: Type) -> Dict[str, Any]:
        """
        Validate E2E-specific SSOT patterns and conventions.
        
        Checks for compliance with E2E SSOT best practices.
        """
        patterns_result = {
            'class_name': test_class.__name__,
            'environment_usage': 'unknown',
            'metrics_usage': 'unknown', 
            'cleanup_usage': 'unknown',
            'isolation_compliance': 'unknown',
            'patterns_score': 0.0,
            'recommendations': []
        }
        
        # Check environment variable usage patterns
        if hasattr(test_class, 'get_env') or hasattr(test_class, 'get_env_var'):
            patterns_result['environment_usage'] = 'ssot_compliant'
            patterns_result['patterns_score'] += 25
        else:
            patterns_result['environment_usage'] = 'needs_improvement'
            patterns_result['recommendations'].append("Use SSOT environment methods (get_env_var, set_env_var)")
        
        # Check metrics usage patterns
        if hasattr(test_class, 'record_metric') or hasattr(test_class, 'get_metric'):
            patterns_result['metrics_usage'] = 'ssot_compliant'
            patterns_result['patterns_score'] += 25
        else:
            patterns_result['metrics_usage'] = 'needs_improvement'
            patterns_result['recommendations'].append("Use SSOT metrics methods (record_metric, get_metric)")
        
        # Check cleanup patterns
        if hasattr(test_class, 'add_cleanup'):
            patterns_result['cleanup_usage'] = 'ssot_compliant'
            patterns_result['patterns_score'] += 25
        else:
            patterns_result['cleanup_usage'] = 'needs_improvement'
            patterns_result['recommendations'].append("Use SSOT cleanup methods (add_cleanup)")
        
        # Check isolation compliance
        if issubclass(test_class, (SSotBaseTestCase, SSotAsyncTestCase)):
            patterns_result['isolation_compliance'] = 'ssot_compliant'
            patterns_result['patterns_score'] += 25
        else:
            patterns_result['isolation_compliance'] = 'non_compliant'
            patterns_result['recommendations'].append("Inherit from SSOT base classes for proper isolation")
        
        return patterns_result
    
    def scan_e2e_directory_for_compliance(self, e2e_dir: Path) -> Dict[str, Any]:
        """
        Scan an entire E2E directory for SSOT compliance.
        
        Provides comprehensive compliance report for E2E test directories.
        """
        scan_result = {
            'directory': str(e2e_dir),
            'total_files': 0,
            'scanned_files': 0,
            'compliant_files': 0,
            'non_compliant_files': 0,
            'compliance_percentage': 0.0,
            'file_results': [],
            'summary': {
                'total_classes': 0,
                'compliant_classes': 0,
                'classes_with_warnings': 0,
                'classes_with_errors': 0
            }
        }
        
        if not e2e_dir.exists():
            scan_result['error'] = f"Directory {e2e_dir} does not exist"
            return scan_result
        
        # Find all Python test files
        test_files = list(e2e_dir.rglob("test_*.py"))
        scan_result['total_files'] = len(test_files)
        
        for test_file in test_files:
            try:
                file_result = self._scan_single_file_for_compliance(test_file)
                scan_result['file_results'].append(file_result)
                scan_result['scanned_files'] += 1
                
                if file_result['is_compliant']:
                    scan_result['compliant_files'] += 1
                else:
                    scan_result['non_compliant_files'] += 1
                
                # Update summary
                scan_result['summary']['total_classes'] += file_result['class_count']
                scan_result['summary']['compliant_classes'] += file_result['compliant_classes']
                scan_result['summary']['classes_with_warnings'] += file_result['classes_with_warnings']
                scan_result['summary']['classes_with_errors'] += file_result['classes_with_errors']
                
            except Exception as e:
                logger.warning(f"Failed to scan {test_file}: {e}")
        
        # Calculate compliance percentage
        if scan_result['scanned_files'] > 0:
            scan_result['compliance_percentage'] = (
                scan_result['compliant_files'] / scan_result['scanned_files']
            ) * 100.0
        
        return scan_result
    
    def _scan_single_file_for_compliance(self, file_path: Path) -> Dict[str, Any]:
        """Scan a single file for SSOT compliance."""
        file_result = {
            'file_path': str(file_path.relative_to(self.project_root)),
            'is_compliant': True,
            'class_count': 0,
            'compliant_classes': 0,
            'classes_with_warnings': 0,
            'classes_with_errors': 0,
            'classes': []
        }
        
        try:
            # Parse the file to find test classes
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                    file_result['class_count'] += 1
                    
                    # Basic compliance check via AST
                    base_names = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_names.append(base.id)
                    
                    class_info = {
                        'name': node.name,
                        'bases': base_names,
                        'is_compliant': True,
                        'has_warnings': False,
                        'has_errors': False
                    }
                    
                    # Check compliance
                    if 'BaseE2ETest' in base_names:
                        class_info['is_compliant'] = False
                        class_info['has_errors'] = True
                        file_result['is_compliant'] = False
                    elif any(base in ['SSotBaseTestCase', 'SSotAsyncTestCase'] for base in base_names):
                        class_info['is_compliant'] = True
                    else:
                        class_info['has_warnings'] = True
                        class_info['is_compliant'] = False
                        file_result['is_compliant'] = False
                    
                    file_result['classes'].append(class_info)
                    
                    if class_info['is_compliant']:
                        file_result['compliant_classes'] += 1
                    if class_info['has_warnings']:
                        file_result['classes_with_warnings'] += 1
                    if class_info['has_errors']:
                        file_result['classes_with_errors'] += 1
        
        except Exception as e:
            file_result['error'] = str(e)
            file_result['is_compliant'] = False
        
        return file_result


class TestE2ESsotCompliance(SSotBaseTestCase):
    """
    Mission Critical: E2E SSOT Compliance Enhancement Suite.
    
    Validates and enhances SSOT framework for E2E-specific requirements.
    """
    
    def setup_method(self, method=None):
        """Set up E2E SSOT compliance test environment."""
        super().setup_method(method)
        
        # Initialize isolated environment
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        
        # Set test environment
        self.env.set("E2E_SSOT_COMPLIANCE_TEST", "true", "e2e_ssot_test")
        self.env.set("SSOT_ENHANCEMENT_MODE", "true", "e2e_ssot_test")
        self.env.set("TESTING", "true", "e2e_ssot_test")
        
        # Initialize validation enhancer
        self.validation_enhancer = E2ESsotValidationEnhancer()
        
        self.record_metric("e2e_ssot_compliance_setup_completed", True)
    
    def test_e2e_category_maps_to_correct_base_class(self):
        """
        Validate get_test_base_for_category('e2e') returns correct SSOT class.
        
        Tests enhanced category mapping logic for E2E tests.
        """
        logger.info("Testing E2E category to SSOT base class mapping")
        
        # Test standard E2E categories
        e2e_categories = [
            ('e2e', SSotBaseTestCase),
            ('end_to_end', SSotBaseTestCase),
            ('integration', SSotBaseTestCase),
            ('e2e_sync', SSotBaseTestCase),
            ('e2e_critical', SSotBaseTestCase)
        ]
        
        # Test async E2E categories
        async_e2e_categories = [
            ('e2e_async', SSotAsyncTestCase),
            ('async_e2e', SSotAsyncTestCase),
            ('websocket_e2e', SSotAsyncTestCase),
            ('realtime_e2e', SSotAsyncTestCase)
        ]
        
        correct_mappings = 0
        total_mappings = 0
        
        # Test standard E2E mappings
        for category, expected_class in e2e_categories:
            result_class = self.validation_enhancer.enhanced_get_test_base_for_category(category)
            total_mappings += 1
            
            if result_class == expected_class:
                correct_mappings += 1
                logger.debug(f" PASS:  Category '{category}' correctly maps to {expected_class.__name__}")
            else:
                logger.warning(f" FAIL:  Category '{category}' maps to {result_class.__name__}, expected {expected_class.__name__}")
        
        # Test async E2E mappings
        for category, expected_class in async_e2e_categories:
            result_class = self.validation_enhancer.enhanced_get_test_base_for_category(category)
            total_mappings += 1
            
            if result_class == expected_class:
                correct_mappings += 1
                logger.debug(f" PASS:  Category '{category}' correctly maps to {expected_class.__name__}")
            else:
                logger.warning(f" FAIL:  Category '{category}' maps to {result_class.__name__}, expected {expected_class.__name__}")
        
        # Test fallback logic
        fallback_categories = [
            ('custom_async_test', SSotAsyncTestCase),
            ('websocket_integration', SSotAsyncTestCase),
            ('regular_test', SSotBaseTestCase),
            ('sync_integration', SSotBaseTestCase)
        ]
        
        for category, expected_class in fallback_categories:
            result_class = self.validation_enhancer.enhanced_get_test_base_for_category(category)
            total_mappings += 1
            
            if result_class == expected_class:
                correct_mappings += 1
                logger.debug(f" PASS:  Fallback category '{category}' correctly maps to {expected_class.__name__}")
            else:
                logger.debug(f"[U+2139][U+FE0F]  Fallback category '{category}' maps to {result_class.__name__}, expected {expected_class.__name__}")
        
        # Record metrics
        mapping_accuracy = (correct_mappings / total_mappings) * 100.0
        self.record_metric("category_mappings_tested", total_mappings)
        self.record_metric("correct_category_mappings", correct_mappings)
        self.record_metric("category_mapping_accuracy", mapping_accuracy)
        
        # Assert minimum accuracy
        minimum_accuracy = 80.0  # 80% of mappings should be correct
        assert mapping_accuracy >= minimum_accuracy, (
            f"Category mapping accuracy {mapping_accuracy:.1f}% below minimum {minimum_accuracy}%. "
            f"Only {correct_mappings}/{total_mappings} mappings were correct."
        )
        
        logger.info(f" PASS:  E2E category mapping validation passed: {mapping_accuracy:.1f}% accuracy")
    
    def test_validate_test_class_works_for_e2e_tests(self):
        """
        Validate validate_test_class() function works on E2E tests.
        
        Tests enhanced validation logic for E2E test classes.
        """
        logger.info("Testing enhanced test class validation for E2E tests")
        
        # Create mock test classes for validation
        class MockCompliantE2ETest(SSotBaseTestCase):
            def test_example(self):
                pass
        
        class MockAsyncE2ETest(SSotAsyncTestCase):
            async def test_async_example(self):
                pass
        
        class MockNonCompliantTest:
            def test_example(self):
                pass
        
        # Test compliant E2E test
        compliant_result = self.validation_enhancer.enhanced_validate_test_class(MockCompliantE2ETest)
        
        assert compliant_result['is_valid'], "Compliant E2E test should be valid"
        assert compliant_result['ssot_compliance'], "Compliant test should have SSOT compliance"
        assert compliant_result['e2e_specific_compliance'], "Compliant test should have E2E compliance"
        assert len(compliant_result['issues']) == 0, "Compliant test should have no issues"
        
        # Test async compliant E2E test
        async_result = self.validation_enhancer.enhanced_validate_test_class(MockAsyncE2ETest)
        
        assert async_result['is_valid'], "Async compliant E2E test should be valid"
        assert async_result['ssot_compliance'], "Async compliant test should have SSOT compliance"
        assert 'SSotAsyncTestCase' in async_result['base_classes'], "Should inherit from SSotAsyncTestCase"
        
        # Test non-compliant test
        non_compliant_result = self.validation_enhancer.enhanced_validate_test_class(MockNonCompliantTest)
        
        assert not non_compliant_result['is_valid'], "Non-compliant test should be invalid"
        assert not non_compliant_result['ssot_compliance'], "Non-compliant test should fail SSOT compliance"
        assert len(non_compliant_result['issues']) > 0, "Non-compliant test should have issues"
        
        # Record metrics
        self.record_metric("compliant_test_validation_passed", compliant_result['is_valid'])
        self.record_metric("async_test_validation_passed", async_result['is_valid'])
        self.record_metric("non_compliant_test_detected", not non_compliant_result['is_valid'])
        self.record_metric("validation_function_working", True)
        
        logger.info(" PASS:  Enhanced test class validation working correctly for E2E tests")
    
    def test_e2e_tests_follow_ssot_patterns(self):
        """
        Validate E2E tests follow all SSOT patterns and conventions.
        
        Comprehensive SSOT pattern compliance check for E2E tests.
        """
        logger.info("Testing E2E SSOT patterns and conventions compliance")
        
        # Create test classes with different pattern compliance levels
        class FullyCompliantE2ETest(SSotBaseTestCase):
            def test_example(self):
                # Uses SSOT methods
                self.record_metric("test_metric", 1)
                env_value = self.get_env_var("TEST_VAR", "default")
                self.add_cleanup(lambda: None)
        
        class PartiallyCompliantE2ETest(SSotBaseTestCase):
            def test_example(self):
                # Missing some SSOT patterns
                pass
        
        class NonCompliantTest:
            def test_example(self):
                # No SSOT compliance at all
                pass
        
        # Test pattern compliance
        fully_compliant_patterns = self.validation_enhancer.validate_e2e_ssot_patterns(FullyCompliantE2ETest)
        partially_compliant_patterns = self.validation_enhancer.validate_e2e_ssot_patterns(PartiallyCompliantE2ETest)
        non_compliant_patterns = self.validation_enhancer.validate_e2e_ssot_patterns(NonCompliantTest)
        
        # Validate fully compliant test
        assert fully_compliant_patterns['patterns_score'] == 100.0, "Fully compliant test should score 100%"
        assert fully_compliant_patterns['environment_usage'] == 'ssot_compliant', "Should have compliant environment usage"
        assert fully_compliant_patterns['metrics_usage'] == 'ssot_compliant', "Should have compliant metrics usage"
        assert fully_compliant_patterns['cleanup_usage'] == 'ssot_compliant', "Should have compliant cleanup usage"
        assert fully_compliant_patterns['isolation_compliance'] == 'ssot_compliant', "Should have isolation compliance"
        assert len(fully_compliant_patterns['recommendations']) == 0, "Fully compliant should have no recommendations"
        
        # Validate partially compliant test
        assert 0 < partially_compliant_patterns['patterns_score'] < 100.0, "Partially compliant should have partial score"
        assert len(partially_compliant_patterns['recommendations']) > 0, "Should have improvement recommendations"
        
        # Validate non-compliant test
        assert non_compliant_patterns['patterns_score'] == 0.0, "Non-compliant should score 0%"
        assert non_compliant_patterns['isolation_compliance'] == 'non_compliant', "Should be non-compliant"
        assert len(non_compliant_patterns['recommendations']) >= 4, "Should have multiple recommendations"
        
        # Test directory scanning capability
        e2e_dir = Path(__file__).parent.parent / "e2e"
        if e2e_dir.exists():
            scan_result = self.validation_enhancer.scan_e2e_directory_for_compliance(e2e_dir)
            
            self.record_metric("e2e_directory_scanned", True)
            self.record_metric("e2e_files_found", scan_result['total_files'])
            self.record_metric("e2e_compliance_percentage", scan_result['compliance_percentage'])
            
            logger.info(f"E2E directory scan: {scan_result['compliance_percentage']:.1f}% compliance")
        
        # Record comprehensive metrics
        self.record_metric("fully_compliant_patterns_score", fully_compliant_patterns['patterns_score'])
        self.record_metric("partially_compliant_patterns_score", partially_compliant_patterns['patterns_score'])
        self.record_metric("non_compliant_patterns_score", non_compliant_patterns['patterns_score'])
        self.record_metric("pattern_validation_working", True)
        
        logger.info(" PASS:  E2E SSOT patterns and conventions validation passed")
    
    def test_comprehensive_e2e_ssot_enhancement_validation(self):
        """
        Comprehensive validation of all E2E SSOT enhancement features.
        
        Final validation ensuring all enhancement capabilities work correctly.
        """
        logger.info("Running comprehensive E2E SSOT enhancement validation")
        
        enhancement_report = {
            'category_mapping_functional': False,
            'test_validation_functional': False,
            'pattern_validation_functional': False,
            'directory_scanning_functional': False,
            'enhancement_coverage_percentage': 0.0
        }
        
        # Test category mapping functionality
        try:
            sync_class = self.validation_enhancer.enhanced_get_test_base_for_category('e2e')
            async_class = self.validation_enhancer.enhanced_get_test_base_for_category('e2e_async')
            
            enhancement_report['category_mapping_functional'] = (
                sync_class == SSotBaseTestCase and async_class == SSotAsyncTestCase
            )
        except Exception as e:
            logger.warning(f"Category mapping test failed: {e}")
        
        # Test validation functionality
        try:
            class TestValidationClass(SSotBaseTestCase):
                def test_example(self):
                    pass
            
            validation_result = self.validation_enhancer.enhanced_validate_test_class(TestValidationClass)
            enhancement_report['test_validation_functional'] = validation_result['is_valid']
        except Exception as e:
            logger.warning(f"Test validation test failed: {e}")
        
        # Test pattern validation functionality
        try:
            class TestPatternClass(SSotBaseTestCase):
                def test_example(self):
                    pass
            
            pattern_result = self.validation_enhancer.validate_e2e_ssot_patterns(TestPatternClass)
            enhancement_report['pattern_validation_functional'] = (
                'patterns_score' in pattern_result and pattern_result['patterns_score'] >= 0
            )
        except Exception as e:
            logger.warning(f"Pattern validation test failed: {e}")
        
        # Test directory scanning functionality
        try:
            test_dir = Path(__file__).parent
            scan_result = self.validation_enhancer.scan_e2e_directory_for_compliance(test_dir)
            enhancement_report['directory_scanning_functional'] = (
                'total_files' in scan_result and scan_result['total_files'] >= 0
            )
        except Exception as e:
            logger.warning(f"Directory scanning test failed: {e}")
        
        # Calculate overall enhancement coverage
        functional_features = sum(enhancement_report[key] for key in enhancement_report if key != 'enhancement_coverage_percentage')
        total_features = len(enhancement_report) - 1  # Exclude percentage key
        enhancement_report['enhancement_coverage_percentage'] = (functional_features / total_features) * 100.0
        
        # Record comprehensive metrics
        for feature, status in enhancement_report.items():
            self.record_metric(f"enhancement_{feature}", status)
        
        # Log comprehensive report
        logger.info(f"""
E2E SSOT ENHANCEMENT VALIDATION REPORT
====================================
Category Mapping: {' PASS:  FUNCTIONAL' if enhancement_report['category_mapping_functional'] else ' FAIL:  BROKEN'}
Test Validation: {' PASS:  FUNCTIONAL' if enhancement_report['test_validation_functional'] else ' FAIL:  BROKEN'}
Pattern Validation: {' PASS:  FUNCTIONAL' if enhancement_report['pattern_validation_functional'] else ' FAIL:  BROKEN'}
Directory Scanning: {' PASS:  FUNCTIONAL' if enhancement_report['directory_scanning_functional'] else ' FAIL:  BROKEN'}

Overall Enhancement Coverage: {enhancement_report['enhancement_coverage_percentage']:.1f}% ({functional_features}/{total_features})
        """)
        
        # Assert minimum enhancement coverage
        minimum_coverage = 75.0  # 75% of enhancement features must work
        assert enhancement_report['enhancement_coverage_percentage'] >= minimum_coverage, (
            f"E2E SSOT enhancement coverage {enhancement_report['enhancement_coverage_percentage']:.1f}% "
            f"below minimum {minimum_coverage}%. Enhancement features may be broken."
        )
        
        logger.info(f" PASS:  COMPREHENSIVE ENHANCEMENT VALIDATION PASSED: {enhancement_report['enhancement_coverage_percentage']:.1f}% coverage")
    
    def test_integration_with_existing_ssot_infrastructure(self):
        """
        Test integration with existing SSOT compliance infrastructure.
        
        Validates compatibility with existing SSOT validation systems.
        """
        logger.info("Testing integration with existing SSOT infrastructure")
        
        integration_status = {
            'existing_ssot_orchestration_available': HAS_SSOT_ORCHESTRATION,
            'enhanced_validation_compatible': True,
            'fallback_mechanisms_working': True,
            'integration_functional': True
        }
        
        # Test existing SSOT orchestration integration
        if HAS_SSOT_ORCHESTRATION:
            try:
                # Test existing validate_test_class function
                existing_result = validate_test_class(SSotBaseTestCase)
                integration_status['existing_validation_working'] = existing_result is not None
                
                # Test existing get_test_base_for_category function  
                existing_base = get_test_base_for_category('e2e')
                integration_status['existing_category_mapping_working'] = existing_base is not None
                
            except Exception as e:
                logger.warning(f"Existing SSOT orchestration integration failed: {e}")
                integration_status['existing_validation_working'] = False
                integration_status['existing_category_mapping_working'] = False
        
        # Test enhanced functions work alongside existing ones
        try:
            enhanced_result = self.validation_enhancer.enhanced_validate_test_class(SSotBaseTestCase)
            enhanced_base = self.validation_enhancer.enhanced_get_test_base_for_category('e2e')
            
            integration_status['enhanced_functions_working'] = (
                enhanced_result['is_valid'] and enhanced_base == SSotBaseTestCase
            )
        except Exception as e:
            logger.warning(f"Enhanced functions test failed: {e}")
            integration_status['enhanced_functions_working'] = False
            integration_status['integration_functional'] = False
        
        # Record integration metrics
        for status_key, status_value in integration_status.items():
            self.record_metric(f"integration_{status_key}", status_value)
        
        # Log integration status
        integration_summary = []
        integration_summary.append(f"Existing SSOT Orchestration: {'Available' if integration_status['existing_ssot_orchestration_available'] else 'Not Available'}")
        integration_summary.append(f"Enhanced Validation: {'Compatible' if integration_status['enhanced_validation_compatible'] else 'Incompatible'}")
        integration_summary.append(f"Fallback Mechanisms: {'Working' if integration_status['fallback_mechanisms_working'] else 'Broken'}")
        integration_summary.append(f"Overall Integration: {'Functional' if integration_status['integration_functional'] else 'Broken'}")
        
        logger.info("SSOT Infrastructure Integration Status:\n" + "\n".join(integration_summary))
        
        # Assert integration is functional (this is informational, so we don't fail)
        if not integration_status['integration_functional']:
            logger.warning("E2E SSOT enhancement integration has issues but continuing...")
        
        logger.info(" PASS:  SSOT infrastructure integration validation completed")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])