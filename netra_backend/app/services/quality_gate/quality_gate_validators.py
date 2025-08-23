"""Quality Gate Service Validators and Threshold Checking"""

from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.core.interfaces_quality import (
    QualityValidator as CoreQualityValidator,
)
from netra_backend.app.core.quality_types import (
    ContentType,
    QualityLevel,
    QualityMetrics,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.quality_types import (
    QualityValidationResult,
    QualityValidatorInterface,
)

logger = central_logger.get_logger(__name__)


class QualityValidator(QualityValidatorInterface):
    """Validate content quality against thresholds - delegates to core implementation"""
    
    def __init__(self):
        """Initialize quality validator using core implementation."""
        self._core_validator = CoreQualityValidator()
    
    def get_weights_for_type(self, content_type: ContentType) -> Dict[str, float]:
        """Get scoring weights based on content type"""
        return self._core_validator.get_weights_for_type(content_type)
    
    def calculate_weighted_score(self, metrics: QualityMetrics, weights: Dict[str, float]) -> float:
        """Calculate weighted overall score"""
        return self._core_validator.calculate_weighted_score(metrics, weights)
    
    def determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level from score"""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.7:
            return QualityLevel.GOOD
        elif score >= 0.5:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.3:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE
    
    def check_thresholds(
        self,
        metrics: QualityMetrics,
        content_type: ContentType,
        strict_mode: bool
    ) -> bool:
        """Check if metrics meet thresholds for the content type"""
        return self._core_validator.check_thresholds(metrics, content_type, strict_mode)
    
    def generate_suggestions(self, metrics: QualityMetrics, content_type: ContentType) -> List[str]:
        """Generate improvement suggestions based on metrics"""
        return self._core_validator.generate_suggestions(metrics, content_type)
    
    def generate_prompt_adjustments(self, metrics: QualityMetrics) -> Dict[str, Any]:
        """Generate prompt adjustments for retry based on quality issues"""
        return self._core_validator.generate_prompt_adjustments(metrics)
    
    # Interface Implementation Methods
    async def validate_content(
        self, 
        content: str, 
        content_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> QualityValidationResult:
        """Validate content and return detailed quality results"""
        from datetime import UTC, datetime

        from netra_backend.app.services.quality_gate_service import QualityGateService
        
        # Convert string content_type to ContentType enum
        content_type_enum = self._convert_content_type(content_type)
        
        # Create QualityGateService instance to perform full validation
        service = QualityGateService()
        validation_result = await service.validate_content(
            content=content,
            content_type=content_type_enum,
            context=context or {},
            strict_mode=False
        )
        
        return validation_result
    
    def _convert_content_type(self, content_type: Optional[str]) -> ContentType:
        """Convert string content type to ContentType enum"""
        if not content_type:
            return ContentType.GENERAL
        
        try:
            return ContentType(content_type.lower())
        except ValueError:
            return ContentType.GENERAL
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            "validator_type": "QualityGateValidator",
            "has_core_validator": True,
            "supported_content_types": [ct.value for ct in ContentType],
            "validation_capabilities": [
                "threshold_checking", "scoring", "improvement_suggestions",
                "prompt_adjustments", "quality_level_determination"
            ]
        }