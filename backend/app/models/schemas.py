from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class TraceRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=64, description="Gene symbol or variant id")


class SourceResult(BaseModel):
    source: str
    hits: int
    data: list[dict[str, Any]]
    error: str | None = None


class TraceResponse(BaseModel):
    query: str
    brief: str
    eval_score: float
    sources: list[SourceResult]
    created_at: datetime


class HistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    query: str
    brief: str
    eval_score: float
    clinvar_hits: int
    pubmed_hits: int
    uniprot_hits: int
    created_at: datetime
