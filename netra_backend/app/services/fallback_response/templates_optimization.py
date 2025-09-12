"""Optimization Templates - Templates for AI optimization failures and guidance.

This module provides templates for optimization-related content types and failures
with 25-line function compliance.
"""

from typing import Dict, List, Tuple

from netra_backend.app.services.fallback_response.models import FailureReason
from netra_backend.app.services.quality_gate_service import ContentType


class OptimizationTemplates:
    """Optimization-focused template provider."""
    
    def get_templates(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get all optimization templates."""
        return {
            **self._get_low_quality_mapping(),
            **self._get_context_mapping(),
            **self._get_circular_mapping()
        }
    
    def _get_low_quality_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get low quality templates mapping."""
        return {(ContentType.OPTIMIZATION, FailureReason.LOW_QUALITY): 
                self._get_low_quality_templates()}
    
    def _get_context_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get context missing templates mapping."""
        return {(ContentType.OPTIMIZATION, FailureReason.CONTEXT_MISSING): 
                self._get_context_templates()}
    
    def _get_circular_mapping(self) -> Dict[Tuple[ContentType, FailureReason], List[str]]:
        """Get circular reasoning templates mapping."""
        return {(ContentType.OPTIMIZATION, FailureReason.CIRCULAR_REASONING): 
                self._get_circular_templates()}
    
    def _get_low_quality_templates(self) -> List[str]:
        """Get templates for optimization low quality failures."""
        return [
            self._get_info_request_template(),
            self._get_context_template(),
            self._get_stepwise_template()
        ]
    
    def _get_context_templates(self) -> List[str]:
        """Get templates for optimization context missing failures."""
        return [
            self._get_key_info_template(),
            self._get_setup_template()
        ]
    
    def _get_circular_templates(self) -> List[str]:
        """Get templates for optimization circular reasoning failures."""
        return [
            self._get_concrete_template(),
            self._get_practical_template()
        ]
    
    def _get_info_request_template(self) -> str:
        """Get optimization info request template."""
        intro = "I need more specific information about your {context} to provide actionable optimization recommendations."
        requirements = self._build_info_requirements()
        conclusion = "This will help me generate specific, measurable optimization strategies."
        return f"{intro} Could you provide:\n{requirements}{conclusion}"
    
    def _build_info_requirements(self) -> str:
        """Build information requirements list."""
        return ("[U+2022] Current performance metrics (latency, throughput)\n"
                "[U+2022] Resource constraints (memory, compute)\n"
                "[U+2022] Target improvements (e.g., 20% latency reduction)\n")
    
    def _get_context_template(self) -> str:
        """Get optimization context template."""
        intro = "The optimization analysis for {context} requires additional context."
        purpose = "To provide value-driven recommendations, I need:"
        requirements = self._build_context_requirements()
        conclusion = "With this information, I can suggest targeted optimizations with expected improvements."
        return f"{intro} {purpose}\n{requirements}{conclusion}"
    
    def _build_context_requirements(self) -> str:
        """Build context requirements list."""
        return ("[U+2022] Baseline performance data\n"
                "[U+2022] System architecture details\n"
                "[U+2022] Specific bottlenecks you're experiencing\n")
    
    def _get_stepwise_template(self) -> str:
        """Get optimization stepwise template."""
        intro = "After multiple attempts to optimize {context}, let's try a different approach."
        request = "Please consider:"
        steps = self._build_stepwise_steps()
        conclusion = "Sometimes a step-by-step approach yields better results."
        return f"{intro} {request}\n{steps}{conclusion}"
    
    def _build_stepwise_steps(self) -> str:
        """Build stepwise optimization steps."""
        return ("[U+2022] Breaking the optimization into smaller, more focused tasks\n"
                "[U+2022] Providing a simplified version of your requirements\n"
                "[U+2022] Starting with basic performance profiling first\n"
                "[U+2022] Describing the most critical performance issue only\n")
    
    def _get_key_info_template(self) -> str:
        """Get optimization key info template."""
        intro = "To optimize {context} effectively, I need key information:"
        requirements = self._build_key_requirements()
        conclusion = "Please provide these details for targeted optimization recommendations."
        return f"{intro}\n{requirements}{conclusion}"
    
    def _build_key_requirements(self) -> str:
        """Build key information requirements."""
        return ("[U+2022] Model/system specifications\n"
                "[U+2022] Current configuration parameters\n"
                "[U+2022] Performance requirements\n"
                "[U+2022] Available resources\n")
    
    def _get_setup_template(self) -> str:
        """Get optimization setup template."""
        intro = "Optimization requires understanding your specific setup."
        context = "For {context}, please share:"
        requirements = self._build_setup_requirements()
        conclusion = "This enables me to provide quantified improvement strategies."
        return f"{intro} {context}\n{requirements}{conclusion}"
    
    def _build_setup_requirements(self) -> str:
        """Build setup requirements list."""
        return ("[U+2022] Current implementation details\n"
                "[U+2022] Performance metrics you're tracking\n"
                "[U+2022] Constraints or limitations\n")
    
    def _get_concrete_template(self) -> str:
        """Get concrete optimization template."""
        intro = "Let me provide a more concrete optimization approach for {context}:"
        steps = self._build_concrete_steps()
        conclusion = "Would you like me to elaborate on any of these steps?"
        return f"{intro}\n{steps}{conclusion}"
    
    def _build_concrete_steps(self) -> str:
        """Build concrete optimization steps."""
        return ("1. **Measure**: First, profile your current system using tools like [specific profiler]\n"
                "2. **Identify**: Look for bottlenecks in [specific areas]\n"
                "3. **Apply**: Implement specific techniques like [concrete optimization]\n"
                "4. **Verify**: Measure improvements against baseline\n")
    
    def _get_practical_template(self) -> str:
        """Get practical optimization template."""
        intro = "I'll be more specific about optimizing {context}."
        approach = "Here's a practical approach:"
        steps = self._build_practical_steps()
        conclusion = "Each includes measurable impact. Which would you like to explore first?"
        return f"{intro} {approach}\n{steps}{conclusion}"
    
    def _build_practical_steps(self) -> str:
        """Build practical optimization steps."""
        return ("[U+2022] **Quick win**: [Specific easy optimization]\n"
                "[U+2022] **Medium effort**: [Specific moderate optimization]\n"
                "[U+2022] **Major improvement**: [Specific significant optimization]\n")