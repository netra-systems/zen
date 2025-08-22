"""Code impact metrics for AI Factory Status Report.

Measures lines of code, change complexity, and module coverage.
Module follows 450-line limit with 25-line function limit.
"""

import math
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from netra_backend.app.services.factory_status.git_commit_parser import (
    CommitInfo,
    CommitType,
    GitCommitParser,
)
from netra_backend.app.services.factory_status.git_diff_analyzer import (
    ChangeCategory,
    DiffMetrics,
    GitDiffAnalyzer,
)


class ImpactLevel(Enum):
    """Levels of code impact."""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeType(Enum):
    """Types of changes for impact analysis."""
    CUSTOMER_FACING = "customer_facing"
    INTERNAL = "internal"
    INFRASTRUCTURE = "infrastructure"
    TEST_ONLY = "test_only"


@dataclass
class CodebaseMetrics:
    """Overall codebase metrics."""
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    total_files: int
    modules_count: int
    test_coverage_percent: float


@dataclass
class ChangeComplexity:
    """Complexity metrics for changes."""
    cyclomatic_complexity: float
    cognitive_complexity: float
    dependency_impact: float
    file_coupling: float
    change_magnitude: float
    risk_score: float


@dataclass
class ModuleCoverage:
    """Module coverage assessment."""
    total_modules: int
    affected_modules: int
    coverage_percentage: float
    critical_modules_affected: int
    new_modules_introduced: int
    deprecated_modules: int


@dataclass
class ImpactMetrics:
    """Comprehensive impact metrics."""
    lines_added: int
    lines_deleted: int
    lines_modified: int
    net_change: int
    files_affected: int
    complexity: ChangeComplexity
    module_coverage: ModuleCoverage
    impact_level: ImpactLevel
    customer_vs_internal_ratio: float


