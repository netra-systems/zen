"""
Pytest configuration for staging E2E tests.
Provides fixtures, hooks, and reporting configuration.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import os
from pathlib import Path

# Test result collector
class TestResultCollector:
    """Collects test results for reporting"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
        self.total_tests = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = 0
        
    def add_result(self, result: Dict[str, Any]):
        """Add a test result"""
        self.results.append(result)
        
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary"""
        return {
            "total": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "duration": (self.end_time - self.start_time) if self.end_time else 0,
            "pass_rate": (self.passed / self.total_tests * 100) if self.total_tests > 0 else 0
        }

# Global collector instance
collector = TestResultCollector()

# Pytest hooks
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "staging: mark test to run against staging environment"
    )
    config.addinivalue_line(
        "markers", "critical: mark test as business critical"
    )
    config.addinivalue_line(
        "markers", "high: mark test as high priority"
    )
    config.addinivalue_line(
        "markers", "medium: mark test as medium priority"
    )
    config.addinivalue_line(
        "markers", "low: mark test as low priority"
    )

def pytest_sessionstart(session):
    """Called at test session start"""
    collector.start_time = time.time()
    print("\n" + "="*70)
    print("STAGING E2E TEST SESSION STARTED")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

def pytest_sessionfinish(session, exitstatus):
    """Called at test session end"""
    collector.end_time = time.time()
    
    # Generate report
    generate_test_report()

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Capture test results"""
    outcome = yield
    report = outcome.get_result()
    
    if report.when == "call":
        result = {
            "test_name": item.name,
            "test_file": str(item.fspath),
            "outcome": report.outcome,
            "duration": report.duration,
            "timestamp": time.time()
        }
        
        # Extract markers
        markers = [mark.name for mark in item.iter_markers()]
        result["priority"] = "critical" if "critical" in markers else \
                            "high" if "high" in markers else \
                            "medium" if "medium" in markers else \
                            "low" if "low" in markers else "normal"
        
        # Add to collector
        collector.add_result(result)
        collector.total_tests += 1
        
        if report.outcome == "passed":
            collector.passed += 1
        elif report.outcome == "failed":
            collector.failed += 1
            if hasattr(report, "longrepr"):
                result["error"] = str(report.longrepr)
        elif report.outcome == "skipped":
            collector.skipped += 1

