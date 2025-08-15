#!/usr/bin/env python3
"""
🔴 BOUNDARY ENFORCER 🔴
Ultra Deep Thinking Approach to Growth Control

CRITICAL MISSION: Stop unhealthy system growth permanently
Enforces MANDATORY architectural boundaries from CLAUDE.md:
- File lines ≤300 (HARD LIMIT)
- Function lines ≤8 (HARD LIMIT)  
- Module count ≤700 (SYSTEM LIMIT)
- Total LOC ≤200,000 (CODEBASE LIMIT)
- Complexity score ≤3 (MAINTAINABILITY LIMIT)

Enhanced with real-time monitoring, auto-split suggestions, and CI/CD gates.
"""

import ast
import glob
import json
import os
import sys
import time
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict, Optional, Union, Set
from pathlib import Path

try:
    import radon.complexity as radon_cc
    HAS_RADON = True
except ImportError:
    HAS_RADON = False
    print("Warning: radon not installed. Install with: pip install radon")

@dataclass
class BoundaryViolation:
    """Enhanced violation with boundary context"""
    file_path: str
    violation_type: str
    severity: str
    boundary_name: str
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    actual_value: Optional[int] = None
    expected_value: Optional[int] = None
    description: str = ""
    fix_suggestion: str = ""
    auto_split_suggestion: Optional[str] = None
    impact_score: int = 1  # 1-10 scale

@dataclass
class SystemBoundaries:
    """System-wide boundary definitions"""
    max_file_lines: int = 300
    max_function_lines: int = 8
    max_module_count: int = 700
    max_total_loc: int = 200000
    max_complexity_score: float = 3.0
    max_duplicate_types: int = 0
    max_test_stubs: int = 0

@dataclass
class BoundaryReport:
    """Complete boundary enforcement report"""
    total_violations: int
    boundary_compliance_score: float
    growth_risk_level: str
    timestamp: str
    violations_by_boundary: Dict[str, int]
    violations: List[BoundaryViolation]
    system_metrics: Dict[str, Union[int, float, str]]
    remediation_plan: List[str]
    emergency_actions: List[str]

