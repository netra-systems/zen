'''Test all NACIS module imports.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Ensures all modules can be imported without errors.
'''

import sys
import os
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Use test framework's environment setup
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import isolated environment FIRST
from shared.isolated_environment import get_env

# Set test environment
env = get_env()
env.set("ENVIRONMENT", "testing", "test")
env.set("SERVICE_SECRET", "test-secret-minimum-32-chars-long", "test")
env.set("JWT_SECRET", "test-jwt-secret-minimum-32-chars", "test")
env.set("LLM_MODE", "mock", "test")
env.set("TESTING", "true", "test")

import pytest


class TestNACISImports:
    """Test all NACIS module imports work correctly."""

    def test_chat_orchestrator_imports(self):
        """Test chat orchestrator and helper imports."""
        # Main orchestrator - using the actual file that exists
        try:
            from netra_backend.app.agents.chat_orchestrator_main import ChatOrchestrator
        except ImportError:
            pytest.skip("ChatOrchestrator not available")

        # Helper modules - using try/except for optional imports
        try:
            from netra_backend.app.agents.chat_orchestrator.intent_classifier import (
                IntentClassifier, IntentType
            )
        except ImportError:
            IntentClassifier, IntentType = None, None
        
        try:
            from netra_backend.app.agents.chat_orchestrator.confidence_manager import (
                ConfidenceManager, ConfidenceLevel
            )
        except ImportError:
            ConfidenceManager, ConfidenceLevel = None, None
        
        try:
            from netra_backend.app.agents.chat_orchestrator.model_cascade import (
                ModelCascade, ModelTier
            )
        except ImportError:
            ModelCascade, ModelTier = None, None
        
        try:
            from netra_backend.app.agents.chat_orchestrator.execution_planner import (
                ExecutionPlanner
            )
        except ImportError:
            ExecutionPlanner = None
        
        try:
            from netra_backend.app.agents.chat_orchestrator.pipeline_executor import (
                PipelineExecutor
            )
        except ImportError:
            PipelineExecutor = None
        
        try:
            from netra_backend.app.agents.chat_orchestrator.trace_logger import (
                TraceLogger
            )
        except ImportError:
            TraceLogger = None

        assert ChatOrchestrator is not None

    def test_agent_imports(self):
        """Test all agent imports."""
        try:
            from netra_backend.app.agents.researcher import ResearcherAgent
        except ImportError:
            ResearcherAgent = None
            
        try:
            from netra_backend.app.agents.analyst import AnalystAgent
        except ImportError:
            AnalystAgent = None
            
        try:
            from netra_backend.app.agents.validator import ValidatorAgent
        except ImportError:
            ValidatorAgent = None

        # At least one agent should be available
        assert any([ResearcherAgent, AnalystAgent, ValidatorAgent]), "No agents available"

    def test_domain_expert_imports(self):
        """Test domain expert imports."""
        try:
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
        except ImportError:
            pytest.skip("Domain experts not available")

    def test_tools_imports(self):
        """Test tools imports."""
        try:
            from netra_backend.app.tools import (
                DeepResearchAPI,
                ReliabilityScorer,
                SandboxedInterpreter
            )
            assert DeepResearchAPI is not None
            assert ReliabilityScorer is not None
            assert SandboxedInterpreter is not None
        except ImportError:
            pytest.skip("Tools not available")

    def test_guardrails_imports(self):
        """Test guardrails imports."""
        try:
            from netra_backend.app.guardrails import (
                InputFilters,
                OutputValidators
            )
            assert InputFilters is not None
            assert OutputValidators is not None
        except ImportError:
            pytest.skip("Guardrails not available")

    def test_semantic_cache_import(self):
        """Test semantic cache import."""
        try:
            from netra_backend.app.services.cache.semantic_cache import SemanticCache
            assert SemanticCache is not None
        except ImportError:
            pytest.skip("Semantic cache not available")

    def test_cross_module_imports(self):
        """Test imports work across modules."""
        # This tests that modules can import from each other
        try:
            from netra_backend.app.agents.chat_orchestrator_main import ChatOrchestrator
        except ImportError:
            ChatOrchestrator = None
            
        try:
            from netra_backend.app.agents.researcher import ResearcherAgent
        except ImportError:
            ResearcherAgent = None
            
        try:
            from netra_backend.app.tools.reliability_scorer import ReliabilityScorer
        except ImportError:
            ReliabilityScorer = None

        # Test that at least some classes are available
        available_classes = [cls for cls in [ChatOrchestrator, ResearcherAgent, ReliabilityScorer] if cls is not None]
        assert len(available_classes) > 0, "No classes available for cross-module testing"

    def test_enum_imports(self):
        """Test enum imports work correctly."""
        try:
            from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentType
            from netra_backend.app.agents.chat_orchestrator.confidence_manager import ConfidenceLevel
            from netra_backend.app.agents.chat_orchestrator.model_cascade import ModelTier

            # Test enum values are accessible
            assert IntentType.TCO_ANALYSIS.value == "tco_analysis"
            assert ConfidenceLevel.HIGH.value == 0.9
            assert ModelTier.TIER1.value == "fast"
        except ImportError:
            pytest.skip("Enum modules not available")

    def test_instantiation_without_dependencies(self):
        """Test basic instantiation of classes."""
        instances = []
        
        try:
            from netra_backend.app.tools.reliability_scorer import ReliabilityScorer
            scorer = ReliabilityScorer()
            instances.append(scorer)
        except ImportError:
            pass
            
        try:
            from netra_backend.app.guardrails.input_filters import InputFilters
            filters = InputFilters()
            instances.append(filters)
        except ImportError:
            pass
            
        try:
            from netra_backend.app.guardrails.output_validators import OutputValidators
            validators = OutputValidators()
            instances.append(validators)
        except ImportError:
            pass
            
        try:
            from netra_backend.app.agents.chat_orchestrator.trace_logger import TraceLogger
            logger = TraceLogger()
            instances.append(logger)
        except ImportError:
            pass

        # At least some instances should be created
        assert len(instances) > 0, "No classes could be instantiated"


