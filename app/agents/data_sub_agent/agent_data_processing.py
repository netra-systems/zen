"""Data processing operations for DataSubAgent."""

from typing import Dict, List, Any
import json

from app.logging_config import central_logger as logger


class DataProcessor:
    """Handles data processing operations for DataSubAgent."""
    
    def __init__(self, agent):
        self.agent = agent
    
    async def process_and_stream(self, data: Dict[str, Any], websocket) -> None:
        """Process data and stream results via WebSocket for real-time updates."""
        try:
            result = await self.agent.analysis_engine.process_data(data)
            await websocket.send(json.dumps({"type": "data_result", "data": result}))
        except Exception as e:
            await websocket.send(json.dumps({"type": "error", "message": str(e)}))

    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate data has required fields."""
        required_fields = ["input", "type"]
        return all(field in data for field in required_fields)

    async def _transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data and preserve type."""
        result = self._create_base_transform_result(data)
        
        if self._should_parse_json_content(data):
            result["parsed"] = self._safe_json_parse(data["content"])
        
        return result
    
    def _create_base_transform_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create base transformation result structure."""
        return {
            "transformed": True,
            "type": data.get("type", "unknown"),
            "content": data.get("content", ""),
            "original": data
        }
    
    def _should_parse_json_content(self, data: Dict[str, Any]) -> bool:
        """Check if data should be parsed as JSON."""
        return data.get("type") == "json" and "content" in data
    
    def _safe_json_parse(self, content: str) -> Dict[str, Any]:
        """Safely parse JSON content with error handling."""
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return {}

    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual data item."""
        return {"status": "processed", "data": data}

    async def process_batch(self, batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process batch of data items."""
        results = []
        for item in batch_data:
            result = await self.process_data(item)
            results.append(result)
        return results