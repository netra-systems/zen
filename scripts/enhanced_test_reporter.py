#!/usr/bin/env python
"""
Enhanced Test Reporter for Netra AI Platform
Provides comprehensive test reporting with improved organization and metrics
"""

import os
import sys
import json
import time
import re
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict, Counter
import hashlib
from dataclasses import dataclass, asdict
import difflib

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

@dataclass
class TestMetrics:
    """Comprehensive test metrics"""
    total_files: int = 0
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    coverage: Optional[float] = None
    avg_test_duration: float = 0.0
    slowest_tests: List[Dict] = None
    fastest_tests: List[Dict] = None
    flaky_tests: List[str] = None
    new_failures: List[str] = None
    fixed_tests: List[str] = None
    
    def __post_init__(self):
        if self.slowest_tests is None:
            self.slowest_tests = []
        if self.fastest_tests is None:
            self.fastest_tests = []
        if self.flaky_tests is None:
            self.flaky_tests = []
        if self.new_failures is None:
            self.new_failures = []
        if self.fixed_tests is None:
            self.fixed_tests = []

@dataclass
class TestCategory:
    """Test categorization data"""
    name: str
    count: int = 0
    passed: int = 0
    failed: int = 0
    duration: float = 0.0
    files: List[str] = None
    
    def __post_init__(self):
        if self.files is None:
            self.files = []

