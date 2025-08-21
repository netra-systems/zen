"""Test coverage metrics calculator.

Calculates test coverage and related metrics.
Follows 450-line limit with 25-line function limit.
"""

import subprocess
from pathlib import Path
from typing import List

from netra_backend.app.services.factory_status.git_commit_parser import (
    CommitType,
    GitCommitParser,
)
from netra_backend.app.services.factory_status.metrics_quality_types import (
    TestCoverageMetrics,
)


class TestCoverageCalculator:
    """Calculator for test coverage metrics."""
    
    CRITICAL_FILES = [
        "app/auth", "app/db", "app/core", "app/llm",
        "app/websocket", "frontend/components/chat"
    ]
    
    def __init__(self, repo_path: str = "."):
        """Initialize test coverage calculator."""
        self.commit_parser = GitCommitParser(repo_path)
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
            count += self._count_files_by_pattern(pattern)
        return count
    
    def _count_files_by_pattern(self, pattern: str) -> int:
        """Count files matching a pattern."""
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
        
        # Simple heuristic based on test to source ratio
        ratio = min(test_files / source_files, 1.0)
        return ratio * 100
    
    def _calculate_coverage_trend(self) -> float:
        """Calculate coverage trend over last week."""
        commits = self.commit_parser.get_commits(168)  # Last week
        test_commits = self._filter_test_commits(commits)
        
        if not commits:
            return 0.0
        
        test_ratio = len(test_commits) / len(commits)
        return (test_ratio - 0.2) * 100  # Baseline 20% test commits
    
    def _filter_test_commits(self, commits) -> List:
        """Filter commits that are test-related."""
        return [c for c in commits if c.commit_type == CommitType.TEST]
    
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
        test_patterns = self._generate_test_patterns(file_path)
        return any(Path(self.repo_path).glob(f"**/{pattern}*") for pattern in test_patterns)
    
    def _generate_test_patterns(self, file_path: str) -> List[str]:
        """Generate test file patterns for a given path."""
        return [f"test_{file_path}", f"{file_path}_test", f"{file_path}.test"]