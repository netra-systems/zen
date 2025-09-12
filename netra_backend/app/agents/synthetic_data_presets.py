# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: CLAUDE.md compliance - Split synthetic data agent into modules  <= 300 lines
# Git: anthony-aug-13-2 | modified
# Change: Refactor | Scope: Component | Risk: Low
# Session: claude-md-compliance | Seq: 1
# Review: Pending | Score: 90
# ================================
"""
Synthetic Data Preset Configurations

This module contains pre-configured workload profiles for common use cases.
Each preset defines realistic parameters for synthetic data generation.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from pydantic import BaseModel, Field


class DataGenerationType(str, Enum):
    """Types of synthetic data generation"""
    INFERENCE_LOGS = "inference_logs"
    TRAINING_DATA = "training_data"
    PERFORMANCE_METRICS = "performance_metrics"
    COST_DATA = "cost_data"
    CUSTOM = "custom"

# Alias for backward compatibility
WorkloadType = DataGenerationType

class WorkloadProfile(BaseModel):
    """Profile for synthetic workload generation"""
    workload_type: DataGenerationType
    volume: int = Field(ge=100, le=1000000, default=1000)
    time_range_days: int = Field(ge=1, le=365, default=30)
    distribution: str = Field(default="normal")  # normal, uniform, exponential
    noise_level: float = Field(ge=0.0, le=0.5, default=0.1)
    custom_parameters: Dict[str, Any] = Field(default_factory=dict)

def get_ecommerce_preset() -> WorkloadProfile:
    """Get e-commerce workload preset"""
    return WorkloadProfile(
        workload_type=DataGenerationType.INFERENCE_LOGS,
        volume=10000,
        time_range_days=30,
        distribution="exponential",
        noise_level=0.15,
        custom_parameters=_get_ecommerce_params()
    )

def _get_ecommerce_params() -> Dict[str, any]:
    """Get e-commerce specific parameters"""
    return {
        "peak_hours": [10, 14, 19, 20],
        "models": [LLMModel.GEMINI_2_5_FLASH.value, "claude-2", "embedding-ada-002"],
        "use_cases": ["product_recommendations", "search", "chat_support"],
        "avg_tokens_per_request": 500,
        "peak_multiplier": 3.5
    }

def get_financial_preset() -> WorkloadProfile:
    """Get financial services workload preset"""
    return WorkloadProfile(
        workload_type=DataGenerationType.INFERENCE_LOGS,
        volume=50000,
        time_range_days=90,
        distribution="normal",
        noise_level=0.05,
        custom_parameters=_get_financial_params()
    )

def _get_financial_params() -> Dict[str, any]:
    """Get financial services specific parameters"""
    return {
        "models": [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value],
        "use_cases": ["risk_analysis", "fraud_detection", "compliance"],
        "avg_tokens_per_request": 1500,
        "compliance_requirements": True,
        "data_sensitivity": "high"
    }

def get_healthcare_preset() -> WorkloadProfile:
    """Get healthcare workload preset"""
    return WorkloadProfile(
        workload_type=DataGenerationType.INFERENCE_LOGS,
        volume=25000,
        time_range_days=60,
        distribution="uniform",
        noise_level=0.08,
        custom_parameters=_get_healthcare_params()
    )

def _get_healthcare_params() -> Dict[str, any]:
    """Get healthcare specific parameters"""
    return {
        "models": ["med-palm-2", LLMModel.GEMINI_2_5_FLASH.value, "bio-gpt"],
        "use_cases": ["diagnosis_assist", "medical_qa", "report_generation"],
        "avg_tokens_per_request": 2000,
        "hipaa_compliant": True,
        "requires_audit_trail": True
    }

def get_gaming_preset() -> WorkloadProfile:
    """Get gaming workload preset"""
    return WorkloadProfile(
        workload_type=DataGenerationType.PERFORMANCE_METRICS,
        volume=100000,
        time_range_days=7,
        distribution="exponential",
        noise_level=0.25,
        custom_parameters=_get_gaming_params()
    )

def _get_gaming_params() -> Dict[str, any]:
    """Get gaming specific parameters"""
    return {
        "models": [LLMModel.GEMINI_2_5_FLASH.value, "llama-2-7b"],
        "use_cases": ["npc_dialogue", "story_generation", "player_assistance"],
        "avg_tokens_per_request": 200,
        "peak_hours": [19, 20, 21, 22, 23],
        "weekend_multiplier": 2.0
    }

def get_research_preset() -> WorkloadProfile:
    """Get research workload preset"""
    return WorkloadProfile(
        workload_type=DataGenerationType.TRAINING_DATA,
        volume=5000,
        time_range_days=180,
        distribution="normal",
        noise_level=0.02,
        custom_parameters=_get_research_params()
    )

def _get_research_params() -> Dict[str, any]:
    """Get research specific parameters"""
    return {
        "models": [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, "palm-2"],
        "use_cases": ["paper_analysis", "hypothesis_generation", "data_synthesis"],
        "avg_tokens_per_request": 5000,
        "batch_processing": True,
        "quality_over_speed": True
    }

def get_all_presets() -> Dict[str, WorkloadProfile]:
    """Get all available workload presets"""
    return {
        "ecommerce": get_ecommerce_preset(),
        "financial": get_financial_preset(),
        "healthcare": get_healthcare_preset(),
        "gaming": get_gaming_preset(),
        "research": get_research_preset()
    }

def find_preset_by_name(name: str) -> WorkloadProfile:
    """Find preset by name (case-insensitive)"""
    presets = get_all_presets()
    preset = presets.get(name.lower())
    if not preset:
        raise ValueError(f"Unknown preset: {name}")
    return preset

def is_valid_preset_name(name: str) -> bool:
    """Check if preset name is valid"""
    presets = get_all_presets()
    return name.lower() in presets

def get_preset_names() -> list[str]:
    """Get list of all preset names"""
    return list(get_all_presets().keys())
