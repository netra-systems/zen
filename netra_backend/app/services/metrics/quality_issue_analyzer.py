"""
Quality issue analysis for corpus operations
Handles issue categorization, tracking, and analysis
"""

from typing import Dict, List, Any
from collections import defaultdict

from netra_backend.app.schemas.Metrics import QualityMetrics


class QualityIssueAnalyzer:
    """Analyzes and categorizes quality issues"""
    
    def __init__(self):
        self._issue_tracker = defaultdict(lambda: defaultdict(int))
    
    async def analyze_issues(self, corpus_id: str, metrics: QualityMetrics):
        """Analyze and track quality issues"""
        for issue in metrics.issues_detected:
            self._issue_tracker[corpus_id][issue] += 1
    
    def get_issue_analysis(self, corpus_id: str) -> Dict[str, Any]:
        """Get analysis of detected issues"""
        issues = self._issue_tracker.get(corpus_id, {})
        total_issues = sum(issues.values())
        
        if total_issues == 0:
            return self._get_empty_issue_analysis()
        
        sorted_issues = sorted(issues.items(), key=lambda x: x[1], reverse=True)
        return self._build_issue_analysis(total_issues, sorted_issues, issues)
    
    def _get_empty_issue_analysis(self) -> Dict[str, Any]:
        """Get empty issue analysis."""
        return {"total_issues": 0, "top_issues": [], "issue_categories": {}}
    
    def _build_issue_analysis(self, total_issues: int, sorted_issues: List, issues: Dict[str, int]) -> Dict[str, Any]:
        """Build issue analysis from components."""
        return {
            "total_issues": total_issues,
            "top_issues": sorted_issues[:5],
            "issue_categories": self._categorize_issues(issues),
            "unique_issue_types": len(issues)
        }
    
    def _categorize_issues(self, issues: Dict[str, int]) -> Dict[str, int]:
        """Categorize issues by type"""
        categories = self._initialize_issue_categories()
        
        for issue_type, count in issues.items():
            category = self._classify_issue(issue_type)
            categories[category] += count
        
        return categories
    
    def _initialize_issue_categories(self) -> Dict[str, int]:
        """Initialize empty issue categories."""
        return {
            "data_quality": 0,
            "validation": 0,
            "completeness": 0,
            "consistency": 0,
            "other": 0
        }
    
    def _classify_issue(self, issue_type: str) -> str:
        """Classify issue into category"""
        issue_lower = issue_type.lower()
        
        if self._is_completeness_issue(issue_lower):
            return "completeness"
        elif self._is_validation_issue(issue_lower):
            return "validation"
        elif self._is_consistency_issue(issue_lower):
            return "consistency"
        elif self._is_data_quality_issue(issue_lower):
            return "data_quality"
        else:
            return "other"
    
    def _is_completeness_issue(self, issue_lower: str) -> bool:
        """Check if issue is completeness-related."""
        return any(keyword in issue_lower for keyword in ["missing", "empty", "null", "incomplete"])
    
    def _is_validation_issue(self, issue_lower: str) -> bool:
        """Check if issue is validation-related."""
        return any(keyword in issue_lower for keyword in ["validation", "format", "type", "schema"])
    
    def _is_consistency_issue(self, issue_lower: str) -> bool:
        """Check if issue is consistency-related."""
        return any(keyword in issue_lower for keyword in ["duplicate", "conflict", "mismatch"])
    
    def _is_data_quality_issue(self, issue_lower: str) -> bool:
        """Check if issue is data quality-related."""
        return any(keyword in issue_lower for keyword in ["quality", "accuracy", "integrity"])
    
    def get_total_issues_tracked(self) -> int:
        """Get total number of issues tracked across all corpora."""
        return sum(len(issues) for issues in self._issue_tracker.values())