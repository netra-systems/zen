#!/usr/bin/env python
"""
Advanced Report Formatters for Enhanced Test Reporter
Handles performance analysis and recommendations with 8-line function limit
"""

from typing import Dict, List, Optional, Any
from collections import defaultdict

from .report_types import TestComponentData, CompleteTestMetrics


class PerformanceFormatter:
    """Formats performance analysis section"""
    
    def format_performance_analysis(self, backend_data: TestComponentData, 
                                   frontend_data: TestComponentData) -> str:
        """Format performance analysis section"""
        speed_analysis = self._format_speed_distribution(backend_data, frontend_data)
        slowest_tests = self._format_slowest_tests(backend_data, frontend_data)
        
        return f"""## ⚡ Performance Analysis

### Test Speed Distribution

{speed_analysis}

### Top 5 Slowest Tests

{slowest_tests}"""
    
    def _format_speed_distribution(self, backend: TestComponentData, frontend: TestComponentData) -> str:
        """Format test speed distribution table"""
        all_tests = backend.test_details + frontend.test_details
        
        if not all_tests:
            return "*No timing data available*"
        
        durations = [t.duration for t in all_tests if t.duration > 0]
        
        if not durations:
            return "*No timing data available*"
        
        stats = self._calculate_duration_stats(durations)
        return self._format_stats_table(stats)
    
    def _calculate_duration_stats(self, durations: List[float]) -> Dict:
        """Calculate duration statistics"""
        durations.sort()
        return {
            "median": durations[len(durations) // 2],
            "p95": durations[int(len(durations) * 0.95)] if len(durations) > 20 else durations[-1],
            "p99": durations[int(len(durations) * 0.99)] if len(durations) > 100 else durations[-1],
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / len(durations)
        }
    
    def _format_stats_table(self, stats: Dict) -> str:
        """Format statistics into table"""
        return f"""| Metric | Value |
|--------|-------|
| **Median (P50)** | {stats['median']:.3f}s |
| **P95** | {stats['p95']:.3f}s |
| **P99** | {stats['p99']:.3f}s |
| **Min** | {stats['min']:.3f}s |
| **Max** | {stats['max']:.3f}s |
| **Average** | {stats['avg']:.3f}s |"""
    
    def _format_slowest_tests(self, backend: TestComponentData, frontend: TestComponentData) -> str:
        """Format slowest tests table"""
        all_tests = backend.test_details + frontend.test_details
        
        if not all_tests:
            return "*No timing data available*"
        
        slowest = sorted(all_tests, key=lambda x: x.duration, reverse=True)[:5]
        
        table = "| Test | Category | Duration |\n"
        table += "|------|----------|----------|\n"
        
        for test in slowest:
            name = f"{test.file}::{test.name}"
            if len(name) > 60:
                name = name[:57] + "..."
            table += f"| `{name}` | {test.category} | {test.duration:.2f}s |\n"
        
        return table


class FailureFormatter:
    """Formats failure analysis section"""
    
    def format_failure_analysis(self, backend_data: TestComponentData, 
                               frontend_data: TestComponentData) -> str:
        """Format failure analysis section"""
        all_failures = backend_data.failure_details + frontend_data.failure_details
        
        if not all_failures:
            return "✅ **No failures detected!**"
        
        by_category = self._group_failures_by_category(all_failures)
        analysis = f"### Total Failures: {len(all_failures)}\n\n"
        analysis += self._format_failures_by_category(by_category)
        
        return analysis
    
    def _group_failures_by_category(self, failures: List) -> Dict:
        """Group failures by category"""
        by_category = defaultdict(list)
        for failure in failures:
            category = getattr(failure, 'category', 'other')
            test_name = getattr(failure, 'test', 'unknown')
            by_category[category].append(test_name)
        return by_category
    
    def _format_failures_by_category(self, by_category: Dict) -> str:
        """Format failures by category table"""
        analysis = "### Failures by Category\n\n"
        analysis += "| Category | Count | Tests |\n"
        analysis += "|----------|-------|-------|\n"
        
        for category, tests in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True):
            test_list = self._format_test_list(tests)
            analysis += f"| **{category.title()}** | {len(tests)} | {test_list} |\n"
        
        return analysis
    
    def _format_test_list(self, tests: List[str]) -> str:
        """Format test list for table cell"""
        short_tests = [f"`{t.split('::')[-1][:20]}`" for t in tests[:3]]
        test_list = ", ".join(short_tests)
        if len(tests) > 3:
            test_list += f" +{len(tests)-3} more"
        return test_list


