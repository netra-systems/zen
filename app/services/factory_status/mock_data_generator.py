"""Mock data generator for factory status when git is unavailable.

Provides mock data for testing and development.
Module follows 300-line limit with 8-line function limit.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import random
import uuid


class MockDataGenerator:
    """Generate mock data for factory status reports."""
    
    def generate_mock_commits(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Generate mock commit data."""
        commits = []
        for i in range(random.randint(5, 15)):
            commits.append({
                "hash": str(uuid.uuid4())[:8],
                "author": f"Developer {i % 3 + 1}",
                "email": f"dev{i % 3 + 1}@example.com",
                "timestamp": datetime.now() - timedelta(hours=random.randint(0, hours)),
                "message": self._get_random_commit_message(),
                "files_changed": random.randint(1, 10),
                "insertions": random.randint(10, 200),
                "deletions": random.randint(5, 100)
            })
        return commits
    
    def generate_mock_branches(self) -> List[Dict[str, Any]]:
        """Generate mock branch data."""
        branches = [
            {"name": "main", "status": "active", "commits_ahead": 0},
            {"name": "develop", "status": "active", "commits_ahead": 5},
            {"name": "feature/ai-factory", "status": "active", "commits_ahead": 12},
            {"name": "fix/websocket-issues", "status": "merged", "commits_ahead": 0},
        ]
        return branches
    
    def generate_mock_metrics(self) -> Dict[str, Any]:
        """Generate mock metrics."""
        return {
            "velocity": {
                "commits_per_day": random.randint(8, 20),
                "pr_merge_time": random.uniform(2.5, 8.0),
                "cycle_time": random.uniform(12.0, 48.0)
            },
            "quality": {
                "test_coverage": random.uniform(70, 95),
                "code_review_rate": random.uniform(85, 100),
                "bug_fix_rate": random.uniform(0.1, 0.3)
            },
            "business_value": {
                "features_delivered": random.randint(3, 8),
                "customer_impact_score": random.uniform(7.0, 9.5),
                "innovation_ratio": random.uniform(0.3, 0.6)
            }
        }
    
    def _get_random_commit_message(self) -> str:
        """Get a random commit message."""
        messages = [
            "feat: Add AI factory status reporting",
            "fix: Resolve WebSocket connection issues",
            "refactor: Improve error handling in agents",
            "test: Add unit tests for factory metrics",
            "docs: Update API documentation",
            "perf: Optimize database queries",
            "chore: Update dependencies",
            "feat: Implement business value calculator",
            "fix: Correct type safety issues",
            "refactor: Split large modules into smaller ones"
        ]
        return random.choice(messages)