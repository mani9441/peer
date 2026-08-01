import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database.db import Base

class EmbeddingIndex(Base):
    __tablename__ = "embedding_indexes"

    id = Column(String, primary_key=True)  # unique ID, e.g. "dataset_sst2_v1"
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False)
    embedding_model = Column(String, nullable=False)
    index_path = Column(String, nullable=False)
    embedding_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class FewShotConfiguration(Base):
    __tablename__ = "fewshot_configurations"

    id = Column(String, primary_key=True)
    experiment_id = Column(String, nullable=False)  # Link to experimental run configuration
    selection_strategy = Column(String, nullable=False)  # "Random", "Balanced", "Semantic", "Sequential"
    ordering_strategy = Column(String, nullable=False)  # "Original", "Random", "Similarity", "Reverse Similarity", "Label Alternating"
    diversity_level = Column(String, nullable=False)  # "High Similarity", "Medium Diversity", "High Diversity"
    example_count = Column(Integer, default=0)
    embedding_model = Column(String, nullable=False)

class FewShotExample(Base):
    __tablename__ = "fewshot_examples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_run = Column(String, nullable=False)  # uniquely identifies an experimental run
    query_sample = Column(String, nullable=False)  # record query ID or input
    example_sample = Column(String, nullable=False)  # selected demonstration ID or text
    rank = Column(Integer, nullable=False)
    similarity_score = Column(Float, nullable=False)
    order_position = Column(Integer, nullable=False)
