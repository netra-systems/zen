"""
WebSocket Dual Pattern SSOT Violation Detection Test

PURPOSE: Detect multiple WebSocket factory patterns across dual directories
SHOULD FAIL: Because multiple factory implementations exist in dual directories (/websocket/ and /websocket_core/)
SHOULD PASS: When single SSOT factory pattern is implemented

Business Impact: $500K+ ARR chat functionality at risk from dual pattern confusion
GitHub Issue: #1144 - WebSocket Factory Dual Pattern Blocking Golden Path

This test validates that:
1. Only one canonical WebSocket manager implementation exists
2. No duplicate factory patterns across directories
3. All imports resolve to single SSOT implementation
4. Factory pattern follows enterprise user isolation standards
"""

import unittest
import os
import ast
import importlib.util
from pathlib import Path
from typing import List, Dict, Set, Tuple


class WebSocketDualPatternSSotViolationTest(unittest.TestCase):
    """
    Test to detect SSOT violations in WebSocket factory dual pattern.
    
    This test MUST FAIL with current dual pattern implementation to prove
    the violation exists. After SSOT remediation, it should PASS.
    """
    
    def setUp(self):
        """Set up test environment with WebSocket directory paths."""
        self.backend_root = Path(__file__).parent.parent.parent.parent / "netra_backend" / "app"
        self.websocket_legacy_dir = self.backend_root / "websocket"
        self.websocket_core_dir = self.backend_root / "websocket_core"
        
        # Expected violation patterns that should trigger failure
        self.violation_patterns = {
            'duplicate_managers': [],
            'dual_factory_imports': [],
            'inconsistent_patterns': [],
            'compatibility_shims': []
        }
    
    def test_websocket_manager_ssot_violation_detection(self):
        """
        CRITICAL: Test detecting multiple WebSocket manager implementations.
        
        This test MUST FAIL because:
        - /websocket/connection_manager.py contains compatibility shims
        - /websocket_core/manager.py contains re-export compatibility
        - /websocket_core/unified_manager.py contains actual implementation
        - Multiple manager classes exist across dual directories
        
        After SSOT fix, should PASS with single manager implementation.
        """
        # Discover all WebSocket manager classes
        manager_implementations = self._discover_websocket_managers()
        
        # VIOLATION CHECK: Multiple manager implementations
        print(f"\nDETECTED WEBSOCKET MANAGERS: {len(manager_implementations)}")
        for impl in manager_implementations:
            print(f"  - {impl['file']}: {impl['class_name']}")
        
        # This assertion SHOULD FAIL with current dual pattern
        # Expected failure: 3+ manager implementations found
        self.assertLessEqual(
            len(manager_implementations), 1,
            f"SSOT VIOLATION: Found {len(manager_implementations)} WebSocket manager implementations. "
            f"Expected 1 canonical implementation. Detected: {[impl['file'] for impl in manager_implementations]}"
        )
    
    def test_websocket_import_path_fragmentation_detection(self):
        """
        CRITICAL: Test detecting fragmented import paths across dual directories.
        
        This test MUST FAIL because:
        - Imports exist for both /websocket/ and /websocket_core/ paths
        - Multiple entry points for same functionality
        - Compatibility shims create import confusion
        
        After SSOT fix, should PASS with unified import paths.
        """
        # Discover all WebSocket import paths
        import_fragmentations = self._discover_websocket_import_paths()
        
        # VIOLATION CHECK: Multiple import paths for same functionality
        print(f"\nDETECTED IMPORT FRAGMENTATIONS: {len(import_fragmentations)}")
        for path_group in import_fragmentations:
            print(f"  - Functionality: {path_group['functionality']}")
            print(f"    Paths: {path_group['paths']}")
        
        # This assertion SHOULD FAIL with current dual pattern
        # Expected failure: Multiple import paths for manager functionality
        manager_paths = [fg for fg in import_fragmentations if 'manager' in fg['functionality'].lower()]
        self.assertLessEqual(
            len(manager_paths), 0,
            f"SSOT VIOLATION: Found {len(manager_paths)} different import paths for WebSocket manager functionality. "
            f"Expected single canonical path. Detected: {manager_paths}"
        )
    
    def test_compatibility_shim_dependency_violation(self):
        """
        CRITICAL: Test detecting compatibility shims indicating dual pattern.
        
        This test MUST FAIL because:
        - /websocket/connection_manager.py is a compatibility shim
        - Shims indicate incomplete migration to SSOT pattern
        - Multiple code paths for same functionality
        
        After SSOT fix, should PASS with no compatibility shims needed.
        """
        # Discover compatibility shims
        compatibility_shims = self._discover_compatibility_shims()
        
        # VIOLATION CHECK: Compatibility shims exist
        print(f"\nDETECTED COMPATIBILITY SHIMS: {len(compatibility_shims)}")
        for shim in compatibility_shims:
            print(f"  - {shim['file']}: {shim['purpose']}")
        
        # This assertion SHOULD FAIL with current compatibility shims
        # Expected failure: Compatibility shims found in /websocket/ directory
        self.assertEqual(
            len(compatibility_shims), 0,
            f"SSOT VIOLATION: Found {len(compatibility_shims)} compatibility shims indicating incomplete SSOT migration. "
            f"Shims detected: {[shim['file'] for shim in compatibility_shims]}"
        )
    
    def test_factory_pattern_consistency_violation(self):
        """
        CRITICAL: Test detecting inconsistent factory patterns across directories.
        
        This test MUST FAIL because:
        - Different factory implementations in dual directories
        - Inconsistent factory method signatures
        - Mixed singleton vs factory patterns
        
        After SSOT fix, should PASS with consistent factory pattern.
        """
        # Discover factory patterns
        factory_patterns = self._discover_factory_patterns()
        
        # VIOLATION CHECK: Inconsistent factory patterns
        print(f"\nDETECTED FACTORY PATTERNS: {len(factory_patterns)}")
        for pattern in factory_patterns:
            print(f"  - {pattern['file']}: {pattern['pattern_type']}")
        
        # This assertion SHOULD FAIL with current inconsistent patterns
        # Expected failure: Multiple different factory patterns detected
        unique_patterns = set(p['pattern_type'] for p in factory_patterns)
        self.assertLessEqual(
            len(unique_patterns), 1,
            f"SSOT VIOLATION: Found {len(unique_patterns)} different factory patterns. "
            f"Expected single consistent pattern. Detected: {list(unique_patterns)}"
        )
    
    def _discover_websocket_managers(self) -> List[Dict]:
        """Discover all WebSocket manager class implementations."""
        managers = []
        
        # Search both websocket directories
        for directory in [self.websocket_legacy_dir, self.websocket_core_dir]:
            if not directory.exists():
                continue
                
            for py_file in directory.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse AST to find manager classes
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            if 'manager' in node.name.lower() and 'websocket' in node.name.lower():
                                managers.append({
                                    'file': str(py_file.relative_to(self.backend_root)),
                                    'class_name': node.name,
                                    'line': node.lineno
                                })
                except Exception as e:
                    # Skip files that can't be parsed
                    continue
        
        return managers
    
    def _discover_websocket_import_paths(self) -> List[Dict]:
        """Discover fragmented import paths for WebSocket functionality."""
        import_paths = []
        functionality_map = {}
        
        # Analyze both directories for import patterns
        for directory in [self.websocket_legacy_dir, self.websocket_core_dir]:
            if not directory.exists():
                continue
            
            for py_file in directory.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Look for class definitions that represent similar functionality
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            # Extract functionality name (remove specific prefixes/suffixes)
                            functionality = node.name.lower()
                            for prefix in ['unified', 'legacy', 'core', 'websocket']:
                                functionality = functionality.replace(prefix, '')
                            for suffix in ['manager', 'handler', 'adapter']:
                                if functionality.endswith(suffix):
                                    functionality = suffix
                                    break
                            
                            if functionality not in functionality_map:
                                functionality_map[functionality] = []
                            
                            import_path = f"netra_backend.app.{py_file.relative_to(self.backend_root).with_suffix('')}"
                            import_path = import_path.replace('/', '.')
                            
                            functionality_map[functionality].append({
                                'path': import_path,
                                'class': node.name,
                                'file': str(py_file.relative_to(self.backend_root))
                            })
                            
                except Exception:
                    continue
        
        # Convert to list of fragmentations (multiple paths for same functionality)
        for functionality, paths in functionality_map.items():
            if len(paths) > 1:
                import_paths.append({
                    'functionality': functionality,
                    'paths': paths
                })
        
        return import_paths
    
    def _discover_compatibility_shims(self) -> List[Dict]:
        """Discover compatibility shim files indicating incomplete migration."""
        shims = []
        
        for py_file in self.websocket_legacy_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for compatibility shim indicators
                shim_indicators = [
                    'compatibility',
                    'backward compatibility',
                    'compatibility layer',
                    'legacy imports',
                    'import.*websocket_core',
                    'compatibility wrapper'
                ]
                
                for indicator in shim_indicators:
                    if indicator.lower() in content.lower():
                        shims.append({
                            'file': str(py_file.relative_to(self.backend_root)),
                            'purpose': f"Contains '{indicator}'",
                            'indicator': indicator
                        })
                        break
                        
            except Exception:
                continue
        
        return shims
    
    def _discover_factory_patterns(self) -> List[Dict]:
        """Discover different factory pattern implementations."""
        patterns = []
        
        # Search both directories for factory patterns
        for directory in [self.websocket_legacy_dir, self.websocket_core_dir]:
            if not directory.exists():
                continue
                
            for py_file in directory.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Detect factory patterns
                    pattern_type = None
                    if 'def get_' in content and 'manager' in content.lower():
                        pattern_type = 'function_factory'
                    elif 'class.*Factory' in content:
                        pattern_type = 'class_factory'
                    elif '@staticmethod' in content and 'create' in content:
                        pattern_type = 'static_factory'
                    elif '_instance' in content and 'None' in content:
                        pattern_type = 'singleton_pattern'
                    elif 'ConnectionManager =' in content:
                        pattern_type = 'alias_pattern'
                    
                    if pattern_type:
                        patterns.append({
                            'file': str(py_file.relative_to(self.backend_root)),
                            'pattern_type': pattern_type
                        })
                        
                except Exception:
                    continue
        
        return patterns


if __name__ == '__main__':
    # Run with verbose output to show violation details
    unittest.main(verbosity=2)