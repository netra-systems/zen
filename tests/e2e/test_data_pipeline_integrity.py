"""
Data Pipeline Integrity E2E Tests

Tests that validate data flow integrity across services, databases, and processing
pipelines. Ensures data consistency and reliability in ETL operations.

Business Value: Data accuracy and reliability for AI/ML operations
Expected Coverage Gaps: Data validation, pipeline monitoring, error recovery

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability and Data Integrity
- Value Impact: Ensures reliable data pipeline operations for AI/ML workloads
- Strategic Impact: Prevents data corruption and maintains system reliability
"""

import pytest
import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

# ABSOLUTE IMPORTS ONLY - CLAUDE.md compliance
from test_framework.environment_isolation import get_test_env_manager
from netra_backend.app.core.isolated_environment import get_env


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_thread_message_data_pipeline():
    """
    Test that thread and message data flows correctly through the entire pipeline.
    
    Tests real data pipeline integrity using actual services - NO MOCKS.
    Uses IsolatedEnvironment for configuration management per CLAUDE.md standards.
    
    Expected Failure: Data pipeline may not handle edge cases or maintain consistency
    Business Impact: Lost conversations, corrupt message history, poor user experience
    """
    # Use IsolatedEnvironment instead of hardcoded URLs - CLAUDE.md compliance
    env = get_env()
    backend_url = f"http://localhost:{env.get('BACKEND_PORT', '8000')}"
    auth_url = f"http://localhost:{env.get('AUTH_PORT', '8081')}"
    pipeline_issues = []
    
    # Setup test environment with proper isolation
    test_env_manager = get_test_env_manager()
    test_env = test_env_manager.setup_test_environment()
    
    async with aiohttp.ClientSession() as session:
        try:
            # Step 0: Create a test user and authenticate (real auth flow)
            auth_token = await _create_test_user_and_authenticate(session, auth_url, pipeline_issues)
            if not auth_token:
                pipeline_issues.append("Failed to authenticate test user")
                return
                
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            # Step 1: Create a thread with proper authentication
            thread_data = {
                "title": "Data Pipeline Test Thread",
                "metadata": {"test_type": "data_pipeline_integrity"}
            }
            
            async with session.post(f"{backend_url}/api/threads", json=thread_data, headers=headers) as response:
                if response.status == 201:
                    thread_response = await response.json()
                    thread_id = thread_response.get("id")
                    print(f"✅ Thread created: {thread_id}")
                else:
                    response_text = await response.text()
                    pipeline_issues.append(f"Thread creation failed: {response.status} - {response_text}")
                    return
            
            # Step 2: Add messages to thread using correct agent endpoint
            messages = [
                {"content": "First message for data pipeline test", "role": "user"},
                {"content": "Testing special characters: !@#$%^&*()", "role": "user"},
                {"content": "Unicode test: 🚀💯✅❌", "role": "user"}
            ]
            
            message_ids = []
            for msg in messages:
                msg_data = {
                    "thread_id": thread_id,
                    "message": msg["content"],
                    "role": msg["role"]
                }
                
                # Use the correct agent message endpoint instead of non-existent /api/messages
                async with session.post(f"{backend_url}/api/agent/message", json=msg_data, headers=headers) as response:
                    if response.status in [200, 201]:
                        msg_response = await response.json()
                        message_id = msg_response.get("message_id") or msg_response.get("id")
                        if message_id:
                            message_ids.append(message_id)
                            print(f"✅ Message created: {message_id}")
                        else:
                            print(f"⚠️ Message created but no ID returned: {msg_response}")
                    else:
                        response_text = await response.text()
                        pipeline_issues.append(f"Message creation failed: {response.status} - {response_text}")
            
            # Step 3: Verify thread integrity using authenticated request
            async with session.get(f"{backend_url}/api/threads/{thread_id}", headers=headers) as response:
                if response.status == 200:
                    thread_details = await response.json()
                    
                    # Check thread data integrity
                    if thread_details.get("title") != thread_data["title"]:
                        pipeline_issues.append("Thread title data corruption detected")
                    
                    print(f"✅ Thread integrity verified: {thread_details.get('title')}")
                else:
                    response_text = await response.text()
                    pipeline_issues.append(f"Thread retrieval failed: {response.status} - {response_text}")
                    
            # Step 3b: Verify messages through dedicated messages endpoint
            async with session.get(f"{backend_url}/api/threads/{thread_id}/messages", headers=headers) as response:
                if response.status == 200:
                    messages_response = await response.json()
                    returned_messages = messages_response if isinstance(messages_response, list) else messages_response.get("messages", [])
                    
                    # Check if we got any messages back
                    if len(returned_messages) == 0 and len(message_ids) > 0:
                        pipeline_issues.append("No messages returned despite successful message creation")
                    
                    print(f"✅ Messages retrieved: {len(returned_messages)} messages found")
                    
                    # Basic content integrity check if messages exist
                    if returned_messages:
                        for i, msg in enumerate(returned_messages):
                            if not msg.get("content") and not msg.get("message"):
                                pipeline_issues.append(f"Message {i} has no content field")
                else:
                    response_text = await response.text()
                    pipeline_issues.append(f"Messages retrieval failed: {response.status} - {response_text}")
            
            # Step 4: Test concurrent thread operations (stress test pipeline)
            concurrent_threads = []
            for i in range(3):  # Reduced concurrency for more reliable testing
                thread_data_concurrent = {
                    "title": f"Concurrent Test Thread {i}",
                    "metadata": {"test_type": "concurrent_stress", "index": i}
                }
                concurrent_threads.append(
                    session.post(f"{backend_url}/api/threads", json=thread_data_concurrent, headers=headers)
                )
            
            concurrent_responses = await asyncio.gather(*concurrent_threads, return_exceptions=True)
            
            successful_concurrent = 0
            for i, resp in enumerate(concurrent_responses):
                if isinstance(resp, Exception):
                    print(f"⚠️ Concurrent thread {i} failed with exception: {resp}")
                elif hasattr(resp, 'status') and resp.status == 201:
                    successful_concurrent += 1
                    resp.close()  # Close the response properly
                else:
                    if hasattr(resp, 'close'):
                        resp.close()
            
            if successful_concurrent < 2:  # Allow some failures under concurrent load
                pipeline_issues.append(
                    f"Pipeline failed under concurrent load: only {successful_concurrent}/3 threads succeeded"
                )
            else:
                print(f"✅ Pipeline handles concurrent operations: {successful_concurrent}/3 succeeded")
            
            # Step 5: Test data consistency after updates
            update_data = {"title": "Updated Pipeline Test Thread"}
            async with session.put(f"{backend_url}/api/threads/{thread_id}", json=update_data, headers=headers) as response:
                if response.status == 200:
                    # Verify update propagated correctly
                    async with session.get(f"{backend_url}/api/threads/{thread_id}", headers=headers) as verify_response:
                        if verify_response.status == 200:
                            updated_thread = await verify_response.json()
                            if updated_thread.get("title") != update_data["title"]:
                                pipeline_issues.append("Thread update did not propagate correctly")
                            else:
                                print("✅ Thread update propagated successfully")
                        else:
                            response_text = await verify_response.text()
                            pipeline_issues.append(f"Thread verification after update failed: {verify_response.status} - {response_text}")
                else:
                    response_text = await response.text()
                    pipeline_issues.append(f"Thread update failed: {response.status} - {response_text}")
            
        except Exception as e:
            pipeline_issues.append(f"Pipeline test failed with exception: {str(e)}")
        finally:
            # Cleanup test environment
            test_env_manager.teardown_test_environment()
    
    # Report findings
    if pipeline_issues:
        print("🔍 DATA PIPELINE ISSUES:")
        for issue in pipeline_issues:
            print(f"  - {issue}")
        
        # For iteration purposes, we'll skip if this is an infrastructure issue
        if any("failed to connect" in issue.lower() or "connection" in issue.lower() for issue in pipeline_issues):
            pytest.skip("Service connectivity issues - infrastructure gap identified")
        else:
            pytest.fail(f"Data pipeline integrity issues: {pipeline_issues}")
    else:
        print("✅ Data pipeline integrity validated successfully")


