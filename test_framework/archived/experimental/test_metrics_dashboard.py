#!/usr/bin/env python
"""
Test Metrics Dashboard - Real-time test quality and performance monitoring.

Business Value Justification (BVJ):
1. Segment: All customer segments (Engineering Operations)
2. Business Goal: Maintain >99.9% platform reliability  
3. Value Impact: Prevents production issues that could lose 15-20% of customers
4. Revenue Impact: Protects $100K+ MRR through early issue detection

Features:
- Real-time test metrics collection
- Performance trend analysis
- Coverage tracking
- Flaky test detection
- SLA compliance monitoring
"""

import json
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path

@dataclass
class TestMetrics:
    """Strong typing for test metrics ( <= 8 lines per method)."""
    timestamp: datetime
    test_level: str
    total_tests: int
    passed_tests: int
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100
    
    @property
    def meets_sla(self) -> bool:
        """Check if metrics meet SLA requirements."""
        return self.pass_rate >= 95.0

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking ( <= 8 lines per method)."""
    test_level: str
    execution_time: float
    target_time: float
    memory_usage: Optional[float] = None
    
    @property
    def meets_performance_sla(self) -> bool:
        """Check if performance meets SLA."""
        return self.execution_time <= self.target_time
    
    @property
    def performance_score(self) -> float:
        """Calculate performance score (0-100)."""
        if self.execution_time <= self.target_time:
            return 100.0
        return max(0.0, 100.0 - ((self.execution_time - self.target_time) / self.target_time) * 50)

class TestMetricsCollector:
    """Collect and store test metrics ( <= 300 lines total)."""
    
    __test__ = False  # Tell pytest this is not a test class
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize metrics collector."""
        self.db_path = db_path or PROJECT_ROOT / "reports" / "test_metrics.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for metrics storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    test_level TEXT NOT NULL,
                    total_tests INTEGER NOT NULL,
                    passed_tests INTEGER NOT NULL,
                    failed_tests INTEGER NOT NULL,
                    execution_time REAL NOT NULL,
                    coverage_percent REAL,
                    memory_usage REAL
                )
            """)
    
    def collect_metrics(self, test_level: str = "integration") -> TestMetrics:
        """Collect current test metrics."""
        start_time = time.time()
        
        # Run tests and collect metrics
        result = self._run_test_command(test_level)
        execution_time = time.time() - start_time
        
        # Parse test results
        metrics = self._parse_test_results(result, test_level)
        
        # Store metrics in database
        self._store_metrics(metrics, execution_time)
        
        return metrics
    
    def _run_test_command(self, test_level: str) -> Dict:
        """Run test command and capture results."""
        cmd = [
            sys.executable, "test_runner.py", 
            "--level", test_level,
            "--no-coverage", "--fast-fail",
            "--report-format", "json",
            "--output", str(PROJECT_ROOT / "temp_test_results.json")
        ]
        
        try:
            result = subprocess.run(
                cmd, cwd=PROJECT_ROOT, 
                capture_output=True, text=True, timeout=600
            )
            return self._load_test_results()
        except subprocess.TimeoutExpired:
            return {"error": "Test execution timeout"}
        except Exception as e:
            return {"error": f"Test execution failed: {e}"}

class MetricsDashboard:
    """Display test metrics dashboard ( <= 300 lines total)."""
    
    def __init__(self, collector: TestMetricsCollector):
        """Initialize dashboard with metrics collector."""
        self.collector = collector
    
    def display_dashboard(self):
        """Display comprehensive test metrics dashboard."""
        print("=" * 80)
        print("NETRA AI PLATFORM - TEST METRICS DASHBOARD")
        print("=" * 80)
        
        self._display_current_metrics()
        self._display_performance_trends()
        self._display_coverage_analysis()
        self._display_sla_compliance()
    
    def _display_current_metrics(self):
        """Display current test metrics."""
        print("\nCURRENT TEST METRICS")
        print("-" * 40)
        
        # Collect metrics for key test levels
        for level in ["smoke", "unit", "integration"]:
            try:
                metrics = self.collector.collect_metrics(level)
                status = " PASS:  PASS" if metrics.meets_sla else " FAIL:  FAIL"
                print(f"{level:12} | {metrics.pass_rate:6.1f}% | {status}")
            except Exception as e:
                print(f"{level:12} | ERROR: {e}")
    
    def _display_performance_trends(self):
        """Display performance trend analysis."""
        print("\nPERFORMANCE TRENDS (Last 7 Days)")
        print("-" * 40)
        
        trends = self._get_performance_trends()
        for level, trend_data in trends.items():
            avg_time = trend_data.get('avg_execution_time', 0)
            target_time = self._get_target_time(level)
            status = " PASS: " if avg_time <= target_time else " WARNING: [U+FE0F]"
            print(f"{level:12} | {avg_time:6.1f}s | Target: {target_time}s {status}")
    
    def _get_target_time(self, level: str) -> float:
        """Get target execution time for test level."""
        targets = {
            "smoke": 30.0,
            "unit": 120.0,
            "integration": 300.0,
            "agents": 180.0,
            "comprehensive": 2700.0
        }
        return targets.get(level, 300.0)

class FlakeyTestDetector:
    """Detect and track flaky tests ( <= 300 lines total)."""
    
    def __init__(self, db_path: Path):
        """Initialize flaky test detector."""
        self.db_path = db_path
    
    def detect_flaky_tests(self, days: int = 7) -> List[Dict]:
        """Detect tests with inconsistent pass/fail patterns."""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT test_name, 
                       COUNT(*) as total_runs,
                       SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passes,
                       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failures
                FROM test_results 
                WHERE timestamp > date('now', '-{} days')
                GROUP BY test_name
                HAVING total_runs >= 3 AND failures > 0 AND passes > 0
                ORDER BY (failures * 1.0 / total_runs) DESC
            """.format(days)
            
            cursor = conn.execute(query)
            return [
                {
                    "test_name": row[0],
                    "total_runs": row[1],
                    "passes": row[2],
                    "failures": row[3],
                    "flake_rate": (row[3] / row[1]) * 100
                }
                for row in cursor.fetchall()
            ]
    
    def report_flaky_tests(self):
        """Generate flaky test report."""
        flaky_tests = self.detect_flaky_tests()
        
        if not flaky_tests:
            print(" PASS:  No flaky tests detected")
            return
        
        print(f"\n WARNING: [U+FE0F]  FLAKY TESTS DETECTED ({len(flaky_tests)})")
        print("-" * 60)
        print(f"{'Test Name':40} | {'Flake Rate':>10} | {'Runs':>5}")
        print("-" * 60)
        
        for test in flaky_tests[:10]:  # Show top 10 flaky tests
            print(f"{test['test_name'][:40]:40} | {test['flake_rate']:9.1f}% | {test['total_runs']:4d}")

