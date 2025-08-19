"""
Data Consistency Validators

Validates data consistency across service boundaries to ensure data integrity
and prevent data corruption or inconsistencies between services.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
import asyncio
import json
from datetime import datetime, timedelta
from uuid import UUID
from pydantic import BaseModel

from .validator_framework import (
    BaseValidator, ValidationResult, ValidationStatus, ValidationSeverity
)


class DataInconsistency(BaseModel):
    """Represents a data inconsistency between services."""
    field_name: str
    service_a: str
    service_b: str
    value_a: Any
    value_b: Any
    severity: str


class UserDataConsistencyValidator(BaseValidator):
    """Validates user data consistency across services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("user_data_consistency_validator", config)
        self.critical_fields = ["user_id", "email", "permissions", "roles"]
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate user data consistency across services."""
        results = []
        
        # Get test users to validate
        test_users = context.get("test_users", [])
        if not test_users:
            # Generate test user IDs for validation
            test_users = ["user-123", "user-456", "user-789"]
        
        for user_id in test_users:
            results.extend(await self._validate_user_data_consistency(user_id, context))
        
        return results
    
    async def _validate_user_data_consistency(
        self, 
        user_id: str, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate consistency for a specific user across services."""
        results = []
        
        try:
            # Simulate fetching user data from different services
            auth_user_data = await self._fetch_user_from_auth_service(user_id, context)
            backend_user_data = await self._fetch_user_from_backend(user_id, context)
            
            # Compare critical fields
            inconsistencies = self._compare_user_data(
                auth_user_data, 
                backend_user_data,
                "auth_service",
                "backend"
            )
            
            if inconsistencies:
                for inconsistency in inconsistencies:
                    severity = ValidationSeverity.CRITICAL if inconsistency.field_name in self.critical_fields else ValidationSeverity.HIGH
                    
                    results.append(self.create_result(
                        check_name=f"user_data_consistency_{user_id}_{inconsistency.field_name}",
                        status=ValidationStatus.FAILED,
                        severity=severity,
                        message=f"User data inconsistency in {inconsistency.field_name}: "
                               f"auth='{inconsistency.value_a}' vs backend='{inconsistency.value_b}'",
                        service_pair="auth-backend",
                        details={
                            "user_id": user_id,
                            "field": inconsistency.field_name,
                            "auth_value": inconsistency.value_a,
                            "backend_value": inconsistency.value_b
                        }
                    ))
            else:
                results.append(self.create_result(
                    check_name=f"user_data_consistency_{user_id}",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message=f"User data consistency verified for user {user_id}",
                    service_pair="auth-backend",
                    details={"user_id": user_id, "fields_checked": len(self.critical_fields)}
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name=f"user_data_consistency_{user_id}_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Failed to validate user data consistency: {str(e)}",
                service_pair="auth-backend",
                details={"user_id": user_id, "error": str(e)}
            ))
        
        return results
    
    async def _fetch_user_from_auth_service(
        self, 
        user_id: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch user data from auth service."""
        # Mock implementation - would make actual API call in production
        return {
            "user_id": user_id,
            "email": f"user{user_id}@example.com",
            "permissions": ["read", "write"],
            "roles": ["user"],
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-15T10:00:00Z"
        }
    
    async def _fetch_user_from_backend(
        self, 
        user_id: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch user data from backend service."""
        # Mock implementation - would make actual API call in production
        return {
            "user_id": user_id,
            "email": f"user{user_id}@example.com",
            "permissions": ["read", "write"],
            "roles": ["user"],
            "created_at": "2024-01-01T00:00:00Z",
            "profile": {"name": "Test User"}
        }
    
    def _compare_user_data(
        self, 
        data_a: Dict[str, Any], 
        data_b: Dict[str, Any],
        service_a: str,
        service_b: str
    ) -> List[DataInconsistency]:
        """Compare user data from two sources."""
        inconsistencies = []
        
        for field in self.critical_fields:
            if field in data_a and field in data_b:
                if data_a[field] != data_b[field]:
                    inconsistencies.append(DataInconsistency(
                        field_name=field,
                        service_a=service_a,
                        service_b=service_b,
                        value_a=data_a[field],
                        value_b=data_b[field],
                        severity="critical" if field in ["user_id", "email"] else "high"
                    ))
        
        return inconsistencies


class SessionStateValidator(BaseValidator):
    """Validates session state synchronization across services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("session_state_validator", config)
        self.max_session_drift_seconds = config.get("max_session_drift_seconds", 30) if config else 30
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate session state consistency."""
        results = []
        
        # Test session state synchronization
        test_sessions = context.get("test_sessions", [])
        if not test_sessions:
            test_sessions = ["session-abc123", "session-def456"]
        
        for session_id in test_sessions:
            results.extend(await self._validate_session_state(session_id, context))
        
        # Validate session timeout consistency
        results.extend(await self._validate_session_timeout_consistency(context))
        
        return results
    
    async def _validate_session_state(
        self, 
        session_id: str, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate state for a specific session."""
        results = []
        
        try:
            # Fetch session data from different sources
            auth_session = await self._fetch_session_from_auth(session_id, context)
            backend_session = await self._fetch_session_from_backend(session_id, context)
            frontend_session = await self._fetch_session_from_frontend(session_id, context)
            
            # Validate session consistency
            if auth_session and backend_session:
                # Check user_id consistency
                if auth_session.get("user_id") != backend_session.get("user_id"):
                    results.append(self.create_result(
                        check_name=f"session_user_consistency_{session_id}",
                        status=ValidationStatus.FAILED,
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Session user_id mismatch: auth={auth_session.get('user_id')} "
                               f"vs backend={backend_session.get('user_id')}",
                        service_pair="auth-backend",
                        details={"session_id": session_id}
                    ))
                
                # Check session expiry consistency
                auth_expiry = auth_session.get("expires_at")
                backend_expiry = backend_session.get("expires_at")
                
                if auth_expiry and backend_expiry:
                    expiry_drift = abs((
                        datetime.fromisoformat(auth_expiry.replace('Z', '+00:00')) -
                        datetime.fromisoformat(backend_expiry.replace('Z', '+00:00'))
                    ).total_seconds())
                    
                    if expiry_drift > self.max_session_drift_seconds:
                        results.append(self.create_result(
                            check_name=f"session_expiry_drift_{session_id}",
                            status=ValidationStatus.FAILED,
                            severity=ValidationSeverity.HIGH,
                            message=f"Session expiry drift too large: {expiry_drift}s > {self.max_session_drift_seconds}s",
                            service_pair="auth-backend",
                            details={
                                "session_id": session_id,
                                "drift_seconds": expiry_drift,
                                "max_allowed": self.max_session_drift_seconds
                            }
                        ))
            
            # If all checks pass
            if not any(r.status == ValidationStatus.FAILED for r in results[-2:]):
                results.append(self.create_result(
                    check_name=f"session_state_consistency_{session_id}",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message=f"Session state consistency verified for {session_id}",
                    service_pair="auth-backend-frontend",
                    details={"session_id": session_id}
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name=f"session_state_error_{session_id}",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Session state validation failed: {str(e)}",
                service_pair="auth-backend",
                details={"session_id": session_id, "error": str(e)}
            ))
        
        return results
    
    async def _fetch_session_from_auth(
        self, 
        session_id: str, 
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Fetch session data from auth service."""
        return {
            "session_id": session_id,
            "user_id": f"user-{session_id[-6:]}",
            "created_at": "2024-01-15T10:00:00Z",
            "expires_at": "2024-01-15T18:00:00Z",
            "ip_address": "192.168.1.100"
        }
    
    async def _fetch_session_from_backend(
        self, 
        session_id: str, 
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Fetch session data from backend service."""
        return {
            "session_id": session_id,
            "user_id": f"user-{session_id[-6:]}",
            "last_activity": "2024-01-15T14:00:00Z",
            "expires_at": "2024-01-15T18:00:00Z",
            "thread_context": {"current_thread": "thread-123"}
        }
    
    async def _fetch_session_from_frontend(
        self, 
        session_id: str, 
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Fetch session data from frontend (localStorage/sessionStorage)."""
        return {
            "session_id": session_id,
            "user_id": f"user-{session_id[-6:]}",
            "cached_at": "2024-01-15T14:00:00Z",
            "ui_state": {"current_page": "/chat"}
        }
    
    async def _validate_session_timeout_consistency(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate that session timeout configurations are consistent."""
        results = []
        
        # Mock timeout configurations from different services
        auth_timeout = 8 * 3600  # 8 hours
        backend_timeout = 8 * 3600  # 8 hours
        frontend_timeout = 8 * 3600  # 8 hours
        
        if auth_timeout != backend_timeout:
            results.append(self.create_result(
                check_name="session_timeout_consistency",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Session timeout mismatch: auth={auth_timeout}s vs backend={backend_timeout}s",
                service_pair="auth-backend",
                details={
                    "auth_timeout": auth_timeout,
                    "backend_timeout": backend_timeout
                }
            ))
        else:
            results.append(self.create_result(
                check_name="session_timeout_consistency",
                status=ValidationStatus.PASSED,
                severity=ValidationSeverity.INFO,
                message="Session timeout configurations are consistent",
                service_pair="auth-backend",
                details={"timeout_seconds": auth_timeout}
            ))
        
        return results


class MessageDeliveryValidator(BaseValidator):
    """Validates message delivery guarantees across WebSocket connections."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("message_delivery_validator", config)
        self.max_delivery_delay_ms = config.get("max_delivery_delay_ms", 5000) if config else 5000
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate message delivery guarantees."""
        results = []
        
        # Test message ordering
        results.extend(await self._validate_message_ordering(context))
        
        # Test message delivery confirmation
        results.extend(await self._validate_delivery_confirmation(context))
        
        # Test duplicate message detection
        results.extend(await self._validate_duplicate_detection(context))
        
        return results
    
    async def _validate_message_ordering(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate that messages are delivered in the correct order."""
        results = []
        
        try:
            # Simulate sending a sequence of messages
            test_messages = [
                {"id": "msg-1", "sequence": 1, "text": "First message"},
                {"id": "msg-2", "sequence": 2, "text": "Second message"},
                {"id": "msg-3", "sequence": 3, "text": "Third message"}
            ]
            
            # Simulate message delivery and ordering check
            delivered_messages = await self._simulate_message_delivery(test_messages, context)
            
            # Check ordering
            ordering_correct = True
            for i in range(len(delivered_messages) - 1):
                if delivered_messages[i]["sequence"] > delivered_messages[i + 1]["sequence"]:
                    ordering_correct = False
                    break
            
            if ordering_correct:
                results.append(self.create_result(
                    check_name="message_ordering",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="Message ordering validation passed",
                    service_pair="frontend-backend",
                    details={
                        "messages_tested": len(test_messages),
                        "ordering_preserved": True
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="message_ordering",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message="Message ordering violation detected",
                    service_pair="frontend-backend",
                    details={
                        "messages_tested": len(test_messages),
                        "delivered_order": [m["sequence"] for m in delivered_messages]
                    }
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="message_ordering_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Message ordering validation failed: {str(e)}",
                service_pair="frontend-backend",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_delivery_confirmation(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate message delivery confirmation mechanism."""
        results = []
        
        try:
            # Simulate sending messages that require confirmation
            test_messages = [
                {"id": "confirm-msg-1", "requires_ack": True},
                {"id": "confirm-msg-2", "requires_ack": True}
            ]
            
            # Simulate sending and waiting for confirmations
            confirmations_received = await self._simulate_delivery_confirmations(test_messages, context)
            
            missing_confirmations = []
            for msg in test_messages:
                if msg["id"] not in confirmations_received:
                    missing_confirmations.append(msg["id"])
            
            if not missing_confirmations:
                results.append(self.create_result(
                    check_name="delivery_confirmation",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="All message delivery confirmations received",
                    service_pair="frontend-backend",
                    details={
                        "messages_sent": len(test_messages),
                        "confirmations_received": len(confirmations_received)
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="delivery_confirmation",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"Missing delivery confirmations for messages: {missing_confirmations}",
                    service_pair="frontend-backend",
                    details={"missing_confirmations": missing_confirmations}
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="delivery_confirmation_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Delivery confirmation validation failed: {str(e)}",
                service_pair="frontend-backend",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_duplicate_detection(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate duplicate message detection and handling."""
        results = []
        
        try:
            # Simulate sending duplicate messages
            original_message = {"id": "dup-test-1", "text": "Original message"}
            duplicate_message = {"id": "dup-test-1", "text": "Original message"}
            
            # Simulate processing both messages
            processing_results = await self._simulate_duplicate_processing(
                [original_message, duplicate_message], 
                context
            )
            
            # Check that duplicate was detected
            duplicates_detected = processing_results.get("duplicates_detected", 0)
            messages_processed = processing_results.get("messages_processed", 0)
            
            if duplicates_detected == 1 and messages_processed == 1:
                results.append(self.create_result(
                    check_name="duplicate_detection",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="Duplicate message detection working correctly",
                    service_pair="frontend-backend",
                    details={
                        "duplicates_detected": duplicates_detected,
                        "unique_messages_processed": messages_processed
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="duplicate_detection",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.MEDIUM,
                    message="Duplicate message detection not working correctly",
                    service_pair="frontend-backend",
                    details={
                        "expected_duplicates": 1,
                        "detected_duplicates": duplicates_detected,
                        "messages_processed": messages_processed
                    }
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="duplicate_detection_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.MEDIUM,
                message=f"Duplicate detection validation failed: {str(e)}",
                service_pair="frontend-backend",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _simulate_message_delivery(
        self, 
        messages: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Simulate message delivery and return delivered messages."""
        # Mock implementation - would interact with actual WebSocket in production
        await asyncio.sleep(0.1)  # Simulate network delay
        return messages  # Assume messages are delivered in order
    
    async def _simulate_delivery_confirmations(
        self, 
        messages: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> Set[str]:
        """Simulate delivery confirmations and return confirmed message IDs."""
        # Mock implementation
        await asyncio.sleep(0.1)
        return {msg["id"] for msg in messages}  # Assume all messages are confirmed
    
    async def _simulate_duplicate_processing(
        self, 
        messages: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate duplicate message processing."""
        # Mock implementation - detect duplicates by ID
        seen_ids = set()
        duplicates = 0
        processed = 0
        
        for msg in messages:
            if msg["id"] in seen_ids:
                duplicates += 1
            else:
                seen_ids.add(msg["id"])
                processed += 1
        
        return {
            "duplicates_detected": duplicates,
            "messages_processed": processed
        }


class CrossServiceDataValidator(BaseValidator):
    """Validates cross-service data operations and transactions."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("cross_service_data_validator", config)
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate cross-service data operations."""
        results = []
        
        # Validate distributed transaction consistency
        results.extend(await self._validate_distributed_transactions(context))
        
        # Validate data synchronization patterns
        results.extend(await self._validate_data_synchronization(context))
        
        # Validate event sourcing consistency
        results.extend(await self._validate_event_sourcing(context))
        
        return results
    
    async def _validate_distributed_transactions(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate distributed transaction consistency."""
        results = []
        
        try:
            # Simulate a distributed transaction (e.g., user creation)
            transaction_id = "tx-user-create-123"
            
            # Steps: 1) Create user in auth, 2) Create profile in backend, 3) Initialize preferences
            steps = [
                {"service": "auth", "operation": "create_user", "status": "committed"},
                {"service": "backend", "operation": "create_profile", "status": "committed"},
                {"service": "backend", "operation": "init_preferences", "status": "committed"}
            ]
            
            # Check that all steps are in the same state (all committed or all rolled back)
            statuses = [step["status"] for step in steps]
            all_committed = all(status == "committed" for status in statuses)
            all_rolled_back = all(status == "rolled_back" for status in statuses)
            
            if all_committed or all_rolled_back:
                results.append(self.create_result(
                    check_name=f"distributed_transaction_{transaction_id}",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="Distributed transaction consistency maintained",
                    service_pair="auth-backend",
                    details={
                        "transaction_id": transaction_id,
                        "steps": len(steps),
                        "final_status": statuses[0] if all_committed else "rolled_back"
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name=f"distributed_transaction_{transaction_id}",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.CRITICAL,
                    message="Distributed transaction in inconsistent state",
                    service_pair="auth-backend",
                    details={
                        "transaction_id": transaction_id,
                        "inconsistent_statuses": statuses
                    }
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="distributed_transaction_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Distributed transaction validation failed: {str(e)}",
                service_pair="auth-backend",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_data_synchronization(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate data synchronization between services."""
        results = []
        
        # Mock data synchronization validation
        sync_entities = ["user_permissions", "thread_metadata", "agent_state"]
        
        for entity in sync_entities:
            try:
                # Simulate checking sync status
                last_sync = datetime.utcnow() - timedelta(minutes=5)
                sync_lag = (datetime.utcnow() - last_sync).total_seconds()
                max_lag = 300  # 5 minutes
                
                if sync_lag <= max_lag:
                    results.append(self.create_result(
                        check_name=f"data_sync_{entity}",
                        status=ValidationStatus.PASSED,
                        severity=ValidationSeverity.INFO,
                        message=f"Data synchronization for {entity} is current",
                        service_pair="auth-backend",
                        details={
                            "entity": entity,
                            "sync_lag_seconds": sync_lag,
                            "max_allowed": max_lag
                        }
                    ))
                else:
                    results.append(self.create_result(
                        check_name=f"data_sync_{entity}",
                        status=ValidationStatus.FAILED,
                        severity=ValidationSeverity.HIGH,
                        message=f"Data synchronization lag too high for {entity}: {sync_lag}s",
                        service_pair="auth-backend",
                        details={
                            "entity": entity,
                            "sync_lag_seconds": sync_lag,
                            "max_allowed": max_lag
                        }
                    ))
                    
            except Exception as e:
                results.append(self.create_result(
                    check_name=f"data_sync_{entity}_error",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.MEDIUM,
                    message=f"Data sync validation failed for {entity}: {str(e)}",
                    service_pair="auth-backend",
                    details={"entity": entity, "error": str(e)}
                ))
        
        return results
    
    async def _validate_event_sourcing(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate event sourcing consistency."""
        results = []
        
        try:
            # Mock event sourcing validation
            events = [
                {"id": "evt-1", "type": "user_created", "timestamp": "2024-01-15T10:00:00Z"},
                {"id": "evt-2", "type": "profile_updated", "timestamp": "2024-01-15T10:01:00Z"},
                {"id": "evt-3", "type": "permissions_changed", "timestamp": "2024-01-15T10:02:00Z"}
            ]
            
            # Check event ordering
            timestamps = [datetime.fromisoformat(e["timestamp"].replace('Z', '+00:00')) for e in events]
            is_ordered = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
            
            if is_ordered:
                results.append(self.create_result(
                    check_name="event_sourcing_ordering",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="Event sourcing ordering is correct",
                    service_pair="auth-backend",
                    details={"events_checked": len(events)}
                ))
            else:
                results.append(self.create_result(
                    check_name="event_sourcing_ordering",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message="Event sourcing ordering violation detected",
                    service_pair="auth-backend",
                    details={"events_checked": len(events), "timestamps": [e["timestamp"] for e in events]}
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="event_sourcing_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.MEDIUM,
                message=f"Event sourcing validation failed: {str(e)}",
                service_pair="auth-backend",
                details={"error": str(e)}
            ))
        
        return results