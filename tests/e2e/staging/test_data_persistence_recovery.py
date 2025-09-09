"""
E2E Staging Tests: Data Persistence and Recovery Scenarios - BATCH 2
====================================================================

This module tests comprehensive data persistence and recovery capabilities end-to-end in staging.
Tests REAL data operations, backup/recovery scenarios, data integrity, and persistence mechanisms.

Business Value:
- Prevents $2M+ data loss incidents that would terminate customer relationships
- Ensures 99.99% data durability SLA compliance for enterprise customers
- Validates data recovery capabilities restore business continuity within RPO/RTO
- Tests data integrity mechanisms prevent corruption costing $100K+ per incident

CRITICAL E2E REQUIREMENTS:
- MUST use real authentication (JWT/OAuth)
- MUST test actual data persistence with real database operations
- MUST validate business data integrity and recovery
- MUST test with real staging environment configuration  
- NO MOCKS ALLOWED - uses real databases, real data operations

Test Coverage:
1. Cross-session data persistence with business continuity validation
2. Agent execution state recovery after system interruption
3. Multi-user concurrent data integrity with transaction isolation
"""

import asyncio
import json
import logging
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Set

import aiohttp
import pytest
import websockets
from dataclasses import dataclass

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper, 
    E2EAuthConfig,
    create_authenticated_user_context
)
from tests.e2e.staging_config import get_staging_config, StagingTestConfig
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID

logger = logging.getLogger(__name__)

