import os
import numpy as np
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class EmbeddingManager:
    """
    Sentence Transformers interface for computing and caching text embeddings.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None  # Lazy loaded

    @property
    def model(self):
        """Lazy load the sentence transformer model to save memory during startup."""
        if self._model is None:
            # We import sentence_transformers here to avoid torch load overhead in lightweight tasks
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformer model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encodes list of strings to sentence embedding vectors."""
        if not texts:
            return np.empty((0, 384), dtype=np.float32)
        # Convert to list of strings
        str_texts = [str(t) for t in texts]
        embeddings = self.model.encode(str_texts, show_progress_bar=False)
        return np.array(embeddings, dtype=np.float32)

    @staticmethod
    def save_embeddings(filepath: str, embeddings: np.ndarray):
        """Saves embedding array to local numpy format."""
        np.save(filepath, embeddings)
        logger.info(f"Saved {embeddings.shape} embeddings cache to {filepath}")

    @staticmethod
    def load_embeddings(filepath: str) -> np.ndarray:
        """Loads cached embeddings numpy array."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Embeddings cache not found: {filepath}")
        return np.load(filepath)
