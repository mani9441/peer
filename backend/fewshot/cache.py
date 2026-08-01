import os
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class FewShotCache:
    """
    Manages filesystem cache paths and checks for vector indices and embeddings.
    """

    def __init__(self, cache_dir: str = "datasets/cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_embedding_path(self, dataset_id: str, version_name: str, model_name: str) -> str:
        """Returns the numpy file path for cached embeddings."""
        clean_model = "".join(c for c in model_name if c.isalnum()).lower()
        filename = f"{dataset_id}_{version_name}_{clean_model}_embeddings.npy"
        return os.path.join(self.cache_dir, filename)

    def get_faiss_path(self, dataset_id: str, version_name: str, model_name: str) -> str:
        """Returns the FAISS index file path."""
        clean_model = "".join(c for c in model_name if c.isalnum()).lower()
        filename = f"{dataset_id}_{version_name}_{clean_model}_faiss.index"
        return os.path.join(self.cache_dir, filename)

    def get_metadata_path(self, dataset_id: str, version_name: str, model_name: str) -> str:
        """Returns the metadata JSON file path."""
        clean_model = "".join(c for c in model_name if c.isalnum()).lower()
        filename = f"{dataset_id}_{version_name}_{clean_model}_metadata.json"
        return os.path.join(self.cache_dir, filename)

    def cache_exists(self, dataset_id: str, version_name: str, model_name: str) -> bool:
        """Checks if both embeddings and FAISS index are cached on disk."""
        npy_path = self.get_embedding_path(dataset_id, version_name, model_name)
        faiss_path = self.get_faiss_path(dataset_id, version_name, model_name)
        return os.path.exists(npy_path) and os.path.exists(faiss_path)
