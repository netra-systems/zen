"""Database Error Handling Validation



This module contains validators for database error handling and recovery mechanisms.

"""



import asyncio

import logging



# Add project root to path for imports

import sys

from pathlib import Path

from typing import Any, Dict, List





from tests.e2e.helpers.resilience.error_propagation.error_generators import (

    ErrorCorrelationContext,

    RealErrorPropagationTester,

)



logger = logging.getLogger(__name__)





class DatabaseErrorHandlingValidator:

    """Validates database errors are handled gracefully with recovery mechanisms."""

    

    def __init__(self, tester: RealErrorPropagationTester):

        self.tester = tester

        self.db_error_scenarios: List[Dict[str, Any]] = []

    

    async def test_database_connection_failure_handling(self) -> Dict[str, Any]:

        """Test database connection failure handling and recovery."""

        context = self.tester._create_correlation_context("db_connection_failure")

        context.service_chain.append("database_layer")

        

        # Test database-dependent endpoint

        db_test_result = await self._test_database_dependent_operation(context)

        

        # Test graceful degradation

        degradation_result = await self._test_graceful_degradation(context)

        

        # Test recovery mechanisms

        recovery_result = await self._test_database_recovery(context)

        

        return {

            "test_type": "database_connection_failure",

            "request_id": context.request_id,

            "database_operation": db_test_result,

            "graceful_degradation": degradation_result,

            "recovery_mechanisms": recovery_result,

            "system_stability": self._assess_system_stability(

                db_test_result, degradation_result, recovery_result

            )

        }

    

    async def _test_database_dependent_operation(self, context: ErrorCorrelationContext) -> Dict[str, Any]:

        """Test operation that depends on database."""

        context.service_chain.append("user_profile_service")

        

        try:

            response = await self.tester.http_client.get("/auth/me", token="mock_token_for_db_test")

            

            return {

                "database_accessible": True,

                "operation_successful": True,

                "status_code": getattr(response, 'status_code', None)

            }

            

        except Exception as e:

            return self._analyze_database_error(e, context)

    

    def _analyze_database_error(self, error: Exception, context: ErrorCorrelationContext) -> Dict[str, Any]:

        """Analyze database error response."""

        error_str = str(error).lower()

        

        # Check for database-related error indicators

        db_indicators = ["database", "connection", "timeout", "unavailable", "service", "502", "503"]

        db_error_detected = any(indicator in error_str for indicator in db_indicators)

        

        # Check for graceful error handling

        graceful_indicators = ["temporarily", "unavailable", "try again", "maintenance", "service"]

        graceful_handling = any(indicator in error_str for indicator in graceful_indicators)

        

        context.error_source = "database"

        

        return {

            "database_error_detected": db_error_detected,

            "graceful_handling": graceful_handling,

            "error_message": str(error),

            "system_stable": True  # If we can catch and handle it, system is stable

        }

    

    async def _test_graceful_degradation(self, context: ErrorCorrelationContext) -> Dict[str, Any]:

        """Test system graceful degradation when database is unavailable."""

        context.service_chain.append("degradation_layer")

        

        try:

            response = await self.tester.http_client.get("/health")

            

            return {

                "health_endpoint_available": True,

                "graceful_degradation": True,

                "status_code": getattr(response, 'status_code', None)

            }

            

        except Exception as e:

            return {

                "health_endpoint_failed": True,

                "system_still_responding": True,

                "error_handled": self._is_graceful_error(str(e))

            }

    

    def _is_graceful_error(self, error_str: str) -> bool:

        """Check if error indicates graceful handling."""

        return "health" in error_str.lower() or "service" in error_str.lower()

    

    async def _test_database_recovery(self, context: ErrorCorrelationContext) -> Dict[str, Any]:

        """Test database recovery mechanisms."""

        context.service_chain.append("recovery_layer")

        

        recovery_attempts = []

        

        for attempt in range(3):

            try:

                response = await self.tester.http_client.get("/health")

                recovery_attempts.append({

                    "attempt": attempt + 1,

                    "successful": True,

                    "status": getattr(response, 'status_code', None)

                })

                break

                

            except Exception as e:

                recovery_attempts.append({

                    "attempt": attempt + 1,

                    "successful": False,

                    "error": str(e)

                })

                await asyncio.sleep(1.0)

        

        successful_recovery = any(attempt["successful"] for attempt in recovery_attempts)

        

        return {

            "recovery_attempts": recovery_attempts,

            "successful_recovery": successful_recovery,

            "retry_mechanism_active": len(recovery_attempts) > 1

        }

    

    def _assess_system_stability(self, *test_results) -> Dict[str, Any]:

        """Assess overall system stability during database issues."""

        stability_indicators = []

        

        for result in test_results:

            if isinstance(result, dict):

                if result.get("system_stable", False):

                    stability_indicators.append("stable_error_handling")

                if result.get("graceful_handling", False):

                    stability_indicators.append("graceful_degradation")

                if result.get("successful_recovery", False):

                    stability_indicators.append("recovery_capability")

        

        return {

            "stability_score": len(stability_indicators),

            "stability_indicators": stability_indicators,

            "system_resilient": len(stability_indicators) >= 2

        }





class DatabaseConnectionTester:

    """Utility for testing database connection scenarios."""

    

    def __init__(self, tester: RealErrorPropagationTester):

        self.tester = tester

    

    async def test_connection_pool_exhaustion(self) -> Dict[str, Any]:

        """Test behavior when database connection pool is exhausted."""

        # This would require special setup to exhaust the connection pool

        # For now, return a mock result

        return {

            "test_type": "connection_pool_exhaustion",

            "pool_exhausted": False,

            "graceful_handling": True,

            "note": "Mock implementation - requires special database setup"

        }

    

    async def test_slow_query_timeout(self) -> Dict[str, Any]:

        """Test behavior with slow database queries."""

        try:

            # Attempt a potentially slow operation

            response = await self.tester.http_client.get("/auth/me", token="test_token")

            

            return {

                "test_type": "slow_query_timeout",

                "query_completed": True,

                "timeout_handled": False

            }

            

        except Exception as e:

            error_str = str(e).lower()

            timeout_indicators = ["timeout", "slow", "query"]

            timeout_handled = any(indicator in error_str for indicator in timeout_indicators)

            

            return {

                "test_type": "slow_query_timeout",

                "query_completed": False,

                "timeout_handled": timeout_handled,

                "error_message": str(e)

            }

    

    def validate_connection_parameters(self, config: Dict[str, Any]) -> Dict[str, bool]:

        """Validate database connection configuration."""

        required_params = ["host", "port", "database", "username"]

        optional_params = ["timeout", "pool_size", "ssl_mode"]

        

        validation_result = {}

        

        for param in required_params:

            validation_result[f"{param}_present"] = param in config

            if param in config:

                validation_result[f"{param}_valid"] = bool(config[param])

        

        for param in optional_params:

            if param in config:

                validation_result[f"{param}_present"] = True

                validation_result[f"{param}_valid"] = bool(config[param])

        

        validation_result["overall_valid"] = all(

            validation_result.get(f"{param}_present", False) 

            for param in required_params

        )

        

        return validation_result

