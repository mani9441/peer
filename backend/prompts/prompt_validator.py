from typing import Dict, Any, List
from jinja2 import Environment, meta
import logging

logger = logging.getLogger(__name__)

class PromptValidator:
    """
    Validates prompt templates for syntax errors and placeholder completeness.
    """
    
    def __init__(self):
        self.env = Environment()

    def validate(self, template_body: str, task_type: str) -> Dict[str, Any]:
        """
        Validates Jinja2 syntax and placeholder variables.
        Returns a dictionary validation report.
        """
        report = {
            "status": "PASS",
            "errors": [],
            "warnings": [],
            "placeholders": []
        }
        
        if not template_body or not template_body.strip():
            report["status"] = "FAIL"
            report["errors"].append("Template body cannot be empty.")
            return report

        # 1. Syntax Check
        try:
            ast = self.env.parse(template_body)
            variables = list(meta.find_undeclared_variables(ast))
            report["placeholders"] = sorted(variables)
        except Exception as e:
            report["status"] = "FAIL"
            report["errors"].append(f"Jinja2 Syntax Error: {str(e)}")
            return report

        # 2. Variable Consistency Warnings
        task_type = task_type.lower().strip()
        
        if task_type == "classification":
            # Classification usually expects at least 'input' or 'text'
            if not any(v in variables for v in ["input", "text", "sentence", "content"]):
                report["warnings"].append(
                    "Classification template lacks a standard input placeholder (e.g., '{{input}}' or '{{text}}')."
                )
        elif task_type == "qa":
            # QA usually expects 'question' and 'context'
            if "question" not in variables:
                report["warnings"].append("QA template lacks a '{{question}}' placeholder.")
            if "context" not in variables:
                report["warnings"].append("QA template lacks a '{{context}}' placeholder.")
        
        # Check for empty variables
        if not variables:
            report["warnings"].append("No placeholders (like '{{input}}') detected. This template will render statically.")

        # 3. Warn on excessive length (e.g. > 10,000 characters for a raw template)
        if len(template_body) > 10000:
            report["warnings"].append(
                f"Template body length ({len(template_body)} chars) is very large. Check if this fits model limits."
            )

        return report
