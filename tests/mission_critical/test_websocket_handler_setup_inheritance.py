"""
WebSocket Handler Setup Method Inheritance Validation Test Suite

MISSION: Detect and report inheritance issues with setup_method() calls in WebSocket handler test classes.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Critical for ALL customer segments
- Business Goal: Prevent inheritance-related test failures that could mask revenue-impacting bugs
- Value Impact: Ensures proper test initialization so revenue-critical WebSocket functionality is properly validated
- Strategic Impact: CRITICAL - Improper test inheritance can lead to undetected bugs in $500K+ ARR chat functionality

CURRENT ISSUE DETECTION:
Test classes like TestTypingHandler don't call super().setup_method() while others like TestConnectionHandler do.
This creates inheritance inconsistency that can lead to test failures and undetected bugs.

CRITICAL SUCCESS CRITERIA:
1. Test FAILS when it detects missing super().setup_method() calls
2. Detailed violation reports with exact class names, file paths, line numbers
3. Comprehensive discovery of ALL WebSocket handler test classes
4. Hard failures with no try/except blocks (per CLAUDE.md requirements)
5. MRO analysis for comprehensive inheritance understanding

Following CLAUDE.md: Tests MUST raise errors, no try/except blocks.
Following SSOT: Use test_framework.ssot patterns consistently.
"""

import ast
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
import importlib.util

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class SetupMethodInheritanceViolation:
    """Data class representing a setup method inheritance violation."""
    test_class_name: str
    file_path: str
    line_number: int
    has_setup_method: bool
    calls_super_setup: bool
    mro_chain: List[str]
    violation_type: str
    details: str
    remediation_steps: List[str] = field(default_factory=list)


@dataclass  
class InheritanceAnalysisReport:
    """Comprehensive inheritance analysis report."""
    total_test_classes: int = 0
    violations_found: int = 0
    violations: List[SetupMethodInheritanceViolation] = field(default_factory=list)
    compliant_classes: List[str] = field(default_factory=list)
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_violation(self, violation: SetupMethodInheritanceViolation) -> None:
        """Add a violation to the report."""
        self.violations.append(violation)
        self.violations_found += 1
    
    def add_compliant_class(self, class_name: str) -> None:
        """Add a compliant class to the report."""
        self.compliant_classes.append(class_name)
    
    def get_summary(self) -> str:
        """Get a summary of the analysis."""
        return (
            f"WebSocket Handler Setup Inheritance Analysis:\n"
            f"  Total test classes analyzed: {self.total_test_classes}\n"
            f"  Violations found: {self.violations_found}\n"
            f"  Compliant classes: {len(self.compliant_classes)}\n"
            f"  Violation rate: {(self.violations_found / max(1, self.total_test_classes)) * 100:.1f}%"
        )


