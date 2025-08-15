#!/usr/bin/env python
"""
Enhanced Real Service Test Runner with Comprehensive Reporting

This script runs real service tests with detailed metrics collection and reporting:
- Tracks LLM API calls and costs
- Monitors database query performance
- Measures cache effectiveness
- Generates quality score reports
- Creates detailed HTML/JSON reports
"""

import os
import sys
import json
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class RealServiceTestMetrics:
    """Tracks metrics for real service tests"""
    
    def __init__(self):
        self.metrics = {
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration": 0,
            "llm_calls": defaultdict(int),
            "llm_costs": defaultdict(float),
            "db_queries": defaultdict(int),
            "cache_stats": {"hits": 0, "misses": 0, "hit_rate": 0},
            "quality_scores": [],
            "test_results": defaultdict(list),
            "errors": [],
            "warnings": []
        }
        
        # LLM pricing (per 1K tokens)
        self.llm_pricing = {
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "gemini-1.5-flash": {"input": 0.00035, "output": 0.0007},
            "gemini-2.5-pro": {"input": 0.0035, "output": 0.007}
        }
    
    def track_llm_call(self, model: str, tokens: int, call_type: str = "input"):
        """Track an LLM API call"""
        self.metrics["llm_calls"][model] += 1
        
        if model in self.llm_pricing:
            cost = (tokens / 1000) * self.llm_pricing[model][call_type]
            self.metrics["llm_costs"][model] += cost
    
    def track_db_query(self, db_type: str, duration: float):
        """Track a database query"""
        self.metrics["db_queries"][db_type] += 1
        if "db_latencies" not in self.metrics:
            self.metrics["db_latencies"] = defaultdict(list)
        self.metrics["db_latencies"][db_type].append(duration)
    
    def track_cache(self, hit: bool):
        """Track cache hit/miss"""
        if hit:
            self.metrics["cache_stats"]["hits"] += 1
        else:
            self.metrics["cache_stats"]["misses"] += 1
        
        total = self.metrics["cache_stats"]["hits"] + self.metrics["cache_stats"]["misses"]
        if total > 0:
            self.metrics["cache_stats"]["hit_rate"] = self.metrics["cache_stats"]["hits"] / total
    
    def track_quality_score(self, score: float, test_name: str):
        """Track quality gate score"""
        self.metrics["quality_scores"].append({
            "test": test_name,
            "score": score,
            "timestamp": datetime.now().isoformat()
        })
    
    def track_test_result(self, category: str, test_name: str, passed: bool, duration: float):
        """Track individual test result"""
        self.metrics["test_results"][category].append({
            "name": test_name,
            "passed": passed,
            "duration": duration
        })
    
    def finalize(self):
        """Finalize metrics calculation"""
        self.metrics["end_time"] = datetime.now().isoformat()
        start = datetime.fromisoformat(self.metrics["start_time"])
        end = datetime.fromisoformat(self.metrics["end_time"])
        self.metrics["duration"] = (end - start).total_seconds()
        
        # Calculate summary statistics
        if self.metrics["quality_scores"]:
            scores = [s["score"] for s in self.metrics["quality_scores"]]
            self.metrics["quality_summary"] = {
                "average": sum(scores) / len(scores),
                "min": min(scores),
                "max": max(scores),
                "count": len(scores)
            }
        
        # Calculate total costs
        self.metrics["total_llm_cost"] = sum(self.metrics["llm_costs"].values())
        
        # Calculate DB latency stats
        if "db_latencies" in self.metrics:
            for db_type, latencies in self.metrics["db_latencies"].items():
                if latencies:
                    self.metrics[f"{db_type}_latency_avg"] = sum(latencies) / len(latencies)
                    self.metrics[f"{db_type}_latency_p95"] = sorted(latencies)[int(len(latencies) * 0.95)]
    
    def generate_report(self, format: str = "json") -> str:
        """Generate report in specified format"""
        if format == "json":
            return json.dumps(self.metrics, indent=2, default=str)
        elif format == "markdown":
            return self._generate_markdown_report()
        elif format == "html":
            return self._generate_html_report()
        else:
            return str(self.metrics)
    
    def _generate_markdown_report(self) -> str:
        """Generate markdown report"""
        report = []
        report.append("# Real Service Test Report")
        report.append(f"\n**Generated:** {self.metrics['end_time']}")
        report.append(f"**Duration:** {self.metrics['duration']:.2f} seconds\n")
        
        # Test Results Summary
        report.append("## Test Results Summary\n")
        total_tests = sum(len(tests) for tests in self.metrics["test_results"].values())
        passed_tests = sum(1 for tests in self.metrics["test_results"].values() 
                          for test in tests if test["passed"])
        report.append(f"- **Total Tests:** {total_tests}")
        report.append(f"- **Passed:** {passed_tests}")
        report.append(f"- **Failed:** {total_tests - passed_tests}")
        report.append(f"- **Pass Rate:** {(passed_tests/total_tests*100):.1f}%\n")
        
        # LLM Usage
        if self.metrics["llm_calls"]:
            report.append("## LLM API Usage\n")
            report.append("| Model | Calls | Estimated Cost |")
            report.append("|-------|-------|----------------|")
            for model in sorted(self.metrics["llm_calls"].keys()):
                calls = self.metrics["llm_calls"][model]
                cost = self.metrics["llm_costs"].get(model, 0)
                report.append(f"| {model} | {calls} | ${cost:.4f} |")
            report.append(f"\n**Total LLM Cost:** ${self.metrics['total_llm_cost']:.4f}\n")
        
        # Database Performance
        if self.metrics["db_queries"]:
            report.append("## Database Performance\n")
            report.append("| Database | Queries | Avg Latency (ms) |")
            report.append("|----------|---------|------------------|")
            for db in sorted(self.metrics["db_queries"].keys()):
                queries = self.metrics["db_queries"][db]
                avg_latency = self.metrics.get(f"{db}_latency_avg", 0) * 1000
                report.append(f"| {db} | {queries} | {avg_latency:.2f} |")
            report.append("")
        
        # Cache Performance
        if self.metrics["cache_stats"]["hits"] + self.metrics["cache_stats"]["misses"] > 0:
            report.append("## Cache Performance\n")
            report.append(f"- **Hits:** {self.metrics['cache_stats']['hits']}")
            report.append(f"- **Misses:** {self.metrics['cache_stats']['misses']}")
            report.append(f"- **Hit Rate:** {self.metrics['cache_stats']['hit_rate']:.1%}\n")
        
        # Quality Scores
        if "quality_summary" in self.metrics:
            report.append("## Quality Gate Scores\n")
            report.append(f"- **Average Score:** {self.metrics['quality_summary']['average']:.3f}")
            report.append(f"- **Min Score:** {self.metrics['quality_summary']['min']:.3f}")
            report.append(f"- **Max Score:** {self.metrics['quality_summary']['max']:.3f}")
            report.append(f"- **Total Validations:** {self.metrics['quality_summary']['count']}\n")
        
        # Test Details by Category
        report.append("## Test Details by Category\n")
        for category, tests in self.metrics["test_results"].items():
            if tests:
                passed = sum(1 for t in tests if t["passed"])
                report.append(f"### {category.upper()}")
                report.append(f"- Tests: {len(tests)}")
                report.append(f"- Passed: {passed}")
                report.append(f"- Failed: {len(tests) - passed}")
                report.append("")
        
        # Errors and Warnings
        if self.metrics["errors"]:
            report.append("## Errors\n")
            for error in self.metrics["errors"]:
                report.append(f"- {error}")
            report.append("")
        
        if self.metrics["warnings"]:
            report.append("## Warnings\n")
            for warning in self.metrics["warnings"]:
                report.append(f"- {warning}")
            report.append("")
        
        return "\n".join(report)
    
    def _build_html_header(self) -> str:
        """Build HTML header with styling"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Real Service Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .metric-card { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }
        .success { color: #28a745; font-weight: bold; }
        .failure { color: #dc3545; font-weight: bold; }
        .warning { color: #ffc107; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th { background: #007bff; color: white; padding: 10px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #ddd; }
        tr:hover { background: #f5f5f5; }
        .chart { margin: 20px 0; }
        .progress-bar { width: 100%; height: 30px; background: #e9ecef; border-radius: 5px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #28a745, #20c997); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <h1>Real Service Test Report</h1>
        """
    
    def _build_summary_section(self) -> str:
        """Build summary section with timing info"""
        return f"""<p><strong>Generated:</strong> {self.metrics['end_time']}</p>
<p><strong>Duration:</strong> {self.metrics['duration']:.2f} seconds</p>"""
    
    def _build_test_results_section(self) -> str:
        """Build test results section with progress bar"""
        total_tests = sum(len(tests) for tests in self.metrics["test_results"].values())
        passed_tests = sum(1 for tests in self.metrics["test_results"].values() for test in tests if test["passed"])
        pass_rate = (passed_tests/total_tests*100) if total_tests > 0 else 0
        return f"""<h2>Test Results</h2>
<div class="metric-card">
<p>Total Tests: {total_tests}</p>
<p class="success">Passed: {passed_tests}</p>
<p class="failure">Failed: {total_tests - passed_tests}</p>
<div class="progress-bar">
<div class="progress-fill" style="width: {pass_rate}%">{pass_rate:.1f}% Pass Rate</div>
</div>
</div>"""
    
    def _build_llm_usage_section(self) -> str:
        """Build LLM usage chart section"""
        if not self.metrics["llm_calls"]:
            return ""
        labels_json = json.dumps(list(self.metrics['llm_calls'].keys()))
        values_json = json.dumps(list(self.metrics['llm_calls'].values()))
        cost_display = f"${self.metrics['total_llm_cost']:.4f}"
        return f"""<h2>LLM API Usage</h2>
<canvas id="llmChart" width="400" height="200"></canvas>
<script>
new Chart(document.getElementById('llmChart'), {{
  type: 'bar',
  data: {{
    labels: {labels_json},
    datasets: [{{
      label: 'API Calls',
      data: {values_json},
      backgroundColor: 'rgba(0, 123, 255, 0.5)'
    }}]
  }}
}});
</script>
<p><strong>Total LLM Cost:</strong> {cost_display}</p>"""
    
    def _build_database_section(self) -> str:
        """Build database performance table section"""
        if not self.metrics["db_queries"]:
            return ""
        rows = []
        for db in sorted(self.metrics["db_queries"].keys()):
            queries = self.metrics["db_queries"][db]
            avg_latency = self.metrics.get(f"{db}_latency_avg", 0) * 1000
            rows.append(f"<tr><td>{db}</td><td>{queries}</td><td>{avg_latency:.2f}</td></tr>")
        table_rows = "\n".join(rows)
        return f"""<h2>Database Performance</h2>
<table>
<tr><th>Database</th><th>Queries</th><th>Avg Latency (ms)</th></tr>
{table_rows}
</table>"""
    
    def _build_quality_section(self) -> str:
        """Build quality scores section"""
        if "quality_summary" not in self.metrics:
            return ""
        avg_score = self.metrics['quality_summary']['average']
        min_score = self.metrics['quality_summary']['min']
        max_score = self.metrics['quality_summary']['max']
        count = self.metrics['quality_summary']['count']
        return f"""<h2>Quality Gate Performance</h2>
<div class="metric-card">
<p>Average Score: {avg_score:.3f}</p>
<p>Score Range: {min_score:.3f} - {max_score:.3f}</p>
<p>Total Validations: {count}</p>
</div>"""
    
    def _build_html_footer(self) -> str:
        """Build HTML footer"""
        return "</div></body></html>"
    
    def _generate_html_report(self) -> str:
        """Generate HTML report with charts"""
        sections = [
            self._build_html_header(),
            self._build_summary_section(),
            self._build_test_results_section(),
            self._build_llm_usage_section(),
            self._build_database_section(),
            self._build_quality_section(),
            self._build_html_footer()
        ]
        return "\n".join(filter(None, sections))


