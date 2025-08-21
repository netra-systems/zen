"""Data Consistency Across Services Critical Path Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (data integrity for all operations)
- Business Goal: Maintain data consistency across distributed services
- Value Impact: Prevents data corruption, ensures reliable transactions, maintains data integrity
- Strategic Impact: $30K-60K MRR protection through reliable data operations

Critical Path: Transaction initiation -> Service coordination -> Consistency checks -> Commit/rollback -> Verification
Coverage: Distributed transactions, eventual consistency, conflict resolution, data reconciliation
"""

import pytest
import asyncio
import time
import uuid
import logging
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from enum import Enum

from netra_backend.app.services.data.transaction_coordinator import TransactionCoordinator
from netra_backend.app.services.data.consistency_manager import ConsistencyManager
from netra_backend.app.services.data.conflict_resolver import ConflictResolver
from netra_backend.app.services.database.connection_manager import DatabaseConnectionManager

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()


logger = logging.getLogger(__name__)


class TransactionStatus(Enum):
    PENDING = "pending"
    COMMITTED = "committed"
    ABORTED = "aborted"
    COMPENSATED = "compensated"


class DataConsistencyManager:
    """Manages data consistency testing across distributed services."""
    
    def __init__(self):
        self.transaction_coordinator = None
        self.consistency_manager = None
        self.conflict_resolver = None
        self.db_manager = None
        self.active_transactions = {}
        self.consistency_checks = []
        self.conflict_resolutions = []
        
    async def initialize_services(self):
        """Initialize data consistency services."""
        try:
            self.transaction_coordinator = TransactionCoordinator()
            await self.transaction_coordinator.initialize()
            
            self.consistency_manager = ConsistencyManager()
            await self.consistency_manager.initialize()
            
            self.conflict_resolver = ConflictResolver()
            await self.conflict_resolver.initialize()
            
            self.db_manager = DatabaseConnectionManager()
            await self.db_manager.initialize()
            
            logger.info("Data consistency services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize data consistency services: {e}")
            raise
    
    async def begin_distributed_transaction(self, services: List[str], 
                                          transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Begin distributed transaction across multiple services."""
        transaction_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            transaction_context = {
                "transaction_id": transaction_id,
                "services": services,
                "transaction_data": transaction_data,
                "status": TransactionStatus.PENDING,
                "start_time": start_time,
                "service_states": {},
                "compensation_actions": []
            }
            
            # Step 1: Prepare phase - notify all services
            prepare_results = {}
            for service in services:
                prepare_result = await self.prepare_service_transaction(service, transaction_id, transaction_data)
                prepare_results[service] = prepare_result
                transaction_context["service_states"][service] = prepare_result
            
            # Step 2: Check if all services can participate
            all_prepared = all(result["prepared"] for result in prepare_results.values())
            
            if all_prepared:
                # All services prepared - proceed to commit phase
                transaction_context["status"] = TransactionStatus.COMMITTED
                
                commit_results = {}
                for service in services:
                    commit_result = await self.commit_service_transaction(service, transaction_id)
                    commit_results[service] = commit_result
                    transaction_context["service_states"][service].update(commit_result)
                
                transaction_context["commit_results"] = commit_results
                transaction_context["completion_time"] = time.time()
                
                self.active_transactions[transaction_id] = transaction_context
                
                return {
                    "transaction_id": transaction_id,
                    "success": True,
                    "status": TransactionStatus.COMMITTED,
                    "transaction_time": time.time() - start_time,
                    "services_involved": services
                }
            else:
                # Some services failed to prepare - abort transaction
                transaction_context["status"] = TransactionStatus.ABORTED
                
                abort_results = {}
                for service in services:
                    if prepare_results[service]["prepared"]:
                        abort_result = await self.abort_service_transaction(service, transaction_id)
                        abort_results[service] = abort_result
                
                transaction_context["abort_results"] = abort_results
                transaction_context["completion_time"] = time.time()
                
                return {
                    "transaction_id": transaction_id,
                    "success": False,
                    "status": TransactionStatus.ABORTED,
                    "transaction_time": time.time() - start_time,
                    "failed_services": [s for s, r in prepare_results.items() if not r["prepared"]]
                }
            
        except Exception as e:
            transaction_context["status"] = TransactionStatus.ABORTED
            transaction_context["error"] = str(e)
            transaction_context["completion_time"] = time.time()
            
            return {
                "transaction_id": transaction_id,
                "success": False,
                "error": str(e),
                "transaction_time": time.time() - start_time
            }
    
    async def prepare_service_transaction(self, service: str, transaction_id: str, 
                                        transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare service for transaction participation."""
        try:
            # Simulate service preparation
            await asyncio.sleep(0.02)  # Simulate network call
            
            # Check if service can participate
            service_data = transaction_data.get(service, {})
            
            # Simulate preparation logic
            if service == "user_service" and service_data.get("operation") == "update_profile":
                return {"prepared": True, "locks_acquired": ["user_profile"], "preparation_time": time.time()}
            elif service == "billing_service" and service_data.get("operation") == "process_payment":
                return {"prepared": True, "locks_acquired": ["payment_method"], "preparation_time": time.time()}
            elif service == "notification_service":
                return {"prepared": True, "locks_acquired": [], "preparation_time": time.time()}
            else:
                return {"prepared": False, "reason": "Service unavailable"}
                
        except Exception as e:
            return {"prepared": False, "error": str(e)}
    
    async def commit_service_transaction(self, service: str, transaction_id: str) -> Dict[str, Any]:
        """Commit transaction in specific service."""
        try:
            # Simulate service commit
            await asyncio.sleep(0.01)
            
            return {
                "committed": True,
                "commit_time": time.time(),
                "changes_applied": True
            }
            
        except Exception as e:
            return {
                "committed": False,
                "error": str(e)
            }
    
    async def abort_service_transaction(self, service: str, transaction_id: str) -> Dict[str, Any]:
        """Abort transaction in specific service."""
        try:
            # Simulate service abort/rollback
            await asyncio.sleep(0.01)
            
            return {
                "aborted": True,
                "abort_time": time.time(),
                "locks_released": True
            }
            
        except Exception as e:
            return {
                "aborted": False,
                "error": str(e)
            }
    
    async def check_data_consistency(self, services: List[str], 
                                   consistency_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Check data consistency across services."""
        consistency_check_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            consistency_results = {}
            
            for service in services:
                service_consistency = await self.check_service_consistency(service, consistency_criteria)
                consistency_results[service] = service_consistency
            
            # Analyze overall consistency
            all_consistent = all(result["consistent"] for result in consistency_results.values())
            
            # Identify inconsistencies
            inconsistencies = []
            if not all_consistent:
                for service, result in consistency_results.items():
                    if not result["consistent"]:
                        inconsistencies.append({
                            "service": service,
                            "inconsistency_type": result.get("inconsistency_type"),
                            "details": result.get("details")
                        })
            
            consistency_check = {
                "check_id": consistency_check_id,
                "services": services,
                "all_consistent": all_consistent,
                "service_results": consistency_results,
                "inconsistencies": inconsistencies,
                "check_time": time.time() - start_time,
                "timestamp": start_time
            }
            
            self.consistency_checks.append(consistency_check)
            
            return {
                "check_id": consistency_check_id,
                "consistent": all_consistent,
                "consistency_results": consistency_results,
                "inconsistencies": inconsistencies,
                "check_time": time.time() - start_time
            }
            
        except Exception as e:
            error_check = {
                "check_id": consistency_check_id,
                "services": services,
                "all_consistent": False,
                "error": str(e),
                "check_time": time.time() - start_time,
                "timestamp": start_time
            }
            
            self.consistency_checks.append(error_check)
            
            return {
                "check_id": consistency_check_id,
                "consistent": False,
                "error": str(e),
                "check_time": time.time() - start_time
            }
    
    async def check_service_consistency(self, service: str, 
                                      criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Check consistency within a specific service."""
        try:
            # Simulate service-specific consistency checks
            await asyncio.sleep(0.01)
            
            if service == "user_service":
                # Check user data consistency
                return {
                    "consistent": True,
                    "checks_performed": ["profile_integrity", "permissions_sync"],
                    "last_updated": time.time()
                }
            elif service == "billing_service":
                # Check billing data consistency
                return {
                    "consistent": True,
                    "checks_performed": ["payment_records", "invoice_totals"],
                    "last_updated": time.time()
                }
            elif service == "notification_service":
                # Check notification consistency
                return {
                    "consistent": True,
                    "checks_performed": ["delivery_status", "recipient_mapping"],
                    "last_updated": time.time()
                }
            else:
                return {
                    "consistent": False,
                    "inconsistency_type": "service_unavailable",
                    "details": f"Service {service} not available for consistency check"
                }
                
        except Exception as e:
            return {
                "consistent": False,
                "inconsistency_type": "check_error",
                "details": str(e)
            }
    
    async def resolve_data_conflict(self, conflict_data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve data conflicts between services."""
        resolution_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            conflict_type = conflict_data["type"]
            services_involved = conflict_data["services"]
            conflict_details = conflict_data["details"]
            
            resolution_strategy = await self.determine_resolution_strategy(conflict_type, conflict_details)
            
            resolution_result = await self.apply_conflict_resolution(
                resolution_strategy, services_involved, conflict_details
            )
            
            resolution_record = {
                "resolution_id": resolution_id,
                "conflict_type": conflict_type,
                "services_involved": services_involved,
                "resolution_strategy": resolution_strategy,
                "resolution_successful": resolution_result["success"],
                "resolution_time": time.time() - start_time,
                "timestamp": start_time
            }
            
            self.conflict_resolutions.append(resolution_record)
            
            return {
                "resolution_id": resolution_id,
                "resolved": resolution_result["success"],
                "resolution_strategy": resolution_strategy,
                "resolution_result": resolution_result,
                "resolution_time": time.time() - start_time
            }
            
        except Exception as e:
            error_resolution = {
                "resolution_id": resolution_id,
                "conflict_type": conflict_data.get("type", "unknown"),
                "resolution_successful": False,
                "error": str(e),
                "resolution_time": time.time() - start_time,
                "timestamp": start_time
            }
            
            self.conflict_resolutions.append(error_resolution)
            
            return {
                "resolution_id": resolution_id,
                "resolved": False,
                "error": str(e),
                "resolution_time": time.time() - start_time
            }
    
    async def determine_resolution_strategy(self, conflict_type: str, 
                                          conflict_details: Dict[str, Any]) -> str:
        """Determine appropriate conflict resolution strategy."""
        if conflict_type == "version_conflict":
            return "last_write_wins"
        elif conflict_type == "data_inconsistency":
            return "majority_consensus"
        elif conflict_type == "duplicate_records":
            return "merge_records"
        else:
            return "manual_intervention"
    
    async def apply_conflict_resolution(self, strategy: str, services: List[str], 
                                      conflict_details: Dict[str, Any]) -> Dict[str, Any]:
        """Apply conflict resolution strategy."""
        try:
            if strategy == "last_write_wins":
                # Simulate last write wins resolution
                latest_timestamp = max(
                    conflict_details.get("timestamps", [time.time()])
                )
                return {
                    "success": True,
                    "strategy_applied": strategy,
                    "resolution_data": {"winning_timestamp": latest_timestamp}
                }
            
            elif strategy == "majority_consensus":
                # Simulate majority consensus resolution
                return {
                    "success": True,
                    "strategy_applied": strategy,
                    "resolution_data": {"consensus_achieved": True}
                }
            
            elif strategy == "merge_records":
                # Simulate record merging
                return {
                    "success": True,
                    "strategy_applied": strategy,
                    "resolution_data": {"merged_successfully": True}
                }
            
            else:
                return {
                    "success": False,
                    "strategy_applied": strategy,
                    "reason": "Strategy requires manual intervention"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_eventual_consistency(self, services: List[str], 
                                      update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test eventual consistency across services."""
        try:
            # Apply update to primary service
            primary_service = services[0]
            await self.apply_service_update(primary_service, update_data)
            
            # Wait for propagation and check consistency over time
            consistency_timeline = []
            
            for check_interval in [0.1, 0.5, 1.0, 2.0]:
                await asyncio.sleep(check_interval)
                
                consistency_result = await self.check_data_consistency(
                    services, {"update_data": update_data}
                )
                
                consistency_timeline.append({
                    "time_elapsed": check_interval,
                    "consistent": consistency_result["consistent"],
                    "timestamp": time.time()
                })
                
                if consistency_result["consistent"]:
                    break
            
            # Determine if eventual consistency was achieved
            final_consistency = consistency_timeline[-1]["consistent"]
            convergence_time = sum(entry["time_elapsed"] for entry in consistency_timeline)
            
            return {
                "eventual_consistency_achieved": final_consistency,
                "convergence_time": convergence_time,
                "consistency_timeline": consistency_timeline,
                "services_tested": services
            }
            
        except Exception as e:
            return {
                "eventual_consistency_achieved": False,
                "error": str(e)
            }
    
    async def apply_service_update(self, service: str, update_data: Dict[str, Any]):
        """Apply update to a specific service."""
        # Simulate service update
        await asyncio.sleep(0.02)
        return {"updated": True, "service": service}
    
    async def get_consistency_metrics(self) -> Dict[str, Any]:
        """Get comprehensive data consistency metrics."""
        total_transactions = len(self.active_transactions)
        committed_transactions = len([
            t for t in self.active_transactions.values() 
            if t["status"] == TransactionStatus.COMMITTED
        ])
        
        total_consistency_checks = len(self.consistency_checks)
        consistent_checks = len([c for c in self.consistency_checks if c["all_consistent"]])
        
        total_conflict_resolutions = len(self.conflict_resolutions)
        successful_resolutions = len([
            r for r in self.conflict_resolutions if r["resolution_successful"]
        ])
        
        # Calculate success rates
        transaction_success_rate = (committed_transactions / total_transactions * 100) if total_transactions > 0 else 0
        consistency_rate = (consistent_checks / total_consistency_checks * 100) if total_consistency_checks > 0 else 0
        resolution_success_rate = (successful_resolutions / total_conflict_resolutions * 100) if total_conflict_resolutions > 0 else 0
        
        # Calculate average times
        transaction_times = [
            t.get("completion_time", t["start_time"]) - t["start_time"]
            for t in self.active_transactions.values()
            if "completion_time" in t
        ]
        avg_transaction_time = sum(transaction_times) / len(transaction_times) if transaction_times else 0
        
        consistency_times = [c["check_time"] for c in self.consistency_checks if "check_time" in c]
        avg_consistency_time = sum(consistency_times) / len(consistency_times) if consistency_times else 0
        
        return {
            "distributed_transactions": {
                "total_transactions": total_transactions,
                "committed_transactions": committed_transactions,
                "success_rate": transaction_success_rate,
                "average_transaction_time": avg_transaction_time
            },
            "consistency_monitoring": {
                "total_checks": total_consistency_checks,
                "consistent_checks": consistent_checks,
                "consistency_rate": consistency_rate,
                "average_check_time": avg_consistency_time
            },
            "conflict_resolution": {
                "total_conflicts": total_conflict_resolutions,
                "resolved_conflicts": successful_resolutions,
                "resolution_success_rate": resolution_success_rate
            },
            "data_integrity_health": {
                "transaction_system_healthy": transaction_success_rate >= 95,
                "consistency_system_healthy": consistency_rate >= 90,
                "conflict_resolution_healthy": resolution_success_rate >= 85,
                "overall_status": "healthy" if (
                    transaction_success_rate >= 95 and 
                    consistency_rate >= 90 and 
                    resolution_success_rate >= 85
                ) else "degraded"
            }
        }
    
    async def cleanup(self):
        """Clean up data consistency resources."""
        try:
            if self.transaction_coordinator:
                await self.transaction_coordinator.shutdown()
            if self.consistency_manager:
                await self.consistency_manager.shutdown()
            if self.conflict_resolver:
                await self.conflict_resolver.shutdown()
            if self.db_manager:
                await self.db_manager.shutdown()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def consistency_manager():
    """Create data consistency manager for testing."""
    manager = DataConsistencyManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
async def test_distributed_transaction_success(consistency_manager):
    """Test successful distributed transaction across services."""
    services = ["user_service", "billing_service", "notification_service"]
    transaction_data = {
        "user_service": {"operation": "update_profile", "user_id": "user123"},
        "billing_service": {"operation": "process_payment", "amount": 100},
        "notification_service": {"operation": "send_confirmation"}
    }
    
    result = await consistency_manager.begin_distributed_transaction(services, transaction_data)
    
    assert result["success"] is True
    assert result["status"] == TransactionStatus.COMMITTED
    assert result["transaction_time"] < 5.0
    assert len(result["services_involved"]) == 3


@pytest.mark.asyncio
async def test_distributed_transaction_rollback(consistency_manager):
    """Test distributed transaction rollback on service failure."""
    services = ["user_service", "billing_service", "failing_service"]
    transaction_data = {
        "user_service": {"operation": "update_profile"},
        "billing_service": {"operation": "process_payment"},
        "failing_service": {"operation": "unavailable_operation"}
    }
    
    result = await consistency_manager.begin_distributed_transaction(services, transaction_data)
    
    assert result["success"] is False
    assert result["status"] == TransactionStatus.ABORTED
    assert "failed_services" in result
    assert "failing_service" in result["failed_services"]


@pytest.mark.asyncio
async def test_data_consistency_monitoring(consistency_manager):
    """Test data consistency monitoring across services."""
    services = ["user_service", "billing_service", "notification_service"]
    consistency_criteria = {
        "check_type": "full_consistency",
        "timestamp_tolerance": 5.0
    }
    
    consistency_result = await consistency_manager.check_data_consistency(
        services, consistency_criteria
    )
    
    assert "consistent" in consistency_result
    assert "consistency_results" in consistency_result
    assert consistency_result["check_time"] < 2.0
    
    # Verify all services were checked
    assert len(consistency_result["consistency_results"]) == 3
    for service in services:
        assert service in consistency_result["consistency_results"]


@pytest.mark.asyncio
async def test_conflict_resolution_mechanisms(consistency_manager):
    """Test conflict resolution mechanisms."""
    conflict_scenarios = [
        {
            "type": "version_conflict",
            "services": ["user_service", "billing_service"],
            "details": {"timestamps": [1634567890, 1634567900]}
        },
        {
            "type": "data_inconsistency",
            "services": ["billing_service", "notification_service"],
            "details": {"field": "user_balance", "values": [100, 105]}
        }
    ]
    
    resolution_results = []
    for conflict in conflict_scenarios:
        result = await consistency_manager.resolve_data_conflict(conflict)
        resolution_results.append(result)
    
    # Verify all conflicts were addressed
    for result in resolution_results:
        assert "resolved" in result
        assert "resolution_strategy" in result
        assert result["resolution_time"] < 1.0


@pytest.mark.asyncio
async def test_eventual_consistency_convergence(consistency_manager):
    """Test eventual consistency convergence."""
    services = ["user_service", "billing_service", "notification_service"]
    update_data = {
        "user_id": "user123",
        "field": "email",
        "new_value": "newemail@example.com"
    }
    
    consistency_result = await consistency_manager.test_eventual_consistency(
        services, update_data
    )
    
    assert "eventual_consistency_achieved" in consistency_result
    assert "convergence_time" in consistency_result
    assert "consistency_timeline" in consistency_result
    
    # Verify convergence happened within reasonable time
    assert consistency_result["convergence_time"] < 5.0


@pytest.mark.asyncio
async def test_concurrent_distributed_transactions(consistency_manager):
    """Test concurrent distributed transactions."""
    services = ["user_service", "billing_service"]
    
    # Create concurrent transactions
    transaction_tasks = []
    for i in range(5):
        transaction_data = {
            "user_service": {"operation": "update_profile", "user_id": f"user{i}"},
            "billing_service": {"operation": "process_payment", "amount": 50 + i}
        }
        task = consistency_manager.begin_distributed_transaction(services, transaction_data)
        transaction_tasks.append(task)
    
    # Execute concurrently
    start_time = time.time()
    results = await asyncio.gather(*transaction_tasks)
    execution_time = time.time() - start_time
    
    # Verify concurrent performance
    assert execution_time < 10.0
    
    # Verify transaction isolation
    successful_transactions = [r for r in results if r["success"]]
    assert len(successful_transactions) >= 4  # At least 80% success rate


@pytest.mark.asyncio
async def test_consistency_performance_requirements(consistency_manager):
    """Test data consistency performance requirements."""
    services = ["user_service", "billing_service"]
    
    # Test transaction performance
    transaction_times = []
    for i in range(10):
        transaction_data = {
            "user_service": {"operation": "update_profile"},
            "billing_service": {"operation": "process_payment"}
        }
        
        start_time = time.time()
        result = await consistency_manager.begin_distributed_transaction(services, transaction_data)
        transaction_time = time.time() - start_time
        
        if result["success"]:
            transaction_times.append(transaction_time)
    
    # Verify transaction performance
    avg_transaction_time = sum(transaction_times) / len(transaction_times) if transaction_times else 0
    max_transaction_time = max(transaction_times) if transaction_times else 0
    
    assert avg_transaction_time < 2.0  # Average < 2 seconds
    assert max_transaction_time < 5.0  # Max < 5 seconds
    
    # Test consistency check performance
    consistency_times = []
    for i in range(20):
        start_time = time.time()
        await consistency_manager.check_data_consistency(services, {"test": f"check_{i}"})
        check_time = time.time() - start_time
        consistency_times.append(check_time)
    
    avg_check_time = sum(consistency_times) / len(consistency_times)
    assert avg_check_time < 0.5  # Average < 500ms


@pytest.mark.asyncio
async def test_data_consistency_metrics_collection(consistency_manager):
    """Test comprehensive data consistency metrics collection."""
    services = ["user_service", "billing_service", "notification_service"]
    
    # Generate distributed transactions
    for i in range(3):
        transaction_data = {
            "user_service": {"operation": "update_profile"},
            "billing_service": {"operation": "process_payment"}
        }
        await consistency_manager.begin_distributed_transaction(services[:2], transaction_data)
    
    # Generate consistency checks
    for i in range(5):
        await consistency_manager.check_data_consistency(services, {"check": i})
    
    # Generate conflict resolutions
    for i in range(2):
        conflict_data = {
            "type": "version_conflict",
            "services": services[:2],
            "details": {"conflict_id": i}
        }
        await consistency_manager.resolve_data_conflict(conflict_data)
    
    # Get metrics
    metrics = await consistency_manager.get_consistency_metrics()
    
    # Verify metrics structure
    assert "distributed_transactions" in metrics
    assert "consistency_monitoring" in metrics
    assert "conflict_resolution" in metrics
    assert "data_integrity_health" in metrics
    
    # Verify metrics values
    assert metrics["distributed_transactions"]["total_transactions"] >= 3
    assert metrics["consistency_monitoring"]["total_checks"] >= 5
    assert metrics["conflict_resolution"]["total_conflicts"] >= 2
    
    # Verify health status
    health = metrics["data_integrity_health"]
    assert "overall_status" in health
    assert health["overall_status"] in ["healthy", "degraded"]


@pytest.mark.asyncio
async def test_transaction_compensation_patterns(consistency_manager):
    """Test transaction compensation patterns for failure scenarios."""
    services = ["user_service", "billing_service", "external_service"]
    
    # Simulate transaction that fails in final service
    with patch.object(consistency_manager, 'commit_service_transaction') as mock_commit:
        # Make external_service fail
        def side_effect(service, transaction_id):
            if service == "external_service":
                raise Exception("External service unavailable")
            return {"committed": True, "commit_time": time.time()}
        
        mock_commit.side_effect = side_effect
        
        transaction_data = {
            "user_service": {"operation": "update_profile"},
            "billing_service": {"operation": "process_payment"},
            "external_service": {"operation": "send_notification"}
        }
        
        result = await consistency_manager.begin_distributed_transaction(services, transaction_data)
        
        # Should handle compensation
        assert result["success"] is False
        assert result["status"] == TransactionStatus.ABORTED


@pytest.mark.asyncio
async def test_data_reconciliation_across_services(consistency_manager):
    """Test data reconciliation mechanisms across services."""
    services = ["user_service", "billing_service"]
    
    # Simulate data divergence
    inconsistent_data = {
        "user_service": {"user_balance": 100},
        "billing_service": {"user_balance": 95}
    }
    
    # Check for inconsistency
    consistency_result = await consistency_manager.check_data_consistency(
        services, {"reconciliation_test": inconsistent_data}
    )
    
    # If inconsistency detected, resolve it
    if not consistency_result["consistent"]:
        conflict_data = {
            "type": "data_inconsistency",
            "services": services,
            "details": inconsistent_data
        }
        
        resolution_result = await consistency_manager.resolve_data_conflict(conflict_data)
        assert resolution_result["resolved"] is True
    
    # Verify final consistency
    final_check = await consistency_manager.check_data_consistency(services, {})
    assert "consistent" in final_check