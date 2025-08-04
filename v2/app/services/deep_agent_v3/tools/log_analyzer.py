
import json
from app.services.deep_agent_v3.tools.base import BaseTool

class LogAnalyzer(BaseTool):
    async def analyze_logs(self, logs):
        prompt = f'Analyze the following logs and return a summary in JSON format: {logs}'
        response = await self.llm_connector.generate_text_async(prompt)
        return json.loads(response)
