"""Mock data generator for factory status reports.

Provides mock data for testing and development.
Module follows 450-line limit with 25-line function limit.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

class MockDataGenerator:
    """Generate mock data for factory status reports."""
    
    def __init__(self):
        """Initialize mock data generator."""
        self.base_seed = 42
        random.seed(self.base_seed)
    
    def generate_mock_commit(self) -> Dict[str, Any]:
        """Generate a mock git commit."""
        commit_types = ["feature", "fix", "refactor", "test", "docs"]
        return {
            "hash": self._generate_hash(),
            "message": f"{random.choice(commit_types)}: Mock commit message",
            "author": "Mock Author",
            "date": datetime.now() - timedelta(days=random.randint(0, 30))
        }
    
    def generate_mock_metrics(self) -> Dict[str, float]:
        """Generate mock metrics data."""
        return {
            "code_quality": random.uniform(0.7, 1.0),
            "test_coverage": random.uniform(0.6, 0.95),
            "performance": random.uniform(0.8, 1.0),
            "security_score": random.uniform(0.85, 1.0)
        }
    
    def generate_mock_report(self) -> Dict[str, Any]:
        """Generate a complete mock report."""
        commits = [self.generate_mock_commit() for _ in range(10)]
        metrics = self.generate_mock_metrics()
        return {"commits": commits, "metrics": metrics, "timestamp": datetime.now()}
    
    def _generate_hash(self) -> str:
        """Generate a mock git hash."""
        chars = "0123456789abcdef"
        hash_length = 40
        return "".join(random.choice(chars) for _ in range(hash_length))