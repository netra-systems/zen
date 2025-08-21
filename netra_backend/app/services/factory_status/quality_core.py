"""Core types and interfaces for quality metrics.

Defines enums, dataclasses and interfaces for quality assessment.
Module follows 450-line limit with 25-line function limit.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class QualityLevel(Enum):
    """Quality assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    NEEDS_IMPROVEMENT = "needs_improvement"
    POOR = "poor"


class ComplianceStatus(Enum):
    """Architecture compliance status."""
    COMPLIANT = "compliant"
    MINOR_VIOLATIONS = "minor_violations"
    MAJOR_VIOLATIONS = "major_violations"
    NON_COMPLIANT = "non_compliant"


@dataclass
class TestCoverageMetrics:
    """Test coverage tracking metrics."""
    overall_coverage: float
    line_coverage: float
    function_coverage: float
    branch_coverage: float
    test_files_count: int
    source_files_count: int
    coverage_trend: float
    uncovered_critical_files: List[str]


@dataclass
class DocumentationMetrics:
    """Documentation quality metrics."""
    docstring_coverage: float
    readme_updated: bool
    api_docs_updated: bool
    spec_files_updated: int
    comment_density: float
    documentation_quality: QualityLevel


@dataclass
class ArchitectureCompliance:
    """Architecture compliance assessment."""
    line_limit_violations: int
    function_limit_violations: int
    module_violations: List[str]
    compliance_score: float
    compliance_status: ComplianceStatus
    violation_details: Dict[str, int]


@dataclass
class TechnicalDebt:
    """Technical debt metrics."""
    code_smells: int
    duplication_percentage: float
    complexity_hotspots: List[str]
    deprecated_usage: int
    todo_count: int
    debt_score: float
    debt_trend: float


@dataclass
class QualityMetrics:
    """Comprehensive quality metrics."""
    test_coverage: TestCoverageMetrics
    documentation: DocumentationMetrics
    architecture: ArchitectureCompliance
    technical_debt: TechnicalDebt
    overall_quality_score: float
    quality_level: QualityLevel


class QualityConstants:
    """Constants for quality calculations."""
    
    MAX_LINES_PER_FILE = 300
    MAX_LINES_PER_FUNCTION = 8
    
    CRITICAL_FILES = [
        "app/auth", "app/db", "app/core", "app/llm",
        "app/websocket", "frontend/components/chat"
    ]