class EnhancedRealServiceTestRunner:
    """Enhanced runner for real service tests with detailed reporting"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.metrics = RealServiceTestMetrics()
        self.test_dir = Path(__file__).parent.parent / "app" / "tests"
        self.reports_dir = Path(__file__).parent.parent / "test_reports" / "real_services"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def run_tests(self, 
                  categories: Optional[List[str]] = None,
                  model: str = "gemini-1.5-flash",
                  parallel: int = 1,
                  timeout: int = 300) -> int:
        """Run real service tests with specified configuration"""
        self._print_test_header(model, parallel, timeout, categories)
        env = self._setup_test_environment(model, timeout)
        cmd, json_report = self._build_pytest_command(categories, parallel, timeout)
        return self._execute_tests_with_handling(cmd, env, json_report, timeout)
    
    def _print_test_header(self, model: str, parallel: int, timeout: int, categories: Optional[List[str]]):
        """Print test execution header"""
        print("\n" + "="*60)
        print("ENHANCED REAL SERVICE TEST RUNNER")
        print("="*60)
        print(f"Model: {model}")
        print(f"Parallel: {parallel}")
        print(f"Timeout: {timeout}s")
        print(f"Categories: {categories or 'all'}")
        print("="*60)
    
    def _setup_test_environment(self, model: str, timeout: int) -> Dict[str, str]:
        """Setup environment variables for test execution"""
        env = os.environ.copy()
        env["ENABLE_REAL_LLM_TESTING"] = "true"
        env["ENABLE_REAL_DB_TESTING"] = "true"
        env["ENABLE_REAL_REDIS_TESTING"] = "true"
        env["ENABLE_REAL_CLICKHOUSE_TESTING"] = "true"
        env["TEST_LLM_MODEL"] = model
        env["TEST_LLM_TIMEOUT"] = str(timeout)
        return env
    
    def _build_pytest_command(self, categories: Optional[List[str]], parallel: int, timeout: int) -> Tuple[List[str], Path]:
        """Build pytest command with all options"""
        cmd = self._create_base_pytest_command(timeout)
        cmd = self._add_test_markers(cmd, categories)
        cmd = self._add_parallelization(cmd, parallel)
        json_report = self._add_json_reporting(cmd)
        return cmd, json_report
    
    def _create_base_pytest_command(self, timeout: int) -> List[str]:
        """Create base pytest command"""
        return [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "-v", "--tb=short",
            f"--timeout={timeout}",
            "-W", "ignore::DeprecationWarning"
        ]
    
    def _add_test_markers(self, cmd: List[str], categories: Optional[List[str]]) -> List[str]:
        """Add test markers to command"""
        if categories:
            markers = " or ".join(categories)
            cmd.extend(["-m", markers])
        else:
            cmd.extend(["-m", "real_services"])
        return cmd
    
    def _add_parallelization(self, cmd: List[str], parallel: int) -> List[str]:
        """Add parallelization options to command"""
        if parallel > 1:
            cmd.extend(["-n", str(parallel)])
        return cmd
    
    def _add_json_reporting(self, cmd: List[str]) -> Path:
        """Add JSON reporting to command and return report path"""
        json_report = self.reports_dir / f"pytest_report_{int(time.time())}.json"
        cmd.extend(["--json-report", "--json-report-file", str(json_report)])
        return json_report
    
    def _execute_tests_with_handling(self, cmd: List[str], env: Dict[str, str], json_report: Path, timeout: int) -> int:
        """Execute tests with comprehensive error handling"""
        print("\nRunning tests...")
        try:
            result = self._run_subprocess(cmd, env, timeout)
            return self._process_successful_execution(result, json_report)
        except subprocess.TimeoutExpired:
            return self._handle_test_timeout(timeout)
        except Exception as e:
            return self._handle_test_error(e)
    
    def _run_subprocess(self, cmd: List[str], env: Dict[str, str], timeout: int) -> subprocess.CompletedProcess:
        """Run subprocess with specified configuration"""
        return subprocess.run(
            cmd, env=env, capture_output=True, text=True,
            timeout=timeout * 10  # Give extra time for all tests
        )
    
    def _process_successful_execution(self, result: subprocess.CompletedProcess, json_report: Path) -> int:
        """Process successful test execution results"""
        self._parse_test_output(result.stdout + result.stderr)
        if json_report.exists():
            self._parse_json_report(json_report)
        self.metrics.finalize()
        self._generate_reports()
        self._print_summary()
        return result.returncode
    
    def _handle_test_timeout(self, timeout: int) -> int:
        """Handle test execution timeout"""
        print(f"\n[TIMEOUT] Tests exceeded timeout of {timeout * 10}s")
        self.metrics.metrics["errors"].append(f"Test execution timeout after {timeout * 10}s")
        self.metrics.finalize()
        self._generate_reports()
        return -1
    
    def _handle_test_error(self, error: Exception) -> int:
        """Handle general test execution error"""
        print(f"\n[ERROR] Test execution failed: {error}")
        self.metrics.metrics["errors"].append(str(error))
        self.metrics.finalize()
        self._generate_reports()
        return -1
    
    def _parse_test_output(self, output: str):
        """Parse test output for metrics"""
        import re
        
        # Parse test counts
        passed_match = re.search(r'(\d+) passed', output)
        failed_match = re.search(r'(\d+) failed', output)
        
        if passed_match:
            passed = int(passed_match.group(1))
            for i in range(passed):
                self.metrics.track_test_result("unknown", f"test_{i}", True, 0)
        
        if failed_match:
            failed = int(failed_match.group(1))
            for i in range(failed):
                self.metrics.track_test_result("unknown", f"test_{i}", False, 0)
        
        # Parse LLM calls (if logged)
        llm_pattern = r"LLM call: (\w+) with (\d+) tokens"
        for match in re.finditer(llm_pattern, output):
            model = match.group(1)
            tokens = int(match.group(2))
            self.metrics.track_llm_call(model, tokens)
        
        # Parse quality scores (if logged)
        quality_pattern = r"Quality score: ([\d.]+) for (\w+)"
        for match in re.finditer(quality_pattern, output):
            score = float(match.group(1))
            test = match.group(2)
            self.metrics.track_quality_score(score, test)
        
        # Parse cache hits/misses
        if "cache hit" in output.lower():
            self.metrics.track_cache(True)
        if "cache miss" in output.lower():
            self.metrics.track_cache(False)
    
    def _parse_json_report(self, json_file: Path):
        """Parse pytest JSON report for detailed metrics"""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Extract test results
            for test in data.get("tests", []):
                category = self._categorize_test(test["nodeid"])
                passed = test["outcome"] == "passed"
                duration = test.get("duration", 0)
                self.metrics.track_test_result(category, test["nodeid"], passed, duration)
            
            # Extract summary
            summary = data.get("summary", {})
            if "total" in summary:
                self.metrics.metrics["pytest_summary"] = summary
                
        except Exception as e:
            self.metrics.metrics["warnings"].append(f"Failed to parse JSON report: {e}")
    
    def _categorize_test(self, test_path: str) -> str:
        """Categorize test based on path"""
        if "real_llm" in test_path:
            return "llm"
        elif "real_database" in test_path:
            return "database"
        elif "real_redis" in test_path:
            return "redis"
        elif "real_clickhouse" in test_path:
            return "clickhouse"
        elif "e2e" in test_path:
            return "e2e"
        else:
            return "integration"
    
    def _generate_reports(self):
        """Generate all report formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON report
        json_report = self.reports_dir / f"real_service_report_{timestamp}.json"
        with open(json_report, 'w') as f:
            f.write(self.metrics.generate_report("json"))
        print(f"\nJSON report: {json_report}")
        
        # Markdown report
        md_report = self.reports_dir / f"real_service_report_{timestamp}.md"
        with open(md_report, 'w') as f:
            f.write(self.metrics.generate_report("markdown"))
        print(f"Markdown report: {md_report}")
        
        # HTML report
        html_report = self.reports_dir / f"real_service_report_{timestamp}.html"
        with open(html_report, 'w') as f:
            f.write(self.metrics.generate_report("html"))
        print(f"HTML report: {html_report}")
        
        # Update latest symlinks
        for ext in ["json", "md", "html"]:
            latest = self.reports_dir / f"latest_real_service_report.{ext}"
            if latest.exists():
                latest.unlink()
            latest.symlink_to(self.reports_dir / f"real_service_report_{timestamp}.{ext}")
    
    def _print_summary(self):
        """Print test execution summary"""
        print("\n" + "="*60)
        print("TEST EXECUTION SUMMARY")
        print("="*60)
        
        # Test results
        total_tests = sum(len(tests) for tests in self.metrics.metrics["test_results"].values())
        if total_tests > 0:
            passed_tests = sum(1 for tests in self.metrics.metrics["test_results"].values() 
                              for test in tests if test["passed"])
            print(f"Tests: {passed_tests}/{total_tests} passed ({passed_tests/total_tests*100:.1f}%)")
        
        # LLM usage
        if self.metrics.metrics["llm_calls"]:
            total_calls = sum(self.metrics.metrics["llm_calls"].values())
            print(f"LLM Calls: {total_calls} (Cost: ${self.metrics.metrics['total_llm_cost']:.4f})")
        
        # Cache performance
        cache_total = self.metrics.metrics["cache_stats"]["hits"] + self.metrics.metrics["cache_stats"]["misses"]
        if cache_total > 0:
            print(f"Cache Hit Rate: {self.metrics.metrics['cache_stats']['hit_rate']:.1%}")
        
        # Quality scores
        if "quality_summary" in self.metrics.metrics:
            print(f"Avg Quality Score: {self.metrics.metrics['quality_summary']['average']:.3f}")
        
        print(f"Duration: {self.metrics.metrics['duration']:.2f}s")
        print("="*60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Enhanced Real Service Test Runner")
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=["real_llm", "real_database", "real_redis", "real_clickhouse", "e2e"],
        help="Test categories to run"
    )
    parser.add_argument(
        "--model",
        default="gemini-1.5-flash",
        choices=["gemini-1.5-flash", "gemini-2.5-pro", "gpt-3.5-turbo", "gpt-4", "claude-3-sonnet"],
        help="LLM model to use for tests"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Number of parallel test workers"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout per test in seconds"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    runner = EnhancedRealServiceTestRunner(verbose=args.verbose)
    exit_code = runner.run_tests(
        categories=args.categories,
        model=args.model,
        parallel=args.parallel,
        timeout=args.timeout
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()