"""
MCP Prompt Manager

Manages prompt templates for common operations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from pydantic import BaseModel, Field
from app.logging_config import CentralLogger
from app.core.exceptions import NetraException

logger = CentralLogger()


class Prompt(BaseModel):
    """Represents an MCP prompt template"""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = Field(default_factory=list)
    messages: List[Dict[str, str]] = Field(default_factory=list)
    category: Optional[str] = None
    version: str = "1.0.0"


class PromptManager:
    """
    Manager for MCP prompt templates
    
    Provides pre-configured prompts for common Netra operations.
    """
    
    def __init__(self):
        self.prompts: Dict[str, Prompt] = {}
        self._initialize_builtin_prompts()
        
    def _initialize_builtin_prompts(self):
        """Initialize built-in Netra prompts"""
        # Optimization prompts
        self.register_prompt(Prompt(
            name="optimize_workload",
            description="Analyze and optimize an AI workload",
            arguments=[
                {"name": "workload_description", "type": "string", "description": "Description of the workload"},
                {"name": "target_metric", "type": "string", "description": "Primary optimization target"}
            ],
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI workload optimization expert. Analyze the given workload and provide specific, actionable optimization recommendations."
                },
                {
                    "role": "user",
                    "content": "Analyze this workload: {{workload_description}}. Focus on optimizing for {{target_metric}}."
                }
            ],
            category="optimization"
        ))
        
        self.register_prompt(Prompt(
            name="cost_analysis",
            description="Perform cost analysis on AI operations",
            arguments=[
                {"name": "usage_data", "type": "object", "description": "Usage statistics"},
                {"name": "budget", "type": "number", "description": "Monthly budget"}
            ],
            messages=[
                {
                    "role": "system",
                    "content": "You are a cost optimization specialist for AI workloads. Analyze usage patterns and provide cost reduction strategies."
                },
                {
                    "role": "user",
                    "content": "Analyze this usage data: {{usage_data}}. Monthly budget is ${{budget}}. Provide cost optimization recommendations."
                }
            ],
            category="optimization"
        ))
        
        # Analysis prompts
        self.register_prompt(Prompt(
            name="performance_analysis",
            description="Analyze system performance metrics",
            arguments=[
                {"name": "metrics", "type": "object", "description": "Performance metrics"},
                {"name": "timeframe", "type": "string", "description": "Analysis timeframe"}
            ],
            messages=[
                {
                    "role": "system",
                    "content": "You are a performance analysis expert. Identify bottlenecks and provide improvement recommendations."
                },
                {
                    "role": "user",
                    "content": "Analyze these performance metrics from {{timeframe}}: {{metrics}}"
                }
            ],
            category="analysis"
        ))
        
        self.register_prompt(Prompt(
            name="error_diagnosis",
            description="Diagnose and troubleshoot errors",
            arguments=[
                {"name": "error_logs", "type": "array", "description": "Error log entries"},
                {"name": "context", "type": "string", "description": "Error context"}
            ],
            messages=[
                {
                    "role": "system",
                    "content": "You are a system debugging expert. Analyze error patterns and provide solutions."
                },
                {
                    "role": "user",
                    "content": "Diagnose these errors in context of {{context}}: {{error_logs}}"
                }
            ],
            category="troubleshooting"
        ))
        
        # Generation prompts
        self.register_prompt(Prompt(
            name="generate_test_data",
            description="Generate synthetic test data",
            arguments=[
                {"name": "schema", "type": "object", "description": "Data schema"},
                {"name": "requirements", "type": "string", "description": "Specific requirements"}
            ],
            messages=[
                {
                    "role": "system",
                    "content": "You are a test data generation expert. Create realistic synthetic data that meets specifications."
                },
                {
                    "role": "user",
                    "content": "Generate test data matching this schema: {{schema}}. Requirements: {{requirements}}"
                }
            ],
            category="generation"
        ))
        
        self.register_prompt(Prompt(
            name="create_optimization_plan",
            description="Create a comprehensive optimization plan",
            arguments=[
                {"name": "current_state", "type": "object", "description": "Current system state"},
                {"name": "goals", "type": "array", "description": "Optimization goals"}
            ],
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI systems architect. Create detailed optimization plans with clear steps and expected outcomes."
                },
                {
                    "role": "user",
                    "content": "Create an optimization plan. Current state: {{current_state}}. Goals: {{goals}}"
                }
            ],
            category="planning"
        ))
        
        # Reporting prompts
        self.register_prompt(Prompt(
            name="summarize_results",
            description="Summarize optimization results",
            arguments=[
                {"name": "results", "type": "object", "description": "Optimization results"},
                {"name": "audience", "type": "string", "description": "Target audience"}
            ],
            messages=[
                {
                    "role": "system",
                    "content": "You are a technical writer specializing in AI optimization reports. Create clear, actionable summaries."
                },
                {
                    "role": "user",
                    "content": "Summarize these optimization results for {{audience}}: {{results}}"
                }
            ],
            category="reporting"
        ))
        
    def register_prompt(self, prompt: Prompt):
        """Register a new prompt template"""
        if prompt.name in self.prompts:
            logger.warning(f"Overwriting existing prompt: {prompt.name}")
        self.prompts[prompt.name] = prompt
        logger.info(f"Registered prompt: {prompt.name}")
        
    def unregister_prompt(self, prompt_name: str):
        """Unregister a prompt template"""
        if prompt_name in self.prompts:
            del self.prompts[prompt_name]
            logger.info(f"Unregistered prompt: {prompt_name}")
            
    async def list_prompts(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available prompts for a session"""
        prompts_list = []
        for prompt in self.prompts.values():
            prompt_dict = {
                "name": prompt.name,
                "description": prompt.description
            }
            if prompt.arguments:
                prompt_dict["arguments"] = [
                    {
                        "name": arg["name"],
                        "description": arg.get("description", ""),
                        "required": arg.get("required", False)
                    }
                    for arg in prompt.arguments
                ]
            if prompt.category:
                prompt_dict["category"] = prompt.category
            prompts_list.append(prompt_dict)
        return prompts_list
        
    async def get_prompt(self, name: str, arguments: Dict[str, Any], session_id: Optional[str] = None) -> List[Dict[str, str]]:
        """Get a prompt template with arguments filled in"""
        if name not in self.prompts:
            raise NetraException(f"Prompt not found: {name}")
            
        prompt = self.prompts[name]
        
        # Validate required arguments
        for arg in prompt.arguments:
            if arg.get("required", False) and arg["name"] not in arguments:
                raise NetraException(f"Missing required argument: {arg['name']}")
                
        # Fill in template variables
        messages = []
        for message in prompt.messages:
            content = message["content"]
            
            # Simple template replacement (could be enhanced with Jinja2)
            for arg_name, arg_value in arguments.items():
                placeholder = f"{{{{{arg_name}}}}}"
                if isinstance(arg_value, (dict, list)):
                    arg_value = json.dumps(arg_value, indent=2)
                content = content.replace(placeholder, str(arg_value))
                
            messages.append({
                "role": message["role"],
                "content": content
            })
            
        return messages
        
    async def shutdown(self):
        """Clean up resources"""
        self.prompts.clear()