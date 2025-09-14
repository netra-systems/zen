"""
CRITICAL SSOT Test 2: MessageRouter Implementation Detection - Issue #1101

PURPOSE: Detect and validate ALL MessageRouter implementation patterns across the codebase.
These tests SHOULD FAIL before remediation and PASS after consolidation.

VIOLATION: Multiple MessageRouter implementations scattered across modules:
- DEPRECATED: /netra_backend/app/core/message_router.py (standalone implementation)
- COMPATIBILITY: /netra_backend/app/services/message_router.py (re-export compatibility)
- COMPATIBILITY: /netra_backend/app/agents/message_router.py (re-export compatibility)  
- CANONICAL: /netra_backend/app/websocket_core/handlers.py (target SSOT implementation)

BUSINESS IMPACT: $500K+ ARR Golden Path failures due to:
- Routing conflicts when multiple routers active simultaneously
- Inconsistent message handling across different implementations
- Race conditions in multi-user scenarios

TEST STRATEGY: 20% of MessageRouter SSOT testing strategy focused on implementation detection
"""

import unittest
import importlib
import inspect
import ast
import os
from typing import Set, List, Dict, Any, Tuple
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMessageRouterImplementationDetection(SSotBaseTestCase):
    """Test that detects ALL MessageRouter implementations in the codebase."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.expected_ssot_module = "netra_backend.app.websocket_core.handlers"
        self.deprecated_modules = [
            "netra_backend.app.core.message_router",
        ]
        self.compatibility_modules = [
            "netra_backend.app.services.message_router",
            "netra_backend.app.agents.message_router"
        ]
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    def test_detect_all_message_router_class_definitions(self):
        """
        CRITICAL: Detect ALL MessageRouter class definitions across codebase.
        
        SHOULD FAIL: Currently finds multiple class definitions
        WILL PASS: After consolidation finds only 1 SSOT class definition
        
        Business Impact: Multiple class definitions cause routing conflicts
        """
        message_router_definitions = []
        
        # Check known modules for class definitions
        modules_to_check = [
            self.expected_ssot_module,
            *self.deprecated_modules,
            *self.compatibility_modules
        ]
        
        for module_path in modules_to_check:
            try:
                module = importlib.import_module(module_path)
                module_file = inspect.getfile(module)
                
                # Parse the module to find class definitions
                with open(module_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=module_file)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == 'MessageRouter':
                        message_router_definitions.append({
                            'module': module_path,
                            'file': module_file,
                            'line': node.lineno,
                            'class_name': node.name
                        })
                        
            except (ImportError, FileNotFoundError, SyntaxError) as e:
                # Module might not exist or be accessible
                continue
        
        # CRITICAL: Should find exactly 1 class definition after SSOT consolidation
        self.assertEqual(
            len(message_router_definitions), 1,
            f"SSOT VIOLATION: Found {len(message_router_definitions)} MessageRouter class definitions: "
            f"{message_router_definitions}. Expected exactly 1 SSOT class definition in {self.expected_ssot_module}."
        )
        
        # Verify the single definition is in the expected SSOT module
        if message_router_definitions:
            ssot_definition = message_router_definitions[0]
            self.assertEqual(
                ssot_definition['module'], self.expected_ssot_module,
                f"SSOT VIOLATION: MessageRouter class definition found in {ssot_definition['module']}, "
                f"but expected in {self.expected_ssot_module}"
            )

    def test_detect_re_export_vs_implementation_patterns(self):
        """
        CRITICAL: Distinguish between re-exports and actual implementations.
        
        SHOULD FAIL: Currently has both re-exports and standalone implementations
        WILL PASS: After consolidation has only re-exports pointing to SSOT
        
        Business Impact: Standalone implementations create routing conflicts
        """
        implementation_analysis = {}
        
        modules_to_analyze = [
            self.expected_ssot_module,
            *self.deprecated_modules,
            *self.compatibility_modules
        ]
        
        for module_path in modules_to_analyze:
            try:
                module = importlib.import_module(module_path)
                module_file = inspect.getfile(module)
                
                with open(module_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content, filename=module_file)
                
                # Check for class definitions (implementations)
                has_class_def = any(
                    isinstance(node, ast.ClassDef) and node.name == 'MessageRouter'
                    for node in ast.walk(tree)
                )
                
                # Check for imports (re-exports)
                has_import = any(
                    (isinstance(node, ast.ImportFrom) and 
                     hasattr(node, 'names') and 
                     any(alias.name == 'MessageRouter' for alias in node.names if alias.name))
                    for node in ast.walk(tree)
                )
                
                implementation_analysis[module_path] = {
                    'has_class_definition': has_class_def,
                    'has_import': has_import,
                    'pattern': 'implementation' if has_class_def else 'reexport' if has_import else 'none'
                }
                
            except (ImportError, FileNotFoundError, SyntaxError):
                continue
        
        # Count standalone implementations (should be 1 after SSOT)
        standalone_implementations = [
            module for module, analysis in implementation_analysis.items()
            if analysis['pattern'] == 'implementation'
        ]
        
        # Count re-exports (compatibility layers are OK)
        reexports = [
            module for module, analysis in implementation_analysis.items()
            if analysis['pattern'] == 'reexport'
        ]
        
        # CRITICAL: Should have exactly 1 implementation, rest should be re-exports
        self.assertEqual(
            len(standalone_implementations), 1,
            f"SSOT VIOLATION: Found {len(standalone_implementations)} standalone implementations: "
            f"{standalone_implementations}. Expected exactly 1 in {self.expected_ssot_module}."
        )
        
        # Verify the implementation is in the SSOT module
        if standalone_implementations:
            self.assertIn(
                self.expected_ssot_module, standalone_implementations,
                f"SSOT VIOLATION: Implementation found in {standalone_implementations}, "
                f"but expected in {self.expected_ssot_module}"
            )

    def test_detect_deprecated_implementation_usage(self):
        """
        CRITICAL: Detect usage of deprecated implementations in production code.
        
        SHOULD FAIL: Currently production code uses deprecated implementations
        WILL PASS: After migration all production code uses SSOT imports
        
        Business Impact: Deprecated implementations lack latest features/fixes
        """
        deprecated_usage_found = []
        
        # Check if deprecated modules are still being used as primary implementations
        for deprecated_module in self.deprecated_modules:
            try:
                module = importlib.import_module(deprecated_module)
                
                # If we can import MessageRouter from deprecated module and it's not a re-export
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    
                    # Check if this is a standalone implementation (not re-export)
                    if router_class.__module__ == deprecated_module:
                        deprecated_usage_found.append({
                            'module': deprecated_module,
                            'class_module': router_class.__module__,
                            'type': 'standalone_implementation'
                        })
                        
            except ImportError:
                # Module doesn't exist - that's actually good for deprecated modules
                continue
        
        # CRITICAL: No deprecated standalone implementations should exist
        self.assertEqual(
            len(deprecated_usage_found), 0,
            f"SSOT VIOLATION: Found {len(deprecated_usage_found)} deprecated implementations still active: "
            f"{deprecated_usage_found}. All deprecated modules should be removed or converted to re-exports."
        )

    def test_validate_compatibility_layers_point_to_ssot(self):
        """
        CRITICAL: Validate compatibility layers correctly point to SSOT implementation.
        
        SHOULD FAIL: Initially compatibility layers might point to deprecated implementations
        WILL PASS: After migration all compatibility layers point to SSOT
        
        Business Impact: Incorrect compatibility layers cause routing to wrong implementation
        """
        compatibility_validation = {}
        
        for compat_module in self.compatibility_modules:
            try:
                module = importlib.import_module(compat_module)
                
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    
                    # Check where this router class actually comes from
                    actual_source_module = router_class.__module__
                    
                    compatibility_validation[compat_module] = {
                        'points_to': actual_source_module,
                        'correct_ssot': actual_source_module == self.expected_ssot_module,
                        'is_reexport': actual_source_module != compat_module
                    }
                    
            except ImportError:
                # Compatibility module doesn't exist
                compatibility_validation[compat_module] = {
                    'points_to': None,
                    'correct_ssot': False,
                    'is_reexport': False
                }
        
        # CRITICAL: All compatibility layers should point to SSOT
        incorrect_compatibility = []
        for compat_module, validation in compatibility_validation.items():
            if not validation['correct_ssot']:
                incorrect_compatibility.append({
                    'module': compat_module,
                    'points_to': validation['points_to'],
                    'expected': self.expected_ssot_module
                })
        
        self.assertEqual(
            len(incorrect_compatibility), 0,
            f"SSOT VIOLATION: Found {len(incorrect_compatibility)} compatibility layers pointing to wrong implementations: "
            f"{incorrect_compatibility}. All should point to {self.expected_ssot_module}."
        )

    def test_detect_implementation_feature_parity(self):
        """
        CRITICAL: Ensure SSOT implementation has all features from other implementations.
        
        SHOULD FAIL: Initially SSOT might be missing features from other implementations
        WILL PASS: After consolidation SSOT has all required features
        
        Business Impact: Missing features cause functionality regressions
        """
        feature_analysis = {}
        
        # Get methods from all implementations
        all_modules = [self.expected_ssot_module, *self.deprecated_modules]
        
        for module_path in all_modules:
            try:
                module = importlib.import_module(module_path)
                
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    
                    # Get public methods (features)
                    methods = [
                        method for method in dir(router_class)
                        if not method.startswith('_') and callable(getattr(router_class, method))
                    ]
                    
                    feature_analysis[module_path] = {
                        'class': router_class,
                        'methods': methods,
                        'method_count': len(methods)
                    }
                    
            except ImportError:
                continue
        
        if len(feature_analysis) > 1:
            ssot_methods = set(feature_analysis.get(self.expected_ssot_module, {}).get('methods', []))
            
            # Check if SSOT has all methods from other implementations
            missing_features = []
            for module_path, analysis in feature_analysis.items():
                if module_path != self.expected_ssot_module:
                    other_methods = set(analysis['methods'])
                    missing_in_ssot = other_methods - ssot_methods
                    
                    if missing_in_ssot:
                        missing_features.extend([
                            {'method': method, 'from_module': module_path}
                            for method in missing_in_ssot
                        ])
            
            # CRITICAL: SSOT should have all features from other implementations
            self.assertEqual(
                len(missing_features), 0,
                f"SSOT VIOLATION: SSOT implementation missing {len(missing_features)} features: "
                f"{missing_features}. SSOT should have ALL features from consolidated implementations."
            )


class TestMessageRouterImplementationConflictDetection(SSotBaseTestCase):
    """Test for detecting conflicts between different implementations."""

    def test_detect_method_signature_conflicts(self):
        """
        CRITICAL: Detect method signature differences between implementations.
        
        SHOULD FAIL: Different implementations have conflicting method signatures  
        WILL PASS: After consolidation single implementation has consistent signatures
        
        Business Impact: Signature conflicts cause runtime errors in multi-user scenarios
        """
        signature_analysis = {}
        
        modules_to_check = [
            "netra_backend.app.websocket_core.handlers",
            "netra_backend.app.core.message_router"
        ]
        
        common_methods = ['__init__', 'route_message'] # Methods expected in all implementations
        
        for module_path in modules_to_check:
            try:
                module = importlib.import_module(module_path)
                
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    
                    method_signatures = {}
                    for method_name in common_methods:
                        if hasattr(router_class, method_name):
                            method = getattr(router_class, method_name)
                            if callable(method):
                                try:
                                    sig = inspect.signature(method)
                                    method_signatures[method_name] = str(sig)
                                except (ValueError, TypeError):
                                    method_signatures[method_name] = 'signature_unavailable'
                    
                    signature_analysis[module_path] = method_signatures
                    
            except ImportError:
                continue
        
        # Check for signature conflicts
        signature_conflicts = []
        if len(signature_analysis) > 1:
            method_names = set()
            for analysis in signature_analysis.values():
                method_names.update(analysis.keys())
            
            for method_name in method_names:
                signatures = []
                for module_path, analysis in signature_analysis.items():
                    if method_name in analysis:
                        signatures.append((module_path, analysis[method_name]))
                
                # Check if all signatures for this method are the same
                if len(set(sig[1] for sig in signatures)) > 1:
                    signature_conflicts.append({
                        'method': method_name,
                        'conflicts': signatures
                    })
        
        # CRITICAL: No signature conflicts should exist after consolidation
        self.assertEqual(
            len(signature_conflicts), 0,
            f"SSOT VIOLATION: Found {len(signature_conflicts)} method signature conflicts: "
            f"{signature_conflicts}. All implementations should have consistent signatures."
        )

    def test_detect_initialization_parameter_conflicts(self):
        """
        CRITICAL: Detect initialization parameter differences.
        
        SHOULD FAIL: Different implementations require different initialization parameters
        WILL PASS: After consolidation single implementation has consistent initialization
        
        Business Impact: Parameter conflicts cause factory initialization failures
        """
        init_analysis = {}
        
        modules_to_check = [
            "netra_backend.app.websocket_core.handlers",
            "netra_backend.app.core.message_router"
        ]
        
        for module_path in modules_to_check:
            try:
                module = importlib.import_module(module_path)
                
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    
                    try:
                        init_signature = inspect.signature(router_class.__init__)
                        init_analysis[module_path] = {
                            'signature': str(init_signature),
                            'param_count': len(init_signature.parameters) - 1,  # Exclude 'self'
                            'params': list(init_signature.parameters.keys())[1:]  # Exclude 'self'
                        }
                    except (ValueError, TypeError):
                        init_analysis[module_path] = {
                            'signature': 'unavailable',
                            'param_count': 0,
                            'params': []
                        }
                        
            except ImportError:
                continue
        
        # Check for initialization conflicts
        if len(init_analysis) > 1:
            signatures = [analysis['signature'] for analysis in init_analysis.values()]
            param_counts = [analysis['param_count'] for analysis in init_analysis.values()]
            
            # Check signature consistency
            unique_signatures = set(signatures)
            unique_param_counts = set(param_counts)
            
            # CRITICAL: All implementations should have same initialization signature
            self.assertEqual(
                len(unique_signatures), 1,
                f"SSOT VIOLATION: Found {len(unique_signatures)} different initialization signatures: "
                f"{dict(zip(init_analysis.keys(), signatures))}. All should be consistent."
            )
            
            self.assertEqual(
                len(unique_param_counts), 1,
                f"SSOT VIOLATION: Found {len(unique_param_counts)} different parameter counts: "
                f"{dict(zip(init_analysis.keys(), param_counts))}. All should be consistent."
            )


if __name__ == '__main__':
    unittest.main()