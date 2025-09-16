"""
Modifications to be applied to UnifiedWebSocketManager for Issue #712 remediation.
"""

# Constructor modification - add after line ~311
CONSTRUCTOR_MODIFICATION = '''
    def __init__(self, mode: WebSocketManagerMode = WebSocketManagerMode.UNIFIED, user_context: Optional[Any] = None, config: Optional[Dict[str, Any]] = None, _ssot_authorization_token: Optional[str] = None):
        """Initialize UnifiedWebSocketManager - ALL MODES CONSOLIDATED TO UNIFIED.

        SSOT MIGRATION NOTICE: All WebSocket modes now use unified initialization.
        User isolation is achieved through UserExecutionContext, not separate modes.

        ISSUE #712 ENHANCEMENT: Added SSOT validation and authorization controls.

        Args:
            mode: DEPRECATED - All modes redirect to UNIFIED (kept for backward compatibility)
            user_context: User execution context for proper user isolation (REQUIRED for SSOT compliance)
            config: Configuration dictionary (optional)
            _ssot_authorization_token: Internal token for SSOT factory pattern enforcement
        """
        # ISSUE #712 FIX: SSOT Validation Integration
        from netra_backend.app.websocket_core.ssot_validation_enhancer import (
            validate_websocket_manager_creation,
            FactoryBypassDetected,
            UserIsolationViolation
        )

        # PHASE 1: Direct instantiation prevention (Issue #712)
        # Check if this is being created through proper factory pattern
        if _ssot_authorization_token is None:
            error_msg = "Direct instantiation not allowed. Use get_websocket_manager() factory function."
            logger.error(f"SSOT VIOLATION: {error_msg}")
            raise FactoryBypassDetected(error_msg)

        # Validate authorization token format (basic security)
        if not isinstance(_ssot_authorization_token, str) or len(_ssot_authorization_token) < 10:
            error_msg = "Invalid SSOT authorization token format"
            logger.error(f"SSOT VIOLATION: {error_msg}")
            raise FactoryBypassDetected(error_msg)

        # PHASE 1: User context requirement enforcement (Issue #712)
        if user_context is None:
            error_msg = "UserExecutionContext required for proper user isolation"
            logger.error(f"USER ISOLATION VIOLATION: {error_msg}")
            raise UserIsolationViolation(error_msg)

        # DEPRECATED: Mode is ignored - all instances use unified behavior
        self.mode = WebSocketManagerMode.UNIFIED  # Force unified mode
        self.user_context = user_context
        self.config = config or {}

        # PHASE 1: SSOT validation integration (Issue #712)
        try:
            validate_websocket_manager_creation(
                manager_instance=self,
                user_context=user_context,
                creation_method="factory_authorized"
            )
            logger.info(f"SSOT validation passed for user {getattr(user_context, 'user_id', 'unknown')}")
        except Exception as e:
            logger.error(f"SSOT validation failed: {e}")
            # Re-raise to prevent creation of non-compliant instances
            raise
'''

# User isolation validation methods to add
USER_ISOLATION_METHODS = '''
    def _validate_user_isolation(self, user_id: str, operation: str = "unknown") -> bool:
        """
        ISSUE #712 FIX: Validate user isolation for operations.

        This method enforces user isolation by ensuring operations are only
        performed on behalf of the user this manager was created for.

        Args:
            user_id: User ID requesting the operation
            operation: Description of operation for logging

        Returns:
            bool: True if validation passes

        Raises:
            UserIsolationViolation: If user isolation is violated in strict mode
        """
        from netra_backend.app.websocket_core.ssot_validation_enhancer import validate_user_isolation

        try:
            return validate_user_isolation(
                manager_instance=self,
                user_id=user_id,
                operation=operation
            )
        except Exception as e:
            logger.error(f"User isolation validation failed for {operation}: {e}")
            raise

    def _prevent_cross_user_event_bleeding(self, event_data: Dict[str, Any], target_user_id: str) -> Dict[str, Any]:
        """
        ISSUE #712 FIX: Prevent cross-user event bleeding.

        This method ensures events are only delivered to the intended user
        and adds isolation metadata to prevent contamination.

        Args:
            event_data: Event data to be sent
            target_user_id: User ID that should receive this event

        Returns:
            Dict[str, Any]: Event data with isolation metadata
        """
        # Add user isolation metadata
        isolated_event = event_data.copy()
        isolated_event['_user_isolation'] = {
            'target_user_id': target_user_id,
            'manager_user_id': getattr(self.user_context, 'user_id', None),
            'isolation_token': f"{target_user_id}_{time.time()}",
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Validate user match
        manager_user_id = getattr(self.user_context, 'user_id', None)
        if manager_user_id and str(manager_user_id) != str(target_user_id):
            logger.warning(f"Cross-user event bleeding prevented: manager_user={manager_user_id}, target_user={target_user_id}")
            raise UserIsolationViolation(f"Event targeting different user: {target_user_id} != {manager_user_id}")

        return isolated_event
'''