import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from backend.database.db import Base

class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(String, primary_key=True)  # unique string id, e.g. UUID
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    dataset_id = Column(String, nullable=False)
    template_id = Column(String, nullable=True)  # nullable if using default template
    strategy_id = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    runs = relationship("ExperimentRun", back_populates="experiment", cascade="all, delete-orphan")


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id = Column(String, primary_key=True)  # unique run UUID
    experiment_id = Column(String, ForeignKey("experiments.id"), nullable=False)
    run_number = Column(Integer, nullable=False)
    status = Column(String, nullable=False)  # "Created", "Queued", "Running", "Completed", "Failed", "Cancelled"
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    # Relationships
    experiment = relationship("Experiment", back_populates="runs")
    responses = relationship("Response", back_populates="run", cascade="all, delete-orphan")
    metrics = relationship("Metric", uselist=False, back_populates="run", cascade="all, delete-orphan")
    metadata_rel = relationship("Metadata", uselist=False, back_populates="run", cascade="all, delete-orphan")


class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("experiment_runs.id"), nullable=False)
    sample_index = Column(Integer, nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    latency = Column(Float, nullable=False)  # in ms
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    cost = Column(Float, nullable=False)
    finish_reason = Column(String, nullable=True)
    ground_truth = Column(String, nullable=True)
    prediction = Column(String, nullable=True)
    is_correct = Column(Boolean, nullable=True)

    # Relationships
    run = relationship("ExperimentRun", back_populates="responses")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("experiment_runs.id"), nullable=False)
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1 = Column(Float, nullable=True)
    latency = Column(Float, nullable=True)  # mean latency in ms
    cost = Column(Float, nullable=True)     # total cost in USD
    consistency = Column(Float, nullable=True)

    # Relationships
    run = relationship("ExperimentRun", back_populates="metrics")


class Metadata(Base):
    __tablename__ = "metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("experiment_runs.id"), nullable=False)
    temperature = Column(Float, nullable=True)
    top_p = Column(Float, nullable=True)
    seed = Column(Integer, nullable=True)
    prompt_length = Column(String, nullable=True)
    fewshot_count = Column(Integer, nullable=True)
    selection_strategy = Column(String, nullable=True)
    ordering_strategy = Column(String, nullable=True)

    # Relationships
    run = relationship("ExperimentRun", back_populates="metadata_rel")
