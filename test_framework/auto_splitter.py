#!/usr/bin/env python3
"""
Auto-Splitter Module - Intelligent test splitting with historical timing
Provides dynamic test execution window creation and workload balancing
"""

import json
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union


class SplittingStrategy(Enum):
    """Test splitting strategies"""
    TIME_BASED = "time_based"        # Split by estimated execution time
    COUNT_BASED = "count_based"      # Split by number of tests
    CATEGORY_BASED = "category_based" # Split by test categories
    COMPLEXITY_BASED = "complexity_based" # Split by test complexity
    DEPENDENCY_AWARE = "dependency_aware" # Split considering dependencies
    HYBRID = "hybrid"                # Combine multiple strategies


class WindowPriority(Enum):
    """Execution window priorities"""
    CRITICAL = 1    # Must execute first
    HIGH = 2        # High priority execution
    NORMAL = 3      # Normal execution order
    LOW = 4         # Can be deferred
    BACKGROUND = 5  # Background execution


@dataclass
class TestItem:
    """Individual test item with metadata"""
    name: str
    category: str
    file_path: str
    estimated_duration: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    complexity_score: float = 1.0
    
    # Historical data
    average_duration: Optional[timedelta] = None
    success_rate: float = 1.0
    failure_rate: float = 0.0
    last_run_duration: Optional[timedelta] = None
    
    # Dependencies and constraints
    dependencies: Set[str] = field(default_factory=set)
    resource_requirements: Set[str] = field(default_factory=set)  # memory, cpu, network, database
    
    # Metadata
    tags: Set[str] = field(default_factory=set)
    markers: Set[str] = field(default_factory=set)  # pytest markers
    flaky: bool = False
    slow: bool = False
    
    def __post_init__(self):
        """Initialize computed properties"""
        if isinstance(self.dependencies, (list, tuple)):
            self.dependencies = set(self.dependencies)
        if isinstance(self.resource_requirements, (list, tuple)):
            self.resource_requirements = set(self.resource_requirements)
        if isinstance(self.tags, (list, tuple)):
            self.tags = set(self.tags)
        if isinstance(self.markers, (list, tuple)):
            self.markers = set(self.markers)
    
    @property
    def effective_duration(self) -> timedelta:
        """Get the most accurate duration estimate"""
        if self.average_duration:
            return self.average_duration
        elif self.last_run_duration:
            return self.last_run_duration
        else:
            return self.estimated_duration
    
    @property
    def reliability_score(self) -> float:
        """Calculate test reliability score (0-1, higher is better)"""
        if self.flaky:
            return 0.3
        return max(0.1, self.success_rate - (self.failure_rate * 0.5))
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "category": self.category,
            "file_path": self.file_path,
            "estimated_duration": self.estimated_duration.total_seconds(),
            "complexity_score": self.complexity_score,
            "average_duration": self.average_duration.total_seconds() if self.average_duration else None,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "last_run_duration": self.last_run_duration.total_seconds() if self.last_run_duration else None,
            "dependencies": list(self.dependencies),
            "resource_requirements": list(self.resource_requirements),
            "tags": list(self.tags),
            "markers": list(self.markers),
            "flaky": self.flaky,
            "slow": self.slow,
            "effective_duration": self.effective_duration.total_seconds(),
            "reliability_score": self.reliability_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TestItem':
        """Create from dictionary"""
        item = cls(
            name=data["name"],
            category=data["category"],
            file_path=data["file_path"],
            estimated_duration=timedelta(seconds=data.get("estimated_duration", 30)),
            complexity_score=data.get("complexity_score", 1.0),
            success_rate=data.get("success_rate", 1.0),
            failure_rate=data.get("failure_rate", 0.0),
            dependencies=set(data.get("dependencies", [])),
            resource_requirements=set(data.get("resource_requirements", [])),
            tags=set(data.get("tags", [])),
            markers=set(data.get("markers", [])),
            flaky=data.get("flaky", False),
            slow=data.get("slow", False)
        )
        
        if data.get("average_duration"):
            item.average_duration = timedelta(seconds=data["average_duration"])
        if data.get("last_run_duration"):
            item.last_run_duration = timedelta(seconds=data["last_run_duration"])
        
        return item


