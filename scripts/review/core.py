#!/usr/bin/env python3
"""
Core data structures and types for code review system.
Implements foundational classes and issue tracking.
"""

from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime


class ReviewIssue:
    """Represents a single review issue"""
    
    def __init__(self, severity: str, description: str, category: str = "general"):
        self.severity = severity  # critical, high, medium, low
        self.description = description
        self.category = category
        self.timestamp = datetime.now()
    
    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.description}"


class IssueTracker:
    """Tracks and organizes review issues by severity"""
    
    def __init__(self):
        self.issues = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
    
    def add_issue(self, severity: str, description: str, category: str = "general") -> None:
        """Add a new issue to the tracker"""
        if severity not in self.issues:
            severity = "medium"
        issue = ReviewIssue(severity, description, category)
        self.issues[severity].append(issue)
    
    def get_issues_by_severity(self, severity: str) -> List[ReviewIssue]:
        """Get all issues of a specific severity"""
        return self.issues.get(severity, [])
    
    def get_total_count(self) -> int:
        """Get total number of issues"""
        return sum(len(issues) for issues in self.issues.values())
    
    def get_counts_by_severity(self) -> Dict[str, int]:
        """Get count of issues by severity"""
        return {severity: len(issues) for severity, issues in self.issues.items()}
    
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues"""
        return len(self.issues["critical"]) > 0
    
    def has_high_issues(self, threshold: int = 5) -> bool:
        """Check if there are many high priority issues"""
        return len(self.issues["high"]) > threshold


class ReviewConfig:
    """Configuration for code review operations"""
    
    def __init__(self, mode: str = "standard", focus: str = None, recent_commits: int = 20):
        self.mode = mode
        self.focus = focus
        self.recent_commits = recent_commits
        self.project_root = Path(__file__).parent.parent.parent
        self.timeout_default = 60
        self.timeout_extended = 120
    
    def should_run_smoke_tests(self) -> bool:
        """Check if smoke tests should be run"""
        return self.mode != "ai-focus"
    
    def should_run_spec_check(self) -> bool:
        """Check if spec alignment should be checked"""
        return self.mode != "quick"
    
    def should_run_performance_check(self) -> bool:
        """Check if performance analysis should be run"""
        return self.mode == "full"
    
    def should_run_security_check(self) -> bool:
        """Check if security analysis should be run"""
        return self.mode != "quick"
    
    def is_quick_mode(self) -> bool:
        """Check if running in quick mode"""
        return self.mode == "quick"
    
    def is_ai_focused(self) -> bool:
        """Check if focusing on AI issues"""
        return self.focus == "ai-issues" or self.mode == "full"


class ReviewData:
    """Container for all review data and results"""
    
    def __init__(self):
        self.smoke_test_results: Dict[str, bool] = {}
        self.spec_code_conflicts: List[str] = []
        self.ai_issues_found: List[str] = []
        self.performance_concerns: List[str] = []
        self.security_issues: List[str] = []
        self.recent_changes: List[str] = []
        self.issue_tracker = IssueTracker()
    
    def add_smoke_test_result(self, test_name: str, passed: bool) -> None:
        """Add a smoke test result"""
        self.smoke_test_results[test_name] = passed
        if not passed:
            self.issue_tracker.add_issue("critical", f"Smoke test failed: {test_name}")
    
    def add_spec_conflict(self, conflict: str) -> None:
        """Add a spec-code conflict"""
        self.spec_code_conflicts.append(conflict)
        self.issue_tracker.add_issue("high", f"Missing implementation for spec: {conflict}")
    
    def add_ai_issue(self, issue: str) -> None:
        """Add an AI coding issue"""
        self.ai_issues_found.append(issue)
    
    def add_performance_concern(self, concern: str) -> None:
        """Add a performance concern"""
        self.performance_concerns.append(concern)
    
    def add_security_issue(self, issue: str) -> None:
        """Add a security issue"""
        self.security_issues.append(issue)
    
    def add_recent_changes(self, changes: List[str]) -> None:
        """Add recent git changes"""
        self.recent_changes = changes
    
    def get_all_smoke_tests_passed(self) -> bool:
        """Check if all smoke tests passed"""
        return all(self.smoke_test_results.values())


def create_review_config(mode: str = "standard", focus: str = None, 
                        recent_commits: int = 20) -> ReviewConfig:
    """Create a review configuration"""
    return ReviewConfig(mode, focus, recent_commits)


def create_review_data() -> ReviewData:
    """Create a review data container"""
    return ReviewData()