#!/usr/bin/env python3
"""
System boundary checking module for boundary enforcement system.
Handles system-wide metrics and boundary validation.
"""

import glob
import re
import subprocess
from pathlib import Path
from typing import Dict, Tuple, Union

try:
    import radon.complexity as radon_cc
    HAS_RADON = True
except ImportError:
    HAS_RADON = False

from boundary_enforcer_core_types import (
    BoundaryViolation,
    SystemBoundaries,
    get_file_patterns,
    should_skip_file,
)


class SystemBoundaryChecker:
    """Handles system-wide boundary validation"""
    
    def __init__(self, root_path: Path, boundaries: SystemBoundaries):
        self.root_path = root_path
        self.boundaries = boundaries
        self.system_metrics: Dict[str, Union[int, float]] = {}

    def collect_system_metrics(self) -> Dict[str, Union[int, float]]:
        """Collect comprehensive system metrics"""
        file_metrics = self._count_system_files()
        growth_metrics = self._calculate_growth_metrics()
        self.system_metrics = self._build_metrics_dict(file_metrics, growth_metrics)
        return self.system_metrics.copy()

    def check_module_count_boundary(self) -> BoundaryViolation:
        """Check module count boundary"""
        if self.system_metrics["module_count"] <= self.boundaries.max_module_count:
            return None
        return self._create_module_count_violation()

    def check_total_loc_boundary(self) -> BoundaryViolation:
        """Check total lines of code boundary"""
        if self.system_metrics["total_lines"] <= self.boundaries.max_total_loc:
            return None
        return self._create_total_loc_violation()

    def check_complexity_boundary(self) -> BoundaryViolation:
        """Check complexity score boundary"""
        avg_complexity = self.system_metrics.get("complexity_debt", 0)
        if avg_complexity <= self.boundaries.max_complexity_score:
            return None
        return self._create_complexity_violation(avg_complexity)

    def _count_system_files(self) -> Dict[str, int]:
        """Count files and lines across system patterns"""
        total_files, total_lines, module_count = 0, 0, 0
        for pattern in get_file_patterns():
            file_count, line_count = self._count_pattern_files(pattern)
            total_files += file_count
            total_lines += line_count
            module_count += file_count
        return {"total_files": total_files, "total_lines": total_lines, "module_count": module_count}

    def _count_pattern_files(self, pattern: str) -> Tuple[int, int]:
        """Count files and lines for a specific glob pattern"""
        file_count, line_count = 0, 0
        for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
            if should_skip_file(filepath):
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

