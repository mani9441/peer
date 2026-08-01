from pydantic import BaseModel, Field
from typing import Optional, List
import datetime

class ExperimentBase(BaseModel):
    name: str
    description: Optional[str] = None
    dataset_id: str
    template_id: Optional[str] = None
    strategy_id: str
    provider: str
    model: str

class ExperimentCreate(ExperimentBase):
    pass

class ExperimentResponse(ExperimentBase):
    id: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class RunMetadataBase(BaseModel):
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    seed: Optional[int] = None
    prompt_length: Optional[str] = None
    fewshot_count: Optional[int] = None
    selection_strategy: Optional[str] = None
    ordering_strategy: Optional[str] = None

class RunMetadataResponse(RunMetadataBase):
    id: int
    run_id: str

    class Config:
        from_attributes = True


class RunMetricBase(BaseModel):
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    latency: Optional[float] = None
    cost: Optional[float] = None
    consistency: Optional[float] = None

class RunMetricResponse(RunMetricBase):
    id: int
    run_id: str

    class Config:
        from_attributes = True


class SampleResponseBase(BaseModel):
    sample_index: int
    prompt: str
    response: str
    latency: float
    input_tokens: int
    output_tokens: int
    cost: float
    finish_reason: Optional[str] = None
    ground_truth: Optional[str] = None
    prediction: Optional[str] = None
    is_correct: Optional[bool] = None

class SampleResponseView(SampleResponseBase):
    id: int
    run_id: str

    class Config:
        from_attributes = True


class ExperimentRunResponse(BaseModel):
    id: str
    experiment_id: str
    run_number: int
    status: str
    started_at: datetime.datetime
    finished_at: Optional[datetime.datetime] = None
    metadata_rel: Optional[RunMetadataResponse] = None
    metrics: Optional[RunMetricResponse] = None

    class Config:
        from_attributes = True