class EnhancedTestReporter:
    """Enhanced test reporting with comprehensive metrics and organization"""
    
    def __init__(self, reports_dir: Path = None):
        self.reports_dir = reports_dir or PROJECT_ROOT / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Organized directory structure
        self.latest_dir = self.reports_dir / "latest"
        self.history_dir = self.reports_dir / "history"
        self.metrics_dir = self.reports_dir / "metrics"
        self.analysis_dir = self.reports_dir / "analysis"
        
        # Create all directories
        for dir_path in [self.latest_dir, self.history_dir, self.metrics_dir, self.analysis_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Test categories
        self.categories = {
            "unit": TestCategory("Unit Tests"),
            "integration": TestCategory("Integration Tests"),
            "e2e": TestCategory("End-to-End Tests"),
            "smoke": TestCategory("Smoke Tests"),
            "performance": TestCategory("Performance Tests"),
            "security": TestCategory("Security Tests"),
            "api": TestCategory("API Tests"),
            "ui": TestCategory("UI Tests"),
            "database": TestCategory("Database Tests"),
            "websocket": TestCategory("WebSocket Tests"),
            "auth": TestCategory("Authentication Tests"),
            "agent": TestCategory("Agent Tests"),
            "llm": TestCategory("LLM Tests"),
            "other": TestCategory("Other Tests")
        }
        
        # Historical data
        self.historical_data = self.load_historical_data()
        
    def load_historical_data(self) -> Dict:
        """Load historical test data for comparison"""
        history_file = self.metrics_dir / "test_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "runs": [],
            "flaky_tests": defaultdict(int),
            "failure_patterns": defaultdict(list),
            "performance_trends": []
        }
    
    def save_historical_data(self):
        """Save historical data"""
        history_file = self.metrics_dir / "test_history.json"
        with open(history_file, 'w', encoding='utf-8') as f:
            # Convert defaultdict to regular dict for JSON serialization
            data = {
                "runs": self.historical_data["runs"],
                "flaky_tests": dict(self.historical_data["flaky_tests"]),
                "failure_patterns": dict(self.historical_data["failure_patterns"]),
                "performance_trends": self.historical_data["performance_trends"]
            }
            json.dump(data, f, indent=2, default=str)
    
    def categorize_test(self, test_path: str, test_name: str = "") -> str:
        """Intelligently categorize a test based on path and name"""
        path_lower = test_path.lower()
        name_lower = test_name.lower()
        combined = f"{path_lower} {name_lower}"
        
        # Check for specific categories
        if "unit" in combined or "test_unit" in combined:
            return "unit"
        elif "integration" in combined or "test_integration" in combined:
            return "integration"
        elif "e2e" in combined or "end_to_end" in combined or "cypress" in combined:
            return "e2e"
        elif "smoke" in combined or "test_smoke" in combined or "health" in combined:
            return "smoke"
        elif "performance" in combined or "perf" in combined or "benchmark" in combined:
            return "performance"
        elif "security" in combined or "auth" in combined or "permission" in combined:
            return "security" if "security" in combined else "auth"
        elif "api" in combined or "route" in combined or "endpoint" in combined:
            return "api"
        elif "ui" in combined or "component" in combined or "render" in combined:
            return "ui"
        elif "database" in combined or "db" in combined or "repository" in combined:
            return "database"
        elif "websocket" in combined or "ws" in combined or "socket" in combined:
            return "websocket"
        elif "agent" in combined or "supervisor" in combined or "tool" in combined:
            return "agent"
        elif "llm" in combined or "model" in combined or "ai" in combined:
            return "llm"
        else:
            return "other"
    
    def parse_test_output(self, output: str, component: str) -> Dict:
        """Enhanced parsing of test output with detailed metrics"""
        metrics = TestMetrics()
        test_details = []
        failure_details = []
        
        # Parse pytest output for backend
        if component == "backend":
            # Count test files
            file_pattern = r"(\S+\.py)::"
            test_files = set(re.findall(file_pattern, output))
            metrics.total_files = len(test_files)
            
            # Parse test counts
            summary_pattern = r"(\d+)\s+(passed|failed|skipped|error|xfailed|xpassed)"
            for match in re.finditer(summary_pattern, output):
                count = int(match.group(1))
                status = match.group(2)
                if status == "passed" or status == "xpassed":
                    metrics.passed += count
                elif status == "failed":
                    metrics.failed += count
                elif status == "skipped" or status == "xfailed":
                    metrics.skipped += count
                elif status == "error":
                    metrics.errors += count
            
            # Parse individual test results with timing
            test_pattern = r"(PASSED|FAILED|SKIPPED|ERROR)\s+([^\s]+)::([\w_]+)(?:\[([^\]]+)\])?\s*(?:\(?([\d.]+)s?\)?)??"
            for match in re.finditer(test_pattern, output):
                status = match.group(1)
                file_path = match.group(2)
                test_name = match.group(3)
                params = match.group(4) or ""
                duration = float(match.group(5) or 0) if match.group(5) else 0
                
                full_test_name = f"{test_name}[{params}]" if params else test_name
                category = self.categorize_test(file_path, test_name)
                
                test_detail = {
                    "file": file_path,
                    "name": full_test_name,
                    "status": status.lower(),
                    "duration": duration,
                    "category": category
                }
                test_details.append(test_detail)
                
                # Track failures
                if status == "FAILED":
                    failure_details.append({
                        "test": f"{file_path}::{full_test_name}",
                        "category": category
                    })
            
            # Parse coverage
            coverage_patterns = [
                r"TOTAL\s+\d+\s+\d+\s+([\d.]+)%",
                r"Overall coverage:\s*([\d.]+)%",
                r"Required test coverage of ([\d.]+)% reached"
            ]
            for pattern in coverage_patterns:
                match = re.search(pattern, output)
                if match:
                    metrics.coverage = float(match.group(1))
                    break
        
        # Parse Jest/frontend output
        elif component == "frontend":
            # Count test files
            file_pattern = r"(PASS|FAIL)\s+(\S+\.(test|spec)\.(ts|tsx|js|jsx))"
            for match in re.finditer(file_pattern, output):
                test_files.add(match.group(2))
            metrics.total_files = len(test_files) if test_files else 0
            
            # Parse test counts
            test_summary = re.search(r"Tests:\s+(\d+)\s+failed[,\s]+(\d+)\s+passed[,\s]+(\d+)\s+total", output)
            if test_summary:
                metrics.failed = int(test_summary.group(1))
                metrics.passed = int(test_summary.group(2))
                metrics.total_tests = int(test_summary.group(3))
            
            # Parse test suites
            suite_pattern = r"Test Suites:\s+(\d+)\s+failed[,\s]+(\d+)\s+passed[,\s]+(\d+)\s+total"
            suite_match = re.search(suite_pattern, output)
            if suite_match:
                metrics.total_files = int(suite_match.group(3))
        
        # Calculate total tests
        metrics.total_tests = metrics.passed + metrics.failed + metrics.skipped + metrics.errors
        
        # Calculate average duration if we have test details
        if test_details:
            durations = [t["duration"] for t in test_details if t["duration"] > 0]
            if durations:
                metrics.avg_test_duration = sum(durations) / len(durations)
                sorted_tests = sorted(test_details, key=lambda x: x["duration"], reverse=True)
                metrics.slowest_tests = sorted_tests[:5]
                metrics.fastest_tests = sorted_tests[-5:] if len(sorted_tests) > 5 else []
        
        # Update categories
        for test in test_details:
            cat = self.categories[test["category"]]
            cat.count += 1
            if test["status"] == "passed":
                cat.passed += 1
            elif test["status"] == "failed":
                cat.failed += 1
            cat.duration += test["duration"]
            if test["file"] not in cat.files:
                cat.files.append(test["file"])
        
        return {
            "metrics": metrics,
            "test_details": test_details,
            "failure_details": failure_details,
            "categories": {k: asdict(v) for k, v in self.categories.items() if v.count > 0}
        }
    
    def generate_comprehensive_report(self, 
                                     level: str,
                                     results: Dict,
                                     config: Dict,
                                     exit_code: int) -> str:
        """Generate comprehensive markdown report with all metrics"""
        
        timestamp = datetime.now()
        
        # Parse detailed metrics
        backend_data = self.parse_test_output(
            results["backend"].get("output", ""), "backend"
        )
        frontend_data = self.parse_test_output(
            results["frontend"].get("output", ""), "frontend"
        )
        
        # Combine metrics
        total_files = backend_data["metrics"].total_files + frontend_data["metrics"].total_files
        total_tests = backend_data["metrics"].total_tests + frontend_data["metrics"].total_tests
        total_passed = backend_data["metrics"].passed + frontend_data["metrics"].passed
        total_failed = backend_data["metrics"].failed + frontend_data["metrics"].failed
        total_skipped = backend_data["metrics"].skipped + frontend_data["metrics"].skipped
        total_errors = backend_data["metrics"].errors + frontend_data["metrics"].errors
        
        # Calculate overall coverage
        overall_coverage = None
        if backend_data["metrics"].coverage or frontend_data["metrics"].coverage:
            if backend_data["metrics"].coverage and frontend_data["metrics"].coverage:
                overall_coverage = (backend_data["metrics"].coverage + frontend_data["metrics"].coverage) / 2
            else:
                overall_coverage = backend_data["metrics"].coverage or frontend_data["metrics"].coverage
        
        # Detect changes from last run
        changes = self.detect_changes(level, {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "coverage": overall_coverage
        })
        
        # Generate report
        report = f"""# 📊 Netra AI Platform - Comprehensive Test Report

## 🎯 Executive Summary

**Generated:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}  
**Test Level:** `{level}` - {config.get('description', 'N/A')}  
**Overall Status:** {"✅ PASSED" if exit_code == 0 else "❌ FAILED"}

### 📈 Key Metrics

| Metric | Value | Change | Trend |
|--------|-------|--------|-------|
| **Total Test Files** | {total_files} | {changes.get('files_change', 'N/A')} | {self.get_trend_icon(changes.get('files_change', '0'))} |
| **Total Tests** | {total_tests} | {changes.get('tests_change', 'N/A')} | {self.get_trend_icon(changes.get('tests_change', '0'))} |
| **Pass Rate** | {(total_passed/total_tests*100 if total_tests else 0):.1f}% | {changes.get('pass_rate_change', 'N/A')} | {self.get_trend_icon(changes.get('pass_rate_change', '0'))} |
| **Coverage** | {f"{overall_coverage:.1f}%" if overall_coverage else "N/A"} | {changes.get('coverage_change', 'N/A')} | {self.get_trend_icon(changes.get('coverage_change', '0'))} |
| **Duration** | {self.format_duration(results['backend']['duration'] + results['frontend']['duration'])} | {changes.get('duration_change', 'N/A')} | {self.get_trend_icon(changes.get('duration_change', '0'), reverse=True)} |

## 📊 Test Results Overview

### Summary Statistics

| Status | Count | Percentage | Visual |
|--------|-------|------------|--------|
| ✅ **Passed** | {total_passed} | {(total_passed/total_tests*100 if total_tests else 0):.1f}% | {self.generate_bar(total_passed, total_tests, '🟩')} |
| ❌ **Failed** | {total_failed} | {(total_failed/total_tests*100 if total_tests else 0):.1f}% | {self.generate_bar(total_failed, total_tests, '🟥')} |
| ⏭️ **Skipped** | {total_skipped} | {(total_skipped/total_tests*100 if total_tests else 0):.1f}% | {self.generate_bar(total_skipped, total_tests, '🟨')} |
| 🔥 **Errors** | {total_errors} | {(total_errors/total_tests*100 if total_tests else 0):.1f}% | {self.generate_bar(total_errors, total_tests, '🟧')} |

### Component Breakdown

| Component | Files | Tests | Passed | Failed | Coverage | Duration | Status |
|-----------|-------|-------|--------|--------|----------|----------|--------|
| **Backend** | {backend_data['metrics'].total_files} | {backend_data['metrics'].total_tests} | {backend_data['metrics'].passed} | {backend_data['metrics'].failed} | {f"{backend_data['metrics'].coverage:.1f}%" if backend_data['metrics'].coverage else "N/A"} | {self.format_duration(results['backend']['duration'])} | {self.get_status_badge(results['backend']['status'])} |
| **Frontend** | {frontend_data['metrics'].total_files} | {frontend_data['metrics'].total_tests} | {frontend_data['metrics'].passed} | {frontend_data['metrics'].failed} | {f"{frontend_data['metrics'].coverage:.1f}%" if frontend_data['metrics'].coverage else "N/A"} | {self.format_duration(results['frontend']['duration'])} | {self.get_status_badge(results['frontend']['status'])} |

## 🏷️ Test Categories

{self.generate_category_table(backend_data['categories'], frontend_data['categories'])}

## 🔄 Change Detection

{self.generate_change_summary(changes)}

## ⚡ Performance Analysis

### Test Speed Distribution

{self.generate_speed_analysis(backend_data, frontend_data)}

### Top 5 Slowest Tests

{self.generate_slowest_tests_table(backend_data['metrics'].slowest_tests + frontend_data['metrics'].slowest_tests)}

## 🐛 Failure Analysis

{self.generate_failure_analysis(backend_data['failure_details'] + frontend_data['failure_details'])}

## 📈 Historical Trends

{self.generate_historical_trends(level)}

## 🔧 Environment Configuration

- **Test Level:** `{level}`
- **Parallelization:** {config.get('parallel', 'default')}
- **Coverage Enabled:** {config.get('run_coverage', False)}
- **Timeout:** {config.get('timeout', 300)}s
- **Exit Code:** {exit_code}

### Command Configuration

**Backend:** `{' '.join(config.get('backend_args', []))}`  
**Frontend:** `{' '.join(config.get('frontend_args', []))}`

## 📝 Recommendations

{self.generate_recommendations(backend_data, frontend_data, overall_coverage)}

---
*Generated by Enhanced Test Reporter v2.0 | {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return report
    
    def get_trend_icon(self, change: str, reverse: bool = False) -> str:
        """Get trend icon based on change value"""
        if change == "N/A" or change == "0":
            return "➖"
        
        try:
            value = float(change.replace('+', '').replace('%', ''))
            if reverse:  # For metrics where decrease is good (like duration)
                if value > 0:
                    return "📉"  # Good
                else:
                    return "📈"  # Bad
            else:  # For metrics where increase is good
                if value > 0:
                    return "📈"  # Good
                else:
                    return "📉"  # Bad
        except:
            return "➖"
    
    def generate_bar(self, value: int, total: int, symbol: str) -> str:
        """Generate visual bar for percentages"""
        if total == 0:
            return ""
        percentage = value / total
        bar_length = int(percentage * 20)
        return symbol * bar_length if bar_length > 0 else ""
    
    def get_status_badge(self, status: str) -> str:
        """Get status badge with emoji"""
        status_map = {
            "passed": "✅ PASSED",
            "failed": "❌ FAILED",
            "timeout": "⏱️ TIMEOUT",
            "skipped": "⏭️ SKIPPED",
            "pending": "⏳ PENDING"
        }
        return status_map.get(status, "❓ UNKNOWN")
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.2f}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{int(minutes)}m {secs:.1f}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{int(hours)}h {int(minutes)}m"
    
    def generate_category_table(self, backend_cats: Dict, frontend_cats: Dict) -> str:
        """Generate test category breakdown table"""
        all_categories = set(backend_cats.keys()) | set(frontend_cats.keys())
        
        if not all_categories:
            return "*No category data available*"
        
        table = "| Category | Backend | Frontend | Total | Pass Rate |\n"
        table += "|----------|---------|----------|-------|----------|\n"
        
        for cat in sorted(all_categories):
            b_data = backend_cats.get(cat, {})
            f_data = frontend_cats.get(cat, {})
            
            b_count = b_data.get('count', 0)
            f_count = f_data.get('count', 0)
            total = b_count + f_count
            
            b_passed = b_data.get('passed', 0)
            f_passed = f_data.get('passed', 0)
            total_passed = b_passed + f_passed
            
            pass_rate = (total_passed / total * 100) if total > 0 else 0
            
            table += f"| **{cat.title()}** | {b_count} | {f_count} | {total} | {pass_rate:.1f}% |\n"
        
        return table
    
    def generate_change_summary(self, changes: Dict) -> str:
        """Generate change summary section"""
        if not changes or all(v == "N/A" for v in changes.values()):
            return "*First run or no historical data available*"
        
        summary = ""
        
        # New failures
        if changes.get('new_failures'):
            summary += f"### 🆕 New Failures ({len(changes['new_failures'])})\n\n"
            for failure in changes['new_failures'][:10]:
                summary += f"- `{failure}`\n"
            if len(changes['new_failures']) > 10:
                summary += f"- *... and {len(changes['new_failures']) - 10} more*\n"
            summary += "\n"
        
        # Fixed tests
        if changes.get('fixed_tests'):
            summary += f"### ✅ Fixed Tests ({len(changes['fixed_tests'])})\n\n"
            for fixed in changes['fixed_tests'][:10]:
                summary += f"- `{fixed}`\n"
            if len(changes['fixed_tests']) > 10:
                summary += f"- *... and {len(changes['fixed_tests']) - 10} more*\n"
            summary += "\n"
        
        # Flaky tests
        if changes.get('flaky_tests'):
            summary += f"### 🎲 Flaky Tests Detected ({len(changes['flaky_tests'])})\n\n"
            for flaky in changes['flaky_tests'][:5]:
                summary += f"- `{flaky}`\n"
            summary += "\n"
        
        return summary if summary else "*No significant changes detected*"
    
    def generate_speed_analysis(self, backend_data: Dict, frontend_data: Dict) -> str:
        """Generate test speed analysis"""
        all_tests = backend_data.get('test_details', []) + frontend_data.get('test_details', [])
        
        if not all_tests:
            return "*No timing data available*"
        
        durations = [t['duration'] for t in all_tests if t.get('duration', 0) > 0]
        
        if not durations:
            return "*No timing data available*"
        
        # Calculate percentiles
        durations.sort()
        p50 = durations[len(durations) // 2]
        p95 = durations[int(len(durations) * 0.95)] if len(durations) > 20 else durations[-1]
        p99 = durations[int(len(durations) * 0.99)] if len(durations) > 100 else durations[-1]
        
        return f"""
