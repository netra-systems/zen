# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:48:05.518963+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to agent support files
# Git: v6 | 2c55fb99 | dirty (32 uncommitted)
# Change: Feature | Scope: Component | Risk: Medium
# Session: 3338d1f9-246a-461a-8cae-a81a10615db4 | Seq: 4
# Review: Pending | Score: 85
# ================================

"""Agent Prompts

Backward compatibility module that imports from the new modular structure.
This module contains all prompt templates for various agents in the Netra platform.
"""

# Import all prompts from the modular structure for backward compatibility
from netra_backend.app.prompts import (
    triage_prompt_template,
    data_prompt_template,
    optimizations_core_prompt_template,
    actions_to_meet_goals_prompt_template,
    reporting_prompt_template
)

# Export all prompts for backward compatibility
__all__ = [
    "triage_prompt_template",
    "data_prompt_template",
    "optimizations_core_prompt_template", 
    "actions_to_meet_goals_prompt_template",
    "reporting_prompt_template"
]