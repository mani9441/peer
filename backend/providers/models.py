import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.database.db import Base

class Provider(Base):
    __tablename__ = "providers"

    id = Column(String, primary_key=True)  # "gemini", "openai", "openrouter", "ollama"
    provider_name = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)
    api_base = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    models = relationship("Model", back_populates="provider", cascade="all, delete-orphan")

class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=False)
    model_name = Column(String, nullable=False)
    context_window = Column(Integer, nullable=True)
    supports_seed = Column(Boolean, default=True)
    supports_temperature = Column(Boolean, default=True)
    supports_top_p = Column(Boolean, default=True)
    supports_json_mode = Column(Boolean, default=True)
    status = Column(String, default="active")  # "active", "deprecated"

    # Relationships
    provider = relationship("Provider", back_populates="models")

class ProviderRequest(Base):
    __tablename__ = "provider_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_run = Column(String, nullable=True)  # maps to experiment_id in LLMRequest
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    latency = Column(Integer, nullable=False)  # latency in ms
    tokens = Column(Integer, nullable=False)   # total tokens
    cost = Column(Float, nullable=False)       # estimated cost in USD
    status = Column(String, nullable=False)    # "success", "failed"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
