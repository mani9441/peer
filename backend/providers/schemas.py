import datetime
from pydantic import BaseModel, Field
from typing import Optional

class GenerationConfig(BaseModel):
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    seed: Optional[int] = None

class LLMRequest(BaseModel):
    experiment_id: Optional[str] = None
    provider: str
    model: str
    prompt: str
    generation_config: Optional[GenerationConfig] = Field(default_factory=GenerationConfig)

class LLMResponse(BaseModel):
    provider: str
    model: str
    response_text: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    finish_reason: Optional[str] = None
    request_timestamp: datetime.datetime
    response_timestamp: datetime.datetime
    status: str
