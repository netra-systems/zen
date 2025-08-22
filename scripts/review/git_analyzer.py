#!/usr/bin/env python3
"""
Git analysis functionality for code review system.
Analyzes recent git changes for potential issues and hotspots.
"""

from typing import List

from .command_runner import CommandRunner
from .core import ReviewConfig, ReviewData


class GitAnalyzer:
    """Analyzes git history and changes for review insights"""
    
    def __init__(self, config: ReviewConfig, command_runner: CommandRunner):
        self.config = config
        self.runner = command_runner
    
    def analyze_recent_changes(self, review_data: ReviewData) -> None:
        """Analyze recent git changes for potential issues"""
        print("\n[GIT] Analyzing Recent Changes...")
        self._analyze_recent_commits(review_data)
        self._find_change_hotspots(review_data)
        self._check_large_changes(review_data)
        self._check_unstaged_changes(review_data)
    
    def _analyze_recent_commits(self, review_data: ReviewData) -> None:
        """Get and analyze recent commits"""
        success, output = self.runner.run(f"git log --oneline -n {self.config.recent_commits}")
        if success:
            commits = output.strip().split('\n')
            review_data.add_recent_changes(commits[:10])
            print(f"  Found {len(commits)} recent commits")
    
    def _find_change_hotspots(self, review_data: ReviewData) -> None:
        """Find files with frequent changes (potential bug hotspots)"""
        cmd = "git log --pretty=format: --name-only | sort | uniq -c | sort -rg | head -20"
        success, output = self.runner.run(cmd)
        if success:
            hotspots = self._parse_hotspots(output)
            self._report_hotspots(hotspots, review_data)
    
    def _parse_hotspots(self, output: str) -> List[str]:
        """Parse hotspot files from git output"""
        hotspots = []
        for line in output.strip().split('\n'):
            if line.strip():
                parts = line.strip().split(None, 1)
                if len(parts) == 2:
                    count, file = parts
                    if int(count) > 5:
                        hotspots.append(file)
        return hotspots
    
    def _report_hotspots(self, hotspots: List[str], review_data: ReviewData) -> None:
        """Report identified hotspots"""
        if hotspots:
            print(f"  [WARN] Found {len(hotspots)} frequently changed files (potential bug hotspots)")
            for file in hotspots[:5]:
                review_data.issue_tracker.add_issue("medium", f"High-churn file (bug-prone): {file}")
    
    def _check_large_changes(self, review_data: ReviewData) -> None:
        """Check for large recent changes"""
        success, output = self.runner.run("git diff --stat HEAD~5..HEAD")
        if success:
            self._analyze_change_sizes(output, review_data)
    
    def _analyze_change_sizes(self, output: str, review_data: ReviewData) -> None:
        """Analyze the size of recent changes"""
        lines = output.strip().split('\n')
        for line in lines:
            if '|' in line and '+' in line:
                parts = line.split('|')
                if len(parts) == 2:
                    file = parts[0].strip()
                    changes = parts[1].strip()
                    plus_count = changes.count('+')
                    if plus_count > 50:
                        review_data.issue_tracker.add_issue("high", f"Large recent changes in: {file}")
    
    def _check_unstaged_changes(self, review_data: ReviewData) -> None:
        """Check for unstaged changes"""
        success, output = self.runner.run("git status --short")
        if success and output.strip():
            unstaged_files = output.strip().split('\n')
            file_count = len(unstaged_files)
            if file_count > 0:
                print(f"  [WARN] Found {file_count} files with unstaged changes")
                if file_count > 10:
                    review_data.issue_tracker.add_issue("medium", f"Many unstaged changes ({file_count} files)")