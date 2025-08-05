from langchain_core.tools import tool
from typing import Any, Dict

@tool
async def code_analyzer(request: Dict[str, Any], code_analyzer: any) -> str:
    """
    Analyzes the code of a specific function.
    """
    file_path = request.get("file_path")
    function_name = request.get("function_name")

    if not file_path or not function_name:
        return "Error: file_path and function_name are required."

    analysis = await code_analyzer.analyze_function(file_path, function_name)
    return f"Function {function_name} in {file_path} analyzed."
