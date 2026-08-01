from typing import Dict, Any, List, Optional
import json
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.datasets.dataset_manager import DatasetManager
from backend.datasets.dataset_validator import DatasetValidator
from backend.fewshot.schemas import FewShotExample, FewShotSet, RetrievedExample
from backend.fewshot.retriever import CandidateRetriever, SemanticRetriever
from backend.fewshot.selector import FewShotSelector
from backend.fewshot.diversity import DiversityFilter
from backend.fewshot.ordering import OrderingEngine
from backend.fewshot.validators import FewShotValidator
from backend.fewshot.embeddings import EmbeddingManager
from backend.fewshot.index_manager import IndexManager
from backend.fewshot.service import FewShotService
import logging

logger = logging.getLogger(__name__)

class FewShotBuilder:
    """
    Main orchestrator for few-shot example selection, diversity filtering, reordering, and schema validation.
    """

    def __init__(self, cache_dir: str = "datasets/cache"):
        self.dataset_manager = DatasetManager()
        self.service = FewShotService(cache_dir=cache_dir)

    def build_examples(
        self,
        db: Session,
        dataset_id: str,
        dataset_version: str,
        query_index: int,
        strategy_config: Dict[str, Any],
        seed: int = 42
    ) -> FewShotSet:
        """
        Coordinates candidate retrieval, selection, diversity filtering,
        ordering, and validation to produce a validated FewShotSet.
        """
        # Load Dataset details
        dataset = self.dataset_manager.get_dataset(db, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} not found.")

        df_dict = self.dataset_manager.get_dataset_version_data(db, dataset_id, dataset_version)
        
        # We query demonstrations strictly from the train split
        train_split = "train" if "train" in df_dict else list(df_dict.keys())[0]
        train_df = df_dict[train_split]
        
        # Identify mapping text/label columns
        val_report = DatasetValidator.detect_and_normalize_columns(train_df, dataset.task)
        mapping = val_report.get("column_mapping", {})
        text_col = mapping.get("text") if dataset.task == "classification" else mapping.get("context")
        label_col = mapping.get("label") if dataset.task == "classification" else mapping.get("answers")
        
        # Determine query split
        # We can find which split contains the query index, or default to the train_df if not specified.
        # For simplicity, if query_index is within bounds of a split, we extract it.
        # The user previewer specifies a target split or we search in df_dict.
        # Let's check splits:
        query_split = "train"
        for s, df in df_dict.items():
            if 0 <= query_index < len(df):
                query_split = s
                break
        
        query_df = df_dict[query_split]
        query_row = query_df.iloc[query_index]
        query_text = str(query_row[text_col])
        query_id = str(query_row.get("id", query_index)) # fallback to index string

        # Define configurations
        k_shot = int(strategy_config.get("example_count", 0))
        selection_strat = strategy_config.get("selection_strategy", "Random")
        ordering_strat = strategy_config.get("ordering_strategy", "Original")
        diversity_level = strategy_config.get("diversity_level", "High Similarity")
        embedding_model = strategy_config.get("embedding_model", "all-MiniLM-L6-v2")

        if k_shot <= 0:
            return FewShotSet(
                query_sample=query_row.to_dict(),
                examples=[],
                strategy=selection_strat,
                ordering=ordering_strat,
                diversity=diversity_level
            )

        # Retrieve Candidate Pool (Excluding target query row index if query split matches train_split)
        exclude_idx = query_index if query_split == train_split else None
        candidates_df = CandidateRetriever.retrieve_candidates(train_df, query_idx=exclude_idx)

        # Apply Selection Strategies
        selected_df = pd.DataFrame()

        if selection_strat == "Random":
            selected_df = FewShotSelector.select_random(candidates_df, k_shot, seed=seed)
            # Add dummy similarity columns
            selected_df["similarity"] = 0.0
            
        elif selection_strat == "Sequential":
            # Exclude query index
            selected_df = FewShotSelector.select_sequential(candidates_df, query_index if query_split == train_split else len(train_df), k_shot)
            selected_df["similarity"] = 0.0
            
        elif selection_strat == "Balanced":
            selected_df = FewShotSelector.select_balanced(candidates_df, label_col, k_shot, seed=seed)
            selected_df["similarity"] = 0.0
            
        elif selection_strat == "Semantic":
            # Check embedding index status
            db_idx = self.service.get_index(db, dataset_id, dataset_version, embedding_model)
            if not db_idx:
                # Build index lazily if cache files missing, or raise error
                db_idx = self.service.build_dataset_index(db, dataset_id, dataset_version, embedding_model)

            # Load FAISS index and cached embeddings
            faiss_index = IndexManager.load_index(db_idx.index_path)
            embeddings = np.load(db_idx.embedding_path)

            # Instatiate semantic retriever
            em = EmbeddingManager(model_name=embedding_model)
            retriever = SemanticRetriever(embedding_manager=em)
            
            # Retrieve candidates (retrieve more than k to allow diversity filter space, e.g. top 100)
            max_retrieve = max(100, k_shot * 5)
            retrieved_examples = retriever.search(faiss_index, query_text, k=max_retrieve)
            
            # Build DataFrame matching indices of train_df
            retrieved_records = []
            for r in retrieved_examples:
                idx = int(r.sample_id)
                # Map back to train split columns
                row_dict = train_df.iloc[idx].to_dict()
                row_dict["similarity"] = r.similarity
                row_dict["__df_index"] = idx
                retrieved_records.append(row_dict)

            semantic_candidates_df = pd.DataFrame(retrieved_records)

            # Filter target query out if present
            if query_split == train_split and not semantic_candidates_df.empty:
                semantic_candidates_df = semantic_candidates_df[semantic_candidates_df["__df_index"] != query_index]

            # Apply Diversity Filters
            if diversity_level == "Medium Diversity":
                selected_df = DiversityFilter.filter_medium_diversity(
                    semantic_candidates_df, embeddings, k_shot
                )
            elif diversity_level == "High Diversity":
                selected_df = DiversityFilter.filter_high_diversity(
                    semantic_candidates_df, embeddings, k_shot, seed=seed
                )
            else:
                # High Similarity (Top K)
                selected_df = semantic_candidates_df.head(k_shot).copy()

        # Apply Ordering Strategy
        ordered_df = OrderingEngine.apply_ordering(
            df=selected_df,
            strategy=ordering_strat,
            label_col=label_col if dataset.task == "classification" else None,
            seed=seed
        )

        # Convert to schemas
        examples_list = []
        for idx, row in ordered_df.iterrows():
            ex_id = str(row.get("id", row.get("__df_index", idx)))
            # Extract answers correctly if QA SQuAD style dict
            label_val = row[label_col]
            if isinstance(label_val, dict):
                # QA answers dict
                text_list = label_val.get("text", [])
                label_val = text_list[0] if (isinstance(text_list, list) and text_list) else str(label_val)
            elif isinstance(label_val, (list, tuple)):
                label_val = label_val[0] if label_val else ""

            examples_list.append(
                FewShotExample(
                    id=ex_id,
                    input=str(row[text_col]),
                    label=str(label_val),
                    metadata={"similarity": float(row.get("similarity", 0.0))}
                )
            )

        # Run Verification Checks
        val_errors = FewShotValidator.validate_few_shot_set(
            examples=examples_list,
            query_id=query_id,
            query_text=query_text,
            text_col=text_col,
            expected_count=k_shot
        )

        if val_errors:
            logger.error(f"Few-shot validation errors: {val_errors}")
            raise RuntimeError(f"Few-shot validation checks failed: {val_errors}")

        return FewShotSet(
            query_sample=query_row.to_dict(),
            examples=examples_list,
            strategy=selection_strat,
            ordering=ordering_strat,
            diversity=diversity_level
        )
