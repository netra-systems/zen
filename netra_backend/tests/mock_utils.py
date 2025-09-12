"""
Mock utility classes for testing purposes.

These classes provide mock implementations for testing without dependencies on external services.
"""

import re
from typing import List

import numpy as np

class MockLanguageDetector:
    """Mock implementation of a language detector for testing."""
    
    def detect(self, text: str) -> str:
        """Detect language based on simple heuristics for testing."""
        if 'import ' in text or 'def ' in text or 'class ' in text:
            return 'python'
        # Simple heuristic for demonstration
        if any(char in '[U+4F60][U+597D]' for char in text):
            return 'zh'
        return 'en'

class MockJargonExtractor:
    """Mock implementation to find domain-specific jargon for testing."""
    
    def __init__(self):
        self._jargon_map = {
            'medical': ['metformin', 'diabetes', 'treatment'],
            'financial': ['ipo', 'quarterly earnings', 'sec'],
            'pandas': ['dataframe', 'pd.read_csv'],
            'numpy': ['np.array', 'ndarray']
        }
    
    def find_jargon(self, text: str) -> List[str]:
        """Find jargon terms for testing purposes."""
        found = []
        lower_text = text.lower()
        for domain, terms in self._jargon_map.items():
            if any(term in lower_text for term in terms):
                found.append(domain)
        return found

class MockCodeDetector:
    """Mock implementation to detect code in prompts for testing."""
    
    def contains_code(self, text: str) -> bool:
        """Detect code patterns for testing purposes."""
        # Simple regex for common code patterns
        patterns = [
            r'import\s+\w+',
            r'def\s+\w+\(.*\):',
            r'class\s+\w+:',
            r'\{.*\}',  # JSON-like structures
            r';\s*$',   # C-style line endings
        ]
        return any(re.search(p, text) for p in patterns)

class MockSemanticVectorizer:
    """
    Mock implementation of a semantic vectorizer for testing.
    In a real system, this would wrap a library like sentence-transformers.
    """
    
    def __init__(self, model_name: str):
        self._model_name = model_name
        self._dimension = 384  # Matching 'all-MiniLM-L6-v2'
    
    def embed_text(self, text: str) -> List[float]:
        """
        Creates a deterministic, pseudo-random vector based on the text's hash.
        This provides a consistent embedding for testing purposes.
        """
        # Create a stable seed from the text hash
        seed = int.from_bytes(text.encode(), 'little') % (2**32 - 1)
        np.random.seed(seed)
        vector = np.random.rand(self._dimension)
        # Normalize to a unit vector, a common practice for embeddings
        vector /= np.linalg.norm(vector)
        return vector.tolist()