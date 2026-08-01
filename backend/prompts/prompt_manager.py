from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session# pyrefly: ignore [missing-import]

from backend.prompts.prompt_renderer import PromptRenderer
from backend.prompts.prompt_validator import PromptValidator
from backend.prompts.prompt_versioning import PromptVersioning
from backend.prompts.prompt_library import PromptLibrary
from backend.prompts.prompt_exporter import PromptExporter
from backend.prompts.models import PromptTemplate, PromptVersion

class PromptManager:
    """
    Public orchestrator for prompt template validation, rendering, library tracking, and version diffs.
    """
    
    def __init__(self, export_dir: str = "exports"):
        self.renderer = PromptRenderer()
        self.validator = PromptValidator()
        self.versioning = PromptVersioning()
        self.library = PromptLibrary()
        self.exporter = PromptExporter(export_dir=export_dir)

    def create_prompt(
        self,
        db: Session,
        name: str,
        template_body: str,
        task_type: str,
        strategy: str,
        format: str,
        instruction_style: str,
        reasoning_style: str,
        description: Optional[str] = None,
        language: str = "English",
        tags: Optional[List[str]] = None
    ) -> PromptTemplate:
        """
        Validates template syntax and saves it to the library.
        """
        # Run validation
        val_report = self.validate_prompt(template_body, task_type)
        if val_report["status"] == "FAIL":
            raise ValueError(f"Template validation failed: {val_report['errors']}")

        return self.library.create_prompt(
            db=db,
            name=name,
            template_body=template_body,
            task_type=task_type,
            strategy=strategy,
            format=format,
            instruction_style=instruction_style,
            reasoning_style=reasoning_style,
            description=description,
            language=language,
            tags=tags
        )

    def create_new_version(
        self,
        db: Session,
        prompt_id: str,
        version_name: str,
        template_body: str,
        change_notes: Optional[str] = None
    ) -> PromptVersion:
        """
        Validates syntax and creates a new template version.
        """
        prompt = self.get_prompt(db, prompt_id)
        if not prompt:
            raise ValueError(f"Prompt template with ID {prompt_id} not found.")

        # Run validation
        val_report = self.validate_prompt(template_body, prompt.task_type)
        if val_report["status"] == "FAIL":
            raise ValueError(f"Template validation failed: {val_report['errors']}")

        return self.library.add_version(
            db=db,
            prompt_id=prompt_id,
            version=version_name,
            template_body=template_body,
            change_notes=change_notes
        )

    def validate_prompt(self, template_body: str, task_type: str) -> Dict[str, Any]:
        """Validates Jinja2 syntax and required parameters."""
        return self.validator.validate(template_body, task_type)

    def render_prompt(self, template_body: str, placeholders: Dict[str, Any]) -> str:
        """Renders the template with dynamic parameters."""
        return self.renderer.render(template_body, placeholders)

    def estimate_tokens(self, text: str) -> int:
        """Estimates the token size of a given text string."""
        return self.renderer.estimate_tokens(text)

    def get_prompt_metrics(self, text: str) -> Dict[str, Any]:
        """Gets character, word, and token counts for a prompt string."""
        return self.renderer.get_metrics(text)

    def list_prompts(
        self,
        db: Session,
        task_type: Optional[str] = None,
        strategy: Optional[str] = None,
        format: Optional[str] = None,
        tag: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[PromptTemplate]:
        """Lists registered prompt templates matching filter criteria."""
        return self.library.list_prompts(db, task_type, strategy, format, tag, search_query)

    def get_prompt(self, db: Session, prompt_id: str) -> Optional[PromptTemplate]:
        """Retrieves a registered prompt template."""
        return self.library.get_prompt(db, prompt_id)

    def get_prompt_version_body(self, db: Session, prompt_id: str, version: str) -> Optional[str]:
        """Fetches the raw template body text for a specific version."""
        ver_rec = self.library.get_prompt_version(db, prompt_id, version)
        return ver_rec.template_body if ver_rec else None

    def get_diff(self, body_a: str, body_b: str, name_a: str = "v1", name_b: str = "v2") -> str:
        """Generates visual text diff lines between template versions."""
        return self.versioning.get_diff(body_a, body_b, name_a, name_b)

    def get_next_version_name(self, current_version: str) -> str:
        """Helper to increment active version string (e.g. '1' -> '2')."""
        return self.versioning.increment_version(current_version)

    def delete_prompt(self, db: Session, prompt_id: str) -> bool:
        """Deletes template and associated rows."""
        return self.library.delete_prompt(db, prompt_id)

    def export_prompt(
        self, 
        db: Session, 
        prompt_id: str, 
        version: str, 
        filename: str, 
        format: str = "txt"
    ) -> str:
        """Exports a template version to exports folder."""
        prompt = self.get_prompt(db, prompt_id)
        if not prompt:
            raise ValueError(f"Prompt template with ID {prompt_id} not found.")

        ver_rec = self.library.get_prompt_version(db, prompt_id, version)
        if not ver_rec:
            raise ValueError(f"Version '{version}' not found for prompt '{prompt_id}'.")

        tags_list = [t.tag for t in prompt.tags]
        prompt_data = {
            "id": prompt.id,
            "name": prompt.name,
            "description": prompt.description,
            "task_type": prompt.task_type,
            "strategy": prompt.strategy,
            "format": prompt.format,
            "instruction_style": prompt.instruction_style,
            "reasoning_style": prompt.reasoning_style,
            "language": prompt.language,
            "version": version,
            "tags": tags_list,
            "template_body": ver_rec.template_body,
            "token_estimate": ver_rec.token_estimate
        }

        return self.exporter.export(prompt_data, filename, format)
