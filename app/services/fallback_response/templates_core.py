"""Core Template Manager - Central orchestrator for fallback response templates.

This module provides the main interface for template management with strong typing
and modular architecture compliance.
"""

from typing import Dict, List, Tuple

from app.services.quality_gate_service import ContentType
from .models import FailureReason
from .templates_optimization import OptimizationTemplates
from .templates_data import DataTemplates  
from .templates_reports import ReportTemplates
from .templates_system import SystemTemplates


class TemplateManager:
    """Manages fallback response templates with modular architecture."""
    
    def __init__(self):
        """Initialize the template manager with modular components."""
        self._optimization = OptimizationTemplates()
        self._data = DataTemplates()
        self._reports = ReportTemplates()
        self._system = SystemTemplates()
        self._templates = self._build_template_registry()
    
    def _build_template_registry(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Build complete template registry from all modules."""
        templates = {}
        self._register_optimization_templates(templates)
        self._register_data_templates(templates)
        self._register_report_templates(templates)
        self._register_system_templates(templates)
        return templates
    
    def _register_optimization_templates(self, templates: dict) -> None:
        """Register optimization templates in registry."""
        templates.update(self._optimization.get_templates())
    
    def _register_data_templates(self, templates: dict) -> None:
        """Register data templates in registry."""
        templates.update(self._data.get_templates())
    
    def _register_report_templates(self, templates: dict) -> None:
        """Register report templates in registry."""
        templates.update(self._reports.get_templates())
    
    def _register_system_templates(self, templates: dict) -> None:
        """Register system templates in registry."""
        templates.update(self._system.get_templates())
    
    def get_template(self, content_type: ContentType, 
                    failure_reason: FailureReason, retry_count: int = 0) -> str:
        """Get template for content type and failure reason."""
        templates = self._find_templates(content_type, failure_reason)
        template_index = retry_count % len(templates)
        return templates[template_index]
    
    def _find_templates(self, content_type: ContentType, 
                       failure_reason: FailureReason) -> List[str]:
        """Find matching templates for content type and failure reason."""
        key = (content_type, failure_reason)
        if key in self._templates:
            return self._templates[key]
        return self._get_fallback_templates(failure_reason)
    
    def _get_fallback_templates(self, failure_reason: FailureReason) -> List[str]:
        """Get fallback templates for failure reason."""
        fallback_key = (ContentType.GENERAL, failure_reason)
        if fallback_key in self._templates:
            return self._templates[fallback_key]
        return self._get_generic_templates()
    
    def _get_generic_templates(self) -> List[str]:
        """Get generic fallback templates."""
        return [self._system.get_generic_template()]