from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ContentGenParams(BaseModel):
    samples_per_type: int = Field(10, gt=0, le=100, description="Number of samples to generate for each workload type.")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Controls randomness. Higher is more creative.")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling probability.")
    top_k: Optional[int] = Field(None, ge=0, description="Top-k sampling control.")
    max_cores: int = Field(4, ge=1, description="Max CPU cores to use.")

class LogGenParams(BaseModel):
    corpus_id: str = Field(..., description="The ID of the content corpus to use for generation.")
    num_logs: int = Field(1000, gt=0, le=100000, description="Number of log entries to generate.")
    max_cores: int = Field(4, ge=1, description="Max CPU cores to use.")

class SyntheticDataGenParams(BaseModel):
    num_traces: int = Field(10000, gt=0, le=100000, description="Number of traces to generate.")
    num_users: int = Field(100, gt=0, le=10000, description="Number of unique users to simulate.")
    error_rate: float = Field(0.05, ge=0.0, le=1.0, description="The fraction of traces that should be errors.")
    event_types: List[str] = Field(default_factory=lambda: ["search", "login", "purchase", "logout"], description="A list of event types to simulate.")
    source_table: str = Field("content_corpus", description="The name of the source ClickHouse table for the content corpus.")
    destination_table: str = Field("synthetic_data", description="The name of the destination ClickHouse table for the generated data.")

class DataIngestionParams(BaseModel):
    data_path: str = Field(..., description="The path to the data file to ingest.")
    table_name: str = Field(..., description="The name of the table to ingest the data into.")

class ContentCorpusGenParams(BaseModel):
    samples_per_type: int = Field(10, gt=0, le=100, description="Number of samples to generate for each workload type.")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Controls randomness. Higher is more creative.")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling probability.")
    top_k: Optional[int] = Field(None, ge=0, description="Top-k sampling control.")
    max_cores: int = Field(4, ge=1, description="Max CPU cores to use.")
    clickhouse_table: str = Field('content_corpus', description="The name of the ClickHouse table to store the corpus in.")
