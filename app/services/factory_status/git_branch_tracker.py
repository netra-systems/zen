"""Git branch tracker for AI Factory Status Report.

Tracks branch activity, merge patterns, and feature lifecycle.
Module follows 300-line limit with 8-line function limit.
"""

import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class BranchType(Enum):
    """Types of git branches."""
    MAIN = "main"
    DEVELOP = "develop"
    FEATURE = "feature"
    HOTFIX = "hotfix"
    RELEASE = "release"
    BUGFIX = "bugfix"
    EXPERIMENTAL = "experimental"
    UNKNOWN = "unknown"


class BranchStatus(Enum):
    """Status of a branch."""
    ACTIVE = "active"
    MERGED = "merged"
    STALE = "stale"
    DELETED = "deleted"


@dataclass
class BranchInfo:
    """Information about a git branch."""
    name: str
    branch_type: BranchType
    status: BranchStatus
    last_commit_date: datetime
    commit_count: int
    author: str
    is_remote: bool
    ahead_behind: Tuple[int, int]  # (ahead, behind) main
    business_value: str


@dataclass
class MergeInfo:
    """Information about a merge."""
    merge_commit: str
    source_branch: str
    target_branch: str
    merge_date: datetime
    conflicts_resolved: int
    files_changed: int


@dataclass
class BranchMetrics:
    """Aggregated branch metrics."""
    total_branches: int
    active_branches: int
    merged_branches: int
    stale_branches: int
    feature_branches: int
    average_branch_lifetime: float
    merge_frequency: float
    collaboration_score: float


