"""
Async Performance Analyzer
Analyzes async test performance and provides recommendations
Maximum 300 lines, functions  <= 8 lines
"""

import asyncio
import time
from typing import Any, Dict, List

class AsyncPerformanceAnalyzer:
    """Analyze async test performance"""
    
    def __init__(self):
        self.performance_data: Dict[str, Any] = {}
    
    async def analyze_test_performance(self, test_func) -> Dict[str, Any]:
        """Analyze performance of async test function"""
        start_metrics = self._capture_start_metrics()
        execution_result = await self._execute_test_function(test_func)
        end_metrics = self._capture_end_metrics()
        return self._compile_performance_result(start_metrics, end_metrics, execution_result)
    
    def _capture_start_metrics(self) -> Dict[str, Any]:
        """Capture initial performance metrics"""
        return {
            "start_time": time.time(),
            "start_tasks": len(asyncio.all_tasks())
        }
    
    async def _execute_test_function(self, test_func) -> Dict[str, Any]:
        """Execute test function and capture result"""
        try:
            await test_func()
            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _capture_end_metrics(self) -> Dict[str, Any]:
        """Capture final performance metrics"""
        return {
            "end_time": time.time(),
            "end_tasks": len(asyncio.all_tasks())
        }
    
    def _compile_performance_result(self, start: Dict, end: Dict, execution: Dict) -> Dict[str, Any]:
        """Compile final performance analysis result"""
        duration = end["end_time"] - start["start_time"]
        return {
            "duration": duration,
            "success": execution["success"],
            "error": execution["error"],
            "task_creation": end["end_tasks"] - start["start_tasks"],
            "recommendations": self._get_performance_recommendations(duration)
        }
    
    def _get_performance_recommendations(self, duration: float) -> List[str]:
        """Get performance recommendations"""
        recommendations = []
        if duration > 1.0:
            recommendations.append("Consider breaking down long tests")
        if duration > 5.0:
            recommendations.append("Test may need timeout handling")
        return recommendations
    
    def _measure_test_performance(self, test_func) -> Dict[str, Any]:
        """Measure test performance metrics"""
        start_time = time.time()
        execution_result = self._execute_performance_test(test_func)
        duration = time.time() - start_time
        return self._format_performance_result(duration, execution_result)
    
    def _execute_performance_test(self, test_func) -> Dict[str, Any]:
        """Execute test function for performance measurement"""
        try:
            if asyncio.iscoroutinefunction(test_func):
                asyncio.run(test_func())
            else:
                test_func()
            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _format_performance_result(self, duration: float, execution: Dict) -> Dict[str, Any]:
        """Format performance measurement result"""
        return {
            "duration": duration,
            "success": execution["success"],
            "error": execution["error"]
        }