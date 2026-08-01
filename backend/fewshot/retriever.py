import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from backend.fewshot.schemas import RetrievedExample
from backend.fewshot.embeddings import EmbeddingManager
from backend.fewshot.index_manager import IndexManager
import logging

logger = logging.getLogger(__name__)

class CandidateRetriever:
    """
    Excludes the active evaluation query sample from candidate pools to prevent target data leakage.
    """

    @staticmethod
    def retrieve_candidates(df: pd.DataFrame, query_idx: Optional[int] = None) -> pd.DataFrame:
        """
        Returns all records from the DataFrame, excluding the query record at query_idx if specified.
        Adds a '__df_index' helper column to track original row positions.
        """
        temp_df = df.copy()
        # Keep track of original DataFrame row index
        temp_df["__df_index"] = temp_df.index
        
        if query_idx is not None and 0 <= query_idx < len(df):
            # Exclude query row index
            temp_df = temp_df.drop(index=query_idx)
            
        return temp_df.reset_index(drop=True)

class SemanticRetriever:
    """
    Encodes query texts and searches FAISS vector index to retrieve similar dataset matches.
    """

    def __init__(self, embedding_manager: EmbeddingManager):
        self.em = embedding_manager

    def search(self, faiss_index, query_text: str, k: int = 100) -> List[RetrievedExample]:
        """
        Performs inner product search in FAISS using normalized query vector.
        Returns top-K vector search results.
        """
        # Encode query
        query_vector = self.em.encode([query_text])
        
        # Normalize
        norm = np.linalg.norm(query_vector, axis=1, keepdims=True)
        normalized_q_vector = query_vector / (norm + 1e-10)
        
        # Search index
        similarities, indices = faiss_index.search(normalized_q_vector.astype("float32"), k)
        
        results = []
        for sim, idx in zip(similarities[0], indices[0]):
            # FAISS returns index -1 if not enough items in vector index
            if int(idx) == -1:
                continue
            results.append(
                RetrievedExample(
                    sample_id=str(int(idx)),
                    similarity=float(sim),
                    label=""
                )
            )
            
        return results
