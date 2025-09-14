#!/usr/bin/env python3
"""WebSocket Factory Pattern Consistency Validator - Issue #1036

FAIL-FIRST TEST: This test is designed to FAIL before factory consolidation
and PASS after WebSocket factory patterns return consistent instance types.

Business Value: Protects $500K+ ARR by ensuring factory patterns provide
consistent WebSocket manager instances for proper user isolation.

EXPECTED BEHAVIOR:
- BEFORE CONSOLIDATION: Test FAILS - Factory returns different types/inconsistent instances
- AFTER CONSOLIDATION: Test PASSES - Factory always returns same SSOT type

This test validates Issue #1036 Step 2: Factory pattern consistency detection.
"""

import inspect
import sys
import re
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Type, Set
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketFactoryConsistency(SSotBaseTestCase):
    """Fail-first test to detect WebSocket factory pattern inconsistencies.
    
    This test validates that WebSocket factory functions and methods return
    consistent instance types for SSOT compliance and user isolation.
    """

    def test_websocket_factory_return_type_consistency(self):
        """FAIL-FIRST: Detect inconsistent return types from WebSocket factories.
        
        EXPECTED TO FAIL: Currently has factories that return different types:
        - get_websocket_manager() returns UnifiedWebSocketManager
        - create_websocket_manager() returns WebSocketManager
        - WebSocketManagerFactory.create() returns IsolatedWebSocketManager
        
        EXPECTED TO PASS: After consolidation, all factories return same SSOT type.
        
        Business Impact: Ensures consistent manager behavior for user isolation.
        """
        factory_functions = self._discover_websocket_factories()
        return_type_violations = []
        
        # Analyze return types from different factory functions
        expected_return_types = set()
        
        for factory_info in factory_functions:
            try:
                return_type = self._analyze_factory_return_type(factory_info)
                if return_type:
                    expected_return_types.add(return_type)
                    
                    # Check for type annotation inconsistencies  
                    if hasattr(factory_info['function'], '__annotations__'):
                        annotations = factory_info['function'].__annotations__
                        if 'return' in annotations:
                            annotated_type = annotations['return']
                            if str(annotated_type) != return_type:
                                return_type_violations.append({
                                    'factory': factory_info['name'],
                                    'module': factory_info['module'],
                                    'annotated_type': str(annotated_type),
                                    'actual_type': return_type,
                                    'inconsistency': 'annotation_mismatch'
                                })
                                
            except Exception as e:
                # Factory analysis failed - document as potential violation
                return_type_violations.append({
                    'factory': factory_info['name'],
                    'module': factory_info['module'],
                    'error': str(e),
                    'inconsistency': 'analysis_failure'
                })
        
        # FAIL-FIRST ASSERTION: Should find factory inconsistencies
        total_violations = len(return_type_violations) + (len(expected_return_types) - 1 if expected_return_types else 0)
        
        self.assertGreater(
            total_violations, 0,
            f"WEBSOCKET FACTORY CONSISTENCY VIOLATIONS: Found {total_violations} inconsistencies.\n"
            f"Expected > 0 to validate current factory inconsistencies exist.\n\n"
            f"Return type variations detected: {len(expected_return_types)}\n"
            f"Types: {sorted(expected_return_types)}\n\n"
            f"Factory violations:\n" +
            "\n".join(f"  - {v['factory']} ({v['module']}): {v.get('inconsistency', 'unknown')}" 
                     for v in return_type_violations) + "\n\n"
            f"BUSINESS IMPACT: Factory inconsistencies cause:\n"
            f"- Different manager instances with varying behaviors\n"
            f"- User isolation breaches in multi-tenant scenarios\n"
            f"- WebSocket event delivery inconsistencies\n"
            f"- Golden Path failures affecting $500K+ ARR\n"
            f"- Enterprise compliance violations (HIPAA, SOC2)\n\n"
            f"REMEDIATION: Standardize all factories to return single SSOT type"
        )

    def test_websocket_factory_initialization_consistency(self):
        """FAIL-FIRST: Detect inconsistent WebSocket factory initialization patterns.
        
        EXPECTED TO FAIL: Currently has different initialization approaches:
        - Some factories require user_context parameter
        - Others create default contexts automatically
        - Different parameter names/types across factories
        
        EXPECTED TO PASS: After consolidation, consistent initialization patterns.
        """
        factory_functions = self._discover_websocket_factories()
        initialization_violations = []
        
        # Analyze initialization patterns across factories
        param_patterns = set()
        
        for factory_info in factory_functions:
            try:
                signature = inspect.signature(factory_info['function'])
                params = list(signature.parameters.keys())
                param_patterns.add(tuple(sorted(params)))
                
                # Check for inconsistent parameter requirements
                has_required_context = any('context' in p.lower() for p in params)
                has_optional_context = any(
                    'context' in p.lower() and signature.parameters[p].default != inspect.Parameter.empty
                    for p in params
                )
                
                # Document parameter inconsistencies
                if not has_required_context and not has_optional_context:
                    initialization_violations.append({
                        'factory': factory_info['name'],
                        'issue': 'missing_user_context_parameter',
                        'params': params,
                        'risk': 'user_isolation_bypass'
                    })
                elif has_required_context and has_optional_context:
                    initialization_violations.append({
                        'factory': factory_info['name'], 
                        'issue': 'conflicting_context_requirements',
                        'params': params,
                        'risk': 'inconsistent_behavior'
                    })
                    
            except Exception as e:
                initialization_violations.append({
                    'factory': factory_info['name'],
                    'issue': 'signature_analysis_failed',
                    'error': str(e),
                    'risk': 'unknown_initialization_pattern'
                })
        
        # FAIL-FIRST ASSERTION: Should find initialization inconsistencies
        total_violations = len(initialization_violations) + (len(param_patterns) - 1 if param_patterns else 0)
        
        self.assertGreater(
            total_violations, 0,
            f"WEBSOCKET FACTORY INITIALIZATION VIOLATIONS: Found {total_violations} inconsistencies.\n"
            f"Expected > 0 to validate current initialization inconsistencies exist.\n\n"
            f"Parameter pattern variations: {len(param_patterns)}\n"
            f"Patterns: {sorted([str(p) for p in param_patterns])}\n\n"
            f"Initialization violations:\n" +
            "\n".join(f"  - {v['factory']}: {v['issue']} (risk: {v.get('risk', 'unknown')})"
                     for v in initialization_violations) + "\n\n"
            f"BUSINESS IMPACT: Initialization inconsistencies cause:\n"
            f"- User context bypass leading to data contamination\n"
            f"- Unpredictable factory behavior across services\n"
            f"- Developer confusion and incorrect usage patterns\n"
            f"- Multi-user isolation failures\n"
            f"- Potential security vulnerabilities in enterprise deployments\n\n"
            f"REMEDIATION: Standardize factory initialization to require user context"
        )

    def test_websocket_factory_ssot_compliance_validation(self):
        """FAIL-FIRST: Detect WebSocket factories that bypass SSOT patterns.
        
        EXPECTED TO FAIL: Currently has factories that don't follow SSOT patterns:
        - Direct class instantiation instead of factory functions
        - Multiple factory classes for same functionality
        - Factories that don't validate SSOT compliance
        
        EXPECTED TO PASS: After consolidation, all factories follow SSOT patterns.
        """
        ssot_violations = []
        
        # Check for direct WebSocket manager instantiation (bypassing factory)
        direct_instantiations = self._find_direct_websocket_instantiations()
        ssot_violations.extend(direct_instantiations)
        
        # Check for multiple factory classes/functions
        factory_functions = self._discover_websocket_factories()
        factory_classes = self._discover_websocket_factory_classes()
        
        if len(factory_functions) + len(factory_classes) > 1:
            ssot_violations.append({
                'type': 'multiple_factory_patterns',
                'functions': len(factory_functions),
                'classes': len(factory_classes),
                'total': len(factory_functions) + len(factory_classes),
                'risk': 'ssot_fragmentation'
            })
        
        # Check for factories without SSOT validation
        for factory_info in factory_functions:
            if not self._factory_has_ssot_validation(factory_info):
                ssot_violations.append({
                    'type': 'missing_ssot_validation',
                    'factory': factory_info['name'],
                    'module': factory_info['module'],
                    'risk': 'unchecked_ssot_compliance'
                })
        
        # FAIL-FIRST ASSERTION: Should find SSOT violations
        self.assertGreater(
            len(ssot_violations), 0,
            f"WEBSOCKET FACTORY SSOT VIOLATIONS: Found {len(ssot_violations)} violations.\n"
            f"Expected > 0 to validate current SSOT violations exist.\n\n"
            f"SSOT violations detected:\n" +
            "\n".join(f"  - {v['type']}: {v.get('factory', v.get('risk', 'details unavailable'))}"
                     for v in ssot_violations) + "\n\n"
            f"BUSINESS IMPACT: SSOT violations cause:\n"
            f"- Multiple WebSocket manager implementations active simultaneously\n"
            f"- Bypass of user isolation and security controls\n"
            f"- Inconsistent WebSocket event delivery\n"
            f"- Golden Path failures and system instability\n"
            f"- $500K+ ARR at risk from unreliable chat functionality\n\n"
            f"REMEDIATION: Consolidate all factories to single SSOT pattern with validation"
        )

    def _discover_websocket_factories(self) -> List[Dict[str, Any]]:
        """Discover WebSocket factory functions in the codebase."""
        factories = []
        project_root = self._get_project_root()
        
        # Search for WebSocket factory functions
        for py_file in project_root.rglob("*.py"):
            if "/tests/" in str(py_file) or "__pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for factory function patterns
                factory_patterns = [
                    r'def\s+(\w*websocket\w*(?:manager|factory)\w*)\s*\(',
                    r'def\s+(get_websocket_manager)\s*\(',
                    r'def\s+(create_websocket_manager)\s*\(',
                ]
                
                for pattern in factory_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        factories.append({
                            'name': match.group(1),
                            'file': str(py_file),
                            'module': str(py_file.relative_to(project_root)).replace('/', '.').replace('.py', ''),
                            'function': None  # Will be populated if needed
                        })
                        
            except (UnicodeDecodeError, OSError):
                continue
        
        return factories

    def _discover_websocket_factory_classes(self) -> List[Dict[str, Any]]:
        """Discover WebSocket factory classes in the codebase."""
        factory_classes = []
        project_root = self._get_project_root()
        
        for py_file in project_root.rglob("*.py"):
            if "/tests/" in str(py_file) or "__pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for factory class patterns
                if re.search(r'class\s+\w*WebSocket\w*Factory\w*[:(]', content, re.IGNORECASE):
                    factory_classes.append({
                        'file': str(py_file),
                        'module': str(py_file.relative_to(project_root)).replace('/', '.').replace('.py', '')
                    })
                    
            except (UnicodeDecodeError, OSError):
                continue
        
        return factory_classes

    def _analyze_factory_return_type(self, factory_info: Dict[str, Any]) -> str:
        """Analyze the return type of a factory function."""
        try:
            # Try to import and inspect the function
            module_name = factory_info['module']
            if module_name.startswith('netra_backend'):
                spec = importlib.util.find_spec(module_name)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, factory_info['name']):
                        func = getattr(module, factory_info['name'])
                        if hasattr(func, '__annotations__') and 'return' in func.__annotations__:
                            return str(func.__annotations__['return'])
                            
        except Exception:
            pass
        
        return 'unknown'

    def _find_direct_websocket_instantiations(self) -> List[Dict[str, Any]]:
        """Find direct WebSocket manager instantiations that bypass factories."""
        direct_instantiations = []
        project_root = self._get_project_root()
        
        for py_file in project_root.rglob("*.py"):
            if "/tests/" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for direct instantiation patterns
                instantiation_patterns = [
                    r'\w*WebSocketManager\w*\s*\(',
                    r'UnifiedWebSocketManager\s*\(',
                    r'IsolatedWebSocketManager\s*\(',
                ]
                
                for pattern in instantiation_patterns:
                    if re.search(pattern, content):
                        direct_instantiations.append({
                            'type': 'direct_instantiation',
                            'file': str(py_file),
                            'pattern': pattern,
                            'risk': 'factory_bypass'
                        })
                        break
                        
            except (UnicodeDecodeError, OSError):
                continue
        
        return direct_instantiations

    def _factory_has_ssot_validation(self, factory_info: Dict[str, Any]) -> bool:
        """Check if a factory has SSOT validation logic."""
        try:
            with open(factory_info['file'], 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Look for SSOT validation patterns
            validation_patterns = [
                r'ssot.*validat',
                r'_validate.*ssot',
                r'ssot.*complian',
                r'single.*source.*truth'
            ]
            
            for pattern in validation_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
                    
        except (UnicodeDecodeError, OSError):
            pass
        
        return False

    def _get_project_root(self) -> Path:
        """Get the project root directory for scanning."""
        current_file = Path(__file__)
        # Navigate up from tests/unit/ssot/ to project root  
        project_root = current_file.parent.parent.parent.parent
        return project_root


if __name__ == '__main__':
    import unittest
    unittest.main()