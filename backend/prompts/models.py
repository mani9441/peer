import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database.db import Base

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(String, primary_key=True)  # unique string id, e.g. "binary_sentiment_17855368"
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    task_type = Column(String, nullable=False)  # "classification", "qa", "summarization", "reasoning", "translation", "extraction", "custom"
    strategy = Column(String, nullable=False)  # "Instruction", "Example", "Mixed", "JSON", "Markdown", "XML", "CoT", "Custom"
    format = Column(String, nullable=False)  # "Plain Text", "Markdown", "JSON", "XML"
    instruction_style = Column(String, nullable=False)  # "Simple", "Detailed", "Step-by-Step", "None"
    reasoning_style = Column(String, nullable=False)  # "None", "Chain-of-Thought"
    language = Column(String, default="English")
    current_version = Column(String, nullable=False, default="1")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    versions = relationship("PromptVersion", back_populates="prompt", cascade="all, delete-orphan")
    tags = relationship("PromptTag", back_populates="prompt", cascade="all, delete-orphan")

class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(String, ForeignKey("prompt_templates.id"), nullable=False)
    version = Column(String, nullable=False)
    template_body = Column(Text, nullable=False)
    change_notes = Column(Text, nullable=True)
    token_estimate = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    prompt = relationship("PromptTemplate", back_populates="versions")

class PromptTag(Base):
    __tablename__ = "prompt_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(String, ForeignKey("prompt_templates.id"), nullable=False)
    tag = Column(String, nullable=False)

    prompt = relationship("PromptTemplate", back_populates="tags")
