# netra_apex/utils/vectorizers.py

import numpy as np
from typing import List

class SemanticVectorizer:
    """
    A mock implementation of a semantic vectorizer. In a real system, this would
    wrap a library like sentence-transformers.
    """
    def __init__(self, model_name: str):
        # The model name is stored but not used in this mock implementation.
        self._model_name = model_name
        self._dimension = 384  # Matching 'all-MiniLM-L6-v2'
        print(f"Mock SemanticVectorizer initialized for model: '{self._model_name}'.")

    def embed_text(self, text: str) -> List[float]:
        """
        Creates a deterministic, pseudo-random vector based on the text's hash.
        This provides a consistent embedding for demonstration purposes.
        """
        # Create a stable seed from the text hash
        seed = int.from_bytes(text.encode(), 'little') % (2**32 - 1)
        np.random.seed(seed)
        vector = np.random.rand(self._dimension)
        # Normalize to a unit vector, a common practice for embeddings
        vector /= np.linalg.norm(vector)
        return vector.tolist()
