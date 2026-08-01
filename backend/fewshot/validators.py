from typing import List, Dict, Any, Optional
import pandas as pd
from backend.fewshot.schemas import FewShotExample

class FewShotValidator:
    """
    Executes structural integrity checks on the generated few-shot demonstration example set.
    """

    @staticmethod
    def validate_few_shot_set(
        examples: List[FewShotExample], 
        query_id: Optional[str],
        query_text: Optional[str],
        text_col: Optional[str],
        expected_count: int
    ) -> List[str]:
        """
        Validates the few-shot set against strict duplication and exclusion rules.
        Returns a list of error messages (empty if valid).
        """
        errors = []

        # 1. Check exact size match
        if len(examples) != expected_count:
            # Only add as error if expected count was positive
            if expected_count > 0:
                errors.append(f"Expected exactly {expected_count} examples, but built {len(examples)}.")

        # 2. Duplicate Detection (IDs and Texts)
        seen_ids = set()
        seen_texts = set()
        for idx, ex in enumerate(examples):
            # Check ID duplicates
            if ex.id in seen_ids:
                errors.append(f"Duplicate example ID detected: {ex.id}")
            seen_ids.add(ex.id)

            # Check text duplicates
            if ex.input in seen_texts:
                errors.append(f"Duplicate example input text detected at position {idx}.")
            seen_texts.add(ex.input)

            # Check label empty
            if not ex.label or not str(ex.label).strip():
                errors.append(f"Missing label for example ID {ex.id}")

        # 3. Query Leakage Prevention
        if query_id:
            if query_id in seen_ids:
                errors.append(f"Target query ID '{query_id}' is leaked inside the few-shot demonstrations.")
        if query_text:
            cleaned_query = query_text.strip().lower()
            for ex in examples:
                if ex.input.strip().lower() == cleaned_query:
                    errors.append("Target query text matched one of the demonstrations, leaking test data.")

        return errors
