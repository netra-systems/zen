#!/usr/bin/env python
"""
Report Data Collector for Enhanced Test Reporter
Handles data collection and parsing with 8-line function limit
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

from .report_types import (
    CompleteTestMetrics, TestDetail, FailureDetail, 
    TestComponentData, CategoryMap, HistoricalData,
    create_all_categories, convert_category_to_dict
)


class TestOutputParser:
    """Parses test output from different test runners"""
    
    def __init__(self):
        self.backend_patterns = self._init_backend_patterns()
        self.frontend_patterns = self._init_frontend_patterns()
    
    def _init_backend_patterns(self) -> Dict[str, str]:
        """Initialize backend parsing patterns"""
        return {
            "file": r"(\S+\.py)::",
            "summary": r"(\d+)\s+(passed|failed|skipped|error|xfailed|xpassed)",
            "test": r"(PASSED|FAILED|SKIPPED|ERROR)\s+([^\s]+)::([\w_]+)(?:\[([^\]]+)\])?\s*(?:\(?([\d.]+)s?\))??"
        }
    
    def _init_frontend_patterns(self) -> Dict[str, str]:
        """Initialize frontend parsing patterns"""
        return {
            "file": r"(PASS|FAIL)\s+(\S+\.(test|spec)\.(ts|tsx|js|jsx))",
            "summary": r"Tests:\s+(\d+)\s+failed[,\s]+(\d+)\s+passed[,\s]+(\d+)\s+total",
            "suite": r"Test Suites:\s+(\d+)\s+failed[,\s]+(\d+)\s+passed[,\s]+(\d+)\s+total"
        }


class TestCategorizer:
    """Categorizes tests based on path and name patterns"""
    
    def __init__(self):
        self.categories = create_all_categories()
        self.category_patterns = self._init_category_patterns()
    
    def _init_category_patterns(self) -> Dict[str, List[str]]:
        """Initialize category detection patterns"""
        return {
            "unit": ["unit", "test_unit"],
            "integration": ["integration", "test_integration"],
            "e2e": ["e2e", "end_to_end", "cypress"],
            "smoke": ["smoke", "test_smoke", "health"]
        }
    
    def _init_performance_patterns(self) -> Dict[str, List[str]]:
        """Initialize performance category patterns"""
        return {
            "performance": ["performance", "perf", "benchmark"],
            "security": ["security"],
            "auth": ["auth", "permission"]
        }
    
    def _init_domain_patterns(self) -> Dict[str, List[str]]:
        """Initialize domain category patterns"""
        return {
            "api": ["api", "route", "endpoint"],
            "ui": ["ui", "component", "render"],
            "database": ["database", "db", "repository"],
            "websocket": ["websocket", "ws", "socket"]
        }
    
    def _init_specialized_patterns(self) -> Dict[str, List[str]]:
        """Initialize specialized category patterns"""
        return {
            "agent": ["agent", "supervisor", "tool"],
            "llm": ["llm", "model", "ai"]
        }


class TestMetricsCollector:
    """Collects and aggregates test metrics"""
    
    def __init__(self):
        self.parser = TestOutputParser()
        self.categorizer = TestCategorizer()
    
    def parse_test_output(self, output: str, component: str) -> TestComponentData:
        """Parse test output for a component"""
        if component == "backend":
            return self._parse_backend_output(output)
        elif component == "frontend":
            return self._parse_frontend_output(output)
        else:
            return self._create_empty_data()
    
    def _parse_backend_output(self, output: str) -> TestComponentData:
        """Parse backend pytest output"""
        metrics = CompleteTestMetrics()
        test_details = []
        failure_details = []
        
        self._extract_backend_files(output, metrics)
        self._extract_backend_summary(output, metrics)
        self._extract_backend_tests(output, test_details, failure_details)
        self._extract_coverage(output, metrics)
        
        return self._build_component_data(metrics, test_details, failure_details)
    
    def _parse_frontend_output(self, output: str) -> TestComponentData:
        """Parse frontend Jest output"""
        metrics = CompleteTestMetrics()
        test_details = []
        failure_details = []
        
        self._extract_frontend_files(output, metrics)
        self._extract_frontend_summary(output, metrics)
        
        return self._build_component_data(metrics, test_details, failure_details)


class HistoricalDataManager:
    """Manages historical test data"""
    
    def __init__(self, metrics_dir: Path):
        self.metrics_dir = metrics_dir
        self.history_file = metrics_dir / "test_history.json"
    
    def load_historical_data(self) -> HistoricalData:
        """Load historical test data"""
        if not self.history_file.exists():
            return self._create_empty_history()
        
        try:
            return self._read_history_file()
        except Exception:
            return self._create_empty_history()
    
    def _create_empty_history(self) -> HistoricalData:
        """Create empty historical data structure"""
        return {
            "runs": [],
            "flaky_tests": defaultdict(int),
            "failure_patterns": defaultdict(list),
            "performance_trends": []
        }
    
    def _read_history_file(self) -> HistoricalData:
        """Read historical data from file"""
        with open(self.history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_historical_data(self, data: HistoricalData) -> None:
        """Save historical data to file"""
        converted_data = self._convert_for_json(data)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, indent=2, default=str)
    
    def _convert_for_json(self, data: HistoricalData) -> Dict:
        """Convert defaultdict to regular dict for JSON"""
        return {
            "runs": data["runs"],
            "flaky_tests": dict(data["flaky_tests"]),
            "failure_patterns": dict(data["failure_patterns"]),
            "performance_trends": data["performance_trends"]
        }


class ChangeDetector:
    """Detects changes between test runs"""
    
    def __init__(self, historical_data: HistoricalData):
        self.historical_data = historical_data
    
    def detect_changes(self, level: str, current_metrics: Dict) -> Dict:
        """Detect changes from last run of same level"""
        last_run = self._find_last_run(level)
        if not last_run:
            return {}
        
        changes = {}
        self._detect_test_count_changes(last_run, current_metrics, changes)
        self._detect_pass_rate_changes(last_run, current_metrics, changes)
        self._detect_coverage_changes(last_run, current_metrics, changes)
        self._detect_failure_changes(last_run, changes)
        
        return changes
    
    def _find_last_run(self, level: str) -> Optional[Dict]:
        """Find last run for the specified level"""
        level_runs = [
            r for r in self.historical_data.get('runs', []) 
            if r.get('level') == level
        ]
        return level_runs[-1] if level_runs else None
    
    def _detect_test_count_changes(self, last_run: Dict, current: Dict, changes: Dict) -> None:
        """Detect changes in test count"""
        if last_run.get('total'):
            diff = current['total_tests'] - last_run['total']
            changes['tests_change'] = f"+{diff}" if diff >= 0 else str(diff)
    
    def _detect_pass_rate_changes(self, last_run: Dict, current: Dict, changes: Dict) -> None:
        """Detect changes in pass rate"""
        if not (last_run.get('passed') and current['total_tests']):
            return
        
        last_rate = last_run['passed'] / last_run['total'] * 100
        current_rate = current['passed'] / current['total_tests'] * 100
        diff = current_rate - last_rate
        changes['pass_rate_change'] = f"+{diff:.1f}%" if diff >= 0 else f"{diff:.1f}%"
    
    def _detect_coverage_changes(self, last_run: Dict, current: Dict, changes: Dict) -> None:
        """Detect changes in coverage"""
        if not (last_run.get('coverage') and current.get('coverage')):
            return
        
        diff = current['coverage'] - last_run['coverage']
        changes['coverage_change'] = f"+{diff:.1f}%" if diff >= 0 else f"{diff:.1f}%"
    
    def _detect_failure_changes(self, last_run: Dict, changes: Dict) -> None:
        """Detect new failures and fixed tests"""
        if not last_run.get('failures'):
            return
        
        last_failures = set(last_run['failures'])
        current_failures = set()  # Would need to track this
        changes['new_failures'] = list(current_failures - last_failures)
        changes['fixed_tests'] = list(last_failures - current_failures)


class CoverageExtractor:
    """Extracts test coverage information"""
    
    def __init__(self):
        self.coverage_patterns = self._init_coverage_patterns()
    
    def _init_coverage_patterns(self) -> List[str]:
        """Initialize coverage detection patterns"""
        return [
            r"TOTAL\s+\d+\s+\d+\s+([\d.]+)%",
            r"Overall coverage:\s*([\d.]+)%",
            r"Required test coverage of ([\d.]+)% reached"
        ]
    
    def extract_coverage(self, output: str) -> Optional[float]:
        """Extract coverage percentage from output"""
        for pattern in self.coverage_patterns:
            match = re.search(pattern, output)
            if match:
                return float(match.group(1))
        return None


class TestDataAggregator:
    """Aggregates test data from multiple sources"""
    
    def __init__(self):
        self.metrics_collector = TestMetricsCollector()
        self.change_detector = None
    
    def aggregate_test_data(self, results: Dict, historical_data: HistoricalData) -> Dict:
        """Aggregate test data from all components"""
        backend_data = self._parse_component_data(results, "backend")
        frontend_data = self._parse_component_data(results, "frontend")
        
        combined_metrics = self._combine_metrics(backend_data, frontend_data)
        changes = self._detect_all_changes(historical_data, combined_metrics)
        
        return {
            "backend_data": backend_data,
            "frontend_data": frontend_data,
            "combined_metrics": combined_metrics,
            "changes": changes
        }
    
    def _parse_component_data(self, results: Dict, component: str) -> TestComponentData:
        """Parse data for a single component"""
        output = results.get(component, {}).get("output", "")
        return self.metrics_collector.parse_test_output(output, component)
    
    def _combine_metrics(self, backend: TestComponentData, frontend: TestComponentData) -> Dict:
        """Combine metrics from both components"""
        return {
            "total_files": backend.metrics.total_files + frontend.metrics.total_files,
            "total_tests": backend.metrics.total_tests + frontend.metrics.total_tests,
            "passed": backend.metrics.passed + frontend.metrics.passed,
            "failed": backend.metrics.failed + frontend.metrics.failed
        }
    
    def _detect_all_changes(self, historical_data: HistoricalData, metrics: Dict) -> Dict:
        """Detect changes using historical data"""
        if not self.change_detector:
            self.change_detector = ChangeDetector(historical_data)
        return self.change_detector.detect_changes("unit", metrics)