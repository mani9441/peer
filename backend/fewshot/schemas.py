from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class FewShotExample(BaseModel):
    id: str
    input: str  # The input text, e.g., the review text or passage question
    label: str  # The target label
    metadata: Dict[str, Any] = {}

class RetrievedExample(BaseModel):
    sample_id: str
    similarity: float
    label: str
    metadata: Dict[str, Any] = {}

class FewShotSet(BaseModel):
    query_sample: Dict[str, Any]
    examples: List[FewShotExample]
    strategy: str
    ordering: str
    diversity: str
