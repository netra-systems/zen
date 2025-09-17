"""
E2E Test: Auth Service Port Configuration Validation
This test exposes the port mismatch issue where E2E tests expect different ports but auth service uses a different default.

BVJ: Enterprise | Infrastructure | Service Discovery | BLOCKING - Port mismatches prevent E2E tests from running"""
ISSUE: Auth service defaults to 8080 but E2E tests expect 8001/8081 causing connection failures"""
import asyncio
import os
import httpx
import pytest
from typing import Dict, List, Any
from shared.isolated_environment import IsolatedEnvironment

# Test configurations that represent the current inconsistent state
PORT_CONFIGURATIONS = [ ]"""
"name": "CORRECTED_E2E_CONFIG",
"expected_auth_port": 8081,
"description": "Corrected E2E test configuration - now expects auth on 8081 (matches dev launcher)",
"test_files_using": [ )
"config.py", "harness_complete.py", "integration/config.py",
"oauth_test_providers.py", "README.md", "fixtures/*.py"

},
{ }
"name": "DEV_LAUNCHER_CONFIG",
"expected_auth_port": 8081,
"description": "Dev launcher and real service tests expect auth on 8081 (CORRECT)",
"test_files_using": [ )
"dev_launcher_real_system.py", "real_services_manager.py",
"jwt_token_helpers.py", "performance/*.py"

},
{ }
"name": "AUTH_SERVICE_RUNTIME",
"expected_auth_port": 8081,
"description": "Auth service main.py runtime - defaults to 8081 when PORT not set",
"test_files_using": [ )
"auth_service/main.py"




class AuthServicePortConfigurationValidator:
    """Validates auth service port configuration consistency across the system."""

    def __init__(self):
        pass
        self.results: List[Dict[str, Any]] = []
"""
        """Test all port configurations and expose the mismatch."""
validation_results = {"success": False,, "configurations_tested": len(PORT_CONFIGURATIONS),, "working_configurations": 0,, "failed_configurations": 0,, "port_mismatch_detected": False,, "configuration_results": [],, "recommended_fix": None}
        working_ports = set()

        for config in PORT_CONFIGURATIONS:
        result = await self.validate_port_configuration(config)
        validation_results["configuration_results"].append(result)

        if result["connection_successful"]:
        validation_results["working_configurations"] += 1
        working_ports.add(config["expected_auth_port"])
        else:
        validation_results["failed_configurations"] += 1

                # Detect port mismatch if we have different expected ports but only some work
        if len(working_ports) < len(PORT_CONFIGURATIONS):
        validation_results["port_mismatch_detected"] = True
        validation_results["recommended_fix"] = self._generate_fix_recommendation(validation_results)

                    # Overall success only if ALL configurations work
        validation_results["success"] = validation_results["working_configurations"] == validation_results["configurations_tested"]

        return validation_results

    async def validate_port_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test a specific port configuration."""
        port = config["expected_auth_port"]
