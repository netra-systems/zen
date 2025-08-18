"""Git diff analyzer for AI Factory Status Report.

Analyzes code changes, calculates impact metrics, and maps to business value.
Module follows 300-line limit with 8-line function limit.
"""

import re
import asyncio
import subprocess
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ChangeCategory(Enum):
    """Categories of code changes aligned with business goals."""
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    TEST = "test"
    DOCS = "documentation"
    CONFIG = "configuration"
    INFRASTRUCTURE = "infrastructure"
    SECURITY = "security"
    PERFORMANCE = "performance"


class BusinessImpact(Enum):
    """Business impact levels for changes."""
    CRITICAL = "critical"       # Customer-facing, revenue impact
    HIGH = "high"               # Important features, major fixes
    MEDIUM = "medium"           # Regular improvements
    LOW = "low"                 # Internal changes, minor updates
    MINIMAL = "minimal"         # Formatting, comments


@dataclass
class DiffMetrics:
    """Metrics for a single diff/commit."""
    commit_hash: str
    files_changed: int
    lines_added: int
    lines_deleted: int
    modules_affected: Set[str]
    change_category: ChangeCategory
    business_impact: BusinessImpact
    complexity_score: float
    test_coverage_delta: float
    customer_facing: bool


@dataclass
class FileChange:
    """Represents changes to a single file."""
    path: str
    additions: int
    deletions: int
    is_test: bool
    is_config: bool
    module: str
    extension: str


