"""Git Changes Analyzer - Analyzes git commits and generates summaries."""

import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import re
import json


class GitAnalyzer:
    """Analyzes git repository changes."""
    
    def __init__(self, project_root: Path):
        """Initialize with project root."""
        self.project_root = project_root
        self.feature_pattern = re.compile(r'feat|feature|add|new', re.I)
        self.bug_pattern = re.compile(r'fix|bug|patch|resolve', re.I)
        self.refactor_pattern = re.compile(r'refactor|clean|optimize', re.I)
    
    async def analyze(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Analyze git commits in time range."""
        commits = await self.get_commits(start, end)
        summary = self.summarize_commits(commits)
        authors = self.identify_authors(commits)
        
        return {
            "commits": commits,
            "commit_summary": summary,
            "contributors": authors,
            "total_commits": len(commits)
        }
    
    async def get_commits(self, start: datetime, end: datetime) -> List[Dict]:
        """Fetch commits for time range."""
        since = start.strftime("%Y-%m-%d %H:%M:%S")
        until = end.strftime("%Y-%m-%d %H:%M:%S")
        
        cmd = [
            "git", "log", f"--since={since}", f"--until={until}",
            "--pretty=format:%H|%an|%ae|%ad|%s", "--date=iso"
        ]
        result = await self._run_git_command(cmd)
        return self._parse_commit_log(result)
    
    def summarize_commits(self, commits: List[Dict]) -> Dict[str, Any]:
        """Create human-readable commit summary."""
        features = [c for c in commits if self.feature_pattern.search(c["message"])]
        bugs = [c for c in commits if self.bug_pattern.search(c["message"])]
        refactors = [c for c in commits if self.refactor_pattern.search(c["message"])]
        
        return {
            "features": self._extract_feature_descriptions(features),
            "bugs": self._extract_bug_descriptions(bugs),
            "refactors": len(refactors),
            "other": len(commits) - len(features) - len(bugs) - len(refactors)
        }
    
    def identify_authors(self, commits: List[Dict]) -> List[Dict]:
        """List contributors and their changes."""
        author_stats = {}
        for commit in commits:
            author = commit["author"]
            if author not in author_stats:
                author_stats[author] = {"commits": 0, "features": 0, "bugs": 0}
            author_stats[author]["commits"] += 1
            if self.feature_pattern.search(commit["message"]):
                author_stats[author]["features"] += 1
            if self.bug_pattern.search(commit["message"]):
                author_stats[author]["bugs"] += 1
        
        return self._format_author_stats(author_stats)
    
    async def _run_git_command(self, cmd: List[str]) -> str:
        """Execute git command and return output."""
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=self.project_root,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode() if proc.returncode == 0 else ""
    
    def _parse_commit_log(self, log: str) -> List[Dict]:
        """Parse git log output into structured data."""
        commits = []
        for line in log.strip().split('\n'):
            if not line: continue
            parts = line.split('|')
            if len(parts) >= 5:
                commits.append({
                    "hash": parts[0][:8],
                    "author": parts[1],
                    "email": parts[2],
                    "date": parts[3],
                    "message": parts[4]
                })
        return commits
    
    def _extract_feature_descriptions(self, features: List[Dict]) -> List[Dict]:
        """Extract clean feature descriptions."""
        descriptions = []
        for feat in features[:10]:  # Limit to top 10
            msg = feat["message"]
            clean_msg = re.sub(r'^(feat|feature)[:\(\)]?\s*', '', msg, flags=re.I)
            descriptions.append({
                "title": clean_msg[:50],
                "author": feat["author"],
                "hash": feat["hash"]
            })
        return descriptions
    
    def _extract_bug_descriptions(self, bugs: List[Dict]) -> List[Dict]:
        """Extract clean bug fix descriptions."""
        descriptions = []
        for bug in bugs[:10]:  # Limit to top 10
            msg = bug["message"]
            clean_msg = re.sub(r'^(fix|bug)[:\(\)]?\s*', '', msg, flags=re.I)
            descriptions.append({
                "title": clean_msg[:50],
                "author": bug["author"],
                "hash": bug["hash"]
            })
        return descriptions
    
    def _format_author_stats(self, stats: Dict) -> List[Dict]:
        """Format author statistics for output."""
        formatted = []
        for author, data in stats.items():
            formatted.append({
                "name": author,
                "commits": data["commits"],
                "features": data["features"],
                "bugs": data["bugs"]
            })
        return sorted(formatted, key=lambda x: x["commits"], reverse=True)