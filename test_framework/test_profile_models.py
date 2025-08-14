#!/usr/bin/env python
"""
Test Profile Models - Data classes for test profiling and tracking
Contains test priority, status enums, and profile/suite management classes
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Set, Optional
from dataclasses import dataclass, field
from enum import Enum

class TestPriority(Enum):
    """Test priority levels for execution ordering"""
    CRITICAL = 1  # Must pass for deployment
    HIGH = 2      # Core functionality
    MEDIUM = 3    # Important features
    LOW = 4       # Nice-to-have tests
    OPTIONAL = 5  # Can be skipped if needed

class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    ERROR = "error"
    FLAKY = "flaky"

@dataclass
class TestProfile:
    """Profile of a test with historical data"""
    path: str
    name: str
    category: str
    priority: TestPriority = TestPriority.MEDIUM
    avg_duration: float = 0.0
    failure_rate: float = 0.0
    last_status: TestStatus = TestStatus.PENDING
    last_run: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_passes: int = 0
    total_runs: int = 0
    total_failures: int = 0
    dependencies: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    flaky_score: float = 0.0  # 0-1, higher means more flaky
    
    def update_result(self, status: TestStatus, duration: float):
        """Update test profile with new result"""
        self.total_runs += 1
        self.last_status = status
        self.last_run = datetime.now()
        
        # Update average duration
        if self.avg_duration == 0:
            self.avg_duration = duration
        else:
            self.avg_duration = (self.avg_duration * (self.total_runs - 1) + duration) / self.total_runs
        
        # Update failure tracking
        if status in [TestStatus.FAILED, TestStatus.ERROR, TestStatus.TIMEOUT]:
            self.total_failures += 1
            self.consecutive_failures += 1
            self.consecutive_passes = 0
        elif status == TestStatus.PASSED:
            self.consecutive_passes += 1
            self.consecutive_failures = 0
        
        # Update failure rate
        self.failure_rate = self.total_failures / self.total_runs if self.total_runs > 0 else 0
        
        # Calculate flaky score (tests that sometimes pass, sometimes fail)
        if self.total_runs > 5:
            if 0.2 < self.failure_rate < 0.8:
                self.flaky_score = 1 - abs(0.5 - self.failure_rate) * 2
            else:
                self.flaky_score = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "path": self.path,
            "name": self.name,
            "category": self.category,
            "priority": self.priority.value if isinstance(self.priority, TestPriority) else self.priority,
            "avg_duration": self.avg_duration,
            "failure_rate": self.failure_rate,
            "last_status": self.last_status.value if isinstance(self.last_status, TestStatus) else self.last_status,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_passes": self.consecutive_passes,
            "total_runs": self.total_runs,
            "total_failures": self.total_failures,
            "flaky_score": self.flaky_score,
            "dependencies": self.dependencies,
            "tags": list(self.tags)
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TestProfile':
        """Create TestProfile from dictionary"""
        profile = cls(
            path=data["path"],
            name=data["name"],
            category=data["category"]
        )
        
        # Set attributes with proper type conversion
        if "priority" in data:
            profile.priority = TestPriority(data["priority"]) if isinstance(data["priority"], int) else data["priority"]
        if "last_status" in data and data["last_status"]:
            profile.last_status = TestStatus(data["last_status"])
        if "last_run" in data and data["last_run"]:
            profile.last_run = datetime.fromisoformat(data["last_run"])
            
        # Copy numeric values
        for key in ["avg_duration", "failure_rate", "consecutive_failures", 
                   "consecutive_passes", "total_runs", "total_failures", "flaky_score"]:
            if key in data:
                setattr(profile, key, data[key])
                
        # Set collections
        if "dependencies" in data:
            profile.dependencies = data["dependencies"]
        if "tags" in data:
            profile.tags = set(data["tags"])
            
        return profile

@dataclass
class TestSuite:
    """Collection of tests with metadata"""
    name: str
    tests: List[TestProfile]
    priority: TestPriority = TestPriority.MEDIUM
    parallel_safe: bool = True
    max_parallel: int = 4
    timeout: int = 300
    retry_failed: bool = False
    retry_count: int = 1
    tags: Set[str] = field(default_factory=set)
    
    def get_execution_order(self) -> List[TestProfile]:
        """Get optimal execution order based on priorities and dependencies"""
        # Sort by priority, then by failure rate (run stable tests first)
        return sorted(self.tests, key=lambda t: (
            t.priority.value if isinstance(t.priority, TestPriority) else t.priority,
            t.failure_rate, 
            -t.avg_duration
        ))

    def add_test(self, test: TestProfile):
        """Add a test to the suite"""
        self.tests.append(test)

    def remove_test(self, test_name: str) -> bool:
        """Remove a test from the suite by name"""
        original_count = len(self.tests)
        self.tests = [t for t in self.tests if t.name != test_name]
        return len(self.tests) < original_count

    def get_test_by_name(self, test_name: str) -> Optional[TestProfile]:
        """Get a test by name"""
        for test in self.tests:
            if test.name == test_name:
                return test
        return None

    def get_tests_by_category(self, category: str) -> List[TestProfile]:
        """Get all tests in a specific category"""
        return [t for t in self.tests if t.category == category]

    def get_failing_tests(self) -> List[TestProfile]:
        """Get all tests that are currently failing"""
        return [t for t in self.tests if t.consecutive_failures > 0]

    def get_flaky_tests(self, threshold: float = 0.3) -> List[TestProfile]:
        """Get all flaky tests above threshold"""
        return [t for t in self.tests if t.flaky_score > threshold]


class TestProfileManager:
    """Manages loading, saving, and querying test profiles"""
    
    def __init__(self, profiles_path: Path):
        self.profiles_path = profiles_path
        self.profiles: dict[str, TestProfile] = {}
    
    def load_profiles(self) -> dict[str, TestProfile]:
        """Load test profiles from file"""
        if not self.profiles_path.exists():
            return {}
            
        try:
            with open(self.profiles_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return {}
                data = json.loads(content)
                profiles = {}
                for test_id, profile_data in data.items():
                    profiles[test_id] = TestProfile.from_dict(profile_data)
                self.profiles = profiles
                return profiles
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            return {}
    
    def save_profiles(self, profiles: dict[str, TestProfile]):
        """Save test profiles to file"""
        profiles_data = {
            name: profile.to_dict()
            for name, profile in profiles.items()
        }
        
        # Ensure directory exists
        self.profiles_path.parent.mkdir(exist_ok=True, parents=True)
        
        with open(self.profiles_path, 'w', encoding='utf-8') as f:
            json.dump(profiles_data, f, indent=2)
        
        self.profiles = profiles
    
    def get_profile(self, test_name: str) -> Optional[TestProfile]:
        """Get a specific test profile"""
        return self.profiles.get(test_name)
    
    def update_profile(self, test_name: str, profile: TestProfile):
        """Update or add a test profile"""
        self.profiles[test_name] = profile
    
    def get_profiles_by_category(self, category: str) -> List[TestProfile]:
        """Get all profiles in a category"""
        return [p for p in self.profiles.values() if p.category == category]
    
    def get_problem_tests(self, min_failures: int = 3) -> List[TestProfile]:
        """Get tests with consecutive failures"""
        return [p for p in self.profiles.values() if p.consecutive_failures >= min_failures]
    
    def get_flaky_tests(self, threshold: float = 0.3) -> List[TestProfile]:
        """Get flaky tests above threshold"""
        return [p for p in self.profiles.values() if p.flaky_score > threshold]