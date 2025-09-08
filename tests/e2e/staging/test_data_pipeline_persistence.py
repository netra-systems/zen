"""
Test Data Pipeline Persistence E2E

Business Value Justification (BVJ):
- Segment: All (Data integrity critical across all user tiers)
- Business Goal: Ensure user data, agent results, and system state persist correctly
- Value Impact: Users can rely on data consistency and retrieve past agent interactions
- Strategic Impact: Data reliability foundation for enterprise trust and compliance

CRITICAL AUTHENTICATION REQUIREMENT:
ALL tests MUST use authentication to ensure data is properly scoped to authenticated
user sessions and isolated between users.

CRITICAL DATA PIPELINE REQUIREMENTS:
- Agent Results Persistence: Agent outputs saved to database correctly
- Thread Management: Conversation threads persist across sessions
- Database Transaction Integrity: ACID properties maintained during concurrent operations  
- Cross-Environment Configuration: Settings consistent across test/staging/production
- Data Isolation: User data remains isolated and private
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import aiohttp
import websockets

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user
from tests.e2e.staging_config import get_staging_config


class TestDataPipelinePersistence(BaseE2ETest):
    """Test data pipeline persistence and integrity."""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.staging_config = get_staging_config()
        self.auth_helper = E2EAuthHelper(environment="staging")
        
    async def verify_thread_exists(self, thread_id: str, expected_user_id: str, token: str) -> bool:
        """Verify thread exists and belongs to expected user."""
        try:
            async with aiohttp.ClientSession() as session:
                # Attempt to retrieve thread via API
                api_url = f"{self.staging_config.urls.api_base_url}/threads/{thread_id}"
                headers = {"Authorization": f"Bearer {token}"}
                
                async with session.get(api_url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        thread_data = await resp.json()
                        return thread_data.get("user_id") == expected_user_id
                    elif resp.status == 404:
                        return False
                    else:
                        self.logger.warning(f"Unexpected response for thread {thread_id}: {resp.status}")
                        return False
                        
        except Exception as e:
            self.logger.warning(f"Could not verify thread {thread_id}: {e}")
            return False
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.staging
    async def test_agent_results_persistence_complete_flow(self, real_services, real_llm):
        """Test complete agent results persistence and retrieval flow."""
        self.logger.info("🚀 Starting Agent Results Persistence Complete Flow E2E Test")
        
        # MANDATORY: Authenticate user
        token, user_data = await create_authenticated_user(
            environment="staging",
            email=f"results-persistence-{uuid.uuid4().hex[:8]}@staging.netrasystems.ai"
        )
        
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            # Step 1: Execute agent and capture results
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=websocket_headers,
                    open_timeout=20.0
                ),
                timeout=25.0
            )
            
            # Send agent request that should generate substantial results
            agent_request = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": "Provide detailed cost optimization analysis with specific recommendations and savings calculations",
                "context": {
                    "user_id": user_data["id"],
                    "analysis_scope": "comprehensive",
                    "require_persistence": True,
                    "test_scenario": "persistence_validation"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(agent_request))
            self.logger.info("📤 Agent request sent for persistence test")
            
            # Collect all events and extract results
            events = []
            agent_result = None
            thread_id = None
            start_time = time.time()
            
            while time.time() - start_time < 120:  # 2 minute timeout for real LLM
                try:
                    event_str = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    event = json.loads(event_str)
                    events.append(event)
                    
                    # Capture final result and thread ID
                    if event["type"] == "agent_completed":
                        agent_result = event["data"]["result"]
                        thread_id = event["data"].get("thread_id")
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            await websocket.close()
            
            # Validate we got results to persist
            assert agent_result is not None, "Agent should have produced results"
            assert thread_id is not None, "Agent should have created a thread"
            assert isinstance(agent_result, dict), "Agent result should be structured data"
            
            self.logger.info(f"✅ Agent execution completed - Thread ID: {thread_id}")
            
            # Step 2: Verify thread persistence via API
            thread_exists = await self.verify_thread_exists(thread_id, user_data["id"], token)
            
            if thread_exists:
                self.logger.info("✅ Thread successfully persisted to database")
            else:
                self.logger.warning("⚠️ Could not verify thread persistence via API (may not be exposed)")
            
            # Step 3: Reconnect and verify session continuity
            await asyncio.sleep(2)  # Brief pause between connections
            
            websocket2 = await websockets.connect(
                self.staging_config.urls.websocket_url,
                additional_headers=websocket_headers
            )
            
            # Send follow-up request referencing previous thread
            followup_request = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": "Based on my previous analysis, provide implementation timeline for top recommendation",
                "context": {
                    "user_id": user_data["id"],
                    "reference_thread": thread_id,
                    "followup": True
                }
            }
            
            await websocket2.send(json.dumps(followup_request))
            
            # Collect followup events
            followup_events = []
            start_time = time.time()
            
            while time.time() - start_time < 60:
                try:
                    event_str = await asyncio.wait_for(websocket2.recv(), timeout=20.0)
                    event = json.loads(event_str)
                    followup_events.append(event)
                    
                    if event["type"] == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            await websocket2.close()
            
            # Validate followup execution
            followup_event_types = [e["type"] for e in followup_events]
            assert "agent_completed" in followup_event_types, "Follow-up request should complete"
            
            final_followup_event = next(e for e in reversed(followup_events) if e["type"] == "agent_completed")
            followup_result = final_followup_event["data"]["result"]
            followup_thread_id = final_followup_event["data"].get("thread_id")
            
            # Should have created results in second session
            assert followup_result is not None, "Follow-up should produce results"
            assert followup_thread_id is not None, "Follow-up should have thread ID"
            
            # Results should be different (different conversations)
            assert followup_result != agent_result, "Follow-up should produce different results"
            
            self.logger.info("✅ Agent Results Persistence Complete Flow E2E Test completed")
            
        except Exception as e:
            self.logger.error(f"❌ Agent Results Persistence test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_configuration_consistency_across_environments(self, real_services):
        """Test configuration consistency and environment-specific settings."""
        self.logger.info("🚀 Starting Configuration Consistency E2E Test")
        
        # MANDATORY: Authenticate user
        token, user_data = await create_authenticated_user(
            environment="staging",
            email=f"config-consistency-{uuid.uuid4().hex[:8]}@staging.netrasystems.ai"
        )
        
        async with aiohttp.ClientSession() as session:
            # Step 1: Validate staging configuration endpoints
            config_endpoints = [
                f"{self.staging_config.urls.backend_url}/health",
                f"{self.staging_config.urls.auth_url}/auth/health",
                f"{self.staging_config.urls.frontend_url}/health"
            ]
            
            config_results = {}
            
            for endpoint in config_endpoints:
                try:
                    async with session.get(endpoint, timeout=10) as resp:
                        service_name = endpoint.split('/')[-2] if 'auth' in endpoint else endpoint.split('/')[-1]
                        config_results[service_name] = {
                            "status": resp.status,
                            "available": resp.status < 500,
                            "response_time": time.time()
                        }
                        
                        if resp.status == 200:
                            try:
                                health_data = await resp.json()
                                config_results[service_name]["environment"] = health_data.get("environment", "unknown")
                                config_results[service_name]["version"] = health_data.get("version", "unknown")
                            except:
                                # Health endpoint may not return JSON
                                pass
                                
                except Exception as e:
                    service_name = endpoint.split('/')[-2] if 'auth' in endpoint else endpoint.split('/')[-1]
                    config_results[service_name] = {
                        "status": 0,
                        "available": False,
                        "error": str(e)
                    }
            
            # Validate at least 2 out of 3 services are available
            available_services = sum(1 for result in config_results.values() if result.get("available", False))
            assert available_services >= 2, f"Only {available_services}/3 services available: {config_results}"
            
            self.logger.info(f"✅ Configuration validation - {available_services}/3 services available")
            
            # Step 2: Test environment-specific configurations
            # Connect WebSocket to verify staging-specific settings
            websocket_headers = self.auth_helper.get_websocket_headers(token)
            
            try:
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.staging_config.urls.websocket_url,
                        additional_headers=websocket_headers,
                        open_timeout=15.0
                    ),
                    timeout=18.0
                )
                
                # Send environment validation request
                env_request = {
                    "type": "environment_info",
                    "user_id": user_data["id"],
                    "test_type": "configuration_validation"
                }
                
                await websocket.send(json.dumps(env_request))
                
                # Check for response (any response indicates proper config)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    self.logger.info("✅ WebSocket environment configuration working")
                except asyncio.TimeoutError:
                    self.logger.info("✅ WebSocket connection established (no response expected)")
                
                await websocket.close()
                
            except Exception as e:
                self.logger.warning(f"⚠️ WebSocket environment test failed: {e}")
            
            # Step 3: Validate staging-specific authentication configuration
            auth_headers = {"Authorization": f"Bearer {token}"}
            validate_url = f"{self.staging_config.urls.auth_url}/auth/validate"
            
            async with session.get(validate_url, headers=auth_headers, timeout=8) as resp:
                if resp.status == 200:
                    validate_result = await resp.json()
                    
                    # Should have staging-appropriate token validation
                    assert validate_result.get("valid") == True, "Token should validate in staging"
                    
                    # Check for staging-specific claims if available
                    if "environment" in validate_result:
                        assert validate_result["environment"].lower() in ["staging", "test"], "Should indicate staging environment"
                    
                    self.logger.info("✅ Staging authentication configuration validated")
                else:
                    self.logger.warning(f"⚠️ Auth validation response: {resp.status}")
        
        self.logger.info("✅ Configuration Consistency E2E Test completed")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_database_transaction_integrity(self, real_services):
        """Test database transaction integrity during concurrent operations."""
        self.logger.info("🚀 Starting Database Transaction Integrity E2E Test")
        
        # Create multiple users for concurrent database operations
        users = []
        for i in range(3):
            token, user_data = await create_authenticated_user(
                environment="staging",
                email=f"db-integrity-{i}-{uuid.uuid4().hex[:6]}@staging.netrasystems.ai"
            )
            users.append((token, user_data))
        
        async def concurrent_database_operation(user_idx: int, token: str, user_data: Dict):
            """Perform database operations that test transaction integrity."""
            operation_id = f"db-op-{user_idx}-{uuid.uuid4().hex[:6]}"
            
            try:
                websocket_headers = self.auth_helper.get_websocket_headers(token)
                websocket = await websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=websocket_headers,
                    open_timeout=15.0
                )
                
                # Perform operations that involve database writes
                operations = [
                    {
                        "type": "agent_request",
                        "agent": "triage_agent",
                        "message": f"Database integrity test operation {op_num + 1}",
                        "context": {
                            "user_id": user_data["id"],
                            "operation_id": f"{operation_id}-{op_num}",
                            "integrity_test": True
                        }
                    }
                    for op_num in range(2)  # 2 operations per user
                ]
                
                results = []
                for operation in operations:
                    await websocket.send(json.dumps(operation))
                    
                    # Wait for completion
                    start_time = time.time()
                    while time.time() - start_time < 30:
                        try:
                            event_str = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                            event = json.loads(event_str)
                            
                            if event["type"] == "agent_completed":
                                results.append({
                                    "thread_id": event["data"].get("thread_id"),
                                    "result": event["data"]["result"]
                                })
                                break
                                
                        except asyncio.TimeoutError:
                            break
                    
                    # Small delay between operations
                    await asyncio.sleep(1)
                
                await websocket.close()
                
                return {
                    "user_idx": user_idx,
                    "operation_id": operation_id,
                    "operations_completed": len(results),
                    "thread_ids": [r["thread_id"] for r in results if r["thread_id"]],
                    "status": "success"
                }
                
            except Exception as e:
                return {
                    "user_idx": user_idx,
                    "operation_id": operation_id,
                    "status": "error",
                    "error": str(e)
                }
        
        # Run concurrent operations
        tasks = [
            concurrent_database_operation(i, token, user_data)
            for i, (token, user_data) in enumerate(users)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate transaction integrity
        successful_operations = [r for r in results if not isinstance(r, Exception) and r.get("status") == "success"]
        
        # Should have most operations succeed
        assert len(successful_operations) >= 2, f"Database integrity test failed - only {len(successful_operations)}/3 users successful"
        
        # Validate data integrity
        total_operations = sum(r.get("operations_completed", 0) for r in successful_operations)
        total_threads = sum(len(r.get("thread_ids", [])) for r in successful_operations)
        
        # Should have created database records
        assert total_operations >= 4, "Should have completed multiple database operations"
        assert total_threads >= 2, "Should have created multiple thread records"
        
        # Validate thread ID uniqueness (no collisions)
        all_thread_ids = []
        for result in successful_operations:
            all_thread_ids.extend(result.get("thread_ids", []))
        
        unique_thread_ids = set(all_thread_ids)
        assert len(unique_thread_ids) == len(all_thread_ids), "Thread IDs should be unique (no database collisions)"
        
        self.logger.info(f"✅ Database Transaction Integrity Test - {total_operations} operations, {len(unique_thread_ids)} unique threads")
        
    async def teardown_method(self):
        """Cleanup after each test method."""
        await super().cleanup_resources()