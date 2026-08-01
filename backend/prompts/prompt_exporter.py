import os
import json
import yaml
from typing import Dict, Any, Union
import logging

logger = logging.getLogger(__name__)

class PromptExporter:
    """
    Exports prompt templates and configurations to text, Markdown, JSON, or YAML.
    """
    
    def __init__(self, export_dir: str = "exports"):
        self.export_dir = export_dir
        os.makedirs(self.export_dir, exist_ok=True)

    def export(
        self, 
        prompt_data: Dict[str, Any], 
        filename: str, 
        format: str = "txt"
    ) -> str:
        """
        Exports prompt template data.
        prompt_data structure should be:
        {
            "name": str,
            "task_type": str,
            "strategy": str,
            "format": str,
            "current_version": str,
            "template_body": str,
            "description": str,
            ...
        }
        """
        format = format.lower().strip()
        if format not in ["txt", "md", "json", "yaml"]:
            raise ValueError(f"Unsupported export format: {format}")

        ext = f".{format}"
        if not filename.endswith(ext):
            filename += ext
            
        filepath = os.path.join(self.export_dir, filename)

        if format == "txt":
            # Just template body
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(prompt_data.get("template_body", ""))
                
        elif format == "md":
            # Frontmatter + Template body
            metadata = {k: v for k, v in prompt_data.items() if k != "template_body"}
            frontmatter = yaml.dump(metadata, default_flow_style=False)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("---\n")
                f.write(frontmatter)
                f.write("---\n\n")
                f.write(prompt_data.get("template_body", ""))
                
        elif format == "json":
            # JSON config
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(prompt_data, f, indent=2)
                
        elif format == "yaml":
            # YAML config
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(prompt_data, f, default_flow_style=False)

        logger.info(f"Exported prompt template to {filepath}")
        return filepath
