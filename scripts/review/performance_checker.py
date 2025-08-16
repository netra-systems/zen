#!/usr/bin/env python3
"""
Performance issue checker for code review system.
Detects potential performance problems and bottlenecks.
"""

from .core import ReviewConfig, ReviewData
from .command_runner import CommandRunner


class PerformanceChecker:
    """Checks for potential performance problems"""
    
    def __init__(self, config: ReviewConfig, command_runner: CommandRunner):
        self.config = config
        self.runner = command_runner
    
    def check_performance_issues(self, review_data: ReviewData) -> None:
        """Check for potential performance problems"""
        print("\n[PERF] Checking Performance Issues...")
        self._check_n_plus_one_queries(review_data)
        self._check_frontend_bundle_size(review_data)
    
    def _check_n_plus_one_queries(self, review_data: ReviewData) -> None:
        """Check for N+1 query patterns"""
        success, output = self.runner.run(
            "grep -r --include='*.py' 'for .* in .*:' app/ | grep -A 2 'db\\|query\\|select' | head -10"
        )
        if success and output:
            if self._has_query_in_loop(output):
                review_data.add_performance_concern("Potential N+1 query pattern detected")
                review_data.issue_tracker.add_issue("high", "Possible N+1 database query pattern")
    
    def _has_query_in_loop(self, output: str) -> bool:
        """Check if output contains query patterns in loops"""
        return 'for' in output and ('query' in output or 'select' in output)
    
    def _check_frontend_bundle_size(self, review_data: ReviewData) -> None:
        """Check frontend bundle size if build exists"""
        if self.runner.check_directory_exists("frontend/.next"):
            self._analyze_bundle_size(review_data)
    
    def _analyze_bundle_size(self, review_data: ReviewData) -> None:
        """Analyze frontend bundle size"""
        size_str = self.runner.get_file_size("frontend/.next")
        print(f"  Frontend build size: {size_str}")
        if self._is_bundle_too_large(size_str):
            review_data.add_performance_concern(f"Large frontend bundle: {size_str}")
            review_data.issue_tracker.add_issue("medium", f"Frontend bundle size is large: {size_str}")
    
    def _is_bundle_too_large(self, size_str: str) -> bool:
        """Check if bundle size is concerning"""
        if 'G' in size_str:
            return True
        if 'M' in size_str:
            try:
                size_mb = int(size_str.rstrip('M'))
                return size_mb > 100
            except ValueError:
                return False
        return False