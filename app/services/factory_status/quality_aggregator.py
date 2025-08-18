"""Quality metrics aggregation module.

Aggregates quality metrics from all calculators.
Follows 300-line limit with 8-line function limit.
"""

from .quality_models import (
    QualityMetrics, QualityLevel, TestCoverageMetrics,
    DocumentationMetrics, ArchitectureCompliance, TechnicalDebt
)
from .test_coverage_calculator import TestCoverageCalculator
from .documentation_assessor import DocumentationAssessor
from .architecture_compliance_checker import ArchitectureComplianceChecker
from .metrics_technical_debt import TechnicalDebtCalculator


class QualityAggregator:
    """Aggregator for comprehensive quality metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize quality aggregator."""
        self.coverage_calc = TestCoverageCalculator(repo_path)
        self.doc_assessor = DocumentationAssessor(repo_path)
        self.compliance_checker = ArchitectureComplianceChecker(repo_path)
        self.debt_calc = TechnicalDebtCalculator(repo_path)
    
    def calculate_metrics(self) -> QualityMetrics:
        """Calculate comprehensive quality metrics."""
        quality_components = self._gather_all_quality_components()
        overall_score = self._calculate_overall_score(**quality_components)
        return self._build_quality_metrics(quality_components, overall_score)
    
    def _gather_all_quality_components(self) -> dict:
        """Gather all quality components from calculators."""
        return {
            'coverage': self.coverage_calc.calculate_coverage(),
            'docs': self.doc_assessor.assess_quality(),
            'architecture': self.compliance_checker.check_compliance(),
            'debt': self.debt_calc.calculate_debt()
        }
    
    def _build_quality_metrics(self, components: dict, overall_score: float) -> QualityMetrics:
        """Build final quality metrics object."""
        quality_level = self._determine_quality_level(overall_score)
        return QualityMetrics(
            test_coverage=components['coverage'],
            documentation=components['docs'],
            architecture=components['architecture'],
            technical_debt=components['debt'],
            overall_quality_score=overall_score,
            quality_level=quality_level
        )
    
    def _calculate_overall_score(self, coverage: TestCoverageMetrics,
                               docs: DocumentationMetrics,
                               arch: ArchitectureCompliance,
                               debt: TechnicalDebt) -> float:
        """Calculate overall quality score."""
        component_scores = self._extract_component_scores(coverage, docs, arch, debt)
        return self._weighted_average(component_scores)
    
    def _extract_component_scores(self, coverage: TestCoverageMetrics, docs: DocumentationMetrics,
                                 arch: ArchitectureCompliance, debt: TechnicalDebt) -> list:
        """Extract numeric scores from all quality components."""
        return [
            (coverage.overall_coverage, 0.3),
            (self._get_docs_score(docs.documentation_quality), 0.2),
            (arch.compliance_score, 0.3),
            (self._get_debt_score(debt.debt_score), 0.2)
        ]
    
    def _get_docs_score(self, quality: QualityLevel) -> float:
        """Convert documentation quality to numeric score."""
        quality_scores = {
            QualityLevel.EXCELLENT: 90,
            QualityLevel.GOOD: 75,
            QualityLevel.ACCEPTABLE: 60,
            QualityLevel.NEEDS_IMPROVEMENT: 40,
            QualityLevel.POOR: 20
        }
        return quality_scores.get(quality, 60)
    
    def _get_debt_score(self, debt_score: float) -> float:
        """Convert debt score to quality score."""
        return max(0, 100 - debt_score * 10)
    
    def _weighted_average(self, score_weight_pairs: list) -> float:
        """Calculate weighted average of scores."""
        total_score = sum(score * weight for score, weight in score_weight_pairs)
        return total_score
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level from overall score."""
        if score >= 90:
            return QualityLevel.EXCELLENT
        elif score >= 75:
            return QualityLevel.GOOD
        elif score >= 60:
            return QualityLevel.ACCEPTABLE
        elif score >= 40:
            return QualityLevel.NEEDS_IMPROVEMENT
        return QualityLevel.POOR
