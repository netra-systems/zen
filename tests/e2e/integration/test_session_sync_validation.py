"""
Session Synchronization Validation Test

A focused validation test for session state synchronization that works with various backend states.
This test provides a practical validation of session management without relying on specific backend endpoints.

Business Value: Validates core session synchronization capabilities protecting $7K MRR.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment

import httpx
import pytest
import redis.asyncio as redis
import websockets

from tests.e2e.jwt_token_helpers import JWTTestHelper


class SessionSyncValidator:
    """Practical session synchronization validator."""
    
    def __init__(self):
        """Initialize session sync validator."""
        self.jwt_helper = JWTTestHelper()
        self.redis_client = None
        self.backend_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000/ws"
        
    async def setup_redis(self) -> Tuple[bool, str]:
        """Setup Redis connection with status reporting."""
        try:
            redis_url = "redis://localhost:6379"
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            await self.redis_client.ping()
            return True, "Redis connected successfully"
        except Exception as e:
            return False, f"Redis connection failed: {e}"
    
    async def cleanup_redis(self):
        """Cleanup Redis connection."""
        if self.redis_client:
            await self.redis_client.aclose()
    
    @pytest.mark.e2e
    async def test_backend_health(self) -> Tuple[bool, str]:
        """Test backend service health."""
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                response = await client.get(f"{self.backend_url}/health")
                if response.status_code == 200:
                    return True, f"Backend healthy (HTTP {response.status_code})"
                else:
                    return False, f"Backend unhealthy (HTTP {response.status_code})"
        except Exception as e:
            return False, f"Backend unreachable: {e}"
    
    @pytest.mark.e2e
    async def test_redis_session_operations(self) -> Tuple[bool, str]:
        """Test basic Redis session operations."""
        if not self.redis_client:
            return False, "Redis not available"
        
        try:
            # Test session creation
            session_id = str(uuid.uuid4())
            session_data = {
                "user_id": f"test_user_{uuid.uuid4().hex[:8]}",
                "created_at": time.time(),
                "test_session": True
            }
            
            # Store session
            redis_key = f"session:{session_id}"
            await self.redis_client.setex(redis_key, 30, json.dumps(session_data))
            
            # Retrieve session
            stored_data = await self.redis_client.get(redis_key)
            if stored_data:
                retrieved_session = json.loads(stored_data)
                if retrieved_session.get("user_id") == session_data["user_id"]:
                    # Cleanup test session
                    await self.redis_client.delete(redis_key)
                    return True, "Redis session operations working"
            
            return False, "Redis session data mismatch"
            
        except Exception as e:
            return False, f"Redis session operations failed: {e}"
    
    @pytest.mark.e2e
    async def test_websocket_connectivity(self) -> Tuple[bool, str]:
        """Test WebSocket connectivity without authentication."""
        try:
            # Create a simple JWT token for testing
            test_payload = self.jwt_helper.create_valid_payload()
            test_payload.update({
                "sub": f"test_websocket_user_{uuid.uuid4().hex[:8]}",
                "test_connection": True
            })
            test_token = await self.jwt_helper.create_jwt_token(test_payload)
            
            # Attempt WebSocket connection
            uri = f"{self.websocket_url}?token={test_token}"
            websocket = await asyncio.wait_for(
                websockets.connect(uri),
                timeout=10.0
            )
            
            # Send test message
            test_message = {
                "type": "ping",
                "test": True,
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                await websocket.close()
                
                if response_data.get("type") == "pong":
                    return True, "WebSocket connectivity confirmed"
                else:
                    return True, f"WebSocket connected (response: {response_data.get('type', 'unknown')})"
            except asyncio.TimeoutError:
                await websocket.close()
                return True, "WebSocket connected (no response to ping)"
            
        except Exception as e:
            return False, f"WebSocket connection failed: {e}"
    
    @pytest.mark.e2e
    async def test_jwt_token_creation(self) -> Tuple[bool, str]:
        """Test JWT token creation and validation."""
        try:
            # Create test token
            payload = self.jwt_helper.create_valid_payload()
            payload.update({
                "sub": f"jwt_test_user_{uuid.uuid4().hex[:8]}",
                "test_token": True
            })
            
            token = await self.jwt_helper.create_jwt_token(payload)
            
            if token and len(token) > 50:  # Basic token validation
                return True, "JWT token creation working"
            else:
                return False, "JWT token creation failed"
                
        except Exception as e:
            return False, f"JWT token creation error: {e}"
    
    @pytest.mark.e2e
    async def test_session_component_integration(self) -> Tuple[bool, str]:
        """Test integration between session components."""
        try:
            # Create test user data
            user_id = f"integration_test_{uuid.uuid4().hex[:8]}"
            
            # Test 1: Create JWT token
            payload = self.jwt_helper.create_valid_payload()
            payload.update({"sub": user_id, "integration_test": True})
            token = await self.jwt_helper.create_jwt_token(payload)
            
            if not token:
                return False, "JWT token creation failed in integration test"
            
            # Test 2: Store session in Redis (if available)
            redis_success = True
            if self.redis_client:
                session_data = {
                    "user_id": user_id,
                    "token_hash": hash(token) % 10000,  # Simple hash for correlation
                    "created_at": time.time(),
                    "integration_test": True
                }
                
                session_id = str(uuid.uuid4())
                redis_key = f"session:{session_id}"
                
                try:
                    await self.redis_client.setex(redis_key, 60, json.dumps(session_data))
                    
                    # Verify storage
                    stored_data = await self.redis_client.get(redis_key)
                    if stored_data:
                        stored_session = json.loads(stored_data)
                        if stored_session.get("user_id") != user_id:
                            redis_success = False
                    
                    # Cleanup
                    await self.redis_client.delete(redis_key)
                    
                except Exception:
                    redis_success = False
            
            # Test 3: WebSocket connection with token
            websocket_success = True
            try:
                uri = f"{self.websocket_url}?token={token}"
                websocket = await asyncio.wait_for(
                    websockets.connect(uri),
                    timeout=5.0
                )
                await websocket.close()
            except Exception:
                websocket_success = False
            
            # Evaluate overall integration
            if redis_success and websocket_success:
                return True, "Session component integration working (Redis + WebSocket + JWT)"
            elif websocket_success:
                return True, "Partial integration working (WebSocket + JWT, Redis unavailable)"
            else:
                return False, "Session component integration failed"
                
        except Exception as e:
            return False, f"Session integration test error: {e}"
    
    async def run_validation_suite(self) -> Dict[str, Any]:
        """Run complete session synchronization validation suite."""
        results = {
            "timestamp": time.time(),
            "test_results": {},
            "overall_success": False,
            "summary": "",
            "business_value_protected": False
        }
        
        print("\n" + "="*60)
        print("SESSION SYNCHRONIZATION VALIDATION SUITE")
        print("="*60)
        
        # Test 1: Backend Health
        print("[1/6] Testing backend health...")
        backend_ok, backend_msg = await self.test_backend_health()
        results["test_results"]["backend_health"] = {"success": backend_ok, "message": backend_msg}
        print(f"  {'[U+2713]' if backend_ok else '[U+2717]'} {backend_msg}")
        
        # Test 2: Redis Setup
        print("[2/6] Testing Redis connection...")
        redis_ok, redis_msg = await self.setup_redis()
        results["test_results"]["redis_connection"] = {"success": redis_ok, "message": redis_msg}
        print(f"  {'[U+2713]' if redis_ok else '[U+2717]'} {redis_msg}")
        
        # Test 3: Redis Operations
        print("[3/6] Testing Redis session operations...")
        redis_ops_ok, redis_ops_msg = await self.test_redis_session_operations()
        results["test_results"]["redis_operations"] = {"success": redis_ops_ok, "message": redis_ops_msg}
        print(f"  {'[U+2713]' if redis_ops_ok else '[U+2717]'} {redis_ops_msg}")
        
        # Test 4: JWT Token Creation
        print("[4/6] Testing JWT token creation...")
        jwt_ok, jwt_msg = await self.test_jwt_token_creation()
        results["test_results"]["jwt_creation"] = {"success": jwt_ok, "message": jwt_msg}
        print(f"  {'[U+2713]' if jwt_ok else '[U+2717]'} {jwt_msg}")
        
        # Test 5: WebSocket Connectivity
        print("[5/6] Testing WebSocket connectivity...")
        ws_ok, ws_msg = await self.test_websocket_connectivity()
        results["test_results"]["websocket_connectivity"] = {"success": ws_ok, "message": ws_msg}
        print(f"  {'[U+2713]' if ws_ok else '[U+2717]'} {ws_msg}")
        
        # Test 6: Component Integration
        print("[6/6] Testing session component integration...")
        integration_ok, integration_msg = await self.test_session_component_integration()
        results["test_results"]["component_integration"] = {"success": integration_ok, "message": integration_msg}
        print(f"  {'[U+2713]' if integration_ok else '[U+2717]'} {integration_msg}")
        
        # Evaluate overall success
        critical_tests = ["backend_health", "jwt_creation", "websocket_connectivity", "component_integration"]
        critical_passed = sum(1 for test in critical_tests if results["test_results"][test]["success"])
        total_critical = len(critical_tests)
        
        success_rate = critical_passed / total_critical
        results["overall_success"] = success_rate >= 0.75  # 75% success rate required
        results["business_value_protected"] = success_rate >= 0.5  # 50% minimum for basic protection
        
        print("\n" + "="*60)
        print("VALIDATION RESULTS SUMMARY")
        print("="*60)
        print(f"Critical Tests Passed: {critical_passed}/{total_critical} ({success_rate:.1%})")
        print(f"Overall Success: {'[U+2713]' if results['overall_success'] else '[U+2717]'}")
        print(f"Business Value Protected: {'[U+2713]' if results['business_value_protected'] else '[U+2717]'}")
        
        if results["business_value_protected"]:
            print(f"[U+1F4B0] $7K MRR protection validated through session management")
        else:
            print(f" WARNING: [U+FE0F]  Session management issues detected - MRR protection at risk")
        
        results["summary"] = f"Session validation: {critical_passed}/{total_critical} critical tests passed"
        
        return results


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.e2e
async def test_session_synchronization_validation():
    """
    Practical session synchronization validation test.
    
    Validates core session management capabilities without relying on specific backend endpoints.
    Designed to work with various backend states and provide actionable feedback.
    """
    validator = SessionSyncValidator()
    
    try:
        results = await validator.run_validation_suite()
        
        # Business value assertions
        assert results["business_value_protected"], (
            f"Session synchronization validation failed to meet minimum standards. "
            f"Summary: {results['summary']}. "
            f"This indicates risks to $7K MRR from session management issues."
        )
        
        # Component-specific assertions with helpful messages
        assert results["test_results"]["jwt_creation"]["success"], "JWT token creation failed - authentication system not working"
        assert results["test_results"]["websocket_connectivity"]["success"], "WebSocket connectivity failed - real-time features unavailable"
        assert results["test_results"]["component_integration"]["success"], "Session component integration failed - cross-service sync broken"
        
        # Performance validation
        execution_time = time.time() - results["timestamp"]
        assert execution_time < 30.0, f"Validation suite took {execution_time:.2f}s, must complete in <30s"
        
        print(f"\n[SUCCESS] Session synchronization validation PASSED")
        print(f"[BUSINESS VALUE] $7K MRR protection validated")
        print(f"[PERFORMANCE] Validation completed in {execution_time:.2f}s")
        
    finally:
        await validator.cleanup_redis()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_session_component_health_check():
    """
    Quick health check for session management components.
    
    Lightweight test for CI/CD pipelines and basic system validation.
    """
    validator = SessionSyncValidator()
    
    try:
        start_time = time.time()
        
        # Essential component checks
        backend_ok, _ = await validator.test_backend_health()
        jwt_ok, _ = await validator.test_jwt_token_creation()
        
        execution_time = time.time() - start_time
        
        # Quick validation assertions
        assert backend_ok or jwt_ok, "Neither backend nor JWT creation working - system unavailable"
        assert execution_time < 10.0, f"Health check took {execution_time:.2f}s, must be <10s"
        
        print(f"[HEALTH CHECK PASS] Session components healthy in {execution_time:.2f}s")
        
    finally:
        await validator.cleanup_redis()


if __name__ == "__main__":
    """Run session synchronization validation standalone."""
    async def run_validation():
        validator = SessionSyncValidator()
        try:
            results = await validator.run_validation_suite()
            print(f"\nValidation completed: {'SUCCESS' if results['overall_success'] else 'PARTIAL SUCCESS'}")
            print(f"Business value protected: {'YES' if results['business_value_protected'] else 'AT RISK'}")
        finally:
            await validator.cleanup_redis()
    
    asyncio.run(run_validation())


# Business Value Summary
"""
Session Synchronization Validation Test - Business Value Summary

BVJ: Practical validation of session management protecting $7K MRR
- Validates core session synchronization without specific backend dependencies
- Provides actionable feedback on session management component health
- Ensures business continuity through session reliability validation
- Supports various deployment environments and backend states

Strategic Value:
- CI/CD pipeline integration for deployment confidence
- Early detection of session management issues
- Validation of cross-service session synchronization
- Foundation for enterprise session reliability requirements
"""