def generate_test_report():
    """Generate comprehensive test report with Windows I/O error handling"""
    
    report_path = Path("STAGING_TEST_REPORT_PYTEST.md")
    summary = collector.get_summary()
    
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Staging E2E Test Report - Pytest Results\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Environment:** Staging\n")
            f.write(f"**Test Framework:** Pytest\n\n")
            
            # Executive Summary
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Tests:** {summary['total']}\n")
            if summary['total'] > 0:
                f.write(f"- **Passed:** {summary['passed']} ({summary['passed']/summary['total']*100:.1f}%)\n")
                f.write(f"- **Failed:** {summary['failed']} ({summary['failed']/summary['total']*100:.1f}%)\n")
            else:
                f.write(f"- **Passed:** {summary['passed']} (0.0%)\n")
                f.write(f"- **Failed:** {summary['failed']} (0.0%)\n")
            f.write(f"- **Skipped:** {summary['skipped']}\n")
            f.write(f"- **Duration:** {summary['duration']:.2f} seconds\n")
            f.write(f"- **Pass Rate:** {summary['pass_rate']:.1f}%\n\n")
            
            # Test Results by Priority
            f.write("## Test Results by Priority\n\n")
            
            priorities = ["critical", "high", "medium", "low", "normal"]
            for priority in priorities:
                priority_results = [r for r in collector.results if r.get("priority") == priority]
                if priority_results:
                    f.write(f"### {priority.upper()} Priority Tests\n\n")
                    f.write("| Test Name | Status | Duration | File |\n")
                    f.write("|-----------|--------|----------|------|\n")
                    
                    for result in priority_results:
                        status_icon = "PASS" if result["outcome"] == "passed" else "FAIL" if result["outcome"] == "failed" else "SKIP"
                        f.write(f"| {result['test_name']} | {status_icon} {result['outcome']} | {result['duration']:.3f}s | {Path(result['test_file']).name} |\n")
                    f.write("\n")
            
            # Failed Tests Details
            if collector.failed > 0:
                f.write("## Failed Tests Details\n\n")
                failed_results = [r for r in collector.results if r["outcome"] == "failed"]
                
                for result in failed_results:
                    f.write(f"### FAILED: {result['test_name']}\n")
                    f.write(f"- **File:** {result['test_file']}\n")
                    f.write(f"- **Duration:** {result['duration']:.3f}s\n")
                    if "error" in result:
                        f.write(f"- **Error:** {result['error'][:500]}...\n")
                    f.write("\n")
            
            # Pytest Output Format
            f.write("## Pytest Output Format\n\n")
            f.write("```\n")
            
            # Generate pytest-style output
            for result in collector.results:
                if result["outcome"] == "passed":
                    f.write(f"{Path(result['test_file']).name}::{result['test_name']} PASSED\n")
                elif result["outcome"] == "failed":
                    f.write(f"{Path(result['test_file']).name}::{result['test_name']} FAILED\n")
                elif result["outcome"] == "skipped":
                    f.write(f"{Path(result['test_file']).name}::{result['test_name']} SKIPPED\n")
            
            f.write(f"\n{'='*50}\n")
            f.write(f"{summary['passed']} passed, {summary['failed']} failed")
            if summary['skipped'] > 0:
                f.write(f", {summary['skipped']} skipped")
            f.write(f" in {summary['duration']:.2f}s\n")
            f.write("```\n\n")
            
            # Test Coverage Matrix
            f.write("## Test Coverage Matrix\n\n")
            f.write("| Category | Total | Passed | Failed | Coverage |\n")
            f.write("|----------|-------|--------|--------|----------|\n")
            
            categories = {
                "WebSocket": ["websocket", "ws"],
                "Agent": ["agent"],
                "Authentication": ["auth", "jwt", "oauth"],
                "Performance": ["performance", "response_time", "throughput"],
                "Security": ["security", "cors", "injection"],
                "Data": ["storage", "database", "cache"]
            }
            
            for category, keywords in categories.items():
                cat_tests = [r for r in collector.results 
                            if any(kw in r["test_name"].lower() for kw in keywords)]
                if cat_tests:
                    cat_passed = sum(1 for t in cat_tests if t["outcome"] == "passed")
                    cat_failed = sum(1 for t in cat_tests if t["outcome"] == "failed")
                    coverage = (cat_passed / len(cat_tests) * 100) if cat_tests else 0
                    f.write(f"| {category} | {len(cat_tests)} | {cat_passed} | {cat_failed} | {coverage:.1f}% |\n")
            
            f.write("\n---\n")
            f.write(f"*Report generated by pytest-staging framework v1.0*\n")
    except (OSError, IOError) as e:
        print(f"Warning: Could not generate test report due to I/O error: {e}")
    
    print(f"\nTest report saved to: {report_path.absolute()}")

# Fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def staging_config():
    """Staging configuration fixture"""
    from tests.e2e.staging_test_config import get_staging_config
    return get_staging_config()

@pytest.fixture
async def staging_client():
    """HTTP client for staging API"""
    import httpx
    from tests.e2e.staging_test_config import get_staging_config
    
    config = get_staging_config()
    async with httpx.AsyncClient(base_url=config.backend_url, timeout=30) as client:
        yield client

@pytest.fixture
async def websocket_client():
    """WebSocket client for staging"""
    import websockets
    from tests.e2e.staging_test_config import get_staging_config
    
    config = get_staging_config()
    try:
        async with websockets.connect(config.websocket_url) as ws:
            yield ws
    except Exception as e:
        pytest.skip(f"WebSocket connection failed: {e}")