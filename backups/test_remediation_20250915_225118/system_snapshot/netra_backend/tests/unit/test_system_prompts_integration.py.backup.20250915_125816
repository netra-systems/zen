"""Unit tests for system prompts integration.

Tests that system prompts are properly integrated into agent prompt templates.
Business Value: Ensures consistent agent behavior through system prompts.
"""

import pytest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.prompts import (
    actions_system_prompt,
    actions_to_meet_goals_prompt_template,
    data_helper_prompt_template,
    data_helper_system_prompt,
    data_prompt_template,
    data_system_prompt,
    optimization_system_prompt,
    optimizations_core_prompt_template,
    reporting_prompt_template,
    reporting_system_prompt,
    supervisor_orchestration_prompt,
    supervisor_system_prompt,
    triage_prompt_template,
    triage_system_prompt,
)


class TestSystemPromptsIntegration:
    """Test suite for system prompts integration into agent templates."""
    
    def test_all_system_prompts_exist(self):
        """Test that all system prompts are defined."""
        system_prompts = [
            ("supervisor", supervisor_system_prompt),
            ("triage", triage_system_prompt),
            ("data", data_system_prompt),
            ("optimization", optimization_system_prompt),
            ("actions", actions_system_prompt),
            ("reporting", reporting_system_prompt),
            ("data_helper", data_helper_system_prompt),
        ]
        
        for name, prompt in system_prompts:
            assert prompt is not None, f"{name} system prompt is None"
            assert isinstance(prompt, str), f"{name} system prompt is not a string"
            assert len(prompt) > 100, f"{name} system prompt is too short"
            assert "You are the" in prompt, f"{name} system prompt missing identity"
    
    def test_system_prompts_have_required_sections(self):
        """Test that system prompts have required sections."""
        system_prompts = [
            ("triage", triage_system_prompt),
            ("data", data_system_prompt),
            ("optimization", optimization_system_prompt),
            ("actions", actions_system_prompt),
            ("reporting", reporting_system_prompt),
            ("data_helper", data_helper_system_prompt),
        ]
        
        for name, prompt in system_prompts:
            # Check for key sections
            assert "Core Identity:" in prompt or "identity" in prompt.lower(), \
                f"{name} missing Core Identity section"
            assert "Key Capabilities:" in prompt or "capabilities" in prompt.lower(), \
                f"{name} missing Key Capabilities section"
            assert "Critical Responsibilit" in prompt or "responsibilit" in prompt.lower(), \
                f"{name} missing Critical Responsibilities section"
    
    def test_prompt_templates_include_system_context(self):
        """Test that prompt templates include system context."""
        templates = [
            ("triage", triage_prompt_template),
            ("data", data_prompt_template),
            ("optimization", optimizations_core_prompt_template),
            ("actions", actions_to_meet_goals_prompt_template),
            ("reporting", reporting_prompt_template),
            ("data_helper", data_helper_prompt_template),
            ("supervisor_orchestration", supervisor_orchestration_prompt),
        ]
        
        for name, template in templates:
            assert hasattr(template, 'template'), f"{name} template missing template attribute"
            template_str = template.template
            
            # Check for system context or any system prompt inclusion
            # Each template should include either "System Context" header or the appropriate system prompt
            has_context = ("System Context" in template_str or 
                          "You are the" in template_str)  # All system prompts start with "You are the"
            assert has_context, f"{name} template missing system context"
    
    def test_prompt_templates_have_correct_input_variables(self):
        """Test that prompt templates have correct input variables."""
        template_vars = [
            ("triage", triage_prompt_template, ["user_request"]),
            ("data", data_prompt_template, ["triage_result", "user_request", "thread_id"]),
            ("optimization", optimizations_core_prompt_template, ["data", "triage_result", "user_request"]),
            ("actions", actions_to_meet_goals_prompt_template, ["optimizations", "data", "user_request"]),
            ("reporting", reporting_prompt_template, ["action_plan", "optimizations", "data", "triage_result", "user_request"]),
            ("data_helper", data_helper_prompt_template, ["user_request", "triage_result", "previous_results"]),
            ("supervisor_orchestration", supervisor_orchestration_prompt, ["user_request", "triage_result"]),
        ]
        
        for name, template, expected_vars in template_vars:
            assert hasattr(template, 'input_variables'), f"{name} template missing input_variables"
            actual_vars = set(template.input_variables)
            expected_set = set(expected_vars)
            assert actual_vars == expected_set, \
                f"{name} template variables mismatch. Expected: {expected_set}, Got: {actual_vars}"
    
    def test_system_prompts_in_template_content(self):
        """Test that system prompts are actually in the template content."""
        # Check specific system prompts are embedded in their templates
        assert triage_system_prompt in triage_prompt_template.template, \
            "Triage system prompt not found in triage template"
        
        assert data_system_prompt in data_prompt_template.template, \
            "Data system prompt not found in data template"
        
        assert optimization_system_prompt in optimizations_core_prompt_template.template, \
            "Optimization system prompt not found in optimization template"
        
        assert actions_system_prompt in actions_to_meet_goals_prompt_template.template, \
            "Actions system prompt not found in actions template"
        
        assert reporting_system_prompt in reporting_prompt_template.template, \
            "Reporting system prompt not found in reporting template"
        
        assert data_helper_system_prompt in data_helper_prompt_template.template, \
            "Data helper system prompt not found in data helper template"
        
        assert supervisor_system_prompt in supervisor_orchestration_prompt.template, \
            "Supervisor system prompt not found in orchestration template"
    
    def test_triage_template_includes_data_sufficiency(self):
        """Test that triage template includes data sufficiency assessment."""
        template_str = triage_prompt_template.template
        
        # Check for data sufficiency in output
        assert "data_sufficiency" in template_str, \
            "Triage template missing data_sufficiency in output"
        
        # Check for sufficiency levels
        assert "sufficient" in template_str, "Missing 'sufficient' level"
        assert "partial" in template_str, "Missing 'partial' level"
        assert "insufficient" in template_str, "Missing 'insufficient' level"
    
    def test_supervisor_orchestration_prompt(self):
        """Test supervisor orchestration prompt structure."""
        template_str = supervisor_orchestration_prompt.template
        
        # Check for orchestration logic
        assert "Orchestration Logic" in template_str, \
            "Missing orchestration logic section"
        
        # Check for workflow steps
        assert "TriageSubAgent" in template_str, "Missing triage agent reference"
        assert "data_helper" in template_str, "Missing data_helper reference"
        
        # Check for output format
        assert "Workflow steps" in template_str or "workflow steps" in template_str, "Missing workflow_steps in output"
        assert "State management" in template_str or "state management" in template_str, "Missing state_management in output"
    
    def test_data_helper_prompt_structure(self):
        """Test data helper prompt has correct structure."""
        template_str = data_helper_prompt_template.template
        
        # Check for key sections
        assert "Required Data Sources" in template_str, \
            "Missing Required Data Sources section"
        
        assert "Data Collection Instructions" in template_str, \
            "Missing Data Collection Instructions section"
        
        # Check it references user request and triage result
        assert "{user_request}" in template_str, "Missing user_request placeholder"
        assert "{triage_result}" in template_str, "Missing triage_result placeholder"
        assert "{previous_results}" in template_str, "Missing previous_results placeholder"


