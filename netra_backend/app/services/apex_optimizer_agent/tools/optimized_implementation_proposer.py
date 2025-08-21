from langchain_core.tools import tool
from typing import Any
from netra_backend.app.services.context import ToolContext

@tool
async def optimized_implementation_proposer(context: ToolContext, function_name: str) -> str:
    """Proposes an optimized implementation for a function."""
    prompt = f"""
    Given the function '{function_name}', propose an optimized implementation.
    Provide the optimized code and an explanation of the changes.
    """
    
    response = await context.llm_connector.get_completion(prompt)
    
    return f"Proposed optimized implementation for {function_name}."