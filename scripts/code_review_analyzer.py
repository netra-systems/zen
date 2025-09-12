#!/usr/bin/env python3
"""
Code Review Analyzer
ULTRA DEEP THINK: Module-based architecture - Main coordinator  <= 300 lines
"""

from pathlib import Path

from code_review_ai_detector import CodeReviewAIDetector
from code_review_analysis import CodeReviewAnalysis
from code_review_smoke_tests import CodeReviewSmokeTests


class CodeReviewAnalyzer:
    """Main coordinator for code analysis operations"""
    
    def __init__(self, project_root: Path, mode: str, recent_commits: int):
        self.project_root = project_root
        self.mode = mode
        self.recent_commits = recent_commits
        
        # Initialize sub-modules
        self.smoke_tests = CodeReviewSmokeTests(project_root, mode)
        self.ai_detector = CodeReviewAIDetector(project_root, mode)
        self.analysis = CodeReviewAnalysis(project_root, recent_commits)
        
        # Consolidated results
        self.issues = {"critical": [], "high": [], "medium": [], "low": []}
        self.smoke_test_results = {}
        self.spec_code_conflicts = []
        self.ai_issues_found = []
        self.performance_concerns = []
        self.security_issues = []
        self.recent_changes = []

    def run_smoke_tests(self) -> bool:
        """Run critical system smoke tests"""
        result = self.smoke_tests.run_smoke_tests()
        self._consolidate_smoke_test_results()
        return result

    def _consolidate_smoke_test_results(self):
        """Consolidate smoke test results from sub-module"""
        self.smoke_test_results = self.smoke_tests.smoke_test_results
        self._merge_issues(self.smoke_tests.issues)

    def analyze_recent_changes(self):
        """Analyze recent git changes for potential issues"""
        self.analysis.analyze_recent_changes()
        self._consolidate_analysis_results()

    def _consolidate_analysis_results(self):
        """Consolidate analysis results from sub-module"""
        self.recent_changes = self.analysis.recent_changes
        self._merge_issues(self.analysis.issues)

    def check_spec_code_alignment(self):
        """Check alignment between specifications and code"""
        self.analysis.check_spec_code_alignment()
        self.spec_code_conflicts = self.analysis.spec_code_conflicts
        self._merge_issues(self.analysis.issues)

    def detect_ai_coding_issues(self):
        """Detect common issues from AI-assisted coding"""
        self.ai_detector.detect_ai_coding_issues()
        self._consolidate_ai_detector_results()

    def _consolidate_ai_detector_results(self):
        """Consolidate AI detector results from sub-module"""
        self.ai_issues_found = self.ai_detector.ai_issues_found
        self._merge_issues(self.ai_detector.issues)

    def check_performance_issues(self):
        """Check for potential performance problems"""
        self.analysis.check_performance_issues()
        self.performance_concerns = self.analysis.performance_concerns
        self._merge_issues(self.analysis.issues)

    def check_security_issues(self):
        """Check for security vulnerabilities"""
        self.analysis.check_security_issues()
        self.security_issues = self.analysis.security_issues
        self._merge_issues(self.analysis.issues)

    def _merge_issues(self, module_issues):
        """Merge issues from a sub-module into main issues"""
        for level in ["critical", "high", "medium", "low"]:
            if level in module_issues:
                self.issues[level].extend(module_issues[level])