def generate_daily_report():
    """Generate daily test metrics report."""
    collector = TestMetricsCollector()
    dashboard = MetricsDashboard(collector)
    detector = FlakeyTestDetector(collector.db_path)
    
    print(f"Daily Test Metrics Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    dashboard.display_dashboard()
    detector.report_flaky_tests()
    
    # Generate recommendations
    print("\nRECOMMENDations")
    print("-" * 40)
    print("[U+2022] Run 'python test_runner.py --level integration --real-llm' before releases")
    print("[U+2022] Address flaky tests to improve reliability")
    print("[U+2022] Monitor performance trends for SLA compliance")
    print("[U+2022] Maintain >95% pass rate for production readiness")

def main():
    """Main entry point for metrics dashboard."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Metrics Dashboard")
    parser.add_argument("--daily-report", action="store_true", help="Generate daily report")
    parser.add_argument("--collect", type=str, help="Collect metrics for specific test level")
    parser.add_argument("--dashboard", action="store_true", help="Show live dashboard")
    parser.add_argument("--flaky-tests", action="store_true", help="Show flaky test report")
    
    args = parser.parse_args()
    
    if args.daily_report:
        generate_daily_report()
    elif args.collect:
        collector = TestMetricsCollector()
        metrics = collector.collect_metrics(args.collect)
        print(f"Collected metrics for {args.collect}: {metrics.pass_rate:.1f}% pass rate")
    elif args.dashboard:
        collector = TestMetricsCollector()
        dashboard = MetricsDashboard(collector)
        dashboard.display_dashboard()
    elif args.flaky_tests:
        collector = TestMetricsCollector()
        detector = FlakeyTestDetector(collector.db_path)
        detector.report_flaky_tests()
    else:
        generate_daily_report()

if __name__ == "__main__":
    main()