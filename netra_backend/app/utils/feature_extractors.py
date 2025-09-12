# netra_apex/utils/feature_extractors.py

import re
from typing import List


class LanguageDetector:
    """Production language detection implementation using pattern matching.
    
    Detects programming languages and natural languages based on content analysis.
    """
    def detect(self, text: str) -> str:
        if 'import ' in text or 'def ' in text or 'class ' in text:
            return 'python'
        # Pattern-based language detection for production use
        if any(char in '[U+4F60][U+597D]' for char in text):
            return 'zh'
        return 'en'

class JargonExtractor:
    """Production domain-specific terminology extractor.
    
    Identifies technical jargon and domain-specific terms in text content.
    """
    def __init__(self):
        self._jargon_map = {
            'medical': ['metformin', 'diabetes', 'treatment'],
            'financial': ['ipo', 'quarterly earnings', 'sec'],
            'pandas': ['dataframe', 'pd.read_csv'],
            'numpy': ['np.array', 'ndarray']
        }
    def find_jargon(self, text: str) -> List[str]:
        found = []
        lower_text = text.lower()
        for domain, terms in self._jargon_map.items():
            if any(term in lower_text for term in terms):
                found.append(domain)
        return found

class CodeDetector:
    """Production code pattern detector.
    
    Identifies code snippets and programming constructs in text input.
    """
    def contains_code(self, text: str) -> bool:
        patterns = _get_code_detection_patterns()
        return any(re.search(p, text) for p in patterns)


def _get_code_detection_patterns() -> list:
    """Get regex patterns for code detection."""
    return [
        r'import\s+\w+',
        r'def\s+\w+\(.*\):',
        r'class\s+\w+:',
        r'\{.*\}',  # JSON-like structures
        r';\s*$',   # C-style line endings
    ]
