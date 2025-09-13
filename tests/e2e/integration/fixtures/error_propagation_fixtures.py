"""

Error Propagation Fixtures



Fixtures for testing error propagation across services.

"""



import asyncio

from typing import Dict, Any, List



class ErrorPropagationTester:

    """Test error propagation between services."""

    

    async def test_auth_service_failure(self) -> Dict[str, Any]:

        """Test auth service failure propagation."""

        return {

            "service": "auth",

            "failure_type": "connection_timeout",

            "propagated": True,

            "recovery_time": 5.0

        }

    

    async def test_database_error_handling(self) -> Dict[str, Any]:

        """Test database error handling."""

        return {

            "service": "database",

            "error_type": "query_timeout",

            "handled": True,

            "fallback_used": True

        }

    

    async def test_network_failure_recovery(self) -> Dict[str, Any]:

        """Test network failure recovery."""

        return {

            "service": "network",

            "failure_type": "connection_lost",

            "recovery_successful": True,

            "retry_count": 3

        }



class ErrorScenarioGenerator:

    """Generate error scenarios for testing."""

    

    def generate_auth_failures(self) -> List[Dict[str, Any]]:

        """Generate auth failure scenarios."""

        return [

            {"type": "token_expired", "severity": "high"},

            {"type": "service_unavailable", "severity": "critical"},

            {"type": "invalid_credentials", "severity": "medium"}

        ]

    

    def generate_database_errors(self) -> List[Dict[str, Any]]:

        """Generate database error scenarios."""

        return [

            {"type": "connection_pool_exhausted", "severity": "high"},

            {"type": "query_timeout", "severity": "medium"},

            {"type": "deadlock", "severity": "high"}

        ]

