from typing import Dict, Any

class StrategyMetadata:
    """
    Computes heuristic complexity estimations and metrics profiles for prompt strategies.
    """

    # Real token count heuristics
    INSTRUCTION_STYLE_TOKENS = {
        "Simple": 10,
        "Detailed": 45,
        "Step-by-Step": 60,
        "None": 0
    }

    FORMAT_TOKENS = {
        "Plain Text": 0,
        "Markdown": 15,
        "JSON": 30,
        "XML": 25
    }

    REASONING_TOKENS = {
        "None": 0,
        "Chain-of-Thought": 25
    }

    CONSTRAINT_TOKENS_VAL = 8
    FEW_SHOT_AVG_TOKENS = 150  # Average token footprint per few-shot example

    @classmethod
    def estimate_complexity(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates expected token usage breakdown and complexity summary.
        """
        # Fetch configurations safely
        style = config.get("instruction_style", "Simple")
        fmt = config.get("format", "Plain Text")
        reasoning = config.get("reasoning_style", "None")
        example_count = int(config.get("example_count", 0))
        constraints_list = config.get("output_constraints", [])
        
        # 1. Calculation
        instruction_tokens = cls.INSTRUCTION_STYLE_TOKENS.get(style, 10)
        format_tokens = cls.FORMAT_TOKENS.get(fmt, 0)
        reasoning_tokens = cls.REASONING_TOKENS.get(reasoning, 0)
        
        constraints_count = len(constraints_list)
        constraints_tokens = constraints_count * cls.CONSTRAINT_TOKENS_VAL
        
        few_shot_tokens = example_count * cls.FEW_SHOT_AVG_TOKENS
        
        # Expected base overhead without the actual run dataset sample text
        expected_overhead_size = instruction_tokens + format_tokens + reasoning_tokens + constraints_tokens
        
        # Expected total size (overhead + few-shot examples)
        expected_prompt_size = expected_overhead_size + few_shot_tokens

        # Recommendations or warnings based on total estimated size
        complexity_rating = "Low"
        if expected_prompt_size > 1000:
            complexity_rating = "High"
        elif expected_prompt_size > 300:
            complexity_rating = "Medium"

        return {
            "instruction_tokens": instruction_tokens,
            "formatting_tokens": format_tokens,
            "reasoning_tokens": reasoning_tokens,
            "constraints_tokens": constraints_tokens,
            "few_shot_tokens": few_shot_tokens,
            "expected_prompt_overhead": expected_overhead_size,
            "expected_prompt_size": expected_prompt_size,
            "complexity_rating": complexity_rating,
            "example_count": example_count,
            "constraints_count": constraints_count
        }
