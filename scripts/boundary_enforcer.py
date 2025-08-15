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
        total_files = 0
        total_lines = 0
        module_count = 0
        
        patterns = [
            'app/**/*.py', 'frontend/**/*.tsx', 'frontend/**/*.ts', 
            'scripts/**/*.py', 'test_framework/**/*.py'
        ]
        
        for pattern in patterns:
            for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
                if self._should_skip_file(filepath):
                    continue
                    
                total_files += 1
                module_count += 1
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        total_lines += lines
                except Exception:
                    continue
        
        self.system_metrics = {
            "total_files": total_files,
            "total_lines": total_lines,
            "module_count": module_count,
            "avg_file_size": total_lines / total_files if total_files > 0 else 0,
            "growth_velocity": self._calculate_growth_velocity(),
            "complexity_debt": self._calculate_complexity_debt()
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
            for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
                if self._should_skip_file(filepath):
                    continue
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        
                    if lines > self.boundaries.max_file_lines:
                        rel_path = str(Path(filepath).relative_to(self.root_path))
                        split_suggestion = self._generate_file_split_suggestion(filepath, lines)
                        
                        self.violations.append(BoundaryViolation(
                            file_path=rel_path,
                            violation_type="file_line_boundary",
                            severity="critical",
                            boundary_name="FILE_SIZE_LIMIT",
                            actual_value=lines,
                            expected_value=self.boundaries.max_file_lines,
                            description=f"File exceeds {self.boundaries.max_file_lines} line HARD LIMIT",
                            fix_suggestion=f"MANDATORY: Split into {(lines // self.boundaries.max_file_lines) + 1} modules",
                            auto_split_suggestion=split_suggestion,
                            impact_score=min(10, lines // 100)
                        ))
                except Exception:
                    continue
    
    def _generate_file_split_suggestion(self, filepath: str, lines: int) -> str:
        """Generate intelligent file split suggestions"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            classes = []
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(f"class {node.name} (line {node.lineno})")
                elif isinstance(node, ast.FunctionDef):
                    functions.append(f"function {node.name} (line {node.lineno})")
            
            suggestions = []
            if classes:
                suggestions.append(f"Split by classes: {', '.join(classes[:3])}")
            if functions:
                suggestions.append(f"Split by functions: {', '.join(functions[:3])}")
                
            return " | ".join(suggestions) if suggestions else "Consider splitting by logical boundaries"
        except Exception:
            return "Unable to analyze - manual split required"
    
    def _check_function_line_boundaries(self) -> None:
        """Check function line boundaries with refactor suggestions"""
        patterns = ['app/**/*.py', 'scripts/**/*.py']
        
        for pattern in patterns:
            for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
                if self._should_skip_file(filepath):
                    continue
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())
                    
                    rel_path = str(Path(filepath).relative_to(self.root_path))
                    
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            lines = self._count_function_lines(node)
                            
                            if lines > self.boundaries.max_function_lines:
                                refactor_suggestion = self._generate_function_refactor_suggestion(node, lines)
                                
                                self.violations.append(BoundaryViolation(
                                    file_path=rel_path,
                                    violation_type="function_line_boundary",
                                    severity="critical",
                                    boundary_name="FUNCTION_SIZE_LIMIT",
                                    line_number=node.lineno,
                                    function_name=node.name,
                                    actual_value=lines,
                                    expected_value=self.boundaries.max_function_lines,
                                    description=f"Function exceeds {self.boundaries.max_function_lines} line HARD LIMIT",
                                    fix_suggestion=f"MANDATORY: Split into {(lines // self.boundaries.max_function_lines) + 1} functions",
                                    auto_split_suggestion=refactor_suggestion,
                                    impact_score=min(10, lines // 2)
                                ))
                except Exception:
                    continue
    
    def _generate_function_refactor_suggestion(self, node: ast.FunctionDef, lines: int) -> str:
        """Generate intelligent function refactoring suggestions"""
        suggestions = []
        
        # Analyze function structure
        if hasattr(node, 'body') and len(node.body) > 0:
            has_conditions = any(isinstance(n, (ast.If, ast.While, ast.For)) for n in ast.walk(node))
            has_try_except = any(isinstance(n, ast.Try) for n in ast.walk(node))
            
            if has_conditions:
                suggestions.append("Extract conditional logic into helper functions")
            if has_try_except:
                suggestions.append("Extract error handling into separate function")
            if lines > 15:
                suggestions.append("Break into validation + processing + result functions")
            else:
                suggestions.append("Split into 2-3 smaller focused functions")
        
        return " | ".join(suggestions) if suggestions else "Requires manual refactoring"
    
    def _check_module_count_boundary(self) -> None:
        """Check module count boundary"""
        if self.system_metrics["module_count"] > self.boundaries.max_module_count:
            self.violations.append(BoundaryViolation(
                file_path="SYSTEM_WIDE",
                violation_type="module_count_boundary",
                severity="critical",
                boundary_name="MODULE_COUNT_LIMIT",
                actual_value=self.system_metrics["module_count"],
                expected_value=self.boundaries.max_module_count,
                description=f"System exceeds {self.boundaries.max_module_count} module HARD LIMIT",
                fix_suggestion="EMERGENCY: Archive unused modules, consolidate similar modules",
                impact_score=10
            ))
    
    def _check_total_loc_boundary(self) -> None:
        """Check total lines of code boundary"""
        if self.system_metrics["total_lines"] > self.boundaries.max_total_loc:
            self.violations.append(BoundaryViolation(
                file_path="SYSTEM_WIDE",
                violation_type="total_loc_boundary",
                severity="critical",
                boundary_name="TOTAL_LOC_LIMIT",
                actual_value=self.system_metrics["total_lines"],
                expected_value=self.boundaries.max_total_loc,
                description=f"System exceeds {self.boundaries.max_total_loc} LOC HARD LIMIT",
                fix_suggestion="EMERGENCY: Remove deprecated code, refactor duplicates",
                impact_score=10
            ))
    
    def _check_complexity_boundaries(self) -> None:
        """Check complexity score boundaries"""
        avg_complexity = self.system_metrics.get("complexity_debt", 0)
        if avg_complexity > self.boundaries.max_complexity_score:
            self.violations.append(BoundaryViolation(
                file_path="SYSTEM_WIDE",
                violation_type="complexity_boundary",
                severity="high",
                boundary_name="COMPLEXITY_LIMIT",
                actual_value=int(avg_complexity * 100),
                expected_value=int(self.boundaries.max_complexity_score * 100),
                description=f"System complexity exceeds {self.boundaries.max_complexity_score} LIMIT",
                fix_suggestion="Refactor complex functions, simplify logic paths",
                impact_score=8
            ))
    
    def _check_duplicate_type_boundaries(self) -> None:
        """Check for duplicate types across system"""
        type_definitions = defaultdict(list)
        
        # Check Python files
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if self._should_skip_file(filepath):
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    rel_path = str(Path(filepath).relative_to(self.root_path))
                    for match in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
                        type_name = match.group(1)
                        type_definitions[type_name].append(rel_path)
            except Exception:
                continue
        
        # Check TypeScript files
        for pattern in ['frontend/**/*.ts', 'frontend/**/*.tsx']:
            for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
                if 'node_modules' in filepath:
                    continue
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        rel_path = str(Path(filepath).relative_to(self.root_path))
                        for match in re.finditer(r'(?:interface|type)\s+(\w+)', content):
                            type_name = match.group(1)
                            type_definitions[type_name].append(rel_path)
                except Exception:
                    continue
        
        # Create violations for duplicates
        duplicate_count = 0
        for type_name, files in type_definitions.items():
            if len(files) > 1:
                duplicate_count += 1
                self.violations.append(BoundaryViolation(
                    file_path=", ".join(files[:2]) + ("..." if len(files) > 2 else ""),
                    violation_type="duplicate_type_boundary",
                    severity="medium",
                    boundary_name="NO_DUPLICATE_TYPES",
                    actual_value=len(files),
                    expected_value=1,
                    description=f"Duplicate type '{type_name}' violates SINGLE SOURCE OF TRUTH",
                    fix_suggestion=f"Consolidate '{type_name}' into shared module",
                    impact_score=3
                ))
    
    def _check_test_stub_boundaries(self) -> None:
        """Check for test stubs in production code"""
        suspicious_patterns = [
            (r'# Mock implementation', 'Mock implementation comment'),
            (r'# Test stub', 'Test stub comment'),
            (r'# TODO.*implement', 'TODO implementation comment'),
            (r'return \[{"id": "1"', 'Hardcoded test data'),
            (r'raise NotImplementedError', 'Not implemented error'),
        ]
        
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if '__pycache__' in filepath or 'app/tests' in filepath or '/tests/' in filepath:
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    rel_path = str(Path(filepath).relative_to(self.root_path))
                    
                    for pattern, description in suspicious_patterns:
                        matches = list(re.finditer(pattern, content, re.IGNORECASE | re.DOTALL))
                        for match in matches:
                            line_number = content[:match.start()].count('\n') + 1
                            self.violations.append(BoundaryViolation(
                                file_path=rel_path,
                                violation_type="test_stub_boundary",
                                severity="critical",
                                boundary_name="NO_TEST_STUBS",
                                line_number=line_number,
                                description=f"Test stub in production: {description}",
                                fix_suggestion="Replace with production implementation",
                                impact_score=7
                            ))
                            break  # Only report first match per file
            except Exception:
                continue
    
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
        
        # Skip docstring if present
        start_idx = 0
        if (len(node.body) > 0 and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, (ast.Constant, ast.Str))):
            start_idx = 1
        
        if start_idx >= len(node.body):
            return 0
            
        # Count lines from first real statement to last
        first_line = node.body[start_idx].lineno
        last_line = node.body[-1].end_lineno if hasattr(node.body[-1], 'end_lineno') else node.body[-1].lineno
        return last_line - first_line + 1
    
    def _generate_boundary_report(self) -> BoundaryReport:
        """Generate comprehensive boundary enforcement report"""
        violations_by_boundary = defaultdict(int)
        emergency_actions = []
        remediation_plan = []
        
        for violation in self.violations:
            violations_by_boundary[violation.boundary_name] += 1
            
            if violation.severity == "critical" and violation.impact_score >= 8:
                emergency_actions.append(f"EMERGENCY: {violation.fix_suggestion}")
        
        # Calculate growth risk level
        total_violations = len(self.violations)
        risk_score = sum(v.impact_score for v in self.violations)
        
        if risk_score > 500 or total_violations > 1000:
            growth_risk_level = "CRITICAL - SYSTEM UNSTABLE"
            emergency_actions.append("IMMEDIATE: Stop all new feature development")
            emergency_actions.append("IMMEDIATE: Begin emergency refactoring sprint")
        elif risk_score > 200 or total_violations > 500:
            growth_risk_level = "HIGH - REQUIRES INTERVENTION"
            remediation_plan.append("Schedule architecture review within 1 week")
            remediation_plan.append("Implement daily boundary monitoring")
        elif risk_score > 50 or total_violations > 100:
            growth_risk_level = "MEDIUM - MONITOR CLOSELY"
            remediation_plan.append("Weekly boundary compliance checks")
        else:
            growth_risk_level = "LOW - MANAGEABLE"
        
        # Calculate compliance score
        total_possible_violations = 7  # Number of boundary types
        boundary_compliance_score = max(0, (total_possible_violations - len(violations_by_boundary)) / total_possible_violations * 100)
        
        if not emergency_actions:
            remediation_plan.extend([
                "Continue enforcing pre-commit hooks",
                "Maintain CI/CD boundary gates",
                "Regular automated compliance monitoring"
            ])
        
        return BoundaryReport(
            total_violations=total_violations,
            boundary_compliance_score=boundary_compliance_score,
            growth_risk_level=growth_risk_level,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            violations_by_boundary=dict(violations_by_boundary),
            violations=self.violations,
            system_metrics=self.system_metrics,
            remediation_plan=remediation_plan,
            emergency_actions=emergency_actions
        )
    
    def generate_enforcement_report(self) -> str:
        """Generate human-readable enforcement report"""
        report = self.enforce_all_boundaries()
        
        print("\n" + "=" * 80)
        print("BOUNDARY ENFORCEMENT REPORT")
        print("=" * 80)
        print(f"Timestamp: {report.timestamp}")
        print(f"Growth Risk Level: {report.growth_risk_level}")
        print(f"Boundary Compliance: {report.boundary_compliance_score:.1f}%")
        print(f"Total Violations: {report.total_violations}")
        
        print(f"\n[SYSTEM METRICS]:")
        print(f"  Total Files: {report.system_metrics['total_files']}")
        print(f"  Total Lines: {report.system_metrics['total_lines']:,}")
        print(f"  Module Count: {report.system_metrics['module_count']}")
        print(f"  Avg File Size: {report.system_metrics['avg_file_size']:.1f} lines")
        print(f"  Growth Velocity: {report.system_metrics['growth_velocity']:.2f}")
        print(f"  Complexity Debt: {report.system_metrics['complexity_debt']:.2f}")
        
        print(f"\n[BOUNDARY VIOLATIONS]:")
        for boundary, count in report.violations_by_boundary.items():
            print(f"  {boundary}: {count} violations")
        
        if report.emergency_actions:
            print(f"\n[EMERGENCY ACTIONS REQUIRED]:")
            for action in report.emergency_actions:
                print(f"  - {action}")
        
        if report.remediation_plan:
            print(f"\n[REMEDIATION PLAN]:")
            for action in report.remediation_plan:
                print(f"  - {action}")
        
        print(f"\n[TOP CRITICAL VIOLATIONS]:")
        critical_violations = [v for v in report.violations if v.severity == "critical"]
        for i, violation in enumerate(sorted(critical_violations, key=lambda x: x.impact_score, reverse=True)[:10], 1):
            print(f"  {i}. {violation.description}")
            print(f"     File: {violation.file_path}")
            if violation.auto_split_suggestion:
                print(f"     Auto-fix: {violation.auto_split_suggestion}")
        
        return "FAIL" if report.emergency_actions else "MONITOR" if report.total_violations > 0 else "PASS"

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
    runs-on: ubuntu-latest
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

def main():
    """Main CLI for boundary enforcement"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='BOUNDARY ENFORCER - Stop unhealthy system growth',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python boundary_enforcer.py --enforce
  python boundary_enforcer.py --check-file-boundaries --fail-on-critical
  python boundary_enforcer.py --json-output report.json --emergency-only
  python boundary_enforcer.py --install-hooks
        """)
    
    parser.add_argument('--enforce', action='store_true',
                       help='Run full boundary enforcement')
    parser.add_argument('--check-file-boundaries', action='store_true',
                       help='Check only file size boundaries')
    parser.add_argument('--check-function-boundaries', action='store_true',
                       help='Check only function size boundaries')
    parser.add_argument('--fail-on-critical', action='store_true',
                       help='Exit with error code on critical violations')
    parser.add_argument('--fail-on-emergency', action='store_true',
                       help='Exit with error code on emergency actions')
    parser.add_argument('--json-output', help='Save JSON report to file')
    parser.add_argument('--emergency-only', action='store_true',
                       help='Show only emergency-level violations')
    parser.add_argument('--install-hooks', action='store_true',
                       help='Install pre-commit hooks')
    parser.add_argument('--pr-comment', action='store_true',
                       help='Generate PR comment with boundary status')
    
    args = parser.parse_args()
    
    if args.install_hooks:
        pre_commit_config = Path('.pre-commit-config.yaml')
        pre_commit_config.write_text(create_pre_commit_config())
        
        workflow_config = Path('.github/workflows/boundary-enforcement.yml')
        workflow_config.parent.mkdir(exist_ok=True)
        workflow_config.write_text(create_ci_workflow_config())
        
        print("[OK] Boundary enforcement hooks and CI workflow installed")
        return
    
    enforcer = BoundaryEnforcer()
    
    if args.check_file_boundaries:
        enforcer._check_file_line_boundaries()
        violations = [v for v in enforcer.violations if v.violation_type == "file_line_boundary"]
    elif args.check_function_boundaries:
        enforcer._check_function_line_boundaries()
        violations = [v for v in enforcer.violations if v.violation_type == "function_line_boundary"]
    else:
        result_status = enforcer.generate_enforcement_report()
        
        if args.json_output:
            report = enforcer.enforce_all_boundaries()
            with open(args.json_output, 'w') as f:
                json.dump(asdict(report), f, indent=2)
            print(f"\n[INFO] JSON report saved to: {args.json_output}")
        
        if args.fail_on_emergency:
            report = enforcer.enforce_all_boundaries()
            if report.emergency_actions:
                print("\n[CRITICAL] EMERGENCY ACTIONS REQUIRED - Build failing")
                sys.exit(1)
        
        if args.fail_on_critical:
            critical_violations = [v for v in enforcer.violations if v.severity == "critical"]
            if critical_violations:
                print(f"\n[FAIL] {len(critical_violations)} critical violations - Build failing")
                sys.exit(1)
        
        return
    
    # Handle specific boundary checks
    if violations:
        print(f"\n[FAIL] Found {len(violations)} boundary violations")
        for v in violations[:10]:
            print(f"  - {v.description} in {v.file_path}")
        
        if args.fail_on_critical:
            sys.exit(1)
    else:
        print("[PASS] No boundary violations found")

if __name__ == "__main__":
    main()