class GitBranchTracker:
    """Tracker for git branch activity and patterns."""
    
    BRANCH_PATTERNS = {
        BranchType.FEATURE: [r"feature/", r"feat/", r"f/"],
        BranchType.HOTFIX: [r"hotfix/", r"hf/"],
        BranchType.RELEASE: [r"release/", r"rel/"],
        BranchType.BUGFIX: [r"bugfix/", r"fix/", r"bf/"],
        BranchType.EXPERIMENTAL: [r"exp/", r"experiment/", r"poc/"],
        BranchType.DEVELOP: [r"develop", r"dev"],
        BranchType.MAIN: [r"main", r"master", r"production"],
    }
    
    STALE_DAYS = 14  # Days before branch is considered stale
    
    def __init__(self, repo_path: str = "."):
        """Initialize branch tracker."""
        self.repo_path = repo_path
        self.main_branch = self._detect_main_branch()
    
    def _detect_main_branch(self) -> str:
        """Detect the main branch name."""
        candidates = ["main", "master", "production"]
        for candidate in candidates:
            if self._branch_exists(candidate):
                return candidate
        return "main"
    
    def _branch_exists(self, branch: str) -> bool:
        """Check if branch exists."""
        cmd = ["git", "rev-parse", "--verify", branch]
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0
    
    def get_all_branches(self) -> List[BranchInfo]:
        """Get information about all branches."""
        local_branches = self._get_local_branches()
        remote_branches = self._get_remote_branches()
        all_branch_names = self._combine_branch_lists(local_branches, remote_branches)
        return self._process_branch_list(all_branch_names)
    
    def _combine_branch_lists(self, local: List[str], remote: List[str]) -> Set[str]:
        """Combine local and remote branch lists."""
        return set(local + remote)
    
    def _process_branch_list(self, branch_names: Set[str]) -> List[BranchInfo]:
        """Process branch names into BranchInfo objects."""
        all_branches = []
        for branch in branch_names:
            info = self._analyze_branch(branch)
            if info:
                all_branches.append(info)
        return all_branches
    
    def _get_local_branches(self) -> List[str]:
        """Get list of local branches."""
        cmd = ["git", "branch", "--format=%(refname:short)"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip().split("\n") if result.stdout else []
    
    def _get_remote_branches(self) -> List[str]:
        """Get list of remote branches."""
        cmd = ["git", "branch", "-r", "--format=%(refname:short)"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        branches = result.stdout.strip().split("\n") if result.stdout else []
        return [b.replace("origin/", "") for b in branches if "HEAD" not in b]
    
    def _analyze_branch(self, branch: str) -> Optional[BranchInfo]:
        """Analyze a single branch."""
        if not branch:
            return None
        branch_data = self._gather_branch_data(branch)
        return self._create_branch_info(branch, branch_data)
    
    def _gather_branch_data(self, branch: str) -> Dict[str, Any]:
        """Gather all data needed for branch analysis."""
        return {
            'branch_type': self._classify_branch(branch),
            'last_commit': self._get_last_commit_date(branch),
            'commit_count': self._count_commits(branch),
            'author': self._get_branch_author(branch),
            'ahead_behind': self._get_ahead_behind(branch)
        }
    
    def _create_branch_info(self, branch: str, data: Dict[str, Any]) -> BranchInfo:
        """Create BranchInfo object from gathered data."""
        status = self._determine_status(branch, data['last_commit'])
        return BranchInfo(
            name=branch, branch_type=data['branch_type'], status=status,
            last_commit_date=data['last_commit'], commit_count=data['commit_count'],
            author=data['author'], is_remote=self._is_remote_branch(branch),
            ahead_behind=data['ahead_behind'],
            business_value=self._assess_business_value(data['branch_type'], status)
        )
    
    def _classify_branch(self, branch: str) -> BranchType:
        """Classify branch type from name."""
        branch_lower = branch.lower()
        for branch_type, patterns in self.BRANCH_PATTERNS.items():
            for pattern in patterns:
                if pattern in branch_lower:
                    return branch_type
        return BranchType.UNKNOWN
    
    def _get_last_commit_date(self, branch: str) -> datetime:
        """Get last commit date for branch."""
        cmd = ["git", "log", "-1", "--format=%at", branch]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            timestamp = int(result.stdout.strip())
            return datetime.fromtimestamp(timestamp)
        return datetime.now()
    
    def _determine_status(self, branch: str, last_commit: datetime) -> BranchStatus:
        """Determine branch status."""
        if self._is_merged(branch):
            return BranchStatus.MERGED
        return self._check_staleness(last_commit)
    
    def _check_staleness(self, last_commit: datetime) -> BranchStatus:
        """Check if branch is stale based on last commit date."""
        days_inactive = (datetime.now() - last_commit).days
        if days_inactive > self.STALE_DAYS:
            return BranchStatus.STALE
        return BranchStatus.ACTIVE
    
    def _is_merged(self, branch: str) -> bool:
        """Check if branch is merged to main."""
        if branch == self.main_branch:
            return False
        cmd = ["git", "branch", "--merged", self.main_branch]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return branch in result.stdout
    
    def _count_commits(self, branch: str) -> int:
        """Count commits in branch."""
        cmd = ["git", "rev-list", "--count", branch]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return int(result.stdout.strip())
        except ValueError:
            return 0
    
    def _get_branch_author(self, branch: str) -> str:
        """Get primary author of branch."""
        cmd = ["git", "log", "--format=%an", branch, "-1"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip() if result.stdout else "unknown"
    
    def _get_ahead_behind(self, branch: str) -> Tuple[int, int]:
        """Get ahead/behind counts relative to main."""
        if branch == self.main_branch:
            return (0, 0)
        return self._calculate_ahead_behind_counts(branch)
    
    def _calculate_ahead_behind_counts(self, branch: str) -> Tuple[int, int]:
        """Calculate actual ahead/behind counts."""
        cmd = ["git", "rev-list", "--left-right", "--count", f"{self.main_branch}...{branch}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return self._parse_ahead_behind_output(result.stdout)
    
    def _parse_ahead_behind_output(self, output: str) -> Tuple[int, int]:
        """Parse ahead/behind output from git."""
        if output:
            parts = output.strip().split("\t")
            if len(parts) == 2:
                return (int(parts[1]), int(parts[0]))
        return (0, 0)
    
    def _is_remote_branch(self, branch: str) -> bool:
        """Check if branch exists on remote."""
        cmd = ["git", "ls-remote", "--heads", "origin", branch]
        result = subprocess.run(cmd, capture_output=True)
        return bool(result.stdout)
    
    def _assess_business_value(self, branch_type: BranchType, status: BranchStatus) -> str:
        """Assess business value of branch."""
        critical_value = self._check_critical_value(branch_type)
        if critical_value:
            return critical_value
        return self._assess_standard_value(branch_type, status)
    
    def _check_critical_value(self, branch_type: BranchType) -> Optional[str]:
        """Check for critical business value types."""
        if branch_type == BranchType.HOTFIX:
            return "Critical - Production fix"
        if branch_type == BranchType.RELEASE:
            return "High - Release preparation"
        return None
    
    def _assess_standard_value(self, branch_type: BranchType, status: BranchStatus) -> str:
        """Assess standard business value."""
        if branch_type == BranchType.FEATURE and status == BranchStatus.ACTIVE:
            return "Medium - Active development"
        if status == BranchStatus.STALE:
            return "Low - Stale/abandoned"
        if status == BranchStatus.MERGED:
            return "Delivered"
        return "Standard"
    
    def get_recent_merges(self, days: int = 7) -> List[MergeInfo]:
        """Get recent merge information."""
        merge_lines = self._fetch_merge_log(days)
        return self._process_merge_lines(merge_lines)
    
    def _fetch_merge_log(self, days: int) -> List[str]:
        """Fetch merge log entries for specified days."""
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cmd = ["git", "log", "--merges", f"--since={since_date}", "--format=%H|%at|%s"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip().split("\n") if result.stdout else []
    
    def _process_merge_lines(self, lines: List[str]) -> List[MergeInfo]:
        """Process merge log lines into MergeInfo objects."""
        merges = []
        for line in lines:
            if line:
                merge = self._parse_merge(line)
                if merge:
                    merges.append(merge)
        return merges
    
    def _parse_merge(self, line: str) -> Optional[MergeInfo]:
        """Parse merge commit information."""
        parts = line.split("|")
        if len(parts) < 3:
            return None
        return self._create_merge_info(parts)
    
    def _create_merge_info(self, parts: List[str]) -> MergeInfo:
        """Create MergeInfo from parsed parts."""
        commit_hash, timestamp, message = parts[0], int(parts[1]), parts[2]
        source, target = self._extract_branch_names(message)
        return MergeInfo(
            merge_commit=commit_hash, source_branch=source, target_branch=target,
            merge_date=datetime.fromtimestamp(timestamp), conflicts_resolved=0,
            files_changed=self._count_merge_files(commit_hash)
        )
    
    def _extract_branch_names(self, message: str) -> Tuple[str, str]:
        """Extract source and target branch names from merge message."""
        import re
        match = re.search(r"Merge.* '(.+)' into '(.+)'", message)
        if not match:
            match = re.search(r"Merge branch '(.+)'", message)
        source = match.group(1) if match else "unknown"
        target = match.group(2) if match and match.lastindex > 1 else self.main_branch
        return source, target
    
    def _count_merge_files(self, commit: str) -> int:
        """Count files changed in merge."""
        cmd = ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return len(result.stdout.strip().split("\n")) if result.stdout else 0
    
    def calculate_metrics(self) -> BranchMetrics:
        """Calculate aggregated branch metrics."""
        branches = self.get_all_branches()
        counts = self._calculate_branch_counts(branches)
        advanced_metrics = self._calculate_advanced_metrics(branches)
        return self._create_branch_metrics(branches, counts, advanced_metrics)
    
    def _calculate_branch_counts(self, branches: List[BranchInfo]) -> Dict[str, int]:
        """Calculate basic branch counts."""
        return {
            'active': sum(1 for b in branches if b.status == BranchStatus.ACTIVE),
            'merged': sum(1 for b in branches if b.status == BranchStatus.MERGED),
            'stale': sum(1 for b in branches if b.status == BranchStatus.STALE),
            'features': sum(1 for b in branches if b.branch_type == BranchType.FEATURE)
        }
    
    def _calculate_advanced_metrics(self, branches: List[BranchInfo]) -> Dict[str, float]:
        """Calculate advanced metrics."""
        return {
            'avg_lifetime': self._calculate_avg_lifetime(branches),
            'merge_freq': self._calculate_merge_frequency(),
            'collab_score': self._calculate_collaboration_score(branches)
        }
    
    def _create_branch_metrics(self, branches: List[BranchInfo], counts: Dict[str, int], 
                              metrics: Dict[str, float]) -> BranchMetrics:
        """Create BranchMetrics object from calculated data."""
        return BranchMetrics(
            total_branches=len(branches), active_branches=counts['active'],
            merged_branches=counts['merged'], stale_branches=counts['stale'],
            feature_branches=counts['features'], average_branch_lifetime=metrics['avg_lifetime'],
            merge_frequency=metrics['merge_freq'], collaboration_score=metrics['collab_score']
        )
    
    def _calculate_avg_lifetime(self, branches: List[BranchInfo]) -> float:
        """Calculate average branch lifetime in days."""
        lifetimes = []
        for branch in branches:
            if branch.status == BranchStatus.MERGED:
                lifetime = (datetime.now() - branch.last_commit_date).days
                lifetimes.append(lifetime)
        
        return sum(lifetimes) / len(lifetimes) if lifetimes else 0.0
    
    def _calculate_merge_frequency(self) -> float:
        """Calculate merges per day over last 30 days."""
        merges = self.get_recent_merges(30)
        return len(merges) / 30.0
    
    def _calculate_collaboration_score(self, branches: List[BranchInfo]) -> float:
        """Calculate collaboration score based on branch patterns."""
        if not branches:
            return 0.0
        
        unique_authors = len(set(b.author for b in branches))
        active_features = sum(1 for b in branches 
                            if b.branch_type == BranchType.FEATURE 
                            and b.status == BranchStatus.ACTIVE)
        
        score = (unique_authors * 2 + active_features) / len(branches)
        return min(score * 10, 10.0)  # Normalize to 0-10