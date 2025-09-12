"""
Onboarding Flow Executor - Main execution logic for user onboarding E2E tests

BVJ (Business Value Justification):
1. Segment: Free  ->  Paid conversion segment (most critical)
2. Business Goal: Execute complete user onboarding flow efficiently
3. Value Impact: Protects $100K+ MRR through comprehensive flow execution
4. Revenue Impact: Ensures reliable onboarding test execution

REQUIREMENTS:
- Modular execution components
- Performance validation (<10 seconds)
- 450-line file limit, 25-line function limit
"""
import time
from typing import Dict, Any

from tests.e2e.user_onboarding_helpers import (
    OnboardingFlowManager, UserRegistrationHelper, ProfileSetupHelper, OptimizationRequestHelper,
    OnboardingFlowManager,
    UserRegistrationHelper,
    ProfileSetupHelper,
    OptimizationRequestHelper
)


class ResultValidationHelper:
    """Helper for validating onboarding flow results."""
    
    def __init__(self, flow_manager: OnboardingFlowManager):
        self.flow_manager = flow_manager
        
    def validate_registration_result(self, result: Dict[str, Any]) -> None:
        """Validate registration result meets business requirements."""
        assert result.get("success"), "Registration must succeed"
        assert "access_token" in result, "Must provide access token"
        assert result.get("token_type") == "Bearer", "Must use Bearer token"
        assert result["user"]["email"].endswith("@netrasystems.ai"), "Must use test email"
    
    def validate_profile_result(self, result: Dict[str, Any]) -> None:
        """Validate profile setup result."""
        assert "user_id" in result, "Profile must have user ID"
        assert "ai_goals" in result, "Profile must include AI goals"
        assert result.get("onboarding_complete"), "Onboarding must be complete"
    
    def validate_optimization_result(self, result: Dict[str, Any]) -> None:
        """Validate optimization request result."""
        assert result.get("type") == "agent_response", "Must be agent response"
        assert len(result.get("content", "")) > 50, "Response must be substantial"
        assert "cost" in result.get("content", "").lower(), "Must address costs"
        assert "recommendations" in result, "Must provide recommendations"
    
    def validate_performance(self, execution_time: float) -> None:
        """Validate performance meets business requirements."""
        assert execution_time < 10.0, f"Flow took {execution_time:.2f}s, max 10s"
        print(f"[PERFORMANCE] Onboarding completed in {execution_time:.2f}s")


class OnboardingFlowExecutor:
    """Main executor for complete onboarding flow."""
    
    def __init__(self, harness):
        self.flow_manager = OnboardingFlowManager(harness)
        self.registration_helper = UserRegistrationHelper(self.flow_manager)
        self.profile_helper = ProfileSetupHelper(self.flow_manager)
        self.optimization_helper = OptimizationRequestHelper(self.flow_manager)
        self.validator = ResultValidationHelper(self.flow_manager)
    
    async def execute_complete_onboarding_flow(self) -> Dict[str, Any]:
        """Execute complete user onboarding flow."""
        start_time = time.time()
        results = await self._run_flow_with_error_handling()
        execution_time = time.time() - start_time
        return self._finalize_results(results, execution_time)
    
    async def _run_flow_with_error_handling(self) -> Dict[str, Any]:
        """Run flow with proper error handling."""
        try:
            await self.flow_manager.setup_services()
            return await self._execute_flow_steps()
        except Exception as e:
            return {"error": str(e), "success": False}
        finally:
            await self.flow_manager.cleanup_services()
    
    def _finalize_results(self, results: Dict, execution_time: float) -> Dict[str, Any]:
        """Finalize results with performance validation."""
        if not results.get("error"):
            results["execution_time"] = execution_time
            results["success"] = True
            self.validator.validate_performance(execution_time)
        return results
    
    async def _execute_flow_steps(self) -> Dict[str, Any]:
        """Execute all onboarding flow steps."""
        registration_result = await self._execute_registration_step()
        profile_result = await self._execute_profile_step(registration_result)
        optimization_result = await self._execute_optimization_step(registration_result)
        return self._build_flow_results(registration_result, profile_result, optimization_result)
    
    async def _execute_registration_step(self) -> Dict[str, Any]:
        """Execute registration step with validation."""
        registration_result = await self.registration_helper.execute_registration()
        self.validator.validate_registration_result(registration_result)
        return registration_result
    
    async def _execute_profile_step(self, registration_result: Dict) -> Dict[str, Any]:
        """Execute profile setup step with validation."""
        profile_result = await self.profile_helper.execute_profile_setup(registration_result)
        self.validator.validate_profile_result(profile_result)
        return profile_result
    
    async def _execute_optimization_step(self, registration_result: Dict) -> Dict[str, Any]:
        """Execute optimization step with validation."""
        optimization_result = await self.optimization_helper.execute_optimization_request(registration_result)
        self.validator.validate_optimization_result(optimization_result)
        return optimization_result
    
    def _build_flow_results(self, reg: Dict, profile: Dict, opt: Dict) -> Dict[str, Any]:
        """Build comprehensive flow results."""
        return {
            "registration": reg,
            "profile_setup": profile,
            "first_optimization": opt,
            "user_email": reg["user"]["email"]
        }