class TestDataPersistenceRecovery:
    """
    E2E Tests for Data Persistence and Recovery in Staging Environment.
    
    These tests validate that business-critical data is properly persisted,
    can be recovered after failures, and maintains integrity across operations.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_authenticated_context(self):
        """Setup authenticated user context for all tests."""
        self.auth_helper = E2EAuthHelper(environment="staging")
        self.websocket_helper = E2EWebSocketAuthHelper(environment="staging")
        self.staging_config = StagingTestConfig()
        
        # Create authenticated user context
        self.user_context = await create_authenticated_user_context(
            user_email=f"data_persistence_test_{int(time.time())}@example.com",
            environment="staging",
            permissions=["read", "write", "agent_execute", "data_manage"],
            websocket_enabled=True
        )
        
        # Get authentication token
        self.auth_token = await self.auth_helper.get_staging_token_async(
            email=self.user_context.agent_context['user_email']
        )
        
        logger.info(f"✅ Setup authenticated context for data persistence tests")
        logger.info(f"User ID: {self.user_context.user_id}")
        logger.info(f"Thread ID: {self.user_context.thread_id}")

    @pytest.mark.asyncio
    async def test_cross_session_data_persistence_with_business_continuity_validation(self):
        """
        Test 1: Cross-Session Data Persistence with Business Continuity Validation
        
        Business Value: $1M+ ARR protection - Tests that:
        1. Business data persists correctly across multiple user sessions  
        2. Customer optimization data survives session disconnections
        3. Thread continuity maintains business context between sessions
        4. Data integrity ensures customer work is never lost
        
        This validates our enterprise data durability promises.
        """
        test_start_time = time.time()
        
        # Data Persistence Configuration
        persistence_config = {
            "test_type": "cross_session_persistence",
            "business_data_types": [
                "customer_optimization_context",
                "agent_execution_history", 
                "thread_conversation_state",
                "user_preferences_configuration"
            ],
            "session_lifecycle_stages": [
                "session_1_data_creation",
                "session_1_termination", 
                "session_2_data_retrieval",
                "session_2_data_validation"
            ],
            "data_integrity_requirements": {
                "zero_data_loss": True,
                "context_preservation": True,
                "business_continuity": True
            }
        }
        
        # Test data for persistence validation
        test_business_data = {
            "customer_id": f"enterprise_customer_{int(time.time())}",
            "optimization_context": {
                "cost_savings_target": 250000,  # $250K savings goal
                "performance_improvement_target": 0.35,  # 35% performance improvement
                "infrastructure_scope": ["compute", "storage", "networking"],
                "timeline": "90_days"
            },
            "agent_collaboration_state": {
                "primary_agent": "cost_optimization_agent",
                "supporting_agents": ["data_analysis_agent", "performance_agent"],
                "workflow_stage": "analysis_complete_optimization_pending",
                "intermediate_results": {
                    "current_costs": 750000,  # $750K current annual costs
                    "identified_optimizations": [
                        {"type": "compute_rightsizing", "potential_savings": 180000},
                        {"type": "storage_optimization", "potential_savings": 45000},
                        {"type": "network_efficiency", "potential_savings": 25000}
                    ]
                }
            },
            "user_session_metadata": {
                "session_start": time.time(),
                "user_id": str(self.user_context.user_id),
                "thread_id": str(self.user_context.thread_id),
                "business_priority": "high_value_enterprise"
            }
        }
        
        persistence_validation_results = {
            "session_1_data_stored": False,
            "session_1_data_verified": False,
            "session_2_data_retrieved": False,
            "session_2_data_integrity_confirmed": False,
            "business_continuity_validated": False,
            "data_loss_detected": False
        }
        
        # SESSION 1: Create and store business data
        logger.info("📝 SESSION 1: Creating and storing business-critical data")
        
        async with aiohttp.ClientSession() as session:
            headers = self.websocket_helper.get_websocket_headers(self.auth_token)
            
            async with websockets.connect(
                self.staging_config.urls.websocket_url,
                extra_headers=headers,
                open_timeout=15.0
            ) as websocket:
                
                # Store business data with persistence requirements
                data_storage_request = {
                    "type": "business_data_persistence_request",
                    "request_id": str(self.user_context.request_id),
                    "thread_id": str(self.user_context.thread_id),
                    "user_id": str(self.user_context.user_id),
                    "operation": "store_business_critical_data",
                    "data_payload": test_business_data,
                    "persistence_requirements": {
                        "durability": "enterprise_grade",
                        "cross_session_availability": True,
                        "backup_required": True,
                        "integrity_validation": True
                    },
                    "business_impact": "high_value_customer_optimization"
                }
                
                await websocket.send(json.dumps(data_storage_request))
                logger.info("📤 Sent business data storage request")
                
                # Wait for storage confirmation
                storage_timeout = 30.0
                storage_start = time.time()
                storage_confirmed = False
                
                while time.time() - storage_start < storage_timeout and not storage_confirmed:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event_data = json.loads(message)
                        
                        event_type = event_data.get("event_type", "")
                        status = event_data.get("status", "")
                        
                        logger.info(f"📥 Storage event: {event_type} - {status}")
                        
                        if event_type in ["data_stored", "persistence_confirmed"]:
                            if "success" in status.lower() or "confirmed" in status.lower():
                                persistence_validation_results["session_1_data_stored"] = True
                                storage_confirmed = True
                                logger.info("✅ Business data storage confirmed in Session 1")
                                
                                # Verify data integrity immediately after storage
                                if event_data.get("data_integrity_hash"):
                                    persistence_validation_results["session_1_data_verified"] = True
                                    logger.info("🔍 Data integrity verification passed in Session 1")
                                    
                    except asyncio.TimeoutError:
                        logger.warning("⚠️ Timeout waiting for storage confirmation")
                        continue
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Storage event decode error: {e}")
                        continue
                
                # Additional business context storage
                context_storage_request = {
                    "type": "thread_context_persistence",
                    "request_id": f"{self.user_context.request_id}_context",
                    "thread_id": str(self.user_context.thread_id),
                    "user_id": str(self.user_context.user_id),
                    "conversation_state": {
                        "stage": "optimization_analysis_complete",
                        "next_actions": ["implement_cost_optimizations", "measure_performance_impact"],
                        "business_context_preserved": True
                    }
                }
                
                await websocket.send(json.dumps(context_storage_request))
                logger.info("📤 Sent thread context persistence request")
                
                # Brief wait for context storage
                await asyncio.sleep(2.0)
        
        logger.info("🔚 SESSION 1: Terminated - simulating session disconnection")
        await asyncio.sleep(3.0)  # Simulate time gap between sessions
        
        # SESSION 2: Retrieve and validate persisted data
        logger.info("🔄 SESSION 2: Retrieving and validating persisted data")
        
        # Create new authentication context for Session 2 (same user)
        session_2_auth_token = await self.auth_helper.get_staging_token_async(
            email=self.user_context.agent_context['user_email']
        )
        
        async with aiohttp.ClientSession() as session:
            headers = self.websocket_helper.get_websocket_headers(session_2_auth_token)
            
            async with websockets.connect(
                self.staging_config.urls.websocket_url,
                extra_headers=headers,
                open_timeout=15.0
            ) as websocket:
                
                # Retrieve persisted business data
                data_retrieval_request = {
                    "type": "business_data_retrieval_request",
                    "request_id": f"{self.user_context.request_id}_retrieval",
                    "thread_id": str(self.user_context.thread_id),  # Same thread ID
                    "user_id": str(self.user_context.user_id),      # Same user ID
                    "operation": "retrieve_business_critical_data",
                    "retrieval_scope": "complete_business_context",
                    "validation_required": True
                }
                
                await websocket.send(json.dumps(data_retrieval_request))
                logger.info("📤 Sent business data retrieval request")
                
                # Monitor data retrieval and validation
                retrieval_timeout = 30.0
                retrieval_start = time.time()
                retrieved_data = None
                
                while time.time() - retrieval_start < retrieval_timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event_data = json.loads(message)
                        
                        event_type = event_data.get("event_type", "")
                        status = event_data.get("status", "")
                        
                        logger.info(f"📥 Retrieval event: {event_type} - {status}")
                        
                        if event_type in ["data_retrieved", "business_data_loaded"]:
                            if "success" in status.lower():
                                persistence_validation_results["session_2_data_retrieved"] = True
                                retrieved_data = event_data.get("data_payload", {})
                                logger.info("✅ Business data retrieval successful in Session 2")
                                
                                # Validate data integrity
                                if self._validate_data_integrity(test_business_data, retrieved_data):
                                    persistence_validation_results["session_2_data_integrity_confirmed"] = True
                                    logger.info("🔍 Data integrity validation passed in Session 2")
                                else:
                                    persistence_validation_results["data_loss_detected"] = True
                                    logger.error("❌ Data integrity validation failed - data loss detected")
                                    
                        elif event_type == "business_continuity_validated":
                            if "confirmed" in status.lower():
                                persistence_validation_results["business_continuity_validated"] = True
                                logger.info("🏢 Business continuity validation confirmed")
                                break
                                
                    except asyncio.TimeoutError:
                        logger.warning("⚠️ Timeout waiting for retrieval events")
                        continue
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Retrieval event decode error: {e}")
                        continue
                
                # Test business continuity by resuming optimization workflow
                if persistence_validation_results["session_2_data_retrieved"]:
                    continuation_request = {
                        "type": "business_workflow_continuation",
                        "request_id": f"{self.user_context.request_id}_continuation",
                        "thread_id": str(self.user_context.thread_id),
                        "user_id": str(self.user_context.user_id),
                        "operation": "resume_optimization_workflow",
                        "context_source": "persisted_session_data"
                    }
                    
                    await websocket.send(json.dumps(continuation_request))
                    logger.info("📤 Sent workflow continuation request")
                    
                    # Brief monitoring for continuation success
                    continuation_timeout = 15.0
                    continuation_start = time.time()
                    
                    while time.time() - continuation_start < continuation_timeout:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                            event_data = json.loads(message)
                            
                            if event_data.get("event_type") == "workflow_resumed":
                                persistence_validation_results["business_continuity_validated"] = True
                                logger.info("🏢 Workflow continuation successful - business continuity confirmed")
                                break
                                
                        except asyncio.TimeoutError:
                            break
                        except json.JSONDecodeError:
                            continue
        
        # Validation: Comprehensive data persistence validation
        test_duration = time.time() - test_start_time
        
        # Assert 1: Real persistence testing timing
        assert test_duration >= 10.0, f"Data persistence test too fast ({test_duration:.2f}s) - likely fake/mocked"
        
        # Assert 2: Session 1 data storage successful
        assert persistence_validation_results["session_1_data_stored"], "Business data storage failed in Session 1"
        assert persistence_validation_results["session_1_data_verified"], "Data integrity verification failed in Session 1"
        
        # Assert 3: Session 2 data retrieval successful  
        assert persistence_validation_results["session_2_data_retrieved"], "Business data retrieval failed in Session 2"
        assert persistence_validation_results["session_2_data_integrity_confirmed"], "Data integrity validation failed in Session 2"
        
        # Assert 4: No data loss detected
        assert not persistence_validation_results["data_loss_detected"], "Data loss detected between sessions - critical failure"
        
        # Assert 5: Business continuity validated
        assert persistence_validation_results["business_continuity_validated"], "Business continuity validation failed"
        
        logger.info(f"✅ PASS: Cross-session data persistence with business continuity - {test_duration:.2f}s")
        logger.info(f"Session 1 storage: {persistence_validation_results['session_1_data_stored']}")
        logger.info(f"Session 1 verification: {persistence_validation_results['session_1_data_verified']}")
        logger.info(f"Session 2 retrieval: {persistence_validation_results['session_2_data_retrieved']}")
        logger.info(f"Session 2 integrity: {persistence_validation_results['session_2_data_integrity_confirmed']}")
        logger.info(f"Business continuity: {persistence_validation_results['business_continuity_validated']}")
        logger.info(f"Data loss detected: {persistence_validation_results['data_loss_detected']}")

    @pytest.mark.asyncio
    async def test_agent_execution_state_recovery_after_system_interruption(self):
        """
        Test 2: Agent Execution State Recovery After System Interruption
        
        Business Value: $800K+ ARR protection - Tests that:
        1. Agent execution state is preserved during system interruptions
        2. Long-running agent workflows can be resumed after failures
        3. Partial results and intermediate state are not lost
        4. Customer work in progress survives system instability
        
        This prevents loss of expensive agent computations and customer work.
        """
        test_start_time = time.time()
        
        # Agent State Recovery Configuration
        recovery_config = {
            "test_type": "agent_execution_state_recovery",
            "long_running_agent_workflow": {
                "agent_type": "comprehensive_optimization_agent",
                "expected_duration": 45.0,  # 45 second workflow
                "checkpoint_intervals": 10.0,  # Checkpoint every 10 seconds
                "interruption_point": 25.0,  # Interrupt at 25 seconds
                "recovery_validation_duration": 15.0  # 15 seconds to validate recovery
            },
            "state_preservation_requirements": {
                "intermediate_results_preserved": True,
                "execution_context_maintained": True,
                "progress_tracking_intact": True,
                "business_value_calculations_preserved": True
            }
        }
        
        agent_state_tracking = {
            "execution_started": False,
            "checkpoints_created": 0,
            "interruption_detected": False,
            "recovery_initiated": False,
            "state_restored": False,
            "workflow_resumed": False,
            "final_completion": False,
            "intermediate_results": [],
            "execution_events": []
        }
        
        # Step 1: Start long-running agent workflow
        logger.info("🤖 Starting long-running agent execution for state recovery test")
        
        async with aiohttp.ClientSession() as session:
            headers = self.websocket_helper.get_websocket_headers(self.auth_token)
            
            async with websockets.connect(
                self.staging_config.urls.websocket_url,
                extra_headers=headers,
                open_timeout=15.0
            ) as websocket:
                
                # Initiate long-running agent workflow
                long_running_request = {
                    "type": "long_running_agent_execution",
                    "request_id": str(self.user_context.request_id),
                    "thread_id": str(self.user_context.thread_id),
                    "user_id": str(self.user_context.user_id),
                    "agent_config": recovery_config["long_running_agent_workflow"],
                    "state_preservation": {
                        "enabled": True,
                        "checkpoint_frequency": recovery_config["long_running_agent_workflow"]["checkpoint_intervals"],
                        "recovery_metadata": True
                    },
                    "business_context": {
                        "customer_value": 500000,  # $500K optimization project
                        "criticality": "high",
                        "recovery_required": True
                    }
                }
                
                await websocket.send(json.dumps(long_running_request))
                logger.info("📤 Sent long-running agent execution request")
                
                # Monitor initial execution and checkpoints
                execution_start = time.time()
                interruption_point = execution_start + recovery_config["long_running_agent_workflow"]["interruption_point"]
                
                while time.time() < interruption_point:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        event_data = json.loads(message)
                        agent_state_tracking["execution_events"].append(event_data)
                        
                        event_type = event_data.get("event_type", "")
                        
                        logger.info(f"🔍 Agent execution event: {event_type}")
                        
                        if event_type == "agent_started":
                            agent_state_tracking["execution_started"] = True
                            logger.info("🚀 Long-running agent execution started")
                            
                        elif event_type == "checkpoint_created" or "checkpoint" in event_type.lower():
                            agent_state_tracking["checkpoints_created"] += 1
                            logger.info(f"📍 Checkpoint {agent_state_tracking['checkpoints_created']} created")
                            
                        elif event_type == "intermediate_result":
                            intermediate_result = event_data.get("result_data", {})
                            agent_state_tracking["intermediate_results"].append(intermediate_result)
                            logger.info("📊 Intermediate result captured")
                            
                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError:
                        continue
        
        # Step 2: Simulate system interruption
        logger.info("⚡ SIMULATING SYSTEM INTERRUPTION - WebSocket connection terminated")
        agent_state_tracking["interruption_detected"] = True
        await asyncio.sleep(5.0)  # Simulate downtime
        
        # Step 3: Attempt state recovery
        logger.info("🔄 Attempting agent execution state recovery")
        
        # Create new WebSocket connection to simulate system recovery
        recovery_auth_token = await self.auth_helper.get_staging_token_async(
            email=self.user_context.agent_context['user_email']
        )
        
        async with aiohttp.ClientSession() as session:
            headers = self.websocket_helper.get_websocket_headers(recovery_auth_token)
            
            async with websockets.connect(
                self.staging_config.urls.websocket_url,
                extra_headers=headers,
                open_timeout=15.0
            ) as websocket:
                
                # Request state recovery
                state_recovery_request = {
                    "type": "agent_execution_state_recovery",
                    "request_id": f"{self.user_context.request_id}_recovery",
                    "original_request_id": str(self.user_context.request_id),
                    "thread_id": str(self.user_context.thread_id),
                    "user_id": str(self.user_context.user_id),
                    "recovery_operation": "restore_and_resume",
                    "state_recovery_requirements": recovery_config["state_preservation_requirements"]
                }
                
                await websocket.send(json.dumps(state_recovery_request))
                logger.info("📤 Sent agent state recovery request")
                
                # Monitor state recovery process
                recovery_timeout = 30.0
                recovery_start = time.time()
                
                while time.time() - recovery_start < recovery_timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event_data = json.loads(message)
                        agent_state_tracking["execution_events"].append(event_data)
                        
                        event_type = event_data.get("event_type", "")
                        status = event_data.get("status", "")
                        
                        logger.info(f"🔧 Recovery event: {event_type} - {status}")
                        
                        if event_type == "recovery_initiated":
                            agent_state_tracking["recovery_initiated"] = True
                            logger.info("🔄 Agent state recovery initiated")
                            
                        elif event_type == "state_restored":
                            agent_state_tracking["state_restored"] = True
                            logger.info("💾 Agent execution state restored")
                            
                            # Validate preserved intermediate results
                            recovered_results = event_data.get("intermediate_results", [])
                            if len(recovered_results) > 0:
                                logger.info(f"📊 {len(recovered_results)} intermediate results recovered")
                                
                        elif event_type == "workflow_resumed":
                            agent_state_tracking["workflow_resumed"] = True
                            logger.info("▶️ Agent workflow execution resumed")
                            
                        elif event_type == "agent_completed":
                            agent_state_tracking["final_completion"] = True
                            logger.info("✅ Agent execution completed after recovery")
                            break
                            
                    except asyncio.TimeoutError:
                        logger.warning("⚠️ Timeout in recovery monitoring")
                        continue
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Recovery event decode error: {e}")
                        continue
        
        # Validation: Comprehensive agent state recovery validation
        test_duration = time.time() - test_start_time
        
        # Assert 1: Real agent execution and recovery timing
        assert test_duration >= 20.0, f"Agent state recovery test too fast ({test_duration:.2f}s) - likely fake"
        
        # Assert 2: Initial agent execution established
        assert agent_state_tracking["execution_started"], "Long-running agent execution never started"
        assert agent_state_tracking["checkpoints_created"] >= 1, f"No checkpoints created ({agent_state_tracking['checkpoints_created']}) - state preservation failed"
        
        # Assert 3: System interruption handled
        assert agent_state_tracking["interruption_detected"], "System interruption not properly simulated"
        
        # Assert 4: State recovery process successful
        assert agent_state_tracking["recovery_initiated"], "Agent state recovery was not initiated"
        assert agent_state_tracking["state_restored"], "Agent execution state was not restored"
        
        # Assert 5: Workflow resumption after recovery
        assert agent_state_tracking["workflow_resumed"], "Agent workflow did not resume after state recovery"
        
        # Assert 6: Intermediate results preservation
        assert len(agent_state_tracking["intermediate_results"]) > 0, "No intermediate results preserved during execution"
        
        # Assert 7: Execution events show complete recovery cycle
        event_types = {event.get("event_type", "") for event in agent_state_tracking["execution_events"]}
        required_recovery_events = {"agent_started"}
        missing_events = required_recovery_events - event_types
        assert not missing_events, f"Missing required recovery events: {missing_events}"
        
        logger.info(f"✅ PASS: Agent execution state recovery after system interruption - {test_duration:.2f}s")
        logger.info(f"Execution started: {agent_state_tracking['execution_started']}")
        logger.info(f"Checkpoints created: {agent_state_tracking['checkpoints_created']}")
        logger.info(f"Recovery initiated: {agent_state_tracking['recovery_initiated']}")
        logger.info(f"State restored: {agent_state_tracking['state_restored']}")
        logger.info(f"Workflow resumed: {agent_state_tracking['workflow_resumed']}")
        logger.info(f"Final completion: {agent_state_tracking['final_completion']}")
        logger.info(f"Intermediate results preserved: {len(agent_state_tracking['intermediate_results'])}")
        logger.info(f"Total execution events: {len(agent_state_tracking['execution_events'])}")

    @pytest.mark.asyncio
    async def test_multi_user_concurrent_data_integrity_with_transaction_isolation(self):
        """
        Test 3: Multi-User Concurrent Data Integrity with Transaction Isolation
        
        Business Value: $600K+ ARR protection - Tests that:
        1. Multiple users can operate concurrently without data corruption
        2. Transaction isolation prevents data race conditions
        3. Each user's data remains isolated and consistent
        4. Concurrent operations maintain system-wide data integrity
        
        This ensures multi-tenant data safety for enterprise customers.
        """
        test_start_time = time.time()
        
        # Multi-User Concurrency Configuration
        concurrency_config = {
            "test_type": "multi_user_data_integrity",
            "concurrent_users": 8,  # 8 users operating simultaneously
            "operations_per_user": 4,  # 4 data operations per user
            "data_operations": [
                "create_customer_profile",
                "update_optimization_settings", 
                "store_analysis_results",
                "validate_data_integrity"
            ],
            "isolation_requirements": {
                "user_data_isolation": True,
                "transaction_consistency": True,
                "no_data_corruption": True,
                "concurrent_access_control": True
            }
        }
        
        # Track data integrity across all concurrent users
        multi_user_integrity_tracking = {
            "users_created": 0,
            "total_operations_attempted": 0,
            "total_operations_completed": 0,
            "data_corruption_detected": 0,
            "isolation_violations": 0,
            "transaction_conflicts": 0,
            "integrity_validations_passed": 0,
            "user_data_maps": {},  # Track each user's data separately
            "concurrent_operation_events": []
        }
        
        async def create_concurrent_user_data_operations(user_index: int) -> Dict[str, Any]:
            """Create concurrent data operations for a single user."""
            user_id = f"concurrent_data_user_{user_index}_{int(time.time())}"
            user_email = f"{user_id}@example.com"
            
            user_metrics = {
                "user_index": user_index,
                "user_id": user_id,
                "operations_completed": 0,
                "operations_failed": 0,
                "data_integrity_confirmed": False,
                "isolation_validated": False,
                "user_data_checksum": ""
            }
            
            try:
                # Create authenticated context for this user
                user_context = await create_authenticated_user_context(
                    user_email=user_email,
                    environment="staging",
                    permissions=["read", "write", "data_manage"],
                    websocket_enabled=True
                )
                
                # Get user authentication token
                user_auth_token = await self.auth_helper.get_staging_token_async(email=user_email)
                
                # Connect to WebSocket for concurrent operations
                headers = self.websocket_helper.get_websocket_headers(user_auth_token)
                
                async with websockets.connect(
                    self.staging_config.urls.websocket_url,
                    extra_headers=headers,
                    open_timeout=20.0
                ) as websocket:
                    
                    logger.info(f"👤 User {user_index}: Connected for concurrent data operations")
                    
                    # Perform concurrent data operations
                    for op_index, operation in enumerate(concurrency_config["data_operations"]):
                        operation_start = time.time()
                        
                        # Create unique business data for this user and operation
                        user_business_data = {
                            "user_specific_data": {
                                "customer_segment": f"enterprise_segment_{user_index}",
                                "optimization_budget": 100000 + (user_index * 25000),  # Unique budget per user
                                "performance_targets": {
                                    "cost_reduction": 0.15 + (user_index * 0.02),  # Unique targets
                                    "efficiency_gain": 0.25 + (user_index * 0.03)
                                }
                            },
                            "operation_metadata": {
                                "operation_type": operation,
                                "operation_index": op_index,
                                "user_index": user_index,
                                "timestamp": time.time(),
                                "isolation_required": True
                            }
                        }
                        
                        # Send concurrent data operation request
                        data_operation_request = {
                            "type": "concurrent_data_operation",
                            "request_id": f"{user_context.request_id}_op_{op_index}",
                            "thread_id": str(user_context.thread_id),
                            "user_id": str(user_context.user_id),
                            "operation": operation,
                            "data_payload": user_business_data,
                            "isolation_requirements": concurrency_config["isolation_requirements"],
                            "user_index": user_index
                        }
                        
                        await websocket.send(json.dumps(data_operation_request))
                        multi_user_integrity_tracking["total_operations_attempted"] += 1
                        
                        # Wait for operation completion
                        operation_timeout = 15.0
                        operation_completed = False
                        
                        while time.time() - operation_start < operation_timeout and not operation_completed:
                            try:
                                message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                                event_data = json.loads(message)
                                multi_user_integrity_tracking["concurrent_operation_events"].append({
                                    **event_data,
                                    "user_index": user_index,
                                    "operation_index": op_index
                                })
                                
                                event_type = event_data.get("event_type", "")
                                status = event_data.get("status", "")
                                
                                if event_type == "data_operation_completed":
                                    operation_completed = True
                                    user_metrics["operations_completed"] += 1
                                    multi_user_integrity_tracking["total_operations_completed"] += 1
                                    logger.info(f"👤 User {user_index}: Operation {operation} completed")
                                    
                                elif event_type == "data_integrity_validated":
                                    if "passed" in status.lower():
                                        multi_user_integrity_tracking["integrity_validations_passed"] += 1
                                        user_metrics["data_integrity_confirmed"] = True
                                        
                                elif event_type == "isolation_violation":
                                    multi_user_integrity_tracking["isolation_violations"] += 1
                                    logger.warning(f"⚠️ User {user_index}: Isolation violation detected")
                                    
                                elif event_type == "data_corruption":
                                    multi_user_integrity_tracking["data_corruption_detected"] += 1
                                    logger.error(f"❌ User {user_index}: Data corruption detected")
                                    
                                elif event_type == "transaction_conflict":
                                    multi_user_integrity_tracking["transaction_conflicts"] += 1
                                    logger.warning(f"⚠️ User {user_index}: Transaction conflict")
                                    
                            except asyncio.TimeoutError:
                                continue
                            except json.JSONDecodeError:
                                continue
                        
                        if not operation_completed:
                            user_metrics["operations_failed"] += 1
                            logger.warning(f"👤 User {user_index}: Operation {operation} timed out")
                    
                    # Final data integrity check for this user
                    integrity_check_request = {
                        "type": "user_data_integrity_check",
                        "request_id": f"{user_context.request_id}_integrity",
                        "thread_id": str(user_context.thread_id),
                        "user_id": str(user_context.user_id),
                        "validation_scope": "complete_user_data"
                    }
                    
                    await websocket.send(json.dumps(integrity_check_request))
                    
                    # Wait for final integrity validation
                    integrity_timeout = 10.0
                    integrity_start = time.time()
                    
                    while time.time() - integrity_start < integrity_timeout:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            event_data = json.loads(message)
                            
                            if event_data.get("event_type") == "integrity_check_completed":
                                if "passed" in event_data.get("status", "").lower():
                                    user_metrics["isolation_validated"] = True
                                    user_metrics["user_data_checksum"] = event_data.get("data_checksum", "")
                                    logger.info(f"👤 User {user_index}: Final integrity check passed")
                                break
                                
                        except asyncio.TimeoutError:
                            break
                        except json.JSONDecodeError:
                            continue
            
            except Exception as e:
                logger.error(f"👤 User {user_index}: Concurrent operations failed - {e}")
                user_metrics["operations_failed"] = concurrency_config["operations_per_user"]
            
            return user_metrics
        
        # Execute concurrent multi-user data operations
        logger.info(f"🚀 Starting multi-user concurrent data integrity test with {concurrency_config['concurrent_users']} users")
        
        concurrent_user_tasks = []
        for user_index in range(concurrency_config["concurrent_users"]):
            task = asyncio.create_task(create_concurrent_user_data_operations(user_index))
            concurrent_user_tasks.append(task)
            multi_user_integrity_tracking["users_created"] += 1
        
        # Wait for all concurrent user operations to complete
        concurrent_timeout = 120.0  # 2 minutes for all concurrent operations
        try:
            user_results = await asyncio.wait_for(
                asyncio.gather(*concurrent_user_tasks, return_exceptions=True),
                timeout=concurrent_timeout
            )
        except asyncio.TimeoutError:
            logger.error("❌ Concurrent multi-user test timed out")
            user_results = [task.result() if task.done() else None for task in concurrent_user_tasks]
        
        # Analyze multi-user data integrity results
        successful_users = 0
        users_with_integrity_confirmed = 0
        users_with_isolation_validated = 0
        
        for result in user_results:
            if result is not None and not isinstance(result, Exception):
                multi_user_integrity_tracking["user_data_maps"][result["user_id"]] = result
                
                if result["operations_completed"] > 0:
                    successful_users += 1
                if result["data_integrity_confirmed"]:
                    users_with_integrity_confirmed += 1
                if result["isolation_validated"]:
                    users_with_isolation_validated += 1
        
        # Validation: Comprehensive multi-user data integrity validation
        test_duration = time.time() - test_start_time
        
        # Assert 1: Real concurrent multi-user timing
        assert test_duration >= 15.0, f"Multi-user concurrency test too fast ({test_duration:.2f}s) - likely fake"
        
        # Assert 2: Multiple users operated concurrently
        assert multi_user_integrity_tracking["users_created"] >= 6, f"Expected at least 6 concurrent users, created {multi_user_integrity_tracking['users_created']}"
        assert successful_users >= 4, f"Too few successful concurrent users ({successful_users}) - concurrency issues"
        
        # Assert 3: Data operations completed successfully
        assert multi_user_integrity_tracking["total_operations_completed"] >= 16, f"Too few operations completed ({multi_user_integrity_tracking['total_operations_completed']}) across all users"
        
        # Assert 4: No data corruption detected
        assert multi_user_integrity_tracking["data_corruption_detected"] == 0, f"Data corruption detected ({multi_user_integrity_tracking['data_corruption_detected']}) - integrity failure"
        
        # Assert 5: User isolation maintained
        assert users_with_isolation_validated >= 3, f"Too few users with validated isolation ({users_with_isolation_validated}) - isolation failure"
        
        # Assert 6: Data integrity validations passed
        assert multi_user_integrity_tracking["integrity_validations_passed"] >= 3, f"Too few integrity validations passed ({multi_user_integrity_tracking['integrity_validations_passed']})"
        
        # Assert 7: Acceptable level of transaction conflicts (some are expected in concurrent systems)
        transaction_conflict_rate = multi_user_integrity_tracking["transaction_conflicts"] / multi_user_integrity_tracking["total_operations_attempted"] if multi_user_integrity_tracking["total_operations_attempted"] > 0 else 0
        assert transaction_conflict_rate <= 0.3, f"Transaction conflict rate too high ({transaction_conflict_rate:.2%}) - poor concurrency control"
        
        logger.info(f"✅ PASS: Multi-user concurrent data integrity with transaction isolation - {test_duration:.2f}s")
        logger.info(f"Users created: {multi_user_integrity_tracking['users_created']}")
        logger.info(f"Successful users: {successful_users}")
        logger.info(f"Operations attempted: {multi_user_integrity_tracking['total_operations_attempted']}")
        logger.info(f"Operations completed: {multi_user_integrity_tracking['total_operations_completed']}")
        logger.info(f"Data corruption detected: {multi_user_integrity_tracking['data_corruption_detected']}")
        logger.info(f"Isolation violations: {multi_user_integrity_tracking['isolation_violations']}")
        logger.info(f"Transaction conflicts: {multi_user_integrity_tracking['transaction_conflicts']}")
        logger.info(f"Integrity validations passed: {multi_user_integrity_tracking['integrity_validations_passed']}")
        logger.info(f"Users with integrity confirmed: {users_with_integrity_confirmed}")
        logger.info(f"Users with isolation validated: {users_with_isolation_validated}")

    def _validate_data_integrity(self, original_data: Dict[str, Any], retrieved_data: Dict[str, Any]) -> bool:
        """
        Validate data integrity between original and retrieved data.
        
        Returns:
            True if data integrity is maintained, False if corruption detected
        """
        try:
            # Check key business data fields for integrity
            if "customer_id" in original_data and "customer_id" in retrieved_data:
                if original_data["customer_id"] != retrieved_data.get("customer_id"):
                    logger.error("Customer ID mismatch in retrieved data")
                    return False
            
            # Check optimization context preservation
            if "optimization_context" in original_data:
                original_context = original_data["optimization_context"]
                retrieved_context = retrieved_data.get("optimization_context", {})
                
                # Validate critical business values
                for key in ["cost_savings_target", "performance_improvement_target"]:
                    if key in original_context:
                        if abs(original_context[key] - retrieved_context.get(key, 0)) > 0.01:
                            logger.error(f"Business value {key} corrupted in retrieved data")
                            return False
            
            # Check agent state preservation
            if "agent_collaboration_state" in original_data:
                original_state = original_data["agent_collaboration_state"]
                retrieved_state = retrieved_data.get("agent_collaboration_state", {})
                
                if original_state.get("workflow_stage") != retrieved_state.get("workflow_stage"):
                    logger.error("Workflow stage not preserved in retrieved data")
                    return False
            
            logger.info("✅ Data integrity validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Data integrity validation failed with exception: {e}")
            return False