@dataclass
class TestExecutionWindow:
    """Test execution window with balanced workload"""
    window_id: str
    tests: List[TestItem] = field(default_factory=list)
    priority: WindowPriority = WindowPriority.NORMAL
    
    # Timing and resource estimates
    estimated_duration: timedelta = field(default_factory=lambda: timedelta(0))
    max_duration: timedelta = field(default_factory=lambda: timedelta(minutes=30))
    resource_requirements: Set[str] = field(default_factory=set)
    
    # Execution constraints
    parallel_safe: bool = True
    max_parallel_tests: int = 4
    requires_isolation: bool = False
    
    # Categorization and grouping
    primary_category: Optional[str] = None
    categories: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    
    # Dependencies and ordering
    dependencies: Set[str] = field(default_factory=set)  # Other window IDs
    blocks: Set[str] = field(default_factory=set)        # Windows this blocks
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    strategy_used: Optional[SplittingStrategy] = None
    balancing_score: float = 0.0  # How well balanced this window is (0-1)
    
    def __post_init__(self):
        """Initialize computed properties"""
        if isinstance(self.resource_requirements, (list, tuple)):
            self.resource_requirements = set(self.resource_requirements)
        if isinstance(self.categories, (list, tuple)):
            self.categories = set(self.categories)
        if isinstance(self.tags, (list, tuple)):
            self.tags = set(self.tags)
        if isinstance(self.dependencies, (list, tuple)):
            self.dependencies = set(self.dependencies)
        if isinstance(self.blocks, (list, tuple)):
            self.blocks = set(self.blocks)
        
        self._update_computed_properties()
    
    def _update_computed_properties(self):
        """Update computed properties based on current tests"""
        if not self.tests:
            return
        
        # Calculate estimated duration
        self.estimated_duration = sum((test.effective_duration for test in self.tests), timedelta(0))
        
        # Aggregate resource requirements
        for test in self.tests:
            self.resource_requirements.update(test.resource_requirements)
        
        # Aggregate categories and tags
        for test in self.tests:
            self.categories.add(test.category)
            self.tags.update(test.tags)
        
        # Set primary category (most common)
        if self.categories:
            category_counts = {}
            for test in self.tests:
                category_counts[test.category] = category_counts.get(test.category, 0) + 1
            self.primary_category = max(category_counts, key=category_counts.get)
        
        # Check if parallel safe (all tests must be parallel safe)
        self.parallel_safe = all(
            "not_parallel" not in test.markers and "sequential" not in test.markers
            for test in self.tests
        )
        
        # Check if isolation required
        self.requires_isolation = any(
            "isolation" in test.markers or "database" in test.resource_requirements
            for test in self.tests
        )
        
        # Calculate balancing score
        self._calculate_balancing_score()
    
    def _calculate_balancing_score(self) -> float:
        """Calculate how well balanced this window is"""
        if not self.tests:
            self.balancing_score = 0.0
            return
        
        # Factors for balancing score:
        # 1. Duration variance (lower is better)
        # 2. Complexity variance (lower is better)
        # 3. Reliability variance (lower is better)
        # 4. Resource conflicts (fewer is better)
        
        durations = [test.effective_duration.total_seconds() for test in self.tests]
        complexities = [test.complexity_score for test in self.tests]
        reliabilities = [test.reliability_score for test in self.tests]
        
        # Duration variance score (0-1, higher is better)
        duration_score = 1.0
        if len(durations) > 1:
            duration_variance = statistics.variance(durations)
            duration_mean = statistics.mean(durations)
            if duration_mean > 0:
                duration_cv = (duration_variance ** 0.5) / duration_mean
                duration_score = max(0.1, 1.0 - min(1.0, duration_cv))
        
        # Complexity variance score (0-1, higher is better)
        complexity_score = 1.0
        if len(complexities) > 1:
            complexity_variance = statistics.variance(complexities)
            complexity_mean = statistics.mean(complexities)
            if complexity_mean > 0:
                complexity_cv = (complexity_variance ** 0.5) / complexity_mean
                complexity_score = max(0.1, 1.0 - min(1.0, complexity_cv))
        
        # Reliability score (average reliability)
        reliability_score = statistics.mean(reliabilities) if reliabilities else 0.5
        
        # Resource conflict penalty
        resource_penalty = 0.0
        resource_count = len(self.resource_requirements)
        if resource_count > 2:  # More than 2 resource types may cause conflicts
            resource_penalty = min(0.3, (resource_count - 2) * 0.1)
        
        # Combined score
        self.balancing_score = (
            (duration_score * 0.3) +
            (complexity_score * 0.2) +
            (reliability_score * 0.3) +
            (max(0, 1.0 - resource_penalty) * 0.2)
        )
    
    def add_test(self, test: TestItem) -> bool:
        """Add a test to this window"""
        # Check if adding this test would exceed duration limit
        new_duration = self.estimated_duration + test.effective_duration
        if new_duration > self.max_duration:
            return False
        
        # Check for resource conflicts if isolation required
        if self.requires_isolation and test.resource_requirements.intersection(self.resource_requirements):
            return False
        
        self.tests.append(test)
        self._update_computed_properties()
        return True
    
    def remove_test(self, test_name: str) -> bool:
        """Remove a test from this window"""
        for i, test in enumerate(self.tests):
            if test.name == test_name:
                self.tests.pop(i)
                self._update_computed_properties()
                return True
        return False
    
    def can_run_with(self, other_window: 'TestExecutionWindow') -> bool:
        """Check if this window can run in parallel with another"""
        if not self.parallel_safe or not other_window.parallel_safe:
            return False
        
        if self.requires_isolation or other_window.requires_isolation:
            return False
        
        # Check for resource conflicts
        if self.resource_requirements.intersection(other_window.resource_requirements):
            # Some resources can be shared, others cannot
            conflicting_resources = {"database", "external_service", "file_system"}
            if self.resource_requirements.intersection(other_window.resource_requirements).intersection(conflicting_resources):
                return False
        
        return True
    
    @property
    def test_count(self) -> int:
        """Get number of tests in this window"""
        return len(self.tests)
    
    @property
    def average_complexity(self) -> float:
        """Get average complexity score"""
        if not self.tests:
            return 0.0
        return statistics.mean(test.complexity_score for test in self.tests)
    
    @property
    def average_reliability(self) -> float:
        """Get average reliability score"""
        if not self.tests:
            return 0.0
        return statistics.mean(test.reliability_score for test in self.tests)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "window_id": self.window_id,
            "tests": [test.to_dict() for test in self.tests],
            "priority": self.priority.name,
            "estimated_duration": self.estimated_duration.total_seconds(),
            "max_duration": self.max_duration.total_seconds(),
            "resource_requirements": list(self.resource_requirements),
            "parallel_safe": self.parallel_safe,
            "max_parallel_tests": self.max_parallel_tests,
            "requires_isolation": self.requires_isolation,
            "primary_category": self.primary_category,
            "categories": list(self.categories),
            "tags": list(self.tags),
            "dependencies": list(self.dependencies),
            "blocks": list(self.blocks),
            "created_at": self.created_at.isoformat(),
            "strategy_used": self.strategy_used.value if self.strategy_used else None,
            "balancing_score": self.balancing_score,
            "test_count": self.test_count,
            "average_complexity": self.average_complexity,
            "average_reliability": self.average_reliability
        }


