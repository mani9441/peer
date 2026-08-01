import numpy as np
import pandas as pd
from typing import List, Dict, Any
from sklearn.cluster import MiniBatchKMeans
import logging

logger = logging.getLogger(__name__)

class DiversityFilter:
    """
    Applies vector filtering thresholds or KMeans clustering to candidate pools for diversity.
    """

    @staticmethod
    def filter_medium_diversity(
        candidates_df: pd.DataFrame, 
        embeddings: np.ndarray, 
        k: int, 
        threshold: float = 0.92
    ) -> pd.DataFrame:
        """
        Filters candidates sequentially. If a candidate is too similar (>0.92 cosine similarity)
        to any already selected candidate, it is skipped.
        Assumes candidates_df is already ordered by relevance/similarity.
        """
        if len(candidates_df) <= 1 or k <= 1:
            return candidates_df.head(k)
            
        selected_indices = []
        selected_vectors = []
        
        # Keep track of indices that match rows in candidates_df
        for idx, row in candidates_df.iterrows():
            # Get original df index or array row position
            original_idx = int(row["__df_index"])
            vector = embeddings[original_idx]
            
            # L2 Normalize vector
            v_norm = np.linalg.norm(vector)
            norm_vector = vector / (v_norm + 1e-10)
            
            if not selected_vectors:
                # Add first element
                selected_indices.append(idx)
                selected_vectors.append(norm_vector)
            else:
                # Calculate cosine similarities to all selected vectors
                # Inner product since all vectors are normalized
                sims = np.dot(selected_vectors, norm_vector)
                
                # Check threshold
                if np.max(sims) <= threshold:
                    selected_indices.append(idx)
                    selected_vectors.append(norm_vector)
                    
            if len(selected_indices) >= k:
                break
                
        return candidates_df.loc[selected_indices].reset_index(drop=True)

    @staticmethod
    def filter_high_diversity(
        candidates_df: pd.DataFrame, 
        embeddings: np.ndarray, 
        k: int, 
        seed: int = 42
    ) -> pd.DataFrame:
        """
        Clusters candidate vectors into K clusters using MiniBatchKMeans.
        From each cluster, selects the candidate with the highest similarity score.
        """
        # If not enough items to cluster, fallback to simple top K
        if len(candidates_df) <= k:
            return candidates_df
            
        # Get embeddings for candidate pool
        candidate_indices = candidates_df["__df_index"].astype(int).tolist()
        candidate_vectors = embeddings[candidate_indices]
        
        # Run MiniBatchKMeans
        # k is the target number of clusters
        kmeans = MiniBatchKMeans(n_clusters=k, random_state=seed, n_init=3)
        labels = kmeans.fit_predict(candidate_vectors)
        
        selected_indices = []
        
        # For each cluster, pick the sample with the highest FAISS similarity score
        # candidates_df contains a 'similarity' column or we can sort by rank
        for i in range(k):
            cluster_mask = (labels == i)
            cluster_indices = np.where(cluster_mask)[0]
            
            if len(cluster_indices) == 0:
                continue
                
            # Filter candidates_df rows belonging to this cluster
            cluster_df = candidates_df.iloc[cluster_indices]
            
            # If 'similarity' exists, pick highest similarity, else first item (highest rank)
            if "similarity" in cluster_df.columns:
                best_idx = cluster_df["similarity"].idxmax()
            else:
                best_idx = cluster_df.index[0]
                
            selected_indices.append(best_idx)
            
        return candidates_df.loc[selected_indices].reset_index(drop=True)
