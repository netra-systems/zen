#!/usr/bin/env python
"""
Real Service Test Metrics Tracking
ULTRA DEEP THINK: Module-based architecture - Metrics tracking extracted for 300-line compliance
"""

import json
from datetime import datetime
from collections import defaultdict
from typing import List

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
    
    def _build_report_header(self) -> List[str]:
        """Build report header with title and timing info"""
        return [
            "# Real Service Test Report",
            f"\n**Generated:** {self.metrics['end_time']}",
            f"**Duration:** {self.metrics['duration']:.2f} seconds\n"
        ]
    
    def _build_test_summary_section(self) -> List[str]:
        """Build test results summary section"""
        total_tests = sum(len(tests) for tests in self.metrics["test_results"].values())
        passed_tests = sum(1 for tests in self.metrics["test_results"].values() 
                          for test in tests if test["passed"])
        pass_rate = (passed_tests/total_tests*100) if total_tests > 0 else 0
        return [
            "## Test Results Summary\n",
            f"- **Total Tests:** {total_tests}",
            f"- **Passed:** {passed_tests}",
            f"- **Failed:** {total_tests - passed_tests}",
            f"- **Pass Rate:** {pass_rate:.1f}%\n"
        ]
    
    def _build_llm_section(self) -> List[str]:
        """Build LLM API usage section"""
        if not self.metrics["llm_calls"]:
            return []
        section = ["## LLM API Usage\n", "| Model | Calls | Estimated Cost |", "|-------|-------|----------------|"]
        for model in sorted(self.metrics["llm_calls"].keys()):
            calls = self.metrics["llm_calls"][model]
            cost = self.metrics["llm_costs"].get(model, 0)
            section.append(f"| {model} | {calls} | ${cost:.4f} |")
        section.append(f"\n**Total LLM Cost:** ${self.metrics['total_llm_cost']:.4f}\n")
        return section
    
    def _build_database_section(self) -> List[str]:
        """Build database performance section"""
        if not self.metrics["db_queries"]:
            return []
        section = ["## Database Performance\n", "| Database | Queries | Avg Latency (ms) |", "|----------|---------|------------------|"]
        for db in sorted(self.metrics["db_queries"].keys()):
            queries = self.metrics["db_queries"][db]
            avg_latency = self.metrics.get(f"{db}_latency_avg", 0) * 1000
            section.append(f"| {db} | {queries} | {avg_latency:.2f} |")
        section.append("")
        return section
    
    def _build_cache_section(self) -> List[str]:
        """Build cache performance section"""
        cache_total = self.metrics["cache_stats"]["hits"] + self.metrics["cache_stats"]["misses"]
        if cache_total == 0:
            return []
        return [
            "## Cache Performance\n",
            f"- **Hits:** {self.metrics['cache_stats']['hits']}",
            f"- **Misses:** {self.metrics['cache_stats']['misses']}",
            f"- **Hit Rate:** {self.metrics['cache_stats']['hit_rate']:.1%}\n"
        ]
    
    def _build_quality_section(self) -> List[str]:
        """Build quality gate scores section"""
        if "quality_summary" not in self.metrics:
            return []
        qs = self.metrics['quality_summary']
        return [
            "## Quality Gate Scores\n",
            f"- **Average Score:** {qs['average']:.3f}",
            f"- **Min Score:** {qs['min']:.3f}",
            f"- **Max Score:** {qs['max']:.3f}",
            f"- **Total Validations:** {qs['count']}\n"
        ]
    
    def _build_test_details_section(self) -> List[str]:
        """Build test details by category section"""
        section = ["## Test Details by Category\n"]
        for category, tests in self.metrics["test_results"].items():
            if tests:
                passed = sum(1 for t in tests if t["passed"])
                section.extend([
                    f"### {category.upper()}", f"- Tests: {len(tests)}",
                    f"- Passed: {passed}", f"- Failed: {len(tests) - passed}", ""
                ])
        return section
    
    def _build_errors_section(self) -> List[str]:
        """Build errors section"""
        if not self.metrics["errors"]:
            return []
        section = ["## Errors\n"]
        for error in self.metrics["errors"]:
            section.append(f"- {error}")
        section.append("")
        return section
    
    def _build_warnings_section(self) -> List[str]:
        """Build warnings section"""
        if not self.metrics["warnings"]:
            return []
        section = ["## Warnings\n"]
        for warning in self.metrics["warnings"]:
            section.append(f"- {warning}")
        section.append("")
        return section
    
    def _generate_markdown_report(self) -> str:
        """Generate markdown report by assembling all sections"""
        sections = [
            self._build_report_header(), self._build_test_summary_section(),
            self._build_llm_section(), self._build_database_section(),
            self._build_cache_section(), self._build_quality_section(),
            self._build_test_details_section(), self._build_errors_section(),
            self._build_warnings_section()
        ]
        return "\n".join(line for section in sections for line in section)
    
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
    
    def _generate_html_report(self) -> str:
        """Generate HTML report with charts"""
        return self._build_html_header() + "</div></body></html>"