import pandas as pd
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class DatasetValidator:
    """
    Validates a dataset according to standard schema requirements and checks for quality issues.
    """
    
    CLASSIFICATION_TEXT_CANDIDATES = ["text", "sentence", "content", "document", "review", "input", "sentence1", "sentence2", "premise", "hypothesis"]
    CLASSIFICATION_LABEL_CANDIDATES = ["label", "target", "class", "sentiment", "category", "coarse_label", "fine_label"]
    
    QA_CONTEXT_CANDIDATES = ["context", "passage", "text"]
    QA_QUESTION_CANDIDATES = ["question", "query"]
    QA_ANSWER_CANDIDATES = ["answers", "answer", "target"]

    @classmethod
    def detect_and_normalize_columns(cls, df: pd.DataFrame, task_type: str, custom_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Detects relevant columns and returns a mapping and validation report.
        If custom_mapping is provided, it uses that instead of auto-detection.
        """
        report = {
            "status": "PASS",
            "errors": [],
            "warnings": [],
            "column_mapping": {},
            "task_type": task_type
        }
        
        columns = [str(c) for c in df.columns]
        mapping = {}
        
        if task_type == "classification":
            # Find Text Column
            text_col = None
            if custom_mapping and "text" in custom_mapping:
                text_col = custom_mapping["text"]
            else:
                for cand in cls.CLASSIFICATION_TEXT_CANDIDATES:
                    # Case insensitive check
                    match = next((c for c in columns if c.lower() == cand.lower()), None)
                    if match:
                        text_col = match
                        break
            
            if text_col not in df.columns:
                report["status"] = "FAIL"
                report["errors"].append(f"Text column not found. Checked candidates: {cls.CLASSIFICATION_TEXT_CANDIDATES}")
            else:
                mapping["text"] = text_col
                
            # Find Label Column
            label_col = None
            if custom_mapping and "label" in custom_mapping:
                label_col = custom_mapping["label"]
            else:
                for cand in cls.CLASSIFICATION_LABEL_CANDIDATES:
                    match = next((c for c in columns if c.lower() == cand.lower()), None)
                    if match:
                        label_col = match
                        break
            
            if label_col not in df.columns:
                report["status"] = "FAIL"
                report["errors"].append(f"Label column not found. Checked candidates: {cls.CLASSIFICATION_LABEL_CANDIDATES}")
            else:
                mapping["label"] = label_col
                
        elif task_type == "qa":
            # Find Context Column
            context_col = None
            if custom_mapping and "context" in custom_mapping:
                context_col = custom_mapping["context"]
            else:
                for cand in cls.QA_CONTEXT_CANDIDATES:
                    match = next((c for c in columns if c.lower() == cand.lower()), None)
                    if match:
                        context_col = match
                        break
            
            if context_col not in df.columns:
                report["status"] = "FAIL"
                report["errors"].append(f"Context column not found. Checked candidates: {cls.QA_CONTEXT_CANDIDATES}")
            else:
                mapping["context"] = context_col
                
            # Find Question Column
            question_col = None
            if custom_mapping and "question" in custom_mapping:
                question_col = custom_mapping["question"]
            else:
                for cand in cls.QA_QUESTION_CANDIDATES:
                    match = next((c for c in columns if c.lower() == cand.lower()), None)
                    if match:
                        question_col = match
                        break
            
            if question_col not in df.columns:
                report["status"] = "FAIL"
                report["errors"].append(f"Question column not found. Checked candidates: {cls.QA_QUESTION_CANDIDATES}")
            else:
                mapping["question"] = question_col
                
            # Find Answers/Answer Column
            answers_col = None
            if custom_mapping and "answers" in custom_mapping:
                answers_col = custom_mapping["answers"]
            else:
                for cand in cls.QA_ANSWER_CANDIDATES:
                    match = next((c for c in columns if c.lower() == cand.lower()), None)
                    if match:
                        answers_col = match
                        break
            
            if answers_col not in df.columns:
                report["status"] = "FAIL"
                report["errors"].append(f"Answers/Answer column not found. Checked candidates: {cls.QA_ANSWER_CANDIDATES}")
            else:
                mapping["answers"] = answers_col
        else:
            report["status"] = "FAIL"
            report["errors"].append(f"Unsupported task type: {task_type}")
            
        report["column_mapping"] = mapping
        return report

    def validate(self, df: pd.DataFrame, task_type: str, custom_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Validates the schema, content quality, missing values, duplicates, and returns a detailed report.
        """
        if df.empty:
            return {
                "status": "FAIL",
                "errors": ["Dataset is empty."],
                "warnings": [],
                "column_mapping": {},
                "task_type": task_type
            }

        # Step 1: Check Columns
        report = self.detect_and_normalize_columns(df, task_type, custom_mapping)
        if report["status"] == "FAIL":
            return report

        mapping = report["column_mapping"]
        
        # Step 2: Check missing values and duplicates
        total_rows = len(df)
        
        if task_type == "classification":
            text_col = mapping["text"]
            label_col = mapping["label"]
            
            # Check missing
            missing_text = df[text_col].isna().sum()
            missing_label = df[label_col].isna().sum()
            
            if missing_text > 0:
                report["warnings"].append(f"Found {missing_text} ({missing_text/total_rows*100:.2f}%) missing values in text column '{text_col}'.")
            if missing_label > 0:
                report["errors"].append(f"Found {missing_label} ({missing_label/total_rows*100:.2f}%) missing values in label column '{label_col}'.")
                report["status"] = "FAIL"
                
            # Check duplicates
            duplicates = df.duplicated(subset=[text_col]).sum()
            if duplicates > 0:
                report["warnings"].append(f"Found {duplicates} ({duplicates/total_rows*100:.2f}%) duplicate text records.")
                
            # Class distribution warnings
            class_counts = df[label_col].dropna().value_counts()
            if len(class_counts) <= 1:
                report["errors"].append("Dataset contains 1 or fewer distinct classes. Classification requires at least 2 classes.")
                report["status"] = "FAIL"
                
        elif task_type == "qa":
            context_col = mapping["context"]
            question_col = mapping["question"]
            answers_col = mapping["answers"]
            
            missing_context = df[context_col].isna().sum()
            missing_question = df[question_col].isna().sum()
            missing_answers = df[answers_col].isna().sum()
            
            if missing_context > 0:
                report["errors"].append(f"Found {missing_context} missing contexts.")
                report["status"] = "FAIL"
            if missing_question > 0:
                report["errors"].append(f"Found {missing_question} missing questions.")
                report["status"] = "FAIL"
            if missing_answers > 0:
                report["warnings"].append(f"Found {missing_answers} missing answers.")
            
            # Check answer format
            sample_answer = df[answers_col].dropna().iloc[0] if not df[answers_col].dropna().empty else None
            if sample_answer is not None:
                # SQuAD represents answers as: dict with 'text' (list of strings) and 'answer_start' (list of ints)
                if isinstance(sample_answer, dict):
                    if "text" not in sample_answer:
                        report["warnings"].append("Answers dict column does not contain standard 'text' subkey.")
                elif isinstance(sample_answer, (list, tuple)):
                    pass
                elif not isinstance(sample_answer, str):
                    report["warnings"].append(f"Answer column has unusual type: {type(sample_answer)}. Expected dict, list, or string.")
                    
        return report
