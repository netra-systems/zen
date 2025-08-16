"""Triage Prompt Building Module

Handles prompt construction and enhancement for triage operations.
Keeps functions under 8 lines and module under 300 lines.
"""

from typing import List, Dict, Any
from app.logging_config import central_logger
from app.agents.prompts import triage_prompt_template

logger = central_logger.get_logger(__name__)


class TriagePromptBuilder:
    """Handles prompt building and enhancement for triage."""
    
    def __init__(self, agent=None):
        """Initialize prompt builder."""
        self.agent = agent
        self.logger = logger
    
    def build_enhanced_prompt(self, user_request: str) -> str:
        """Build enhanced prompt for LLM processing."""
        base_prompt = self._build_base_prompt(user_request)
        analysis_instructions = self._get_analysis_instructions()
        category_options = self._get_category_options()
        
        return f"{base_prompt}\n\n{analysis_instructions}\n\n{category_options}"
    
    def _build_base_prompt(self, user_request: str) -> str:
        """Build base prompt using template."""
        return triage_prompt_template.format(user_request=user_request)
    
    def _get_analysis_instructions(self) -> str:
        """Get analysis instructions for the triage prompt."""
        instructions = self._get_core_analysis_tasks()
        formatted_instructions = self._format_analysis_instructions(instructions)
        return f"Consider the following in your analysis:\n{formatted_instructions}"
    
    def _get_core_analysis_tasks(self) -> List[str]:
        """Get core analysis tasks for triage."""
        return [
            "Extract all mentioned models, metrics, and time ranges",
            "Determine the urgency and complexity of the request",
            "Suggest specific tools that would be helpful",
            "Identify any constraints or requirements mentioned"
        ]
    
    def _format_analysis_instructions(self, instructions: List[str]) -> str:
        """Format analysis instructions as numbered list."""
        return "\n".join([f"{i+1}. {instruction}" for i, instruction in enumerate(instructions)])
    
    def _get_category_options(self) -> str:
        """Get category options for triage classification."""
        categories = self._get_main_categories()
        formatted_categories = self._format_category_list(categories)
        return f"Categorize into one of these main categories:\n{formatted_categories}"
    
    def _get_main_categories(self) -> List[str]:
        """Get list of main triage categories."""
        return [
            "Cost Optimization",
            "Performance Optimization", 
            "Workload Analysis",
            "Configuration & Settings",
            "Monitoring & Reporting",
            "Model Selection",
            "Supply Catalog Management",
            "Quality Optimization"
        ]
    
    def _format_category_list(self, categories: List[str]) -> str:
        """Format categories as bulleted list."""
        return "\n".join([f"- {category}" for category in categories])
    
    def build_admin_prompt(self, user_request: str) -> str:
        """Build prompt specifically for admin mode requests."""
        base_prompt = self._build_base_prompt(user_request)
        admin_instructions = self._get_admin_analysis_instructions()
        admin_categories = self._get_admin_category_options()
        
        return f"{base_prompt}\n\n{admin_instructions}\n\n{admin_categories}"
    
    def _get_admin_analysis_instructions(self) -> str:
        """Get analysis instructions for admin mode."""
        admin_tasks = self._get_admin_analysis_tasks()
        formatted_tasks = self._format_analysis_instructions(admin_tasks)
        return f"Admin mode analysis considerations:\n{formatted_tasks}"
    
    def _get_admin_analysis_tasks(self) -> List[str]:
        """Get admin-specific analysis tasks."""
        return [
            "Identify data generation or management requirements",
            "Determine corpus manipulation needs",
            "Assess administrative privileges required",
            "Evaluate system configuration impacts"
        ]
    
    def _get_admin_category_options(self) -> str:
        """Get admin-specific category options."""
        admin_categories = self._get_admin_categories()
        formatted_categories = self._format_category_list(admin_categories)
        return f"Admin categories available:\n{formatted_categories}"
    
    def _get_admin_categories(self) -> List[str]:
        """Get admin-specific categories."""
        return [
            "Synthetic Data Generation",
            "Corpus Management",
            "System Configuration",
            "Administrative Tools"
        ]
    
    def build_fallback_prompt(self, user_request: str, error_context: str = None) -> str:
        """Build simplified prompt for fallback scenarios."""
        simple_base = self._build_simple_base_prompt(user_request)
        fallback_instructions = self._get_fallback_instructions(error_context)
        basic_categories = self._get_basic_category_options()
        
        return f"{simple_base}\n\n{fallback_instructions}\n\n{basic_categories}"
    
    def _build_simple_base_prompt(self, user_request: str) -> str:
        """Build simplified base prompt for fallback."""
        return f"Analyze and categorize this user request: {user_request}"
    
    def _get_fallback_instructions(self, error_context: str = None) -> str:
        """Get simplified instructions for fallback processing."""
        base_instruction = "Provide a simple categorization with basic analysis."
        context_note = f" Error context: {error_context}" if error_context else ""
        return base_instruction + context_note
    
    def _get_basic_category_options(self) -> str:
        """Get basic category options for fallback."""
        basic_categories = self._get_basic_categories()
        formatted_categories = self._format_category_list(basic_categories)
        return f"Basic categories:\n{formatted_categories}"
    
    def _get_basic_categories(self) -> List[str]:
        """Get basic categories for fallback."""
        return [
            "General Inquiry",
            "Optimization Request",
            "Configuration Help",
            "Analysis Request"
        ]
    
    def add_context_enhancement(self, prompt: str, context: Dict[str, Any]) -> str:
        """Add contextual enhancement to prompt."""
        enhancements = self._build_context_enhancements(context)
        if enhancements:
            return f"{prompt}\n\nAdditional context:\n{enhancements}"
        return prompt
    
    def _build_context_enhancements(self, context: Dict[str, Any]) -> str:
        """Build context enhancement string."""
        enhancements = []
        self._add_user_history_context(context, enhancements)
        self._add_session_context(context, enhancements)
        self._add_system_state_context(context, enhancements)
        return "\n".join(enhancements)
    
    def _add_user_history_context(self, context: Dict[str, Any], enhancements: list) -> None:
        """Add user history context if available."""
        if context.get('user_history'):
            enhancements.append(f"User history: {context['user_history']}")
    
    def _add_session_context(self, context: Dict[str, Any], enhancements: list) -> None:
        """Add session context if available."""
        if context.get('current_session'):
            enhancements.append(f"Session context: {context['current_session']}")
    
    def _add_system_state_context(self, context: Dict[str, Any], enhancements: list) -> None:
        """Add system state context if available."""
        if context.get('system_state'):
            enhancements.append(f"System state: {context['system_state']}")
    
    def build_structured_prompt(self, user_request: str, schema_hint: str = None) -> str:
        """Build prompt with structured output requirements."""
        base_prompt = self.build_enhanced_prompt(user_request)
        structure_requirements = self._get_structure_requirements(schema_hint)
        
        return f"{base_prompt}\n\n{structure_requirements}"
    
    def _get_structure_requirements(self, schema_hint: str = None) -> str:
        """Get structured output requirements."""
        base_requirement = "IMPORTANT: Return response as properly formatted JSON."
        
        if schema_hint:
            return f"{base_requirement} Follow this schema: {schema_hint}"
        
        return base_requirement
    
    def add_validation_instructions(self, prompt: str) -> str:
        """Add validation instructions to prompt."""
        validation_note = self._get_validation_instructions()
        return f"{prompt}\n\n{validation_note}"
    
    def _get_validation_instructions(self) -> str:
        """Get validation instructions."""
        return (
            "Validation requirements:\n"
            "- Ensure confidence score is between 0.0 and 1.0\n"
            "- Category must be from the provided list\n"
            "- All required fields must be present"
        )
    
    def customize_for_domain(self, prompt: str, domain: str) -> str:
        """Customize prompt for specific domain."""
        domain_context = self._get_domain_context(domain)
        if domain_context:
            return f"{prompt}\n\nDomain-specific context:\n{domain_context}"
        return prompt
    
    def _get_domain_context(self, domain: str) -> str:
        """Get domain-specific context."""
        domain_contexts = {
            'cost': 'Focus on cost optimization and budget considerations.',
            'performance': 'Emphasize performance metrics and optimization.',
            'security': 'Consider security implications and compliance.',
            'quality': 'Focus on quality metrics and improvement opportunities.'
        }
        
        return domain_contexts.get(domain.lower(), '')
    
    def build_multi_turn_prompt(self, user_request: str, conversation_history: List[Dict]) -> str:
        """Build prompt considering conversation history."""
        base_prompt = self.build_enhanced_prompt(user_request)
        history_context = self._format_conversation_history(conversation_history)
        
        if history_context:
            return f"{base_prompt}\n\nConversation history:\n{history_context}"
        
        return base_prompt
    
    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Format conversation history for prompt."""
        if not history:
            return ""
        formatted_entries = self._format_recent_entries(history)
        return "\n".join(formatted_entries)
    
    def _format_recent_entries(self, history: List[Dict]) -> List[str]:
        """Format recent conversation entries."""
        formatted_entries = []
        for entry in history[-3:]:  # Last 3 entries
            role = entry.get('role', 'unknown')
            content = self._truncate_content(entry.get('content', ''))
            formatted_entries.append(f"{role}: {content}")
        return formatted_entries
    
    def _truncate_content(self, content: str) -> str:
        """Truncate content if too long."""
        return content[:100] + '...' if len(content) > 100 else content