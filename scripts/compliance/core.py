#!/usr/bin/env python3
"""
Core data structures and types for architecture compliance checking.
Enforces CLAUDE.md architectural rules with modular design.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union


@dataclass
class Violation:
    """Structured violation data with enhanced severity tracking"""
    file_path: str
    violation_type: str
    severity: str  # Now uses 4-tier: critical, high, medium, low
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    actual_value: Optional[int] = None
    expected_value: Optional[int] = None
    description: str = ""
    fix_suggestion: str = ""
    business_impact: Optional[str] = None  # Business impact description
    remediation_timeline: Optional[str] = None  # Expected fix timeline
    category: Optional[str] = None  # Violation category for grouping


@dataclass
class ComplianceResults:
    """Complete compliance results"""
    total_violations: int
    compliance_score: float
    timestamp: str
    violations_by_type: Dict[str, int]
    violations: List[Violation]
    summary: Dict[str, Union[int, str, float]]
    category_scores: Dict[str, Dict[str, Union[int, float]]] = None


class ComplianceConfig:
    """Configuration for compliance checking"""
    
    def __init__(self, root_path: str = ".", max_file_lines: int = 500, 
                 max_function_lines: int = 25, target_folders: List[str] = None,
                 ignore_folders: List[str] = None):
        self.root_path = Path(root_path)
        # CLAUDE.md 2.2: Modules should aim for <500 lines (approx)
        self.max_file_lines = max_file_lines
        # CLAUDE.md 2.2: Functions should strive for <25 lines (approx)
        self.max_function_lines = max_function_lines
        self.target_folders = target_folders or ['app', 'frontend', 'auth_service']
        self.ignore_folders = ignore_folders or ['scripts', 'test_framework']
    
    def get_patterns(self) -> List[str]:
        """Get file patterns to check"""
        patterns = []
        for folder in self.target_folders:
            patterns.extend([f'{folder}/**/*.py', f'{folder}/**/*.ts', f'{folder}/**/*.tsx'])
        return patterns
    
    def get_python_patterns(self) -> List[str]:
        """Get Python file patterns"""
        return [f'{folder}/**/*.py' for folder in self.target_folders]
    
    def get_typescript_patterns(self) -> List[str]:
        """Get TypeScript file patterns"""
        patterns = []
        for folder in self.target_folders:
            if folder == 'frontend':
                patterns.extend([f'{folder}/**/*.ts', f'{folder}/**/*.tsx'])
        return patterns
    
    def should_skip_file(self, filepath: str) -> bool:
        """Check if file should be skipped"""
        skip_patterns = self._get_skip_patterns()
        path_str = str(filepath)
        # Skip ignored folders
        for folder in self.ignore_folders:
            if path_str.startswith(folder + '/') or f'/{folder}/' in path_str:
                return True
        return any(pattern in path_str for pattern in skip_patterns)
    
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
    
    def is_test_file(self, filepath: str) -> bool:
        """Check if file is a test file"""
        test_indicators = ['test_', '_test.', '/tests/', '/test/', 'spec.', '.spec.', '.test.']
        path_str = str(filepath).lower()
        return any(indicator in path_str for indicator in test_indicators)


class ViolationBuilder:
    """Builder for creating violation objects with enhanced severity"""
    
    @staticmethod
    def file_size_violation(rel_path: str, lines: int, max_lines: int) -> Violation:
        """Build file size violation with tiered severity"""
        # Determine severity based on how much the limit is exceeded
        if lines > max_lines * 2:  # More than double the limit
            severity = "high"
            violation_type = "file_size_extreme"
            business_impact = "Severe maintainability issues, high cognitive load"
            timeline = "Within 24 hours"
        elif lines > max_lines:
            severity = "medium"
            violation_type = "file_size_high"
            business_impact = "Reduced maintainability, testing complexity"
            timeline = "Current sprint"
        else:
            severity = "low"
            violation_type = "file_size_warning"
            business_impact = "Code quality concern"
            timeline = "Next refactor cycle"
        
        return Violation(
            file_path=rel_path, violation_type=violation_type, severity=severity,
            actual_value=lines, expected_value=max_lines,
            description=f"File exceeds {max_lines} line limit",
            fix_suggestion=f"Split into {(lines // max_lines) + 1} modules",
            business_impact=business_impact,
            remediation_timeline=timeline,
            category="complexity"
        )
    
    @staticmethod
    def function_violation(node, rel_path: str, lines: int, max_lines: int,
                          severity: str, prefix: str) -> Violation:
        """Build function complexity violation with enhanced severity"""
        # Override severity based on complexity level
        if lines > max_lines * 2:  # More than double the limit
            severity = "high"
            violation_type = "function_complexity_extreme"
            business_impact = "Severe testing difficulty, high bug risk"
            timeline = "Within 24 hours"
            fix_action = "Urgently split"
        elif lines > max_lines:
            severity = "medium"
            violation_type = "function_complexity_high"
            business_impact = "Testing complexity, maintenance burden"
            timeline = "Current sprint"
            fix_action = "Split"
        else:
            severity = "low"
            violation_type = "function_complexity_warning"
            business_impact = "Code quality concern"
            timeline = "Next refactor cycle"
            fix_action = "Consider splitting"
        
        return Violation(
            file_path=rel_path, violation_type=violation_type, severity=severity,
            line_number=node.lineno, function_name=node.name, actual_value=lines,
            expected_value=max_lines,
            description=f"{prefix} Function '{node.name}' has {lines} lines (max: {max_lines})",
            fix_suggestion=f"{fix_action} into {(lines // max_lines) + 1} smaller functions",
            business_impact=business_impact,
            remediation_timeline=timeline,
            category="complexity"
        )
    
    @staticmethod
    def duplicate_violation(type_name: str, files: List[str]) -> Violation:
        """Build duplicate type violation with context-aware severity"""
        file_list = ", ".join(files[:3]) + ("..." if len(files) > 3 else "")

        # Check if it's a critical type based on naming
        critical_patterns = ['Agent', 'Service', 'Config', 'Auth', 'Security']
        is_critical = any(pattern in type_name for pattern in critical_patterns)

        # Common UI types that are often legitimately duplicated
        common_ui_types = ['Props', 'State', 'FormData', 'ButtonProps', 'ModalProps']
        is_common_ui = any(ui_type in type_name for ui_type in common_ui_types)

        # Different components can have their own Props/State - reduce severity
        if is_common_ui and len(files) <= 5:
            severity = "low"
            violation_type = "duplicate_ui_types"
            business_impact = "Common UI type duplication - may be acceptable"
            timeline = "Low priority - review during refactor"
        elif is_critical and len(files) > 2:
            severity = "high"
            violation_type = "duplicate_critical_logic"
            business_impact = "Critical logic fragmentation, high bug risk"
            timeline = "Within 24 hours"
        else:
            severity = "medium"
            violation_type = "duplicate_types"
            business_impact = "Type system inconsistency, maintenance burden"
            timeline = "Current sprint"

        return Violation(
            file_path=file_list, violation_type=violation_type, severity=severity,
            actual_value=len(files), expected_value=1,
            description=f"Type '{type_name}' defined in {len(files)} files",
            fix_suggestion=f"Consolidate '{type_name}' into single source of truth",
            business_impact=business_impact,
            remediation_timeline=timeline,
            category="duplication"
        )
    
    @staticmethod
    def test_stub_violation(rel_path: str, line_number: int, description: str) -> Violation:
        """Build test stub violation - always critical in production"""
        # Test stubs in production are always critical
        is_production = not any(indicator in rel_path.lower() 
                               for indicator in ['/test', '/tests', '_test.', 'test_'])
        
        if is_production:
            severity = "critical"
            violation_type = "production_test_stub"
            business_impact = "Production code contains test logic - system failure risk"
            timeline = "Immediate - Stop all work and fix"
        else:
            severity = "medium"
            violation_type = "test_stub"
            business_impact = "Test quality issue"
            timeline = "Current sprint"
        
        return Violation(
            file_path=rel_path, violation_type=violation_type, severity=severity,
            line_number=line_number, description=f"Test stub detected: {description}",
            fix_suggestion="Replace with production implementation",
            business_impact=business_impact,
            remediation_timeline=timeline,
            category="quality"
        )


def create_compliance_results(violations: List[Violation], total_files: int,
                            compliance_score: float, violations_by_type: Dict[str, int],
                            max_file_lines: int, max_function_lines: int,
                            category_scores: Dict[str, Dict] = None) -> ComplianceResults:
    """Create compliance results object"""
    import time
    summary = _build_summary(violations, total_files, compliance_score, 
                            max_file_lines, max_function_lines)
    return ComplianceResults(
        total_violations=len(violations), compliance_score=compliance_score,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"), violations_by_type=violations_by_type,
        violations=violations, summary=summary, category_scores=category_scores
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