import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database.db import Base

class PromptStrategy(Base):
    __tablename__ = "prompt_strategies"

    id = Column(String, primary_key=True)  # unique ID, e.g. "mixed_markdown_1785536"
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    structure = Column(String, nullable=False)  # "Instruction", "Example-Based", "Mixed"
    format = Column(String, nullable=False)  # "Plain Text", "Markdown", "JSON", "XML"
    instruction_style = Column(String, nullable=False)  # "Simple", "Detailed", "Step-by-Step", "None"
    reasoning_style = Column(String, nullable=False)  # "None", "Chain-of-Thought"
    prompt_length = Column(String, nullable=False)  # "Short", "Medium", "Long"
    example_count = Column(Integer, default=0)
    selection_strategy = Column(String, nullable=False)  # "Random", "Balanced", "Semantic", "None"
    ordering_strategy = Column(String, nullable=False)  # "Original", "Random", "Similarity", "None"
    output_constraints = Column(Text, nullable=True)  # JSON string representation of a list of strings
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    version = Column(String, nullable=False, default="1")

    # Relationships
    versions = relationship("StrategyVersion", back_populates="strategy", cascade="all, delete-orphan")

class StrategyVersion(Base):
    __tablename__ = "strategy_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String, ForeignKey("prompt_strategies.id"), nullable=False)
    version = Column(String, nullable=False)
    configuration = Column(Text, nullable=False)  # JSON serialized full configuration dictionary
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    strategy = relationship("PromptStrategy", back_populates="versions")