class ImpactCalculator:
    """Calculator for code impact metrics."""
    
    CRITICAL_MODULES = [
        "app/auth", "app/db", "app/core", "app/llm", 
        "app/websocket", "frontend/components/chat"
    ]
    
    CUSTOMER_FACING_PATTERNS = [
        r"frontend/", r"app/routes/", r"app/schemas/",
        r"app/websocket/", r"public/"
    ]
    
    def __init__(self, repo_path: str = "."):
        """Initialize impact calculator."""
        self.commit_parser = GitCommitParser(repo_path)
        self.diff_analyzer = GitDiffAnalyzer(repo_path)
        self.repo_path = repo_path
    
    def calculate_codebase_metrics(self) -> CodebaseMetrics:
        """Calculate overall codebase metrics."""
        basic_counts = self._get_basic_counts()
        derived_metrics = self._get_derived_metrics(basic_counts)
        return self._build_codebase_metrics_object(basic_counts, derived_metrics)
    
    def _build_codebase_metrics_object(self, basic: Dict[str, int], derived: Dict[str, int]) -> CodebaseMetrics:
        """Build CodebaseMetrics object from counts."""
        return CodebaseMetrics(
            total_lines=basic["total_lines"], code_lines=basic["code_lines"],
            comment_lines=derived["comment_lines"], blank_lines=derived["blank_lines"],
            total_files=basic["total_files"], modules_count=basic["modules_count"],
            test_coverage_percent=basic["test_coverage"]
        )
    
    def _get_basic_counts(self) -> Dict[str, int]:
        """Get basic codebase counts."""
        total_lines, code_lines = self._count_lines()
        return {
            "total_lines": total_lines, "code_lines": code_lines,
            "total_files": self._count_files(), "modules_count": self._count_modules(),
            "test_coverage": self._estimate_test_coverage()
        }
    
    def _get_derived_metrics(self, basic_counts: Dict[str, int]) -> Dict[str, int]:
        """Get derived metrics from basic counts."""
        return {
            "comment_lines": self._count_comment_lines(),
            "blank_lines": basic_counts["total_lines"] - basic_counts["code_lines"]
        }
    
    def _count_lines(self) -> Tuple[int, int]:
        """Count total and code lines."""
        cmd = self._build_line_count_command()
        result = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
        total_lines = self._extract_total_lines(result.stdout)
        code_lines = int(total_lines * 0.7)  # Estimate 70% are code lines
        return total_lines, code_lines
    
    def _build_line_count_command(self) -> List[str]:
        """Build command for counting lines."""
        return ["find", ".", "-name", "*.py", "-o", "-name", "*.ts", 
               "-o", "-name", "*.tsx", "|", "xargs", "wc", "-l"]
    
    def _extract_total_lines(self, stdout: str) -> int:
        """Extract total line count from wc output."""
        if not stdout:
            return 0
        lines = stdout.strip().split("\n")
        return int(lines[-1].split()[0]) if lines else 0
    
    def _count_files(self) -> int:
        """Count total source files."""
        cmd = ["find", ".", "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return len(result.stdout.strip().split("\n")) if result.stdout else 0
    
    def _count_modules(self) -> int:
        """Count distinct modules."""
        modules = set()
        roots = ["app", "frontend"]
        for root in roots:
            self._collect_modules_from_root(root, modules)
        return len(modules)
    
    def _collect_modules_from_root(self, root: str, modules: Set[str]) -> None:
        """Collect modules from a root directory."""
        path = Path(self.repo_path) / root
        if not path.exists():
            return
        for item in path.rglob("*"):
            if item.is_dir() and not item.name.startswith("."):
                modules.add(str(item.relative_to(path)))
    
    def _count_comment_lines(self) -> int:
        """Estimate comment lines."""
        # Simple estimation - would need proper parsing for accuracy
        return int(self._count_lines()[0] * 0.15)  # Estimate 15% comments
    
    def _estimate_test_coverage(self) -> float:
        """Estimate test coverage percentage."""
        # Simplified estimation - would use coverage tools in practice
        test_files = self._count_test_files()
        source_files = self._count_files()
        
        coverage_ratio = min(test_files / max(source_files, 1), 1.0)
        return coverage_ratio * 100
    
    def _count_test_files(self) -> int:
        """Count test files."""
        cmd = ["find", ".", "-name", "*test*.py", "-o", "-name", "*test*.ts", 
               "-o", "-name", "*.test.*", "-o", "-name", "*.spec.*"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return len(result.stdout.strip().split("\n")) if result.stdout else 0
    
    def calculate_change_complexity(self, commit_hash: str) -> ChangeComplexity:
        """Calculate complexity of changes in commit."""
        diff_metrics = self.diff_analyzer.analyze_commit(commit_hash)
        complexity_metrics = self._calculate_all_complexity_metrics(diff_metrics)
        risk_score = self._compute_final_risk_score(complexity_metrics)
        return self._build_change_complexity(complexity_metrics, risk_score)
    
    def _compute_final_risk_score(self, metrics: Dict[str, float]) -> float:
        """Compute final risk score from complexity metrics."""
        return self._calculate_risk_score(
            metrics["cyclomatic"], metrics["cognitive"], metrics["dependency"],
            metrics["coupling"], metrics["magnitude"]
        )
    
    def _calculate_all_complexity_metrics(self, diff_metrics) -> Dict[str, float]:
        """Calculate all complexity metrics."""
        basic_metrics = self._calculate_basic_complexity_metrics(diff_metrics)
        advanced_metrics = self._calculate_advanced_complexity_metrics(diff_metrics)
        return {**basic_metrics, **advanced_metrics}
    
    def _calculate_basic_complexity_metrics(self, diff_metrics) -> Dict[str, float]:
        """Calculate basic complexity metrics."""
        return {
            "cyclomatic": self._calculate_cyclomatic_complexity(diff_metrics),
            "cognitive": self._calculate_cognitive_complexity(diff_metrics)
        }
    
    def _calculate_advanced_complexity_metrics(self, diff_metrics) -> Dict[str, float]:
        """Calculate advanced complexity metrics."""
        return {
            "dependency": self._calculate_dependency_impact(diff_metrics),
            "coupling": self._calculate_file_coupling(diff_metrics),
            "magnitude": self._calculate_change_magnitude(diff_metrics)
        }
    
    def _build_change_complexity(self, metrics: Dict[str, float], risk: float) -> ChangeComplexity:
        """Build ChangeComplexity object."""
        return ChangeComplexity(
            cyclomatic_complexity=metrics["cyclomatic"], cognitive_complexity=metrics["cognitive"],
            dependency_impact=metrics["dependency"], file_coupling=metrics["coupling"],
            change_magnitude=metrics["magnitude"], risk_score=risk
        )
    
    def _calculate_cyclomatic_complexity(self, metrics: DiffMetrics) -> float:
        """Calculate cyclomatic complexity score."""
        base_complexity = 1.0
        factors = self._get_cyclomatic_factors(metrics)
        return base_complexity + factors["file"] + factors["line"]
    
    def _get_cyclomatic_factors(self, metrics: DiffMetrics) -> Dict[str, float]:
        """Get factors for cyclomatic complexity."""
        return {
            "file": min(metrics.files_changed * 0.5, 5.0),
            "line": min((metrics.lines_added + metrics.lines_deleted) * 0.01, 3.0)
        }
    
    def _calculate_cognitive_complexity(self, metrics: DiffMetrics) -> float:
        """Calculate cognitive complexity score."""
        factors = self._get_cognitive_factors(metrics)
        base_complexity = factors["module"] + factors["category"]
        return base_complexity * factors["business"]
    
    def _get_cognitive_factors(self, metrics: DiffMetrics) -> Dict[str, float]:
        """Get factors for cognitive complexity."""
        return {
            "module": len(metrics.modules_affected) * 0.8,
            "business": 1.5 if metrics.customer_facing else 1.0,
            "category": self._get_category_complexity_factor(metrics.change_category)
        }
    
    def _get_category_complexity_factor(self, category: ChangeCategory) -> float:
        """Get complexity factor for change category."""
        factors = self._get_category_complexity_factors()
        return factors.get(category, 1.0)
    
    def _get_category_complexity_factors(self) -> Dict[ChangeCategory, float]:
        """Get category complexity factor mapping."""
        return {
            ChangeCategory.SECURITY: 3.0, ChangeCategory.INFRASTRUCTURE: 2.5,
            ChangeCategory.FEATURE: 2.0, ChangeCategory.REFACTOR: 1.8,
            ChangeCategory.BUGFIX: 1.5, ChangeCategory.TEST: 1.0,
            ChangeCategory.DOCS: 0.5
        }
    
    def _calculate_dependency_impact(self, metrics: DiffMetrics) -> float:
        """Calculate dependency impact score."""
        critical_affected = self._count_critical_affected(metrics.modules_affected)
        impact_components = self._get_impact_components(metrics.modules_affected, critical_affected)
        return min(impact_components["base"] + impact_components["critical"], 10.0)
    
    def _count_critical_affected(self, modules: Set[str]) -> int:
        """Count critical modules affected."""
        return sum(1 for module in modules 
                  if any(crit in module for crit in self.CRITICAL_MODULES))
    
    def _get_impact_components(self, modules: Set[str], critical_count: int) -> Dict[str, float]:
        """Get impact calculation components."""
        return {
            "base": len(modules) * 0.5,
            "critical": critical_count * 2.0
        }
    
    def _calculate_file_coupling(self, metrics: DiffMetrics) -> float:
        """Calculate file coupling factor."""
        if metrics.files_changed <= 1:
            return 1.0
        
        coupling = math.log10(metrics.files_changed) * 2
        return min(coupling, 5.0)
    
    def _calculate_change_magnitude(self, metrics: DiffMetrics) -> float:
        """Calculate change magnitude score."""
        total_changes = metrics.lines_added + metrics.lines_deleted
        magnitude = math.sqrt(total_changes) * 0.1
        
        return min(magnitude, 10.0)
    
    def _calculate_risk_score(self, cyclomatic: float, cognitive: float,
                             dependency: float, coupling: float, 
                             magnitude: float) -> float:
        """Calculate overall risk score."""
        weights = self._get_risk_weights()
        values = [cyclomatic, cognitive, dependency, coupling, magnitude]
        weighted_sum = self._compute_weighted_sum(weights, values)
        return min(weighted_sum, 10.0)
    
    def _get_risk_weights(self) -> List[float]:
        """Get risk calculation weights."""
        return [0.2, 0.25, 0.3, 0.15, 0.1]
    
    def _compute_weighted_sum(self, weights: List[float], values: List[float]) -> float:
        """Compute weighted sum of values."""
        return sum(w * v for w, v in zip(weights, values))
    
    def assess_module_coverage(self, hours: int = 24) -> ModuleCoverage:
        """Assess module coverage of recent changes."""
        coverage_data = self._gather_coverage_data(hours)
        metrics = self._calculate_coverage_metrics(coverage_data)
        return self._build_module_coverage_object(coverage_data, metrics)
    
    def _build_module_coverage_object(self, coverage_data: Dict[str, Any], metrics: Dict[str, Any]) -> ModuleCoverage:
        """Build ModuleCoverage object from data and metrics."""
        module_counts = self._extract_module_counts(coverage_data)
        metric_values = self._extract_metric_values(metrics)
        return ModuleCoverage(**module_counts, **metric_values, deprecated_modules=0)
    
    def _extract_module_counts(self, coverage_data: Dict[str, Any]) -> Dict[str, int]:
        """Extract module counts from coverage data."""
        return {
            "total_modules": len(coverage_data["all_modules"]),
            "affected_modules": len(coverage_data["affected_modules"])
        }
    
    def _extract_metric_values(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metric values."""
        return {
            "coverage_percentage": metrics["coverage_percentage"],
            "critical_modules_affected": metrics["critical_affected"],
            "new_modules_introduced": metrics["new_modules"]
        }
    
    def _gather_coverage_data(self, hours: int) -> Dict[str, Any]:
        """Gather data for coverage analysis."""
        commits = self.commit_parser.get_commits(hours)
        return {
            "all_modules": self._get_all_modules(),
            "affected_modules": self._get_affected_modules(commits),
            "hours": hours
        }
    
    def _calculate_coverage_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate coverage metrics from data."""
        coverage_pct = (len(data["affected_modules"]) / len(data["all_modules"])) * 100
        return {
            "coverage_percentage": coverage_pct,
            "critical_affected": self._count_critical_modules_affected(data["affected_modules"]),
            "new_modules": self._count_new_modules(data["hours"])
        }
    
    def _get_all_modules(self) -> Set[str]:
        """Get all modules in codebase."""
        modules = set()
        roots = ["app", "frontend"]
        for root in roots:
            self._collect_root_modules(root, modules)
        return modules
    
    def _collect_root_modules(self, root: str, modules: Set[str]) -> None:
        """Collect modules from a root directory."""
        path = Path(self.repo_path) / root
        if not path.exists():
            return
        for item in path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                modules.add(f"{root}/{item.name}")
    
    def _get_affected_modules(self, commits: List[CommitInfo]) -> Set[str]:
        """Get modules affected by commits."""
        modules = set()
        for commit in commits:
            self._add_commit_modules(commit, modules)
        return modules
    
    def _add_commit_modules(self, commit: CommitInfo, modules: Set[str]) -> None:
        """Add modules from commit to set."""
        diff_metrics = self.diff_analyzer.analyze_commit(commit.hash)
        modules.update(diff_metrics.modules_affected)
    
    def _count_critical_modules_affected(self, modules: Set[str]) -> int:
        """Count critical modules affected."""
        return sum(1 for module in modules 
                  if any(crit in module for crit in self.CRITICAL_MODULES))
    
    def _count_new_modules(self, hours: int) -> int:
        """Count new modules introduced."""
        # Simplified - would check git history for new directories
        return 0
    
    def calculate_customer_vs_internal_ratio(self, hours: int = 24) -> float:
        """Calculate ratio of customer-facing vs internal changes."""
        commits = self.commit_parser.get_commits(hours)
        change_counts = self._categorize_commit_changes(commits)
        return self._compute_ratio(change_counts)
    
    def _categorize_commit_changes(self, commits: List[CommitInfo]) -> Dict[str, int]:
        """Categorize changes as customer or internal."""
        changes_data = self._process_commit_changes(commits)
        return self._aggregate_change_counts(changes_data)
    
    def _process_commit_changes(self, commits: List[CommitInfo]) -> List[Tuple[int, bool]]:
        """Process commits and return change counts with customer_facing flag."""
        changes_data = []
        for commit in commits:
            diff_metrics = self.diff_analyzer.analyze_commit(commit.hash)
            changes = diff_metrics.lines_added + diff_metrics.lines_deleted
            changes_data.append((changes, diff_metrics.customer_facing))
        return changes_data
    
    def _aggregate_change_counts(self, changes_data: List[Tuple[int, bool]]) -> Dict[str, int]:
        """Aggregate change counts by customer vs internal."""
        customer_changes = sum(changes for changes, is_customer in changes_data if is_customer)
        internal_changes = sum(changes for changes, is_customer in changes_data if not is_customer)
        return {"customer": customer_changes, "internal": internal_changes}
    
    def _compute_ratio(self, change_counts: Dict[str, int]) -> float:
        """Compute customer vs internal ratio."""
        total = change_counts["customer"] + change_counts["internal"]
        if total == 0:
            return 0.0
        return change_counts["customer"] / total
    
    def calculate_impact_metrics(self, hours: int = 24) -> ImpactMetrics:
        """Calculate comprehensive impact metrics."""
        commits = self.commit_parser.get_commits(hours)
        basic_metrics = self._calculate_basic_impact_metrics(commits)
        advanced_metrics = self._calculate_advanced_impact_metrics(commits, hours, basic_metrics)
        return self._build_impact_metrics_object(basic_metrics, advanced_metrics)
    
    def _build_impact_metrics_object(self, basic: Dict[str, int], advanced: Dict[str, Any]) -> ImpactMetrics:
        """Build ImpactMetrics object from basic and advanced metrics."""
        return ImpactMetrics(
            lines_added=basic["added"], lines_deleted=basic["deleted"],
            lines_modified=basic["modified"], net_change=basic["net"],
            files_affected=basic["files"], complexity=advanced["complexity"],
            module_coverage=advanced["coverage"], impact_level=advanced["level"],
            customer_vs_internal_ratio=advanced["ratio"]
        )
    
    def _calculate_basic_impact_metrics(self, commits: List[CommitInfo]) -> Dict[str, int]:
        """Calculate basic impact metrics."""
        total_added = sum(c.insertions for c in commits)
        total_deleted = sum(c.deletions for c in commits)
        total_files = len(set(self._get_files_from_commits(commits)))
        return {
            "added": total_added, "deleted": total_deleted,
            "modified": total_added + total_deleted, "net": total_added - total_deleted,
            "files": total_files
        }
    
    def _calculate_advanced_impact_metrics(self, commits: List[CommitInfo], hours: int, 
                                         basic: Dict[str, int]) -> Dict[str, Any]:
        """Calculate advanced impact metrics."""
        complexity = (ChangeComplexity(0, 0, 0, 0, 0, 0) if not commits 
                     else self.calculate_change_complexity(commits[0].hash))
        return {
            "complexity": complexity,
            "coverage": self.assess_module_coverage(hours),
            "level": self._determine_impact_level(basic["added"], basic["deleted"], basic["files"]),
            "ratio": self.calculate_customer_vs_internal_ratio(hours)
        }
    
    def _get_files_from_commits(self, commits: List[CommitInfo]) -> List[str]:
        """Get unique files from commits."""
        # Simplified - would parse actual file changes
        return [f"file_{i}" for i in range(sum(c.files_changed for c in commits))]
    
    def _determine_impact_level(self, added: int, deleted: int, files: int) -> ImpactLevel:
        """Determine overall impact level."""
        total_changes = added + deleted
        thresholds = self._get_impact_thresholds()
        return self._evaluate_impact_thresholds(total_changes, files, thresholds)
    
    def _get_impact_thresholds(self) -> List[Tuple[int, int, ImpactLevel]]:
        """Get impact level thresholds."""
        return [
            (1000, 20, ImpactLevel.CRITICAL),
            (500, 10, ImpactLevel.HIGH),
            (200, 5, ImpactLevel.MODERATE),
            (50, 2, ImpactLevel.LOW)
        ]
    
    def _evaluate_impact_thresholds(self, total_changes: int, files: int, 
                                   thresholds: List[Tuple[int, int, ImpactLevel]]) -> ImpactLevel:
        """Evaluate impact level against thresholds."""
        for change_threshold, file_threshold, level in thresholds:
            if total_changes > change_threshold or files > file_threshold:
                return level
        return ImpactLevel.MINIMAL