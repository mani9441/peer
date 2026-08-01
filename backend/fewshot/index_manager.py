import os
import numpy as np
import logging

logger = logging.getLogger(__name__)

class IndexManager:
    """
    Builds, saves, and loads FAISS Vector Indexes using Flat Inner Product (IndexFlatIP).
    """

    @staticmethod
    def build_index(embeddings: np.ndarray, filepath: str):
        """
        Builds a FAISS Flat Inner Product index from embeddings.
        Normalizes embeddings beforehand to ensure Inner Product operates as Cosine Similarity.
        """
        # We import faiss inside methods to prevent failures if faiss is still installing
        import faiss
        
        if embeddings.ndim != 2:
            raise ValueError(f"Embeddings array must be 2D. Received shape: {embeddings.shape}")
            
        dimension = embeddings.shape[1]
        
        # L2 Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized_embeddings = embeddings / (norms + 1e-10)
        
        # Create IndexFlatIP
        index = faiss.IndexFlatIP(dimension)
        index.add(normalized_embeddings.astype('float32'))
        
        # Write to file
        faiss.write_index(index, filepath)
        logger.info(f"Successfully generated and wrote FAISS index to {filepath}")
        return index

    @staticmethod
    def load_index(filepath: str):
        """Loads FAISS index from local path."""
        import faiss
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"FAISS index file not found at: {filepath}")
        return faiss.read_index(filepath)
