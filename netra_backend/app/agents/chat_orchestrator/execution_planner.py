"""Execution planning for NACIS Chat Orchestrator.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Generates optimal execution plans based on intent and confidence.
"""

from typing import Dict, List

from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.chat_orchestrator.confidence_manager import ConfidenceLevel
from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentType


class ExecutionPlanner:
    """Generates dynamic execution plans for agent pipelines."""
    
    def __init__(self):
        self._init_domain_mappings()
        self._init_intent_requirements()
    
    def _init_domain_mappings(self) -> None:
        """Initialize intent to domain mappings."""
        self.domain_mapping = {
            IntentType.TCO_ANALYSIS: "finance",
            IntentType.OPTIMIZATION_ADVICE: "engineering",
            IntentType.MARKET_RESEARCH: "business",
            IntentType.PRICING_INQUIRY: "pricing",
            IntentType.BENCHMARKING: "performance",
        }
    
    def _init_intent_requirements(self) -> None:
        """Initialize intent-specific requirements."""
        self.volatile_intents = [IntentType.PRICING_INQUIRY, IntentType.BENCHMARKING]
        self.complex_intents = [IntentType.TCO_ANALYSIS, IntentType.BENCHMARKING]
        self.domain_intents = [IntentType.TCO_ANALYSIS, IntentType.OPTIMIZATION_ADVICE]
    
    async def generate_plan(self, context: ExecutionContext, 
                           intent: IntentType, confidence: float) -> List[Dict]:
        """Generate execution plan based on context."""
        plan = []
        self._add_research_step(plan, intent, confidence)
        self._add_domain_step(plan, intent)
        self._add_analysis_step(plan, intent)
        self._add_validation_step(plan)
        return plan
    
    def _add_research_step(self, plan: List[Dict], intent: IntentType, 
                          confidence: float) -> None:
        """Add research step if needed."""
        needs_research = self._needs_research(intent, confidence)
        if needs_research:
            plan.append(self._create_research_step(intent))
    
    def _needs_research(self, intent: IntentType, confidence: float) -> bool:
        """Determine if research is needed."""
        if confidence < ConfidenceLevel.HIGH.value:
            return True
        if intent in self.volatile_intents:
            return True
        return False
    
    def _create_research_step(self, intent: IntentType) -> Dict:
        """Create research step configuration."""
        return {
            "agent": "researcher",
            "action": "deep_research",
            "params": {"intent": intent.value, "require_citations": True}
        }
    
    def _add_domain_step(self, plan: List[Dict], intent: IntentType) -> None:
        """Add domain expert step if needed."""
        if intent in self.domain_intents:
            domain = self.domain_mapping.get(intent, "general")
            plan.append(self._create_domain_step(domain))
    
    def _create_domain_step(self, domain: str) -> Dict:
        """Create domain expert step configuration."""
        return {
            "agent": "domain_expert",
            "action": "validate_requirements",
            "params": {"domain": domain}
        }
    
    def _add_analysis_step(self, plan: List[Dict], intent: IntentType) -> None:
        """Add analysis step if needed."""
        if intent in self.complex_intents:
            plan.append(self._create_analysis_step(intent))
    
    def _create_analysis_step(self, intent: IntentType) -> Dict:
        """Create analysis step configuration."""
        return {
            "agent": "analyst",
            "action": "perform_analysis",
            "params": {"analysis_type": intent.value}
        }
    
    def _add_validation_step(self, plan: List[Dict]) -> None:
        """Add validation step (always required)."""
        plan.append({
            "agent": "validator",
            "action": "validate_response",
            "params": {"check_citations": True, "check_accuracy": True}
        })