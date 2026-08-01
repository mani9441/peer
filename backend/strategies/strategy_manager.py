from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.strategies.strategy_validator import StrategyValidator
from backend.strategies.strategy_versioning import StrategyVersioning
from backend.strategies.strategy_metadata import StrategyMetadata
from backend.strategies.strategy_registry import StrategyRegistry
from backend.strategies.models import PromptStrategy, StrategyVersion

class StrategyManager:
    """
    Public manager orchestrating validation, registry storage, cloning, complexity metrics, and versions for prompt strategies.
    """

    def __init__(self):
        self.validator = StrategyValidator()
        self.versioning = StrategyVersioning()
        self.metadata = StrategyMetadata()
        self.registry = StrategyRegistry()

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
        """Validates configuration settings and registers strategy in DB."""
        return self.registry.create_strategy(
            db=db,
            name=name,
            structure=structure,
            format=format,
            instruction_style=instruction_style,
            reasoning_style=reasoning_style,
            prompt_length=prompt_length,
            example_count=example_count,
            selection_strategy=selection_strategy,
            ordering_strategy=ordering_strategy,
            output_constraints=output_constraints,
            description=description
        )

    def create_new_version(
        self,
        db: Session,
        strategy_id: str,
        version_name: str,
        config_dict: Dict[str, Any]
    ) -> StrategyVersion:
        """Validates configuration parameters and archives a new strategy version."""
        return self.registry.add_version(
            db=db,
            strategy_id=strategy_id,
            version=version_name,
            config_dict=config_dict
        )

    def clone_strategy(self, db: Session, strategy_id: str, new_name: str) -> PromptStrategy:
        """Clones a strategy configuration under a new name."""
        return self.registry.clone_strategy(db, strategy_id, new_name)

    def delete_strategy(self, db: Session, strategy_id: str) -> bool:
        """Deletes strategy configuration and associated versions."""
        return self.registry.delete_strategy(db, strategy_id)

    def validate_strategy(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Runs scope checks and logical constraints validation."""
        return self.validator.validate(config_dict)

    def estimate_complexity(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Runs complexity heuristics to get token count breakdown estimates."""
        return self.metadata.estimate_complexity(config_dict)

    def get_strategy(self, db: Session, strategy_id: str) -> Optional[PromptStrategy]:
        """Retrieves target prompt strategy details."""
        return self.registry.get_strategy(db, strategy_id)

    def get_strategy_version_config(self, db: Session, strategy_id: str, version: str) -> Optional[Dict[str, Any]]:
        """Loads and decodes strategy configuration for a target version."""
        ver_rec = self.registry.get_strategy_version(db, strategy_id, version)
        if not ver_rec:
            return None
        return self.versioning.deserialize_config(ver_rec.configuration)

    def get_next_version_name(self, current_version: str) -> str:
        """Utility to calculate increment of version name."""
        return self.versioning.increment_version(current_version)

    def list_strategies(
        self,
        db: Session,
        structure: Optional[str] = None,
        format: Optional[str] = None,
        prompt_length: Optional[str] = None,
        reasoning_style: Optional[str] = None,
        example_count: Optional[int] = None
    ) -> List[PromptStrategy]:
        """Lists registered prompt strategies with optional filters."""
        return self.registry.list_strategies(
            db=db,
            structure=structure,
            format=format,
            prompt_length=prompt_length,
            reasoning_style=reasoning_style,
            example_count=example_count
        )