class TestSystemPromptContent:
    """Test the content and quality of system prompts."""
    
    def test_supervisor_system_prompt_content(self):
        """Test supervisor system prompt has required content."""
        prompt = supervisor_system_prompt
        
        # Check for key responsibilities
        assert "orchestrator" in prompt.lower(), "Missing orchestrator role"
        assert "Sequential Workflow Orchestration" in prompt, "Missing workflow orchestration"
        assert "Context Sharing" in prompt, "Missing context sharing"
        assert "Quality Assurance" in prompt, "Missing quality assurance"
        assert "Exception Handling" in prompt, "Missing exception handling"
        
        # Check for tool categories
        assert "Synthetic Data Generation" in prompt, "Missing synthetic data tools"
        assert "Corpus Management" in prompt, "Missing corpus management tools"
        assert "data_helper" in prompt, "Missing data_helper tool"
    
    def test_agent_role_clarity(self):
        """Test that each agent has clear role definition."""
        prompts = [
            ("Triage Agent", triage_system_prompt),
            ("Data Agent", data_system_prompt),
            ("Optimization Agent", optimization_system_prompt),
            ("Actions Agent", actions_system_prompt),
            ("Reporting Agent", reporting_system_prompt),
            ("Data Helper Agent", data_helper_system_prompt),
        ]
        
        for name, prompt in prompts:
            assert f"You are the {name}" in prompt, \
                f"System prompt doesn't clearly state '{name}' identity"