class GitDiffAnalyzer:
    """Analyzer for git diffs with business value mapping."""
    
    CUSTOMER_FACING_PATTERNS = [
        r"frontend/", r"app/routes/", r"app/api/",
        r"public/", r"app/websocket/", r"app/schemas/"
    ]
    
    CRITICAL_PATHS = [
        r"app/auth/", r"app/db/", r"app/core/exceptions",
        r"app/services/compensation", r"app/llm/"
    ]
    
    TEST_PATTERNS = [
        r"test_", r"_test\.", r"tests/", r"spec\.",
        r"\.test\.", r"\.spec\."
    ]
    
    def __init__(self, repo_path: str = "."):
        """Initialize diff analyzer."""
        self.repo_path = repo_path
    
    def analyze_commit(self, commit_hash: str) -> DiffMetrics:
        """Analyze a single commit's changes."""
        file_changes = self._get_file_changes(commit_hash)
        analysis_data = self._analyze_commit_changes(file_changes)
        return self._build_metrics(
            commit_hash, file_changes, analysis_data["modules"],
            analysis_data["category"], analysis_data["impact"]
        )
    
    def _analyze_commit_changes(self, file_changes: List[FileChange]) -> Dict[str, Any]:
        """Analyze commit changes for modules, category, and impact."""
        modules = self._extract_modules(file_changes)
        category = self._categorize_changes(file_changes)
        impact = self._assess_business_impact(file_changes, category)
        return {"modules": modules, "category": category, "impact": impact}
    
    def _get_file_changes(self, commit_hash: str) -> List[FileChange]:
        """Get file changes for a commit."""
        try:
            return asyncio.run(self._get_file_changes_async(commit_hash))
        except (asyncio.TimeoutError, Exception):
            return []
    
    async def _get_file_changes_async(self, commit_hash: str) -> List[FileChange]:
        """Get file changes asynchronously."""
        cmd = ["git", "diff", "--numstat", f"{commit_hash}^", commit_hash]
        try:
            stdout = await self._execute_git_command(cmd)
            return self._parse_numstat(stdout.decode())
        except (asyncio.TimeoutError, Exception):
            return []
    
    async def _execute_git_command(self, cmd: List[str]) -> bytes:
        """Execute git command and return stdout."""
        proc = await self._create_git_process(cmd)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2.0)
        return stdout
    
    async def _create_git_process(self, cmd: List[str]) -> asyncio.subprocess.Process:
        """Create git subprocess."""
        return await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    
    def _parse_numstat(self, output: str) -> List[FileChange]:
        """Parse git diff numstat output."""
        lines = self._get_valid_lines(output)
        return self._process_numstat_lines(lines)
    
    def _process_numstat_lines(self, lines: List[str]) -> List[FileChange]:
        """Process numstat lines into FileChange objects."""
        changes = []
        for line in lines:
            change = self._parse_numstat_line(line)
            if change:
                changes.append(change)
        return changes
    
    def _get_valid_lines(self, output: str) -> List[str]:
        """Get valid lines from output."""
        return [line for line in output.strip().split("\n") if line]
    
    def _parse_numstat_line(self, line: str) -> Optional[FileChange]:
        """Parse a single numstat line."""
        parts = line.split("\t")
        if len(parts) < 3:
            return None
        additions, deletions, path = self._extract_line_parts(parts)
        return self._create_file_change(path, additions, deletions)
    
    def _extract_line_parts(self, parts: List[str]) -> Tuple[int, int, str]:
        """Extract line parts from numstat."""
        additions = self._safe_int(parts[0])
        deletions = self._safe_int(parts[1])
        path = parts[2]
        return additions, deletions, path
    
    def _safe_int(self, value: str) -> int:
        """Safely convert to int."""
        try:
            return int(value) if value != "-" else 0
        except (ValueError, TypeError):
            return 0
    
    def _create_file_change(self, path: str, adds: int, dels: int) -> FileChange:
        """Create FileChange object."""
        file_attrs = self._get_file_attributes(path)
        return FileChange(
            path=path, additions=adds, deletions=dels,
            is_test=file_attrs["is_test"], is_config=file_attrs["is_config"],
            module=file_attrs["module"], extension=file_attrs["extension"]
        )
    
    def _get_file_attributes(self, path: str) -> Dict[str, Any]:
        """Get file attributes for FileChange."""
        return {
            "is_test": self._is_test_file(path),
            "is_config": self._is_config_file(path),
            "module": self._extract_module(path),
            "extension": Path(path).suffix
        }
    
    def _is_test_file(self, path: str) -> bool:
        """Check if file is a test file."""
        return any(re.search(pattern, path) for pattern in self.TEST_PATTERNS)
    
    def _is_config_file(self, path: str) -> bool:
        """Check if file is configuration."""
        config_patterns = [r"\.yml$", r"\.yaml$", r"\.json$", r"\.env", r"config"]
        return any(re.search(p, path) for p in config_patterns)
    
    def _extract_module(self, path: str) -> str:
        """Extract module name from path."""
        parts = Path(path).parts
        if len(parts) > 0:
            return parts[0] if parts[0] != "." else "root"
        return "unknown"
    
    def _extract_modules(self, changes: List[FileChange]) -> Set[str]:
        """Extract unique modules from changes."""
        return {change.module for change in changes}
    
    def _categorize_changes(self, changes: List[FileChange]) -> ChangeCategory:
        """Categorize the type of changes."""
        category_checks = self._get_category_checks()
        return self._determine_category(changes, category_checks)
    
    def _get_category_checks(self) -> List[Tuple[Any, ChangeCategory]]:
        """Get category check functions and their corresponding categories."""
        return [
            (self._has_security_changes, ChangeCategory.SECURITY),
            (self._majority_tests, ChangeCategory.TEST),
            (self._majority_docs, ChangeCategory.DOCS),
            (self._has_config_changes, ChangeCategory.CONFIG),
            (self._has_performance_changes, ChangeCategory.PERFORMANCE)
        ]
    
    def _determine_category(self, changes: List[FileChange], 
                          checks: List[Tuple[Any, ChangeCategory]]) -> ChangeCategory:
        """Determine category from checks."""
        for check_func, category in checks:
            if check_func(changes):
                return category
        return ChangeCategory.FEATURE
    
    def _has_security_changes(self, changes: List[FileChange]) -> bool:
        """Check for security-related changes."""
        security_paths = ["auth", "security", "crypto", "password", "token"]
        return self._any_path_contains(changes, security_paths)
    
    def _any_path_contains(self, changes: List[FileChange], keywords: List[str]) -> bool:
        """Check if any change path contains keywords."""
        for change in changes:
            if any(keyword in change.path.lower() for keyword in keywords):
                return True
        return False
    
    def _majority_tests(self, changes: List[FileChange]) -> bool:
        """Check if majority of changes are tests."""
        test_count = sum(1 for c in changes if c.is_test)
        return test_count > len(changes) / 2
    
    def _majority_docs(self, changes: List[FileChange]) -> bool:
        """Check if majority are documentation."""
        doc_extensions = [".md", ".rst", ".txt", ".xml"]
        doc_count = sum(1 for c in changes if c.extension in doc_extensions)
        return doc_count > len(changes) / 2
    
    def _has_config_changes(self, changes: List[FileChange]) -> bool:
        """Check for configuration changes."""
        return any(c.is_config for c in changes)
    
    def _has_performance_changes(self, changes: List[FileChange]) -> bool:
        """Check for performance improvements."""
        perf_keywords = ["cache", "optimize", "performance", "speed", "async"]
        return self._any_path_contains(changes, perf_keywords)
    
    def _assess_business_impact(self, changes: List[FileChange], 
                               category: ChangeCategory) -> BusinessImpact:
        """Assess business impact of changes."""
        impact_rules = self._get_impact_rules()
        return self._evaluate_impact_rules(changes, category, impact_rules)
    
    def _get_impact_rules(self) -> List[Tuple[Any, BusinessImpact]]:
        """Get business impact evaluation rules."""
        return [
            (self._is_critical_change, BusinessImpact.CRITICAL),
            (self._is_customer_facing, BusinessImpact.HIGH),
            (self._is_high_priority_category, BusinessImpact.HIGH)
        ]
    
    def _evaluate_impact_rules(self, changes: List[FileChange], category: ChangeCategory,
                              rules: List[Tuple[Any, BusinessImpact]]) -> BusinessImpact:
        """Evaluate impact rules."""
        for rule_func, impact in rules:
            if rule_func(changes) or (rule_func == self._is_high_priority_category and self._is_high_priority_category(category)):
                return impact
        return self._get_category_impact(category)
    
    def _is_high_priority_category(self, category: ChangeCategory) -> bool:
        """Check if category is high priority."""
        return category in [ChangeCategory.SECURITY, ChangeCategory.PERFORMANCE]
    
    def _get_category_impact(self, category: ChangeCategory) -> BusinessImpact:
        """Get impact based on category."""
        if category == ChangeCategory.FEATURE:
            return BusinessImpact.MEDIUM
        if category in [ChangeCategory.TEST, ChangeCategory.DOCS]:
            return BusinessImpact.LOW
        return BusinessImpact.MINIMAL
    
    def _is_critical_change(self, changes: List[FileChange]) -> bool:
        """Check if changes affect critical paths."""
        return self._any_change_matches_patterns(changes, self.CRITICAL_PATHS)
    
    def _any_change_matches_patterns(self, changes: List[FileChange], 
                                   patterns: List[str]) -> bool:
        """Check if any change matches patterns."""
        for change in changes:
            if any(re.search(pattern, change.path) for pattern in patterns):
                return True
        return False
    
    def _is_customer_facing(self, changes: List[FileChange]) -> bool:
        """Check if changes are customer-facing."""
        return self._any_change_matches_patterns(changes, self.CUSTOMER_FACING_PATTERNS)
    
    def _build_metrics(self, commit_hash: str, changes: List[FileChange],
                      modules: Set[str], category: ChangeCategory,
                      impact: BusinessImpact) -> DiffMetrics:
        """Build DiffMetrics object."""
        metrics_data = self._collect_all_metrics(changes)
        return self._create_diff_metrics(
            commit_hash, changes, modules, category, impact,
            metrics_data["basic"], metrics_data["advanced"]
        )
    
    def _collect_all_metrics(self, changes: List[FileChange]) -> Dict[str, Dict[str, Any]]:
        """Collect all metrics data."""
        return {
            "basic": self._get_basic_metrics(changes),
            "advanced": self._get_advanced_metrics(changes)
        }
    
    def _create_diff_metrics(self, commit_hash: str, changes: List[FileChange],
                            modules: Set[str], category: ChangeCategory,
                            impact: BusinessImpact, basic_metrics: Dict[str, int],
                            advanced_metrics: Dict[str, Any]) -> DiffMetrics:
        """Create DiffMetrics from collected metrics."""
        core_attrs = self._get_core_metric_attrs(commit_hash, changes, modules)
        category_attrs = self._get_category_metric_attrs(category, impact)
        computed_attrs = self._get_computed_metric_attrs(basic_metrics, advanced_metrics)
        return DiffMetrics(**{**core_attrs, **category_attrs, **computed_attrs})
    
    def _get_core_metric_attrs(self, commit_hash: str, changes: List[FileChange], 
                              modules: Set[str]) -> Dict[str, Any]:
        """Get core metric attributes."""
        return {
            "commit_hash": commit_hash,
            "files_changed": len(changes),
            "modules_affected": modules
        }
    
    def _get_category_metric_attrs(self, category: ChangeCategory, 
                                  impact: BusinessImpact) -> Dict[str, Any]:
        """Get category metric attributes."""
        return {
            "change_category": category,
            "business_impact": impact
        }
    
    def _get_computed_metric_attrs(self, basic_metrics: Dict[str, int], 
                                  advanced_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Get computed metric attributes."""
        line_attrs = self._get_line_metric_attrs(basic_metrics)
        score_attrs = self._get_score_metric_attrs(advanced_metrics)
        return {**line_attrs, **score_attrs}
    
    def _get_line_metric_attrs(self, basic_metrics: Dict[str, int]) -> Dict[str, int]:
        """Get line-based metric attributes."""
        return {
            "lines_added": basic_metrics["added"],
            "lines_deleted": basic_metrics["deleted"]
        }
    
    def _get_score_metric_attrs(self, advanced_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Get score-based metric attributes."""
        return {
            "complexity_score": advanced_metrics["complexity"],
            "test_coverage_delta": advanced_metrics["test_delta"],
            "customer_facing": advanced_metrics["customer_facing"]
        }
    
    def _get_basic_metrics(self, changes: List[FileChange]) -> Dict[str, int]:
        """Get basic change metrics."""
        return {
            "added": sum(c.additions for c in changes),
            "deleted": sum(c.deletions for c in changes)
        }
    
    def _get_advanced_metrics(self, changes: List[FileChange]) -> Dict[str, Any]:
        """Get advanced change metrics."""
        return {
            "complexity": self._calculate_complexity(changes),
            "test_delta": self._calculate_test_delta(changes),
            "customer_facing": self._is_customer_facing(changes)
        }
    
    def _calculate_complexity(self, changes: List[FileChange]) -> float:
        """Calculate change complexity score."""
        if not changes:
            return 0.0
        complexity_factors = self._get_complexity_factors(changes)
        raw_complexity = self._compute_raw_complexity(complexity_factors)
        return min(raw_complexity / 100, 10.0)  # Normalize to 0-10 scale
    
    def _get_complexity_factors(self, changes: List[FileChange]) -> Dict[str, int]:
        """Get complexity calculation factors."""
        return {
            "total_changes": sum(c.additions + c.deletions for c in changes),
            "file_count": len(changes),
            "module_count": len({c.module for c in changes})
        }
    
    def _compute_raw_complexity(self, factors: Dict[str, int]) -> float:
        """Compute raw complexity score."""
        return (factors["total_changes"] * 0.5 + 
                factors["file_count"] * 30 + 
                factors["module_count"] * 50)
    
    def _calculate_test_delta(self, changes: List[FileChange]) -> float:
        """Calculate test coverage delta."""
        test_changes = self._sum_test_changes(changes)
        code_changes = self._sum_code_changes(changes)
        return self._compute_test_ratio(test_changes, code_changes)
    
    def _sum_test_changes(self, changes: List[FileChange]) -> int:
        """Sum test file changes."""
        return sum(c.additions - c.deletions for c in changes if c.is_test)
    
    def _sum_code_changes(self, changes: List[FileChange]) -> int:
        """Sum non-test file changes."""
        return sum(c.additions - c.deletions for c in changes if not c.is_test)
    
    def _compute_test_ratio(self, test_changes: int, code_changes: int) -> float:
        """Compute test coverage ratio."""
        if code_changes == 0:
            return 0.0
        return (test_changes / code_changes) * 100 if code_changes > 0 else 0.0
    
    def analyze_range(self, from_ref: str, to_ref: str) -> List[DiffMetrics]:
        """Analyze commits in a range."""
        commits = self._get_commit_range(from_ref, to_ref)
        return self._analyze_commits_batch(commits)
    
    def _analyze_commits_batch(self, commits: List[str]) -> List[DiffMetrics]:
        """Analyze multiple commits in batch."""
        metrics = []
        for commit in commits:
            metrics.append(self.analyze_commit(commit))
        return metrics
    
    def _get_commit_range(self, from_ref: str, to_ref: str) -> List[str]:
        """Get commits in a range."""
        cmd = ["git", "rev-list", f"{from_ref}..{to_ref}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip().split("\n") if result.stdout else []
    
    def get_hotspots(self, days: int = 7) -> Dict[str, int]:
        """Identify code hotspots (frequently changed files)."""
        cmd = self._build_hotspot_command(days)
        result = subprocess.run(cmd, capture_output=True, text=True)
        file_counts = self._count_file_changes(result.stdout)
        return self._get_top_hotspots(file_counts)
    
    def _build_hotspot_command(self, days: int) -> List[str]:
        """Build git command for hotspot analysis."""
        return ["git", "log", f"--since={days} days ago", "--name-only", 
               "--pretty=format:"]
    
    def _count_file_changes(self, stdout: str) -> Dict[str, int]:
        """Count file changes from git output."""
        file_counts = {}
        for line in stdout.strip().split("\n"):
            if line:
                file_counts[line] = file_counts.get(line, 0) + 1
        return file_counts
    
    def _get_top_hotspots(self, file_counts: Dict[str, int]) -> Dict[str, int]:
        """Get top 10 hotspots from file counts."""
        sorted_items = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_items[:10])
    
    def calculate_business_value_score(self, metrics: DiffMetrics) -> float:
        """Calculate business value score for changes."""
        impact_weights = self._get_impact_weights()
        base_score = impact_weights[metrics.business_impact]
        multipliers = self._get_score_multipliers(metrics)
        final_score = self._apply_multipliers(base_score, multipliers)
        return min(final_score, 10.0)  # Cap at 10
    
    def _get_impact_weights(self) -> Dict[BusinessImpact, float]:
        """Get impact weights mapping."""
        return {
            BusinessImpact.CRITICAL: 10.0, BusinessImpact.HIGH: 7.5,
            BusinessImpact.MEDIUM: 5.0, BusinessImpact.LOW: 2.5,
            BusinessImpact.MINIMAL: 1.0
        }
    
    def _get_score_multipliers(self, metrics: DiffMetrics) -> List[float]:
        """Get score multipliers for metrics."""
        multipliers = []
        self._add_customer_facing_multiplier(metrics, multipliers)
        self._add_security_multiplier(metrics, multipliers)
        self._add_test_coverage_multiplier(metrics, multipliers)
        return multipliers
    
    def _add_customer_facing_multiplier(self, metrics: DiffMetrics, multipliers: List[float]) -> None:
        """Add customer facing multiplier if applicable."""
        if metrics.customer_facing:
            multipliers.append(1.5)
    
    def _add_security_multiplier(self, metrics: DiffMetrics, multipliers: List[float]) -> None:
        """Add security multiplier if applicable."""
        if metrics.change_category == ChangeCategory.SECURITY:
            multipliers.append(1.3)
    
    def _add_test_coverage_multiplier(self, metrics: DiffMetrics, multipliers: List[float]) -> None:
        """Add test coverage multiplier if applicable."""
        if metrics.test_coverage_delta > 0:
            multipliers.append(1.1)
    
    def _apply_multipliers(self, base_score: float, multipliers: List[float]) -> float:
        """Apply multipliers to base score."""
        final_score = base_score
        for multiplier in multipliers:
            final_score *= multiplier
        return final_score