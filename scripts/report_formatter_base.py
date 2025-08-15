#!/usr/bin/env python
"""
Base Report Formatters for Enhanced Test Reporter
Handles basic formatting functions with 8-line function limit
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .report_types import (
    TestComponentData, CompleteTestMetrics,
    ReportConfigurationExtended, ChangeDetectionExtended
)


class ReportHeaderFormatter:
    """Formats report headers and executive summary"""
    
    def format_executive_summary(self, level: str, config: Dict, exit_code: int) -> str:
        """Format executive summary section"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = "✅ PASSED" if exit_code == 0 else "❌ FAILED"
        description = config.get('description', 'N/A')
        
        return f"""# 📊 Netra AI Platform - Comprehensive Test Report

## 🎯 Executive Summary

**Generated:** {timestamp}  
**Test Level:** `{level}` - {description}  
**Overall Status:** {status}"""
    
    def format_key_metrics_table(self, metrics: Dict, changes: Dict) -> str:
        """Format key metrics summary table"""
        total_files = metrics.get('total_files', 0)
        total_tests = metrics.get('total_tests', 0)
        passed = metrics.get('passed', 0)
        coverage = metrics.get('coverage')
        duration = metrics.get('duration', 0)
        
        pass_rate = (passed/total_tests*100 if total_tests else 0)
        coverage_str = f"{coverage:.1f}%" if coverage else "N/A"
        
        return f"""
### 📈 Key Metrics

| Metric | Value | Change | Trend |
|--------|-------|--------|-------|
| **Total Test Files** | {total_files} | {changes.get('files_change', 'N/A')} | {self._get_trend_icon(changes.get('files_change', '0'))} |
| **Total Tests** | {total_tests} | {changes.get('tests_change', 'N/A')} | {self._get_trend_icon(changes.get('tests_change', '0'))} |
| **Pass Rate** | {pass_rate:.1f}% | {changes.get('pass_rate_change', 'N/A')} | {self._get_trend_icon(changes.get('pass_rate_change', '0'))} |
| **Coverage** | {coverage_str} | {changes.get('coverage_change', 'N/A')} | {self._get_trend_icon(changes.get('coverage_change', '0'))} |
| **Duration** | {self._format_duration(duration)} | {changes.get('duration_change', 'N/A')} | {self._get_trend_icon(changes.get('duration_change', '0'), reverse=True)} |"""
    
    def _get_trend_icon(self, change: str, reverse: bool = False) -> str:
        """Get trend icon based on change value"""
        if change == "N/A" or change == "0":
            return "➖"
        
        try:
            value = float(change.replace('+', '').replace('%', ''))
            return self._select_trend_icon(value, reverse)
        except:
            return "➖"
    
    def _select_trend_icon(self, value: float, reverse: bool) -> str:
        """Select appropriate trend icon"""
        if reverse:  # For metrics where decrease is good
            return "📉" if value > 0 else "📈"
        else:  # For metrics where increase is good
            return "📈" if value > 0 else "📉"
    
    def _format_duration(self, seconds: float) -> str:
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


