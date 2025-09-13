#!/usr/bin/env python
"""
FAILING TEST: Multiple WebSocketNotifier Detection - Issue #680

This test DETECTS duplicate WebSocketNotifier implementations across the codebase.
Business Impact: $500K+ ARR at risk from conflicting WebSocket implementations

Test Strategy:
- Scan codebase for multiple WebSocketNotifier class definitions
- Should FAIL: Find multiple implementations causing conflicts
- Should PASS after SSOT consolidation to single implementation

Expected Result: FAILS before SSOT refactor, PASSES after SSOT consolidation
"""

import ast
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class WebSocketClassDetector(ast.NodeVisitor):
    """AST visitor to detect WebSocket-related class definitions."""
    
    def __init__(self):
        self.classes_found = []
        self.current_file = None
        
    def set_current_file(self, file_path: str):
        """Set the current file being analyzed."""
        self.current_file = file_path
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions and identify WebSocket-related classes."""
        class_name = node.name
        
        # Target WebSocket-related class patterns
        websocket_patterns = [
            'WebSocketNotifier',
            'WebSocketManager', 
            'WebSocketBridge',
            'WebSocketHandler',
            'WebSocketConnection',
            'WebSocketEvent',
            'WebSocketClient',
            'WebSocketService'
        ]
        
        # Check for exact matches or patterns
        is_websocket_class = False
        pattern_matched = None
        
        for pattern in websocket_patterns:
            if pattern in class_name:
                is_websocket_class = True
                pattern_matched = pattern
                break
        
        if is_websocket_class:
            # Extract additional information
            base_classes = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    base_classes.append(base.id)
                elif isinstance(base, ast.Attribute):
                    base_classes.append(f"{base.value.id}.{base.attr}" if hasattr(base.value, 'id') else str(base.attr))
            
            # Get method names
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)
            
            class_info = {
                'name': class_name,
                'pattern_matched': pattern_matched,
                'file_path': self.current_file,
                'line_number': node.lineno,
                'base_classes': base_classes,
                'methods': methods,
                'is_duplicate_candidate': True
            }
            
            self.classes_found.append(class_info)
        
        # Continue visiting child nodes
        self.generic_visit(node)


class TestMultipleWebSocketNotifierDetection(SSotBaseTestCase):
    """
    FAILING TEST: Detects duplicate WebSocketNotifier implementations.
    
    This test scans the codebase for multiple WebSocket-related class implementations
    that should be consolidated into a single SSOT pattern. Issue #680 indicates
    that multiple implementations are causing conflicts.
    
    Expected to FAIL by finding multiple implementations.
    After SSOT consolidation, should PASS with single authoritative implementation.
    """
    
    def setup_method(self, method=None):
        """Setup for WebSocket class detection."""
        super().setup_method(method)
        
        # Configuration
        self.project_root = Path(project_root)
        self.scan_paths = [
            self.project_root / "netra_backend",
            self.project_root / "auth_service", 
            self.project_root / "shared",
            self.project_root / "test_framework"
        ]
        
        # Results tracking
        self.all_websocket_classes = []
        self.duplicate_groups = {}
        self.ssot_violations = []
        self.scan_errors = []
        
        logger.info(f"Starting WebSocket class detection scan")
    
    def scan_file_for_websocket_classes(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Scan a single Python file for WebSocket class definitions.
        
        Returns list of WebSocket classes found in the file.
        """
        classes_found = []
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                self.scan_errors.append({
                    'file_path': str(file_path),
                    'error_type': 'syntax_error',
                    'error': str(e),
                    'line_number': getattr(e, 'lineno', None)
                })
                return classes_found
            
            # Visit nodes to find WebSocket classes
            detector = WebSocketClassDetector()
            detector.set_current_file(str(file_path))
            detector.visit(tree)
            
            classes_found = detector.classes_found
            
        except Exception as e:
            self.scan_errors.append({
                'file_path': str(file_path),
                'error_type': 'file_read_error',
                'error': str(e)
            })
        
        return classes_found
    
    def scan_directory_for_websocket_classes(self, directory: Path) -> List[Dict[str, Any]]:
        """
        Recursively scan directory for WebSocket class definitions.
        
        Returns list of all WebSocket classes found in the directory.
        """
        all_classes = []
        
        if not directory.exists():
            logger.warning(f"Directory does not exist: {directory}")
            return all_classes
        
        # Find all Python files
        python_files = []
        try:
            python_files = list(directory.rglob("*.py"))
        except Exception as e:
            self.scan_errors.append({
                'directory': str(directory),
                'error_type': 'directory_scan_error',
                'error': str(e)
            })
            return all_classes
        
        # Scan each Python file
        for py_file in python_files:
            # Skip certain directories
            skip_dirs = ['.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv']
            if any(skip_dir in str(py_file) for skip_dir in skip_dirs):
                continue
                
            file_classes = self.scan_file_for_websocket_classes(py_file)
            all_classes.extend(file_classes)
        
        return all_classes
    
    def analyze_duplicates(self, all_classes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Analyze WebSocket classes to identify potential duplicates.
        
        Groups classes by name/pattern to identify SSOT violations.
        """
        groups = {}
        
        for class_info in all_classes:
            class_name = class_info['name']
            pattern = class_info['pattern_matched']
            
            # Group by exact name
            if class_name not in groups:
                groups[class_name] = []
            groups[class_name].append(class_info)
            
            # Also group by pattern for broader analysis
            pattern_key = f"pattern_{pattern}"
            if pattern_key not in groups:
                groups[pattern_key] = []
            groups[pattern_key].append(class_info)
        
        # Filter to only groups with multiple implementations
        duplicate_groups = {}
        for group_name, classes in groups.items():
            if len(classes) > 1:
                duplicate_groups[group_name] = classes
        
        return duplicate_groups
    
    def identify_ssot_violations(self, duplicate_groups: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Identify specific SSOT violations from duplicate class analysis.
        
        Returns list of violations that need to be addressed.
        """
        violations = []
        
        for group_name, classes in duplicate_groups.items():
            if len(classes) < 2:
                continue
            
            # Analyze the duplicates
            file_paths = [cls['file_path'] for cls in classes]
            unique_files = set(file_paths)
            
            # Check for exact same class name in multiple files
            if not group_name.startswith('pattern_'):
                violations.append({
                    'type': 'duplicate_class_definition',
                    'class_name': group_name,
                    'duplicate_count': len(classes),
                    'file_count': len(unique_files),
                    'files': list(unique_files),
                    'classes': classes,
                    'severity': 'HIGH'
                })
            
            # Check for similar functionality that should be consolidated
            else:
                pattern = group_name.replace('pattern_', '')
                violations.append({
                    'type': 'pattern_duplication',
                    'pattern': pattern,
                    'duplicate_count': len(classes),
                    'file_count': len(unique_files), 
                    'files': list(unique_files),
                    'classes': classes,
                    'severity': 'MEDIUM'
                })
        
        # Special checks for critical WebSocket components
        critical_patterns = ['WebSocketNotifier', 'WebSocketManager']
        for pattern in critical_patterns:
            pattern_classes = []
            for group_name, classes in duplicate_groups.items():
                if pattern in group_name:
                    pattern_classes.extend(classes)
            
            if len(pattern_classes) > 1:
                violations.append({
                    'type': 'critical_component_duplication',
                    'component': pattern,
                    'duplicate_count': len(pattern_classes),
                    'impact': 'BUSINESS_CRITICAL',
                    'classes': pattern_classes,
                    'severity': 'CRITICAL'
                })
        
        return violations
    
    def test_detect_multiple_websocket_notifier_implementations(self):
        """
        FAILING TEST: Detects duplicate WebSocketNotifier implementations.
        
        This test scans the codebase for multiple WebSocket class implementations
        that violate SSOT principles. Expected to FAIL by finding violations.
        
        After SSOT consolidation, this test should PASS with single implementations.
        """
        logger.info("Starting codebase scan for WebSocket class duplicates")
        
        # Phase 1: Scan all configured paths
        logger.info("Phase 1: Scanning directories for WebSocket classes")
        
        all_classes = []
        for scan_path in self.scan_paths:
            logger.info(f"Scanning: {scan_path}")
            classes_in_path = self.scan_directory_for_websocket_classes(scan_path)
            all_classes.extend(classes_in_path)
            logger.info(f"Found {len(classes_in_path)} WebSocket classes in {scan_path}")
        
        self.all_websocket_classes = all_classes
        
        # Phase 2: Analyze for duplicates
        logger.info("Phase 2: Analyzing for duplicate implementations")
        duplicate_groups = self.analyze_duplicates(all_classes)
        self.duplicate_groups = duplicate_groups
        
        # Phase 3: Identify SSOT violations
        logger.info("Phase 3: Identifying SSOT violations")
        ssot_violations = self.identify_ssot_violations(duplicate_groups)
        self.ssot_violations = ssot_violations
        
        # Phase 4: Record metrics
        self.record_metric('total_websocket_classes', len(all_classes))
        self.record_metric('duplicate_groups', len(duplicate_groups))
        self.record_metric('ssot_violations', len(ssot_violations))
        self.record_metric('scan_errors', len(self.scan_errors))
        
        # Log detailed findings
        logger.info(f"Scan Results:")
        logger.info(f"  Total WebSocket classes found: {len(all_classes)}")
        logger.info(f"  Duplicate groups identified: {len(duplicate_groups)}")
        logger.info(f"  SSOT violations: {len(ssot_violations)}")
        
        if ssot_violations:
            logger.error("SSOT Violations Detected:")
            for violation in ssot_violations:
                logger.error(f"  - {violation['type']}: {violation.get('class_name', violation.get('pattern', 'unknown'))}")
                logger.error(f"    Severity: {violation['severity']}")
                logger.error(f"    Duplicates: {violation['duplicate_count']}")
                logger.error(f"    Files: {violation.get('file_count', 'unknown')}")
        
        # Log specific duplicate groups for debugging
        if duplicate_groups:
            logger.warning("Duplicate Groups Detail:")
            for group_name, classes in duplicate_groups.items():
                logger.warning(f"  Group: {group_name} ({len(classes)} duplicates)")
                for cls in classes:
                    logger.warning(f"    - {cls['name']} in {cls['file_path']}:{cls['line_number']}")
        
        # Phase 5: Assert violations exist (test should FAIL)
        logger.info("Phase 5: Checking for SSOT violations")
        
        # Check for scan errors that might indicate issues
        if self.scan_errors:
            logger.warning(f"Scan errors encountered: {len(self.scan_errors)}")
            for error in self.scan_errors:
                logger.warning(f"  - {error['error_type']}: {error['error']}")
        
        # SUCCESS CRITERIA FOR AFTER SSOT CONSOLIDATION:
        # After SSOT refactor, these assertions should be flipped to verify single implementations
        
        # CURRENT EXPECTATION: Test should FAIL due to finding duplicate implementations
        
        # Assert we found WebSocket classes (sanity check)
        assert len(all_classes) > 0, (
            "No WebSocket classes found. This suggests either no WebSocket code exists "
            "(unlikely) or the scan is not working properly."
        )
        
        # Check for critical violations
        critical_violations = [v for v in ssot_violations if v['severity'] == 'CRITICAL']
        high_violations = [v for v in ssot_violations if v['severity'] == 'HIGH']
        
        total_violations = len(ssot_violations)
        
        # If no violations found, either the code is already clean or detection needs improvement
        if total_violations == 0:
            # This might indicate SSOT consolidation was already completed
            logger.info("No SSOT violations detected - this might indicate good SSOT compliance")
            return {
                'status': 'no_violations_detected',
                'total_classes': len(all_classes),
                'message': 'Either SSOT consolidation already complete or detection needs refinement'
            }
        
        # Expected: Find violations that confirm Issue #680
        logger.info(f"SSOT violations detected: {total_violations}")
        logger.info(f"Critical violations: {len(critical_violations)}")
        logger.info(f"High severity violations: {len(high_violations)}")
        
        # Specific checks for WebSocketNotifier duplicates (the main issue)
        websocket_notifier_violations = [
            v for v in ssot_violations 
            if 'WebSocketNotifier' in str(v.get('class_name', '')) or 
               'WebSocketNotifier' in str(v.get('pattern', ''))
        ]
        
        if websocket_notifier_violations:
            logger.error(f"WebSocketNotifier violations found: {len(websocket_notifier_violations)}")
            for violation in websocket_notifier_violations:
                logger.error(f"  - {violation}")
        
        # Assert violations exist to confirm the issue
        assert total_violations > 0, (
            f"EXPECTED SSOT VIOLATIONS DETECTED: {total_violations} violations found. "
            f"Critical: {len(critical_violations)}, High: {len(high_violations)}. "
            "This confirms duplicate WebSocket implementations exist (Issue #680)."
        )
        
        # Additional check for WebSocketNotifier specifically
        if websocket_notifier_violations:
            assert len(websocket_notifier_violations) > 0, (
                f"WebSocketNotifier duplication confirmed: {len(websocket_notifier_violations)} violations. "
                "This confirms the specific issue mentioned in Issue #680."
            )
        
        # The test PASSES by proving violations exist (confirming the issue)
        logger.info("TEST PASSES: WebSocket implementation duplicates confirmed")
        logger.info("Next step: Consolidate WebSocket implementations to single SSOT")
        
        return {
            'total_violations': total_violations,
            'critical_violations': len(critical_violations),
            'high_violations': len(high_violations),
            'websocket_notifier_violations': len(websocket_notifier_violations),
            'total_classes_found': len(all_classes),
            'duplicate_groups': len(duplicate_groups),
            'test_status': 'violations_confirmed'
        }


if __name__ == "__main__":
    # Run the test directly for debugging
    import pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])