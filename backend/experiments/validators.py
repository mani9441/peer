from typing import Optional
from sqlalchemy.orm import Session
from backend.providers.exceptions import ConfigurationError
from backend.datasets.models import Dataset
from backend.prompts.models import PromptTemplate
from backend.strategies.models import PromptStrategy
from backend.providers.models import Provider as DBProvider, Model as DBModel

class ExperimentValidator:
    @staticmethod
    def validate_config(
        db: Session,
        dataset_id: str,
        template_id: Optional[str],
        strategy_id: str,
        provider: str,
        model: str
    ) -> None:
        """
        Validates that all configured assets exist in the database and are enabled.
        """
        # Validate dataset
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ConfigurationError(f"Dataset with ID '{dataset_id}' does not exist.")

        # Validate template (if custom template provided)
        if template_id:
            template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
            if not template:
                raise ConfigurationError(f"Prompt template with ID '{template_id}' does not exist.")

        # Validate strategy
        strategy = db.query(PromptStrategy).filter(PromptStrategy.id == strategy_id).first()
        if not strategy:
            raise ConfigurationError(f"Prompt strategy with ID '{strategy_id}' does not exist.")

        # Validate provider
        prov = db.query(DBProvider).filter(DBProvider.id == provider.lower()).first()
        if prov and not prov.enabled:
            raise ConfigurationError(f"Provider '{provider}' is disabled.")
