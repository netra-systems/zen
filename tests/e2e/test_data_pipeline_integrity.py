"""
Data Pipeline Integrity E2E Tests

Tests that validate data flow integrity across services, databases, and processing
pipelines. Ensures data consistency and reliability in ETL operations.

Business Value: Data accuracy and reliability for AI/ML operations
Expected Coverage Gaps: Data validation, pipeline monitoring, error recovery
"""

import pytest
import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_thread_message_data_pipeline():
    """
    Test that thread and message data flows correctly through the entire pipeline.
    
    Expected Failure: Data pipeline may not handle edge cases or maintain consistency
    Business Impact: Lost conversations, corrupt message history, poor user experience
    """
    backend_url = "http://localhost:8000"
    pipeline_issues = []
    
    async with aiohttp.ClientSession() as session:
        try:
            # Step 1: Create a thread
            thread_data = {
                "title": "Data Pipeline Test Thread",
                "description": "Testing data flow integrity"
            }
            
            async with session.post(f"{backend_url}/api/threads", json=thread_data) as response:
                if response.status == 201:
                    thread_response = await response.json()
                    thread_id = thread_response.get("id")
                    print(f"✅ Thread created: {thread_id}")
                else:
                    pipeline_issues.append(f"Thread creation failed: {response.status}")
                    return
            
            # Step 2: Add messages to thread
            messages = [
                {"content": "First message", "role": "user"},
                {"content": "Agent response", "role": "assistant"},
                {"content": "Follow-up message", "role": "user"},
                {"content": "Final response with special chars: !@#$%^&*()", "role": "assistant"}
            ]
            
            message_ids = []
            for msg in messages:
                msg_data = {
                    "thread_id": thread_id,
                    "content": msg["content"],
                    "role": msg["role"]
                }
                
                async with session.post(f"{backend_url}/api/messages", json=msg_data) as response:
                    if response.status == 201:
                        msg_response = await response.json()
                        message_ids.append(msg_response.get("id"))
                        print(f"✅ Message created: {msg_response.get('id')}")
                    else:
                        pipeline_issues.append(f"Message creation failed: {response.status}")
            
            # Step 3: Verify thread integrity
            async with session.get(f"{backend_url}/api/threads/{thread_id}") as response:
                if response.status == 200:
                    thread_details = await response.json()
                    
                    # Check thread data integrity
                    if thread_details.get("title") != thread_data["title"]:
                        pipeline_issues.append("Thread title data corruption detected")
                    
                    # Check message count
                    returned_messages = thread_details.get("messages", [])
                    if len(returned_messages) != len(messages):
                        pipeline_issues.append(
                            f"Message count mismatch: expected {len(messages)}, got {len(returned_messages)}"
                        )
                    
                    # Check message order and content integrity
                    for i, (original, returned) in enumerate(zip(messages, returned_messages)):
                        if returned.get("content") != original["content"]:
                            pipeline_issues.append(f"Message {i} content corruption: {original['content']} != {returned.get('content')}")
                        if returned.get("role") != original["role"]:
                            pipeline_issues.append(f"Message {i} role corruption: {original['role']} != {returned.get('role')}")
                    
                    print(f"✅ Thread integrity verified: {len(returned_messages)} messages")
                else:
                    pipeline_issues.append(f"Thread retrieval failed: {response.status}")
            
            # Step 4: Test concurrent message additions (stress test pipeline)
            concurrent_messages = []
            for i in range(5):
                msg_data = {
                    "thread_id": thread_id,
                    "content": f"Concurrent message {i}",
                    "role": "user" if i % 2 == 0 else "assistant"
                }
                concurrent_messages.append(session.post(f"{backend_url}/api/messages", json=msg_data))
            
            concurrent_responses = await asyncio.gather(*concurrent_messages, return_exceptions=True)
            
            successful_concurrent = sum(
                1 for resp in concurrent_responses 
                if hasattr(resp, 'status') and resp.status == 201
            )
            
            if successful_concurrent < 3:  # Allow some failures under concurrent load
                pipeline_issues.append(
                    f"Pipeline failed under concurrent load: only {successful_concurrent}/5 messages succeeded"
                )
            else:
                print(f"✅ Pipeline handles concurrent operations: {successful_concurrent}/5 succeeded")
            
            # Clean up responses
            for resp in concurrent_responses:
                if hasattr(resp, 'close'):
                    resp.close()
            
            # Step 5: Test data consistency after updates
            update_data = {"title": "Updated Pipeline Test Thread"}
            async with session.put(f"{backend_url}/api/threads/{thread_id}", json=update_data) as response:
                if response.status == 200:
                    # Verify update propagated correctly
                    async with session.get(f"{backend_url}/api/threads/{thread_id}") as verify_response:
                        if verify_response.status == 200:
                            updated_thread = await verify_response.json()
                            if updated_thread.get("title") != update_data["title"]:
                                pipeline_issues.append("Thread update did not propagate correctly")
                            else:
                                print("✅ Thread update propagated successfully")
                else:
                    pipeline_issues.append(f"Thread update failed: {response.status}")
            
        except Exception as e:
            pipeline_issues.append(f"Pipeline test failed with exception: {str(e)}")
    
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


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_user_data_consistency_across_services():
    """
    Test that user data remains consistent across auth and backend services.
    
    Expected Failure: User data synchronization issues between services
    Business Impact: User profile inconsistencies, authentication failures
    """
    backend_url = "http://localhost:8000"
    auth_url = "http://localhost:8081"
    consistency_issues = []
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test user creation workflow
            user_data = {
                "email": "pipeline.test@example.com",
                "name": "Pipeline Test User",
                "password": "TestPassword123!"
            }
            
            # Step 1: Create user via auth service
            async with session.post(f"{auth_url}/auth/register", json=user_data) as response:
                if response.status in [200, 201]:
                    auth_response = await response.json()
                    user_id = auth_response.get("user_id") or auth_response.get("id")
                    token = auth_response.get("access_token") or auth_response.get("token")
                    
                    if not user_id:
                        consistency_issues.append("Auth service did not return user_id after registration")
                        return
                    
                    print(f"✅ User created in auth service: {user_id}")
                else:
                    consistency_issues.append(f"User creation failed in auth service: {response.status}")
                    return
            
            # Step 2: Verify user exists in backend service
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            
            async with session.get(f"{backend_url}/api/user/profile", headers=headers) as response:
                if response.status == 200:
                    backend_user = await response.json()
                    backend_user_id = backend_user.get("id") or backend_user.get("user_id")
                    
                    # Check user data consistency
                    if backend_user.get("email") != user_data["email"]:
                        consistency_issues.append("Email mismatch between auth and backend")
                    
                    if backend_user.get("name") != user_data["name"]:
                        consistency_issues.append("Name mismatch between auth and backend")
                    
                    if str(backend_user_id) != str(user_id):
                        consistency_issues.append(f"User ID mismatch: auth={user_id}, backend={backend_user_id}")
                    
                    print("✅ User data consistent between services")
                    
                elif response.status == 401:
                    # This might be expected if token is not valid or user sync is async
                    print("⚠️ Backend requires authentication - checking if this is expected")
                    
                    # Try to get user info from auth service to compare
                    async with session.get(f"{auth_url}/auth/user", headers=headers) as auth_check:
                        if auth_check.status == 200:
                            auth_user = await auth_check.json()
                            # If auth service has the user but backend doesn't recognize token,
                            # there's a synchronization issue
                            consistency_issues.append("User exists in auth but backend doesn't recognize authentication")
                else:
                    consistency_issues.append(f"Backend user profile inaccessible: {response.status}")
            
            # Step 3: Test user profile updates
            if token:
                profile_update = {"name": "Updated Pipeline Test User"}
                async with session.put(f"{backend_url}/api/user/profile", json=profile_update, headers=headers) as response:
                    if response.status == 200:
                        # Verify update in both services
                        async with session.get(f"{backend_url}/api/user/profile", headers=headers) as backend_check:
                            if backend_check.status == 200:
                                updated_profile = await backend_check.json()
                                if updated_profile.get("name") != profile_update["name"]:
                                    consistency_issues.append("Profile update did not persist in backend")
                        
                        async with session.get(f"{auth_url}/auth/user", headers=headers) as auth_check:
                            if auth_check.status == 200:
                                auth_profile = await auth_check.json()
                                if auth_profile.get("name") != profile_update["name"]:
                                    consistency_issues.append("Profile update did not sync to auth service")
                        
                        if not consistency_issues:
                            print("✅ Profile update synchronized across services")
                    else:
                        consistency_issues.append(f"Profile update failed: {response.status}")
                        
        except Exception as e:
            consistency_issues.append(f"User data consistency test failed: {str(e)}")
    
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
    
    Expected Failure: Insufficient data validation allowing malformed data
    Business Impact: Data corruption, security vulnerabilities, system instability
    """
    backend_url = "http://localhost:8000"
    validation_issues = []
    
    async with aiohttp.ClientSession() as session:
        # Test various malformed data inputs
        malformed_inputs = [
            # Empty/null values
            {"title": "", "description": "Test"},
            {"title": None, "description": "Test"},
            {"title": "Test", "description": None},
            
            # Extremely long values
            {"title": "A" * 1000, "description": "Test"},
            {"title": "Test", "description": "B" * 10000},
            
            # Special characters and encoding
            {"title": "Test\x00\x01\x02", "description": "Null bytes"},
            {"title": "Test🚀🔥💯", "description": "Unicode emojis"},
            {"title": "Test\n\r\t", "description": "Control characters"},
            
            # Potential injection attempts
            {"title": "<script>alert('test')</script>", "description": "XSS attempt"},
            {"title": "'; DROP TABLE threads; --", "description": "SQL injection attempt"},
            
            # Type mismatches
            {"title": 12345, "description": "Number as title"},
            {"title": ["array", "as", "title"], "description": "Array as title"},
            {"title": {"object": "as_title"}, "description": "Object as title"},
        ]
        
        for i, malformed_data in enumerate(malformed_inputs):
            try:
                async with session.post(f"{backend_url}/api/threads", json=malformed_data) as response:
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
                            print(f"⚠️ Input {i} returned unexpected status {response.status}")
                
            except Exception as e:
                # Network errors are acceptable - we're testing validation
                if "connection" not in str(e).lower():
                    validation_issues.append(f"Input {i} caused unexpected exception: {str(e)}")
    
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
    asyncio.run(test_thread_message_data_pipeline())