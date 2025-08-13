"""
Test runner logic for Example Prompts E2E Tests
Handles test execution and result validation
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.agents.state import DeepAgentState
from app.schemas import SubAgentState
from app.services.quality_gate_service import ContentType


class TestRunner:
    """Handles test execution for example prompts"""
    
    async def run_single_test(
        self, 
        prompt: str, 
        context: Dict[str, Any], 
        infra: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run a single test with the given prompt and context
        
        Args:
            prompt: The test prompt to execute
            context: Synthetic context data
            infra: Infrastructure components (services, managers, etc.)
            
        Returns:
            Test result dictionary with response and metrics
        """
        try:
            # Initialize supervisor agent
            supervisor = Supervisor(
                llm_manager=infra["llm_manager"],
                websocket_manager=infra["websocket_manager"],
                db_session=infra["db_session"],
                quality_gate_service=infra["quality_gate_service"],
                corpus_service=infra["corpus_service"],
                agent_service=infra["agent_service"],
                apex_tool_selector=infra["apex_tool_selector"],
                state_persistence_service=infra["state_persistence_service"]
            )
            
            # Create initial state
            state = DeepAgentState(
                messages=[{"role": "user", "content": prompt}],
                context=context,
                metadata={
                    "test_id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "prompt_type": context.get("prompt_type", "unknown")
                },
                sub_agent_states={
                    "triage": SubAgentState(status="pending"),
                    "cost_optimizer": SubAgentState(status="pending"),
                    "latency_optimizer": SubAgentState(status="pending"),
                    "capacity_planner": SubAgentState(status="pending"),
                }
            )
            
            # Execute the supervisor logic
            result = await self._execute_with_timeout(
                supervisor.process(state),
                timeout=30
            )
            
            # Validate the response
            validation_result = await self._validate_result(
                result, 
                infra["quality_gate_service"]
            )
            
            # Generate corpus data if needed
            if context.get("generate_corpus"):
                await infra["corpus_service"].ingest({
                    "prompt": prompt,
                    "response": result.get("response", ""),
                    "context": context,
                    "metadata": result.get("metadata", {})
                })
            
            return {
                "success": True,
                "response": result.get("response", ""),
                "validation": validation_result,
                "metrics": {
                    "execution_time": result.get("execution_time", 0),
                    "tokens_used": result.get("tokens_used", 0),
                    "quality_score": validation_result.get("score", 0),
                },
                "metadata": {
                    "test_id": state.metadata["test_id"],
                    "timestamp": state.metadata["timestamp"],
                    "context_type": context.get("prompt_type", "unknown")
                }
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Test execution timed out after 30 seconds",
                "response": None,
                "validation": {"valid": False, "score": 0},
                "metrics": {}
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": None,
                "validation": {"valid": False, "score": 0},
                "metrics": {}
            }
    
    async def _execute_with_timeout(self, coro, timeout: int = 30):
        """Execute a coroutine with a timeout"""
        return await asyncio.wait_for(coro, timeout=timeout)
    
    async def _validate_result(
        self, 
        result: Dict[str, Any], 
        quality_service
    ) -> Dict[str, Any]:
        """Validate the test result using quality gate service"""
        try:
            response = result.get("response", "")
            
            # Skip validation for empty responses
            if not response:
                return {
                    "valid": False,
                    "score": 0,
                    "feedback": ["Empty response"]
                }
            
            # Validate with quality gate service
            is_valid, score, feedback = await quality_service.validate_content(
                content=response,
                content_type=ContentType.RESPONSE,
                quality_level="medium"
            )
            
            return {
                "valid": is_valid,
                "score": score,
                "feedback": feedback
            }
        except Exception as e:
            return {
                "valid": False,
                "score": 0,
                "feedback": [f"Validation error: {str(e)}"]
            }
    
    def analyze_test_results(self, results: list[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze aggregate test results"""
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.get("success"))
        
        # Calculate metrics
        avg_quality_score = sum(
            r.get("validation", {}).get("score", 0) 
            for r in results
        ) / total_tests if total_tests > 0 else 0
        
        avg_execution_time = sum(
            r.get("metrics", {}).get("execution_time", 0) 
            for r in results
        ) / total_tests if total_tests > 0 else 0
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "average_quality_score": avg_quality_score,
            "average_execution_time": avg_execution_time,
            "failed_tests": [
                r.get("metadata", {}).get("test_id") 
                for r in results 
                if not r.get("success")
            ]
        }