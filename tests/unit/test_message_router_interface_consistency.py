"""Test 2: MessageRouter Interface Consistency Validation

This test validates that all MessageRouter-like classes have consistent interfaces
to prevent API incompatibility issues that break chat functionality.

Business Value: Platform/Internal - API Consistency & Golden Path Protection
- Prevents interface drift between different router implementations
- Ensures consistent behavior across WebSocket message handling
- Protects chat functionality from method signature mismatches

EXPECTED BEHAVIOR:
- FAIL initially: Incompatible APIs between different MessageRouter implementations
- PASS after interface standardization: All routers implement consistent interface

GitHub Issue: #217 - MessageRouter SSOT violations blocking golden path
"""

import inspect
import ast
import unittest
from typing import Dict, List, Set, Optional, Any, Union
from pathlib import Path
import importlib.util
import sys

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMessageRouterInterfaceConsistency(SSotBaseTestCase, unittest.TestCase):
    """Test interface consistency across MessageRouter implementations."""

    def setUp(self):
        """Set up test fixtures."""
        if hasattr(super(), 'setUp'):
            super().setUp()
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)
        
        # Expected canonical interface signature
        self.canonical_interface = {
            '__init__': {
                'required': True,
                'params': ['self'],
                'description': 'Initialize router with default handlers'
            },
            'add_handler': {
                'required': True, 
                'params': ['self', 'handler'],
                'description': 'Add custom message handler to router'
            },
            'route_message': {
                'required': True,
                'params': ['self', 'websocket', 'message', 'user_context'],
                'description': 'Route incoming message to appropriate handler'
            },
            'handlers': {
                'required': True,
                'type': 'property_or_method',
                'description': 'Get all registered handlers'
            },
            'routing_stats': {
                'required': False,
                'type': 'property_or_method', 
                'description': 'Get routing statistics for monitoring'
            }
        }
        
        self.base_path = Path(__file__).parent.parent.parent
        self.interface_violations: List[Dict[str, Any]] = []

    def test_all_message_routers_implement_required_interface(self):
        """Test that all MessageRouter implementations have required methods.
        
        EXPECTED: FAIL initially - Missing methods in some implementations
        EXPECTED: PASS after standardization - All required methods present
        """
        router_implementations = self._discover_message_router_implementations()
        
        if not router_implementations:
            self.fail("No MessageRouter implementations found for interface validation")
        
        missing_interfaces = []
        
        for file_path, router_info in router_implementations.items():
            violations = self._validate_router_interface(file_path, router_info)
            if violations:
                missing_interfaces.append({
                    'file_path': self._relativize_path(file_path),
                    'class_name': router_info['class_name'],
                    'violations': violations
                })
        
        if missing_interfaces:
            violation_summary = self._format_interface_violations(missing_interfaces)
            self.fail(
                f"❌ INTERFACE CONSISTENCY VIOLATION: {len(missing_interfaces)} MessageRouter "
                f"implementations have incomplete interfaces.\n"
                f"BUSINESS IMPACT: Inconsistent interfaces cause method call failures, "
                f"WebSocket errors, and chat functionality breakdown.\n"
                f"INTERFACE VIOLATIONS:\n{violation_summary}"
            )
        
        self.logger.info(f"✅ All {len(router_implementations)} MessageRouter implementations have consistent interfaces")

    def test_method_signatures_are_compatible(self):
        """Test that method signatures across routers are compatible.
        
        EXPECTED: FAIL initially - Incompatible signatures between implementations
        EXPECTED: PASS after standardization - Compatible signatures across all routers
        """
        router_implementations = self._discover_message_router_implementations()
        signature_analysis = self._analyze_method_signatures(router_implementations)
        
        signature_mismatches = []
        
        for method_name, signatures in signature_analysis.items():
            if len(set(signatures.values())) > 1:  # Different signatures exist
                signature_mismatches.append({
                    'method': method_name,
                    'signatures': signatures
                })
        
        if signature_mismatches:
            mismatch_details = self._format_signature_mismatches(signature_mismatches)
            self.fail(
                f"❌ METHOD SIGNATURE MISMATCH: {len(signature_mismatches)} methods have "
                f"incompatible signatures across MessageRouter implementations.\n"
                f"BUSINESS IMPACT: Signature mismatches cause runtime TypeError exceptions "
                f"during message routing, breaking chat functionality.\n"
                f"SIGNATURE MISMATCHES:\n{mismatch_details}"
            )
        
        self.logger.info("✅ All method signatures are compatible across MessageRouter implementations")

    def test_return_types_are_consistent(self):
        """Test that method return types are consistent across implementations.
        
        EXPECTED: FAIL initially - Inconsistent return types between routers
        EXPECTED: PASS after standardization - Consistent return types
        """
        router_implementations = self._discover_message_router_implementations()
        return_type_analysis = self._analyze_return_types(router_implementations)
        
        inconsistent_returns = []
        
        for method_name, return_types in return_type_analysis.items():
            unique_types = set(return_types.values())
            if len(unique_types) > 1:
                inconsistent_returns.append({
                    'method': method_name,
                    'return_types': return_types
                })
        
        if inconsistent_returns:
            return_details = self._format_return_type_inconsistencies(inconsistent_returns)
            self.fail(
                f"❌ RETURN TYPE INCONSISTENCY: {len(inconsistent_returns)} methods have "
                f"different return types across MessageRouter implementations.\n"
                f"BUSINESS IMPACT: Inconsistent return types cause type errors and "
                f"unpredictable behavior in chat message processing.\n"
                f"RETURN TYPE INCONSISTENCIES:\n{return_details}"
            )
        
        self.logger.info("✅ All method return types are consistent")

    def test_required_properties_exist(self):
        """Test that required properties exist in all implementations.
        
        EXPECTED: FAIL initially - Missing properties in some implementations
        EXPECTED: PASS after standardization - All required properties present
        """
        router_implementations = self._discover_message_router_implementations()
        
        required_properties = ['handlers', 'routing_stats', 'fallback_handler']
        missing_properties = []
        
        for file_path, router_info in router_implementations.items():
            missing_props = self._check_required_properties(file_path, required_properties)
            if missing_props:
                missing_properties.append({
                    'file_path': self._relativize_path(file_path),
                    'class_name': router_info['class_name'],
                    'missing_properties': missing_props
                })
        
        if missing_properties:
            property_details = self._format_missing_properties(missing_properties)
            self.fail(
                f"❌ MISSING REQUIRED PROPERTIES: {len(missing_properties)} MessageRouter "
                f"implementations are missing required properties.\n"
                f"BUSINESS IMPACT: Missing properties cause AttributeError exceptions "
                f"during message routing operations.\n"
                f"MISSING PROPERTIES:\n{property_details}"
            )
        
        self.logger.info("✅ All required properties are present in all implementations")

    def _discover_message_router_implementations(self) -> Dict[str, Dict[str, Any]]:
        """Discover all MessageRouter implementations for interface analysis."""
        implementations = {}
        
        for py_file in self.base_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if 'class ' in content and 'MessageRouter' in content:
                    router_info = self._parse_router_interface(str(py_file))
                    if router_info:
                        implementations[str(py_file)] = router_info
                        
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return implementations

    def _parse_router_interface(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse MessageRouter class interface from a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and 'MessageRouter' in node.name:
                    methods = {}
                    properties = {}
                    
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            # Extract method signature
                            params = [arg.arg for arg in item.args.args]
                            methods[item.name] = {
                                'params': params,
                                'line_number': item.lineno,
                                'has_return': any(isinstance(n, ast.Return) for n in ast.walk(item))
                            }
                        elif isinstance(item, ast.Assign):
                            # Look for property assignments
                            for target in item.targets:
                                if isinstance(target, ast.Attribute):
                                    properties[target.attr] = item.lineno
                                elif isinstance(target, ast.Name):
                                    properties[target.id] = item.lineno
                    
                    return {
                        'class_name': node.name,
                        'methods': methods,
                        'properties': properties,
                        'line_number': node.lineno
                    }
                    
        except (SyntaxError, UnicodeDecodeError):
            return None
            
        return None

    def _validate_router_interface(self, file_path: str, router_info: Dict[str, Any]) -> List[str]:
        """Validate that a router implements the required interface."""
        violations = []
        methods = router_info.get('methods', {})
        
        for method_name, spec in self.canonical_interface.items():
            if spec['required'] and method_name not in methods:
                violations.append(f"Missing required method: {method_name}()")
            elif method_name in methods:
                # Check parameter count
                expected_params = spec.get('params', [])
                actual_params = methods[method_name].get('params', [])
                
                if len(actual_params) < len(expected_params):
                    violations.append(
                        f"Method {method_name}() has insufficient parameters: "
                        f"expected {expected_params}, got {actual_params}"
                    )
        
        return violations

    def _analyze_method_signatures(self, implementations: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
        """Analyze method signatures across all implementations."""
        signature_analysis = {}
        
        for file_path, router_info in implementations.items():
            methods = router_info.get('methods', {})
            class_name = router_info.get('class_name', 'Unknown')
            
            for method_name, method_info in methods.items():
                if method_name not in signature_analysis:
                    signature_analysis[method_name] = {}
                    
                params = method_info.get('params', [])
                signature = f"def {method_name}({', '.join(params)})"
                signature_analysis[method_name][f"{class_name} ({self._relativize_path(file_path)})"] = signature
        
        return signature_analysis

    def _analyze_return_types(self, implementations: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
        """Analyze method return type consistency."""
        return_analysis = {}
        
        for file_path, router_info in implementations.items():
            methods = router_info.get('methods', {})
            class_name = router_info.get('class_name', 'Unknown')
            
            for method_name, method_info in methods.items():
                if method_name not in return_analysis:
                    return_analysis[method_name] = {}
                    
                has_return = method_info.get('has_return', False)
                return_type = 'returns_value' if has_return else 'returns_none'
                return_analysis[method_name][f"{class_name} ({self._relativize_path(file_path)})"] = return_type
        
        return return_analysis

    def _check_required_properties(self, file_path: str, required_props: List[str]) -> List[str]:
        """Check if required properties exist in the router class."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            missing_props = []
            for prop in required_props:
                # Look for property definitions, assignments, or @property decorators
                if (f"self.{prop}" not in content and 
                    f"@property" not in content or f"def {prop}" not in content):
                    missing_props.append(prop)
                    
            return missing_props
            
        except (UnicodeDecodeError, PermissionError):
            return required_props  # Assume all missing if can't read

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if file should be skipped."""
        skip_patterns = [
            '__pycache__', '.git', '.pytest_cache', 'node_modules',
            '.venv', '.test_venv', 'venv'
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _relativize_path(self, file_path: str) -> str:
        """Convert absolute path to relative path for readability."""
        return file_path.replace(str(self.base_path), "").lstrip('/')

    def _format_interface_violations(self, violations: List[Dict[str, Any]]) -> str:
        """Format interface violations for clear error reporting."""
        formatted = []
        for i, violation in enumerate(violations, 1):
            formatted.append(
                f"{i}. {violation['file_path']} ({violation['class_name']})\n"
                f"   Violations: {', '.join(violation['violations'])}"
            )
        return "\n".join(formatted)

    def _format_signature_mismatches(self, mismatches: List[Dict[str, Any]]) -> str:
        """Format signature mismatches for clear error reporting."""
        formatted = []
        for mismatch in mismatches:
            method = mismatch['method']
            signatures = mismatch['signatures']
            formatted.append(f"\n{method}():")
            for impl, sig in signatures.items():
                formatted.append(f"  - {impl}: {sig}")
        return "\n".join(formatted)

    def _format_return_type_inconsistencies(self, inconsistencies: List[Dict[str, Any]]) -> str:
        """Format return type inconsistencies for error reporting."""
        formatted = []
        for inconsistency in inconsistencies:
            method = inconsistency['method']
            return_types = inconsistency['return_types']
            formatted.append(f"\n{method}():")
            for impl, ret_type in return_types.items():
                formatted.append(f"  - {impl}: {ret_type}")
        return "\n".join(formatted)

    def _format_missing_properties(self, missing: List[Dict[str, Any]]) -> str:
        """Format missing properties for error reporting."""
        formatted = []
        for i, item in enumerate(missing, 1):
            formatted.append(
                f"{i}. {item['file_path']} ({item['class_name']})\n"
                f"   Missing: {', '.join(item['missing_properties'])}"
            )
        return "\n".join(formatted)


if __name__ == "__main__":
    import unittest
    unittest.main()