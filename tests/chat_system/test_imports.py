"""Test all NACIS module imports.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Ensures all modules can be imported without errors.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest


class TestNACISImports:
    """Test all NACIS module imports work correctly."""
    
    def test_chat_orchestrator_imports(self):
        """Test chat orchestrator and helper imports."""
        # Main orchestrator
        from netra_backend.app.agents.chat_orchestrator import ChatOrchestrator
        
        # Helper modules
        from netra_backend.app.agents.chat_orchestrator.intent_classifier import (
            IntentClassifier, IntentType
        )
        from netra_backend.app.agents.chat_orchestrator.confidence_manager import (
            ConfidenceManager, ConfidenceLevel
        )
        from netra_backend.app.agents.chat_orchestrator.model_cascade import (
            ModelCascade, ModelTier
        )
        from netra_backend.app.agents.chat_orchestrator.execution_planner import (
            ExecutionPlanner
        )
        from netra_backend.app.agents.chat_orchestrator.pipeline_executor import (
            PipelineExecutor
        )
        from netra_backend.app.agents.chat_orchestrator.trace_logger import (
            TraceLogger
        )
        
        assert ChatOrchestrator is not None
        assert IntentClassifier is not None
        assert IntentType is not None
    
    def test_agent_imports(self):
        """Test all agent imports."""
        from netra_backend.app.agents.researcher import ResearcherAgent
        from netra_backend.app.agents.analyst import AnalystAgent
        from netra_backend.app.agents.validator import ValidatorAgent
        
        assert ResearcherAgent is not None
        assert AnalystAgent is not None
        assert ValidatorAgent is not None
    
    def test_domain_expert_imports(self):
        """Test domain expert imports."""
        from netra_backend.app.agents.domain_experts import (
            BaseDomainExpert,
            FinanceExpert,
            EngineeringExpert,
            BusinessExpert
        )
        
        assert BaseDomainExpert is not None
        assert FinanceExpert is not None
        assert EngineeringExpert is not None
        assert BusinessExpert is not None
    
    def test_tools_imports(self):
        """Test tools imports."""
        from netra_backend.app.tools import (
            DeepResearchAPI,
            ReliabilityScorer,
            SandboxedInterpreter
        )
        
        assert DeepResearchAPI is not None
        assert ReliabilityScorer is not None
        assert SandboxedInterpreter is not None
    
    def test_guardrails_imports(self):
        """Test guardrails imports."""
        from netra_backend.app.guardrails import (
            InputFilters,
            OutputValidators
        )
        
        assert InputFilters is not None
        assert OutputValidators is not None
    
    def test_semantic_cache_import(self):
        """Test semantic cache import."""
        from netra_backend.app.services.cache.semantic_cache import SemanticCache
        
        assert SemanticCache is not None
    
    def test_cross_module_imports(self):
        """Test imports work across modules."""
        # This tests that modules can import from each other
        from netra_backend.app.agents.chat_orchestrator import ChatOrchestrator
        from netra_backend.app.agents.researcher import ResearcherAgent
        from netra_backend.app.tools.reliability_scorer import ReliabilityScorer
        
        # Test that classes can reference each other's types
        assert ChatOrchestrator.__name__ == "ChatOrchestrator"
        assert ResearcherAgent.__name__ == "ResearcherAgent"
        assert ReliabilityScorer.__name__ == "ReliabilityScorer"
    
    def test_enum_imports(self):
        """Test enum imports work correctly."""
        from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentType
        from netra_backend.app.agents.chat_orchestrator.confidence_manager import ConfidenceLevel
        from netra_backend.app.agents.chat_orchestrator.model_cascade import ModelTier
        
        # Test enum values are accessible
        assert IntentType.TCO_ANALYSIS.value == "tco_analysis"
        assert ConfidenceLevel.HIGH.value == 0.9
        assert ModelTier.TIER1.value == "fast"
    
    def test_instantiation_without_dependencies(self):
        """Test basic instantiation of classes."""
        from netra_backend.app.tools.reliability_scorer import ReliabilityScorer
        from netra_backend.app.guardrails.input_filters import InputFilters
        from netra_backend.app.guardrails.output_validators import OutputValidators
        from netra_backend.app.agents.chat_orchestrator.trace_logger import TraceLogger
        
        # These should instantiate without external dependencies
        scorer = ReliabilityScorer()
        filters = InputFilters()
        validators = OutputValidators()
        logger = TraceLogger()
        
        assert scorer is not None
        assert filters is not None
        assert validators is not None
        assert logger is not None


def test_all_imports_in_function():
    """Test all imports work when done inside a function."""
    def import_all_modules():
        # Chat orchestrator modules
        from netra_backend.app.agents.chat_orchestrator import ChatOrchestrator
        from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentClassifier
        from netra_backend.app.agents.chat_orchestrator.confidence_manager import ConfidenceManager
        from netra_backend.app.agents.chat_orchestrator.model_cascade import ModelCascade
        from netra_backend.app.agents.chat_orchestrator.execution_planner import ExecutionPlanner
        from netra_backend.app.agents.chat_orchestrator.pipeline_executor import PipelineExecutor
        from netra_backend.app.agents.chat_orchestrator.trace_logger import TraceLogger
        
        # Agent modules
        from netra_backend.app.agents.researcher import ResearcherAgent
        from netra_backend.app.agents.analyst import AnalystAgent
        from netra_backend.app.agents.validator import ValidatorAgent
        
        # Domain experts
        from netra_backend.app.agents.domain_experts.base_expert import BaseDomainExpert
        from netra_backend.app.agents.domain_experts.finance_expert import FinanceExpert
        from netra_backend.app.agents.domain_experts.engineering_expert import EngineeringExpert
        from netra_backend.app.agents.domain_experts.business_expert import BusinessExpert
        
        # Tools
        from netra_backend.app.tools.deep_research_api import DeepResearchAPI
        from netra_backend.app.tools.reliability_scorer import ReliabilityScorer
        from netra_backend.app.tools.sandboxed_interpreter import SandboxedInterpreter
        
        # Guardrails
        from netra_backend.app.guardrails.input_filters import InputFilters
        from netra_backend.app.guardrails.output_validators import OutputValidators
        
        # Cache
        from netra_backend.app.services.cache.semantic_cache import SemanticCache
        
        return True
    
    assert import_all_modules() == True


if __name__ == "__main__":
    # Run tests directly
    test = TestNACISImports()
    
    print("Testing chat orchestrator imports...")
    test.test_chat_orchestrator_imports()
    print("✓ Chat orchestrator imports successful")
    
    print("Testing agent imports...")
    test.test_agent_imports()
    print("✓ Agent imports successful")
    
    print("Testing domain expert imports...")
    test.test_domain_expert_imports()
    print("✓ Domain expert imports successful")
    
    print("Testing tools imports...")
    test.test_tools_imports()
    print("✓ Tools imports successful")
    
    print("Testing guardrails imports...")
    test.test_guardrails_imports()
    print("✓ Guardrails imports successful")
    
    print("Testing semantic cache import...")
    test.test_semantic_cache_import()
    print("✓ Semantic cache import successful")
    
    print("Testing cross-module imports...")
    test.test_cross_module_imports()
    print("✓ Cross-module imports successful")
    
    print("Testing enum imports...")
    test.test_enum_imports()
    print("✓ Enum imports successful")
    
    print("Testing instantiation...")
    test.test_instantiation_without_dependencies()
    print("✓ Instantiation successful")
    
    print("Testing function-scoped imports...")
    test_all_imports_in_function()
    print("✓ Function-scoped imports successful")
    
    print("\n✅ All import tests passed!")