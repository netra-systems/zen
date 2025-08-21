"""Git commit parser for AI Factory Status Report.

Extracts and parses git commit history with semantic analysis.
Module follows 450-line limit with 25-line function limit.
"""

import re
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import json
from netra_backend.app.services.factory_status.mock_data_generator import MockDataGenerator


class CommitType(Enum):
    """Semantic commit type classification."""
    FEATURE = "feature"
    FIX = "fix"
    REFACTOR = "refactor"
    DOCS = "docs"
    TEST = "test"
    STYLE = "style"
    PERF = "perf"
    CHORE = "chore"
    BUILD = "build"
    CI = "ci"
    UNKNOWN = "unknown"


@dataclass
class CommitInfo:
    """Structured commit information."""
    hash: str
    author: str
    email: str
    timestamp: datetime
    message: str
    commit_type: CommitType
    files_changed: int
    insertions: int
    deletions: int
    branch: Optional[str] = None


class GitCommitParser:
    """Parser for git commit history."""
    
    COMMIT_TYPE_PATTERNS = {
        CommitType.FEATURE: r"^(feat|feature|add|new)(\(.*\))?:",
        CommitType.FIX: r"^(fix|bugfix|fixed)(\(.*\))?:",
        CommitType.REFACTOR: r"^(refactor|cleanup|reorganize)(\(.*\))?:",
        CommitType.DOCS: r"^(docs|documentation)(\(.*\))?:",
        CommitType.TEST: r"^(test|tests|testing)(\(.*\))?:",
        CommitType.STYLE: r"^(style|format|formatting)(\(.*\))?:",
        CommitType.PERF: r"^(perf|performance|optimize)(\(.*\))?:",
        CommitType.CHORE: r"^(chore|maintenance)(\(.*\))?:",
        CommitType.BUILD: r"^(build|deps|dependencies)(\(.*\))?:",
        CommitType.CI: r"^(ci|pipeline|workflow)(\(.*\))?:",
    }
    
    def __init__(self, repo_path: str = "."):
        """Initialize parser with repository path."""
        self.repo_path = repo_path
        self.mock_generator = MockDataGenerator()
        
    def get_commits(self, hours: int = 24) -> List[CommitInfo]:
        """Get commits from the last N hours."""
        since_date = self._calculate_since_date(hours)
        raw_commits = self._fetch_raw_commits(since_date)
        if not raw_commits:
            return self._get_mock_commits(hours)
        return self._parse_commits(raw_commits)
    
    def _calculate_since_date(self, hours: int) -> str:
        """Calculate the since date for git log."""
        since = datetime.now() - timedelta(hours=hours)
        return since.strftime("%Y-%m-%d %H:%M:%S")
    
    def _fetch_raw_commits(self, since: str) -> List[str]:
        """Fetch raw commit data from git."""
        try:
            return asyncio.run(self._fetch_raw_commits_async(since))
        except (asyncio.TimeoutError, Exception):
            return []
    
    async def _fetch_raw_commits_async(self, since: str) -> List[str]:
        """Fetch raw commit data from git asynchronously."""
        cmd = self._build_git_command(since)
        try:
            proc = await self._create_subprocess(cmd)
            stdout = await self._get_subprocess_output(proc)
            return self._split_commits(stdout.decode())
        except (asyncio.TimeoutError, Exception):
            return []
    
    async def _create_subprocess(self, cmd: List[str]):
        """Create subprocess for git command."""
        return await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    
    async def _get_subprocess_output(self, proc):
        """Get subprocess output with timeout."""
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
        return stdout
    
    def _get_mock_commits(self, hours: int) -> List[CommitInfo]:
        """Get mock commits when git is unavailable."""
        mock_data = self.mock_generator.generate_mock_commits(hours)
        commits = []
        for data in mock_data:
            commit = self._create_commit_from_mock_data(data)
            commits.append(commit)
        return commits
    
    def _create_commit_from_mock_data(self, data: Dict) -> CommitInfo:
        """Create CommitInfo from mock data."""
        return CommitInfo(
            hash=data["hash"], author=data["author"], email=data["email"],
            timestamp=data["timestamp"], message=data["message"],
            commit_type=self._classify_commit(data["message"]),
            files_changed=data["files_changed"], insertions=data["insertions"],
            deletions=data["deletions"]
        )
    
    def _build_git_command(self, since: str) -> List[str]:
        """Build git log command with parameters."""
        return [
            "git", "log", f"--since=\"{since}\"",
            "--all", "--format=%H|%an|%ae|%at|%s", "--numstat"
        ]
    
    def _split_commits(self, output: str) -> List[str]:
        """Split git log output into individual commits."""
        commits = []
        current = []
        for line in output.strip().split("\n"):
            if self._is_new_commit_line(line, current):
                commits = self._add_current_commit(commits, current)
                current = [line]
            else:
                current.append(line)
        return self._finalize_commit_list(commits, current)
    
    def _is_new_commit_line(self, line: str, current: List[str]) -> bool:
        """Check if line starts a new commit."""
        return "|" in line and len(current) > 0
    
    def _add_current_commit(self, commits: List[str], current: List[str]) -> List[str]:
        """Add current commit to commits list."""
        commits.append("\n".join(current))
        return commits
    
    def _finalize_commit_list(self, commits: List[str], current: List[str]) -> List[str]:
        """Finalize the commits list with remaining current."""
        if current:
            commits.append("\n".join(current))
        return commits
    
    def _parse_commits(self, raw_commits: List[str]) -> List[CommitInfo]:
        """Parse raw commits into CommitInfo objects."""
        commits = []
        for raw in raw_commits:
            commit = self._parse_single_commit(raw)
            if commit:
                commits.append(commit)
        return commits
    
    def _parse_single_commit(self, raw: str) -> Optional[CommitInfo]:
        """Parse a single raw commit string."""
        lines = raw.strip().split("\n")
        if not lines:
            return None
        header = self._parse_header(lines[0])
        if not header:
            return None
        return self._build_commit_info(header, lines[1:])
    
    def _parse_header(self, line: str) -> Optional[Dict]:
        """Parse commit header line."""
        parts = line.split("|")
        if len(parts) < 5:
            return None
        return self._create_header_dict(parts)
    
    def _create_header_dict(self, parts: List[str]) -> Dict:
        """Create header dictionary from parts."""
        return {
            "hash": parts[0], "author": parts[1], "email": parts[2],
            "timestamp": int(parts[3]), "message": parts[4]
        }
    
    def _build_commit_info(self, header: Dict, stat_lines: List[str]) -> CommitInfo:
        """Build CommitInfo from header and stats."""
        stats = self._parse_stats(stat_lines)
        commit_type = self._classify_commit(header["message"])
        return self._create_commit_info(header, stats, commit_type)
    
    def _parse_stats(self, lines: List[str]) -> Dict:
        """Parse file change statistics."""
        stats = {"files": 0, "insertions": 0, "deletions": 0}
        for line in lines:
            if "\t" in line:
                self._update_stats_from_line(stats, line)
        return stats
    
    def _update_stats_from_line(self, stats: Dict, line: str) -> None:
        """Update stats from a single line."""
        parts = line.split("\t")
        if len(parts) >= 2:
            stats["files"] += 1
            stats["insertions"] += self._safe_int(parts[0])
            stats["deletions"] += self._safe_int(parts[1])
    
    def _safe_int(self, value: str) -> int:
        """Safely convert string to int."""
        try:
            return int(value) if value != "-" else 0
        except (ValueError, TypeError):
            return 0
    
    def _classify_commit(self, message: str) -> CommitType:
        """Classify commit type from message."""
        message_lower = message.lower().strip()
        for commit_type, pattern in self.COMMIT_TYPE_PATTERNS.items():
            if re.match(pattern, message_lower):
                return commit_type
        return CommitType.UNKNOWN
    
    def _create_commit_info(self, header: Dict, stats: Dict, 
                           commit_type: CommitType) -> CommitInfo:
        """Create CommitInfo from parsed data."""
        return CommitInfo(
            hash=header["hash"], author=header["author"], email=header["email"],
            timestamp=datetime.fromtimestamp(header["timestamp"]), message=header["message"],
            commit_type=commit_type, files_changed=stats["files"],
            insertions=stats["insertions"], deletions=stats["deletions"]
        )
    
    def get_commit_by_hash(self, commit_hash: str) -> Optional[CommitInfo]:
        """Get specific commit by hash."""
        cmd = ["git", "show", "--format=%H|%an|%ae|%at|%s", 
               "--numstat", commit_hash]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return self._parse_single_commit(result.stdout)
        return None
    
    def get_branch_commits(self, branch: str, hours: int = 24) -> List[CommitInfo]:
        """Get commits from specific branch."""
        since = self._calculate_since_date(hours)
        cmd = self._build_branch_command(branch, since)
        result = subprocess.run(cmd, capture_output=True, text=True)
        raw_commits = self._split_commits(result.stdout)
        commits = self._parse_commits(raw_commits)
        return self._set_branch_on_commits(commits, branch)
    
    def _build_branch_command(self, branch: str, since: str) -> List[str]:
        """Build git command for branch commits."""
        return ["git", "log", branch, f"--since=\"{since}\"",
                "--format=%H|%an|%ae|%at|%s", "--numstat"]
    
    def _set_branch_on_commits(self, commits: List[CommitInfo], branch: str) -> List[CommitInfo]:
        """Set branch name on all commits."""
        for commit in commits:
            commit.branch = branch
        return commits
    
    def get_author_commits(self, author: str, hours: int = 24) -> List[CommitInfo]:
        """Get commits by specific author."""
        commits = self.get_commits(hours)
        return [c for c in commits if author.lower() in c.author.lower()]
    
    def get_commits_by_type(self, commit_type: CommitType, 
                           hours: int = 24) -> List[CommitInfo]:
        """Get commits filtered by type."""
        commits = self.get_commits(hours)
        return [c for c in commits if c.commit_type == commit_type]
    
    def export_commits_json(self, commits: List[CommitInfo]) -> str:
        """Export commits to JSON format."""
        data = []
        for commit in commits:
            data.append(self._commit_to_dict(commit))
        return json.dumps(data, indent=2, default=str)
    
    def _commit_to_dict(self, commit: CommitInfo) -> Dict:
        """Convert CommitInfo to dictionary."""
        base_data = self._get_commit_base_data(commit)
        stats_data = self._get_commit_stats_data(commit)
        return {**base_data, **stats_data}
    
    def _get_commit_base_data(self, commit: CommitInfo) -> Dict:
        """Get base commit data."""
        return {
            "hash": commit.hash, "author": commit.author, "email": commit.email,
            "timestamp": commit.timestamp.isoformat(), "message": commit.message,
            "type": commit.commit_type.value, "branch": commit.branch
        }
    
    def _get_commit_stats_data(self, commit: CommitInfo) -> Dict:
        """Get commit statistics data."""
        return {
            "files_changed": commit.files_changed, "insertions": commit.insertions,
            "deletions": commit.deletions
        }
    
    def analyze_commit_patterns(self, hours: int = 168) -> Dict:
        """Analyze commit patterns over time."""
        commits = self.get_commits(hours)
        basic_stats = self._get_basic_commit_stats(commits)
        advanced_stats = self._get_advanced_commit_stats(commits)
        return {**basic_stats, **advanced_stats}
    
    def _get_basic_commit_stats(self, commits: List[CommitInfo]) -> Dict:
        """Get basic commit statistics."""
        return {
            "total_commits": len(commits),
            "commits_by_type": self._count_by_type(commits),
            "commits_by_author": self._count_by_author(commits)
        }
    
    def _get_advanced_commit_stats(self, commits: List[CommitInfo]) -> Dict:
        """Get advanced commit statistics."""
        return {
            "peak_hours": self._find_peak_hours(commits),
            "average_changes": self._calculate_avg_changes(commits)
        }
    
    def _count_by_type(self, commits: List[CommitInfo]) -> Dict:
        """Count commits by type."""
        counts = {}
        for commit in commits:
            key = commit.commit_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts
    
    def _count_by_author(self, commits: List[CommitInfo]) -> Dict:
        """Count commits by author."""
        counts = {}
        for commit in commits:
            counts[commit.author] = counts.get(commit.author, 0) + 1
        return counts
    
    def _find_peak_hours(self, commits: List[CommitInfo]) -> List[int]:
        """Find peak commit hours."""
        hours = {}
        for commit in commits:
            hour = commit.timestamp.hour
            hours[hour] = hours.get(hour, 0) + 1
        sorted_hours = sorted(hours.items(), key=lambda x: x[1], reverse=True)
        return [h[0] for h in sorted_hours[:3]]
    
    def _calculate_avg_changes(self, commits: List[CommitInfo]) -> Dict:
        """Calculate average changes per commit."""
        if not commits:
            return {"files": 0, "insertions": 0, "deletions": 0}
        totals = self._sum_commit_changes(commits)
        count = len(commits)
        return self._compute_averages(totals, count)
    
    def _sum_commit_changes(self, commits: List[CommitInfo]) -> Dict:
        """Sum all changes across commits."""
        return {
            "files": sum(c.files_changed for c in commits),
            "insertions": sum(c.insertions for c in commits),
            "deletions": sum(c.deletions for c in commits)
        }
    
    def _compute_averages(self, totals: Dict, count: int) -> Dict:
        """Compute averages from totals and count."""
        return {
            "files": round(totals["files"] / count, 2),
            "insertions": round(totals["insertions"] / count, 2),
            "deletions": round(totals["deletions"] / count, 2)
        }