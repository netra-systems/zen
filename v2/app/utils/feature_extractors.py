# netra_apex/utils/feature_extractors.py

import re
from typing import List

class LanguageDetector:
    """Mock implementation of a language detector."""
    def detect(self, text: str) -> str:
        if 'import ' in text or 'def ' in text or 'class ' in text:
            return 'python'
        # Simple heuristic for demonstration
        if any(char in '你好' for char in text):
            return 'zh'
        return 'en'

class JargonExtractor:
    """Mock implementation to find domain-specific jargon."""
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
    """Mock implementation to detect code in prompts."""
    def contains_code(self, text: str) -> bool:
        # Simple regex for common code patterns
        patterns = [
            r'import\s+\w+',
            r'def\s+\w+\(.*\):',
            r'class\s+\w+:',
            r'\{.*\}', # JSON-like structures
            r';\s*$',  # C-style line endings
        ]
        return any(re.search(p, text) for p in patterns)
