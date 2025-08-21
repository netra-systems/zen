"""Violation Analysis for Factory Status Reporting."""

from typing import Dict, List, Any

from netra_backend.app.services.factory_status.spec_compliance_scorer import ViolationSeverity


class ViolationAnalyzer:
    """Handles analysis and categorization of compliance violations."""
    
    def summarize_violations(self, violations: List[Any]) -> Dict[str, int]:
        """Summarize violations by category."""
        summary = self._init_violation_summary()
        
        for violation in violations:
            self._categorize_violation(violation, summary)
        
        return summary
    
    def _init_violation_summary(self) -> Dict[str, int]:
        """Initialize violation summary structure."""
        return {
            "architecture_violations": 0,
            "type_safety_violations": 0,
            "missing_tests": 0,
            "documentation_gaps": 0
        }
    
    def _categorize_violation(self, violation: Any, summary: Dict[str, int]) -> None:
        """Categorize a single violation."""
        if "violation_type" not in violation:
            return
        
        self._increment_violation_count(violation["violation_type"], summary)
    
    def _increment_violation_count(self, vtype: str, summary: Dict[str, int]) -> None:
        """Increment violation count for given type."""
        if vtype in ["file_length", "function_length"]:
            summary["architecture_violations"] += 1
        elif vtype == "missing_types":
            summary["type_safety_violations"] += 1

    def get_critical_violations(self, violations: List[Any]) -> List[Dict]:
        """Get critical violations requiring immediate action."""
        critical = self._filter_critical_violations(violations)
        
        return critical[:10]  # Top 10 critical issues
    
    def _filter_critical_violations(self, violations: List[Any]) -> List[Dict]:
        """Filter and format critical violations."""
        critical = []
        for violation in violations:
            if self._is_critical_violation(violation):
                critical.append(self._format_critical_violation(violation))
        
        return critical
    
    def _is_critical_violation(self, violation: Any) -> bool:
        """Check if violation is critical severity."""
        return violation.get("severity") == ViolationSeverity.CRITICAL.value
    
    def _format_critical_violation(self, violation: Any) -> Dict[str, Any]:
        """Format critical violation for report."""
        return {
            "module": violation.get("module"),
            "type": violation.get("violation_type"),
            "description": violation.get("description"),
            "remediation": violation.get("remediation")
        }