# netra_apex/utils/predictors.py

from netra_backend.app..models.schemas import WorkloadProfile, SupplyRecord

class TokenizationInefficiencyPredictor:
    """
    A mock predictive model that estimates the token overhead when a workload's
    language is mismatched with a model's tokenizer.
    Reference: Section 3, Component 3.
    """
    def predict_ratio(self, workload: WorkloadProfile, supply: SupplyRecord) -> float:
        """
        Predicts the token inefficiency ratio.

        Returns:
            A multiplier (e.g., 1.0 for a perfect match, 1.8 for 80% overhead).
        """
        workload_lang = workload.linguistic_features.language
        tokenizer_name = supply.tokenizer_profile.name
        tokenizer_library = supply.tokenizer_profile.library.lower()
        
        return self._calculate_ratio(workload_lang, tokenizer_name, tokenizer_library)
    
    def _calculate_ratio(self, workload_lang: str, tokenizer_name: str, tokenizer_library: str) -> float:
        """Calculate tokenization inefficiency ratio based on language and tokenizer."""
        # Handle cl100k_base tokenizer scenarios
        if 'cl100k_base' in tokenizer_name:
            return self._handle_cl100k_scenarios(workload_lang)
        
        # Handle SentencePiece tokenizer
        if 'sentencepiece' in tokenizer_library:
            return 1.2  # Generally more robust
        
        return 1.1  # Default small inefficiency
    
    def _handle_cl100k_scenarios(self, workload_lang: str) -> float:
        """Handle cl100k_base tokenizer efficiency scenarios."""
        if workload_lang == 'python':
            return 1.05  # Good but not perfect for code
        elif workload_lang == 'en':
            return 1.0   # Perfect match
        elif workload_lang == 'ja':
            return 1.8   # High inefficiency for Japanese
        return 1.1       # Default for other languages
