"""Quality metrics aggregator.

Orchestrates all quality calculators and provides comprehensive metrics.
Follows 450-line limit with 25-line function limit.
"""

from netra_backend.app.services.factory_status.metrics_architecture_compliance import (
    ArchitectureComplianceCalculator,
)
from netra_backend.app.services.factory_status.metrics_documentation import (
    DocumentationCalculator,
)
from netra_backend.app.services.factory_status.metrics_quality_types import (
    ArchitectureCompliance,
    DocumentationMetrics,
    QualityLevel,
    QualityMetrics,
    TechnicalDebt,
    TestCoverageMetrics,
)
from netra_backend.app.services.factory_status.metrics_technical_debt import (
    TechnicalDebtCalculator,
)
from netra_backend.app.services.factory_status.metrics_test_coverage import (
    TestCoverageCalculator,
)


class QualityAggregator:
    """Aggregates all quality metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize quality aggregator."""
        self.coverage_calc = TestCoverageCalculator(repo_path)
        self.docs_calc = DocumentationCalculator(repo_path)
        self.arch_calc = ArchitectureComplianceCalculator(repo_path)
        self.debt_calc = TechnicalDebtCalculator(repo_path)
        self.repo_path = repo_path
    
    def calculate_quality_metrics(self) -> QualityMetrics:
        """Calculate comprehensive quality metrics."""
        coverage = self.coverage_calc.calculate_test_coverage()
        docs = self.docs_calc.assess_documentation_quality()
        architecture = self.arch_calc.check_architecture_compliance()
        debt = self.debt_calc.calculate_technical_debt()
        
        overall_score = self._calculate_overall_quality_score(
            coverage, docs, architecture, debt
        )
        quality_level = self._determine_quality_level(overall_score)
        
        return QualityMetrics(
            test_coverage=coverage,
            documentation=docs,
            architecture=architecture,
            technical_debt=debt,
            overall_quality_score=overall_score,
            quality_level=quality_level
        )
    
    def _calculate_overall_quality_score(self, coverage: TestCoverageMetrics,
                                        docs: DocumentationMetrics,
                                        arch: ArchitectureCompliance,
                                        debt: TechnicalDebt) -> float:
        """Calculate overall quality score."""
        scores = self._extract_normalized_scores(coverage, docs, arch, debt)
        weights = [0.3, 0.2, 0.3, 0.2]
        
        return sum(w * s for w, s in zip(weights, scores))
    
    def _extract_normalized_scores(self, coverage: TestCoverageMetrics,
                                  docs: DocumentationMetrics,
                                  arch: ArchitectureCompliance,
                                  debt: TechnicalDebt) -> list:
        """Extract and normalize scores from metrics."""
        coverage_score = coverage.overall_coverage
        docs_score = self._normalize_docs_score(docs.documentation_quality)
        arch_score = arch.compliance_score
        debt_score = max(0, 100 - debt.debt_score * 10)
        
        return [coverage_score, docs_score, arch_score, debt_score]
    
    def _normalize_docs_score(self, quality_level: QualityLevel) -> float:
        """Normalize documentation quality to numeric score."""
        quality_scores = {
            QualityLevel.EXCELLENT: 90,
            QualityLevel.GOOD: 75,
            QualityLevel.ACCEPTABLE: 60,
            QualityLevel.NEEDS_IMPROVEMENT: 40,
            QualityLevel.POOR: 20
        }
        return quality_scores.get(quality_level, 50)
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level from score."""
        if score >= 90:
            return QualityLevel.EXCELLENT
        elif score >= 75:
            return QualityLevel.GOOD
        elif score >= 60:
            return QualityLevel.ACCEPTABLE
        elif score >= 40:
            return QualityLevel.NEEDS_IMPROVEMENT
        return QualityLevel.POOR