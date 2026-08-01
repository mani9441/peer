import datetime
from typing import List, Optional, Tuple, Dict, Any
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from sqlalchemy import or_# pyrefly: ignore [missing-import]
from backend.prompts.models import PromptTemplate, PromptVersion, PromptTag
from backend.prompts.prompt_renderer import PromptRenderer
import logging

logger = logging.getLogger(__name__)

class PromptLibrary:
    """
    Handles SQLite transactions for CRUD, search, versioning, and categorizing prompt templates.
    """
    
    @staticmethod
    def create_prompt(
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
        Creates a new prompt template, registers the first version (v1), and adds tags.
        """
        # Generate unique identifier from name
        clean_name = "".join(c for c in name if c.isalnum() or c in ("_", "-")).lower()
        prompt_id = f"{clean_name}_{int(datetime.datetime.utcnow().timestamp())}"
        
        # Verify name is unique
        existing = db.query(PromptTemplate).filter(PromptTemplate.name == name).first()
        if existing:
            raise ValueError(f"A prompt template with name '{name}' already exists.")

        # Estimate tokens for template_body
        token_est = PromptRenderer.estimate_tokens(template_body)

        # 1. Create template model
        prompt = PromptTemplate(
            id=prompt_id,
            name=name,
            description=description,
            task_type=task_type,
            strategy=strategy,
            format=format,
            instruction_style=instruction_style,
            reasoning_style=reasoning_style,
            language=language,
            current_version="1"
        )
        db.add(prompt)
        db.flush()  # Retrieve prompt.id for versions/tags

        # 2. Add PromptVersion model (v1)
        version_rec = PromptVersion(
            prompt_id=prompt.id,
            version="1",
            template_body=template_body,
            change_notes="Initial version creation.",
            token_estimate=token_est
        )
        db.add(version_rec)

        # 3. Add PromptTag models
        if tags:
            for t in tags:
                tag_rec = PromptTag(prompt_id=prompt.id, tag=t.strip())
                db.add(tag_rec)

        db.commit()
        logger.info(f"Registered new prompt template: {prompt.id}")
        return prompt

    @staticmethod
    def add_version(
        db: Session,
        prompt_id: str,
        version: str,
        template_body: str,
        change_notes: Optional[str] = None
    ) -> PromptVersion:
        """
        Adds a new version to an existing prompt template and updates active version properties.
        """
        prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
        if not prompt:
            raise ValueError(f"Prompt template with ID {prompt_id} not found.")

        # Verify version doesn't exist
        existing_ver = db.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt_id,
            PromptVersion.version == version
        ).first()
        if existing_ver:
            raise ValueError(f"Version '{version}' already exists for prompt '{prompt_id}'.")

        token_est = PromptRenderer.estimate_tokens(template_body)

        # Create version record
        version_rec = PromptVersion(
            prompt_id=prompt_id,
            version=version,
            template_body=template_body,
            change_notes=change_notes,
            token_estimate=token_est
        )
        db.add(version_rec)

        # Update parent template active version properties
        prompt.current_version = version
        prompt.updated_at = datetime.datetime.utcnow()

        db.commit()
        logger.info(f"Added version '{version}' to prompt template '{prompt_id}'")
        return version_rec

    @staticmethod
    def get_prompt(db: Session, prompt_id: str) -> Optional[PromptTemplate]:
        return db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()

    @staticmethod
    def get_prompt_version(db: Session, prompt_id: str, version: str) -> Optional[PromptVersion]:
        return db.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt_id,
            PromptVersion.version == version
        ).first()

    @staticmethod
    def delete_prompt(db: Session, prompt_id: str) -> bool:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
        if not prompt:
            return False
        db.delete(prompt)
        db.commit()
        logger.info(f"Deleted prompt template '{prompt_id}' and all associated versions/tags.")
        return True

    @staticmethod
    def list_prompts(
        db: Session,
        task_type: Optional[str] = None,
        strategy: Optional[str] = None,
        format: Optional[str] = None,
        tag: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[PromptTemplate]:
        """
        Lists and filters prompt templates.
        """
        query = db.query(PromptTemplate)

        if task_type:
            query = query.filter(PromptTemplate.task_type == task_type)
        if strategy:
            query = query.filter(PromptTemplate.strategy == strategy)
        if format:
            query = query.filter(PromptTemplate.format == format)
        if tag:
            query = query.join(PromptTag).filter(PromptTag.tag == tag)
        if search_query:
            query = query.filter(
                or_(
                    PromptTemplate.name.contains(search_query),
                    PromptTemplate.description.contains(search_query)
                )
            )

        return query.order_by(PromptTemplate.created_at.desc()).all()