class SystemMetricsCalculator:
    """Calculates advanced system metrics"""
    
    def __init__(self, root_path: Path):
        self.root_path = root_path

    def calculate_growth_velocity(self) -> float:
        """Calculate system growth velocity using git stats"""
        try:
            commits_count = self._get_recent_commits()
            lines_changed = self._get_lines_changed()
            return commits_count * 0.1 + lines_changed * 0.001
        except Exception:
            return 0.0

    def calculate_complexity_debt(self) -> float:
        """Calculate total complexity debt across system"""
        if not HAS_RADON:
            return 0.0
        total_complexity, file_count = 0, 0
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if should_skip_file(filepath):
                continue
            complexity = self._get_file_complexity(filepath)
            if complexity >= 0:
                total_complexity += complexity
                file_count += 1
        return total_complexity / file_count if file_count > 0 else 0.0

    def _get_recent_commits(self) -> int:
        """Get number of commits in last 30 days"""
        result = subprocess.run(
            ['git', 'log', '--oneline', '--since="30 days ago"'],
            capture_output=True, text=True, cwd=self.root_path
        )
        return len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

    def _get_lines_changed(self) -> int:
        """Get lines changed in recent commits"""
        result = subprocess.run(
            ['git', 'diff', '--stat', 'HEAD~10', 'HEAD'],
            capture_output=True, text=True, cwd=self.root_path
        )
        return self._extract_lines_changed(result.stdout)

    def _extract_lines_changed(self, git_output: str) -> int:
        """Extract line changes from git diff output"""
        match = re.search(r'(\d+) insertions?\(\+\)', git_output)
        insertions = int(match.group(1)) if match else 0
        match = re.search(r'(\d+) deletions?\(-\)', git_output)
        deletions = int(match.group(1)) if match else 0
        return insertions + deletions

    def _get_file_complexity(self, filepath: str) -> float:
        """Get complexity score for a single file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                complexity_scores = radon_cc.cc_visit(content)
                return sum(score.complexity for score in complexity_scores)
        except Exception:
            return -1

class ViolationFactory:
    """Creates system boundary violations"""
    
    @staticmethod
    def create_module_count_violation(actual: int, expected: int) -> BoundaryViolation:
        """Create module count boundary violation"""
        return BoundaryViolation(
            file_path="SYSTEM_WIDE", violation_type="module_count_boundary", severity="critical",
            boundary_name="MODULE_COUNT_LIMIT", actual_value=actual, expected_value=expected,
            impact_score=10, description=f"System exceeds {expected} module HARD LIMIT",
            fix_suggestion="EMERGENCY: Archive unused modules, consolidate similar modules"
        )

    @staticmethod
    def create_total_loc_violation(actual: int, expected: int) -> BoundaryViolation:
        """Create total LOC boundary violation"""
        return BoundaryViolation(
            file_path="SYSTEM_WIDE", violation_type="total_loc_boundary", severity="critical",
            boundary_name="TOTAL_LOC_LIMIT", actual_value=actual, expected_value=expected,
            impact_score=10, description=f"System exceeds {expected} LOC HARD LIMIT",
            fix_suggestion="EMERGENCY: Remove deprecated code, refactor duplicates"
        )

    @staticmethod
    def create_complexity_violation(actual: float, expected: float) -> BoundaryViolation:
        """Create complexity boundary violation"""
        return BoundaryViolation(
            file_path="SYSTEM_WIDE", violation_type="complexity_boundary", severity="high",
            boundary_name="COMPLEXITY_LIMIT", impact_score=8,
            actual_value=int(actual * 100), expected_value=int(expected * 100),
            description=f"System complexity exceeds {expected} LIMIT",
            fix_suggestion="Refactor complex functions, simplify logic paths"
        )

# Integration methods for SystemBoundaryChecker
def _calculate_growth_metrics(self) -> Dict[str, float]:
    """Calculate advanced growth and complexity metrics"""
    calculator = SystemMetricsCalculator(self.root_path)
    return {
        "growth_velocity": calculator.calculate_growth_velocity(),
        "complexity_debt": calculator.calculate_complexity_debt()
    }

def _build_metrics_dict(self, file_metrics: Dict[str, int], growth_metrics: Dict[str, float]) -> Dict[str, Union[int, float]]:
    """Build final metrics dictionary combining all metrics"""
    avg_file_size = file_metrics["total_lines"] / file_metrics["total_files"] if file_metrics["total_files"] > 0 else 0
    return {**file_metrics, "avg_file_size": avg_file_size, **growth_metrics}

def _create_module_count_violation(self) -> BoundaryViolation:
    """Create module count violation using factory"""
    return ViolationFactory.create_module_count_violation(
        self.system_metrics["module_count"], self.boundaries.max_module_count
    )

def _create_total_loc_violation(self) -> BoundaryViolation:
    """Create total LOC violation using factory"""
    return ViolationFactory.create_total_loc_violation(
        self.system_metrics["total_lines"], self.boundaries.max_total_loc
    )

def _create_complexity_violation(self, avg_complexity: float) -> BoundaryViolation:
    """Create complexity violation using factory"""
    return ViolationFactory.create_complexity_violation(
        avg_complexity, self.boundaries.max_complexity_score
    )

# Bind methods to SystemBoundaryChecker
SystemBoundaryChecker._calculate_growth_metrics = _calculate_growth_metrics
SystemBoundaryChecker._build_metrics_dict = _build_metrics_dict
SystemBoundaryChecker._create_module_count_violation = _create_module_count_violation
SystemBoundaryChecker._create_total_loc_violation = _create_total_loc_violation
SystemBoundaryChecker._create_complexity_violation = _create_complexity_violation