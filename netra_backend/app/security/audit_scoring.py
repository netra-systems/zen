"""
Security compliance scoring and recommendation engine.
Calculates compliance scores and generates security recommendations.
"""

from typing import Dict, List

from netra_backend.app.security.audit_findings import (
    SecurityCategory,
    SecurityFinding,
    SecuritySeverity,
)


class ComplianceScoreCalculator:
    """Calculates compliance scores based on security findings."""
    
    def calculate_scores(self, findings: List[SecurityFinding]) -> Dict[str, float]:
        """Calculate compliance scores based on findings."""
        category_findings = self._group_findings_by_category(findings)
        scores = self._calculate_category_scores(category_findings)
        scores["overall"] = self._calculate_overall_score(scores)
        return scores
    
    def _group_findings_by_category(self, findings: List[SecurityFinding]) -> Dict[str, List[SecurityFinding]]:
        """Group findings by category."""
        category_findings = {}
        for finding in findings:
            category = finding.category.value
            if category not in category_findings:
                category_findings[category] = []
            category_findings[category].append(finding)
        return category_findings
    
    def _calculate_category_scores(self, category_findings: Dict[str, List[SecurityFinding]]) -> Dict[str, float]:
        """Calculate scores for each category."""
        scores = {}
        for category, cat_findings in category_findings.items():
            scores[category] = self._calculate_single_category_score(cat_findings)
        return scores
    
    def _calculate_single_category_score(self, findings: List[SecurityFinding]) -> float:
        """Calculate score for a single category."""
        severity_weights = self._get_severity_weights()
        total_weight = sum(severity_weights[f.severity] for f in findings)
        max_possible = len(findings) * severity_weights[SecuritySeverity.CRITICAL]
        if max_possible == 0:
            return 1.0
        return max(0.0, 1.0 - (total_weight / max_possible))
    
    def _get_severity_weights(self) -> Dict[SecuritySeverity, int]:
        """Get severity weight mapping."""
        return {
            SecuritySeverity.CRITICAL: 10,
            SecuritySeverity.HIGH: 5,
            SecuritySeverity.MEDIUM: 2,
            SecuritySeverity.LOW: 1,
            SecuritySeverity.INFO: 0
        }
    
    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """Calculate overall compliance score."""
        if not scores:
            return 1.0
        return sum(scores.values()) / len(scores)


class SecurityRecommendationEngine:
    """Generates security recommendations based on findings."""
    
    def generate_recommendations(self, findings: List[SecurityFinding]) -> List[str]:
        """Generate high-level recommendations."""
        recommendations = []
        severity_counts = self._count_findings_by_severity(findings)
        self._add_critical_recommendations(recommendations, severity_counts)
        self._add_high_severity_recommendations(recommendations, severity_counts)
        self._add_category_recommendations(recommendations, findings)
        self._add_general_recommendations(recommendations)
        return recommendations
    
    def _count_findings_by_severity(self, findings: List[SecurityFinding]) -> Dict[SecuritySeverity, int]:
        """Count findings by severity."""
        severity_counts = {}
        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
        return severity_counts
    
    def _add_critical_recommendations(self, recommendations: List[str], severity_counts: Dict[SecuritySeverity, int]) -> None:
        """Add recommendations for critical findings."""
        if severity_counts.get(SecuritySeverity.CRITICAL, 0) > 0:
            recommendations.append("Immediately address all CRITICAL security findings before production deployment")
    
    def _add_high_severity_recommendations(self, recommendations: List[str], severity_counts: Dict[SecuritySeverity, int]) -> None:
        """Add recommendations for high severity findings."""
        if severity_counts.get(SecuritySeverity.HIGH, 0) > 2:
            recommendations.append("Implement a security remediation plan for HIGH severity findings")
    
    def _add_category_recommendations(self, recommendations: List[str], findings: List[SecurityFinding]) -> None:
        """Add category-specific recommendations."""
        auth_findings = [f for f in findings if f.category == SecurityCategory.AUTHENTICATION]
        api_findings = [f for f in findings if f.category == SecurityCategory.API_SECURITY]
        if auth_findings:
            recommendations.append("Review and strengthen authentication mechanisms")
        if api_findings:
            recommendations.append("Implement comprehensive API security controls")
    
    def _add_general_recommendations(self, recommendations: List[str]) -> None:
        """Add general security recommendations."""
        recommendations.append("Schedule regular security audits (weekly recommended)")
        recommendations.append("Implement automated security monitoring and alerting")


# Global instances
compliance_score_calculator = ComplianceScoreCalculator()
security_recommendation_engine = SecurityRecommendationEngine()