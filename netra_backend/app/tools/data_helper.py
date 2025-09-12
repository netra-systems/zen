"""Data Helper Tool Module

This tool generates prompts to request additional data from users when insufficient 
data is available for optimization.

Business Value: Ensures comprehensive data collection for accurate AI optimization strategies.
"""

from typing import Any, Dict, List, Optional

from netra_backend.app.agents.prompts.supervisor_prompts import data_helper_prompt_template
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DataHelper:
    """Data Helper tool for requesting additional data from users.
    
    This tool analyzes the user request, triage results, and previous agent outputs
    to generate comprehensive data requests that enable optimization strategies.
    """
    
    def __init__(self, llm_manager: LLMManager):
        """Initialize the Data Helper tool.
        
        Args:
            llm_manager: LLM manager for generating data requests
        """
        self.llm_manager = llm_manager
        self.prompt_template = data_helper_prompt_template
    
    async def generate_data_request(
        self, 
        user_request: str,
        triage_result: Dict[str, Any],
        previous_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate a comprehensive data request based on the context.
        
        Args:
            user_request: The original user request
            triage_result: Results from the triage agent
            previous_results: Results from previous agents if available
            
        Returns:
            Dictionary containing the data request details
        """
        try:
            # Format previous results for context
            formatted_previous_results = self._format_previous_results(previous_results)
            
            # Create the prompt
            prompt = self.prompt_template.format(
                user_request=user_request,
                triage_result=str(triage_result),
                previous_results=formatted_previous_results
            )
            
            # Generate the data request using LLM
            response = await self.llm_manager.agenerate(
                prompts=[prompt],
                temperature=0.3,  # Lower temperature for more consistent outputs
                max_tokens=2000
            )
            
            # Extract and structure the response
            data_request = self._parse_data_request(response)
            
            logger.info(f"Generated data request for user query: {user_request[:100]}...")
            
            return {
                "success": True,
                "data_request": data_request,
                "user_request": user_request,
                "triage_context": triage_result
            }
            
        except Exception as e:
            logger.error(f"Error generating data request: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "fallback_message": self._get_fallback_message(user_request)
            }
    
    def _format_previous_results(self, previous_results: Optional[List[Dict[str, Any]]]) -> str:
        """Format previous agent results for context.
        
        Args:
            previous_results: List of results from previous agents
            
        Returns:
            Formatted string of previous results
        """
        if not previous_results:
            return "No previous agent results available."
        
        formatted = []
        for i, result in enumerate(previous_results, 1):
            agent_name = result.get("agent_name", f"Agent {i}")
            summary = result.get("summary", result.get("result", "No summary available"))
            formatted.append(f"{agent_name}: {summary}")
        
        return "\n".join(formatted)
    
    def _parse_data_request(self, llm_response) -> Dict[str, Any]:
        """Parse the LLM response into structured data request.
        
        Args:
            llm_response: Raw response from LLM
            
        Returns:
            Structured data request dictionary
        """
        # Extract the text from the LLM response
        if hasattr(llm_response, 'generations') and llm_response.generations:
            text = llm_response.generations[0][0].text
        else:
            text = str(llm_response)
        
        # Parse the response into categories and items
        categories = self._extract_categories(text)
        instructions = self._extract_instructions(text)
        
        return {
            "raw_response": text,
            "data_categories": categories,
            "user_instructions": instructions,
            "structured_items": self._structure_data_items(categories)
        }
    
    def _extract_categories(self, text: str) -> List[Dict[str, Any]]:
        """Extract data categories from the response text.
        
        Args:
            text: Response text from LLM
            
        Returns:
            List of data categories with items
        """
        categories = []
        current_category = None
        current_items = []
        
        lines = text.split('\n')
        for line in lines:
            # Check for category headers (usually marked with brackets or bold)
            if line.strip().startswith('[') or line.strip().startswith('**'):
                if current_category and current_items:
                    categories.append({
                        "name": current_category,
                        "items": current_items
                    })
                current_category = line.strip().replace('[', '').replace(']', '').replace('**', '').replace(':', '')
                current_items = []
            elif line.strip().startswith('- ') or line.strip().startswith('[U+2022] '):
                # Extract data item
                item_text = line.strip()[2:]
                justification = ""
                
                # Look for justification on next line or after colon
                if 'Justification:' in item_text:
                    parts = item_text.split('Justification:')
                    item_text = parts[0].strip()
                    justification = parts[1].strip() if len(parts) > 1 else ""
                
                current_items.append({
                    "item": item_text,
                    "justification": justification
                })
        
        # Add the last category
        if current_category and current_items:
            categories.append({
                "name": current_category,
                "items": current_items
            })
        
        return categories
    
    def _extract_instructions(self, text: str) -> str:
        """Extract user instructions from the response.
        
        Args:
            text: Response text from LLM
            
        Returns:
            User instructions string
        """
        # Look for instructions section
        instructions_markers = [
            "Data Collection Instructions",
            "Please provide the following",
            "To proceed with optimization"
        ]
        
        for marker in instructions_markers:
            if marker in text:
                parts = text.split(marker)
                if len(parts) > 1:
                    return marker + parts[1].strip()
        
        return "Please provide the requested data to enable comprehensive optimization analysis."
    
    def _structure_data_items(self, categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Structure data items for easy processing.
        
        Args:
            categories: List of data categories
            
        Returns:
            Flat list of structured data items
        """
        structured_items = []
        
        for category in categories:
            for item in category.get("items", []):
                structured_items.append({
                    "category": category.get("name", "General"),
                    "data_point": item.get("item", ""),
                    "justification": item.get("justification", ""),
                    "required": True  # Can be enhanced with priority logic
                })
        
        return structured_items
    
    def _get_fallback_message(self, user_request: str) -> str:
        """Generate a fallback message if data request generation fails.
        
        Args:
            user_request: The original user request
            
        Returns:
            Fallback message string
        """
        return f"""To provide optimization recommendations for your request: "{user_request[:200]}...", 
        we need additional information about your current setup, usage patterns, and requirements. 
        Please provide:
        
        1. Current system metrics and usage data
        2. Performance requirements and constraints
        3. Budget and resource limitations
        4. Technical specifications and integration details
        
        This information will help us generate targeted optimization strategies."""


# Factory function for creating DataHelper instances
def create_data_helper(llm_manager: LLMManager) -> DataHelper:
    """Create a DataHelper instance.
    
    Args:
        llm_manager: LLM manager for the tool
        
    Returns:
        DataHelper instance
    """
    return DataHelper(llm_manager)