import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database.db import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String, primary_key=True)  # dataset identifier, e.g., "sst2" or "csv_12345"
    name = Column(String, nullable=False)
    version = Column(String, nullable=False, default="v1")
    task = Column(String, nullable=False)  # "classification", "qa"
    source = Column(String, nullable=False)  # "HuggingFace", "CSV", "JSON"
    language = Column(String, default="English")
    samples = Column(Integer, default=0)
    splits = Column(String, default="train")  # Comma-separated list of splits, e.g. "train,validation,test"
    license = Column(String, default="Unknown")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    hash = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")
    statistics = relationship("DatasetStatistics", uselist=False, back_populates="dataset", cascade="all, delete-orphan")
    labels = relationship("DatasetLabel", back_populates="dataset", cascade="all, delete-orphan")

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False)
    version = Column(String, nullable=False)
    parent_version = Column(String, nullable=True)
    transformations = Column(Text, nullable=True)  # JSON string of applied samplers/splitters/filters
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    hash = Column(String, nullable=False)
    path = Column(String, nullable=False)  # Path to local storage file (e.g. Parquet file)

    dataset = relationship("Dataset", back_populates="versions")

class DatasetStatistics(Base):
    __tablename__ = "dataset_statistics"

    dataset_id = Column(String, ForeignKey("datasets.id"), primary_key=True)
    total_samples = Column(Integer, default=0)
    class_distribution = Column(Text, nullable=True)  # JSON string of class counts
    avg_length = Column(Float, default=0.0)
    min_length = Column(Integer, default=0)
    max_length = Column(Integer, default=0)
    imbalance_score = Column(Float, default=0.0)  # Shannon Entropy or simple ratio
    metadata_json = Column(Text, nullable=True)  # JSON string for other properties (QA context lengths etc.)

    dataset = relationship("Dataset", back_populates="statistics")

class DatasetLabel(Base):
    __tablename__ = "dataset_labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False)
    label_id = Column(Integer, nullable=False)
    label_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    dataset = relationship("Dataset", back_populates="labels")
