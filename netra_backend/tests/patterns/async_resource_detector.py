"""
Async Resource Leak Detector
Detects async resource leaks in test suites
Maximum 300 lines, functions  <= 8 lines
"""

import asyncio
from typing import Any, Dict, List

class AsyncResourceLeakDetector:
    """Detect async resource leaks in tests"""
    
    def __init__(self):
        self.initial_state: Dict[str, Any] = {}
        self.final_state: Dict[str, Any] = {}
    
    async def start_monitoring(self) -> None:
        """Start monitoring async resources"""
        self.initial_state = await self._capture_state()
    
    async def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and detect leaks"""
        self.final_state = await self._capture_state()
        return self._detect_leaks()
    
    async def _capture_state(self) -> Dict[str, Any]:
        """Capture current async state"""
        loop = asyncio.get_event_loop()
        return {
            "tasks": len(asyncio.all_tasks()),
            "handles": len(getattr(loop, '_ready', [])),
            "open_files": len(getattr(loop, '_fd_map', {}))
        }
    
    def _detect_leaks(self) -> Dict[str, Any]:
        """Detect resource leaks between states"""
        leaks = {}
        for resource, initial_count in self.initial_state.items():
            final_count = self.final_state.get(resource, 0)
            if final_count > initial_count:
                leaks[resource] = final_count - initial_count
        
        return {
            "has_leaks": len(leaks) > 0,
            "leaks": leaks,
            "recommendations": self._get_leak_recommendations(leaks)
        }
    
    def _get_leak_recommendations(self, leaks: Dict[str, int]) -> List[str]:
        """Get recommendations for fixing leaks"""
        recommendations = []
        
        if "tasks" in leaks:
            recommendations.append("Cancel background tasks in test cleanup")
        
        if "handles" in leaks:
            recommendations.append("Close async handles and connections")
        
        return recommendations