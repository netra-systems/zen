"""Agent route validation functions."""
from typing import Any, Dict

from fastapi import HTTPException


def validate_agent_state(state, run_id: str) -> None:
    """Validate agent state exists and is valid."""
    if not state or state.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Agent run not found")


def validate_agent_state_exists(state, run_id: str) -> None:
    """Validate agent state exists."""
    if not state:
        raise HTTPException(status_code=404, detail="Agent state not found")


def build_agent_status_response(run_id: str, state: Dict) -> Dict[str, Any]:
    """Build agent status response."""
    return {
        "run_id": run_id,
        "status": state.get("status", "unknown"),
        "current_step": state.get("current_step", 0),
        "total_steps": state.get("total_steps", 0),
    }


def build_agent_state_response(run_id: str, state) -> Dict[str, Any]:
    """Build agent state response."""
    return {
        "run_id": run_id,
        "state": state.model_dump()
    }


def build_thread_runs_response(thread_id: str, runs) -> Dict[str, Any]:
    """Build thread runs response."""
    return {
        "thread_id": thread_id,
        "runs": runs
    }


def handle_run_agent_error(e: Exception):
    """Handle run agent execution errors."""
    raise HTTPException(status_code=500, detail=str(e))


async def handle_agent_message_error(e: Exception):
    """Handle agent message processing errors."""
    raise HTTPException(status_code=500, detail=str(e))