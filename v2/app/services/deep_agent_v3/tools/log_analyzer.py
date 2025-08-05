import json
from app.services.deep_agent_v3.tools.base import BaseTool

class LogAnalyzer(BaseTool):
    async def run(self, logs):
        return await self.analyze_logs(logs)

    async def analyze_logs(self, logs):
        prompt = f'Analyze the following logs and return a summary in JSON format: {logs}'
        llm = self.get_llm()
        response = await llm.ainvoke(prompt)
        return json.loads(response.content)