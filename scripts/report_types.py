#!/usr/bin/env python
"""
Report Type Definitions for Enhanced Test Reporter
Data classes and type definitions following 8-line function limit
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Union
from pathlib import Path


@dataclass
class TestMetrics:
    """Comprehensive test metrics container"""
    total_files: int = 0
    total_tests: int = 0
    passed: int = 0
    failed: int = 0


@dataclass
class TestMetricsExtended(TestMetrics):
    """Extended test metrics with performance data"""
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    coverage: Optional[float] = None


@dataclass
class TestPerformanceMetrics:
    """Test performance and timing metrics"""
    avg_test_duration: float = 0.0
    slowest_tests: List[Dict] = None
    fastest_tests: List[Dict] = None
    
    def __post_init__(self):
        self._init_lists()
    
    def _init_lists(self):
        """Initialize list fields to empty lists"""
        if self.slowest_tests is None:
            self.slowest_tests = []
        if self.fastest_tests is None:
            self.fastest_tests = []


@dataclass
class TestReliabilityMetrics:
    """Test reliability and flakiness metrics"""
    flaky_tests: List[str] = None
    new_failures: List[str] = None
    fixed_tests: List[str] = None
    
    def __post_init__(self):
        self._init_lists()
    
    def _init_lists(self):
        """Initialize list fields to empty lists"""
        if self.flaky_tests is None:
            self.flaky_tests = []
        if self.new_failures is None:
            self.new_failures = []
        if self.fixed_tests is None:
            self.fixed_tests = []


@dataclass
class CompleteTestMetrics(TestMetricsExtended):
    """Complete test metrics combining all metric types"""
    performance: TestPerformanceMetrics = None
    reliability: TestReliabilityMetrics = None
    
    def __post_init__(self):
        self._init_sub_metrics()
    
    def _init_sub_metrics(self):
        """Initialize sub-metric objects"""
        if self.performance is None:
            self.performance = TestPerformanceMetrics()
        if self.reliability is None:
            self.reliability = TestReliabilityMetrics()


@dataclass
class TestCategory:
    """Test categorization data container"""
    name: str
    count: int = 0
    passed: int = 0
    failed: int = 0


@dataclass
class TestCategoryExtended(TestCategory):
    """Extended test category with timing and file data"""
    duration: float = 0.0
    files: List[str] = None
    
    def __post_init__(self):
        self._init_files()
    
    def _init_files(self):
        """Initialize files list to empty list"""
        if self.files is None:
            self.files = []


@dataclass
class TestDetail:
    """Individual test execution details"""
    file: str
    name: str
    status: str
    duration: float
    category: str


@dataclass
class FailureDetail:
    """Test failure details"""
    test: str
    category: str
    error_message: Optional[str] = None


@dataclass
class TestComponentData:
    """Complete test data for a component (backend/frontend)"""
    metrics: CompleteTestMetrics
    test_details: List[TestDetail]
    failure_details: List[FailureDetail]
    categories: Dict[str, Dict]


@dataclass
class HistoricalRun:
    """Historical test run data"""
    timestamp: str
    level: str
    total: int
    passed: int
    failed: int


@dataclass
class HistoricalRunExtended(HistoricalRun):
    """Extended historical run with coverage and duration"""
    coverage: Optional[float] = None
    duration: float = 0.0
    failures: List[str] = None
    
    def __post_init__(self):
        self._init_failures()
    
    def _init_failures(self):
        """Initialize failures list to empty list"""
        if self.failures is None:
            self.failures = []


@dataclass
class ReportConfiguration:
    """Test report configuration"""
    level: str
    description: str
    parallel: Union[str, bool] = 'default'
    run_coverage: bool = False


@dataclass
class ReportConfigurationExtended(ReportConfiguration):
    """Extended report configuration with timing"""
    timeout: int = 300
    backend_args: List[str] = None
    frontend_args: List[str] = None
    
    def __post_init__(self):
        self._init_args()
    
    def _init_args(self):
        """Initialize argument lists to empty lists"""
        if self.backend_args is None:
            self.backend_args = []
        if self.frontend_args is None:
            self.frontend_args = []


@dataclass
class ChangeDetection:
    """Change detection between test runs"""
    tests_change: str = "N/A"
    pass_rate_change: str = "N/A"
    coverage_change: str = "N/A"
    files_change: str = "N/A"


@dataclass
class ChangeDetectionExtended(ChangeDetection):
    """Extended change detection with reliability data"""
    duration_change: str = "N/A"
    new_failures: List[str] = None
    fixed_tests: List[str] = None
    flaky_tests: List[str] = None
    
    def __post_init__(self):
        self._init_changes()
    
    def _init_changes(self):
        """Initialize change lists to empty lists"""
        if self.new_failures is None:
            self.new_failures = []
        if self.fixed_tests is None:
            self.fixed_tests = []
        if self.flaky_tests is None:
            self.flaky_tests = []


@dataclass
class ReportDirectories:
    """Report directory structure"""
    reports_dir: Path
    latest_dir: Path
    history_dir: Path
    metrics_dir: Path


@dataclass
class ReportDirectoriesExtended(ReportDirectories):
    """Extended report directories with analysis"""
    analysis_dir: Path


# Type aliases for clarity
TestResults = Dict[str, Any]
CategoryMap = Dict[str, TestCategoryExtended]
HistoricalData = Dict[str, Any]
ReportContent = str


def create_default_categories() -> CategoryMap:
    """Create default test categories mapping"""
    categories = {
        "unit": TestCategoryExtended("Unit Tests"),
        "integration": TestCategoryExtended("Integration Tests"),
        "e2e": TestCategoryExtended("End-to-End Tests"),
        "smoke": TestCategoryExtended("Smoke Tests"),
    }
    return categories


def create_performance_categories() -> CategoryMap:
    """Create performance-focused test categories"""
    categories = {
        "performance": TestCategoryExtended("Performance Tests"),
        "security": TestCategoryExtended("Security Tests"),
        "api": TestCategoryExtended("API Tests"),
        "ui": TestCategoryExtended("UI Tests"),
    }
    return categories


def create_domain_categories() -> CategoryMap:
    """Create domain-specific test categories"""
    categories = {
        "database": TestCategoryExtended("Database Tests"),
        "websocket": TestCategoryExtended("WebSocket Tests"),
        "auth": TestCategoryExtended("Authentication Tests"),
        "agent": TestCategoryExtended("Agent Tests"),
    }
    return categories


def create_specialized_categories() -> CategoryMap:
    """Create specialized test categories"""
    categories = {
        "llm": TestCategoryExtended("LLM Tests"),
        "other": TestCategoryExtended("Other Tests"),
    }
    return categories


def create_all_categories() -> CategoryMap:
    """Create complete test categories mapping"""
    all_categories = {}
    all_categories.update(create_default_categories())
    all_categories.update(create_performance_categories())
    all_categories.update(create_domain_categories())
    all_categories.update(create_specialized_categories())
    return all_categories


def convert_category_to_dict(category: TestCategoryExtended) -> Dict:
    """Convert test category to dictionary format"""
    return asdict(category)


def convert_metrics_to_dict(metrics: CompleteTestMetrics) -> Dict:
    """Convert test metrics to dictionary format"""
    return asdict(metrics)