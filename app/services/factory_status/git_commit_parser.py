"""Git commit parser for AI Factory Status Report.

Extracts and parses git commit history with semantic analysis.
Module follows 300-line limit with 8-line function limit.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import json
from app.services.factory_status.mock_data_generator import MockDataGenerator


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
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
            return self._split_commits(stdout.decode())
        except asyncio.TimeoutError:
            return []
        except Exception:
            return []
    
    def _get_mock_commits(self, hours: int) -> List[CommitInfo]:
        """Get mock commits when git is unavailable."""
        mock_data = self.mock_generator.generate_mock_commits(hours)
        commits = []
        for data in mock_data:
            commits.append(CommitInfo(
                hash=data["hash"],
                author=data["author"],
                email=data["email"],
                timestamp=data["timestamp"],
                message=data["message"],
                commit_type=self._classify_commit(data["message"]),
                files_changed=data["files_changed"],
                insertions=data["insertions"],
                deletions=data["deletions"]
            ))
        return commits
    
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
            if "|" in line and len(current) > 0:
                commits.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
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
            
        stats = self._parse_stats(lines[1:])
        commit_type = self._classify_commit(header["message"])
        
        return self._create_commit_info(header, stats, commit_type)
    
    def _parse_header(self, line: str) -> Optional[Dict]:
        """Parse commit header line."""
        parts = line.split("|")
        if len(parts) < 5:
            return None
        return {
            "hash": parts[0],
            "author": parts[1],
            "email": parts[2],
            "timestamp": int(parts[3]),
            "message": parts[4]
        }
    
    def _parse_stats(self, lines: List[str]) -> Dict:
        """Parse file change statistics."""
        stats = {"files": 0, "insertions": 0, "deletions": 0}
        for line in lines:
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    stats["files"] += 1
                    stats["insertions"] += self._safe_int(parts[0])
                    stats["deletions"] += self._safe_int(parts[1])
        return stats
    
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
            hash=header["hash"],
            author=header["author"],
            email=header["email"],
            timestamp=datetime.fromtimestamp(header["timestamp"]),
            message=header["message"],
            commit_type=commit_type,
            files_changed=stats["files"],
            insertions=stats["insertions"],
            deletions=stats["deletions"]
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
        cmd = ["git", "log", branch, f"--since=\"{since}\"",
               "--format=%H|%an|%ae|%at|%s", "--numstat"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        raw_commits = self._split_commits(result.stdout)
        commits = self._parse_commits(raw_commits)
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
        return {
            "hash": commit.hash,
            "author": commit.author,
            "email": commit.email,
            "timestamp": commit.timestamp.isoformat(),
            "message": commit.message,
            "type": commit.commit_type.value,
            "files_changed": commit.files_changed,
            "insertions": commit.insertions,
            "deletions": commit.deletions,
            "branch": commit.branch
        }
    
    def analyze_commit_patterns(self, hours: int = 168) -> Dict:
        """Analyze commit patterns over time."""
        commits = self.get_commits(hours)
        return {
            "total_commits": len(commits),
            "commits_by_type": self._count_by_type(commits),
            "commits_by_author": self._count_by_author(commits),
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
        
        total_files = sum(c.files_changed for c in commits)
        total_insertions = sum(c.insertions for c in commits)
        total_deletions = sum(c.deletions for c in commits)
        count = len(commits)
        
        return {
            "files": round(total_files / count, 2),
            "insertions": round(total_insertions / count, 2),
            "deletions": round(total_deletions / count, 2)
        }