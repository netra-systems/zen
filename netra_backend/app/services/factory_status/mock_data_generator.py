"""
Mock data generator for factory status testing.

Business Value Justification (BVJ):
- Segment: All segments  
- Business Goal: Enable testing and development
- Value Impact: Supports development velocity and testing reliability
- Revenue Impact: Indirect - ensures system reliability for production
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List


class MockDataGenerator:
    """Generates mock data for factory status reporting and testing."""
    
    def __init__(self):
        """Initialize mock data generator."""
        self.commit_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore"]
        self.authors = ["dev1", "dev2", "dev3", "dev4"]
    
    def generate_mock_commits(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate mock commit data."""
        commits = []
        for i in range(count):
            commit = self._create_mock_commit(i)
            commits.append(commit)
        return commits
    
    def _create_mock_commit(self, index: int) -> Dict[str, Any]:
        """Create a single mock commit."""
        commit_type = random.choice(self.commit_types)
        author = random.choice(self.authors)
        timestamp = datetime.now() - timedelta(hours=random.randint(0, 168))  # Last week
        return {
            "hash": f"abc123{index}",
            "type": commit_type,
            "message": f"{commit_type}: mock commit {index}",
            "author": author,
            "email": f"{author.lower().replace(' ', '.')}@example.com",
            "timestamp": timestamp,
            "files_changed": random.randint(1, 5),
            "insertions": random.randint(10, 200),
            "deletions": random.randint(0, 100)
        }
    
    def generate_mock_metrics(self) -> Dict[str, Any]:
        """Generate mock metrics data."""
        return {
            "test_coverage": random.uniform(0.7, 0.95),
            "code_quality": random.uniform(0.8, 1.0),
            "build_success_rate": random.uniform(0.85, 1.0),
            "deployment_frequency": random.randint(1, 10)
        }