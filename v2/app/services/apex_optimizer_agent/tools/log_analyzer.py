import json
from app.services.apex_optimizer_agent.tools.base import BaseTool
from typing import Any

from app.services.apex_optimizer_agent.tools.context import ToolContext

class LogAnalyzer(BaseTool):
    async def run(self, context: ToolContext) -> Any:
        return await self.analyze_logs(logs)

    async def analyze_logs(self, logs: Any) -> Any:
        prompt = f'Analyze the following logs and return a summary in JSON format: {logs}'
        llm = self.get_llm()
        response = await llm.ainvoke(prompt)
        return json.loads(response.content)