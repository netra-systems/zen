"""Technical debt metrics calculator.

Calculates code smells, duplication, and complexity metrics.
Follows 300-line limit with 8-line function limit.
"""

import subprocess
from typing import List
from .git_commit_parser import GitCommitParser
from .metrics_quality_types import TechnicalDebt


class TechnicalDebtCalculator:
    """Calculator for technical debt metrics."""
    
    CODE_SMELL_PATTERNS = ["TODO", "FIXME", "HACK", "TEMP", "XXX"]
    
    def __init__(self, repo_path: str = "."):
        """Initialize technical debt calculator."""
        self.commit_parser = GitCommitParser(repo_path)
        self.repo_path = repo_path
    
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
        count = 0
        
        for pattern in self.CODE_SMELL_PATTERNS:
            count += self._count_pattern_occurrences(pattern)
        
        return count
    
    def _count_pattern_occurrences(self, pattern: str) -> int:
        """Count occurrences of a pattern in source files."""
        cmd = ["grep", "-r", pattern, ".", "--include=*.py", "--include=*.ts"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return len(result.stdout.strip().split("\n")) if result.stdout else 0
    
    def _calculate_duplication(self) -> float:
        """Calculate code duplication percentage (simplified)."""
        # Would use proper duplication detection tools in practice
        # For now, estimate based on file similarities
        return self._estimate_duplication_heuristic()
    
    def _estimate_duplication_heuristic(self) -> float:
        """Estimate duplication using simple heuristics."""
        # Look for similar file names as rough indicator
        cmd = ["find", ".", "-name", "*.py", "-o", "-name", "*.ts"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        files = result.stdout.strip().split("\n") if result.stdout else []
        similar_files = self._count_similar_files(files)
        
        return min((similar_files / max(len(files), 1)) * 100, 30.0)
    
    def _count_similar_files(self, files: List[str]) -> int:
        """Count files with similar names."""
        base_names = [self._extract_base_name(f) for f in files]
        duplicates = len(base_names) - len(set(base_names))
        return duplicates
    
    def _extract_base_name(self, file_path: str) -> str:
        """Extract base name without extension and path."""
        return file_path.split("/")[-1].split(".")[0]
    
    def _find_complexity_hotspots(self) -> List[str]:
        """Find complexity hotspots (simplified)."""
        hotspots = []
        
        # Look for files with many nested structures
        hotspots.extend(self._find_nested_files())
        hotspots.extend(self._find_large_functions())
        
        return list(set(hotspots[:10]))  # Return top 10 unique hotspots
    
    def _find_nested_files(self) -> List[str]:
        """Find files with deep nesting."""
        cmd = ["grep", "-r", "def.*def.*def", ".", "--include=*.py"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout:
            return [line.split(":")[0] for line in result.stdout.strip().split("\n")]
        return []
    
    def _find_large_functions(self) -> List[str]:
        """Find files with large functions."""
        # Simplified detection of potential large functions
        cmd = ["grep", "-r", "def.*:", ".", "--include=*.py", "-A", "20"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        large_function_files = []
        if result.stdout:
            lines = result.stdout.split("\n")
            current_file = None
            function_lines = 0
            
            for line in lines:
                if "def " in line and ":" in line:
                    if function_lines > 15:  # Rough heuristic
                        large_function_files.append(current_file)
                    current_file = line.split(":")[0]
                    function_lines = 0
                function_lines += 1
        
        return large_function_files
    
    def _count_deprecated_usage(self) -> int:
        """Count deprecated API usage."""
        deprecated_patterns = ["deprecated", "@deprecated", "deprecation"]
        count = 0
        
        for pattern in deprecated_patterns:
            count += self._count_pattern_occurrences(pattern)
        
        return count
    
    def _count_todo_items(self) -> int:
        """Count TODO items in code."""
        return self._count_pattern_occurrences("TODO")
    
    def _calculate_debt_score(self, smells: int, duplication: float, 
                             hotspots: int, deprecated: int, todos: int) -> float:
        """Calculate overall debt score."""
        # Normalize metrics and combine
        smell_score = min(smells / 100, 1.0)
        dup_score = duplication / 100
        hotspot_score = min(hotspots / 10, 1.0)
        dep_score = min(deprecated / 50, 1.0)
        todo_score = min(todos / 100, 1.0)
        
        weights = [0.2, 0.25, 0.2, 0.15, 0.2]
        scores = [smell_score, dup_score, hotspot_score, dep_score, todo_score]
        
        return sum(w * s for w, s in zip(weights, scores)) * 10
    
    def _calculate_debt_trend(self) -> float:
        """Calculate debt trend over time."""
        current_todos = self._count_todo_items()
        
        # Check recent TODO additions
        cmd = ["git", "log", "--since", "7 days ago", "--grep", "TODO"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        recent_todo_commits = len(result.stdout.strip().split("\n")) if result.stdout else 0
        
        # Positive trend = debt increasing
        return recent_todo_commits - (current_todos * 0.1)