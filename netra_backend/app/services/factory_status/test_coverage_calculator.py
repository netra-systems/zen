"""Test coverage calculation module.

Calculates test coverage metrics and trends.
Follows 450-line limit with 25-line function limit.
"""

import subprocess
from pathlib import Path
from typing import List

from netra_backend.app.services.factory_status.quality_models import TestCoverageMetrics
from netra_backend.app.services.factory_status.git_commit_parser import GitCommitParser, CommitType


class TestCoverageCalculator:
    """Calculator for test coverage metrics."""
    
    CRITICAL_FILES = [
        "app/auth", "app/db", "app/core", "app/llm",
        "app/websocket", "frontend/components/chat"
    ]
    
    def __init__(self, repo_path: str = "."):
        """Initialize coverage calculator."""
        self.commit_parser = GitCommitParser(repo_path)
        self.repo_path = repo_path
    
    def calculate_coverage(self) -> TestCoverageMetrics:
        """Calculate test coverage metrics."""
        test_files = self._count_test_files()
        source_files = self._count_source_files()
        coverage = self._estimate_coverage()
        trend = self._calculate_trend()
        uncovered = self._find_uncovered_critical()
        
        return self._build_metrics(
            coverage, test_files, source_files, trend, uncovered
        )
    
    def _build_metrics(self, coverage: float, test_files: int,
                      source_files: int, trend: float,
                      uncovered: List[str]) -> TestCoverageMetrics:
        """Build coverage metrics object."""
        return TestCoverageMetrics(
            overall_coverage=coverage,
            line_coverage=coverage * 0.9,
            function_coverage=coverage * 0.85,
            branch_coverage=coverage * 0.8
        )
    
    def _count_test_files(self) -> int:
        """Count test files in repository."""
        patterns = ["*test*.py", "*test*.ts", "*.test.*", "*.spec.*"]
        count = 0
        for pattern in patterns:
            result = self._run_find_command(pattern)
            count += self._count_lines_in_output(result.stdout)
        return count
    
    def _count_source_files(self) -> int:
        """Count source files in repository."""
        cmd = ["find", ".", "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return self._count_lines_in_output(result.stdout)
    
    def _run_find_command(self, pattern: str) -> subprocess.CompletedProcess:
        """Run find command for pattern."""
        cmd = ["find", ".", "-name", pattern, "-type", "f"]
        return subprocess.run(cmd, capture_output=True, text=True)
    
    def _count_lines_in_output(self, output: str) -> int:
        """Count non-empty lines in command output."""
        if not output:
            return 0
        lines = output.strip().split("\n")
        return len([line for line in lines if line.strip()])
    
    def _estimate_coverage(self) -> float:
        """Estimate test coverage percentage."""
        test_files = self._count_test_files()
        source_files = self._count_source_files()
        return self._calculate_coverage_ratio(test_files, source_files)
    
    def _calculate_coverage_ratio(self, test_files: int, source_files: int) -> float:
        """Calculate coverage ratio from file counts."""
        if source_files == 0:
            return 0.0
        ratio = min(test_files / source_files, 1.0)
        return ratio * 100
    
    def _calculate_trend(self) -> float:
        """Calculate coverage trend over last week."""
        commits = self.commit_parser.get_commits(168)
        test_commits = self._filter_test_commits(commits)
        return self._calculate_test_ratio(commits, test_commits)
    
    def _filter_test_commits(self, commits: List) -> List:
        """Filter commits for test-related changes."""
        return [c for c in commits if c.commit_type == CommitType.TEST]
    
    def _calculate_test_ratio(self, all_commits: List, test_commits: List) -> float:
        """Calculate test commit ratio."""
        if not all_commits:
            return 0.0
        test_ratio = len(test_commits) / len(all_commits)
        return (test_ratio - 0.2) * 100
    
    def _find_uncovered_critical(self) -> List[str]:
        """Find critical files without test coverage."""
        uncovered = []
        for critical_path in self.CRITICAL_FILES:
            if not self._has_test(critical_path):
                uncovered.append(critical_path)
        return uncovered
    
    def _has_test(self, file_path: str) -> bool:
        """Check if file has corresponding test."""
        patterns = [f"test_{file_path}", f"{file_path}_test", f"{file_path}.test"]
        repo_path = Path(self.repo_path)
        return any(repo_path.glob(f"**/{pattern}*") for pattern in patterns)
