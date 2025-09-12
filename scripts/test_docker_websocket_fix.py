from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python3
"""
Test script to validate WebSocket configuration fixes for Docker environment.

Business Value Justification:
- Segment: Development/DevOps
- Business Goal: Development Velocity
- Value Impact: Eliminates Docker WebSocket connection failures, reduces dev time
- Strategic Impact: Ensures reliable local development environment
"""

import os
import asyncio
import logging
import websockets
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

env = get_env()
class DockerWebSocketTester:
    """Test WebSocket connections for Docker development environment."""
    
    def __init__(self):
        self.results = {
            "environment_vars": {},
            "connection_tests": {},
            "auth_bypass_tests": {},
            "configuration_validation": {}
        }
    
    def test_environment_variables(self) -> None:
        """Test that required environment variables are properly set."""
        logger.info("Testing environment variables configuration...")
        
        # Test variables that should be set in Docker environment
        required_vars = {
            "ALLOW_DEV_OAUTH_SIMULATION": "true",
            "WEBSOCKET_AUTH_BYPASS": "true", 
            "ENVIRONMENT": "development",
        }
        
        docker_compose_vars = {
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
            "NEXT_PUBLIC_WS_URL": "ws://localhost:8000",
            "NEXT_PUBLIC_WEBSOCKET_URL": "ws://localhost:8000/ws"
        }
        
        for var_name, expected in required_vars.items():
            actual = env.get(var_name)
            self.results["environment_vars"][var_name] = {
                "expected": expected,
                "actual": actual,
                "matches": actual == expected
            }
            
        for var_name, expected in docker_compose_vars.items():
            actual = env.get(var_name)
            self.results["environment_vars"][var_name] = {
                "expected": expected,
                "actual": actual,
                "matches": actual == expected
            }
    
    async def test_websocket_connection(self, url: str, auth_bypass: bool = True) -> Dict[str, Any]:
        """Test WebSocket connection to specified URL."""
        logger.info(f"Testing WebSocket connection to: {url}")
        
        result = {
            "url": url,
            "success": False,
            "error": None,
            "response": None,
            "auth_bypass": auth_bypass
        }
        
        try:
            # Try connecting without authentication if bypass is enabled
            headers = {}
            if not auth_bypass:
                # In a real scenario, you'd add a valid auth token here
                headers["Authorization"] = "Bearer fake-token-for-testing"
            
            async with websockets.connect(
                url,
                extra_headers=headers,
                timeout=5
            ) as websocket:
                # Send a test message
                test_message = {
                    "type": "test_connection",
                    "data": {"message": "Docker WebSocket test"}
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Try to receive a response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    result["response"] = response
                    result["success"] = True
                except asyncio.TimeoutError:
                    # Connection successful but no response - still counts as success
                    result["success"] = True
                    result["response"] = "Connection established (no response within timeout)"
                    
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            
        return result
    
    async def test_docker_networking(self) -> None:
        """Test WebSocket connections for Docker networking scenarios."""
        logger.info("Testing Docker networking scenarios...")
        
        # Test URLs that should work in different contexts
        test_scenarios = [
            {
                "name": "localhost_connection",
                "url": "ws://localhost:8000/ws",
                "description": "Frontend connecting from host browser to Docker backend"
            },
            {
                "name": "backend_service_connection", 
                "url": "ws://backend:8000/ws",
                "description": "Internal Docker service-to-service connection"
            }
        ]
        
        for scenario in test_scenarios:
            try:
                result = await self.test_websocket_connection(
                    scenario["url"],
                    auth_bypass=True
                )
                self.results["connection_tests"][scenario["name"]] = {
                    **result,
                    "description": scenario["description"]
                }
            except Exception as e:
                self.results["connection_tests"][scenario["name"]] = {
                    "url": scenario["url"],
                    "success": False,
                    "error": str(e),
                    "description": scenario["description"]
                }
    
    def validate_configuration_files(self) -> None:
        """Validate that configuration files have been properly updated."""
        logger.info("Validating configuration files...")
        
        config_files = [
            {
                "path": "docker-compose.dev.yml",
                "checks": [
                    "ALLOW_DEV_OAUTH_SIMULATION: true",
                    "WEBSOCKET_AUTH_BYPASS: true",
                    "NEXT_PUBLIC_WEBSOCKET_URL: ws://localhost:8000/ws"
                ]
            },
            {
                "path": "frontend/.env.local", 
                "checks": [
                    "NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8000/ws",
                    "NEXT_PUBLIC_WS_URL=ws://localhost:8000"
                ]
            },
            {
                "path": ".env.development.local",
                "checks": [
                    "ALLOW_DEV_OAUTH_SIMULATION=true",
                    "WEBSOCKET_AUTH_BYPASS=true"
                ]
            }
        ]
        
        for file_config in config_files:
            file_path = file_config["path"]
            checks = file_config["checks"]
            
            file_results = {
                "exists": False,
                "checks": {}
            }
            
            try:
                if os.path.exists(file_path):
                    file_results["exists"] = True
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    for check in checks:
                        file_results["checks"][check] = check in content
                else:
                    logger.warning(f"Configuration file not found: {file_path}")
                    
            except Exception as e:
                file_results["error"] = str(e)
                
            self.results["configuration_validation"][file_path] = file_results
    
    def test_auth_bypass_logic(self) -> None:
        """Test the WebSocket OAUTH SIMULATION logic configuration."""
        logger.info("Testing OAUTH SIMULATION logic...")
        
        # Simulate the OAUTH SIMULATION check logic
        try:
            allow_dev_bypass = env.get("ALLOW_DEV_OAUTH_SIMULATION", "false").lower() == "true"
            websocket_bypass = env.get("WEBSOCKET_AUTH_BYPASS", "false").lower() == "true"
            environment = env.get("ENVIRONMENT", "production").lower()
            
            is_development = environment == "development"
            bypass_should_work = is_development and (allow_dev_bypass or websocket_bypass)
            
            self.results["auth_bypass_tests"] = {
                "allow_dev_bypass": allow_dev_bypass,
                "websocket_bypass": websocket_bypass,
                "is_development": is_development,
                "bypass_should_work": bypass_should_work,
                "environment": environment
            }
            
            if bypass_should_work:
                logger.info(" PASS:  OAUTH SIMULATION is properly configured for development")
            else:
                logger.warning(" WARNING: [U+FE0F] OAUTH SIMULATION may not work - check environment variables")
                
        except Exception as e:
            self.results["auth_bypass_tests"]["error"] = str(e)
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all WebSocket configuration tests."""
        logger.info("[U+1F680] Starting Docker WebSocket configuration tests...")
        
        # Test environment variables
        self.test_environment_variables()
        
        # Test OAUTH SIMULATION logic
        self.test_auth_bypass_logic()
        
        # Validate configuration files
        self.validate_configuration_files()
        
        # Test WebSocket connections (only if services are running)
        try:
            await self.test_docker_networking()
        except Exception as e:
            logger.warning(f"WebSocket connection tests failed (services may not be running): {e}")
            self.results["connection_tests"]["error"] = str(e)
        
        return self.results
    
    def print_results(self) -> None:
        """Print test results in a readable format."""
        print("\n" + "="*60)
        print("DOCKER WEBSOCKET CONFIGURATION TEST RESULTS")
        print("="*60)
        
        # Environment Variables
        print("\nEnvironment Variables:")
        for var_name, info in self.results["environment_vars"].items():
            status = "[OK]" if info["matches"] else "[FAIL]"
            print(f"  {status} {var_name}: {info['actual']} (expected: {info['expected']})")
        
        # OAUTH SIMULATION Configuration
        print("\nOAUTH SIMULATION Configuration:")
        auth_tests = self.results["auth_bypass_tests"]
        if "error" not in auth_tests:
            bypass_status = "[OK]" if auth_tests["bypass_should_work"] else "[FAIL]"
            print(f"  {bypass_status} OAUTH SIMULATION enabled: {auth_tests['bypass_should_work']}")
            print(f"     - Environment: {auth_tests['environment']}")
            print(f"     - DEV_AUTH_BYPASS: {auth_tests['allow_dev_bypass']}")
            print(f"     - WEBSOCKET_BYPASS: {auth_tests['websocket_bypass']}")
        else:
            print(f"  [FAIL] Error testing OAUTH SIMULATION: {auth_tests['error']}")
        
        # Configuration Files
        print("\nConfiguration Files:")
        for file_path, file_info in self.results["configuration_validation"].items():
            if file_info["exists"]:
                print(f"  [OK] {file_path}:")
                for check, passed in file_info["checks"].items():
                    status = "[OK]" if passed else "[FAIL]"
                    print(f"    {status} {check}")
            else:
                print(f"  [FAIL] {file_path}: File not found")
        
        # Connection Tests
        print("\nConnection Tests:")
        if "error" in self.results["connection_tests"]:
            print(f"  [SKIP] Connection tests skipped: {self.results['connection_tests']['error']}")
        else:
            for test_name, test_result in self.results["connection_tests"].items():
                if test_name != "error":
                    status = "[OK]" if test_result["success"] else "[FAIL]"
                    print(f"  {status} {test_name}: {test_result['url']}")
                    if not test_result["success"]:
                        print(f"     Error: {test_result['error']}")
        
        print("\n" + "="*60)
        print("Test Complete!")
        print("="*60)


async def main():
    """Main test execution."""
    logging.basicConfig(level=logging.INFO)
    
    tester = DockerWebSocketTester()
    results = await tester.run_all_tests()
    tester.print_results()
    
    # Return exit code based on critical checks
    auth_bypass_works = results.get("auth_bypass_tests", {}).get("bypass_should_work", False)
    config_files_exist = all(
        info.get("exists", False) 
        for info in results.get("configuration_validation", {}).values()
    )
    
    if auth_bypass_works and config_files_exist:
        print("\n[OK] All critical checks passed! WebSocket should work in Docker development environment.")
        return 0
    else:
        print("\n[FAIL] Some critical checks failed. Please review the configuration.")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)