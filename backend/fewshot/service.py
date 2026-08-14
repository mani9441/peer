from typing import Optional
import os
import datetime
from sqlalchemy.orm import Session
from backend.datasets.dataset_manager import DatasetManager
from backend.datasets.dataset_validator import DatasetValidator
from backend.fewshot.models import EmbeddingIndex
from backend.fewshot.cache import FewShotCache
from backend.fewshot.embeddings import EmbeddingManager
from backend.fewshot.index_manager import IndexManager
import logging

logger = logging.getLogger(__name__)

class FewShotService:
    """
    Service layer orchestrating the lazy indexing, database listing, and building of vector indices.
    """

    def __init__(self, cache_dir: str = "datasets/cache"):
        self.cache = FewShotCache(cache_dir=cache_dir)
        self.dataset_manager = DatasetManager()

    def build_dataset_index(
        self, 
        db: Session, 
        dataset_id: str, 
        version_name: str, 
        embedding_model: str = "all-MiniLM-L6-v2"
    ) -> EmbeddingIndex:
        """
        Loads the train split of a dataset version, generates vector embeddings,
        saves the files on disk, and registers the FAISS index in the database.
        """
        # Retrieve dataset info
        dataset = self.dataset_manager.get_dataset(db, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} not found.")

        # Load splits
        df_dict = self.dataset_manager.get_dataset_version_data(db, dataset_id, version_name)
        
        # Enforce retrieving candidates ONLY from train split
        target_split = "train" if "train" in df_dict else list(df_dict.keys())[0]
        train_df = df_dict[target_split].reset_index(drop=True)

        # Get text column mapping
        val_report = DatasetValidator.detect_and_normalize_columns(train_df, dataset.task)
        mapping = val_report.get("column_mapping", {})
        text_col = mapping.get("text") if dataset.task == "classification" else mapping.get("context")

        if not text_col or text_col not in train_df.columns:
            raise ValueError(f"Could not map text column for task {dataset.task}")

        texts = train_df[text_col].fillna("").astype(str).tolist()

        # Build caches
        npy_path = self.cache.get_embedding_path(dataset_id, version_name, embedding_model)
        faiss_path = self.cache.get_faiss_path(dataset_id, version_name, embedding_model)

        # Generate Embeddings
        em = EmbeddingManager(model_name=embedding_model)
        logger.info(f"Generating embeddings for {len(texts)} texts in split {target_split}...")
        embeddings = em.encode(texts)
        
        # Save to disk
        em.save_embeddings(npy_path, embeddings)

        # Build and Save FAISS index
        IndexManager.build_index(embeddings, faiss_path)

        # Database index mapping identifier
        clean_model = "".join(c for c in embedding_model if c.isalnum()).lower()
        index_id = f"idx_{dataset_id}_{version_name}_{clean_model}"

        # Delete existing DB record if exists
        existing = db.query(EmbeddingIndex).filter(EmbeddingIndex.id == index_id).first()
        if existing:
            db.delete(existing)
            db.flush()

        db_idx = EmbeddingIndex(
            id=index_id,
            dataset_id=dataset_id,
            embedding_model=embedding_model,
            index_path=faiss_path,
            embedding_path=npy_path,
            created_at=datetime.datetime.utcnow()
        )
        db.add(db_idx)
        db.commit()

        logger.info(f"Registered embedding index {index_id} in the database.")
        return db_idx

    def get_index(self, db: Session, dataset_id: str, version_name: str, embedding_model: str) -> Optional[EmbeddingIndex]:
        clean_model = "".join(c for c in embedding_model if c.isalnum()).lower()
        index_id = f"idx_{dataset_id}_{version_name}_{clean_model}"
        return db.query(EmbeddingIndex).filter(EmbeddingIndex.id == index_id).first()
