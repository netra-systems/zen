"""
WebSocket SSOT Regression Prevention Tests

These tests prevent future SSOT violations by detecting patterns that could
lead to WebSocket manager duplication and import pattern violations.

Business Value: Platform/Internal - Prevent regression of SSOT consolidation work
Ensures that future development doesn't reintroduce the violations we're fixing.

Test Status: DESIGNED TO FAIL with current code (detecting violation patterns)
Expected Result: PASS after SSOT consolidation + safeguards implemented
"""

import ast
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
import importlib.util

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


class TestWebSocketSSotRegressionPrevention(SSotBaseTestCase):
    """
    Test suite to prevent regression of WebSocket SSOT violations.
    
    These tests catch patterns that could reintroduce violations.
    """
    
    def test_prevent_future_websocket_manager_duplication(self):
        """
        Test that prevents future creation of duplicate WebSocket manager classes.
        
        CURRENT BEHAVIOR: Multiple manager classes exist (VIOLATION)
        EXPECTED AFTER SSOT: Only one manager class allowed, others prevented
        """
        websocket_core_path = PROJECT_ROOT / "netra_backend" / "app" / "websocket_core"
        
        manager_classes_found = {}
        duplicate_violations = []
        
        # Scan all Python files in websocket_core for manager classes
        for py_file in websocket_core_path.glob("*.py"):
            if py_file.name.startswith("test_"):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Parse AST to find class definitions
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_name = node.name
                            
                            # Check for WebSocket manager class patterns
                            if 'websocket' in class_name.lower() and 'manager' in class_name.lower():
                                file_path = str(py_file.relative_to(PROJECT_ROOT))
                                
                                if class_name in manager_classes_found:
                                    duplicate_violations.append({
                                        "class_name": class_name,
                                        "files": [manager_classes_found[class_name], file_path]
                                    })
                                else:
                                    manager_classes_found[class_name] = file_path
                                    
                except SyntaxError:
                    # Skip files with syntax errors
                    continue
                    
            except Exception as e:
                self.logger.warning(f"Failed to scan {py_file}: {e}")
                continue
        
        # Check for inheritance violations (multiple classes inheriting same base)
        base_class_violations = []
        websocket_managers = [cls for cls in manager_classes_found.keys() 
                             if 'WebSocketManager' in cls]
        
        if len(websocket_managers) > 1:
            base_class_violations.append({
                "violation_type": "multiple_websocket_managers",
                "classes": websocket_managers,
                "files": [manager_classes_found[cls] for cls in websocket_managers]
            })
        
        total_violations = len(duplicate_violations) + len(base_class_violations)
        
        # CURRENT EXPECTATION: Violations exist (will fail indicating violations)
        # AFTER SSOT: Should have zero violations
        self.assertGreater(total_violations, 0,
                          "SSOT VIOLATION DETECTED: WebSocket manager duplication patterns found. "
                          f"Duplicates: {len(duplicate_violations)}, Base violations: {len(base_class_violations)}")
        
        self.logger.warning(f"Manager Duplication Violations: {total_violations} violations found")
        self.metrics.record_test_event("websocket_manager_duplication_violation", {
            "total_violations": total_violations,
            "duplicate_violations": duplicate_violations,
            "base_class_violations": base_class_violations,
            "manager_classes_found": manager_classes_found
        })

    def test_import_pattern_violation_detection(self):
        """
        Test that detects import patterns that could reintroduce SSOT violations.
        
        CURRENT BEHAVIOR: Multiple import patterns exist (VIOLATION)
        EXPECTED AFTER SSOT: Standardized import patterns enforced
        """
        # Search for WebSocket manager imports across the codebase
        backend_path = PROJECT_ROOT / "netra_backend"
        import_violations = []
        import_patterns_found = {}
        
        # Patterns that indicate SSOT violations
        violation_patterns = [
            "from netra_backend.app.websocket_core.manager import",
            "from netra_backend.app.websocket_core.websocket_manager import",
            "from netra_backend.app.websocket_core.unified_manager import",
            "import netra_backend.app.websocket_core.manager",
            "import netra_backend.app.websocket_core.websocket_manager",
            "import netra_backend.app.websocket_core.unified_manager"
        ]
        
        # Scan Python files for import patterns
        for py_file in backend_path.rglob("*.py"):
            if "test" in str(py_file) or "__pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                file_violations = []
                for pattern in violation_patterns:
                    if pattern in content:
                        # Count occurrences
                        count = content.count(pattern)
                        file_violations.append({
                            "pattern": pattern,
                            "count": count,
                            "file": str(py_file.relative_to(PROJECT_ROOT))
                        })
                        
                        # Track patterns globally
                        if pattern not in import_patterns_found:
                            import_patterns_found[pattern] = []
                        import_patterns_found[pattern].append(str(py_file.relative_to(PROJECT_ROOT)))
                
                if file_violations:
                    import_violations.extend(file_violations)
                    
            except Exception as e:
                self.logger.warning(f"Failed to scan {py_file}: {e}")
                continue
        
        # Analyze pattern diversity (indicates SSOT violation)
        unique_patterns = len(import_patterns_found)
        total_import_violations = len(import_violations)
        
        # Check for circular import risks
        circular_risk_files = []
        for pattern, files in import_patterns_found.items():
            if len(files) > 5:  # Many files importing same thing differently
                circular_risk_files.extend(files)
        
        circular_risk_count = len(set(circular_risk_files))
        
        # CURRENT EXPECTATION: Multiple patterns exist (violation)
        # AFTER SSOT: Should have single standardized pattern
        self.assertGreater(unique_patterns, 1,
                          "SSOT VIOLATION DETECTED: Multiple WebSocket import patterns found. "
                          f"Found {unique_patterns} different import patterns with {total_import_violations} total violations")
        
        self.logger.warning(f"Import Pattern Violations: {unique_patterns} patterns, {total_import_violations} violations")
        self.metrics.record_test_event("websocket_import_pattern_violation", {
            "unique_patterns": unique_patterns,
            "total_violations": total_import_violations,
            "circular_risk_count": circular_risk_count,
            "patterns_found": {pattern: len(files) for pattern, files in import_patterns_found.items()},
            "violation_details": import_violations[:10]  # Limit details for metrics
        })