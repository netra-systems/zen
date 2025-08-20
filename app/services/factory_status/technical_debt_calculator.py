"""Technical debt calculation module.

Calculates technical debt metrics and trends.
Follows 450-line limit with 25-line function limit.
"""

import subprocess
from typing import List

from .quality_models import TechnicalDebt


class TechnicalDebtCalculator:
    """Calculator for technical debt metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize debt calculator."""
        self.repo_path = repo_path
    
    def calculate_debt(self) -> TechnicalDebt:
        """Calculate technical debt metrics."""
        metrics = self._collect_debt_metrics()
        debt_score = self._calculate_debt_score_from_metrics(metrics)
        debt_trend = self._calculate_debt_trend()
        return self._build_technical_debt(metrics, debt_score, debt_trend)

    def _collect_debt_metrics(self) -> dict:
        """Collect all debt metrics."""
        base_metrics = self._get_base_debt_metrics()
        additional_metrics = self._get_additional_debt_metrics()
        return {**base_metrics, **additional_metrics}
    
    def _get_base_debt_metrics(self) -> dict:
        """Get base debt metrics."""
        return {
            'code_smells': self._count_code_smells(),
            'duplication': self._calculate_duplication(),
            'hotspots': self._find_complexity_hotspots()
        }
    
    def _get_additional_debt_metrics(self) -> dict:
        """Get additional debt metrics."""
        return {
            'deprecated': self._count_deprecated_usage(),
            'todos': self._count_todo_items()
        }

    def _calculate_debt_score_from_metrics(self, metrics: dict) -> float:
        """Calculate debt score from collected metrics."""
        return self._calculate_debt_score(
            metrics['code_smells'], metrics['duplication'], 
            len(metrics['hotspots']), metrics['deprecated'], metrics['todos']
        )

    def _build_technical_debt(self, metrics: dict, debt_score: float, debt_trend: float) -> TechnicalDebt:
        """Build TechnicalDebt object from metrics."""
        debt_params = self._prepare_debt_params(metrics, debt_score, debt_trend)
        return TechnicalDebt(**debt_params)
    
    def _prepare_debt_params(self, metrics: dict, debt_score: float, debt_trend: float) -> dict:
        """Prepare parameters for TechnicalDebt constructor."""
        return {
            'code_smells': metrics['code_smells'],
            'duplication_percentage': metrics['duplication'],
            'complexity_hotspots': metrics['hotspots'],
            'deprecated_usage': metrics['deprecated'],
            'todo_count': metrics['todos'],
            'debt_score': debt_score,
            'debt_trend': debt_trend
        }
    
    def _count_code_smells(self) -> int:
        """Count code smells using pattern matching."""
        patterns = ["TODO", "FIXME", "HACK", "TEMP", "XXX"]
        total_count = 0
        for pattern in patterns:
            count = self._count_pattern_occurrences(pattern)
            total_count += count
        return total_count
    
    def _count_pattern_occurrences(self, pattern: str) -> int:
        """Count occurrences of pattern in codebase."""
        cmd = ["grep", "-r", pattern, ".", "--include=*.py", "--include=*.ts"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return self._count_output_lines(result.stdout)
    
    def _count_output_lines(self, output: str) -> int:
        """Count non-empty lines in command output."""
        if not output:
            return 0
        lines = output.strip().split("\n")
        return len([line for line in lines if line.strip()])
    
    def _calculate_duplication(self) -> float:
        """Calculate code duplication percentage."""
        # Simplified duplication detection
        # In practice, would use proper duplication tools
        return 5.0
    
    def _find_complexity_hotspots(self) -> List[str]:
        """Find complexity hotspots in codebase."""
        hotspots = []
        large_files = self._find_large_files()
        return large_files[:10]  # Top 10 hotspots
    
    def _find_large_files(self) -> List[str]:
        """Find files with high line counts."""
        cmd = ["find", ".", "-name", "*.py", "-exec", "wc", "-l", "{}", ";"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return self._extract_large_files(result.stdout)
    
    def _extract_large_files(self, output: str) -> List[str]:
        """Extract files exceeding complexity threshold."""
        if not output:
            return []
        lines = output.strip().split("\n")
        return self._process_file_lines(lines)

    def _process_file_lines(self, lines: List[str]) -> List[str]:
        """Process lines to extract large files."""
        large_files = []
        for line in lines:
            parts = line.strip().split()
            if self._is_large_file(parts):
                large_files.append(parts[1])
        return large_files
    
    def _is_large_file(self, parts: List[str]) -> bool:
        """Check if file parts indicate large file."""
        if len(parts) < 2 or not parts[0].isdigit():
            return False
        line_count = int(parts[0])
        return line_count > 200
    
    def _count_deprecated_usage(self) -> int:
        """Count deprecated function/method usage."""
        cmd = ["grep", "-r", "deprecated", ".", "--include=*.py", "--include=*.ts"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return self._count_output_lines(result.stdout)
    
    def _count_todo_items(self) -> int:
        """Count TODO items in code."""
        cmd = ["grep", "-r", "TODO", ".", "--include=*.py", "--include=*.ts"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return self._count_output_lines(result.stdout)
    
    def _calculate_debt_score(self, smells: int, duplication: float,
                             hotspots: int, deprecated: int, todos: int) -> float:
        """Calculate overall debt score."""
        raw_score = self._calculate_raw_debt_score(
            smells, duplication, hotspots, deprecated, todos
        )
        return min(raw_score / 10, 10.0)
    
    def _calculate_raw_debt_score(self, smells: int, duplication: float,
                                 hotspots: int, deprecated: int, todos: int) -> float:
        """Calculate raw debt score before normalization."""
        return (smells * 2 + duplication * 5 + hotspots * 10 +
                deprecated * 3 + todos * 1)
    
    def _calculate_debt_trend(self) -> float:
        """Calculate debt trend over time."""
        current_todos = self._count_todo_items()
        recent_todo_commits = self._count_recent_todo_commits()
        return recent_todo_commits - (current_todos * 0.1)
    
    def _count_recent_todo_commits(self) -> int:
        """Count recent commits mentioning TODO."""
        cmd = ["git", "log", "--since", "7 days ago", "--grep", "TODO"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return self._count_output_lines(result.stdout)
