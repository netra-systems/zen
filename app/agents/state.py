# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:48:05.517910+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to agent support files
# Git: v6 | 2c55fb99 | dirty (32 uncommitted)
# Change: Feature | Scope: Component | Risk: Medium
# Session: 3338d1f9-246a-461a-8cae-a81a10615db4 | Seq: 2
# Review: Pending | Score: 85
# ================================
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DeepAgentState(BaseModel):
    user_request: str
    chat_thread_id: Optional[str] = None
    user_id: Optional[str] = None
    triage_result: Optional[Dict[str, Any]] = None
    data_result: Optional[Dict[str, Any]] = None
    optimizations_result: Optional[Dict[str, Any]] = None
    action_plan_result: Optional[Dict[str, Any]] = None
    report_result: Optional[Dict[str, Any]] = None
    synthetic_data_result: Optional[Dict[str, Any]] = None
    supply_research_result: Optional[Dict[str, Any]] = None
    final_report: Optional[str] = None
    step_count: int = 0  # Added for agent tracking
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return self.model_dump(exclude_none=True)