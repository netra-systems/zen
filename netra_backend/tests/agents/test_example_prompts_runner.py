"""
Test runner for Example Prompts E2E Tests
Provides test execution functionality for parameterized tests
"""

import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from typing import Any, Dict, Optional
from datetime import datetime

from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.services.quality_gate_service import QualityGateService, ContentType
from app.schemas.Agent import SubAgentState


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