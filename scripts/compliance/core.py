#!/usr/bin/env python3
"""
Core data structures and types for architecture compliance checking.
Enforces CLAUDE.md architectural rules with modular design.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Union
from pathlib import Path


@dataclass
class Violation:
    """Structured violation data"""
    file_path: str
    violation_type: str
    severity: str
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    actual_value: Optional[int] = None
    expected_value: Optional[int] = None
    description: str = ""
    fix_suggestion: str = ""


@dataclass
class ComplianceResults:
    """Complete compliance results"""
    total_violations: int
    compliance_score: float
    timestamp: str
    violations_by_type: Dict[str, int]
    violations: List[Violation]
    summary: Dict[str, Union[int, str, float]]


class ComplianceConfig:
    """Configuration for compliance checking"""
    
    def __init__(self, root_path: str = ".", max_file_lines: int = 300, 
                 max_function_lines: int = 8):
        self.root_path = Path(root_path)
        self.max_file_lines = max_file_lines
        self.max_function_lines = max_function_lines
    
    def get_patterns(self) -> List[str]:
        """Get file patterns to check"""
        return ['app/**/*.py', 'frontend/**/*.tsx', 'frontend/**/*.ts', 'scripts/**/*.py']
    
    def get_python_patterns(self) -> List[str]:
        """Get Python file patterns"""
        return ['app/**/*.py', 'scripts/**/*.py']
    
    def get_typescript_patterns(self) -> List[str]:
        """Get TypeScript file patterns"""
        return ['frontend/**/*.ts', 'frontend/**/*.tsx']
    
    def should_skip_file(self, filepath: str) -> bool:
        """Check if file should be skipped"""
        skip_patterns = self._get_skip_patterns()
        return any(pattern in filepath for pattern in skip_patterns)
    
    def _get_skip_patterns(self) -> List[str]:
        """Get patterns for files to skip"""
        return [
            '__pycache__', 'node_modules', '.git', 'migrations', 'test_reports',
            'docs', '.pytest_cache', 'venv', '.venv', 'env', '.env', 'virtualenv',
            'site-packages', 'dist-packages', 'vendor', 'third_party', 'third-party',
            'external', 'lib', 'libs', 'bower_components', 'jspm_packages', 'build',
            'dist', '.eggs', '*.egg-info', '.idea', '.vscode', '.vs', 'htmlcov',
            '.coverage', '.tox', '.nox', 'pip-wheel-metadata', 'package-lock.json',
            'yarn.lock', 'static/admin', 'static/rest_framework', 'wwwroot/lib',
            '.terraform', 'terraform/.terraform'
        ]


class ViolationBuilder:
    """Builder for creating violation objects"""
    
    @staticmethod
    def file_size_violation(rel_path: str, lines: int, max_lines: int) -> Violation:
        """Build file size violation"""
        return Violation(
            file_path=rel_path, violation_type="file_size", severity="high",
            actual_value=lines, expected_value=max_lines,
            description=f"File exceeds {max_lines} line limit",
            fix_suggestion=f"Split into {(lines // max_lines) + 1} modules"
        )
    
    @staticmethod
    def function_violation(node, rel_path: str, lines: int, max_lines: int,
                          severity: str, prefix: str) -> Violation:
        """Build function complexity violation"""
        fix_action = "Consider splitting" if severity == "low" else "Split"
        return Violation(
            file_path=rel_path, violation_type="function_complexity", severity=severity,
            line_number=node.lineno, function_name=node.name, actual_value=lines,
            expected_value=max_lines,
            description=f"{prefix} Function '{node.name}' has {lines} lines (max: {max_lines})",
            fix_suggestion=f"{fix_action} into {(lines // max_lines) + 1} smaller functions"
        )
    
    @staticmethod
    def duplicate_violation(type_name: str, files: List[str]) -> Violation:
        """Build duplicate type violation"""
        file_list = ", ".join(files[:3]) + ("..." if len(files) > 3 else "")
        return Violation(
            file_path=file_list, violation_type="duplicate_types", severity="medium",
            actual_value=len(files), expected_value=1,
            description=f"Type '{type_name}' defined in {len(files)} files",
            fix_suggestion=f"Consolidate '{type_name}' into single source of truth"
        )
    
    @staticmethod
    def test_stub_violation(rel_path: str, line_number: int, description: str) -> Violation:
        """Build test stub violation"""
        return Violation(
            file_path=rel_path, violation_type="test_stub", severity="high",
            line_number=line_number, description=f"Test stub detected: {description}",
            fix_suggestion="Replace with production implementation"
        )


def create_compliance_results(violations: List[Violation], total_files: int,
                            compliance_score: float, violations_by_type: Dict[str, int],
                            max_file_lines: int, max_function_lines: int) -> ComplianceResults:
    """Create compliance results object"""
    import time
    summary = _build_summary(violations, total_files, compliance_score, 
                            max_file_lines, max_function_lines)
    return ComplianceResults(
        total_violations=len(violations), compliance_score=compliance_score,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"), violations_by_type=violations_by_type,
        violations=violations, summary=summary
    )


def _build_summary(violations: List[Violation], total_files: int, compliance_score: float,
                  max_file_lines: int, max_function_lines: int) -> Dict:
    """Build summary dictionary"""
    return {
        "total_files_checked": total_files,
        "files_with_violations": len(set(v.file_path for v in violations)),
        "max_file_lines": max_file_lines,
        "max_function_lines": max_function_lines,
        "compliance_score": compliance_score
    }