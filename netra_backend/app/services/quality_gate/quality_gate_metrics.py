"""Quality Gate Service Metrics Calculations - Main Coordinator"""

from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.quality_gate.metrics_core import CoreMetricsCalculator
from netra_backend.app.services.quality_gate.metrics_specialized import (
    SpecializedMetricsCalculator,
)
from netra_backend.app.services.quality_gate.quality_gate_models import (
    ContentType,
    QualityMetrics,
)
from netra_backend.app.services.quality_gate.quality_gate_patterns import (
    QualityPatterns,
)

logger = central_logger.get_logger(__name__)


class QualityGateMetricsCalculator:
    """Main coordinator for quality metrics calculations"""
    
    def __init__(self, patterns: QualityPatterns, redis_manager=None):
        self.patterns = patterns
        self.redis_manager = redis_manager
        
        # Initialize specialized calculators
        self.core_calculator = CoreMetricsCalculator(patterns, redis_manager)
        self.specialized_calculator = SpecializedMetricsCalculator(patterns, redis_manager)
    
    async def calculate_metrics(
        self,
        content: str,
        content_type: ContentType,
        context: Optional[Dict[str, Any]]
    ) -> QualityMetrics:
        """Calculate comprehensive quality metrics for content"""
        # Start with basic metrics
        metrics = await self.core_calculator.calculate_basic_metrics(content)
        
        # Calculate core quality scores
        metrics.specificity_score = await self.core_calculator.calculate_specificity(content, content_type)
        metrics.actionability_score = await self.core_calculator.calculate_actionability(content, content_type)
        metrics.quantification_score = await self.core_calculator.calculate_quantification(content)
        metrics.clarity_score = await self.core_calculator.calculate_clarity(content)
        metrics.redundancy_ratio = await self.core_calculator.calculate_redundancy(content)
        
        # Calculate specialized metrics
        metrics.relevance_score = await self.specialized_calculator.calculate_relevance(content, context)
        metrics.completeness_score = await self.specialized_calculator.calculate_completeness(content, content_type)
        metrics.novelty_score = await self.specialized_calculator.calculate_novelty(content)
        metrics.hallucination_risk = await self.specialized_calculator.calculate_hallucination_risk(content, context)
        
        return metrics
    
    # Delegation methods for backward compatibility
    async def calculate_specificity(self, content: str, content_type: ContentType) -> float:
        """Delegate to core calculator"""
        return await self.core_calculator.calculate_specificity(content, content_type)
    
    async def calculate_actionability(self, content: str, content_type: ContentType) -> float:
        """Delegate to core calculator"""
        return await self.core_calculator.calculate_actionability(content, content_type)
    
    async def calculate_quantification(self, content: str) -> float:
        """Delegate to core calculator"""
        return await self.core_calculator.calculate_quantification(content)
    
    async def calculate_relevance(self, content: str, context: Optional[Dict[str, Any]]) -> float:
        """Delegate to specialized calculator"""
        return await self.specialized_calculator.calculate_relevance(content, context)
    
    async def calculate_completeness(self, content: str, content_type: ContentType) -> float:
        """Delegate to specialized calculator"""
        return await self.specialized_calculator.calculate_completeness(content, content_type)
    
    async def calculate_novelty(self, content: str) -> float:
        """Delegate to specialized calculator"""
        return await self.specialized_calculator.calculate_novelty(content)
    
    async def calculate_clarity(self, content: str) -> float:
        """Delegate to core calculator"""
        return await self.core_calculator.calculate_clarity(content)
    
    async def calculate_redundancy(self, content: str) -> float:
        """Delegate to core calculator"""
        return await self.core_calculator.calculate_redundancy(content)
    
    async def calculate_hallucination_risk(self, content: str, context: Optional[Dict[str, Any]]) -> float:
        """Delegate to specialized calculator"""
        return await self.specialized_calculator.calculate_hallucination_risk(content, context)