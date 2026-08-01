import datetime
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.strategies.models import PromptStrategy, StrategyVersion
from backend.strategies.strategy_validator import StrategyValidator
from backend.strategies.strategy_versioning import StrategyVersioning
import logging

logger = logging.getLogger(__name__)

class StrategyRegistry:
    """
    Handles SQLite transactions for CRUD, search, cloning, and version control of prompt strategies.
    """

    def __init__(self):
        self.validator = StrategyValidator()

    def create_strategy(
        self,
        db: Session,
        name: str,
        structure: str,
        format: str,
        instruction_style: str,
        reasoning_style: str,
        prompt_length: str,
        example_count: int,
        selection_strategy: str,
        ordering_strategy: str,
        output_constraints: List[str],
        description: Optional[str] = None
    ) -> PromptStrategy:
        """
        Creates a new prompt strategy configuration in the DB and registers version 1.
        """
        # Unique ID from name
        clean_name = "".join(c for c in name if c.isalnum() or c in ("_", "-")).lower()
        strategy_id = f"{clean_name}_{int(datetime.datetime.utcnow().timestamp())}"

        # Verify name unique
        existing = db.query(PromptStrategy).filter(PromptStrategy.name == name).first()
        if existing:
            raise ValueError(f"A strategy configuration named '{name}' already exists.")

        config_dict = {
            "name": name,
            "structure": structure,
            "format": format,
            "instruction_style": instruction_style,
            "reasoning_style": reasoning_style,
            "prompt_length": prompt_length,
            "example_count": example_count,
            "selection_strategy": selection_strategy,
            "ordering_strategy": ordering_strategy,
            "output_constraints": output_constraints,
            "description": description
        }

        # Run Validation
        val_report = self.validator.validate(config_dict)
        if val_report["status"] == "FAIL":
            raise ValueError(f"Strategy validation failed: {val_report['errors']}")

        # 1. Save Strategy record
        strategy = PromptStrategy(
            id=strategy_id,
            name=name,
            description=description,
            structure=structure,
            format=format,
            instruction_style=instruction_style,
            reasoning_style=reasoning_style,
            prompt_length=prompt_length,
            example_count=example_count,
            selection_strategy=selection_strategy,
            ordering_strategy=ordering_strategy,
            output_constraints=json.dumps(output_constraints),
            version="1"
        )
        db.add(strategy)
        db.flush()

        # 2. Save StrategyVersion record (v1)
        ser_config = StrategyVersioning.serialize_config(config_dict)
        version_rec = StrategyVersion(
            strategy_id=strategy.id,
            version="1",
            configuration=ser_config
        )
        db.add(version_rec)

        db.commit()
        logger.info(f"Registered new prompt strategy: {strategy.id}")
        return strategy

    def add_version(
        self,
        db: Session,
        strategy_id: str,
        version: str,
        config_dict: Dict[str, Any]
    ) -> StrategyVersion:
        """
        Adds a new version to an existing strategy configuration.
        """
        strategy = db.query(PromptStrategy).filter(PromptStrategy.id == strategy_id).first()
        if not strategy:
            raise ValueError(f"Prompt strategy with ID {strategy_id} not found.")

        # Verify version doesn't exist
        existing_ver = db.query(StrategyVersion).filter(
            StrategyVersion.strategy_id == strategy_id,
            StrategyVersion.version == version
        ).first()
        if existing_ver:
            raise ValueError(f"Version '{version}' already exists for strategy '{strategy_id}'.")

        # Run Validation
        val_report = self.validator.validate(config_dict)
        if val_report["status"] == "FAIL":
            raise ValueError(f"Strategy validation failed: {val_report['errors']}")

        # 1. Create version record
        ser_config = StrategyVersioning.serialize_config(config_dict)
        version_rec = StrategyVersion(
            strategy_id=strategy_id,
            version=version,
            configuration=ser_config
        )
        db.add(version_rec)

        # 2. Update active properties in parent template
        strategy.version = version
        strategy.structure = config_dict["structure"]
        strategy.format = config_dict["format"]
        strategy.instruction_style = config_dict["instruction_style"]
        strategy.reasoning_style = config_dict["reasoning_style"]
        strategy.prompt_length = config_dict["prompt_length"]
        strategy.example_count = int(config_dict["example_count"])
        strategy.selection_strategy = config_dict["selection_strategy"]
        strategy.ordering_strategy = config_dict["ordering_strategy"]
        strategy.output_constraints = json.dumps(config_dict.get("output_constraints", []))

        db.commit()
        logger.info(f"Added version '{version}' to strategy '{strategy_id}'")
        return version_rec

    def clone_strategy(self, db: Session, strategy_id: str, new_name: str) -> PromptStrategy:
        """
        Clones an existing strategy configuration under a new name, resetting version to 1.
        """
        src = db.query(PromptStrategy).filter(PromptStrategy.id == strategy_id).first()
        if not src:
            raise ValueError(f"Source strategy with ID {strategy_id} not found.")

        # Check name uniqueness
        existing = db.query(PromptStrategy).filter(PromptStrategy.name == new_name).first()
        if existing:
            raise ValueError(f"A strategy named '{new_name}' already exists.")

        constraints_list = json.loads(src.output_constraints) if src.output_constraints else []

        return self.create_strategy(
            db=db,
            name=new_name,
            structure=src.structure,
            format=src.format,
            instruction_style=src.instruction_style,
            reasoning_style=src.reasoning_style,
            prompt_length=src.prompt_length,
            example_count=src.example_count,
            selection_strategy=src.selection_strategy,
            ordering_strategy=src.ordering_strategy,
            output_constraints=constraints_list,
            description=f"Cloned from '{src.name}'. " + (src.description or "")
        )

    def get_strategy(self, db: Session, strategy_id: str) -> Optional[PromptStrategy]:
        return db.query(PromptStrategy).filter(PromptStrategy.id == strategy_id).first()

    def get_strategy_version(self, db: Session, strategy_id: str, version: str) -> Optional[StrategyVersion]:
        return db.query(StrategyVersion).filter(
            StrategyVersion.strategy_id == strategy_id,
            StrategyVersion.version == version
        ).first()

    def delete_strategy(self, db: Session, strategy_id: str) -> bool:
        strategy = db.query(PromptStrategy).filter(PromptStrategy.id == strategy_id).first()
        if not strategy:
            return False
        db.delete(strategy)
        db.commit()
        logger.info(f"Deleted strategy '{strategy_id}' and all associated versions.")
        return True

    def list_strategies(
        self,
        db: Session,
        structure: Optional[str] = None,
        format: Optional[str] = None,
        prompt_length: Optional[str] = None,
        reasoning_style: Optional[str] = None,
        example_count: Optional[int] = None
    ) -> List[PromptStrategy]:
        """
        Lists strategies registered in the database with optional filtering.
        """
        query = db.query(PromptStrategy)
        
        if structure:
            query = query.filter(PromptStrategy.structure == structure)
        if format:
            query = query.filter(PromptStrategy.format == format)
        if prompt_length:
            query = query.filter(PromptStrategy.prompt_length == prompt_length)
        if reasoning_style:
            query = query.filter(PromptStrategy.reasoning_style == reasoning_style)
        if example_count is not None:
            query = query.filter(PromptStrategy.example_count == example_count)
            
        return query.order_by(PromptStrategy.created_at.desc()).all()
