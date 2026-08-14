import re
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class PredictionInterpretationEngine:
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Stage 1: Clean whitespace, markdown blocks, quotes, and punctuation.
        """
        if not text:
            return ""
        text = text.strip()
        
        # Clean Markdown formatting blocks (e.g., ```json ... ``` or ``` ... ```)
        text = re.sub(r"```[a-zA-Z]*\s*", "", text)
        text = text.replace("```", "").strip()
        
        # Strip bold/italic markdown and outer quotes
        text = re.sub(r"\*\*|\*|__|_", "", text)
        text = text.strip("\"'`").strip()
        return text

    @staticmethod
    def extract_with_patterns(text: str, target_labels: List[str]) -> Optional[str]:
        """
        Stage 2: Answer Patterns (e.g., "Answer: True", "The answer is Joy")
        """
        patterns = [
            r"(?i)\b(?:answer|prediction|label|result|category|class)\s*:\s*(\w+)",
            r"(?i)\bthe\s+answer\s+is\s+(\w+)",
            r"(?i)\bprediction\s+is\s+(\w+)",
            r"(?i)\bclassified\s+as\s+(\w+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                extracted = match.group(1).strip().rstrip(".,;!?:")
                # Check if extracted word matches any target label
                for label in target_labels:
                    if extracted.lower() == str(label).lower():
                        return str(label)
        return None

    @staticmethod
    def map_boolean_synonyms(text: str, target_labels: List[str]) -> Optional[str]:
        """
        Stage 3: Synonym Mapping (Yes -> True, No -> False, 1 -> True, 0 -> False)
        """
        # Lowercased targets list
        targets_lower = [str(l).lower() for l in target_labels]
        
        has_true = "true" in targets_lower or "1" in targets_lower or "yes" in targets_lower
        has_false = "false" in targets_lower or "0" in targets_lower or "no" in targets_lower
        
        if not (has_true or has_false):
            return None

        # Clean text tokens
        tokens = re.findall(r"\b\w+\b", text.lower())
        
        # Check yes/true mappings
        yes_syns = {"yes", "true", "1", "correct", "right", "positive"}
        no_syns = {"no", "false", "0", "incorrect", "wrong", "negative"}
        
        # Find first token matching synonyms
        for tok in tokens:
            if tok in yes_syns:
                # Return the matching target representation
                for label in target_labels:
                    if str(label).lower() in {"true", "1", "yes"}:
                        return str(label)
            elif tok in no_syns:
                for label in target_labels:
                    if str(label).lower() in {"false", "0", "no"}:
                        return str(label)
        return None

    @staticmethod
    def interpret(
        response_text: str,
        task_type: str,
        target_labels: Optional[List[str]] = None,
        label_mapping: Optional[Dict[Any, str]] = None
    ) -> str:
        """
        Main entry point for interpreting raw LLM output into a canonical prediction label.
        """
        cleaned = PredictionInterpretationEngine.clean_text(response_text)
        if not cleaned:
            return ""

        # Prepare target labels normalized list
        targets = [str(l).strip() for l in target_labels] if target_labels else []
        
        # If no target labels, fallback to clean text
        if not targets:
            return cleaned

        # Prepare reverse mapping (e.g., "negative" -> "0", "0" -> "0")
        reverse_mapping = {}
        if label_mapping:
            for lbl_id, name in label_mapping.items():
                reverse_mapping[str(name).strip().lower()] = str(lbl_id).strip()
                reverse_mapping[str(lbl_id).strip().lower()] = str(lbl_id).strip()

        # -- Layer 1: Exact Match (Case-Insensitive) --
        for label in targets:
            if cleaned.lower() == label.lower():
                return label

        # Check label meanings exact match
        if reverse_mapping:
            for name, lbl_id in reverse_mapping.items():
                if cleaned.lower() == name.lower():
                    return lbl_id

        # -- Layer 2: Answer Patterns --
        pattern_match = PredictionInterpretationEngine.extract_with_patterns(cleaned, targets)
        if pattern_match:
            return pattern_match

        if reverse_mapping:
            pattern_match_names = PredictionInterpretationEngine.extract_with_patterns(cleaned, list(reverse_mapping.keys()))
            if pattern_match_names:
                return reverse_mapping[pattern_match_names.lower()]

        # -- Layer 3: Synonym & Boolean Mappings --
        bool_match = PredictionInterpretationEngine.map_boolean_synonyms(cleaned, targets)
        if bool_match:
            return bool_match

        # -- Layer 4: Standalone Target Label Word Boundaries --
        for label in targets:
            pattern = r"\b" + re.escape(label) + r"\b"
            if re.search(pattern, cleaned, re.IGNORECASE):
                return label

        # Check standalone text label meanings
        if reverse_mapping:
            for name, lbl_id in reverse_mapping.items():
                pattern = r"\b" + re.escape(name) + r"\b"
                if re.search(pattern, cleaned, re.IGNORECASE):
                    return lbl_id

        # -- Layer 5: Case-insensitive Substring Fallback --
        for label in targets:
            if label.lower() in cleaned.lower():
                return label

        if reverse_mapping:
            for name, lbl_id in reverse_mapping.items():
                if name.lower() in cleaned.lower():
                    return lbl_id

        # -- Layer 6: Clean punctuation fallback --
        cleaned_no_punct = re.sub(r"[^\w\s]", "", cleaned)
        for label in targets:
            if label.lower() in cleaned_no_punct.lower():
                return label

        if reverse_mapping:
            for name, lbl_id in reverse_mapping.items():
                if name.lower() in cleaned_no_punct.lower():
                    return lbl_id

        # If everything fails, return the cleaned raw string
        return cleaned
