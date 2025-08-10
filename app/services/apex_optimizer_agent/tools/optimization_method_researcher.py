from langchain_core.tools import tool
from typing import Any
from app.services.context import ToolContext

@tool
async def optimization_method_researcher(context: ToolContext, function_name: str) -> str:
    """Researches advanced optimization methods for a function."""
    prompt = f'''
    Research and suggest advanced optimization methods for the function '{function_name}'.
    '''
    
    response = await context.llm_connector.get_completion(prompt)
    
    return f"Researched optimization methods for {function_name}."