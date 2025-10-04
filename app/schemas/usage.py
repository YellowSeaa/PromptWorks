from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class UsageOverview(BaseModel):
    total_tokens: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    call_count: int = Field(default=0, ge=0)


class UsageModelSummary(BaseModel):
    model_key: str
    model_name: str
    provider: str
    total_tokens: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    call_count: int = Field(default=0, ge=0)

    model_config = ConfigDict(from_attributes=True)


class UsageTimeseriesPoint(BaseModel):
    date: date
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    call_count: int = Field(default=0, ge=0)

    model_config = ConfigDict(from_attributes=True)


__all__ = ["UsageOverview", "UsageModelSummary", "UsageTimeseriesPoint"]
