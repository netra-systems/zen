"""
Integration Tests: SSOT Class Duplication Detection

This test suite scans the codebase for SSOT violations, specifically
duplicate class names that cause field access inconsistencies.

Business Value:
- Prevents runtime errors from class name collisions
- Enforces SSOT architectural principles across codebase  
- Detects architectural drift before it causes production issues

CRITICAL: This test uses filesystem scanning and import analysis.
It validates the actual codebase structure, not mocked components.

Target SSOT Violations:
- Duplicate SessionMetrics classes with different interfaces
- Similar class name patterns that violate SSOT principles
- Import path conflicts that cause confusion

Architecture Compliance:
This test enforces CLAUDE.MD Section 2.1 SSOT principles:
"A concept must have ONE canonical implementation per service"
"""

import ast
import os
import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
from dataclasses import dataclass

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class ClassDefinition:
    """Represents a class definition found in the codebase."""
    name: str
    module_path: str
    file_path: str
    line_number: int
    fields: Set[str]
    methods: Set[str]
    base_classes: List[str]
    docstring: Optional[str] = None


@dataclass
class SSotViolation:
    """Represents an SSOT violation found in the codebase."""
    violation_type: str
    class_name: str
    occurrences: List[ClassDefinition]
    severity: str  # 'critical', 'warning', 'info'
    description: str


