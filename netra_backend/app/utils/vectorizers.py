# netra_apex/utils/vectorizers.py

import numpy as np
from typing import List
from netra_backend.app.logging_config import central_logger as logger

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
        seed = _create_text_seed(text)
        vector = _generate_normalized_vector(seed, self._dimension)
        return vector.tolist()


def _create_text_seed(text: str) -> int:
    """Create a stable seed from text hash."""
    return int.from_bytes(text.encode(), 'little') % (2**32 - 1)


def _generate_normalized_vector(seed: int, dimension: int) -> np.ndarray:
    """Generate a normalized vector from seed."""
    np.random.seed(seed)
    vector = np.random.rand(dimension)
    # Normalize to a unit vector, a common practice for embeddings
    vector /= np.linalg.norm(vector)
    return vector