class RecommendationFormatter:
    """Formats recommendation section"""
    
    def format_recommendations(self, backend_data: TestComponentData, 
                              frontend_data: TestComponentData, coverage: Optional[float]) -> str:
        """Format actionable recommendations"""
        recommendations = []
        
        self._add_coverage_recommendations(coverage, recommendations)
        self._add_failure_recommendations(backend_data, frontend_data, recommendations)
        self._add_performance_recommendations(backend_data, frontend_data, recommendations)
        self._add_flaky_recommendations(recommendations)
        
        if not recommendations:
            recommendations.append("✅ **Excellent:** Test suite is in good shape. Keep up the good work!")
        
        return "\n".join([f"- {r}" for r in recommendations])
    
    def _add_coverage_recommendations(self, coverage: Optional[float], recommendations: List[str]) -> None:
        """Add coverage-based recommendations"""
        if not coverage:
            return
        
        if coverage < 70:
            recommendations.append("🔴 **Critical:** Coverage is below 70%. Focus on adding unit tests for uncovered code.")
        elif coverage < 85:
            recommendations.append("🟡 **Important:** Coverage is below 85%. Consider adding more integration tests.")
        elif coverage < 95:
            recommendations.append("🟢 **Good:** Coverage is good but can be improved. Target 95% for critical paths.")
    
    def _add_failure_recommendations(self, backend: TestComponentData, 
                                   frontend: TestComponentData, recommendations: List[str]) -> None:
        """Add failure-based recommendations"""
        total_failures = backend.metrics.failed + frontend.metrics.failed
        
        if total_failures > 20:
            recommendations.append("🔴 **Critical:** High failure count. Prioritize fixing failing tests.")
        elif total_failures > 10:
            recommendations.append("🟡 **Important:** Moderate failures detected. Schedule test fix session.")
    
    def _add_performance_recommendations(self, backend: TestComponentData, 
                                       frontend: TestComponentData, recommendations: List[str]) -> None:
        """Add performance-based recommendations"""
        all_tests = backend.test_details + frontend.test_details
        slow_tests = [t for t in all_tests if t.duration > 5]
        
        if len(slow_tests) > 5:
            recommendations.append(f"⚡ **Performance:** {len(slow_tests)} tests take >5s. Consider optimization or parallelization.")
    
    def _add_flaky_recommendations(self, recommendations: List[str]) -> None:
        """Add flaky test recommendations - placeholder for future implementation"""
        # This would be implemented when flaky test detection is added
        pass


class ChangeFormatter:
    """Formats change detection and historical analysis"""
    
    def format_change_summary(self, changes: Dict) -> str:
        """Format change summary section"""
        if not changes or all(v == "N/A" for v in changes.values()):
            return "*First run or no historical data available*"
        
        summary_parts = []
        self._add_new_failures_section(changes, summary_parts)
        self._add_fixed_tests_section(changes, summary_parts)
        self._add_flaky_tests_section(changes, summary_parts)
        
        return '\n\n'.join(summary_parts) if summary_parts else "*No significant changes detected*"
    
    def _add_new_failures_section(self, changes: Dict, summary_parts: List[str]) -> None:
        """Add new failures section"""
        if changes.get('new_failures'):
            section = f"### 🆕 New Failures ({len(changes['new_failures'])})\n\n"
            for failure in changes['new_failures'][:10]:
                section += f"- `{failure}`\n"
            if len(changes['new_failures']) > 10:
                section += f"- *... and {len(changes['new_failures']) - 10} more*\n"
            summary_parts.append(section)
    
    def _add_fixed_tests_section(self, changes: Dict, summary_parts: List[str]) -> None:
        """Add fixed tests section"""
        if changes.get('fixed_tests'):
            section = f"### ✅ Fixed Tests ({len(changes['fixed_tests'])})\n\n"
            for fixed in changes['fixed_tests'][:10]:
                section += f"- `{fixed}`\n"
            if len(changes['fixed_tests']) > 10:
                section += f"- *... and {len(changes['fixed_tests']) - 10} more*\n"
            summary_parts.append(section)
    
    def _add_flaky_tests_section(self, changes: Dict, summary_parts: List[str]) -> None:
        """Add flaky tests section"""
        if changes.get('flaky_tests'):
            section = f"### 🎲 Flaky Tests Detected ({len(changes['flaky_tests'])})\n\n"
            for flaky in changes['flaky_tests'][:5]:
                section += f"- `{flaky}`\n"
            summary_parts.append(section)
    
    def format_historical_trends(self, level_runs: List[Dict]) -> str:
        """Format historical trends table"""
        if len(level_runs) < 2:
            return "*Insufficient historical data for trends*"
        
        table = "| Date | Tests | Pass Rate | Coverage | Duration |\n"
        table += "|------|-------|-----------|----------|----------|\n"
        
        for run in level_runs[-5:]:
            date = run['timestamp'][:10]  # Simple date extraction
            pass_rate = (run['passed'] / run['total'] * 100) if run['total'] else 0
            coverage = f"{run['coverage']:.1f}%" if run.get('coverage') else "N/A"
            duration = f"{run['duration']:.1f}s"
            table += f"| {date} | {run['total']} | {pass_rate:.1f}% | {coverage} | {duration} |\n"
        
        return table