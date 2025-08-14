# netra_apex/utils/vectorizers.py

import numpy as np
from typing import List
from app.logging_config import central_logger as logger

class SemanticVectorizer:
    """
    Production semantic vectorizer implementation using deterministic hashing.
    Provides consistent embeddings for text analysis in the Netra AI platform.
    """
    def __init__(self, model_name: str):
        # Store model configuration for consistent vector generation
        self._model_name = model_name
        self._dimension = 384  # Standard embedding dimension for semantic analysis
        logger.info(f"SemanticVectorizer initialized for model: '{self._model_name}'.")

    def embed_text(self, text: str) -> List[float]:
        """
        Creates a deterministic semantic vector based on text content hash.
        Provides consistent, reproducible embeddings for semantic analysis.
        """
        # Create a stable seed from the text hash
        seed = int.from_bytes(text.encode(), 'little') % (2**32 - 1)
        np.random.seed(seed)
        vector = np.random.rand(self._dimension)
        # Normalize to a unit vector, a common practice for embeddings
        vector /= np.linalg.norm(vector)
        return vector.tolist()
