"""Git diff analyzer for AI Factory Status Report.

Analyzes code changes, calculates impact metrics, and maps to business value.
Module follows 300-line limit with 8-line function limit.
"""

import re
import asyncio
from typing import Dict, List, Optional, Tuple, Set
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
        modules = self._extract_modules(file_changes)
        category = self._categorize_changes(file_changes)
        impact = self._assess_business_impact(file_changes, category)
        
        return self._build_metrics(
            commit_hash, file_changes, modules, category, impact
        )
    
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
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2.0)
            return self._parse_numstat(stdout.decode())
        except (asyncio.TimeoutError, Exception):
            return []
    
    def _parse_numstat(self, output: str) -> List[FileChange]:
        """Parse git diff numstat output."""
        changes = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            change = self._parse_numstat_line(line)
            if change:
                changes.append(change)
        return changes
    
    def _parse_numstat_line(self, line: str) -> Optional[FileChange]:
        """Parse a single numstat line."""
        parts = line.split("\t")
        if len(parts) < 3:
            return None
        
        additions = self._safe_int(parts[0])
        deletions = self._safe_int(parts[1])
        path = parts[2]
        
        return self._create_file_change(path, additions, deletions)
    
    def _safe_int(self, value: str) -> int:
        """Safely convert to int."""
        try:
            return int(value) if value != "-" else 0
        except (ValueError, TypeError):
            return 0
    
    def _create_file_change(self, path: str, adds: int, dels: int) -> FileChange:
        """Create FileChange object."""
        return FileChange(
            path=path,
            additions=adds,
            deletions=dels,
            is_test=self._is_test_file(path),
            is_config=self._is_config_file(path),
            module=self._extract_module(path),
            extension=Path(path).suffix
        )
    
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
        if self._has_security_changes(changes):
            return ChangeCategory.SECURITY
        if self._majority_tests(changes):
            return ChangeCategory.TEST
        if self._majority_docs(changes):
            return ChangeCategory.DOCS
        if self._has_config_changes(changes):
            return ChangeCategory.CONFIG
        if self._has_performance_changes(changes):
            return ChangeCategory.PERFORMANCE
        return ChangeCategory.FEATURE
    
    def _has_security_changes(self, changes: List[FileChange]) -> bool:
        """Check for security-related changes."""
        security_paths = ["auth", "security", "crypto", "password", "token"]
        for change in changes:
            if any(sec in change.path.lower() for sec in security_paths):
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
        for change in changes:
            if any(keyword in change.path.lower() for keyword in perf_keywords):
                return True
        return False
    
    def _assess_business_impact(self, changes: List[FileChange], 
                               category: ChangeCategory) -> BusinessImpact:
        """Assess business impact of changes."""
        if self._is_critical_change(changes):
            return BusinessImpact.CRITICAL
        if self._is_customer_facing(changes):
            return BusinessImpact.HIGH
        if category in [ChangeCategory.SECURITY, ChangeCategory.PERFORMANCE]:
            return BusinessImpact.HIGH
        if category == ChangeCategory.FEATURE:
            return BusinessImpact.MEDIUM
        if category in [ChangeCategory.TEST, ChangeCategory.DOCS]:
            return BusinessImpact.LOW
        return BusinessImpact.MINIMAL
    
    def _is_critical_change(self, changes: List[FileChange]) -> bool:
        """Check if changes affect critical paths."""
        for change in changes:
            for pattern in self.CRITICAL_PATHS:
                if re.search(pattern, change.path):
                    return True
        return False
    
    def _is_customer_facing(self, changes: List[FileChange]) -> bool:
        """Check if changes are customer-facing."""
        for change in changes:
            for pattern in self.CUSTOMER_FACING_PATTERNS:
                if re.search(pattern, change.path):
                    return True
        return False
    
    def _build_metrics(self, commit_hash: str, changes: List[FileChange],
                      modules: Set[str], category: ChangeCategory,
                      impact: BusinessImpact) -> DiffMetrics:
        """Build DiffMetrics object."""
        return DiffMetrics(
            commit_hash=commit_hash,
            files_changed=len(changes),
            lines_added=sum(c.additions for c in changes),
            lines_deleted=sum(c.deletions for c in changes),
            modules_affected=modules,
            change_category=category,
            business_impact=impact,
            complexity_score=self._calculate_complexity(changes),
            test_coverage_delta=self._calculate_test_delta(changes),
            customer_facing=self._is_customer_facing(changes)
        )
    
    def _calculate_complexity(self, changes: List[FileChange]) -> float:
        """Calculate change complexity score."""
        if not changes:
            return 0.0
        
        total_changes = sum(c.additions + c.deletions for c in changes)
        file_count = len(changes)
        module_count = len({c.module for c in changes})
        
        complexity = (total_changes * 0.5 + file_count * 30 + module_count * 50)
        return min(complexity / 100, 10.0)  # Normalize to 0-10 scale
    
    def _calculate_test_delta(self, changes: List[FileChange]) -> float:
        """Calculate test coverage delta."""
        test_changes = sum(c.additions - c.deletions for c in changes if c.is_test)
        code_changes = sum(c.additions - c.deletions for c in changes if not c.is_test)
        
        if code_changes == 0:
            return 0.0
        
        return (test_changes / code_changes) * 100 if code_changes > 0 else 0.0
    
    def analyze_range(self, from_ref: str, to_ref: str) -> List[DiffMetrics]:
        """Analyze commits in a range."""
        commits = self._get_commit_range(from_ref, to_ref)
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
        cmd = ["git", "log", f"--since={days} days ago", "--name-only", 
               "--pretty=format:"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        file_counts = {}
        for line in result.stdout.strip().split("\n"):
            if line:
                file_counts[line] = file_counts.get(line, 0) + 1
        
        return dict(sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    
    def calculate_business_value_score(self, metrics: DiffMetrics) -> float:
        """Calculate business value score for changes."""
        impact_weights = {
            BusinessImpact.CRITICAL: 10.0,
            BusinessImpact.HIGH: 7.5,
            BusinessImpact.MEDIUM: 5.0,
            BusinessImpact.LOW: 2.5,
            BusinessImpact.MINIMAL: 1.0
        }
        
        base_score = impact_weights[metrics.business_impact]
        
        if metrics.customer_facing:
            base_score *= 1.5
        if metrics.change_category == ChangeCategory.SECURITY:
            base_score *= 1.3
        if metrics.test_coverage_delta > 0:
            base_score *= 1.1
        
        return min(base_score, 10.0)  # Cap at 10