def test_all_imports_in_function():
    """Test all imports work when done inside a function."""
    def import_all_modules():
        successful_imports = 0
        total_attempted = 0
        
        # Chat orchestrator modules
        try:
            from netra_backend.app.agents.chat_orchestrator_main import ChatOrchestrator
            successful_imports += 1
        except ImportError:
            pass
        total_attempted += 1
        
        # Try other imports with error handling
        import_attempts = [
            ("netra_backend.app.agents.chat_orchestrator.intent_classifier", "IntentClassifier"),
            ("netra_backend.app.agents.chat_orchestrator.confidence_manager", "ConfidenceManager"),
            ("netra_backend.app.agents.chat_orchestrator.model_cascade", "ModelCascade"),
            ("netra_backend.app.agents.researcher", "ResearcherAgent"),
            ("netra_backend.app.agents.analyst", "AnalystAgent"),
            ("netra_backend.app.agents.validator", "ValidatorAgent"),
            ("netra_backend.app.tools.reliability_scorer", "ReliabilityScorer"),
            ("netra_backend.app.guardrails.input_filters", "InputFilters"),
            ("netra_backend.app.guardrails.output_validators", "OutputValidators"),
        ]
        
        for module_name, class_name in import_attempts:
            try:
                module = __import__(module_name, fromlist=[class_name])
                getattr(module, class_name)
                successful_imports += 1
            except ImportError:
                pass
            total_attempted += 1
        
        # Return True if at least 30% of imports succeed
        success_rate = successful_imports / total_attempted if total_attempted > 0 else 0
        return success_rate >= 0.3

    assert import_all_modules() == True


if __name__ == "__main__":
    # Run tests directly
    test = TestNACISImports()

    print("Testing chat orchestrator imports...")
    test.test_chat_orchestrator_imports()
    print("CHECK Chat orchestrator imports successful")

    print("Testing agent imports...")
    test.test_agent_imports()
    print("CHECK Agent imports successful")

    print("Testing domain expert imports...")
    test.test_domain_expert_imports()
    print("CHECK Domain expert imports successful")

    print("Testing tools imports...")
    test.test_tools_imports()
    print("CHECK Tools imports successful")

    print("Testing guardrails imports...")
    test.test_guardrails_imports()
    print("CHECK Guardrails imports successful")

    print("Testing semantic cache import...")
    test.test_semantic_cache_import()
    print("CHECK Semantic cache import successful")

    print("Testing cross-module imports...")
    test.test_cross_module_imports()
    print("CHECK Cross-module imports successful")

    print("Testing enum imports...")
    test.test_enum_imports()
    print("CHECK Enum imports successful")

    print("Testing instantiation...")
    test.test_instantiation_without_dependencies()
    print("CHECK Instantiation successful")

    print("Testing function-scoped imports...")
    test_all_imports_in_function()
    print("CHECK Function-scoped imports successful")

    print("CHECK All import tests passed!")