import json
from app.services.apex_optimizer_agent.tools.base import BaseTool
from typing import Any
from app.services.context import ToolContext

class LogAnalyzer(BaseTool):
    async def run(self, context: ToolContext) -> Any:
        return await self.analyze_logs(context)

    async def analyze_logs(self, context: ToolContext) -> Any:
        prompt = f'Analyze the following logs and return a summary in JSON format: {context.logs}'
        llm = context.llm_manager.get_llm(self.llm_name or "default")
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        return json.loads(content)