class BoundaryEnforcer:
    """Ultra thinking boundary enforcer for system growth control"""
    
    def __init__(self, root_path: str = ".", boundaries: SystemBoundaries = None):
        self.root_path = Path(root_path)
        self.boundaries = boundaries or SystemBoundaries()
        self.violations: List[BoundaryViolation] = []
        self.system_metrics = {}
        
    def enforce_all_boundaries(self) -> BoundaryReport:
        """Enforce all system boundaries with ultra deep analysis"""
        self._collect_system_metrics()
        self._check_file_line_boundaries()
        self._check_function_line_boundaries()
        self._check_module_count_boundary()
        self._check_total_loc_boundary()
        self._check_complexity_boundaries()
        self._check_duplicate_type_boundaries()
        self._check_test_stub_boundaries()
        return self._generate_boundary_report()
    
    def _collect_system_metrics(self) -> None:
        """Collect comprehensive system metrics"""
        file_metrics = self._count_system_files()
        growth_metrics = self._calculate_advanced_metrics()
        self.system_metrics = self._build_metrics_dict(file_metrics, growth_metrics)

    def _get_file_patterns(self) -> List[str]:
        """Get file patterns for system metrics collection"""
        return [
            'app/**/*.py', 'frontend/**/*.tsx', 'frontend/**/*.ts', 
            'scripts/**/*.py', 'test_framework/**/*.py'
        ]

    def _count_system_files(self) -> Dict[str, int]:
        """Count files and lines across system patterns"""
        total_files, total_lines, module_count = 0, 0, 0
        for pattern in self._get_file_patterns():
            file_count, line_count = self._count_pattern_files(pattern)
            total_files += file_count
            total_lines += line_count
            module_count += file_count
        return {"total_files": total_files, "total_lines": total_lines, "module_count": module_count}

    def _count_pattern_files(self, pattern: str) -> Tuple[int, int]:
        """Count files and lines for a specific glob pattern"""
        file_count, line_count = 0, 0
        for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
            if self._should_skip_file(filepath):
                continue
            file_count += 1
            line_count += self._count_file_lines(filepath)
        return file_count, line_count

    def _count_file_lines(self, filepath: str) -> int:
        """Count lines in a single file safely"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except Exception:
            return 0

    def _calculate_advanced_metrics(self) -> Dict[str, float]:
        """Calculate advanced growth and complexity metrics"""
        return {
            "growth_velocity": self._calculate_growth_velocity(),
            "complexity_debt": self._calculate_complexity_debt()
        }

    def _build_metrics_dict(self, file_metrics: Dict[str, int], growth_metrics: Dict[str, float]) -> Dict[str, Union[int, float]]:
        """Build final metrics dictionary combining all metrics"""
        avg_file_size = file_metrics["total_lines"] / file_metrics["total_files"] if file_metrics["total_files"] > 0 else 0
        return {
            **file_metrics,
            "avg_file_size": avg_file_size,
            **growth_metrics
        }
    
    def _calculate_growth_velocity(self) -> float:
        """Calculate system growth velocity using git stats"""
        try:
            result = subprocess.run(
                ['git', 'log', '--oneline', '--since="30 days ago"'],
                capture_output=True, text=True, cwd=self.root_path
            )
            commits_last_month = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            
            result = subprocess.run(
                ['git', 'diff', '--stat', 'HEAD~10', 'HEAD'],
                capture_output=True, text=True, cwd=self.root_path
            )
            lines_changed = self._extract_lines_changed(result.stdout)
            
            return commits_last_month * 0.1 + lines_changed * 0.001
        except Exception:
            return 0.0
    
    def _extract_lines_changed(self, git_output: str) -> int:
        """Extract line changes from git diff output"""
        match = re.search(r'(\d+) insertions?\(\+\)', git_output)
        insertions = int(match.group(1)) if match else 0
        match = re.search(r'(\d+) deletions?\(-\)', git_output)
        deletions = int(match.group(1)) if match else 0
        return insertions + deletions
    
    def _calculate_complexity_debt(self) -> float:
        """Calculate total complexity debt across system"""
        if not HAS_RADON:
            return 0.0  # Fallback when radon not available
            
        total_complexity = 0
        file_count = 0
        
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if self._should_skip_file(filepath):
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    complexity_scores = radon_cc.cc_visit(content)
                    for score in complexity_scores:
                        total_complexity += score.complexity
                    file_count += 1
            except Exception:
                continue
        
        return total_complexity / file_count if file_count > 0 else 0.0
    
    def _check_file_line_boundaries(self) -> None:
        """Check file line boundaries with split suggestions"""
        patterns = ['app/**/*.py', 'frontend/**/*.tsx', 'frontend/**/*.ts', 'scripts/**/*.py']
        for pattern in patterns:
            self._check_pattern_file_boundaries(pattern)

    def _check_pattern_file_boundaries(self, pattern: str) -> None:
        """Check file boundaries for a specific glob pattern"""
        for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
            if self._should_skip_file(filepath):
                continue
            self._validate_single_file_boundary(filepath)

    def _validate_single_file_boundary(self, filepath: str) -> None:
        """Validate boundary for a single file"""
        lines = self._get_file_line_count(filepath)
        if lines is None or lines <= self.boundaries.max_file_lines:
            return
        self._create_file_boundary_violation(filepath, lines)

    def _get_file_line_count(self, filepath: str) -> Optional[int]:
        """Get line count for file, return None on error"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except Exception:
            return None

    def _create_file_boundary_violation(self, filepath: str, lines: int) -> None:
        """Create a file boundary violation entry"""
        rel_path = str(Path(filepath).relative_to(self.root_path))
        split_suggestion = self._generate_file_split_suggestion(filepath, lines)
        violation = self._build_file_violation_object(rel_path, lines, split_suggestion)
        self.violations.append(violation)

    def _build_file_violation_object(self, rel_path: str, lines: int, split_suggestion: str) -> BoundaryViolation:
        """Build file boundary violation object"""
        return BoundaryViolation(
            file_path=rel_path, violation_type="file_line_boundary", severity="critical",
            boundary_name="FILE_SIZE_LIMIT", actual_value=lines, expected_value=self.boundaries.max_file_lines,
            description=f"File exceeds {self.boundaries.max_file_lines} line HARD LIMIT",
            fix_suggestion=f"MANDATORY: Split into {(lines // self.boundaries.max_file_lines) + 1} modules",
            auto_split_suggestion=split_suggestion, impact_score=min(10, lines // 100)
        )
    
    def _generate_file_split_suggestion(self, filepath: str, lines: int) -> str:
        """Generate intelligent file split suggestions"""
        tree = self._parse_file_ast(filepath)
        if tree is None:
            return "Unable to analyze - manual split required"
        classes, functions = self._extract_ast_nodes(tree)
        suggestions = self._build_split_suggestions(classes, functions)
        return " | ".join(suggestions) if suggestions else "Consider splitting by logical boundaries"

    def _extract_ast_nodes(self, tree: ast.AST) -> Tuple[List[str], List[str]]:
        """Extract classes and functions from AST"""
        classes, functions = [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(f"class {node.name} (line {node.lineno})")
            elif isinstance(node, ast.FunctionDef):
                functions.append(f"function {node.name} (line {node.lineno})")
        return classes, functions

    def _build_split_suggestions(self, classes: List[str], functions: List[str]) -> List[str]:
        """Build split suggestions from extracted nodes"""
        suggestions = []
        if classes:
            suggestions.append(f"Split by classes: {', '.join(classes[:3])}")
        if functions:
            suggestions.append(f"Split by functions: {', '.join(functions[:3])}")
        return suggestions
    
    def _check_function_line_boundaries(self) -> None:
        """Check function line boundaries with refactor suggestions"""
        patterns = ['app/**/*.py', 'scripts/**/*.py']
        for pattern in patterns:
            self._check_pattern_function_boundaries(pattern)

    def _check_pattern_function_boundaries(self, pattern: str) -> None:
        """Check function boundaries for a specific glob pattern"""
        for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
            if self._should_skip_file(filepath):
                continue
            self._validate_file_function_boundaries(filepath)

    def _validate_file_function_boundaries(self, filepath: str) -> None:
        """Validate function boundaries for a single file"""
        tree = self._parse_file_ast(filepath)
        if tree is None:
            return
        rel_path = str(Path(filepath).relative_to(self.root_path))
        self._check_ast_function_nodes(tree, rel_path)

    def _parse_file_ast(self, filepath: str) -> Optional[ast.AST]:
        """Parse file to AST, return None on error"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return ast.parse(f.read())
        except Exception:
            return None

    def _check_ast_function_nodes(self, tree: ast.AST, rel_path: str) -> None:
        """Check all function nodes in AST for boundary violations"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._validate_function_node_boundary(node, rel_path)

    def _validate_function_node_boundary(self, node: ast.FunctionDef, rel_path: str) -> None:
        """Validate boundary for a single function node"""
        lines = self._count_function_lines(node)
        if lines <= self.boundaries.max_function_lines:
            return
        self._create_function_boundary_violation(node, lines, rel_path)

    def _create_function_boundary_violation(self, node: ast.FunctionDef, lines: int, rel_path: str) -> None:
        """Create a function boundary violation entry"""
        refactor_suggestion = self._generate_function_refactor_suggestion(node, lines)
        violation = self._build_function_violation_object(node, lines, rel_path, refactor_suggestion)
        self.violations.append(violation)

    def _build_function_violation_object(self, node: ast.FunctionDef, lines: int, rel_path: str, refactor_suggestion: str) -> BoundaryViolation:
        """Build function boundary violation object"""
        return BoundaryViolation(
            file_path=rel_path, violation_type="function_line_boundary", severity="critical",
            boundary_name="FUNCTION_SIZE_LIMIT", line_number=node.lineno, function_name=node.name,
            actual_value=lines, expected_value=self.boundaries.max_function_lines,
            description=f"Function exceeds {self.boundaries.max_function_lines} line HARD LIMIT",
            fix_suggestion=f"MANDATORY: Split into {(lines // self.boundaries.max_function_lines) + 1} functions",
            auto_split_suggestion=refactor_suggestion, impact_score=min(10, lines // 2)
        )
    
    def _generate_function_refactor_suggestion(self, node: ast.FunctionDef, lines: int) -> str:
        """Generate intelligent function refactoring suggestions"""
        if not hasattr(node, 'body') or len(node.body) == 0:
            return "Requires manual refactoring"
        structure_analysis = self._analyze_function_structure(node)
        suggestions = self._build_refactor_suggestions(structure_analysis, lines)
        return " | ".join(suggestions) if suggestions else "Requires manual refactoring"

    def _analyze_function_structure(self, node: ast.FunctionDef) -> Dict[str, bool]:
        """Analyze function structure for refactoring suggestions"""
        return {
            "has_conditions": any(isinstance(n, (ast.If, ast.While, ast.For)) for n in ast.walk(node)),
            "has_try_except": any(isinstance(n, ast.Try) for n in ast.walk(node))
        }

    def _build_refactor_suggestions(self, analysis: Dict[str, bool], lines: int) -> List[str]:
        """Build refactoring suggestions based on analysis"""
        suggestions = []
        if analysis["has_conditions"]:
            suggestions.append("Extract conditional logic into helper functions")
        if analysis["has_try_except"]:
            suggestions.append("Extract error handling into separate function")
        suggestions.append(self._get_size_based_suggestion(lines))
        return suggestions

    def _get_size_based_suggestion(self, lines: int) -> str:
        """Get refactoring suggestion based on function size"""
        if lines > 15:
            return "Break into validation + processing + result functions"
        return "Split into 2-3 smaller focused functions"
    
    def _check_module_count_boundary(self) -> None:
        """Check module count boundary"""
        if self.system_metrics["module_count"] <= self.boundaries.max_module_count:
            return
        violation = self._create_module_count_violation()
        self.violations.append(violation)

    def _create_module_count_violation(self) -> BoundaryViolation:
        """Create module count boundary violation"""
        return BoundaryViolation(
            file_path="SYSTEM_WIDE", violation_type="module_count_boundary", severity="critical",
            boundary_name="MODULE_COUNT_LIMIT", actual_value=self.system_metrics["module_count"],
            expected_value=self.boundaries.max_module_count, impact_score=10,
            description=f"System exceeds {self.boundaries.max_module_count} module HARD LIMIT",
            fix_suggestion="EMERGENCY: Archive unused modules, consolidate similar modules"
        )
    
    def _check_total_loc_boundary(self) -> None:
        """Check total lines of code boundary"""
        if self.system_metrics["total_lines"] <= self.boundaries.max_total_loc:
            return
        violation = self._create_total_loc_violation()
        self.violations.append(violation)

    def _create_total_loc_violation(self) -> BoundaryViolation:
        """Create total LOC boundary violation"""
        return BoundaryViolation(
            file_path="SYSTEM_WIDE", violation_type="total_loc_boundary", severity="critical",
            boundary_name="TOTAL_LOC_LIMIT", actual_value=self.system_metrics["total_lines"],
            expected_value=self.boundaries.max_total_loc, impact_score=10,
            description=f"System exceeds {self.boundaries.max_total_loc} LOC HARD LIMIT",
            fix_suggestion="EMERGENCY: Remove deprecated code, refactor duplicates"
        )
    
    def _check_complexity_boundaries(self) -> None:
        """Check complexity score boundaries"""
        avg_complexity = self.system_metrics.get("complexity_debt", 0)
        if avg_complexity <= self.boundaries.max_complexity_score:
            return
        violation = self._create_complexity_violation(avg_complexity)
        self.violations.append(violation)

    def _create_complexity_violation(self, avg_complexity: float) -> BoundaryViolation:
        """Create complexity boundary violation"""
        return BoundaryViolation(
            file_path="SYSTEM_WIDE", violation_type="complexity_boundary", severity="high",
            boundary_name="COMPLEXITY_LIMIT", impact_score=8,
            actual_value=int(avg_complexity * 100), expected_value=int(self.boundaries.max_complexity_score * 100),
            description=f"System complexity exceeds {self.boundaries.max_complexity_score} LIMIT",
            fix_suggestion="Refactor complex functions, simplify logic paths"
        )
    
    def _check_duplicate_type_boundaries(self) -> None:
        """Check for duplicate types across system"""
        type_definitions = defaultdict(list)
        self._collect_python_type_definitions(type_definitions)
        self._collect_typescript_type_definitions(type_definitions)
        self._create_duplicate_type_violations(type_definitions)

    def _collect_python_type_definitions(self, type_definitions: Dict[str, List[str]]) -> None:
        """Collect Python class definitions from app files"""
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if self._should_skip_file(filepath):
                continue
            self._extract_python_types(filepath, type_definitions)

    def _extract_python_types(self, filepath: str, type_definitions: Dict[str, List[str]]) -> None:
        """Extract Python type definitions from a single file"""
        content = self._read_file_safely(filepath)
        if content is None:
            return
        rel_path = str(Path(filepath).relative_to(self.root_path))
        for match in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
            type_name = match.group(1)
            type_definitions[type_name].append(rel_path)

    def _collect_typescript_type_definitions(self, type_definitions: Dict[str, List[str]]) -> None:
        """Collect TypeScript type definitions from frontend files"""
        for pattern in ['frontend/**/*.ts', 'frontend/**/*.tsx']:
            for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
                if 'node_modules' in filepath:
                    continue
                self._extract_typescript_types(filepath, type_definitions)

    def _extract_typescript_types(self, filepath: str, type_definitions: Dict[str, List[str]]) -> None:
        """Extract TypeScript type definitions from a single file"""
        content = self._read_file_safely(filepath)
        if content is None:
            return
        rel_path = str(Path(filepath).relative_to(self.root_path))
        for match in re.finditer(r'(?:interface|type)\s+(\w+)', content):
            type_name = match.group(1)
            type_definitions[type_name].append(rel_path)

    def _create_duplicate_type_violations(self, type_definitions: Dict[str, List[str]]) -> None:
        """Create violations for duplicate type definitions"""
        for type_name, files in type_definitions.items():
            if len(files) > 1:
                violation = self._build_duplicate_type_violation(type_name, files)
                self.violations.append(violation)

    def _build_duplicate_type_violation(self, type_name: str, files: List[str]) -> BoundaryViolation:
        """Build duplicate type violation object"""
        file_list = ", ".join(files[:2]) + ("..." if len(files) > 2 else "")
        return BoundaryViolation(
            file_path=file_list, violation_type="duplicate_type_boundary", severity="medium",
            boundary_name="NO_DUPLICATE_TYPES", actual_value=len(files), expected_value=1,
            description=f"Duplicate type '{type_name}' violates SINGLE SOURCE OF TRUTH",
            fix_suggestion=f"Consolidate '{type_name}' into shared module", impact_score=3
        )
    
    def _check_test_stub_boundaries(self) -> None:
        """Check for test stubs in production code"""
        suspicious_patterns = self._get_test_stub_patterns()
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if self._should_skip_test_file(filepath):
                continue
            self._scan_file_for_test_stubs(filepath, suspicious_patterns)

    def _get_test_stub_patterns(self) -> List[Tuple[str, str]]:
        """Get patterns that indicate test stubs in production code"""
        return [
            (r'# Mock implementation', 'Mock implementation comment'),
            (r'# Test stub', 'Test stub comment'),
            (r'# TODO.*implement', 'TODO implementation comment'),
            (r'return \[{"id": "1"', 'Hardcoded test data'),
            (r'raise NotImplementedError', 'Not implemented error')
        ]

    def _should_skip_test_file(self, filepath: str) -> bool:
        """Check if file should be skipped from test stub analysis"""
        skip_indicators = ['__pycache__', 'app/tests', '/tests/']
        return any(indicator in filepath for indicator in skip_indicators)

    def _scan_file_for_test_stubs(self, filepath: str, patterns: List[Tuple[str, str]]) -> None:
        """Scan a single file for test stub patterns"""
        content = self._read_file_safely(filepath)
        if content is None:
            return
        rel_path = str(Path(filepath).relative_to(self.root_path))
        self._check_patterns_in_content(content, rel_path, patterns)

    def _read_file_safely(self, filepath: str) -> Optional[str]:
        """Read file content safely, return None on error"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None

    def _check_patterns_in_content(self, content: str, rel_path: str, patterns: List[Tuple[str, str]]) -> None:
        """Check all patterns in file content and create violations"""
        for pattern, description in patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE | re.DOTALL))
            if matches:
                line_number = content[:matches[0].start()].count('\n') + 1
                self._create_test_stub_violation(rel_path, line_number, description)
                break  # Only report first match per file

    def _create_test_stub_violation(self, rel_path: str, line_number: int, description: str) -> None:
        """Create test stub boundary violation"""
        violation = BoundaryViolation(
            file_path=rel_path, violation_type="test_stub_boundary", severity="critical",
            boundary_name="NO_TEST_STUBS", line_number=line_number, impact_score=7,
            description=f"Test stub in production: {description}",
            fix_suggestion="Replace with production implementation"
        )
        self.violations.append(violation)
    
    def _should_skip_file(self, filepath: str) -> bool:
        """Check if file should be skipped from analysis"""
        skip_patterns = [
            '__pycache__', 'node_modules', '.git', 'migrations',
            'test_reports', 'docs', '.pytest_cache', 'venv',
            '.venv', 'env', '.env', 'dist', 'build'
        ]
        return any(pattern in filepath for pattern in skip_patterns)
    
    def _count_function_lines(self, node: ast.FunctionDef) -> int:
        """Count actual code lines in function (excluding docstrings)"""
        if not node.body:
            return 0
        start_idx = self._get_function_start_index(node)
        if start_idx >= len(node.body):
            return 0
        return self._calculate_function_line_count(node, start_idx)

    def _get_function_start_index(self, node: ast.FunctionDef) -> int:
        """Get the starting index after docstring (if present)"""
        if (len(node.body) > 0 and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, (ast.Constant, ast.Str))):
            return 1
        return 0

    def _calculate_function_line_count(self, node: ast.FunctionDef, start_idx: int) -> int:
        """Calculate line count from start index to last statement"""
        first_line = node.body[start_idx].lineno
        last_statement = node.body[-1]
        last_line = getattr(last_statement, 'end_lineno', last_statement.lineno)
        return last_line - first_line + 1
    
    def _generate_boundary_report(self) -> BoundaryReport:
        """Generate comprehensive boundary enforcement report"""
        violations_by_boundary = self._count_violations_by_boundary()
        emergency_actions = self._collect_emergency_actions()
        risk_level, remediation_plan = self._assess_growth_risk(emergency_actions)
        compliance_score = self._calculate_compliance_score(violations_by_boundary)
        return self._build_boundary_report_object(violations_by_boundary, emergency_actions, risk_level, remediation_plan, compliance_score)

    def _count_violations_by_boundary(self) -> Dict[str, int]:
        """Count violations grouped by boundary type"""
        violations_by_boundary = defaultdict(int)
        for violation in self.violations:
            violations_by_boundary[violation.boundary_name] += 1
        return violations_by_boundary

    def _collect_emergency_actions(self) -> List[str]:
        """Collect emergency actions from critical violations"""
        emergency_actions = []
        for violation in self.violations:
            if violation.severity == "critical" and violation.impact_score >= 8:
                emergency_actions.append(f"EMERGENCY: {violation.fix_suggestion}")
        return emergency_actions

    def _assess_growth_risk(self, emergency_actions: List[str]) -> Tuple[str, List[str]]:
        """Assess growth risk level and generate remediation plan"""
        total_violations = len(self.violations)
        risk_score = sum(v.impact_score for v in self.violations)
        if risk_score > 500 or total_violations > 1000:
            return self._handle_critical_risk(emergency_actions)
        elif risk_score > 200 or total_violations > 500:
            return self._handle_high_risk()
        elif risk_score > 50 or total_violations > 100:
            return "MEDIUM - MONITOR CLOSELY", ["Weekly boundary compliance checks"]
        return "LOW - MANAGEABLE", []

    def _handle_critical_risk(self, emergency_actions: List[str]) -> Tuple[str, List[str]]:
        """Handle critical risk level response"""
        emergency_actions.extend([
            "IMMEDIATE: Stop all new feature development",
            "IMMEDIATE: Begin emergency refactoring sprint"
        ])
        return "CRITICAL - SYSTEM UNSTABLE", []

    def _handle_high_risk(self) -> Tuple[str, List[str]]:
        """Handle high risk level response"""
        return "HIGH - REQUIRES INTERVENTION", [
            "Schedule architecture review within 1 week",
            "Implement daily boundary monitoring"
        ]

    def _calculate_compliance_score(self, violations_by_boundary: Dict[str, int]) -> float:
        """Calculate boundary compliance score"""
        total_possible_violations = 7  # Number of boundary types
        return max(0, (total_possible_violations - len(violations_by_boundary)) / total_possible_violations * 100)

    def _build_boundary_report_object(self, violations_by_boundary: Dict[str, int], emergency_actions: List[str], 
                                    risk_level: str, remediation_plan: List[str], compliance_score: float) -> BoundaryReport:
        """Build the final boundary report object"""
        if not emergency_actions:
            remediation_plan.extend(["Continue enforcing pre-commit hooks", "Maintain CI/CD boundary gates", "Regular automated compliance monitoring"])
        return BoundaryReport(
            total_violations=len(self.violations), boundary_compliance_score=compliance_score, growth_risk_level=risk_level,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"), violations_by_boundary=dict(violations_by_boundary),
            violations=self.violations, system_metrics=self.system_metrics, remediation_plan=remediation_plan, emergency_actions=emergency_actions
        )
    
    def generate_enforcement_report(self) -> str:
        """Generate human-readable enforcement report"""
        report = self.enforce_all_boundaries()
        self._print_report_header(report)
        self._print_system_metrics(report)
        self._print_boundary_violations(report)
        self._print_emergency_actions(report)
        self._print_remediation_plan(report)
        self._print_critical_violations(report)
        return self._determine_report_status(report)

    def _print_report_header(self, report: BoundaryReport) -> None:
        """Print report header with basic info"""
        print("\n" + "=" * 80)
        print("BOUNDARY ENFORCEMENT REPORT")
        print("=" * 80)
        print(f"Timestamp: {report.timestamp}")
        print(f"Growth Risk Level: {report.growth_risk_level}")
        print(f"Boundary Compliance: {report.boundary_compliance_score:.1f}%")
        print(f"Total Violations: {report.total_violations}")

    def _print_system_metrics(self, report: BoundaryReport) -> None:
        """Print system metrics section"""
        print(f"\n[SYSTEM METRICS]:")
        print(f"  Total Files: {report.system_metrics['total_files']}")
        print(f"  Total Lines: {report.system_metrics['total_lines']:,}")
        print(f"  Module Count: {report.system_metrics['module_count']}")
        print(f"  Avg File Size: {report.system_metrics['avg_file_size']:.1f} lines")
        print(f"  Growth Velocity: {report.system_metrics['growth_velocity']:.2f}")
        print(f"  Complexity Debt: {report.system_metrics['complexity_debt']:.2f}")

    def _print_boundary_violations(self, report: BoundaryReport) -> None:
        """Print boundary violations section"""
        print(f"\n[BOUNDARY VIOLATIONS]:")
        for boundary, count in report.violations_by_boundary.items():
            print(f"  {boundary}: {count} violations")

    def _print_emergency_actions(self, report: BoundaryReport) -> None:
        """Print emergency actions section if needed"""
        if report.emergency_actions:
            print(f"\n[EMERGENCY ACTIONS REQUIRED]:")
            for action in report.emergency_actions:
                print(f"  - {action}")

    def _print_remediation_plan(self, report: BoundaryReport) -> None:
        """Print remediation plan section if needed"""
        if report.remediation_plan:
            print(f"\n[REMEDIATION PLAN]:")
            for action in report.remediation_plan:
                print(f"  - {action}")

    def _print_critical_violations(self, report: BoundaryReport) -> None:
        """Print top critical violations section"""
        print(f"\n[TOP CRITICAL VIOLATIONS]:")
        critical_violations = [v for v in report.violations if v.severity == "critical"]
        self._print_top_violations(critical_violations)

    def _print_top_violations(self, critical_violations: List[BoundaryViolation]) -> None:
        """Print top critical violations with details"""
        top_violations = sorted(critical_violations, key=lambda x: x.impact_score, reverse=True)[:10]
        for i, violation in enumerate(top_violations, 1):
            print(f"  {i}. {violation.description}")
            print(f"     File: {violation.file_path}")
            if violation.auto_split_suggestion:
                print(f"     Auto-fix: {violation.auto_split_suggestion}")

    def _determine_report_status(self, report: BoundaryReport) -> str:
        """Determine final report status"""
        if report.emergency_actions:
            return "FAIL"
        elif report.total_violations > 0:
            return "MONITOR"
        return "PASS"
    
    def generate_pr_comment(self) -> str:
        """Generate PR comment with boundary status"""
        report = self.enforce_all_boundaries()
        status_emoji, status_text, status_color = self._determine_pr_status(report)
        comment = self._build_pr_header(status_emoji, status_text, status_color, report)
        comment += self._build_system_metrics_section(report)
        comment += self._build_boundary_status_section(report)
        comment += self._build_action_sections(report)
        comment += self._build_violations_section(report)
        comment += self._build_tools_section(report)
        return comment

    def _determine_pr_status(self, report: BoundaryReport) -> Tuple[str, str, str]:
        """Determine PR status emoji, text, and color"""
        if report.emergency_actions:
            return "🚨", "EMERGENCY", "red"
        elif report.total_violations > 50:
            return "❌", "FAILING", "red"
        elif report.total_violations > 0:
            return "⚠️", "WARNING", "yellow"
        return "✅", "PASSING", "green"

    def _build_pr_header(self, emoji: str, status_text: str, color: str, report: BoundaryReport) -> str:
        """Build PR comment header section"""
        return f"""# {emoji} Boundary Enforcement Report

**Status:** <span style="color: {color}; font-weight: bold;">{status_text}</span>
**Growth Risk:** {report.growth_risk_level}
**Compliance Score:** {report.boundary_compliance_score:.1f}%
**Total Violations:** {report.total_violations}

"""

    def _build_system_metrics_section(self, report: BoundaryReport) -> str:
        """Build system metrics section"""
        return f"""## System Metrics
- **Total Files:** {report.system_metrics.get('total_files', 0)}
- **Total Lines:** {report.system_metrics.get('total_lines', 0):,}
- **Module Count:** {report.system_metrics.get('module_count', 0)}
- **Growth Velocity:** {report.system_metrics.get('growth_velocity', 0):.2f}

"""

    def _build_boundary_status_section(self, report: BoundaryReport) -> str:
        """Build boundary status section"""
        section = "## Boundary Status\n"
        for boundary, count in report.violations_by_boundary.items():
            emoji = "🔴" if count > 0 else "✅"
            boundary_name = boundary.replace('_', ' ').title()
            section += f"- **{boundary_name}:** {emoji} {count} violations\n"
        return section + "\n"

    def _build_action_sections(self, report: BoundaryReport) -> str:
        """Build emergency actions and remediation plan sections"""
        sections = ""
        if report.emergency_actions:
            sections += "## 🚨 Emergency Actions Required\n"
            sections += "\n".join(f"- {action}" for action in report.emergency_actions) + "\n\n"
        if report.remediation_plan:
            sections += "## 📋 Remediation Plan\n"
            sections += "\n".join(f"- {action}" for action in report.remediation_plan) + "\n\n"
        return sections

    def _build_violations_section(self, report: BoundaryReport) -> str:
        """Build top critical violations section"""
        if not report.violations:
            return ""
        critical_violations = [v for v in report.violations if v.severity == "critical"][:5]
        if not critical_violations:
            return ""
        section = "## 🔍 Top Critical Violations\n"
        for i, violation in enumerate(critical_violations, 1):
            section += f"{i}. **{violation.file_path}** - {violation.description}\n"
            if violation.auto_split_suggestion:
                section += f"   💡 *{violation.auto_split_suggestion}*\n"
        return section + "\n"

    def _build_tools_section(self, report: BoundaryReport) -> str:
        """Build available tools section"""
        return f"""## 🛠️ Available Tools
- `python scripts/boundary_enforcer.py --enforce` - Full boundary check
- `python scripts/auto_split_files.py --scan` - Automated file splitting
- `python scripts/auto_decompose_functions.py --scan` - Function decomposition
- `python scripts/emergency_boundary_actions.py --assess` - Emergency assessment

---
*Generated by Boundary Enforcement System v2.0 | Timestamp: {report.timestamp}*
"""

def create_pre_commit_config() -> str:
    """Create pre-commit configuration for boundary enforcement"""
    return """# Boundary Enforcement Pre-commit Configuration
repos:
  - repo: local
    hooks:
      - id: boundary-enforcer
        name: System Boundary Enforcer
        entry: python scripts/boundary_enforcer.py --enforce --fail-on-critical
        language: system
        files: '^(app|frontend|scripts)/'
        stages: [commit]
        
      - id: file-size-check
        name: File Size Boundary Check
        entry: python scripts/boundary_enforcer.py --check-file-boundaries
        language: system
        files: '\\.(py|ts|tsx)$'
        stages: [commit]
        
      - id: function-complexity-check
        name: Function Complexity Boundary Check
        entry: python scripts/boundary_enforcer.py --check-function-boundaries
        language: system
        files: '\\.py$'
        stages: [commit]
"""

def create_ci_workflow_config() -> str:
    """Create CI workflow for boundary enforcement"""
    return """name: Boundary Enforcement

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  boundary-enforcement:
    runs-on: warp-custom-default
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install radon
      
      - name: Run Boundary Enforcer
        run: |
          python scripts/boundary_enforcer.py --enforce --json-output boundary-report.json
      
      - name: Check Critical Violations
        run: |
          python scripts/boundary_enforcer.py --fail-on-emergency
      
      - name: Upload Boundary Report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: boundary-report
          path: boundary-report.json
      
      - name: Comment PR with Report
        if: github.event_name == 'pull_request'
        run: |
          python scripts/boundary_enforcer.py --pr-comment
"""

def setup_argument_parser():
    """Setup and configure argument parser"""
    import argparse
    parser = argparse.ArgumentParser(
        description='BOUNDARY ENFORCER - Stop unhealthy system growth',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples: python boundary_enforcer.py --enforce""")
    return configure_parser_arguments(parser)

def configure_parser_arguments(parser):
    """Configure all parser arguments"""
    parser.add_argument('--enforce', action='store_true', help='Run full boundary enforcement')
    parser.add_argument('--check-file-boundaries', action='store_true', help='Check only file size boundaries')
    parser.add_argument('--check-function-boundaries', action='store_true', help='Check only function size boundaries')
    parser.add_argument('--fail-on-critical', action='store_true', help='Exit with error code on critical violations')
    parser.add_argument('--fail-on-emergency', action='store_true', help='Exit with error code on emergency actions')
    add_remaining_arguments(parser)
    return parser

def add_remaining_arguments(parser):
    """Add remaining parser arguments"""
    parser.add_argument('--json-output', help='Save JSON report to file')
    parser.add_argument('--emergency-only', action='store_true', help='Show only emergency-level violations')
    parser.add_argument('--install-hooks', action='store_true', help='Install pre-commit hooks')
    parser.add_argument('--pr-comment', action='store_true', help='Generate PR comment with boundary status')

def handle_install_hooks():
    """Handle installation of pre-commit hooks and CI workflow"""
    pre_commit_config = Path('.pre-commit-config.yaml')
    pre_commit_config.write_text(create_pre_commit_config())
    workflow_config = Path('.github/workflows/boundary-enforcement.yml')
    workflow_config.parent.mkdir(exist_ok=True)
    workflow_config.write_text(create_ci_workflow_config())
    print("[OK] Boundary enforcement hooks and CI workflow installed")

def handle_pr_comment():
    """Handle PR comment generation"""
    enforcer = BoundaryEnforcer()
    comment = enforcer.generate_pr_comment()
    print(comment)

def run_specific_boundary_checks(args, enforcer):
    """Run specific boundary checks based on arguments"""
    if args.check_file_boundaries:
        enforcer._check_file_line_boundaries()
        return [v for v in enforcer.violations if v.violation_type == "file_line_boundary"]
    elif args.check_function_boundaries:
        enforcer._check_function_line_boundaries()
        return [v for v in enforcer.violations if v.violation_type == "function_line_boundary"]
    return None

def run_full_enforcement(args, enforcer):
    """Run full boundary enforcement with output handling"""
    result_status = enforcer.generate_enforcement_report()
    handle_json_output(args, enforcer)
    handle_emergency_failures(args, enforcer)
    handle_critical_failures(args, enforcer)

def handle_json_output(args, enforcer):
    """Handle JSON output if requested"""
    if args.json_output:
        report = enforcer.enforce_all_boundaries()
        with open(args.json_output, 'w') as f:
            json.dump(asdict(report), f, indent=2)
        print(f"\n[INFO] JSON report saved to: {args.json_output}")

def handle_emergency_failures(args, enforcer):
    """Handle emergency failure conditions"""
    if args.fail_on_emergency:
        report = enforcer.enforce_all_boundaries()
        if report.emergency_actions:
            print("\n[CRITICAL] EMERGENCY ACTIONS REQUIRED - Build failing")
            sys.exit(1)

def handle_critical_failures(args, enforcer):
    """Handle critical failure conditions"""
    if args.fail_on_critical:
        critical_violations = [v for v in enforcer.violations if v.severity == "critical"]
        if critical_violations:
            print(f"\n[FAIL] {len(critical_violations)} critical violations - Build failing")
            sys.exit(1)

def display_violation_results(violations, args):
    """Display results for specific boundary check violations"""
    if violations:
        print(f"\n[FAIL] Found {len(violations)} boundary violations")
        for v in violations[:10]:
            print(f"  - {v.description} in {v.file_path}")
        check_critical_exit(args)
    else:
        print("[PASS] No boundary violations found")

def check_critical_exit(args):
    """Exit if fail on critical is enabled"""
    if args.fail_on_critical:
        sys.exit(1)

def main():
    """Main CLI orchestrator for boundary enforcement"""
    parser = setup_argument_parser()
    args = parser.parse_args()
    if args.install_hooks: return handle_install_hooks()
    if args.pr_comment: return handle_pr_comment()
    enforcer = BoundaryEnforcer()
    violations = run_specific_boundary_checks(args, enforcer)
    if violations is not None: return display_violation_results(violations, args)
    run_full_enforcement(args, enforcer)

if __name__ == "__main__":
    main()