| Metric | Value |
|--------|-------|
| **Median (P50)** | {p50:.3f}s |
| **P95** | {p95:.3f}s |
| **P99** | {p99:.3f}s |
| **Min** | {min(durations):.3f}s |
| **Max** | {max(durations):.3f}s |
| **Average** | {sum(durations)/len(durations):.3f}s |
"""
    
    def generate_slowest_tests_table(self, slowest_tests: List[Dict]) -> str:
        """Generate table of slowest tests"""
        if not slowest_tests:
            return "*No timing data available*"
        
        # Sort and take top 5
        slowest = sorted(slowest_tests, key=lambda x: x.get('duration', 0), reverse=True)[:5]
        
        table = "| Test | Category | Duration |\n"
        table += "|------|----------|----------|\n"
        
        for test in slowest:
            name = f"{test['file']}::{test['name']}"
            if len(name) > 60:
                name = name[:57] + "..."
            table += f"| `{name}` | {test['category']} | {test['duration']:.2f}s |\n"
        
        return table
    
    def generate_failure_analysis(self, failures: List[Dict]) -> str:
        """Generate failure analysis section"""
        if not failures:
            return "✅ **No failures detected!**"
        
        # Group failures by category
        by_category = defaultdict(list)
        for failure in failures:
            by_category[failure.get('category', 'other')].append(failure['test'])
        
        analysis = f"### Total Failures: {len(failures)}\n\n"
        
        analysis += "### Failures by Category\n\n"
        analysis += "| Category | Count | Tests |\n"
        analysis += "|----------|-------|-------|\n"
        
        for category, tests in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True):
            test_list = ", ".join([f"`{t.split('::')[-1][:20]}`" for t in tests[:3]])
            if len(tests) > 3:
                test_list += f" +{len(tests)-3} more"
            analysis += f"| **{category.title()}** | {len(tests)} | {test_list} |\n"
        
        return analysis
    
    def generate_historical_trends(self, level: str) -> str:
        """Generate historical trends section"""
        if not self.historical_data.get('runs'):
            return "*No historical data available*"
        
        # Get last 5 runs for this level
        level_runs = [r for r in self.historical_data['runs'][-10:] if r.get('level') == level]
        
        if len(level_runs) < 2:
            return "*Insufficient historical data for trends*"
        
        table = "| Date | Tests | Pass Rate | Coverage | Duration |\n"
        table += "|------|-------|-----------|----------|----------|\n"
        
        for run in level_runs[-5:]:
            date = datetime.fromisoformat(run['timestamp']).strftime('%m/%d %H:%M')
            pass_rate = (run['passed'] / run['total'] * 100) if run['total'] else 0
            coverage = f"{run['coverage']:.1f}%" if run.get('coverage') else "N/A"
            duration = self.format_duration(run['duration'])
            table += f"| {date} | {run['total']} | {pass_rate:.1f}% | {coverage} | {duration} |\n"
        
        return table
    
    def generate_recommendations(self, backend_data: Dict, frontend_data: Dict, coverage: Optional[float]) -> str:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Coverage recommendations
        if coverage:
            if coverage < 70:
                recommendations.append("🔴 **Critical:** Coverage is below 70%. Focus on adding unit tests for uncovered code.")
            elif coverage < 85:
                recommendations.append("🟡 **Important:** Coverage is below 85%. Consider adding more integration tests.")
            elif coverage < 95:
                recommendations.append("🟢 **Good:** Coverage is good but can be improved. Target 95% for critical paths.")
        
        # Failure recommendations
        total_failures = backend_data['metrics'].failed + frontend_data['metrics'].failed
        if total_failures > 20:
            recommendations.append("🔴 **Critical:** High failure count. Prioritize fixing failing tests.")
        elif total_failures > 10:
            recommendations.append("🟡 **Important:** Moderate failures detected. Schedule test fix session.")
        
        # Performance recommendations
        all_tests = backend_data.get('test_details', []) + frontend_data.get('test_details', [])
        slow_tests = [t for t in all_tests if t.get('duration', 0) > 5]
        if len(slow_tests) > 5:
            recommendations.append(f"⚡ **Performance:** {len(slow_tests)} tests take >5s. Consider optimization or parallelization.")
        
        # Flaky test recommendations
        if self.historical_data.get('flaky_tests'):
            flaky_count = len([t for t, count in self.historical_data['flaky_tests'].items() if count > 2])
            if flaky_count > 0:
                recommendations.append(f"🎲 **Reliability:** {flaky_count} flaky tests detected. Investigate and fix.")
        
        if not recommendations:
            recommendations.append("✅ **Excellent:** Test suite is in good shape. Keep up the good work!")
        
        return "\n".join([f"- {r}" for r in recommendations])
    
    def detect_changes(self, level: str, current_metrics: Dict) -> Dict:
        """Detect changes from last run"""
        changes = {}
        
        # Find last run for this level
        level_runs = [r for r in self.historical_data.get('runs', []) if r.get('level') == level]
        
        if not level_runs:
            return changes
        
        last_run = level_runs[-1]
        
        # Calculate changes
        if last_run.get('total'):
            test_diff = current_metrics['total_tests'] - last_run['total']
            changes['tests_change'] = f"+{test_diff}" if test_diff >= 0 else str(test_diff)
        
        if last_run.get('passed') and current_metrics['total_tests']:
            last_pass_rate = last_run['passed'] / last_run['total'] * 100
            current_pass_rate = current_metrics['passed'] / current_metrics['total_tests'] * 100
            diff = current_pass_rate - last_pass_rate
            changes['pass_rate_change'] = f"+{diff:.1f}%" if diff >= 0 else f"{diff:.1f}%"
        
        if last_run.get('coverage') and current_metrics.get('coverage'):
            cov_diff = current_metrics['coverage'] - last_run['coverage']
            changes['coverage_change'] = f"+{cov_diff:.1f}%" if cov_diff >= 0 else f"{cov_diff:.1f}%"
        
        # Detect new failures and fixed tests
        if last_run.get('failures'):
            last_failures = set(last_run['failures'])
            current_failures = set()  # Would need to track this
            changes['new_failures'] = list(current_failures - last_failures)
            changes['fixed_tests'] = list(last_failures - current_failures)
        
        return changes
    
    def save_report(self, level: str, report_content: str, results: Dict, metrics: Dict):
        """Save report with proper organization"""
        timestamp = datetime.now()
        
        # Save latest report (overwrite)
        latest_file = self.latest_dir / f"{level}_report.md"
        with open(latest_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # Archive previous if exists
        if latest_file.exists():
            archive_name = f"{level}_report_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
            archive_path = self.history_dir / archive_name
            # Don't move, just copy for history
            shutil.copy2(latest_file, archive_path)
        
        # Save metrics JSON
        metrics_file = self.metrics_dir / f"{level}_metrics.json"
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": timestamp.isoformat(),
                "level": level,
                "metrics": metrics,
                "results": results
            }, f, indent=2, default=str)
        
        # Update historical data
        self.historical_data['runs'].append({
            "timestamp": timestamp.isoformat(),
            "level": level,
            "total": metrics.get('total_tests', 0),
            "passed": metrics.get('passed', 0),
            "failed": metrics.get('failed', 0),
            "coverage": metrics.get('coverage'),
            "duration": results.get('duration', 0)
        })
        
        # Keep only last 100 runs
        if len(self.historical_data['runs']) > 100:
            self.historical_data['runs'] = self.historical_data['runs'][-100:]
        
        self.save_historical_data()
        
        print(f"\n📊 Report saved:")
        print(f"  📄 Latest: {latest_file}")
        print(f"  📈 Metrics: {metrics_file}")
        print(f"  📁 History: {self.history_dir}")
    
    def cleanup_old_reports(self, keep_days: int = 30):
        """Clean up old reports and organize directory structure"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        # Clean up old history files
        for file in self.history_dir.glob("*.md"):
            # Parse timestamp from filename
            try:
                timestamp_str = file.stem.split('_')[-2] + '_' + file.stem.split('_')[-1]
                file_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                if file_date < cutoff_date:
                    file.unlink()
                    print(f"  🗑️ Deleted old report: {file.name}")
            except:
                pass
        
        # Clean up root test_reports directory (move misplaced files)
        for file in self.reports_dir.glob("test_report_*.md"):
            # Move to history
            archive_path = self.history_dir / file.name
            shutil.move(str(file), str(archive_path))
            print(f"  📦 Archived: {file.name}")
        
        for file in self.reports_dir.glob("test_report_*.json"):
            # Delete old JSON files (we have better metrics now)
            file.unlink()
            print(f"  🗑️ Deleted old JSON: {file.name}")
        
        print("✅ Cleanup complete!")


def main():
    """Test the enhanced reporter"""
    reporter = EnhancedTestReporter()
    
    # Example usage
    print("Enhanced Test Reporter initialized")
    print(f"Reports directory: {reporter.reports_dir}")
    print(f"Latest reports: {reporter.latest_dir}")
    print(f"Metrics: {reporter.metrics_dir}")
    
    # Run cleanup
    print("\nRunning cleanup...")
    reporter.cleanup_old_reports()


if __name__ == "__main__":
    main()