class WebSocketHandlerInheritanceAnalyzer:
    """
    Analyzer for detecting setup_method() inheritance issues in WebSocket handler test classes.
    
    This class performs comprehensive static analysis of test files to detect:
    1. Test classes that don't call super().setup_method()
    2. Missing setup_method implementations
    3. Incorrect inheritance patterns
    4. MRO (Method Resolution Order) issues
    """
    
    def __init__(self):
        """Initialize the analyzer."""
        self.target_file_path = Path("netra_backend/tests/unit/websocket_core/test_websocket_handlers_comprehensive.py")
        self.working_directory = Path.cwd()
        self.full_target_path = self.working_directory / self.target_file_path
    
    def discover_test_classes_from_ast(self, file_path: Path) -> Dict[str, Dict[str, Any]]:
        """
        Discover test classes using AST parsing.
        
        Args:
            file_path: Path to the Python file to analyze
            
        Returns:
            Dictionary mapping class names to their analysis data
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Target file not found: {file_path}")
        
        # Read and parse the file
        file_content = file_path.read_text(encoding='utf-8')
        try:
            tree = ast.parse(file_content, filename=str(file_path))
        except SyntaxError as e:
            raise SyntaxError(f"Failed to parse {file_path}: {e}")
        
        test_classes = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if this is a test class
                if self._is_test_class(node):
                    class_analysis = self._analyze_test_class_ast(node, file_content)
                    test_classes[node.name] = class_analysis
        
        return test_classes
    
    def _is_test_class(self, class_node: ast.ClassDef) -> bool:
        """
        Determine if a class is a test class.
        
        Args:
            class_node: AST class definition node
            
        Returns:
            True if this is a test class
        """
        class_name = class_node.name
        
        # Check naming patterns
        if class_name.startswith('Test') and class_name != 'TestMetrics':
            return True
        
        # Check for test method patterns
        has_test_methods = any(
            method.name.startswith('test_') 
            for method in class_node.body 
            if isinstance(method, ast.FunctionDef)
        )
        
        return has_test_methods
    
    def _analyze_test_class_ast(self, class_node: ast.ClassDef, file_content: str) -> Dict[str, Any]:
        """
        Analyze a test class using AST.
        
        Args:
            class_node: AST class definition node
            file_content: Full file content for line number calculation
            
        Returns:
            Analysis data for the class
        """
        analysis = {
            'name': class_node.name,
            'line_number': class_node.lineno,
            'base_classes': [self._get_base_class_name(base) for base in class_node.bases],
            'has_setup_method': False,
            'calls_super_setup': False,
            'setup_method_line': None,
            'setup_method_body': [],
            'docstring': ast.get_docstring(class_node) or ""
        }
        
        # Find setup_method
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name == 'setup_method':
                analysis['has_setup_method'] = True
                analysis['setup_method_line'] = node.lineno
                analysis['calls_super_setup'] = self._calls_super_setup_method(node)
                analysis['setup_method_body'] = self._extract_method_body(node, file_content)
                break
        
        return analysis
    
    def _get_base_class_name(self, base_node: ast.expr) -> str:
        """Extract base class name from AST node."""
        if isinstance(base_node, ast.Name):
            return base_node.id
        elif isinstance(base_node, ast.Attribute):
            return f"{base_node.value.id}.{base_node.attr}" if hasattr(base_node.value, 'id') else str(base_node.attr)
        else:
            return str(base_node)
    
    def _calls_super_setup_method(self, method_node: ast.FunctionDef) -> bool:
        """
        Check if a setup_method calls super().setup_method().
        
        Args:
            method_node: AST function definition node for setup_method
            
        Returns:
            True if super().setup_method() is called
        """
        for node in ast.walk(method_node):
            if isinstance(node, ast.Call):
                # Check for super().setup_method() pattern
                if (isinstance(node.func, ast.Attribute) and
                    node.func.attr == 'setup_method' and
                    isinstance(node.func.value, ast.Call) and
                    isinstance(node.func.value.func, ast.Name) and
                    node.func.value.func.id == 'super'):
                    return True
        
        return False
    
    def _extract_method_body(self, method_node: ast.FunctionDef, file_content: str) -> List[str]:
        """Extract the method body as lines of code."""
        lines = file_content.split('\n')
        start_line = method_node.lineno
        
        # Find the actual method content (skip def line)
        method_lines = []
        for node in method_node.body:
            if hasattr(node, 'lineno'):
                line_content = lines[node.lineno - 1].strip()
                if line_content:
                    method_lines.append(line_content)
        
        return method_lines
    
    def analyze_inheritance_violations(self) -> InheritanceAnalysisReport:
        """
        Perform comprehensive inheritance analysis.
        
        Returns:
            Complete inheritance analysis report
        """
        report = InheritanceAnalysisReport()
        report.analysis_metadata = {
            'target_file': str(self.target_file_path),
            'full_path': str(self.full_target_path),
            'file_exists': self.full_target_path.exists()
        }
        
        if not self.full_target_path.exists():
            raise FileNotFoundError(f"Target file not found: {self.full_target_path}")
        
        # Discover and analyze test classes
        test_classes = self.discover_test_classes_from_ast(self.full_target_path)
        report.total_test_classes = len(test_classes)
        
        for class_name, class_analysis in test_classes.items():
            violation = self._check_for_violations(class_name, class_analysis)
            
            if violation:
                report.add_violation(violation)
            else:
                report.add_compliant_class(class_name)
        
        return report
    
    def _check_for_violations(self, class_name: str, class_analysis: Dict[str, Any]) -> Optional[SetupMethodInheritanceViolation]:
        """
        Check a single class for inheritance violations.
        
        Args:
            class_name: Name of the test class
            class_analysis: Analysis data for the class
            
        Returns:
            SetupMethodInheritanceViolation if violation found, None otherwise
        """
        # Skip base classes and mixins
        if class_name in ['SSotBaseTestCase', 'WebSocketTestMixin', 'BaseTestCase']:
            return None
        
        base_classes = class_analysis.get('base_classes', [])
        has_setup_method = class_analysis.get('has_setup_method', False)
        calls_super_setup = class_analysis.get('calls_super_setup', False)
        
        # Check for violations
        violation_type = None
        details = ""
        remediation_steps = []
        
        if has_setup_method and not calls_super_setup:
            # This is the main violation we're looking for
            violation_type = "MISSING_SUPER_CALL"
            details = f"Class {class_name} has setup_method() but doesn't call super().setup_method()"
            remediation_steps = [
                f"Add 'super().setup_method()' as the first line in {class_name}.setup_method()",
                "Ensure the call happens before any class-specific initialization",
                "Follow the pattern used in TestConnectionHandler"
            ]
        elif not has_setup_method and self._inherits_from_base_test_case(base_classes):
            # Missing setup method entirely (less critical but worth noting)
            violation_type = "NO_SETUP_METHOD"  
            details = f"Class {class_name} inherits from test base class but has no setup_method()"
            remediation_steps = [
                f"Add setup_method(self): method to {class_name}",
                "Call super().setup_method() as first line",
                "Add any class-specific test setup after super() call"
            ]
        
        if violation_type:
            return SetupMethodInheritanceViolation(
                test_class_name=class_name,
                file_path=str(self.target_file_path),
                line_number=class_analysis.get('line_number', 0),
                has_setup_method=has_setup_method,
                calls_super_setup=calls_super_setup,
                mro_chain=self._calculate_mro_chain(class_name, base_classes),
                violation_type=violation_type,
                details=details,
                remediation_steps=remediation_steps
            )
        
        return None
    
    def _inherits_from_base_test_case(self, base_classes: List[str]) -> bool:
        """Check if class inherits from a test base class."""
        test_base_classes = ['SSotBaseTestCase', 'BaseTestCase', 'AsyncTestCase', 'WebSocketTestMixin']
        return any(base in ' '.join(base_classes) for base in test_base_classes)
    
    def _calculate_mro_chain(self, class_name: str, base_classes: List[str]) -> List[str]:
        """Calculate the Method Resolution Order chain for documentation."""
        mro = [class_name]
        mro.extend(base_classes)
        
        # Add common base classes in expected order
        if 'SSotBaseTestCase' in base_classes or 'BaseTestCase' in base_classes:
            mro.append('object')
        
        return mro


class TestWebSocketHandlerSetupInheritance(SSotBaseTestCase):
    """
    MISSION CRITICAL: Test suite for detecting setup_method() inheritance violations.
    
    This test suite FAILS when inheritance issues are detected, providing detailed
    violation reports for remediation.
    
    CRITICAL: These tests protect the integrity of our WebSocket test infrastructure
    which validates revenue-critical chat functionality.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)  # CRITICAL: This is the pattern we're validating!
        self.analyzer = WebSocketHandlerInheritanceAnalyzer()
        self.report: Optional[InheritanceAnalysisReport] = None
    
    def test_websocket_handler_classes_discovered(self):
        """Test that WebSocket handler test classes are properly discovered."""
        # This test ensures our discovery mechanism works
        test_classes = self.analyzer.discover_test_classes_from_ast(self.analyzer.full_target_path)
        
        # Record discovery metrics
        self.record_metric("classes_discovered", len(test_classes))
        
        # HARD REQUIREMENT: Must find test classes
        assert len(test_classes) > 0, (
            f"No test classes discovered in {self.analyzer.target_file_path}. "
            f"This indicates either the file doesn't exist or has no test classes."
        )
        
        # CRITICAL: Must find specific expected classes
        expected_classes = ['TestTypingHandler', 'TestHeartbeatHandler', 'TestConnectionHandler']
        discovered_names = set(test_classes.keys())
        
        for expected_class in expected_classes:
            assert expected_class in discovered_names, (
                f"Expected test class '{expected_class}' not found. "
                f"Discovered classes: {sorted(discovered_names)}"
            )
        
        print(f"\n✓ Successfully discovered {len(test_classes)} test classes:")
        for class_name in sorted(test_classes.keys()):
            print(f"  - {class_name}")
    
    def test_detect_missing_super_setup_calls(self):
        """
        CRITICAL TEST: Detect test classes missing super().setup_method() calls.
        
        This test FAILS when it finds classes that have setup_method() but don't
        call super().setup_method(), which can lead to test infrastructure failures.
        """
        # Perform comprehensive inheritance analysis
        self.report = self.analyzer.analyze_inheritance_violations()
        
        # Record analysis metrics
        self.record_metric("total_classes_analyzed", self.report.total_test_classes)
        self.record_metric("violations_found", self.report.violations_found)
        self.record_metric("compliant_classes", len(self.report.compliant_classes))
        
        print(f"\n{self.report.get_summary()}")
        
        # CRITICAL ASSERTION: No violations should exist
        if self.report.violations_found > 0:
            violation_details = self._format_violation_report(self.report.violations)
            
            # This HARD FAILURE is intentional - violations must be fixed
            assert False, (
                f"SETUP METHOD INHERITANCE VIOLATIONS DETECTED!\n"
                f"\nFound {self.report.violations_found} inheritance violations:\n"
                f"{violation_details}\n"
                f"\nTHESE VIOLATIONS MUST BE FIXED IMMEDIATELY!\n"
                f"They can cause test infrastructure failures that mask revenue-critical bugs."
            )
        
        print("✓ All test classes have proper setup_method() inheritance")
    
    def test_verify_specific_known_violations(self):
        """
        CRITICAL TEST: Verify detection of known inheritance violations.
        
        Based on the issue description, we expect to find TestTypingHandler and 
        TestHeartbeatHandler missing super().setup_method() calls.
        """
        # Perform analysis if not already done
        if not self.report:
            self.report = self.analyzer.analyze_inheritance_violations()
        
        # Check for expected violations
        violation_classes = {v.test_class_name for v in self.report.violations}
        
        # Record specific violation metrics
        self.record_metric("typing_handler_violation", "TestTypingHandler" in violation_classes)
        self.record_metric("heartbeat_handler_violation", "TestHeartbeatHandler" in violation_classes)
        
        print(f"\nViolation Analysis:")
        print(f"  TestTypingHandler has violation: {'TestTypingHandler' in violation_classes}")
        print(f"  TestHeartbeatHandler has violation: {'TestHeartbeatHandler' in violation_classes}")
        
        # CRITICAL: If we find known violations, this test should FAIL
        known_violators = ['TestTypingHandler', 'TestHeartbeatHandler']
        found_known_violations = [cls for cls in known_violators if cls in violation_classes]
        
        if found_known_violations:
            violation_details = []
            for violation in self.report.violations:
                if violation.test_class_name in found_known_violations:
                    violation_details.append(self._format_single_violation(violation))
            
            assert False, (
                f"DETECTED KNOWN SETUP METHOD VIOLATIONS!\n"
                f"\nThe following classes are missing super().setup_method() calls:\n"
                f"{''.join(violation_details)}\n"
                f"These are the exact violations described in the issue.\n"
                f"IMMEDIATE ACTION REQUIRED: Add super().setup_method() calls to these classes!"
            )
    
    def test_mro_analysis_completeness(self):
        """Test Method Resolution Order analysis for comprehensive understanding."""
        # Perform analysis if not already done
        if not self.report:
            self.report = self.analyzer.analyze_inheritance_violations()
        
        print(f"\nMethod Resolution Order Analysis:")
        
        # Analyze MRO for all test classes
        for violation in self.report.violations:
            print(f"\n  {violation.test_class_name}:")
            print(f"    MRO Chain: {' -> '.join(violation.mro_chain)}")
            print(f"    Violation Type: {violation.violation_type}")
            print(f"    Has setup_method: {violation.has_setup_method}")
            print(f"    Calls super setup: {violation.calls_super_setup}")
        
        # Record MRO metrics
        mro_lengths = [len(v.mro_chain) for v in self.report.violations]
        if mro_lengths:
            self.record_metric("avg_mro_depth", sum(mro_lengths) / len(mro_lengths))
            self.record_metric("max_mro_depth", max(mro_lengths))
        
        # MRO analysis should be complete for all violations
        for violation in self.report.violations:
            assert len(violation.mro_chain) > 0, (
                f"MRO chain empty for {violation.test_class_name}. "
                f"This indicates incomplete inheritance analysis."
            )
    
    def test_remediation_steps_provided(self):
        """Test that detailed remediation steps are provided for all violations."""
        # Perform analysis if not already done  
        if not self.report:
            self.report = self.analyzer.analyze_inheritance_violations()
        
        print(f"\nRemediation Steps Analysis:")
        
        # Every violation must have remediation steps
        for violation in self.report.violations:
            assert len(violation.remediation_steps) > 0, (
                f"No remediation steps provided for {violation.test_class_name} violation. "
                f"All violations must have clear fix instructions."
            )
            
            print(f"\n  {violation.test_class_name} ({violation.violation_type}):")
            for i, step in enumerate(violation.remediation_steps, 1):
                print(f"    {i}. {step}")
        
        # Record remediation completeness
        remediation_counts = [len(v.remediation_steps) for v in self.report.violations]
        if remediation_counts:
            self.record_metric("avg_remediation_steps", sum(remediation_counts) / len(remediation_counts))
        
        print("✓ All violations have detailed remediation steps")
    
    def test_file_path_accuracy(self):
        """Test that violation reports contain accurate file paths and line numbers."""
        # Perform analysis if not already done
        if not self.report:
            self.report = self.analyzer.analyze_inheritance_violations()
        
        print(f"\nFile Path and Line Number Accuracy:")
        
        for violation in self.report.violations:
            # Verify file path is correct
            assert violation.file_path == str(self.analyzer.target_file_path), (
                f"Incorrect file path for {violation.test_class_name}: "
                f"expected {self.analyzer.target_file_path}, got {violation.file_path}"
            )
            
            # Line number should be positive
            assert violation.line_number > 0, (
                f"Invalid line number for {violation.test_class_name}: {violation.line_number}"
            )
            
            print(f"  {violation.test_class_name}: Line {violation.line_number}")
        
        print("✓ All violation reports have accurate file paths and line numbers")
    
    def _format_violation_report(self, violations: List[SetupMethodInheritanceViolation]) -> str:
        """Format a comprehensive violation report."""
        if not violations:
            return "No violations found."
        
        report_lines = [
            f"\n{'='*80}",
            f"WEBSOCKET HANDLER SETUP METHOD INHERITANCE VIOLATIONS",
            f"{'='*80}"
        ]
        
        for i, violation in enumerate(violations, 1):
            report_lines.append(f"\n[VIOLATION #{i}] {violation.test_class_name}")
            report_lines.append(f"  File: {violation.file_path}:{violation.line_number}")
            report_lines.append(f"  Type: {violation.violation_type}")
            report_lines.append(f"  Details: {violation.details}")
            report_lines.append(f"  MRO Chain: {' -> '.join(violation.mro_chain)}")
            report_lines.append(f"  Has setup_method: {violation.has_setup_method}")
            report_lines.append(f"  Calls super setup: {violation.calls_super_setup}")
            
            if violation.remediation_steps:
                report_lines.append(f"  REMEDIATION STEPS:")
                for j, step in enumerate(violation.remediation_steps, 1):
                    report_lines.append(f"    {j}. {step}")
        
        report_lines.extend([
            f"\n{'='*80}",
            f"TOTAL VIOLATIONS: {len(violations)}",
            f"ACTION REQUIRED: Fix all violations before proceeding",
            f"{'='*80}\n"
        ])
        
        return '\n'.join(report_lines)
    
    def _format_single_violation(self, violation: SetupMethodInheritanceViolation) -> str:
        """Format a single violation for detailed display."""
        return (
            f"\n  ❌ {violation.test_class_name} ({violation.file_path}:{violation.line_number})\n"
            f"     Problem: {violation.details}\n"
            f"     Fix: {violation.remediation_steps[0] if violation.remediation_steps else 'No remediation provided'}\n"
        )


if __name__ == "__main__":
    # Run the inheritance validation tests
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])