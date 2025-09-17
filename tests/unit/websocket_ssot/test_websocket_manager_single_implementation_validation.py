"""
WebSocket SSOT Implementation Validation Test

This test validates that WebSocket manager implementations follow SSOT (Single Source of Truth) 
principles by scanning the codebase for multiple implementations and detecting fragmentation.

PURPOSE: Detect SSOT violations in WebSocket infrastructure to ensure system reliability.
BUSINESS VALUE: Platform/Internal - System Stability & Development Velocity
EXPECTED RESULT: FAIL initially - proving SSOT violations exist

CRITICAL: This test should FAIL to prove the fragmentation issue exists.
Once violations are fixed, this test will pass and serve as a regression guard.

Author: Claude Code AI
Created: 2025-01-17
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class WebSocketImplementation:
    """Represents a WebSocket manager implementation found in the codebase."""
    file_path: str
    class_name: str
    line_number: int
    imports: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    is_ssot_canonical: bool = False


@dataclass
class SSotViolationReport:
    """Report of SSOT violations found in WebSocket implementations."""
    total_implementations: int = 0
    canonical_implementations: int = 0
    legacy_implementations: int = 0
    fragmented_imports: Dict[str, List[str]] = field(default_factory=dict)
    duplicate_classes: Dict[str, List[str]] = field(default_factory=dict)
    violations_summary: List[str] = field(default_factory=list)


class TestWebSocketManagerSingleImplementationValidation(SSotBaseTestCase):
    """
    WebSocket SSOT validation test to detect implementation fragmentation.
    
    This test scans the entire codebase to find all WebSocket manager implementations
    and validates that only ONE canonical SSOT implementation exists.
    
    CRITICAL: This test is designed to FAIL initially to prove violations exist.
    """
    
    def setup_method(self, method=None):
        """Setup method for SSOT validation test."""
        super().setup_method(method)
        
        # Get the project root directory
        self.project_root = Path("/Users/anthony/Desktop/netra-apex")
        self.excluded_dirs = {
            ".git", "__pycache__", "node_modules", ".pytest_cache", 
            "venv", "env", ".venv", "build", "dist", ".mypy_cache"
        }
        
        # Expected SSOT canonical path
        self.canonical_websocket_manager = "netra_backend/app/websocket_core/manager.py"
        
        # Record metrics for validation
        self.record_metric("ssot_validation_started", True)
    
    def test_websocket_manager_single_implementation_ssot_validation(self):
        """
        Main SSOT validation test - scans codebase for WebSocket manager implementations.
        
        This test SHOULD FAIL initially to prove SSOT violations exist.
        Expected violations:
        1. Multiple WebSocket manager class implementations
        2. Import path fragmentation
        3. Legacy implementations not removed
        4. Inconsistent SSOT patterns
        """
        # Scan codebase for WebSocket implementations
        implementations = self._scan_websocket_implementations()
        
        # Analyze SSOT compliance
        violation_report = self._analyze_ssot_compliance(implementations)
        
        # Record metrics for business tracking
        self.record_metric("total_websocket_implementations", violation_report.total_implementations)
        self.record_metric("canonical_implementations", violation_report.canonical_implementations)
        self.record_metric("legacy_implementations", violation_report.legacy_implementations)
        self.record_metric("fragmented_import_paths", len(violation_report.fragmented_imports))
        
        # Log detailed violation report
        self._log_violation_report(violation_report)
        
        # CRITICAL ASSERTIONS - These should FAIL initially to prove violations exist
        
        # Assert only ONE canonical implementation exists
        self.assertEqual(
            violation_report.canonical_implementations, 1,
            f"Expected exactly 1 canonical WebSocket manager implementation, "
            f"found {violation_report.canonical_implementations}. "
            f"Total implementations: {violation_report.total_implementations}"
        )
        
        # Assert no legacy implementations exist
        self.assertEqual(
            violation_report.legacy_implementations, 0,
            f"Found {violation_report.legacy_implementations} legacy WebSocket implementations. "
            f"All legacy code should be removed for SSOT compliance."
        )
        
        # Assert no import path fragmentation
        self.assertEqual(
            len(violation_report.fragmented_imports), 0,
            f"Found {len(violation_report.fragmented_imports)} fragmented import paths: "
            f"{list(violation_report.fragmented_imports.keys())}"
        )
        
        # Assert no duplicate class names
        self.assertEqual(
            len(violation_report.duplicate_classes), 0,
            f"Found {len(violation_report.duplicate_classes)} duplicate WebSocket class names: "
            f"{list(violation_report.duplicate_classes.keys())}"
        )
        
        # Final assertion - should PASS only when all violations are fixed
        self.assertLessEqual(
            len(violation_report.violations_summary), 0,
            f"SSOT violations detected:\n" + "\n".join(violation_report.violations_summary)
        )
    
    def _scan_websocket_implementations(self) -> List[WebSocketImplementation]:
        """
        Scan the entire codebase for WebSocket manager implementations.
        
        Returns:
            List of WebSocket implementations found
        """
        implementations = []
        
        # Patterns to detect WebSocket manager classes
        websocket_class_patterns = [
            r"class\s+(\w*WebSocket\w*Manager\w*)",
            r"class\s+(\w*Manager\w*WebSocket\w*)",
            r"class\s+(WebSocket\w*)",
            r"class\s+(\w*Connection\w*Manager\w*)",
            r"class\s+(\w*EventManager\w*)",
        ]
        
        # Compile patterns for efficiency
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in websocket_class_patterns]
        
        # Walk through all Python files
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.project_root)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            lines = content.splitlines()
                        
                        # Search for WebSocket manager classes
                        for line_num, line in enumerate(lines, 1):
                            for pattern in compiled_patterns:
                                match = pattern.search(line)
                                if match:
                                    class_name = match.group(1)
                                    
                                    # Filter out clearly unrelated classes
                                    if self._is_websocket_related(class_name, content):
                                        implementation = WebSocketImplementation(
                                            file_path=str(relative_path),
                                            class_name=class_name,
                                            line_number=line_num,
                                            imports=self._extract_imports(content),
                                            methods=self._extract_methods(content, class_name),
                                            is_ssot_canonical=self._is_canonical_implementation(relative_path)
                                        )
                                        implementations.append(implementation)
                    
                    except (UnicodeDecodeError, OSError) as e:
                        # Skip files that can't be read
                        continue
        
        return implementations
    
    def _is_websocket_related(self, class_name: str, file_content: str) -> bool:
        """
        Determine if a class is actually WebSocket-related.
        
        Args:
            class_name: Name of the class
            file_content: Content of the file
            
        Returns:
            True if the class appears to be WebSocket-related
        """
        websocket_indicators = [
            "websocket", "ws_", "socket", "connection", "event", 
            "message", "client", "session", "notification"
        ]
        
        # Check class name
        class_lower = class_name.lower()
        if any(indicator in class_lower for indicator in websocket_indicators):
            return True
        
        # Check file content for WebSocket-related imports or methods
        content_lower = file_content.lower()
        websocket_imports = [
            "websockets", "socketio", "fastapi.websockets", 
            "websocket", "connection", "event"
        ]
        
        return any(imp in content_lower for imp in websocket_imports)
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements from file content."""
        imports = []
        lines = content.splitlines()
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')):
                imports.append(stripped)
        
        return imports
    
    def _extract_methods(self, content: str, class_name: str) -> List[str]:
        """Extract method names from a class."""
        methods = []
        lines = content.splitlines()
        in_class = False
        
        for line in lines:
            stripped = line.strip()
            
            # Check if we're entering the target class
            if f"class {class_name}" in line:
                in_class = True
                continue
            
            # Check if we've left the class (next class or end of indentation)
            if in_class and stripped.startswith("class ") and f"class {class_name}" not in line:
                break
            
            # Extract method names
            if in_class and stripped.startswith("def "):
                method_match = re.match(r"def\s+(\w+)", stripped)
                if method_match:
                    methods.append(method_match.group(1))
        
        return methods
    
    def _is_canonical_implementation(self, file_path: Path) -> bool:
        """
        Determine if a file path represents the canonical SSOT implementation.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if this is the canonical SSOT implementation
        """
        return str(file_path) == self.canonical_websocket_manager
    
    def _analyze_ssot_compliance(self, implementations: List[WebSocketImplementation]) -> SSotViolationReport:
        """
        Analyze implementations for SSOT compliance violations.
        
        Args:
            implementations: List of WebSocket implementations found
            
        Returns:
            Detailed violation report
        """
        report = SSotViolationReport()
        
        # Count implementations
        report.total_implementations = len(implementations)
        report.canonical_implementations = sum(1 for impl in implementations if impl.is_ssot_canonical)
        report.legacy_implementations = report.total_implementations - report.canonical_implementations
        
        # Analyze import fragmentation
        import_paths = {}
        for impl in implementations:
            for import_stmt in impl.imports:
                if "websocket" in import_stmt.lower() or "socket" in import_stmt.lower():
                    if import_stmt not in import_paths:
                        import_paths[import_stmt] = []
                    import_paths[import_stmt].append(impl.file_path)
        
        # Find fragmented imports (same functionality, different paths)
        for import_stmt, files in import_paths.items():
            if len(files) > 1:
                report.fragmented_imports[import_stmt] = files
        
        # Analyze duplicate class names
        class_names = {}
        for impl in implementations:
            if impl.class_name not in class_names:
                class_names[impl.class_name] = []
            class_names[impl.class_name].append(impl.file_path)
        
        for class_name, files in class_names.items():
            if len(files) > 1:
                report.duplicate_classes[class_name] = files
        
        # Generate violations summary
        if report.canonical_implementations == 0:
            report.violations_summary.append("NO canonical SSOT implementation found")
        elif report.canonical_implementations > 1:
            report.violations_summary.append(f"Multiple canonical implementations: {report.canonical_implementations}")
        
        if report.legacy_implementations > 0:
            report.violations_summary.append(f"Legacy implementations found: {report.legacy_implementations}")
        
        if report.fragmented_imports:
            report.violations_summary.append(f"Import fragmentation detected: {len(report.fragmented_imports)} cases")
        
        if report.duplicate_classes:
            report.violations_summary.append(f"Duplicate class names: {len(report.duplicate_classes)} cases")
        
        return report
    
    def _log_violation_report(self, report: SSotViolationReport):
        """
        Log detailed violation report for analysis.
        
        Args:
            report: SSOT violation report
        """
        self.logger.info("=== WebSocket SSOT Validation Report ===")
        self.logger.info(f"Total implementations found: {report.total_implementations}")
        self.logger.info(f"Canonical implementations: {report.canonical_implementations}")
        self.logger.info(f"Legacy implementations: {report.legacy_implementations}")
        
        if report.fragmented_imports:
            self.logger.info("Fragmented imports detected:")
            for import_stmt, files in report.fragmented_imports.items():
                self.logger.info(f"  {import_stmt} -> {files}")
        
        if report.duplicate_classes:
            self.logger.info("Duplicate class names detected:")
            for class_name, files in report.duplicate_classes.items():
                self.logger.info(f"  {class_name} -> {files}")
        
        if report.violations_summary:
            self.logger.error("SSOT Violations Summary:")
            for violation in report.violations_summary:
                self.logger.error(f"  - {violation}")
        else:
            self.logger.info("✅ No SSOT violations detected - WebSocket implementation is compliant")
    
    def teardown_method(self, method=None):
        """Teardown method with metrics recording."""
        # Record final validation metrics
        self.record_metric("ssot_validation_completed", True)
        self.record_metric("test_execution_time", self.get_metrics().execution_time)
        
        super().teardown_method(method)