class TestSplitter:
    """Intelligent test splitter with multiple strategies"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.history_file = project_root / "test_reports" / "test_history.json"
        self.test_history: Dict[str, Dict] = {}
        self._load_test_history()
    
    def _load_test_history(self):
        """Load historical test execution data"""
        if not self.history_file.exists():
            return
        
        try:
            with open(self.history_file) as f:
                self.test_history = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load test history: {e}")
            self.test_history = {}
    
    def _save_test_history(self):
        """Save test history data"""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump(self.test_history, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save test history: {e}")
    
    def discover_tests(self, test_paths: List[str], categories: List[str] = None) -> List[TestItem]:
        """Discover and analyze tests from given paths"""
        tests = []
        
        for path_str in test_paths:
            path = Path(path_str)
            if path.is_file() and path.suffix == '.py':
                tests.extend(self._discover_tests_in_file(path, categories))
            elif path.is_dir():
                tests.extend(self._discover_tests_in_directory(path, categories))
        
        return tests
    
    def _discover_tests_in_file(self, file_path: Path, categories: List[str] = None) -> List[TestItem]:
        """Discover tests in a single Python file"""
        tests = []
        
        try:
            # Simple regex-based discovery (could be enhanced with AST parsing)
            with open(file_path) as f:
                content = f.read()
            
            import re
            # Find test functions
            test_functions = re.findall(r'def (test_\w+)', content)
            
            for test_func in test_functions:
                test_name = f"{file_path.stem}::{test_func}"
                category = self._categorize_test(file_path, test_func, categories)
                
                # Get historical data
                history = self.test_history.get(test_name, {})
                
                test_item = TestItem(
                    name=test_name,
                    category=category,
                    file_path=str(file_path),
                    estimated_duration=timedelta(seconds=history.get("avg_duration", 30)),
                    complexity_score=self._calculate_complexity_score(content, test_func),
                    success_rate=history.get("success_rate", 1.0),
                    failure_rate=history.get("failure_rate", 0.0),
                    flaky=history.get("flaky", False),
                    slow=history.get("slow", False)
                )
                
                if history.get("avg_duration"):
                    test_item.average_duration = timedelta(seconds=history["avg_duration"])
                if history.get("last_duration"):
                    test_item.last_run_duration = timedelta(seconds=history["last_duration"])
                
                # Analyze markers and requirements
                self._analyze_test_requirements(content, test_func, test_item)
                
                tests.append(test_item)
                
        except Exception as e:
            print(f"Warning: Could not analyze file {file_path}: {e}")
        
        return tests
    
    def _discover_tests_in_directory(self, dir_path: Path, categories: List[str] = None) -> List[TestItem]:
        """Discover tests in a directory recursively"""
        tests = []
        
        for test_file in dir_path.rglob("test_*.py"):
            tests.extend(self._discover_tests_in_file(test_file, categories))
        
        return tests
    
    def _categorize_test(self, file_path: Path, test_func: str, categories: List[str] = None) -> str:
        """Categorize a test based on its path and name"""
        path_str = str(file_path).lower()
        func_name = test_func.lower()
        
        # Category mapping based on path and function name
        if "unit" in path_str or "test_unit" in func_name:
            return "unit"
        elif "integration" in path_str or "test_integration" in func_name:
            return "integration"
        elif "e2e" in path_str or "end_to_end" in path_str or "test_e2e" in func_name:
            return "e2e"
        elif "performance" in path_str or "perf" in path_str or "test_perf" in func_name:
            return "performance"
        elif "security" in path_str or "auth" in path_str or "test_auth" in func_name:
            return "security"
        elif "database" in path_str or "db" in path_str or "test_db" in func_name:
            return "database"
        elif "websocket" in path_str or "ws" in path_str or "test_ws" in func_name:
            return "websocket"
        elif "api" in path_str or "test_api" in func_name:
            return "api"
        elif "agent" in path_str or "test_agent" in func_name:
            return "agent"
        elif "frontend" in path_str or "ui" in path_str:
            return "frontend"
        else:
            return "other"
    
    def _calculate_complexity_score(self, content: str, test_func: str) -> float:
        """Calculate complexity score for a test function"""
        # Simple heuristic based on code patterns
        lines_in_func = 0
        in_function = False
        indent_level = 0
        complexity_indicators = 0
        
        for line in content.split('\n'):
            stripped = line.strip()
            
            if f"def {test_func}" in line:
                in_function = True
                indent_level = len(line) - len(line.lstrip())
                continue
            
            if in_function:
                current_indent = len(line) - len(line.lstrip())
                
                # End of function
                if line.strip() and current_indent <= indent_level:
                    break
                
                if stripped:
                    lines_in_func += 1
                    
                    # Count complexity indicators
                    if any(keyword in stripped for keyword in ['if', 'for', 'while', 'try', 'with']):
                        complexity_indicators += 1
                    if any(pattern in stripped for pattern in ['async', 'await', 'mock', 'patch']):
                        complexity_indicators += 1
        
        # Base complexity score
        base_score = min(3.0, lines_in_func / 10.0)  # 0-3 based on length
        complexity_bonus = min(2.0, complexity_indicators / 5.0)  # 0-2 based on complexity
        
        return max(1.0, base_score + complexity_bonus)
    
    def _analyze_test_requirements(self, content: str, test_func: str, test_item: TestItem):
        """Analyze test requirements from code content"""
        # Extract function content
        func_content = self._extract_function_content(content, test_func)
        
        # Analyze markers
        if "@pytest.mark." in func_content:
            import re
            markers = re.findall(r'@pytest\.mark\.(\w+)', func_content)
            test_item.markers.update(markers)
        
        # Analyze resource requirements
        if any(pattern in func_content.lower() for pattern in ['database', 'db', 'session', 'commit']):
            test_item.resource_requirements.add('database')
        
        if any(pattern in func_content.lower() for pattern in ['requests', 'http', 'api', 'client']):
            test_item.resource_requirements.add('network')
        
        if any(pattern in func_content.lower() for pattern in ['memory', 'large', 'big', 'massive']):
            test_item.resource_requirements.add('memory')
        
        if any(pattern in func_content.lower() for pattern in ['cpu', 'compute', 'calculation', 'process']):
            test_item.resource_requirements.add('cpu')
        
        if any(pattern in func_content.lower() for pattern in ['file', 'disk', 'write', 'read']):
            test_item.resource_requirements.add('file_system')
        
        # Analyze tags from comments
        import re
        tag_matches = re.findall(r'#\s*tags?:\s*([^\n]+)', func_content, re.IGNORECASE)
        for tag_match in tag_matches:
            tags = [tag.strip() for tag in tag_match.split(',')]
            test_item.tags.update(tags)
    
    def _extract_function_content(self, content: str, test_func: str) -> str:
        """Extract the content of a specific function"""
        lines = content.split('\n')
        func_lines = []
        in_function = False
        indent_level = 0
        
        for line in lines:
            if f"def {test_func}" in line:
                in_function = True
                indent_level = len(line) - len(line.lstrip())
                func_lines.append(line)
                continue
            
            if in_function:
                current_indent = len(line) - len(line.lstrip())
                
                # End of function
                if line.strip() and current_indent <= indent_level:
                    break
                
                func_lines.append(line)
        
        return '\n'.join(func_lines)
    
    def create_windows(self, tests: List[TestItem], strategy: SplittingStrategy = SplittingStrategy.HYBRID,
                      target_window_duration: timedelta = timedelta(minutes=15),
                      max_windows: int = None, max_parallel: int = 8) -> List[TestExecutionWindow]:
        """Create execution windows using the specified strategy"""
        
        if strategy == SplittingStrategy.TIME_BASED:
            return self._create_time_based_windows(tests, target_window_duration, max_windows)
        elif strategy == SplittingStrategy.COUNT_BASED:
            return self._create_count_based_windows(tests, max_windows or 8)
        elif strategy == SplittingStrategy.CATEGORY_BASED:
            return self._create_category_based_windows(tests, target_window_duration)
        elif strategy == SplittingStrategy.COMPLEXITY_BASED:
            return self._create_complexity_based_windows(tests, target_window_duration, max_windows)
        elif strategy == SplittingStrategy.DEPENDENCY_AWARE:
            return self._create_dependency_aware_windows(tests, target_window_duration, max_parallel)
        elif strategy == SplittingStrategy.HYBRID:
            return self._create_hybrid_windows(tests, target_window_duration, max_windows, max_parallel)
        else:
            # Default to time-based
            return self._create_time_based_windows(tests, target_window_duration, max_windows)
    
    def _create_time_based_windows(self, tests: List[TestItem], target_duration: timedelta,
                                  max_windows: int = None) -> List[TestExecutionWindow]:
        """Create windows based on execution time balancing"""
        if not tests:
            return []
        
        # Sort tests by duration (longest first for better balancing)
        sorted_tests = sorted(tests, key=lambda t: t.effective_duration, reverse=True)
        
        windows = []
        window_count = max_windows or max(1, math.ceil(len(tests) / 10))
        
        for i in range(window_count):
            window = TestExecutionWindow(
                window_id=f"time_window_{i+1}",
                max_duration=target_duration * 1.5,  # Allow some flexibility
                strategy_used=SplittingStrategy.TIME_BASED
            )
            windows.append(window)
        
        # Distribute tests using best-fit algorithm
        for test in sorted_tests:
            # Find window with least estimated duration that can fit this test
            best_window = None
            for window in windows:
                if window.add_test(test):  # Try to add test
                    best_window = window
                    break
                else:
                    # Remove test if it was added during the attempt
                    window.remove_test(test.name)
            
            if not best_window:
                # Create new window if none can accommodate
                new_window = TestExecutionWindow(
                    window_id=f"time_window_{len(windows)+1}",
                    max_duration=target_duration * 2,
                    strategy_used=SplittingStrategy.TIME_BASED
                )
                new_window.add_test(test)
                windows.append(new_window)
        
        # Remove empty windows
        return [w for w in windows if w.test_count > 0]
    
    def _create_count_based_windows(self, tests: List[TestItem], window_count: int) -> List[TestExecutionWindow]:
        """Create windows with roughly equal test counts"""
        if not tests:
            return []
        
        tests_per_window = math.ceil(len(tests) / window_count)
        windows = []
        
        for i in range(0, len(tests), tests_per_window):
            window_tests = tests[i:i + tests_per_window]
            window = TestExecutionWindow(
                window_id=f"count_window_{len(windows)+1}",
                strategy_used=SplittingStrategy.COUNT_BASED
            )
            
            for test in window_tests:
                window.add_test(test)
            
            if window.test_count > 0:
                windows.append(window)
        
        return windows
    
    def _create_category_based_windows(self, tests: List[TestItem], target_duration: timedelta) -> List[TestExecutionWindow]:
        """Create windows grouped by test categories"""
        if not tests:
            return []
        
        # Group tests by category
        category_groups = {}
        for test in tests:
            if test.category not in category_groups:
                category_groups[test.category] = []
            category_groups[test.category].append(test)
        
        windows = []
        
        for category, category_tests in category_groups.items():
            # Further split large categories by duration
            if sum(test.effective_duration for test in category_tests) > target_duration * 2:
                # Split into multiple windows
                category_windows = self._create_time_based_windows(category_tests, target_duration)
                for i, window in enumerate(category_windows):
                    window.window_id = f"{category}_window_{i+1}"
                    window.strategy_used = SplittingStrategy.CATEGORY_BASED
                    window.primary_category = category
                windows.extend(category_windows)
            else:
                # Single window for category
                window = TestExecutionWindow(
                    window_id=f"{category}_window",
                    max_duration=target_duration * 2,
                    primary_category=category,
                    strategy_used=SplittingStrategy.CATEGORY_BASED
                )
                
                for test in category_tests:
                    window.add_test(test)
                
                windows.append(window)
        
        return windows
    
    def _create_complexity_based_windows(self, tests: List[TestItem], target_duration: timedelta,
                                       max_windows: int = None) -> List[TestExecutionWindow]:
        """Create windows balancing complexity scores"""
        if not tests:
            return []
        
        # Sort by complexity (high to low)
        sorted_tests = sorted(tests, key=lambda t: t.complexity_score, reverse=True)
        
        window_count = max_windows or max(1, math.ceil(len(tests) / 8))
        windows = []
        
        for i in range(window_count):
            window = TestExecutionWindow(
                window_id=f"complexity_window_{i+1}",
                max_duration=target_duration * 1.5,
                strategy_used=SplittingStrategy.COMPLEXITY_BASED
            )
            windows.append(window)
        
        # Distribute tests to balance complexity
        for test in sorted_tests:
            # Find window with lowest total complexity
            best_window = min(windows, key=lambda w: w.average_complexity * w.test_count)
            best_window.add_test(test)
        
        return [w for w in windows if w.test_count > 0]
    
    def _create_dependency_aware_windows(self, tests: List[TestItem], target_duration: timedelta,
                                       max_parallel: int) -> List[TestExecutionWindow]:
        """Create windows considering test dependencies"""
        if not tests:
            return []
        
        # For now, implement a simple dependency-aware grouping
        # This could be enhanced with actual dependency analysis
        
        # Separate tests with and without dependencies
        independent_tests = [t for t in tests if not t.dependencies]
        dependent_tests = [t for t in tests if t.dependencies]
        
        windows = []
        
        # Create windows for independent tests first
        if independent_tests:
            independent_windows = self._create_time_based_windows(independent_tests, target_duration)
            for window in independent_windows:
                window.window_id = window.window_id.replace("time_", "independent_")
                window.strategy_used = SplittingStrategy.DEPENDENCY_AWARE
                window.priority = WindowPriority.HIGH  # Can run in parallel
            windows.extend(independent_windows)
        
        # Create sequential windows for dependent tests
        if dependent_tests:
            dependent_window = TestExecutionWindow(
                window_id="dependent_tests_window",
                max_duration=target_duration * 3,  # Allow longer duration
                strategy_used=SplittingStrategy.DEPENDENCY_AWARE,
                priority=WindowPriority.NORMAL,
                parallel_safe=False  # Dependencies may require sequential execution
            )
            
            for test in dependent_tests:
                dependent_window.add_test(test)
            
            windows.append(dependent_window)
        
        return windows
    
    def _create_hybrid_windows(self, tests: List[TestItem], target_duration: timedelta,
                             max_windows: int = None, max_parallel: int = 8) -> List[TestExecutionWindow]:
        """Create windows using hybrid strategy combining multiple approaches"""
        if not tests:
            return []
        
        # Phase 1: Separate by major characteristics
        critical_tests = [t for t in tests if any(marker in t.markers for marker in ['critical', 'smoke'])]
        slow_tests = [t for t in tests if t.slow or t.effective_duration > timedelta(minutes=5)]
        flaky_tests = [t for t in tests if t.flaky]
        regular_tests = [t for t in tests if t not in critical_tests + slow_tests + flaky_tests]
        
        windows = []
        
        # Phase 2: Create specialized windows
        
        # Critical tests - highest priority, parallel execution
        if critical_tests:
            critical_window = TestExecutionWindow(
                window_id="critical_tests",
                priority=WindowPriority.CRITICAL,
                max_duration=target_duration,
                strategy_used=SplittingStrategy.HYBRID,
                parallel_safe=True,
                max_parallel_tests=max_parallel
            )
            for test in critical_tests:
                critical_window.add_test(test)
            windows.append(critical_window)
        
        # Flaky tests - isolated execution with retries
        if flaky_tests:
            flaky_window = TestExecutionWindow(
                window_id="flaky_tests",
                priority=WindowPriority.LOW,
                max_duration=target_duration * 2,
                strategy_used=SplittingStrategy.HYBRID,
                requires_isolation=True,
                parallel_safe=False
            )
            for test in flaky_tests:
                flaky_window.add_test(test)
            windows.append(flaky_window)
        
        # Slow tests - separate windows to avoid blocking others
        if slow_tests:
            slow_windows = self._create_time_based_windows(slow_tests, target_duration * 2)
            for i, window in enumerate(slow_windows):
                window.window_id = f"slow_tests_{i+1}"
                window.strategy_used = SplittingStrategy.HYBRID
                window.priority = WindowPriority.LOW
            windows.extend(slow_windows)
        
        # Regular tests - category-based with time balancing
        if regular_tests:
            regular_windows = self._create_category_based_windows(regular_tests, target_duration)
            for window in regular_windows:
                window.strategy_used = SplittingStrategy.HYBRID
                if window.primary_category in ['unit', 'smoke']:
                    window.priority = WindowPriority.HIGH
                elif window.primary_category in ['integration', 'api']:
                    window.priority = WindowPriority.NORMAL
                else:
                    window.priority = WindowPriority.LOW
            windows.extend(regular_windows)
        
        # Phase 3: Optimize window count and balancing
        if max_windows and len(windows) > max_windows:
            windows = self._consolidate_windows(windows, max_windows, target_duration)
        
        return windows
    
    def _consolidate_windows(self, windows: List[TestExecutionWindow], max_windows: int,
                           target_duration: timedelta) -> List[TestExecutionWindow]:
        """Consolidate windows to meet maximum count constraint"""
        if len(windows) <= max_windows:
            return windows
        
        # Sort by priority (keep high priority windows separate)
        critical_windows = [w for w in windows if w.priority == WindowPriority.CRITICAL]
        other_windows = [w for w in windows if w.priority != WindowPriority.CRITICAL]
        
        # Keep critical windows as-is
        result_windows = critical_windows[:]
        
        # Consolidate other windows
        remaining_slots = max_windows - len(critical_windows)
        if remaining_slots <= 0:
            return critical_windows
        
        if len(other_windows) <= remaining_slots:
            result_windows.extend(other_windows)
        else:
            # Merge similar windows
            consolidated = self._merge_similar_windows(other_windows, remaining_slots, target_duration)
            result_windows.extend(consolidated)
        
        return result_windows
    
    def _merge_similar_windows(self, windows: List[TestExecutionWindow], target_count: int,
                             target_duration: timedelta) -> List[TestExecutionWindow]:
        """Merge similar windows to reduce count"""
        if len(windows) <= target_count:
            return windows
        
        # Group windows by category and priority
        groups = {}
        for window in windows:
            key = (window.primary_category or 'unknown', window.priority)
            if key not in groups:
                groups[key] = []
            groups[key].append(window)
        
        result = []
        
        for (category, priority), group_windows in groups.items():
            if len(group_windows) == 1:
                result.extend(group_windows)
            else:
                # Merge windows in this group
                merged_window = TestExecutionWindow(
                    window_id=f"merged_{category}_{priority.name.lower()}",
                    primary_category=category,
                    priority=priority,
                    max_duration=target_duration * 2,
                    strategy_used=SplittingStrategy.HYBRID
                )
                
                for window in group_windows:
                    for test in window.tests:
                        if not merged_window.add_test(test):
                            # If can't fit, create additional merged window
                            if merged_window.test_count > 0:
                                result.append(merged_window)
                            
                            merged_window = TestExecutionWindow(
                                window_id=f"merged_{category}_{priority.name.lower()}_{len(result)+1}",
                                primary_category=category,
                                priority=priority,
                                max_duration=target_duration * 2,
                                strategy_used=SplittingStrategy.HYBRID
                            )
                            merged_window.add_test(test)
                
                if merged_window.test_count > 0:
                    result.append(merged_window)
        
        return result
    
    def rebalance_windows(self, windows: List[TestExecutionWindow]) -> List[TestExecutionWindow]:
        """Rebalance existing windows for better load distribution"""
        if not windows:
            return windows
        
        # Calculate current imbalance
        durations = [w.estimated_duration.total_seconds() for w in windows]
        if not durations:
            return windows
        
        avg_duration = statistics.mean(durations)
        duration_variance = statistics.variance(durations) if len(durations) > 1 else 0
        
        # If already well balanced, return as-is
        if duration_variance < (avg_duration * 0.3) ** 2:  # Coefficient of variation < 30%
            return windows
        
        # Find overloaded and underloaded windows
        overloaded = [w for w in windows if w.estimated_duration.total_seconds() > avg_duration * 1.3]
        underloaded = [w for w in windows if w.estimated_duration.total_seconds() < avg_duration * 0.7]
        
        # Move tests from overloaded to underloaded windows
        for overloaded_window in overloaded:
            # Sort tests by duration (move smallest first to preserve balance)
            sorted_tests = sorted(overloaded_window.tests, key=lambda t: t.effective_duration)
            
            for test in sorted_tests:
                if overloaded_window.estimated_duration.total_seconds() <= avg_duration * 1.1:
                    break  # Good enough balance
                
                # Find best underloaded window for this test
                best_window = None
                for underloaded_window in underloaded:
                    if (underloaded_window.estimated_duration + test.effective_duration).total_seconds() < avg_duration * 1.2:
                        if underloaded_window.primary_category == test.category or underloaded_window.primary_category is None:
                            best_window = underloaded_window
                            break
                
                if best_window:
                    overloaded_window.remove_test(test.name)
                    best_window.add_test(test)
                    
                    # Update underloaded list
                    if best_window.estimated_duration.total_seconds() >= avg_duration * 0.9:
                        underloaded.remove(best_window)
        
        # Update computed properties for all windows
        for window in windows:
            window._update_computed_properties()
        
        return windows
    
    def update_test_history(self, test_name: str, duration: timedelta, success: bool):
        """Update historical data for a test"""
        if test_name not in self.test_history:
            self.test_history[test_name] = {
                "run_count": 0,
                "total_duration": 0,
                "success_count": 0,
                "failure_count": 0,
                "durations": []
            }
        
        history = self.test_history[test_name]
        history["run_count"] += 1
        history["total_duration"] += duration.total_seconds()
        history["last_duration"] = duration.total_seconds()
        
        if success:
            history["success_count"] += 1
        else:
            history["failure_count"] += 1
        
        # Keep last 10 durations for variance analysis
        history["durations"].append(duration.total_seconds())
        if len(history["durations"]) > 10:
            history["durations"] = history["durations"][-10:]
        
        # Calculate derived metrics
        history["avg_duration"] = history["total_duration"] / history["run_count"]
        history["success_rate"] = history["success_count"] / history["run_count"]
        history["failure_rate"] = history["failure_count"] / history["run_count"]
        
        # Detect flaky tests
        if len(history["durations"]) >= 5:
            duration_variance = statistics.variance(history["durations"])
            if duration_variance > (history["avg_duration"] * 0.5) ** 2:
                history["flaky"] = True
        
        # Detect slow tests
        if history["avg_duration"] > 300:  # 5 minutes
            history["slow"] = True
        
        # Save updated history
        self._save_test_history()
    
    def export_windows(self, windows: List[TestExecutionWindow], output_path: Path):
        """Export windows to JSON file"""
        data = {
            "windows": [window.to_dict() for window in windows],
            "summary": {
                "total_windows": len(windows),
                "total_tests": sum(w.test_count for w in windows),
                "estimated_total_duration": sum(w.estimated_duration.total_seconds() for w in windows),
                "average_balancing_score": statistics.mean(w.balancing_score for w in windows) if windows else 0,
                "strategies_used": list(set(w.strategy_used.value for w in windows if w.strategy_used))
            },
            "created_at": datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_execution_statistics(self, windows: List[TestExecutionWindow]) -> Dict:
        """Get comprehensive statistics about the execution windows"""
        if not windows:
            return {}
        
        total_tests = sum(w.test_count for w in windows)
        total_duration = sum(w.estimated_duration.total_seconds() for w in windows)
        
        return {
            "total_windows": len(windows),
            "total_tests": total_tests,
            "average_tests_per_window": total_tests / len(windows) if windows else 0,
            "total_estimated_duration": total_duration,
            "average_window_duration": total_duration / len(windows) if windows else 0,
            "balancing_scores": {
                "average": statistics.mean(w.balancing_score for w in windows),
                "min": min(w.balancing_score for w in windows),
                "max": max(w.balancing_score for w in windows),
                "std_dev": statistics.stdev(w.balancing_score for w in windows) if len(windows) > 1 else 0
            },
            "duration_distribution": {
                "average": statistics.mean(w.estimated_duration.total_seconds() for w in windows),
                "min": min(w.estimated_duration.total_seconds() for w in windows),
                "max": max(w.estimated_duration.total_seconds() for w in windows),
                "std_dev": statistics.stdev(w.estimated_duration.total_seconds() for w in windows) if len(windows) > 1 else 0
            },
            "priorities": {
                priority.name: len([w for w in windows if w.priority == priority])
                for priority in WindowPriority
            },
            "categories": {
                category: len([w for w in windows if w.primary_category == category])
                for category in set(w.primary_category for w in windows if w.primary_category)
            },
            "parallel_safe_windows": len([w for w in windows if w.parallel_safe]),
            "windows_requiring_isolation": len([w for w in windows if w.requires_isolation])
        }