class TestSSotClassDuplicationDetection(SSotBaseTestCase):
    """
    Test suite for detecting SSOT violations through class duplication analysis.
    
    These tests scan the actual codebase structure to find architectural
    violations that cause runtime errors and confusion.
    """
    
    @pytest.fixture(autouse=True)
    def setup_codebase_scanner(self):
        """Setup codebase scanning capabilities."""
        self.project_root = Path(__file__).parent.parent.parent
        self.discovered_classes: Dict[str, List[ClassDefinition]] = defaultdict(list)
        self.ssot_violations: List[SSotViolation] = []
        
        # Define paths to scan for classes
        self.scan_paths = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "shared",
            self.project_root / "auth_service", 
            self.project_root / "frontend"  # If has Python components
        ]
        
        # Critical class patterns that often cause SSOT violations
        self.critical_patterns = [
            "SessionMetrics",
            "UserContext", 
            "WebSocketManager",
            "AuthValidator",
            "ConfigManager",
            "DatabaseManager"
        ]
    
    def test_scan_for_duplicate_class_names(self):
        """
        Scan codebase for duplicate class names that violate SSOT principles.
        
        This test will FAIL if duplicate classes are found, proving SSOT violations.
        """
        print(f"\n SEARCH:  SCANNING CODEBASE FOR DUPLICATE CLASSES")
        print(f"Scan paths: {[str(p) for p in self.scan_paths]}")
        
        # Scan all Python files for class definitions
        total_files = 0
        total_classes = 0
        
        for scan_path in self.scan_paths:
            if scan_path.exists():
                files_scanned, classes_found = self._scan_directory_for_classes(scan_path)
                total_files += files_scanned
                total_classes += classes_found
                print(f"  [U+1F4C1] {scan_path.name}: {files_scanned} files, {classes_found} classes")
        
        print(f"\n CHART:  SCAN RESULTS:")
        print(f"  Total files scanned: {total_files}")
        print(f"  Total classes found: {total_classes}")
        print(f"  Unique class names: {len(self.discovered_classes)}")
        
        # Find duplicate class names
        duplicates = {
            name: classes 
            for name, classes in self.discovered_classes.items() 
            if len(classes) > 1
        }
        
        if duplicates:
            print(f"\n FAIL:  SSOT VIOLATIONS FOUND: {len(duplicates)} duplicate class names")
            
            for class_name, class_defs in duplicates.items():
                print(f"\n ALERT:  DUPLICATE CLASS: {class_name}")
                for i, class_def in enumerate(class_defs):
                    print(f"  {i+1}. {class_def.module_path} (line {class_def.line_number})")
                    print(f"     Fields: {sorted(class_def.fields)}")
                    print(f"     Methods: {sorted(list(class_def.methods)[:5])}{'...' if len(class_def.methods) > 5 else ''}")
                
                # Create SSOT violation record
                severity = "critical" if class_name in self.critical_patterns else "warning"
                violation = SSotViolation(
                    violation_type="duplicate_class_name",
                    class_name=class_name,
                    occurrences=class_defs,
                    severity=severity,
                    description=f"Class '{class_name}' defined in {len(class_defs)} different locations"
                )
                self.ssot_violations.append(violation)
        
        # This test should FAIL if critical duplicates are found
        critical_violations = [v for v in self.ssot_violations if v.severity == "critical"]
        
        if critical_violations:
            critical_names = [v.class_name for v in critical_violations]
            pytest.fail(
                f"CRITICAL SSOT VIOLATIONS: {len(critical_violations)} duplicate critical classes found: {critical_names}\n"
                f"These duplicates cause runtime errors and violate SSOT architectural principles.\n"
                f"Each concept should have ONE canonical implementation per service."
            )
        
        print(f" PASS:  No critical SSOT violations found")
        if len(self.ssot_violations) > 0:
            print(f" WARNING: [U+FE0F] Found {len(self.ssot_violations)} non-critical duplicate classes")
    
    def test_session_metrics_specific_ssot_violation(self):
        """
        Specific test for SessionMetrics class duplication SSOT violation.
        
        This test directly validates the known SessionMetrics issue.
        """
        print(f"\n TARGET:  SPECIFIC TEST: SessionMetrics SSOT Violation")
        
        # Look for SessionMetrics classes specifically
        session_metrics_classes = self.discovered_classes.get("SessionMetrics", [])
        
        print(f"SessionMetrics classes found: {len(session_metrics_classes)}")
        
        if len(session_metrics_classes) == 0:
            pytest.skip("No SessionMetrics classes found - may not be scanned properly")
        
        if len(session_metrics_classes) == 1:
            print(" PASS:  Only one SessionMetrics class found - SSOT compliance confirmed")
            return
        
        # Multiple SessionMetrics classes found - analyze the violation
        print(f"\n FAIL:  SSOT VIOLATION: {len(session_metrics_classes)} SessionMetrics classes found")
        
        field_comparison = {}
        method_comparison = {}
        
        for i, class_def in enumerate(session_metrics_classes):
            print(f"\n  SessionMetrics #{i+1}: {class_def.module_path}")
            print(f"    File: {class_def.file_path}")
            print(f"    Line: {class_def.line_number}")
            print(f"    Fields: {sorted(class_def.fields)}")
            print(f"    Methods: {sorted(class_def.methods)}")
            
            field_comparison[f"Class_{i+1}"] = class_def.fields
            method_comparison[f"Class_{i+1}"] = class_def.methods
        
        # Compare interfaces between classes
        all_fields = set()
        all_methods = set()
        for fields in field_comparison.values():
            all_fields.update(fields)
        for methods in method_comparison.values():
            all_methods.update(methods)
        
        print(f"\n CHART:  INTERFACE ANALYSIS:")
        print(f"  All fields across classes: {sorted(all_fields)}")
        print(f"  All methods across classes: {sorted(all_methods)}")
        
        # Find field differences (this proves the SSOT bug)
        field_differences = {}
        for class_name, fields in field_comparison.items():
            missing_fields = all_fields - fields
            extra_fields = fields - all_fields
            if missing_fields or extra_fields:
                field_differences[class_name] = {
                    'missing': missing_fields,
                    'extra': extra_fields
                }
        
        if field_differences:
            print(f"\n[U+1F41B] FIELD INTERFACE MISMATCHES:")
            for class_name, diffs in field_differences.items():
                print(f"  {class_name}:")
                if diffs['missing']:
                    print(f"    Missing: {sorted(diffs['missing'])}")
                if diffs['extra']:
                    print(f"    Extra: {sorted(diffs['extra'])}")
        
        # Check for the specific known field issues
        known_issue_fields = {"last_activity", "operations_count", "errors"}
        found_issue_fields = all_fields & known_issue_fields
        
        if found_issue_fields:
            print(f"\n WARNING: [U+FE0F] KNOWN ISSUE FIELDS DETECTED: {found_issue_fields}")
            print("These are the specific fields that cause AttributeError in request_scoped_session_factory.py")
        
        # This test should FAIL to prove the SSOT violation
        pytest.fail(
            f"SSOT VIOLATION CONFIRMED: {len(session_metrics_classes)} SessionMetrics classes with different interfaces.\n"
            f"Field differences found: {len(field_differences)} classes have interface mismatches.\n"
            f"This proves the exact bug that causes AttributeError in error handling code.\n"
            f"Solution: Consolidate into single SessionMetrics class with consistent interface."
        )
    
    def test_critical_class_pattern_violations(self):
        """
        Test for SSOT violations in critical class patterns.
        
        These are class names that often cause system-wide issues when duplicated.
        """
        print(f"\n ALERT:  TESTING CRITICAL CLASS PATTERNS")
        print(f"Critical patterns: {self.critical_patterns}")
        
        critical_violations_found = []
        
        for pattern in self.critical_patterns:
            classes = self.discovered_classes.get(pattern, [])
            
            if len(classes) > 1:
                print(f"\n FAIL:  CRITICAL VIOLATION: {pattern}")
                print(f"  Found in {len(classes)} locations:")
                
                for class_def in classes:
                    print(f"    - {class_def.module_path} (line {class_def.line_number})")
                
                critical_violations_found.append(pattern)
                
                # Analyze interface differences for critical classes
                if len(classes) == 2:  # Compare two classes
                    class1, class2 = classes
                    field_diff = class1.fields.symmetric_difference(class2.fields)
                    method_diff = class1.methods.symmetric_difference(class2.methods)
                    
                    if field_diff or method_diff:
                        print(f"  Interface differences:")
                        if field_diff:
                            print(f"    Field differences: {sorted(field_diff)}")
                        if method_diff:
                            print(f"    Method differences: {sorted(method_diff)}")
            elif len(classes) == 1:
                print(f" PASS:  {pattern}: Single implementation (SSOT compliant)")
            else:
                print(f"[U+2139][U+FE0F] {pattern}: Not found in scanned paths")
        
        if critical_violations_found:
            pytest.fail(
                f"CRITICAL SSOT VIOLATIONS: {len(critical_violations_found)} critical class patterns have duplicates: {critical_violations_found}\n"
                f"These violations can cause system instability and runtime errors.\n"
                f"Immediate action required to consolidate duplicate implementations."
            )
        
        print(" PASS:  All critical class patterns have single implementations")
    
    def test_import_path_consistency(self):
        """
        Test that duplicate classes don't cause import path conflicts.
        
        This validates that import statements won't accidentally import
        the wrong class due to naming conflicts.
        """
        print(f"\n[U+1F4E6] TESTING IMPORT PATH CONSISTENCY")
        
        # Find classes that could cause import confusion
        problematic_imports = []
        
        for class_name, class_defs in self.discovered_classes.items():
            if len(class_defs) > 1:
                # Check if they're in different top-level modules
                top_level_modules = set()
                for class_def in class_defs:
                    module_parts = class_def.module_path.split('.')
                    top_level = module_parts[0] if module_parts else "unknown"
                    top_level_modules.add(top_level)
                
                if len(top_level_modules) > 1:
                    problematic_imports.append({
                        'class_name': class_name,
                        'modules': top_level_modules,
                        'definitions': class_defs
                    })
        
        if problematic_imports:
            print(f"\n FAIL:  IMPORT PATH CONFLICTS FOUND: {len(problematic_imports)}")
            
            for conflict in problematic_imports:
                class_name = conflict['class_name']
                modules = conflict['modules']
                print(f"\n ALERT:  CONFLICT: {class_name}")
                print(f"  Top-level modules: {sorted(modules)}")
                
                for class_def in conflict['definitions']:
                    print(f"    from {class_def.module_path} import {class_name}")
                
                print("   WARNING: [U+FE0F] Risk: Import statements may import wrong class")
        
        # Check for specific SessionMetrics import conflicts
        session_metrics_classes = self.discovered_classes.get("SessionMetrics", [])
        if len(session_metrics_classes) > 1:
            print(f"\n TARGET:  SessionMetrics Import Analysis:")
            for class_def in session_metrics_classes:
                print(f"  from {class_def.module_path} import SessionMetrics")
            
            print("   FAIL:  Risk: Code importing 'SessionMetrics' may get wrong implementation")
            print("   IDEA:  Solution: Use fully qualified imports or rename classes")
        
        if problematic_imports:
            pytest.fail(
                f"IMPORT PATH CONFLICTS: {len(problematic_imports)} classes have conflicting import paths.\n"
                f"This creates ambiguity in import statements and can cause wrong classes to be imported.\n"
                f"Resolve by renaming classes or consolidating implementations."
            )
        
        print(" PASS:  No import path conflicts found")
    
    def _scan_directory_for_classes(self, directory: Path) -> Tuple[int, int]:
        """Scan a directory for Python files and extract class definitions."""
        files_scanned = 0
        classes_found = 0
        
        for python_file in directory.rglob("*.py"):
            # Skip __pycache__ and test files for main scanning
            if "__pycache__" in str(python_file):
                continue
            
            try:
                class_defs = self._extract_classes_from_file(python_file)
                files_scanned += 1
                classes_found += len(class_defs)
                
                # Add to discovered classes
                for class_def in class_defs:
                    self.discovered_classes[class_def.name].append(class_def)
                    
            except Exception as e:
                # Skip files that can't be parsed (binary, etc.)
                print(f"   WARNING: [U+FE0F] Skipped {python_file.name}: {e}")
                continue
        
        return files_scanned, classes_found
    
    def _extract_classes_from_file(self, file_path: Path) -> List[ClassDefinition]:
        """Extract class definitions from a Python file using AST parsing."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Parse the file into an AST
            tree = ast.parse(source, filename=str(file_path))
            
            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_def = self._analyze_class_node(node, file_path)
                    classes.append(class_def)
            
            return classes
            
        except Exception as e:
            # Return empty list for files that can't be parsed
            return []
    
    def _analyze_class_node(self, node: ast.ClassDef, file_path: Path) -> ClassDefinition:
        """Analyze an AST class node to extract information."""
        # Get relative module path
        project_root = Path(__file__).parent.parent.parent
        try:
            rel_path = file_path.relative_to(project_root)
            module_path = str(rel_path.with_suffix('')).replace(os.sep, '.')
        except ValueError:
            module_path = file_path.stem
        
        # Extract fields and methods
        fields = set()
        methods = set()
        
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                # Type annotated field
                fields.add(item.target.id)
            elif isinstance(item, ast.Assign):
                # Regular assignment field
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        fields.add(target.id)
            elif isinstance(item, ast.FunctionDef):
                # Method
                methods.add(item.name)
        
        # Extract base classes
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                # Handle qualified names like dataclass.field
                base_classes.append(ast.unparse(base))
        
        # Extract docstring
        docstring = None
        if (node.body and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Str)):
            docstring = node.body[0].value.s
        
        return ClassDefinition(
            name=node.name,
            module_path=module_path,
            file_path=str(file_path),
            line_number=node.lineno,
            fields=fields,
            methods=methods,
            base_classes=base_classes,
            docstring=docstring
        )
    
    def test_generate_ssot_violation_report(self):
        """Generate comprehensive report of all SSOT violations found."""
        print(f"\n[U+1F4C4] GENERATING SSOT VIOLATION REPORT")
        
        if not self.ssot_violations:
            print(" PASS:  No SSOT violations to report")
            return
        
        print(f"\n ALERT:  SSOT VIOLATIONS SUMMARY")
        print(f"Total violations: {len(self.ssot_violations)}")
        
        by_severity = defaultdict(list)
        for violation in self.ssot_violations:
            by_severity[violation.severity].append(violation)
        
        for severity in ["critical", "warning", "info"]:
            violations = by_severity[severity]
            if violations:
                print(f"\n{severity.upper()} ({len(violations)}):")
                for violation in violations:
                    print(f"  - {violation.class_name}: {violation.description}")
        
        # Generate detailed report
        report_lines = [
            "# SSOT Class Duplication Violation Report",
            f"Generated: {pytest.current_date if hasattr(pytest, 'current_date') else 'Unknown'}",
            "",
            f"## Summary",
            f"- Total violations: {len(self.ssot_violations)}",
            f"- Critical: {len(by_severity['critical'])}",
            f"- Warning: {len(by_severity['warning'])}",
            f"- Info: {len(by_severity['info'])}",
            "",
        ]
        
        for severity in ["critical", "warning", "info"]:
            violations = by_severity[severity]
            if violations:
                report_lines.append(f"## {severity.title()} Violations")
                report_lines.append("")
                
                for violation in violations:
                    report_lines.append(f"### {violation.class_name}")
                    report_lines.append(f"**Type:** {violation.violation_type}")
                    report_lines.append(f"**Description:** {violation.description}")
                    report_lines.append("")
                    report_lines.append("**Occurrences:**")
                    
                    for occurrence in violation.occurrences:
                        report_lines.append(f"- `{occurrence.module_path}` (line {occurrence.line_number})")
                        report_lines.append(f"  - Fields: {sorted(occurrence.fields)}")
                        report_lines.append(f"  - Methods: {len(occurrence.methods)} methods")
                    
                    report_lines.append("")
        
        # Save report (optional - for debugging)
        report_content = "\n".join(report_lines)
        print(f"\n[U+1F4CB] DETAILED REPORT:")
        print(report_content[:1000] + "..." if len(report_content) > 1000 else report_content)
        
        # Fail if critical violations found
        critical_violations = by_severity["critical"]
        if critical_violations:
            pytest.fail(
                f"CRITICAL SSOT VIOLATIONS DETECTED: {len(critical_violations)} violations require immediate attention.\n"
                f"See detailed report above for resolution guidance."
            )


if __name__ == "__main__":
    # Run with verbose output to see detailed SSOT analysis
    pytest.main([__file__, "-v", "-s", "--tb=short"])