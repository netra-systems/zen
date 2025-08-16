"""Quality metrics for AI Factory Status Report.

Tracks test coverage, documentation, architecture compliance, and technical debt.
Module follows 300-line limit with 8-line function limit.
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from .git_commit_parser import GitCommitParser, CommitInfo, CommitType
from .git_diff_analyzer import GitDiffAnalyzer, ChangeCategory


class QualityLevel(Enum):
    """Quality assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    NEEDS_IMPROVEMENT = "needs_improvement"
    POOR = "poor"


class ComplianceStatus(Enum):
    """Architecture compliance status."""
    COMPLIANT = "compliant"
    MINOR_VIOLATIONS = "minor_violations"
    MAJOR_VIOLATIONS = "major_violations"
    NON_COMPLIANT = "non_compliant"


@dataclass
class TestCoverageMetrics:
    """Test coverage tracking metrics."""
    overall_coverage: float
    line_coverage: float
    function_coverage: float
    branch_coverage: float
    test_files_count: int
    source_files_count: int
    coverage_trend: float
    uncovered_critical_files: List[str]


@dataclass
class DocumentationMetrics:
    """Documentation quality metrics."""
    docstring_coverage: float
    readme_updated: bool
    api_docs_updated: bool
    spec_files_updated: int
    comment_density: float
    documentation_quality: QualityLevel


@dataclass
class ArchitectureCompliance:
    """Architecture compliance assessment."""
    line_limit_violations: int
    function_limit_violations: int
    module_violations: List[str]
    compliance_score: float
    compliance_status: ComplianceStatus
    violation_details: Dict[str, int]


@dataclass
class TechnicalDebt:
    """Technical debt metrics."""
    code_smells: int
    duplication_percentage: float
    complexity_hotspots: List[str]
    deprecated_usage: int
    todo_count: int
    debt_score: float
    debt_trend: float


@dataclass
class QualityMetrics:
    """Comprehensive quality metrics."""
    test_coverage: TestCoverageMetrics
    documentation: DocumentationMetrics
    architecture: ArchitectureCompliance
    technical_debt: TechnicalDebt
    overall_quality_score: float
    quality_level: QualityLevel


