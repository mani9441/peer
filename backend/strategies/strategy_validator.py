from typing import Dict, Any, List

class StrategyValidator:
    """
    Validates experimental prompt strategy configurations for consistency and structural rules.
    """

    ALLOWED_STRUCTURES = ["Instruction", "Example-Based", "Mixed"]
    ALLOWED_FORMATS = ["Plain Text", "Markdown", "JSON", "XML"]
    ALLOWED_LEVELS = ["Short", "Medium", "Long"]
    ALLOWED_STYLES = ["Simple", "Detailed", "Step-by-Step", "None"]
    ALLOWED_REASONING = ["None", "Chain-of-Thought"]
    ALLOWED_SELECTION = ["Random", "Balanced", "Semantic", "None"]
    ALLOWED_ORDERING = ["Original", "Random", "Similarity", "None"]
    ALLOWED_CONSTRAINTS = ["label_only", "no_explanation", "json_format", "markdown_format", "single_sentence", "max_len_50"]

    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates a strategy configuration dictionary.
        Returns a report dictionary.
        """
        report = {
            "status": "PASS",
            "errors": [],
            "warnings": []
        }

        # 1. Required Fields Check
        required_fields = [
            "name", "structure", "format", "prompt_length", 
            "instruction_style", "reasoning_style", "example_count",
            "selection_strategy", "ordering_strategy"
        ]
        
        for field in required_fields:
            if field not in config or config[field] is None:
                report["status"] = "FAIL"
                report["errors"].append(f"Missing required field: '{field}'")
                
        if report["status"] == "FAIL":
            return report

        # 2. Variable Value Scope Checks
        structure = config["structure"]
        if structure not in self.ALLOWED_STRUCTURES:
            report["status"] = "FAIL"
            report["errors"].append(f"Invalid structure '{structure}'. Allowed: {self.ALLOWED_STRUCTURES}")

        fmt = config["format"]
        if fmt not in self.ALLOWED_FORMATS:
            report["status"] = "FAIL"
            report["errors"].append(f"Invalid format '{fmt}'. Allowed: {self.ALLOWED_FORMATS}")

        length = config["prompt_length"]
        if length not in self.ALLOWED_LEVELS:
            report["status"] = "FAIL"
            report["errors"].append(f"Invalid prompt length level '{length}'. Allowed: {self.ALLOWED_LEVELS}")

        style = config["instruction_style"]
        if style not in self.ALLOWED_STYLES:
            report["status"] = "FAIL"
            report["errors"].append(f"Invalid instruction style '{style}'. Allowed: {self.ALLOWED_STYLES}")

        reasoning = config["reasoning_style"]
        if reasoning not in self.ALLOWED_REASONING:
            report["status"] = "FAIL"
            report["errors"].append(f"Invalid reasoning style '{reasoning}'. Allowed: {self.ALLOWED_REASONING}")

        try:
            example_count = int(config["example_count"])
            if example_count < 0:
                report["status"] = "FAIL"
                report["errors"].append("Example count cannot be negative.")
        except (ValueError, TypeError):
            report["status"] = "FAIL"
            report["errors"].append("Example count must be an integer.")
            example_count = 0

        selection = config["selection_strategy"]
        if selection not in self.ALLOWED_SELECTION:
            report["status"] = "FAIL"
            report["errors"].append(f"Invalid selection strategy '{selection}'. Allowed: {self.ALLOWED_SELECTION}")

        ordering = config["ordering_strategy"]
        if ordering not in self.ALLOWED_ORDERING:
            report["status"] = "FAIL"
            report["errors"].append(f"Invalid ordering strategy '{ordering}'. Allowed: {self.ALLOWED_ORDERING}")

        # Constraints validation
        constraints = config.get("output_constraints", [])
        if not isinstance(constraints, list):
            report["status"] = "FAIL"
            report["errors"].append("Output constraints must be a list.")
        else:
            for c in constraints:
                if c not in self.ALLOWED_CONSTRAINTS:
                    report["status"] = "FAIL"
                    report["errors"].append(f"Invalid output constraint '{c}'. Allowed: {self.ALLOWED_CONSTRAINTS}")

        # Exit early if structural parameters are wrong
        if report["status"] == "FAIL":
            return report

        # 3. Variable Compatibility / Logical Consistency Rules
        
        # Rule A: Instruction structure allows NO examples
        if structure == "Instruction" and example_count > 0:
            report["status"] = "FAIL"
            report["errors"].append(
                f"Structure is 'Instruction' but example count is set to {example_count}. "
                "Instruction-only prompts cannot contain few-shot examples."
            )

        # Rule B: Mixed or Example-Based structure REQUIRES examples
        if structure in ["Example-Based", "Mixed"] and example_count == 0:
            report["status"] = "FAIL"
            report["errors"].append(
                f"Structure is '{structure}' but example count is 0. "
                "Few-shot structures require at least 1 demonstration example."
            )

        # Rule C: If few-shot examples are zero, selection/ordering should be 'None'
        if example_count == 0:
            if selection != "None" or ordering != "None":
                report["warnings"].append(
                    f"Example count is 0, but selection strategy '{selection}' and/or ordering strategy "
                    f"'{ordering}' are active. These will be ignored during prompt generation."
                )
                
        # Rule D: If few-shot examples are enabled, selection/ordering should not be 'None'
        if example_count > 0:
            if selection == "None" or ordering == "None":
                report["warnings"].append(
                    f"Few-shot examples count is {example_count}, but selection is '{selection}' "
                    f"and/or ordering is '{ordering}'. Ensure you intended to disable these settings."
                )

        # Rule E: Format vs Constraint consistency
        if fmt == "JSON" and "json_format" not in constraints:
            report["warnings"].append(
                "Prompt format is JSON, but output constraints do not enforce 'json_format'. "
                "Consider adding a constraint to guarantee valid JSON formatting."
            )

        return report
