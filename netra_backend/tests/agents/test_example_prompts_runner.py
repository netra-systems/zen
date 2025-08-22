"""
Test runner for Example Prompts E2E Tests
Provides test execution functionality for parameterized tests
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
from typing import Any, Dict, Optional
from datetime import datetime

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from netra_backend.app.services.quality_gate_service import QualityGateService, ContentType
from netra_backend.app.schemas.Agent import SubAgentState

class TestRunner:
    """Runs individual test cases for example prompts"""
    
    async def run_single_test(
        self, 
        prompt: str, 
        context: Dict[str, Any], 
        infra: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single test case with the given prompt and context
        
        Args:
            prompt: The test prompt to execute
            context: Test context including metadata
            infra: Infrastructure components (supervisor, quality_gate, etc.)
            
        Returns:
            Dictionary containing test results and metrics
        """
        start_time = datetime.now()
        result = {
            "success": False,
            "response": None,
            "error": None,
            "validation": None,
            "metrics": {}
        }
        
        try:
            # Get supervisor from infrastructure
            supervisor = infra.get("supervisor")
            quality_gate = infra.get("quality_gate")
            
            if not supervisor:
                raise ValueError("Supervisor not found in infrastructure")
            
            # Create test state
            test_state = SubAgentState(
                session_id=f"test_{context.get('prompt_index', 0)}_{context.get('variation_num', 0)}",
                context=context,
                messages=[],
                tools=[],
                current_tool_index=0,
                workflow_state={}
            )
            
            # Execute the prompt
            response = await supervisor.process_request(
                prompt=prompt,
                context=context,
                state=test_state
            )
            
            result["response"] = response
            result["success"] = True
            
            # Validate response quality if quality gate is available
            if quality_gate and response:
                validation_result = await quality_gate.validate_content(
                    content=response,
                    content_type=ContentType.RESPONSE,
                    context=context
                )
                result["validation"] = {
                    "valid": validation_result.is_valid,
                    "score": validation_result.score,
                    "feedback": validation_result.feedback
                }
            
            # Calculate metrics
            end_time = datetime.now()
            result["metrics"] = {
                "execution_time": (end_time - start_time).total_seconds(),
                "response_length": len(response) if response else 0,
                "context_type": context.get("prompt_type", "unknown")
            }
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            
        return result
    
    async def run_batch_tests(
        self, 
        test_cases: list, 
        infra: Dict[str, Any],
        concurrency: int = 5
    ) -> list:
        """
        Run multiple test cases concurrently
        
        Args:
            test_cases: List of (prompt, context) tuples
            infra: Infrastructure components
            concurrency: Maximum concurrent tests
            
        Returns:
            List of test results
        """
        semaphore = asyncio.Semaphore(concurrency)
        
        async def run_with_semaphore(prompt, context):
            async with semaphore:
                return await self.run_single_test(prompt, context, infra)
        
        tasks = [
            run_with_semaphore(prompt, context) 
            for prompt, context in test_cases
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def analyze_test_results(self, results: list) -> Dict[str, Any]:
        """
        Analyze a batch of test results and provide summary statistics
        
        Args:
            results: List of test result dictionaries
            
        Returns:
            Dictionary containing analysis metrics
        """
        if not results:
            return {
                "total_tests": 0,
                "successful_tests": 0,
                "failed_tests": 0,
                "success_rate": 0.0,
                "average_quality_score": 0.0,
                "average_execution_time": 0.0
            }
        
        # Count successes and failures
        successful_tests = [r for r in results if r.get("success", False)]
        failed_tests = [r for r in results if not r.get("success", False)]
        
        # Calculate quality scores
        quality_scores = []
        execution_times = []
        
        for result in successful_tests:
            validation = result.get("validation", {})
            if validation.get("score") is not None:
                quality_scores.append(validation["score"])
            
            metrics = result.get("metrics", {})
            if metrics.get("execution_time") is not None:
                execution_times.append(metrics["execution_time"])
        
        # Calculate averages
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        
        return {
            "total_tests": len(results),
            "successful_tests": len(successful_tests),
            "failed_tests": len(failed_tests),
            "success_rate": len(successful_tests) / len(results),
            "average_quality_score": avg_quality,
            "average_execution_time": avg_execution_time,
            "quality_score_count": len(quality_scores),
            "execution_time_count": len(execution_times)
        }