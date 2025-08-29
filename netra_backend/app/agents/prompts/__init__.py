"""Agent Prompts Module

This module contains all prompt templates for various agents in the Netra platform.
The prompts are organized into focused modules for better maintainability.
"""

from netra_backend.app.agents.prompts.action_prompts import (
    actions_system_prompt,
    actions_to_meet_goals_prompt_template,
)
from netra_backend.app.agents.prompts.data_prompts import (
    data_prompt_template,
    data_system_prompt,
)
from netra_backend.app.agents.prompts.optimization_prompts import (
    optimization_system_prompt,
    optimizations_core_prompt_template,
)
from netra_backend.app.agents.prompts.reporting_prompts import (
    reporting_prompt_template,
    reporting_system_prompt,
)
from netra_backend.app.agents.prompts.supervisor_prompts import (
    data_helper_prompt_template,
    data_helper_system_prompt,
    supervisor_orchestration_prompt,
    supervisor_system_prompt,
)
from netra_backend.app.agents.prompts.triage_prompts import (
    triage_prompt_template,
    triage_system_prompt,
)

__all__ = [
    # Prompt templates
    "triage_prompt_template",
    "data_prompt_template", 
    "optimizations_core_prompt_template",
    "actions_to_meet_goals_prompt_template",
    "reporting_prompt_template",
    "data_helper_prompt_template",
    "supervisor_orchestration_prompt",
    # System prompts
    "supervisor_system_prompt",
    "triage_system_prompt",
    "data_system_prompt",
    "optimization_system_prompt",
    "actions_system_prompt",
    "reporting_system_prompt",
    "data_helper_system_prompt",
]