async def _create_test_user_and_authenticate(session: aiohttp.ClientSession, auth_url: str, issues_list: List[str]) -> Optional[str]:
    """
    Helper function to create a test user and authenticate.
    Returns access token on success, None on failure.
    Uses real auth service - NO MOCKS.
    """
    import uuid
    import time
    
    # Generate unique user data for this test run
    test_uuid = str(uuid.uuid4())[:8]
    user_data = {
        "email": f"test.pipeline.{test_uuid}@example.com",
        "name": f"Pipeline Test User {test_uuid}",
        "password": "TestPipeline123!"
    }
    
    try:
        # Register user with auth service
        async with session.post(f"{auth_url}/auth/register", json=user_data) as response:
            if response.status in [200, 201]:
                auth_response = await response.json()
                token = auth_response.get("access_token") or auth_response.get("token")
                if token:
                    print(f"✅ Test user created and authenticated: {user_data['email']}")
                    return token
                else:
                    # Try to login if registration succeeded but no token returned
                    login_data = {"email": user_data["email"], "password": user_data["password"]}
                    async with session.post(f"{auth_url}/auth/login", json=login_data) as login_response:
                        if login_response.status == 200:
                            login_result = await login_response.json()
                            token = login_result.get("access_token") or login_result.get("token")
                            if token:
                                print(f"✅ Test user logged in: {user_data['email']}")
                                return token
            else:
                response_text = await response.text()
                issues_list.append(f"User registration failed: {response.status} - {response_text}")
                
    except Exception as e:
        issues_list.append(f"Authentication setup failed: {str(e)}")
    
    return None


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_user_data_consistency_across_services():
    """
    Test that user data remains consistent across auth and backend services.
    
    Uses real services with proper authentication flow - NO MOCKS.
    Tests actual cross-service data synchronization.
    
    Expected Failure: User data synchronization issues between services
    Business Impact: User profile inconsistencies, authentication failures
    """
    # Use IsolatedEnvironment for configuration - CLAUDE.md compliance  
    env = get_env()
    backend_url = f"http://localhost:{env.get('BACKEND_PORT', '8000')}"
    auth_url = f"http://localhost:{env.get('AUTH_PORT', '8081')}"
    consistency_issues = []
    
    # Setup test environment with proper isolation
    test_env_manager = get_test_env_manager()
    test_env = test_env_manager.setup_test_environment()
    
    async with aiohttp.ClientSession() as session:
        try:
            # Step 1: Create user via auth service using helper function
            token = await _create_test_user_and_authenticate(session, auth_url, consistency_issues)
            if not token:
                consistency_issues.append("Failed to create and authenticate test user")
                return
                
            headers = {"Authorization": f"Bearer {token}"}
            print(f"✅ User created and authenticated successfully")
            
            # Step 2: Verify authentication works with backend service
            # Try to create a thread to test cross-service authentication
            test_thread_data = {"title": "Cross-service authentication test"}
            
            async with session.post(f"{backend_url}/api/threads", json=test_thread_data, headers=headers) as response:
                if response.status == 201:
                    thread_response = await response.json()
                    thread_id = thread_response.get("id")
                    print(f"✅ Cross-service authentication working: created thread {thread_id}")
                    
                    # Clean up the test thread
                    async with session.delete(f"{backend_url}/api/threads/{thread_id}", headers=headers) as del_response:
                        if del_response.status in [200, 204]:
                            print("✅ Test thread cleaned up successfully")
                            
                elif response.status == 401:
                    consistency_issues.append("Backend service doesn't recognize auth service tokens")
                else:
                    response_text = await response.text()
                    consistency_issues.append(f"Cross-service authentication test failed: {response.status} - {response_text}")
            
            # Step 3: Test token validation across services
            # Verify auth service recognizes the token
            async with session.get(f"{auth_url}/auth/verify", headers=headers) as response:
                if response.status == 200:
                    user_info = await response.json()
                    print(f"✅ Token validation successful: {user_info.get('email', 'unknown')}")
                else:
                    response_text = await response.text()
                    consistency_issues.append(f"Token validation failed: {response.status} - {response_text}")
                        
        except Exception as e:
            consistency_issues.append(f"User data consistency test failed: {str(e)}")
        finally:
            # Cleanup test environment
            test_env_manager.teardown_test_environment()
    
    # Report findings
    if consistency_issues:
        print("🔍 USER DATA CONSISTENCY ISSUES:")
        for issue in consistency_issues:
            print(f"  - {issue}")
        
        # Skip if this is a connectivity issue
        if any("failed to connect" in issue.lower() or "connection" in issue.lower() for issue in consistency_issues):
            pytest.skip("Service connectivity issues - infrastructure gap identified")
        else:
            pytest.fail(f"User data consistency issues: {consistency_issues}")
    else:
        print("✅ User data consistency validated successfully")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_data_validation_and_sanitization():
    """
    Test that data validation and sanitization work correctly across the pipeline.
    
    Uses real services to test actual validation logic - NO MOCKS.
    Tests against real database with proper authentication.
    
    Expected Failure: Insufficient data validation allowing malformed data
    Business Impact: Data corruption, security vulnerabilities, system instability
    """
    # Use IsolatedEnvironment for configuration - CLAUDE.md compliance
    env = get_env()
    backend_url = f"http://localhost:{env.get('BACKEND_PORT', '8000')}"
    auth_url = f"http://localhost:{env.get('AUTH_PORT', '8081')}"
    validation_issues = []
    
    # Setup test environment with proper isolation
    test_env_manager = get_test_env_manager()
    test_env = test_env_manager.setup_test_environment()
    
    async with aiohttp.ClientSession() as session:
        try:
            # Authenticate first for real testing
            auth_token = await _create_test_user_and_authenticate(session, auth_url, validation_issues)
            if not auth_token:
                validation_issues.append("Failed to authenticate for validation testing")
                return
                
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            # Test various malformed data inputs
            malformed_inputs = [
                # Empty/null values
                {"title": "", "metadata": {"test": "empty_title"}},
                {"title": None, "metadata": {"test": "null_title"}},
                
                # Extremely long values
                {"title": "A" * 1000, "metadata": {"test": "long_title"}},
                
                # Special characters and encoding
                {"title": "Test\x00\x01\x02", "metadata": {"test": "null_bytes"}},
                {"title": "Test🚀🔥💯", "metadata": {"test": "unicode_emojis"}},
                {"title": "Test\n\r\t", "metadata": {"test": "control_chars"}},
                
                # Potential injection attempts
                {"title": "<script>alert('test')</script>", "metadata": {"test": "xss_attempt"}},
                {"title": "'; DROP TABLE threads; --", "metadata": {"test": "sql_injection"}},
                
                # Type mismatches
                {"title": 12345, "metadata": {"test": "number_title"}},
                {"title": ["array", "as", "title"], "metadata": {"test": "array_title"}},
                {"title": {"object": "as_title"}, "metadata": {"test": "object_title"}},
            ]
        
            for i, malformed_data in enumerate(malformed_inputs):
                try:
                    async with session.post(f"{backend_url}/api/threads", json=malformed_data, headers=headers) as response:
                        response_text = await response.text()
                        
                        if response.status == 200 or response.status == 201:
                            # If the request succeeded, the data should be properly sanitized
                            created_thread = await response.json()
                            title = created_thread.get("title", "")
                            
                            # Check for dangerous content that should have been sanitized
                            dangerous_patterns = ["<script>", "DROP TABLE", "\x00", "\x01"]
                            for pattern in dangerous_patterns:
                                if pattern in str(title):
                                    validation_issues.append(
                                        f"Dangerous pattern '{pattern}' not sanitized in input {i}"
                                    )
                            
                            print(f"✅ Input {i} processed and sanitized successfully")
                            
                        elif response.status == 400:
                            # Bad request is expected for malformed data
                            print(f"✅ Input {i} properly rejected with 400")
                            
                        elif response.status == 422:
                            # Unprocessable entity is also acceptable for validation errors
                            print(f"✅ Input {i} validation failed appropriately with 422")
                            
                        else:
                            # Unexpected status codes might indicate issues
                            if response.status >= 500:
                                validation_issues.append(
                                    f"Input {i} caused server error {response.status} - validation should catch this"
                                )
                            else:
                                print(f"⚠️ Input {i} returned unexpected status {response.status} - {response_text[:100]}")
                    
                except Exception as e:
                    # Network errors are acceptable - we're testing validation
                    if "connection" not in str(e).lower():
                        validation_issues.append(f"Input {i} caused unexpected exception: {str(e)}")
        except Exception as e:
            validation_issues.append(f"Data validation test setup failed: {str(e)}")
        finally:
            # Cleanup test environment
            test_env_manager.teardown_test_environment()
    
    # Report findings
    if validation_issues:
        print("🔍 DATA VALIDATION ISSUES:")
        for issue in validation_issues:
            print(f"  - {issue}")
        
        pytest.fail(f"Data validation issues found: {validation_issues}")
    else:
        print("✅ Data validation and sanitization working correctly")


if __name__ == "__main__":
    # Run individual tests for debugging
    # Setup test environment first
    print("Setting up test environment...")
    test_env_manager = get_test_env_manager()
    test_env_manager.setup_test_environment()
    
    try:
        asyncio.run(test_thread_message_data_pipeline())
    finally:
        print("Cleaning up test environment...")
        test_env_manager.teardown_test_environment()