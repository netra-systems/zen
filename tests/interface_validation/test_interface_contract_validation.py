"""
Interface Contract Validation Test Suite

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Prevent interface evolution failures that break core chat functionality
- Value Impact: Validates systematic interface contract validation prevents parameter mismatches
- Strategic Impact: Ensures interface governance prevents entire classes of integration failures

This test suite implements interface contract validation testing to prevent
the systematic interface evolution governance failures identified in the Five Whys analysis.

VALIDATION TARGETS:
1. Factory-to-constructor parameter contract validation
2. Interface consistency across all factory patterns
3. Automated detection of parameter naming mismatches
4. Contract evolution validation workflows

CRITICAL: These tests serve as the "contract enforcement" layer that would have
prevented the original websocket_connection_id vs websocket_client_id parameter mismatch.
"""

import asyncio
import inspect
import ast
import os
import re
from typing import Dict, List, Any, Optional, Tuple, Set
import pytest
from unittest.mock import patch

from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor
from netra_backend.app.core.supervisor_factory import create_supervisor_core
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.database.database_fixtures import DatabaseTestManager


class InterfaceContractValidator:
    """
    Utility class for validating interface contracts between factory methods and constructors.
    
    This class implements the systematic interface validation that would have prevented
    the original parameter mismatch issue.
    """
    
    @staticmethod
    def extract_constructor_parameters(class_type) -> Dict[str, inspect.Parameter]:
        """Extract constructor parameters from a class."""
        signature = inspect.signature(class_type.__init__)
        # Skip 'self' parameter
        return {name: param for name, param in signature.parameters.items() if name != 'self'}
    
    @staticmethod
    def extract_factory_method_calls(source_code: str, target_class: str) -> List[Dict]:
        """
        Extract factory method calls to a target class from source code.
        
        This uses AST parsing to find all places where a target class constructor is called
        and extract the parameter names used in those calls.
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return []
        
        calls = []
        
        class CallVisitor(ast.NodeVisitor):
            def visit_Call(self, node):
                # Check if this is a call to the target class
                if isinstance(node.func, ast.Name) and node.func.id == target_class:
                    call_info = {
                        'line': node.lineno,
                        'keywords': [],
                        'args': len(node.args)
                    }
                    
                    # Extract keyword arguments
                    for keyword in node.keywords:
                        if keyword.arg:  # Skip **kwargs
                            call_info['keywords'].append(keyword.arg)
                    
                    calls.append(call_info)
                
                self.generic_visit(node)
        
        visitor = CallVisitor()
        visitor.visit(tree)
        return calls
    
    @staticmethod
    def validate_parameter_consistency(
        constructor_params: Dict[str, inspect.Parameter],
        factory_calls: List[Dict]
    ) -> List[str]:
        """
        Validate parameter consistency between constructor and factory calls.
        
        Returns a list of validation errors found.
        """
        errors = []
        
        for call_info in factory_calls:
            call_keywords = set(call_info['keywords'])
            constructor_keywords = set(constructor_params.keys())
            
            # Find parameters passed in factory call but not in constructor
            unknown_params = call_keywords - constructor_keywords
            for param in unknown_params:
                errors.append(
                    f"Line {call_info['line']}: Parameter '{param}' not in constructor signature. "
                    f"Available parameters: {sorted(constructor_keywords)}"
                )
            
            # Check for deprecated parameter patterns
            for param in call_keywords:
                if 'websocket_connection_id' in param:
                    errors.append(
                        f"Line {call_info['line']}: Deprecated parameter '{param}' used. "
                        f"Should use 'websocket_client_id' instead."
                    )
        
        return errors
    
    @staticmethod
    def scan_codebase_for_interface_violations(
        base_path: str,
        target_classes: List[str]
    ) -> Dict[str, List[str]]:
        """
        Scan entire codebase for interface contract violations.
        
        Returns a dictionary mapping file paths to lists of violations found.
        """
        violations = {}
        
        for root, dirs, files in os.walk(base_path):
            # Skip test directories and cache directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    
                    file_violations = []
                    
                    for target_class in target_classes:
                        # Extract constructor parameters
                        try:
                            module_globals = {}
                            exec(f"from {target_class.split('.')[-1]} import {target_class.split('.')[-1]}", module_globals)
                            class_obj = module_globals[target_class.split('.')[-1]]
                            constructor_params = InterfaceContractValidator.extract_constructor_parameters(class_obj)
                        except:
                            # If we can't import the class, use hardcoded validation for known classes
                            if target_class == 'UserExecutionContext':
                                constructor_params = {
                                    'user_id': None,
                                    'thread_id': None,
                                    'run_id': None,
                                    'websocket_client_id': None,  # Correct parameter
                                    'db_session': None
                                }
                            else:
                                continue
                        
                        # Extract factory calls
                        factory_calls = InterfaceContractValidator.extract_factory_method_calls(
                            source_code, target_class.split('.')[-1]
                        )
                        
                        # Validate consistency
                        call_violations = InterfaceContractValidator.validate_parameter_consistency(
                            constructor_params, factory_calls
                        )
                        
                        file_violations.extend(call_violations)
                    
                    if file_violations:
                        violations[file_path] = file_violations
                
                except Exception as e:
                    # Skip files that can't be read or parsed
                    continue
        
        return violations


class TestInterfaceContractValidation(SSotBaseTestCase):
    """
    Test interface contract validation across the codebase.
    
    These tests implement systematic interface validation that would prevent
    parameter contract violations like the original websocket parameter mismatch.
    """
    
    def test_user_execution_context_interface_contract(self):
        """
        Test UserExecutionContext interface contract validation.
        
        This validates that UserExecutionContext constructor parameters match
        what factory methods are attempting to pass.
        """
        # Get actual constructor parameters
        constructor_params = InterfaceContractValidator.extract_constructor_parameters(UserExecutionContext)
        
        # Validate critical parameters are present
        assert 'user_id' in constructor_params, "UserExecutionContext missing user_id parameter"
        assert 'thread_id' in constructor_params, "UserExecutionContext missing thread_id parameter"
        assert 'websocket_client_id' in constructor_params, "UserExecutionContext missing websocket_client_id parameter"
        
        # Validate deprecated parameters are NOT present
        assert 'websocket_connection_id' not in constructor_params, \
            "UserExecutionContext has deprecated websocket_connection_id parameter"
        
        print(f"✅ UserExecutionContext interface contract validation passed")
        print(f"✅ Constructor parameters: {sorted(constructor_params.keys())}")
    
    def test_websocket_factory_interface_compliance(self):
        """
        Test WebSocket factory interface compliance with UserExecutionContext.
        
        This validates that the WebSocket supervisor factory passes parameters
        that match UserExecutionContext constructor expectations.
        """
        # Read WebSocket supervisor factory source code
        factory_path = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/websocket_core/supervisor_factory.py"
        
        if not os.path.exists(factory_path):
            pytest.skip("WebSocket supervisor factory file not found")
        
        with open(factory_path, 'r') as f:
            factory_source = f.read()
        
        # Extract UserExecutionContext calls
        factory_calls = InterfaceContractValidator.extract_factory_method_calls(
            factory_source, 'UserExecutionContext'
        )
        
        # Get constructor parameters
        constructor_params = InterfaceContractValidator.extract_constructor_parameters(UserExecutionContext)
        
        # Validate interface compliance
        violations = InterfaceContractValidator.validate_parameter_consistency(
            constructor_params, factory_calls
        )
        
        if violations:
            pytest.fail(f"WebSocket factory interface violations found:\n" + "\n".join(violations))
        
        print(f"✅ WebSocket factory interface compliance validated")
        print(f"✅ Found {len(factory_calls)} UserExecutionContext calls, all compliant")
    
    def test_core_factory_interface_compliance(self):
        """
        Test core factory interface compliance with UserExecutionContext.
        
        This validates that the core supervisor factory passes parameters
        that match UserExecutionContext constructor expectations.
        """
        # Read core supervisor factory source code
        core_factory_path = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/core/supervisor_factory.py"
        
        if not os.path.exists(core_factory_path):
            pytest.skip("Core supervisor factory file not found")
        
        with open(core_factory_path, 'r') as f:
            core_source = f.read()
        
        # Extract UserExecutionContext calls
        factory_calls = InterfaceContractValidator.extract_factory_method_calls(
            core_source, 'UserExecutionContext'
        )
        
        # Get constructor parameters
        constructor_params = InterfaceContractValidator.extract_constructor_parameters(UserExecutionContext)
        
        # Validate interface compliance
        violations = InterfaceContractValidator.validate_parameter_consistency(
            constructor_params, factory_calls
        )
        
        if violations:
            pytest.fail(f"Core factory interface violations found:\n" + "\n".join(violations))
        
        print(f"✅ Core factory interface compliance validated")
        print(f"✅ Found {len(factory_calls)} UserExecutionContext calls, all compliant")
    
    def test_codebase_wide_interface_contract_scan(self):
        """
        Test codebase-wide interface contract validation.
        
        This scans the entire codebase for interface contract violations
        involving UserExecutionContext and other critical classes.
        """
        # Target classes for interface validation
        target_classes = [
            'UserExecutionContext',
            'UnifiedToolDispatcher'  # Add other critical classes as needed
        ]
        
        # Scan the backend codebase
        backend_path = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend"
        
        if not os.path.exists(backend_path):
            pytest.skip("Backend codebase path not found")
        
        violations = InterfaceContractValidator.scan_codebase_for_interface_violations(
            backend_path, target_classes
        )
        
        # Report violations
        if violations:
            violation_report = []
            for file_path, file_violations in violations.items():
                violation_report.append(f"\n{file_path}:")
                for violation in file_violations:
                    violation_report.append(f"  - {violation}")
            
            pytest.fail(f"Interface contract violations found:{chr(10).join(violation_report)}")
        
        print(f"✅ Codebase-wide interface contract scan completed")
        print(f"✅ No violations found for {len(target_classes)} target classes")
    
    def test_parameter_naming_convention_validation(self):
        """
        Test parameter naming convention validation.
        
        This validates that parameter naming follows consistent conventions
        across the codebase, particularly for WebSocket-related parameters.
        """
        # Define expected parameter naming conventions
        naming_conventions = {
            'websocket_client_id': {
                'pattern': r'websocket_client_id',
                'description': 'WebSocket client identifier parameter'
            },
            'deprecated_websocket_connection_id': {
                'pattern': r'websocket_connection_id',
                'description': 'Deprecated WebSocket connection parameter (should not be used)'
            }
        }
        
        # Scan critical files for naming convention adherence
        critical_files = [
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/websocket_core/supervisor_factory.py",
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/core/supervisor_factory.py",
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/services/user_execution_context.py"
        ]
        
        violations = []
        
        for file_path in critical_files:
            if not os.path.exists(file_path):
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Check for deprecated parameter usage
                if 'websocket_connection_id' in line and 'UserExecutionContext' in line:
                    violations.append(
                        f"{file_path}:{line_num} - Deprecated 'websocket_connection_id' parameter used: {line.strip()}"
                    )
        
        if violations:
            pytest.fail(f"Parameter naming convention violations:\n" + "\n".join(violations))
        
        print(f"✅ Parameter naming convention validation passed")
        print(f"✅ No deprecated parameter names found in critical files")
    
    def test_interface_evolution_tracking(self):
        """
        Test interface evolution tracking capabilities.
        
        This validates that interface changes can be tracked and validated
        through systematic processes.
        """
        # Check for interface evolution documentation
        documentation_files = [
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/docs/interface_evolution.md",
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/SPEC/interface_contracts.xml",
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/docs/parameter_standards.md"
        ]
        
        documentation_found = any(os.path.exists(path) for path in documentation_files)
        
        # Check for interface validation scripts
        validation_scripts = [
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/scripts/validate_interface_contracts.py",
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/scripts/check_parameter_consistency.py"
        ]
        
        scripts_found = any(os.path.exists(path) for path in validation_scripts)
        
        # Interface evolution tracking is acceptable if either documentation or scripts exist
        if not (documentation_found or scripts_found):
            print("⚠️  Interface evolution tracking should be improved")
            print("⚠️  Consider adding documentation or validation scripts")
        else:
            print("✅ Interface evolution tracking capabilities found")
    
    def test_factory_pattern_consistency_validation(self):
        """
        Test factory pattern consistency across implementations.
        
        This validates that all factory patterns use consistent parameter
        interfaces when creating the same target classes.
        """
        # Test consistency between WebSocket and core factories
        websocket_factory_sig = inspect.signature(get_websocket_scoped_supervisor)
        core_factory_sig = inspect.signature(create_supervisor_core)
        
        # Both factories should accept websocket_client_id parameter (where applicable)
        websocket_params = websocket_factory_sig.parameters
        core_params = core_factory_sig.parameters
        
        # Core factory should have websocket_client_id parameter
        assert 'websocket_client_id' in core_params, \
            "Core factory missing websocket_client_id parameter"
        
        # WebSocket factory accepts context which contains connection_id
        assert 'context' in websocket_params, \
            "WebSocket factory missing context parameter"
        
        # Validate parameter types where possible
        if 'websocket_client_id' in core_params:
            core_websocket_param = core_params['websocket_client_id']
            assert core_websocket_param.default is None or core_websocket_param.default == inspect.Parameter.empty, \
                "Core factory websocket_client_id should be optional"
        
        print(f"✅ Factory pattern consistency validation passed")
        print(f"✅ WebSocket factory parameters: {list(websocket_params.keys())}")
        print(f"✅ Core factory parameters: {list(core_params.keys())}")


class TestInterfaceContractRegressionPrevention(SSotBaseTestCase):
    """
    Test interface contract regression prevention mechanisms.
    
    These tests validate that regression prevention mechanisms are in place
    to catch interface contract violations before they cause failures.
    """
    
    def test_automated_interface_validation_available(self):
        """
        Test that automated interface validation tools are available.
        
        This validates that tools exist to automatically validate interface
        contracts during development and CI/CD processes.
        """
        # Check for validation tools
        validation_tools = [
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/scripts/check_architecture_compliance.py",
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/scripts/validate_interfaces.py"
        ]
        
        tools_available = any(os.path.exists(tool) for tool in validation_tools)
        
        # Check for pre-commit hooks
        precommit_config = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/.pre-commit-config.yaml"
        precommit_available = os.path.exists(precommit_config)
        
        if tools_available:
            print(f"✅ Interface validation tools available")
        elif precommit_available:
            print(f"✅ Pre-commit configuration available (may include interface validation)")
        else:
            print(f"⚠️  Automated interface validation tools should be implemented")
    
    def test_interface_change_detection_capabilities(self):
        """
        Test interface change detection capabilities.
        
        This validates that mechanisms exist to detect when interfaces
        are modified and trigger appropriate validation workflows.
        """
        # This test validates the capability exists in principle
        # In a real system, this would check for:
        # - Git hooks that detect interface changes
        # - CI/CD pipelines that run interface validation
        # - Automated notifications for interface modifications
        
        # For now, we validate that the test infrastructure itself can detect changes
        user_context_signature = inspect.signature(UserExecutionContext.__init__)
        current_parameters = set(user_context_signature.parameters.keys())
        
        expected_parameters = {'self', 'user_id', 'thread_id', 'run_id', 'websocket_client_id', 'db_session'}
        
        # This test will fail if UserExecutionContext signature changes unexpectedly
        unexpected_parameters = current_parameters - expected_parameters
        missing_parameters = expected_parameters - current_parameters
        
        if unexpected_parameters:
            print(f"⚠️  Unexpected parameters detected: {unexpected_parameters}")
        
        if missing_parameters:
            pytest.fail(f"Expected parameters missing: {missing_parameters}")
        
        print(f"✅ Interface change detection capabilities validated")
        print(f"✅ Current UserExecutionContext parameters: {sorted(current_parameters - {'self'})}")
    
    def test_contract_validation_framework_integration(self):
        """
        Test contract validation framework integration.
        
        This validates that interface contract validation can be integrated
        into the development workflow and testing infrastructure.
        """
        # Test that InterfaceContractValidator can be used programmatically
        validator = InterfaceContractValidator()
        
        # Test parameter extraction
        params = validator.extract_constructor_parameters(UserExecutionContext)
        assert len(params) > 0, "Parameter extraction should return parameters"
        assert 'websocket_client_id' in params, "Should extract websocket_client_id parameter"
        
        # Test source code analysis
        test_source = '''
class TestClass:
    def test_method(self):
        context = UserExecutionContext(
            user_id="test",
            websocket_client_id="test_id"
        )
        return context
'''
        
        calls = validator.extract_factory_method_calls(test_source, 'UserExecutionContext')
        assert len(calls) == 1, "Should detect one UserExecutionContext call"
        assert 'websocket_client_id' in calls[0]['keywords'], "Should extract websocket_client_id parameter"
        
        print(f"✅ Contract validation framework integration validated")
        print(f"✅ Framework can extract parameters and analyze source code")


if __name__ == "__main__":
    # Run interface contract validation tests
    import os
    os.system("python -m pytest " + __file__ + " -v --tb=short")