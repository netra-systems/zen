"""Agent Prompts Module

This module contains all prompt templates for various agents in the Netra platform.
The prompts are organized into focused modules for better maintainability.
"""

from netra_backend.app.agents.prompts.action_prompts import (
    actions_to_meet_goals_prompt_template,
)
from netra_backend.app.agents.prompts.data_prompts import data_prompt_template
from netra_backend.app.agents.prompts.optimization_prompts import (
    optimizations_core_prompt_template,
)
from netra_backend.app.agents.prompts.reporting_prompts import reporting_prompt_template
from netra_backend.app.agents.prompts.triage_prompts import triage_prompt_template

__all__ = [
    "triage_prompt_template",
    "data_prompt_template", 
    "optimizations_core_prompt_template",
    "actions_to_meet_goals_prompt_template",
    "reporting_prompt_template"
]