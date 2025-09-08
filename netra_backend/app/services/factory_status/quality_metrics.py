"""Quality metrics calculator for test coverage and documentation.

Handles test coverage analysis and documentation quality assessment.
Module follows 450-line limit with 25-line function limit.
"""

import subprocess
from pathlib import Path
from typing import List

from netra_backend.app.services.factory_status.git_commit_parser import (
    CommitType,
    GitCommitParser,
)
from netra_backend.app.services.factory_status.quality_core import (
    DocumentationMetrics,
    QualityConstants,
    QualityLevel,
    TestCoverageMetrics,
)


class TestCoverageCalculator:
    """Calculator for test coverage metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize coverage calculator."""
        self.commit_parser = GitCommitParser(repo_path)
        self.repo_path = repo_path
    
    def calculate(self) -> TestCoverageMetrics:
        """Calculate test coverage metrics."""
        test_files = self._count_test_files()
        source_files = self._count_source_files()
        coverage = self._estimate_coverage()
        trend = self._calculate_coverage_trend()
        uncovered = self._find_uncovered_critical_files()
        
        return TestCoverageMetrics(
            overall_coverage=coverage,
            line_coverage=coverage * 0.9,
            function_coverage=coverage * 0.85,
            branch_coverage=coverage * 0.8,
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
            count += self._count_files_by_pattern(pattern)
        return count
    
    def _count_files_by_pattern(self, pattern: str) -> int:
        """Count files matching pattern."""
        cmd = ["find", ".", "-name", pattern, "-type", "f"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return len(result.stdout.strip().split("\n")) if result.stdout else 0
    
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
        
        ratio = min(test_files / source_files, 1.0)
        return ratio * 100
    
    def _calculate_coverage_trend(self) -> float:
        """Calculate coverage trend over last week."""
        commits = self.commit_parser.get_commits(168)
        test_commits = [c for c in commits if c.commit_type == CommitType.TEST]
        
        if not commits:
            return 0.0
        
        test_ratio = len(test_commits) / len(commits)
        return (test_ratio - 0.2) * 100
    
    def _find_uncovered_critical_files(self) -> List[str]:
        """Find critical files without test coverage."""
        uncovered = []
        for critical_path in QualityConstants.CRITICAL_FILES:
            test_exists = self._has_corresponding_test(critical_path)
            if not test_exists:
                uncovered.append(critical_path)
        return uncovered
    
    def _has_corresponding_test(self, file_path: str) -> bool:
        """Check if file has corresponding test."""
        test_patterns = [f"test_{file_path}", f"{file_path}_test", f"{file_path}.test"]
        return any(Path(self.repo_path).glob(f"**/{pattern}*") for pattern in test_patterns)


class DocumentationCalculator:
    """Calculator for documentation quality metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize documentation calculator."""
        self.repo_path = repo_path
    
    def calculate(self) -> DocumentationMetrics:
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


# Stub imports for compatibility
from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict

class ContentType(Enum):
    """Content type enumeration for quality validation."""
    TEXT = "text"
    CODE = "code"
    JSON = "json"
    MARKDOWN = "markdown"

@dataclass
class QualityMetrics:
    """Quality metrics dataclass."""
    score: float = 0.0
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass
class ValidationResult:
    """Validation result dataclass."""
    is_valid: bool = True
    score: float = 0.0
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []