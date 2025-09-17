#!/usr/bin/env python3
"""
Staging Deployment Validation Script for Issue #1177 Supervisor Consolidation

This script validates that the supervisor consolidation changes deployed successfully
to staging and that all critical functionality remains intact.

Usage:
    python scripts/validate_staging_supervisor_deployment.py

Expected to run AFTER deployment:
    python scripts/deploy_to_gcp_actual.py --project netra-staging --service backend --build-local
"""

import asyncio
import json
import sys
import time
import requests
import websockets
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class StagingValidationResults:
    """Collects and reports validation results."""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.start_time = time.time()
    
    def add_result(self, test_name: str, success: bool, details: str = "", metrics: Dict = None):
        """Add a test result."""
        self.results[test_name] = {
            'success': success,
            'details': details,
            'metrics': metrics or {},
            'timestamp': time.time()
        }
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
    
    def generate_summary(self) -> str:
        """Generate validation summary."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r['success'])
        failed_tests = total_tests - passed_tests
        
        total_time = time.time() - self.start_time
        
        summary = f"""
## Staging Deployment Validation Summary

**Overall Status**: {'✅ SUCCESS' if failed_tests == 0 else '❌ FAILED'}
**Tests**: {passed_tests}/{total_tests} passed
**Duration**: {total_time:.2f} seconds

### Test Results:
"""
        
        for test_name, result in self.results.items():
            status = "✅" if result['success'] else "❌"
            summary += f"- {status} **{test_name}**: {result['details']}\n"
            if result['metrics']:
                for metric, value in result['metrics'].items():
                    summary += f"  - {metric}: {value}\n"
        
        if failed_tests > 0:
            summary += f"\n**⚠️ {failed_tests} tests failed - review logs and consider rollback**"
        else:
            summary += "\n**🎉 All tests passed - deployment validated successfully**"
        
        return summary

class StagingSupervisorValidator:
    """Validates supervisor consolidation deployment in staging."""
    
    def __init__(self):
        self.staging_base_url = "https://staging.netrasystems.ai"
        self.staging_ws_url = "wss://api-staging.netrasystems.ai/ws"
        self.results = StagingValidationResults()
    
    async def validate_websocket_connection(self) -> bool:
        """Test WebSocket connection to staging."""
        try:
            print("🔗 Testing WebSocket connection...")
            
            # Test basic connection
            timeout = 10  # seconds
            async with websockets.connect(
                self.staging_ws_url,
                timeout=timeout,
                ping_timeout=5
            ) as websocket:
                
                # Test ping/pong
                await websocket.send(json.dumps({'type': 'ping'}))
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                
                response_data = json.loads(response)
                
                self.results.add_result(
                    "WebSocket Connection",
                    True,
                    f"Connected successfully, ping response: {response_data.get('type', 'unknown')}",
                    {"response_time": f"< {timeout}s"}
                )
                return True
                
        except asyncio.TimeoutError:
            self.results.add_result(
                "WebSocket Connection",
                False,
                "Connection timeout - service may not be responding"
            )
            return False
        except websockets.exceptions.ConnectionClosed as e:
            self.results.add_result(
                "WebSocket Connection",
                False,
                f"Connection closed unexpectedly: {e}"
            )
            return False
        except Exception as e:
            self.results.add_result(
                "WebSocket Connection",
                False,
                f"Connection failed: {str(e)}"
            )
            return False
    
    def validate_service_health(self) -> bool:
        """Test service health endpoint."""
        try:
            print("🩺 Testing service health...")
            
            response = requests.get(
                f"{self.staging_base_url}/health",
                timeout=10
            )
            
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get('status', 'unknown')
                
                # Check for supervisor-specific health indicators
                supervisor_healthy = True
                supervisor_details = "Service health OK"
                
                if 'services' in health_data:
                    agent_status = health_data['services'].get('agent_registry', {})
                    if 'supervisor_count' in agent_status:
                        supervisor_count = agent_status['supervisor_count']
                        if supervisor_count == 1:
                            supervisor_details = f"✅ Consolidated supervisor registered (count: {supervisor_count})"
                        else:
                            supervisor_healthy = False
                            supervisor_details = f"❌ Unexpected supervisor count: {supervisor_count}"
                
                self.results.add_result(
                    "Service Health",
                    status == 'healthy' and supervisor_healthy,
                    supervisor_details,
                    {"status_code": response.status_code, "response_time": f"{response.elapsed.total_seconds():.2f}s"}
                )
                return status == 'healthy' and supervisor_healthy
            else:
                self.results.add_result(
                    "Service Health",
                    False,
                    f"Health check failed with status {response.status_code}",
                    {"status_code": response.status_code}
                )
                return False
                
        except requests.Timeout:
            self.results.add_result(
                "Service Health",
                False,
                "Health check timeout - service not responding"
            )
            return False
        except Exception as e:
            self.results.add_result(
                "Service Health",
                False,
                f"Health check error: {str(e)}"
            )
            return False
    
    def validate_agent_execution(self) -> bool:
        """Test basic agent execution."""
        try:
            print("🤖 Testing agent execution...")
            
            payload = {
                'message': 'Test supervisor consolidation - validate agent execution',
                'user_id': 'staging-validation-test',
                'agent_type': 'supervisor'  # Explicitly request supervisor
            }
            
            response = requests.post(
                f"{self.staging_base_url}/api/agents/execute",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30  # Allow time for agent processing
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for successful execution indicators
                execution_id = result.get('execution_id')
                status = result.get('status', 'unknown')
                
                success = execution_id is not None and status in ['started', 'completed', 'success']
                details = f"Agent execution {status}"
                if execution_id:
                    details += f" (ID: {execution_id[:8]}...)"
                
                self.results.add_result(
                    "Agent Execution",
                    success,
                    details,
                    {
                        "status_code": response.status_code,
                        "response_time": f"{response.elapsed.total_seconds():.2f}s",
                        "execution_status": status
                    }
                )
                return success
            else:
                self.results.add_result(
                    "Agent Execution",
                    False,
                    f"Execution failed with status {response.status_code}: {response.text[:100]}",
                    {"status_code": response.status_code}
                )
                return False
                
        except requests.Timeout:
            self.results.add_result(
                "Agent Execution",
                False,
                "Agent execution timeout - may indicate processing issues"
            )
            return False
        except Exception as e:
            self.results.add_result(
                "Agent Execution",
                False,
                f"Agent execution error: {str(e)}"
            )
            return False
    
    async def validate_websocket_events(self) -> bool:
        """Test that WebSocket events are properly delivered."""
        try:
            print("📡 Testing WebSocket event delivery...")
            
            events_received = []
            expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            
            async with websockets.connect(self.staging_ws_url, timeout=10) as websocket:
                # Send a test message that should trigger agent execution
                test_message = {
                    'type': 'agent_execute',
                    'message': 'Quick test for WebSocket events',
                    'user_id': 'staging-ws-test'
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Listen for events for up to 20 seconds
                timeout_time = time.time() + 20
                
                while time.time() < timeout_time:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2)
                        event_data = json.loads(message)
                        
                        event_type = event_data.get('type')
                        if event_type in expected_events:
                            events_received.append(event_type)
                            print(f"  📨 Received: {event_type}")
                        
                        # If we get agent_completed, we can stop
                        if event_type == 'agent_completed':
                            break
                            
                    except asyncio.TimeoutError:
                        # Continue listening
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        break
            
            received_count = len(events_received)
            expected_count = len(expected_events)
            
            # Success if we received at least 3 of the 5 expected events
            success = received_count >= 3
            
            self.results.add_result(
                "WebSocket Events",
                success,
                f"Received {received_count}/{expected_count} expected events: {', '.join(events_received)}",
                {
                    "events_received": received_count,
                    "events_expected": expected_count,
                    "events_list": events_received
                }
            )
            return success
            
        except Exception as e:
            self.results.add_result(
                "WebSocket Events",
                False,
                f"WebSocket event test error: {str(e)}"
            )
            return False
    
    def validate_logs_for_errors(self) -> bool:
        """Check for critical errors in logs (requires gcloud CLI)."""
        try:
            print("📋 Checking recent logs for errors...")
            
            import subprocess
            
            # Get recent logs from Cloud Run
            result = subprocess.run([
                'gcloud', 'logs', 'read',
                'resource.type=cloud_run_revision',
                '--project', 'netra-staging',
                '--filter', 'resource.labels.service_name="netra-backend-staging"',
                '--limit', '50',
                '--format', 'json'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logs = json.loads(result.stdout) if result.stdout else []
                
                error_count = 0
                critical_count = 0
                supervisor_errors = 0
                
                for log_entry in logs:
                    severity = log_entry.get('severity', '').upper()
                    message = log_entry.get('textPayload', '')
                    
                    if severity in ['ERROR', 'CRITICAL']:
                        if severity == 'CRITICAL':
                            critical_count += 1
                        error_count += 1
                        
                        # Check for supervisor-related errors
                        if any(term in message.lower() for term in ['supervisor', 'agent_registry']):
                            supervisor_errors += 1
                
                success = critical_count == 0 and supervisor_errors == 0
                
                details = f"Found {error_count} errors, {critical_count} critical, {supervisor_errors} supervisor-related"
                if success:
                    details = "No critical errors or supervisor issues found"
                
                self.results.add_result(
                    "Log Analysis",
                    success,
                    details,
                    {
                        "total_errors": error_count,
                        "critical_errors": critical_count,
                        "supervisor_errors": supervisor_errors
                    }
                )
                return success
            else:
                self.results.add_result(
                    "Log Analysis",
                    False,
                    f"Failed to retrieve logs: {result.stderr}"
                )
                return False
                
        except subprocess.TimeoutExpired:
            self.results.add_result(
                "Log Analysis",
                False,
                "Log retrieval timeout - gcloud command took too long"
            )
            return False
        except FileNotFoundError:
            self.results.add_result(
                "Log Analysis",
                False,
                "gcloud CLI not found - skipping log analysis"
            )
            return True  # Don't fail validation if gcloud is not available
        except Exception as e:
            self.results.add_result(
                "Log Analysis",
                False,
                f"Log analysis error: {str(e)}"
            )
            return False
    
    async def run_full_validation(self) -> bool:
        """Run complete validation suite."""
        print("🚀 Starting Staging Deployment Validation for Issue #1177")
        print(f"Target: {self.staging_base_url}")
        print(f"WebSocket: {self.staging_ws_url}")
        print("="*60)
        
        # Run all validation tests
        tests = [
            ("Service Health", lambda: self.validate_service_health()),
            ("WebSocket Connection", lambda: asyncio.run(self.validate_websocket_connection())),
            ("Agent Execution", lambda: self.validate_agent_execution()),
            ("WebSocket Events", lambda: asyncio.run(self.validate_websocket_events())),
            ("Log Analysis", lambda: self.validate_logs_for_errors()),
        ]
        
        overall_success = True
        
        for test_name, test_func in tests:
            try:
                success = test_func()
                if not success:
                    overall_success = False
            except Exception as e:
                self.results.add_result(test_name, False, f"Test execution error: {str(e)}")
                overall_success = False
        
        print("\n" + "="*60)
        print(self.results.generate_summary())
        
        return overall_success

async def main():
    """Main validation function."""
    validator = StagingSupervisorValidator()
    
    try:
        success = await validator.run_full_validation()
        
        # Write results to file for GitHub issue update
        results_file = project_root / "staging_validation_results.md"
        with open(results_file, 'w') as f:
            f.write(validator.results.generate_summary())
        
        print(f"\nResults written to: {results_file}")
        
        if success:
            print("\n🎉 Staging deployment validation SUCCESSFUL")
            print("Ready for final wrap-up confirmation!")
            return 0
        else:
            print("\n❌ Staging deployment validation FAILED")
            print("Review errors and consider rollback if critical")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Validation failed with unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)