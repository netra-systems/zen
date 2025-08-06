# netra_apex/core/demand_analyzer.py
#
# Copyright (C) 2025, netra apex Inc.
#
# This module implements the Demand Analyzer, the first stage in the Sentient
# Fabric's closed-loop management framework. Its responsibility is to ingest
# raw, unstructured requests and transform them into rich, structured
# Workload Profiles. This deep understanding of demand—spanning semantic,
# operational, and risk dimensions—is a prerequisite for intelligent workload
# routing and multi-objective optimization.
# Reference: Section 2: The Demand Analyzer.

from typing import Dict, Any, List

# Assuming schemas are in a sibling directory `models`
from ..models.schemas import WorkloadProfile, LinguisticFeatures, SLOProfile, RiskProfile
# Assuming utility functions for vectorization and feature extraction exist
from ..utils.vectorizers import SemanticVectorizer
from ..utils.feature_extractors import LanguageDetector, JargonExtractor, CodeDetector

class WorkloadProfiler:
    """
    Component responsible for dissecting a raw request to understand its
    fundamental nature through semantic and linguistic analysis.
    Reference: Section 2, Component 1.
    """
    def __init__(self, vectorizer_model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initializes the profiler with the necessary models for analysis.
        In a production system, these models would be managed and versioned.
        """
        self.vectorizer = SemanticVectorizer(model_name=vectorizer_model_name)
        self.lang_detector = LanguageDetector()
        self.jargon_extractor = JargonExtractor() # Could be backed by a custom vocab
        self.code_detector = CodeDetector()
        print("WorkloadProfiler initialized.")

    def analyze_semantics(self, prompt: str) -> List[float]:
        """
        Generates a high-dimensional Task Vector representing the semantic
        intent of the workload.
        """
        return self.vectorizer.embed_text(prompt)

    def extract_linguistic_features(self, prompt: str) -> LinguisticFeatures:
        """
        Extracts discrete linguistic and structural features from the prompt text.
        """
        language = self.lang_detector.detect(prompt)
        has_code = self.code_detector.contains_code(prompt)
        domain_jargon = self.jargon_extractor.find_jargon(prompt)

        # Using a simple character count for demonstration. A real system would
        # use a reference tokenizer.
        prompt_length_chars = len(prompt)
        # Placeholder for token count, as it depends on a specific tokenizer.
        # This would be more accurately predicted or calculated in a full implementation.
        prompt_length_tokens = prompt_length_chars // 4 # Rough approximation

        return LinguisticFeatures(
            language=language,
            has_code=has_code,
            domain_jargon=domain_jargon,
            prompt_length_tokens=prompt_length_tokens,
            prompt_length_chars=prompt_length_chars
        )

class SLODefiner:
    """
    Component responsible for codifying the performance requirements (SLOs)
    for a given workload based on its originating application metadata.
    Reference: Section 2, Component 2.
    """
    def __init__(self, app_slo_configs: Dict[str, Dict]):
        """
        Initializes the definer with a configuration mapping application IDs
        to their specific SLO requirements.
        """
        self.app_slo_configs = app_slo_configs
        print("SLODefiner initialized.")

    def define_slo_profile(self, app_id: str) -> SLOProfile:
        """
        Looks up the SLOs for an application and returns a structured SLOProfile.
        """
        config = self.app_slo_configs.get(app_id, self.app_slo_configs['default'])
        return SLOProfile(**config)


class RiskAssessor:
    """
    Component responsible for translating qualitative risk concerns into
    quantitative scores and tags that the optimization engine can use.
    Reference: Section 2, Component 3.
    """
    def __init__(self, app_risk_configs: Dict[str, Dict]):
        """
        Initializes the assessor with a configuration mapping application IDs
        to their business impact and likely failure modes.
        """
        self.app_risk_configs = app_risk_configs
        print("RiskAssessor initialized.")

    def assess_risk_profile(self, app_id: str, linguistic_features: LinguisticFeatures) -> RiskProfile:
        """
        Determines the risk profile based on the application and prompt content.
        """
        config = self.app_risk_configs.get(app_id, self.app_risk_configs['default'])

        # Base failure modes from config
        failure_modes = set(config.get('failure_mode_tags', []))

        # Dynamically add failure modes based on content
        if linguistic_features.domain_jargon and 'medical' in linguistic_features.domain_jargon:
            failure_modes.add('risk_of_hallucination')
        if 'financial' in linguistic_features.domain_jargon:
             failure_modes.add('risk_of_hallucination')

        return RiskProfile(
            business_impact_score=config.get('business_impact_score', 3),
            failure_mode_tags=list(failure_modes)
        )

class DemandAnalyzer:
    """
    The main class for this module. It orchestrates the profiler, SLO definer,
    and risk assessor to create a complete WorkloadProfile from a raw request.
    """
    def __init__(self, config: Dict):
        """
        Initializes the DemandAnalyzer with its sub-components.

        Args:
            config: A dictionary containing configurations for sub-components,
                    e.g., {'vectorizer_model': '...', 'app_slos': {...}, ...}
        """
        self.profiler = WorkloadProfiler(
            vectorizer_model_name=config.get('vectorizer_model', 'all-MiniLM-L6-v2')
        )
        self.slo_definer = SLODefiner(
            app_slo_configs=config.get('app_slos', {})
        )
        self.risk_assessor = RiskAssessor(
            app_risk_configs=config.get('app_risks', {})
        )
        print("DemandAnalyzer initialized and ready.")

    def create_workload_profile(self, prompt: str, metadata: Dict[str, Any]) -> WorkloadProfile:
        """
        Processes a raw request and produces a structured WorkloadProfile.

        Args:
            prompt: The raw text prompt from the user or application.
            metadata: A dictionary containing contextual information, crucially
                      including an 'app_id' to look up SLO and risk profiles.

        Returns:
            A fully populated WorkloadProfile object.
        """
        if 'app_id' not in metadata:
            raise ValueError("'app_id' must be present in metadata.")

        app_id = metadata['app_id']

        # 1. Profile the workload's content
        task_vector = self.profiler.analyze_semantics(prompt)
        linguistic_features = self.profiler.extract_linguistic_features(prompt)

        # 2. Define performance requirements
        slo_profile = self.slo_definer.define_slo_profile(app_id)

        # 3. Assess business and operational risk
        risk_profile = self.risk_assessor.assess_risk_profile(app_id, linguistic_features)

        # 4. Assemble the final profile
        workload_profile = WorkloadProfile(
            task_vector=task_vector,
            linguistic_features=linguistic_features,
            slo_profile=slo_profile,
            risk_profile=risk_profile,
            raw_prompt=prompt,
            metadata=metadata
        )

        print(f"Created WorkloadProfile: {workload_profile.workload_id}")
        return workload_profile

# Example usage (can be placed in a main script or test file)
def get_default_config() -> Dict:
    """Provides a sample configuration for demonstration."""
    return {
        "vectorizer_model": "all-MiniLM-L6-v2",
        "app_slos": {
            "default": {"ttft_ms_p95": 2000, "tpot_ms_p95": 100},
            "chatbot-interactive": {"ttft_ms_p95": 500, "tpot_ms_p95": 50},
            "code-assistant": {"ttft_ms_p95": 800, "tpot_ms_p95": 20},
            "batch-summarizer": {"ttft_ms_p95": 10000, "tpot_ms_p95": 200},
        },
        "app_risks": {
            "default": {"business_impact_score": 3, "failure_mode_tags": []},
            "customer-facing-support": {
                "business_impact_score": 7,
                "failure_mode_tags": ["risk_of_bias", "risk_of_prompt_injection"]
            },
            "medical-qa": {
                "business_impact_score": 10,
                "failure_mode_tags": ["risk_of_hallucination", "risk_of_bias"]
            },
             "internal-dev-tool": {
                "business_impact_score": 2,
                "failure_mode_tags": ["risk_of_data_leakage"]
            }
        }
    }
