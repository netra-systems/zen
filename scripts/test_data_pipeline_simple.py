#!/usr/bin/env python3
"""
Simple Data Pipeline Integrity Test
Tests the actual running services without test framework overhead
"""
import asyncio
import aiohttp
import json
import uuid
from shared.isolated_environment import IsolatedEnvironment


async def test_real_data_pipeline():
    """Test the real data pipeline with actual running services."""
    print("[U+1F680] Starting real data pipeline test...")
    
    backend_url = "http://localhost:8000"
    auth_url = "http://localhost:8081"
    issues = []
    
    async with aiohttp.ClientSession() as session:
        try:
            # Step 1: Create a test user
            test_uuid = str(uuid.uuid4())[:8]
            user_data = {
                "email": f"test.pipeline.{test_uuid}@example.com",
                "full_name": f"Pipeline Test User {test_uuid}",
                "password": "TestPipeline123!",
                "confirm_password": "TestPipeline123!"
            }
            
            print(f"[U+1F4E7] Registering user: {user_data['email']}")
            async with session.post(f"{auth_url}/auth/register", json=user_data) as response:
                if response.status in [200, 201]:
                    auth_response = await response.json()
                    token = auth_response.get("access_token") or auth_response.get("token")
                    if not token:
                        print(" FAIL:  No token returned from registration, trying login...")
                        # Try login
                        login_data = {"email": user_data["email"], "password": user_data["password"]}
                        async with session.post(f"{auth_url}/auth/login", json=login_data) as login_response:
                            if login_response.status == 200:
                                login_result = await login_response.json()
                                token = login_result.get("access_token") or login_result.get("token")
                            else:
                                login_text = await login_response.text()
                                issues.append(f"Login failed: {login_response.status} - {login_text}")
                                return issues
                    
                    if token:
                        print(" PASS:  User authenticated successfully")
                    else:
                        issues.append("Failed to get auth token")
                        return issues
                        
                else:
                    response_text = await response.text()
                    issues.append(f"User registration failed: {response.status} - {response_text}")
                    return issues
                    
            headers = {"Authorization": f"Bearer {token}"}
            
            # Step 2: Create a thread
            print("[U+1F4DD] Creating thread...")
            thread_data = {
                "title": "Real Data Pipeline Test Thread",
                "metadata": {"test_type": "real_data_pipeline_integrity"}
            }
            
            async with session.post(f"{backend_url}/api/threads", json=thread_data, headers=headers) as response:
                if response.status == 201:
                    thread_response = await response.json()
                    thread_id = thread_response.get("id")
                    print(f" PASS:  Thread created: {thread_id}")
                else:
                    response_text = await response.text()
                    issues.append(f"Thread creation failed: {response.status} - {response_text}")
                    return issues
                    
            # Step 3: Get the thread to verify it exists
            print(" SEARCH:  Verifying thread integrity...")
            async with session.get(f"{backend_url}/api/threads/{thread_id}", headers=headers) as response:
                if response.status == 200:
                    thread_details = await response.json()
                    if thread_details.get("title") == thread_data["title"]:
                        print(" PASS:  Thread data integrity verified")
                    else:
                        issues.append(f"Thread title mismatch: expected '{thread_data['title']}', got '{thread_details.get('title')}'")
                else:
                    response_text = await response.text()
                    issues.append(f"Thread retrieval failed: {response.status} - {response_text}")
                    
            # Step 4: Test thread update
            print(" CYCLE:  Testing thread update...")
            update_data = {"title": "Updated Real Pipeline Test Thread"}
            async with session.put(f"{backend_url}/api/threads/{thread_id}", json=update_data, headers=headers) as response:
                if response.status == 200:
                    # Verify update
                    async with session.get(f"{backend_url}/api/threads/{thread_id}", headers=headers) as verify_response:
                        if verify_response.status == 200:
                            updated_thread = await verify_response.json()
                            if updated_thread.get("title") == update_data["title"]:
                                print(" PASS:  Thread update successful")
                            else:
                                issues.append("Thread update did not propagate correctly")
                        else:
                            issues.append(f"Thread verification after update failed: {verify_response.status}")
                else:
                    response_text = await response.text()
                    issues.append(f"Thread update failed: {response.status} - {response_text}")
                    
            # Step 5: Try to get messages for the thread
            print("[U+1F4E8] Testing messages endpoint...")
            async with session.get(f"{backend_url}/api/threads/{thread_id}/messages", headers=headers) as response:
                if response.status == 200:
                    messages_response = await response.json()
                    messages = messages_response if isinstance(messages_response, list) else messages_response.get("messages", [])
                    print(f" PASS:  Messages endpoint working: {len(messages)} messages found")
                else:
                    response_text = await response.text()
                    issues.append(f"Messages endpoint failed: {response.status} - {response_text}")
                    
            # Step 6: Test cross-service authentication
            print("[U+1F510] Testing cross-service authentication...")
            async with session.get(f"{auth_url}/auth/verify", headers=headers) as response:
                if response.status == 200:
                    user_info = await response.json()
                    print(f" PASS:  Cross-service auth working: {user_info.get('email')}")
                else:
                    response_text = await response.text()
                    issues.append(f"Cross-service auth failed: {response.status} - {response_text}")
                    
            # Cleanup - delete the test thread
            print("[U+1F9F9] Cleaning up test thread...")
            async with session.delete(f"{backend_url}/api/threads/{thread_id}", headers=headers) as response:
                if response.status in [200, 204]:
                    print(" PASS:  Test thread cleaned up successfully")
                else:
                    print(f" WARNING: [U+FE0F] Thread cleanup failed: {response.status}")
                    
        except Exception as e:
            issues.append(f"Test failed with exception: {str(e)}")
            
    return issues


async def main():
    """Main test runner."""
    print("=" * 60)
    print("DATA PIPELINE INTEGRITY TEST")
    print("=" * 60)
    
    issues = await test_real_data_pipeline()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    if issues:
        print(" FAIL:  ISSUES FOUND:")
        for issue in issues:
            print(f"  [U+2022] {issue}")
        return 1
    else:
        print(" PASS:  ALL TESTS PASSED - Data pipeline integrity verified!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)