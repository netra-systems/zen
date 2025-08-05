from typing import Any, Dict

class CodeAnalyzer:
    def __init__(self, code_analyzer: any):
        self.code_analyzer = code_analyzer

    async def run(self, request: Dict[str, Any]) -> str:
        """
        Analyzes the code of a specific function.
        """
        file_path = request.get("file_path")
        function_name = request.get("function_name")

        if not file_path or not function_name:
            return "Error: file_path and function_name are required."

        analysis = await self.code_analyzer.analyze_function(file_path, function_name)
        return f"Function {function_name} in {file_path} analyzed."