"""
Enums for Synthetic Data Service
"""

from enum import Enum


class WorkloadCategory(Enum):
    """Categories of workload patterns"""
    SIMPLE_CHAT = "simple_chat"
    RAG_PIPELINE = "rag_pipeline"
    TOOL_USE = "tool_use"
    MULTI_TURN_TOOL_USE = "multi_turn_tool_use"
    FAILED_REQUEST = "failed_request"
    CUSTOM_DOMAIN = "custom_domain"


class GenerationJobStatus(Enum):
    """Status of a generation job - renamed to avoid conflict with GenerationStatus model"""
    INITIATED = "initiated"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# Backward compatibility alias - will be removed after import updates
GenerationStatus = GenerationJobStatus