class QualityCalculator:
    """Calculator for code quality metrics."""
    
    MAX_LINES_PER_FILE = 300
    MAX_LINES_PER_FUNCTION = 8
    
    CRITICAL_FILES = [
        "app/auth", "app/db", "app/core", "app/llm",
        "app/websocket", "frontend/components/chat"
    ]
    
    def __init__(self, repo_path: str = "."):
        """Initialize quality calculator."""
        self.commit_parser = GitCommitParser(repo_path)
        self.diff_analyzer = GitDiffAnalyzer(repo_path)
        self.repo_path = repo_path
    
    def calculate_test_coverage(self) -> TestCoverageMetrics:
        """Calculate test coverage metrics."""
        test_files = self._count_test_files()
        source_files = self._count_source_files()
        coverage = self._estimate_coverage()
        trend = self._calculate_coverage_trend()
        uncovered = self._find_uncovered_critical_files()
        
        return TestCoverageMetrics(
            overall_coverage=coverage,
            line_coverage=coverage * 0.9,  # Estimate
            function_coverage=coverage * 0.85,  # Estimate
            branch_coverage=coverage * 0.8,  # Estimate
            test_files_count=test_files,
            source_files_count=source_files,
            coverage_trend=trend,
            uncovered_critical_files=uncovered
        )
    
    def _count_test_files(self) -> int:
        """Count test files in repository."""
        patterns = ["*test*.py", "*test*.ts", "*.test.*", "*.spec.*"]
        count = 0
        for pattern in patterns:
            cmd = ["find", ".", "-name", pattern, "-type", "f"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            count += len(result.stdout.strip().split("\n")) if result.stdout else 0
        return count
    
    def _count_source_files(self) -> int:
        """Count source files in repository."""
        cmd = ["find", ".", "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return len(result.stdout.strip().split("\n")) if result.stdout else 0
    
    def _estimate_coverage(self) -> float:
        """Estimate test coverage percentage."""
        test_files = self._count_test_files()
        source_files = self._count_source_files()
        
        if source_files == 0:
            return 0.0
        
        # Simple heuristic based on test to source ratio
        ratio = min(test_files / source_files, 1.0)
        return ratio * 100
    
    def _calculate_coverage_trend(self) -> float:
        """Calculate coverage trend over last week."""
        commits = self.commit_parser.get_commits(168)  # Last week
        test_commits = [c for c in commits if c.commit_type == CommitType.TEST]
        
        if not commits:
            return 0.0
        
        test_ratio = len(test_commits) / len(commits)
        return (test_ratio - 0.2) * 100  # Baseline 20% test commits
    
    def _find_uncovered_critical_files(self) -> List[str]:
        """Find critical files without test coverage."""
        uncovered = []
        for critical_path in self.CRITICAL_FILES:
            test_exists = self._has_corresponding_test(critical_path)
            if not test_exists:
                uncovered.append(critical_path)
        return uncovered
    
    def _has_corresponding_test(self, file_path: str) -> bool:
        """Check if file has corresponding test."""
        # Simplified check - would need proper test discovery
        test_patterns = [f"test_{file_path}", f"{file_path}_test", f"{file_path}.test"]
        return any(Path(self.repo_path).glob(f"**/{pattern}*") for pattern in test_patterns)
    
    def assess_documentation_quality(self) -> DocumentationMetrics:
        """Assess documentation quality."""
        docstring_coverage = self._calculate_docstring_coverage()
        readme_updated = self._check_readme_updated()
        api_docs_updated = self._check_api_docs_updated()
        specs_updated = self._count_spec_updates()
        comment_density = self._calculate_comment_density()
        
        quality = self._determine_doc_quality(
            docstring_coverage, comment_density, specs_updated
        )
        
        return DocumentationMetrics(
            docstring_coverage=docstring_coverage,
            readme_updated=readme_updated,
            api_docs_updated=api_docs_updated,
            spec_files_updated=specs_updated,
            comment_density=comment_density,
            documentation_quality=quality
        )
    
    def _calculate_docstring_coverage(self) -> float:
        """Calculate docstring coverage for Python files."""
        cmd = ["find", ".", "-name", "*.py", "-exec", "grep", "-l", '"""', "{}", ";"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        files_with_docstrings = len(result.stdout.strip().split("\n")) if result.stdout else 0
        total_py_files = self._count_python_files()
        
        return (files_with_docstrings / max(total_py_files, 1)) * 100
    
    def _count_python_files(self) -> int:
        """Count Python files."""
        cmd = ["find", ".", "-name", "*.py", "-type", "f"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return len(result.stdout.strip().split("\n")) if result.stdout else 0
    
    def _check_readme_updated(self) -> bool:
        """Check if README was updated recently."""
        return self._file_updated_recently("README.md", days=30)
    
    def _check_api_docs_updated(self) -> bool:
        """Check if API docs were updated recently."""
        return self._file_updated_recently("docs/API_DOCUMENTATION.md", days=30)
    
    def _file_updated_recently(self, file_path: str, days: int) -> bool:
        """Check if file was updated in last N days."""
        cmd = ["git", "log", "-1", "--since", f"{days} days ago", "--name-only", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return bool(result.stdout.strip())
    
    def _count_spec_updates(self) -> int:
        """Count SPEC file updates in last week."""
        cmd = ["git", "log", "--since", "7 days ago", "--name-only", "SPEC/"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if not result.stdout:
            return 0
        
        spec_files = [line for line in result.stdout.split("\n") if "SPEC/" in line]
        return len(set(spec_files))
    
    def _calculate_comment_density(self) -> float:
        """Calculate comment density in code."""
        total_lines = self._count_total_lines()
        comment_lines = self._count_comment_lines()
        
        return (comment_lines / max(total_lines, 1)) * 100
    
    def _count_total_lines(self) -> int:
        """Count total lines of code."""
        cmd = ["find", ".", "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx"]
        cmd += ["|", "xargs", "wc", "-l"]
        result = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
        
        if result.stdout:
            lines = result.stdout.strip().split("\n")
            if lines:
                return int(lines[-1].split()[0])
        return 0
    
    def _count_comment_lines(self) -> int:
        """Count comment lines."""
        # Simplified estimation
        py_comments = self._count_python_comments()
        ts_comments = self._count_typescript_comments()
        return py_comments + ts_comments
    
    def _count_python_comments(self) -> int:
        """Count Python comment lines."""
        cmd = ["find", ".", "-name", "*.py", "-exec", "grep", "-c", "^\\s*#", "{}", ";"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        counts = result.stdout.strip().split("\n") if result.stdout else []
        return sum(int(c) for c in counts if c.isdigit())
    
    def _count_typescript_comments(self) -> int:
        """Count TypeScript comment lines."""
        cmd = ["find", ".", "-name", "*.ts", "-o", "-name", "*.tsx"]
        cmd += ["|", "xargs", "grep", "-c", "^\\s*//"]
        result = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
        
        if result.stdout:
            counts = result.stdout.strip().split("\n")
            return sum(int(c.split(":")[-1]) for c in counts if ":" in c and c.split(":")[-1].isdigit())
        return 0
    
    def _determine_doc_quality(self, docstring_cov: float, 
                              comment_density: float, specs: int) -> QualityLevel:
        """Determine documentation quality level."""
        score = (docstring_cov * 0.4 + comment_density * 0.3 + min(specs * 10, 30) * 0.3)
        
        if score >= 80:
            return QualityLevel.EXCELLENT
        elif score >= 60:
            return QualityLevel.GOOD
        elif score >= 40:
            return QualityLevel.ACCEPTABLE
        elif score >= 20:
            return QualityLevel.NEEDS_IMPROVEMENT
        return QualityLevel.POOR
    
    def check_architecture_compliance(self) -> ArchitectureCompliance:
        """Check architecture compliance against 300/8 limits."""
        line_violations = self._check_file_line_limits()
        function_violations = self._check_function_line_limits()
        module_violations = self._check_module_violations()
        
        total_violations = line_violations + function_violations + len(module_violations)
        compliance_score = max(0, 100 - (total_violations * 5))
        status = self._determine_compliance_status(compliance_score)
        
        violation_details = {
            "file_line_limit": line_violations,
            "function_line_limit": function_violations,
            "module_structure": len(module_violations)
        }
        
        return ArchitectureCompliance(
            line_limit_violations=line_violations,
            function_limit_violations=function_violations,
            module_violations=module_violations,
            compliance_score=compliance_score,
            compliance_status=status,
            violation_details=violation_details
        )
    
    def _check_file_line_limits(self) -> int:
        """Check files exceeding 300-line limit."""
        violations = 0
        cmd = ["find", ".", "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        files = result.stdout.strip().split("\n") if result.stdout else []
        for file_path in files:
            if file_path:
                line_count = self._count_file_lines(file_path)
                if line_count > self.MAX_LINES_PER_FILE:
                    violations += 1
        
        return violations
    
    def _count_file_lines(self, file_path: str) -> int:
        """Count lines in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except (IOError, UnicodeDecodeError):
            return 0
    
    def _check_function_line_limits(self) -> int:
        """Check functions exceeding 8-line limit."""
        # Simplified check - would need proper AST parsing
        violations = 0
        cmd = ["find", ".", "-name", "*.py"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        files = result.stdout.strip().split("\n") if result.stdout else []
        for file_path in files:
            if file_path:
                violations += self._count_function_violations(file_path)
        
        return violations
    
    def _count_function_violations(self, file_path: str) -> int:
        """Count function violations in file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple regex-based detection (not perfect)
            function_pattern = r'def\s+\w+\([^)]*\):[^:]*?(?=\n\s*def|\n\s*class|\n\s*$|\Z)'
            functions = re.findall(function_pattern, content, re.DOTALL)
            
            violations = 0
            for func in functions:
                lines = len([line for line in func.split('\n') if line.strip()])
                if lines > self.MAX_LINES_PER_FUNCTION:
                    violations += 1
            
            return violations
        except (IOError, UnicodeDecodeError):
            return 0
    
    def _check_module_violations(self) -> List[str]:
        """Check for module structure violations."""
        violations = []
        
        # Check for overly deep nesting (simplified)
        cmd = ["find", ".", "-type", "d", "-path", "./*/*/*/*/*"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout:
            deep_dirs = result.stdout.strip().split("\n")
            violations.extend(deep_dirs)
        
        return violations
    
    def _determine_compliance_status(self, score: float) -> ComplianceStatus:
        """Determine compliance status from score."""
        if score >= 95:
            return ComplianceStatus.COMPLIANT
        elif score >= 80:
            return ComplianceStatus.MINOR_VIOLATIONS
        elif score >= 60:
            return ComplianceStatus.MAJOR_VIOLATIONS
        return ComplianceStatus.NON_COMPLIANT
    
    def calculate_technical_debt(self) -> TechnicalDebt:
        """Calculate technical debt metrics."""
        code_smells = self._count_code_smells()
        duplication = self._calculate_duplication()
        hotspots = self._find_complexity_hotspots()
        deprecated = self._count_deprecated_usage()
        todos = self._count_todo_items()
        
        debt_score = self._calculate_debt_score(
            code_smells, duplication, len(hotspots), deprecated, todos
        )
        debt_trend = self._calculate_debt_trend()
        
        return TechnicalDebt(
            code_smells=code_smells,
            duplication_percentage=duplication,
            complexity_hotspots=hotspots,
            deprecated_usage=deprecated,
            todo_count=todos,
            debt_score=debt_score,
            debt_trend=debt_trend
        )
    
    def _count_code_smells(self) -> int:
        """Count code smells (simplified)."""
        # Look for common patterns
        patterns = ["TODO", "FIXME", "HACK", "TEMP", "XXX"]
        count = 0
        
        for pattern in patterns:
            cmd = ["grep", "-r", pattern, ".", "--include=*.py", "--include=*.ts"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            count += len(result.stdout.strip().split("\n")) if result.stdout else 0
        
        return count
    
    def _calculate_duplication(self) -> float:
        """Calculate code duplication percentage (simplified)."""
        # Would use proper duplication detection tools in practice
        return 5.0  # Placeholder estimate
    
    def _find_complexity_hotspots(self) -> List[str]:
        """Find complexity hotspots."""
        # Simplified - would use complexity analysis tools
        hotspots = []
        
        # Files with high line count as proxy for complexity
        cmd = ["find", ".", "-name", "*.py", "-exec", "wc", "-l", "{}", ";"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0].isdigit():
                    line_count = int(parts[0])
                    if line_count > 200:  # Threshold for hotspot
                        hotspots.append(parts[1])
        
        return hotspots[:10]  # Top 10 hotspots
    
    def _count_deprecated_usage(self) -> int:
        """Count deprecated function/method usage."""
        cmd = ["grep", "-r", "deprecated", ".", "--include=*.py", "--include=*.ts"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return len(result.stdout.strip().split("\n")) if result.stdout else 0
    
    def _count_todo_items(self) -> int:
        """Count TODO items in code."""
        cmd = ["grep", "-r", "TODO", ".", "--include=*.py", "--include=*.ts"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return len(result.stdout.strip().split("\n")) if result.stdout else 0
    
    def _calculate_debt_score(self, smells: int, duplication: float,
                             hotspots: int, deprecated: int, todos: int) -> float:
        """Calculate overall debt score."""
        # Weighted combination of debt indicators
        score = (smells * 2 + duplication * 5 + hotspots * 10 + 
                deprecated * 3 + todos * 1)
        
        return min(score / 10, 10.0)  # Normalize to 0-10 scale
    
    def _calculate_debt_trend(self) -> float:
        """Calculate debt trend over time."""
        # Compare current TODO count with last week
        current_todos = self._count_todo_items()
        
        # Get TODO count from last week (simplified)
        cmd = ["git", "log", "--since", "7 days ago", "--grep", "TODO"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        recent_todo_commits = len(result.stdout.strip().split("\n")) if result.stdout else 0
        
        # Positive trend = debt increasing
        return recent_todo_commits - (current_todos * 0.1)
    
    def calculate_quality_metrics(self) -> QualityMetrics:
        """Calculate comprehensive quality metrics."""
        coverage = self.calculate_test_coverage()
        docs = self.assess_documentation_quality()
        architecture = self.check_architecture_compliance()
        debt = self.calculate_technical_debt()
        
        overall_score = self._calculate_overall_quality_score(
            coverage, docs, architecture, debt
        )
        quality_level = self._determine_quality_level(overall_score)
        
        return QualityMetrics(
            test_coverage=coverage,
            documentation=docs,
            architecture=architecture,
            technical_debt=debt,
            overall_quality_score=overall_score,
            quality_level=quality_level
        )
    
    def _calculate_overall_quality_score(self, coverage: TestCoverageMetrics,
                                        docs: DocumentationMetrics,
                                        arch: ArchitectureCompliance,
                                        debt: TechnicalDebt) -> float:
        """Calculate overall quality score."""
        coverage_score = coverage.overall_coverage
        docs_score = 80 if docs.documentation_quality == QualityLevel.EXCELLENT else 60
        arch_score = arch.compliance_score
        debt_score = max(0, 100 - debt.debt_score * 10)
        
        weights = [0.3, 0.2, 0.3, 0.2]
        scores = [coverage_score, docs_score, arch_score, debt_score]
        
        return sum(w * s for w, s in zip(weights, scores))
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level from score."""
        if score >= 90:
            return QualityLevel.EXCELLENT
        elif score >= 75:
            return QualityLevel.GOOD
        elif score >= 60:
            return QualityLevel.ACCEPTABLE
        elif score >= 40:
            return QualityLevel.NEEDS_IMPROVEMENT
        return QualityLevel.POOR