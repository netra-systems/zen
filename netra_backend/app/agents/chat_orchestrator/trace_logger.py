"""Trace logging for NACIS Chat Orchestrator.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Provides transparency through compressed trace display.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class TraceLogger:
    """Manages trace logging for transparency."""
    
    def __init__(self, websocket_manager=None):
        self.websocket_manager = websocket_manager
        self.enabled = True
        self.max_entries = 20
        self.traces: List[Dict[str, Any]] = []
    
    async def log(self, action: str, details: Any = None) -> None:
        """Log trace information."""
        if not self.enabled:
            return
        entry = self._create_trace_entry(action, details)
        self._add_trace_entry(entry)
        await self._send_websocket_update(entry)
    
    def _create_trace_entry(self, action: str, details: Any) -> Dict[str, Any]:
        """Create a trace entry."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "details": self._format_details(details)
        }
    
    def _format_details(self, details: Any) -> Dict[str, Any]:
        """Format details for trace entry."""
        if isinstance(details, dict):
            return details
        elif isinstance(details, str):
            return {"message": details}
        else:
            return {"data": str(details)}
    
    def _add_trace_entry(self, entry: Dict[str, Any]) -> None:
        """Add entry to trace list with size limit."""
        self.traces.append(entry)
        if len(self.traces) > self.max_entries:
            self.traces = self.traces[-self.max_entries:]
    
    async def _send_websocket_update(self, entry: Dict[str, Any]) -> None:
        """Send trace update via WebSocket."""
        if not self.websocket_manager:
            return
        await self.websocket_manager.send_agent_update(
            agent_name="ChatOrchestrator",
            status="trace",
            data=entry
        )
    
    def get_compressed_trace(self, limit: int = 5) -> List[str]:
        """Get compressed trace for UI display."""
        compressed = []
        for trace in self.traces[-limit:]:
            compressed.append(self._format_trace_line(trace))
        return compressed
    
    def _format_trace_line(self, trace: Dict[str, Any]) -> str:
        """Format single trace line."""
        timestamp = trace['timestamp'][-8:]  # Last 8 chars of timestamp
        action = trace['action']
        return f"[{timestamp}] {action}"
    
    def clear(self) -> None:
        """Clear all trace entries."""
        self.traces.clear()
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable trace logging."""
        self.enabled = enabled