class TestResultsFormatter:
    """Formats test results overview section"""
    
    def format_results_overview(self, backend_data: TestComponentData, 
                               frontend_data: TestComponentData, results: Dict) -> str:
        """Format test results overview section"""
        summary_table = self._format_summary_statistics(backend_data, frontend_data)
        component_table = self._format_component_breakdown(backend_data, frontend_data, results)
        
        return f"""## 📊 Test Results Overview

### Summary Statistics

{summary_table}

### Component Breakdown

{component_table}"""
    
    def _format_summary_statistics(self, backend: TestComponentData, frontend: TestComponentData) -> str:
        """Format summary statistics table"""
        total_tests = backend.metrics.total_tests + frontend.metrics.total_tests
        total_passed = backend.metrics.passed + frontend.metrics.passed
        total_failed = backend.metrics.failed + frontend.metrics.failed
        total_skipped = backend.metrics.skipped + frontend.metrics.skipped
        total_errors = backend.metrics.errors + frontend.metrics.errors
        
        return f"""| Status | Count | Percentage | Visual |
|--------|-------|------------|--------|
| ✅ **Passed** | {total_passed} | {(total_passed/total_tests*100 if total_tests else 0):.1f}% | {self._generate_bar(total_passed, total_tests, '🟩')} |
| ❌ **Failed** | {total_failed} | {(total_failed/total_tests*100 if total_tests else 0):.1f}% | {self._generate_bar(total_failed, total_tests, '🟥')} |
| ⏭️ **Skipped** | {total_skipped} | {(total_skipped/total_tests*100 if total_tests else 0):.1f}% | {self._generate_bar(total_skipped, total_tests, '🟨')} |
| 🔥 **Errors** | {total_errors} | {(total_errors/total_tests*100 if total_tests else 0):.1f}% | {self._generate_bar(total_errors, total_tests, '🟧')} |"""
    
    def _format_component_breakdown(self, backend: TestComponentData, 
                                  frontend: TestComponentData, results: Dict) -> str:
        """Format component breakdown table"""
        b_coverage = f"{backend.metrics.coverage:.1f}%" if backend.metrics.coverage else "N/A"
        f_coverage = f"{frontend.metrics.coverage:.1f}%" if frontend.metrics.coverage else "N/A"
        
        return f"""| Component | Files | Tests | Passed | Failed | Coverage | Duration | Status |
|-----------|-------|-------|--------|--------|----------|----------|--------|
| **Backend** | {backend.metrics.total_files} | {backend.metrics.total_tests} | {backend.metrics.passed} | {backend.metrics.failed} | {b_coverage} | {self._format_duration(results.get('backend', {}).get('duration', 0))} | {self._get_status_badge(results.get('backend', {}).get('status', 'unknown'))} |
| **Frontend** | {frontend.metrics.total_files} | {frontend.metrics.total_tests} | {frontend.metrics.passed} | {frontend.metrics.failed} | {f_coverage} | {self._format_duration(results.get('frontend', {}).get('duration', 0))} | {self._get_status_badge(results.get('frontend', {}).get('status', 'unknown'))} |"""
    
    def _generate_bar(self, value: int, total: int, symbol: str) -> str:
        """Generate visual bar for percentages"""
        if total == 0:
            return ""
        percentage = value / total
        bar_length = int(percentage * 20)
        return symbol * bar_length if bar_length > 0 else ""
    
    def _get_status_badge(self, status: str) -> str:
        """Get status badge with emoji"""
        status_map = {
            "passed": "✅ PASSED",
            "failed": "❌ FAILED",
            "timeout": "⏱️ TIMEOUT",
            "skipped": "⏭️ SKIPPED",
            "pending": "⏳ PENDING"
        }
        return status_map.get(status, "❓ UNKNOWN")
    
    def _format_duration(self, seconds: float) -> str:
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


class CategoryFormatter:
    """Formats test category breakdown"""
    
    def format_category_table(self, backend_cats: Dict, frontend_cats: Dict) -> str:
        """Format test category breakdown table"""
        all_categories = set(backend_cats.keys()) | set(frontend_cats.keys())
        
        if not all_categories:
            return "*No category data available*"
        
        table_header = "| Category | Backend | Frontend | Total | Pass Rate |\n"
        table_separator = "|----------|---------|----------|-------|----------|\n"
        table_rows = self._generate_category_rows(all_categories, backend_cats, frontend_cats)
        
        return table_header + table_separator + table_rows
    
    def _generate_category_rows(self, categories: set, backend_cats: Dict, frontend_cats: Dict) -> str:
        """Generate table rows for categories"""
        rows = []
        for cat in sorted(categories):
            row = self._format_category_row(cat, backend_cats, frontend_cats)
            rows.append(row)
        return '\n'.join(rows)
    
    def _format_category_row(self, cat: str, backend_cats: Dict, frontend_cats: Dict) -> str:
        """Format single category table row"""
        b_data = backend_cats.get(cat, {})
        f_data = frontend_cats.get(cat, {})
        
        b_count, f_count = b_data.get('count', 0), f_data.get('count', 0)
        total = b_count + f_count
        
        b_passed, f_passed = b_data.get('passed', 0), f_data.get('passed', 0)
        total_passed = b_passed + f_passed
        
        pass_rate = (total_passed / total * 100) if total > 0 else 0
        
        return f"| **{cat.title()}** | {b_count} | {f_count} | {total} | {pass_rate:.1f}% |"