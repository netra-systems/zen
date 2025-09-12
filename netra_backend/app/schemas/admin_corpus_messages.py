"""
Admin Corpus WebSocket Messages

WebSocket message types for admin corpus operations.
All models follow Pydantic with strong typing per type_safety.xml.
Maximum 300 lines per conventions.xml, each function  <= 8 lines.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CorpusIntent(str, Enum):
    """Intent types for corpus operations"""
    DISCOVER = "discover"
    SUGGEST = "suggest"
    VALIDATE = "validate"
    CREATE = "create"
    GENERATE = "generate"
    OPTIMIZE = "optimize"
    EXPORT = "export"
    STATUS = "status"


class CorpusDiscoveryRequest(BaseModel):
    """Request for corpus discovery operations"""
    model_config = ConfigDict(extra="forbid")
    
    message_type: Literal["corpus_discovery_request"] = "corpus_discovery_request"
    intent: Literal["discover", "suggest", "validate"]
    category: Optional[str] = None
    query: str
    context: Dict[str, Any] = Field(default_factory=dict)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorpusDiscoveryResponse(BaseModel):
    """Response for corpus discovery operations"""
    model_config = ConfigDict(extra="forbid")
    
    message_type: Literal["corpus_discovery_response"] = "corpus_discovery_response"
    intent: str
    category: Optional[str] = None
    items: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    parameters: Optional[Dict[str, Any]] = None
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorpusGenerationRequest(BaseModel):
    """Request for corpus generation"""
    model_config = ConfigDict(extra="forbid")
    
    message_type: Literal["corpus_generation_request"] = "corpus_generation_request"
    domain: str
    workload_types: List[str]
    parameters: Dict[str, Any]
    options: Dict[str, Any] = Field(default_factory=dict)
    target_table: Optional[str] = None
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorpusGenerationResponse(BaseModel):
    """Response for corpus generation"""
    model_config = ConfigDict(extra="forbid")
    
    message_type: Literal["corpus_generation_response"] = "corpus_generation_response"
    success: bool
    corpus_id: Optional[str] = None
    status: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConfigurationSuggestionRequest(BaseModel):
    """Request for configuration suggestions"""
    message_type: Literal["config_suggestion_request"] = "config_suggestion_request"
    optimization_focus: str  # "performance", "quality", "balanced"
    domain: Optional[str] = None
    workload_type: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConfigurationSuggestionResponse(BaseModel):
    """Response with configuration suggestions"""
    message_type: Literal["config_suggestion_response"] = "config_suggestion_response"
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    preview: Dict[str, Any] = Field(default_factory=dict)
    validation_results: List[str] = Field(default_factory=list)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorpusOperationStatus(BaseModel):
    """Status update for corpus operations"""
    message_type: Literal["corpus_operation_status"] = "corpus_operation_status"
    operation_id: str
    operation_type: str
    status: Literal["pending", "in_progress", "completed", "failed"]
    progress: Optional[float] = Field(None, ge=0, le=100)
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorpusValidationRequest(BaseModel):
    """Request for corpus validation"""
    message_type: Literal["corpus_validation_request"] = "corpus_validation_request"
    corpus_id: str
    validation_types: List[str] = Field(default_factory=list)
    options: Dict[str, Any] = Field(default_factory=dict)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorpusValidationResponse(BaseModel):
    """Response for corpus validation"""
    message_type: Literal["corpus_validation_response"] = "corpus_validation_response"
    corpus_id: str
    valid: bool
    validation_results: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorpusAutoCompleteRequest(BaseModel):
    """Request for auto-completion"""
    message_type: Literal["corpus_autocomplete_request"] = "corpus_autocomplete_request"
    partial_input: str
    category: str  # "workload", "domain", "parameter"
    context: Dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=10, ge=1, le=50)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorpusAutoCompleteResponse(BaseModel):
    """Response with auto-completion suggestions"""
    message_type: Literal["corpus_autocomplete_response"] = "corpus_autocomplete_response"
    suggestions: List[str] = Field(default_factory=list)
    category: str
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorpusErrorMessage(BaseModel):
    """Error message for corpus operations"""
    message_type: Literal["corpus_error"] = "corpus_error"
    error_code: str
    error_message: str
    operation: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    recoverable: bool = True
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorpusStreamUpdate(BaseModel):
    """Streaming update for long-running operations"""
    message_type: Literal["corpus_stream_update"] = "corpus_stream_update"
    operation_id: str
    chunk_index: int
    total_chunks: Optional[int] = None
    data: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorpusConfigPreview(BaseModel):
    """Preview of corpus configuration"""
    message_type: Literal["corpus_config_preview"] = "corpus_config_preview"
    configuration: Dict[str, Any]
    estimated_size: int  # in MB
    estimated_time: int  # in seconds
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorpusBatchRequest(BaseModel):
    """Batch request for multiple corpus operations"""
    message_type: Literal["corpus_batch_request"] = "corpus_batch_request"
    operations: List[Dict[str, Any]]
    execution_mode: Literal["sequential", "parallel"] = "sequential"
    stop_on_error: bool = True
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CorpusBatchResponse(BaseModel):
    """Response for batch corpus operations"""
    message_type: Literal["corpus_batch_response"] = "corpus_batch_response"
    batch_id: str
    total_operations: int
    completed: int
    failed: int
    results: List[Dict[str, Any]] = Field(default_factory=list)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# Message type mapping for deserialization
CORPUS_MESSAGE_TYPES = {
    "corpus_discovery_request": CorpusDiscoveryRequest,
    "corpus_discovery_response": CorpusDiscoveryResponse,
    "corpus_generation_request": CorpusGenerationRequest,
    "corpus_generation_response": CorpusGenerationResponse,
    "config_suggestion_request": ConfigurationSuggestionRequest,
    "config_suggestion_response": ConfigurationSuggestionResponse,
    "corpus_operation_status": CorpusOperationStatus,
    "corpus_validation_request": CorpusValidationRequest,
    "corpus_validation_response": CorpusValidationResponse,
    "corpus_autocomplete_request": CorpusAutoCompleteRequest,
    "corpus_autocomplete_response": CorpusAutoCompleteResponse,
    "corpus_error": CorpusErrorMessage,
    "corpus_stream_update": CorpusStreamUpdate,
    "corpus_config_preview": CorpusConfigPreview,
    "corpus_batch_request": CorpusBatchRequest,
    "corpus_batch_response": CorpusBatchResponse
}


def deserialize_corpus_message(data: Dict[str, Any]) -> BaseModel:
    """Deserialize corpus message based on message type"""
    message_type = data.get("message_type")
    if message_type not in CORPUS_MESSAGE_TYPES:
        raise ValueError(f"Unknown corpus message type: {message_type}")
    return CORPUS_MESSAGE_TYPES[message_type](**data)