result = {"configuration_name": config["name"],, "expected_port": port,, "description": config["description"],, "test_files_using": config["test_files_using"],, "connection_successful": False,, "health_check_successful": False,, "response_data": None,, "error": None, try:}
        # Test basic connection to the expected port
        health_url = "formatted_string"

        async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(health_url)

        if response.status_code == 200:
        result["connection_successful"] = True
        result["health_check_successful"] = True
        result["response_data"] = response.json()
        else:
        result["error"] = "formatted_string"

        except httpx.ConnectError:
        result["error"] = "formatted_string"
        except httpx.TimeoutException:
        result["error"] = "formatted_string"
        except Exception as e:
        result["error"] = "formatted_string"

        return result

    def _generate_fix_recommendation(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendation for fixing the port mismatch.""""""
        result for result in validation_results["configuration_results"]
        if result["connection_successful"]
    
        failed_configs = [ )
        result for result in validation_results["configuration_results"]
        if not result["connection_successful"]
    

        if working_configs:
        working_port = working_configs[0]["expected_port"]
recommendation = {"issue": "Port configuration mismatch detected",, "working_port": working_port,, "failed_ports": [config["expected_port"] for config in failed_configs],, "recommended_action": "formatted_string",, "files_to_update": []}
        # Collect files that need updating
        for config in failed_configs:
        recommendation["files_to_update"].extend(config["test_files_using"])

        return recommendation
        else:
        return { )
        "issue": "No working auth service port found",
        "recommended_action": "Start auth service on expected port or update all configurations",
        "suggested_ports": [config["expected_port"] for config in PORT_CONFIGURATIONS]
                


@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_auth_service_port_consistency_validation():
"""
FAILING TEST: Expose auth service port configuration inconsistencies

This test is DESIGNED TO FAIL to expose the current port mismatch issue:
- E2E tests expect auth service on different ports (8001, 8081)
- Auth service defaults to port 8080
- This causes E2E test failures when services are not running on expected ports
"""
the need to standardize port configurations across the system."""
pass
validator = AuthServicePortConfigurationValidator()
results = await validator.validate_all_port_configurations()
"""
print(f" )
=== AUTH SERVICE PORT CONFIGURATION VALIDATION ===")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")

print(f" )
=== DETAILED RESULTS ===")
for config_result in results['configuration_results']:
status = " PASS:  WORKING" if config_result['connection_successful'] else " FAIL:  FAILED"
print("formatted_string")
print("formatted_string")
if config_result['error']:
print("formatted_string")
if config_result['test_files_using']:
print("formatted_string")
print()

if results['recommended_fix']:
print(f" )
=== RECOMMENDED FIX ===")
fix = results['recommended_fix']
print("formatted_string")
print("formatted_string")
if 'working_port' in fix:
print("formatted_string")
print("formatted_string")

                                            # This assertion is DESIGNED TO FAIL to expose the port mismatch issue
assert results['success'], ( )
f"AUTH SERVICE PORT MISMATCH DETECTED: "
"formatted_string"
"formatted_string"
f"This test exposes the inconsistent port configurations across E2E tests. "
f"Fix by standardizing all E2E tests to use the same auth service port."
                                            


@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_specific_port_8001_expectation():
"""
Test that specifically checks if auth service is running on port 8001
as expected by many E2E test configuration files.
"""
exposing the mismatch with E2E test expectations."""
pass"""
health_url = "formatted_string"

try:
async with httpx.AsyncClient(timeout=5.0) as client:
response = await client.get(health_url)

                                                        # Verify response is successful and contains auth service identifier
assert response.status_code == 200, "formatted_string"

response_data = response.json()
assert "auth" in response_data.get("service", "").lower(), ( )
"formatted_string"
                                                        

print("formatted_string")

except httpx.ConnectError:
pytest.fail( )
"formatted_string"
f"Many E2E tests expect auth service on this port but it"s not available. "
f"This exposes the port configuration mismatch issue."
                                                            
except httpx.TimeoutException:
pytest.fail("formatted_string")


@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_specific_port_8081_expectation():
"""
Test that specifically checks if auth service is running on port 8081
as expected by dev launcher and real service E2E tests.
"""
exposing the mismatch with dev launcher expectations."""
pass"""
health_url = "formatted_string"

try:
async with httpx.AsyncClient(timeout=5.0) as client:
response = await client.get(health_url)

                                                                            # Verify response is successful and contains auth service identifier
assert response.status_code == 200, "formatted_string"

response_data = response.json()
assert "auth" in response_data.get("service", "").lower(), ( )
"formatted_string"
                                                                            

print("formatted_string")

except httpx.ConnectError:
pytest.fail( )
"formatted_string"
f"Dev launcher and real service E2E tests expect auth service on this port but it"s not available. "
f"This exposes the port configuration mismatch issue."
                                                                                
except httpx.TimeoutException:
pytest.fail("formatted_string")


if __name__ == "__main__":
                                                                                        # Run the validator directly for debugging
async def main():
pass
validator = AuthServicePortConfigurationValidator()
results = await validator.validate_all_port_configurations()

print("=== AUTH SERVICE PORT VALIDATION RESULTS ===")
import json
print(json.dumps(results, indent=2))

asyncio.run(main())
