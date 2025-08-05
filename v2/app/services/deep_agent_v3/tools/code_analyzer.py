
from typing import Any, Dict
from app.services.deep_agent_v3.utils.llm_provider import LLMProvider

class CodeAnalyzer:
    def __init__(self, llm_connector: Any):
        self.llm = LLMProvider(llm_connector)

    async def analyze_function(self, file_path: str, function_name: str) -> Dict[str, Any]:
        """
        Analyzes a specific function within a file and suggests improvements.
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            return {"error": f"File not found: {file_path}"}

        prompt = f"""
        Analyze the function `{function_name}` in the following code and suggest improvements.
        Focus on performance, readability, and best practices.
        Provide a summary of the function's purpose and a list of suggested improvements.

        Code:
        ```python
        {content}
        ```
        """

        response = await self.llm.generate_text(prompt)
        return {"analysis": response}
