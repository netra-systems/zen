"""Modern Execution Helpers for Supervisor Agent

Focused helper methods for modern execution patterns.
Keeps supervisor main file under 300 lines.

Business Value: Standardized execution patterns with 25-line function limit.

SECURITY FIX: Issue #1017 - Enhanced security validation for user context extraction
and processing to prevent user isolation vulnerabilities and data contamination.
"""

import copy
import re
from typing import Any, Dict, Optional

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SupervisorExecutionHelpers:
    """Helper methods for modern supervisor execution."""
    
    def __init__(self, supervisor_agent):
        self.supervisor = supervisor_agent
    
    async def run_supervisor_workflow(self, context, run_id: str):
        """Run supervisor workflow using secure user execution context.

        SECURITY FIX: Issue #1017 - Validates input context type and sanitizes
        results to prevent cross-user data contamination.

        Args:
            context: UserExecutionContext or legacy DeepAgentState (for backwards compatibility)
            run_id: Unique run identifier

        Returns:
            UserExecutionContext with sanitized results

        Raises:
            ValueError: If context contains security violations
        """
        # Convert and validate context for security compliance
        validated_context = self._convert_and_validate_context(context)

        # Extract user request from validated context
        user_request = validated_context.agent_context.get('user_request', 'default_request')

        # Use secure context data for execution
        result = await self.supervisor.run(
            user_request,
            validated_context.thread_id,
            validated_context.user_id,
            run_id
        )

        # Sanitize supervisor result to prevent contamination
        sanitized_result = self._sanitize_supervisor_result(result, validated_context.user_id)

        # Return updated context (maintaining immutability)
        return validated_context.create_child_context(
            operation_name="supervisor_workflow",
            additional_agent_context={"workflow_result": sanitized_result}
        )
    
    async def handle_execution_failure(self, result: ExecutionResult, context: UserExecutionContext) -> None:
        """Handle execution failure with proper error handling."""
        logger.error(
            f"Supervisor execution failed for user {context.user_id}, thread {context.thread_id}: {result.error}",
            extra={"user_id": context.user_id, "thread_id": context.thread_id, "request_id": context.request_id}
        )
        # Could add fallback strategy here if needed
    
    async def execute_legacy_workflow(self, context: UserExecutionContext,
                                    run_id: str, stream_updates: bool) -> UserExecutionContext:
        """Legacy execution workflow adapted for secure user execution context."""
        flow_id = self._start_execution_flow(run_id)
        execution_data = self._extract_context_from_execution_context(context, run_id)
        updated_result = await self._execute_run_with_logging(flow_id, execution_data)
        return self._finalize_execution(flow_id, context, updated_result)
    
    def _start_execution_flow(self, run_id: str) -> str:
        """Start execution flow logging."""
        flow_id = self.supervisor.flow_logger.generate_flow_id()
        self.supervisor.flow_logger.start_flow(flow_id, run_id, 3)
        return flow_id
    
    def _extract_context_from_execution_context(self, context: UserExecutionContext, run_id: str) -> dict:
        """Extract execution context from secure user execution context.

        SECURITY FIX: Issue #1017 - Validates and sanitizes context data to prevent
        user isolation vulnerabilities and cross-user data contamination.
        """
        # Validate input context
        validated_context = self._validate_user_context_security(context)

        # Extract with security filtering
        extracted_data = {
            "thread_id": validated_context.thread_id,
            "user_id": validated_context.user_id,
            "user_prompt": self._sanitize_user_prompt(validated_context.agent_context.get('user_request', '')),
            "run_id": run_id
        }

        # Validate extracted data doesn't contain cross-user contamination
        self._validate_extracted_context_isolation(extracted_data, validated_context.user_id)

        return extracted_data
    
    async def _execute_run_with_logging(self, flow_id: str, context: dict) -> dict:
        """Execute run with flow logging."""
        self.supervisor.flow_logger.step_started(flow_id, "execute_run", "supervisor")
        updated_result = await self.supervisor.run(
            context["user_prompt"], context["thread_id"], context["user_id"], context["run_id"]
        )
        self.supervisor.flow_logger.step_completed(flow_id, "execute_run", "supervisor")
        return {"result": updated_result.to_dict() if hasattr(updated_result, 'to_dict') else str(updated_result)}
    
    def _finalize_execution(self, flow_id: str, context: UserExecutionContext, updated_result: dict) -> UserExecutionContext:
        """Finalize execution and create updated context.

        SECURITY FIX: Issue #1017 - Validates execution results to prevent
        cross-user data contamination in finalized context.
        """
        # Validate execution results before adding to context
        secure_result = self._sanitize_execution_result(updated_result, context.user_id)

        # Create child context with sanitized execution results
        updated_context = context.create_child_context(
            operation_name="finalized_execution",
            additional_agent_context=secure_result
        )
        self.supervisor.flow_logger.complete_flow(flow_id)
        return updated_context

    def _validate_user_context_security(self, context: UserExecutionContext) -> UserExecutionContext:
        """Validate user context for security threats and user isolation.

        SECURITY FIX: Issue #1017 - Validates UserExecutionContext to ensure
        proper user isolation and prevent cross-user data contamination.

        Args:
            context: The user execution context to validate

        Returns:
            Validated context (deep copy to prevent mutation)

        Raises:
            ValueError: If security violations are detected
        """
        if not isinstance(context, UserExecutionContext):
            raise ValueError("SECURITY VIOLATION: Invalid context type - only UserExecutionContext allowed")

        # Validate required fields for user isolation
        if not context.user_id:
            raise ValueError("SECURITY VIOLATION: Missing user_id required for user isolation")

        if not context.thread_id:
            raise ValueError("SECURITY VIOLATION: Missing thread_id required for execution tracking")

        # Deep copy to prevent reference-based contamination
        validated_context = copy.deepcopy(context)

        # Validate agent_context for dangerous content
        if validated_context.agent_context:
            self._validate_agent_context_security(validated_context.agent_context, validated_context.user_id)

        return validated_context

    def _validate_agent_context_security(self, agent_context: Dict[str, Any], expected_user_id: str) -> None:
        """Validate agent context for security violations.

        SECURITY FIX: Issue #1017 - Validates agent_context dictionary to prevent
        injection attacks and cross-user data contamination.

        Args:
            agent_context: The agent context dictionary to validate
            expected_user_id: The expected user ID for isolation validation

        Raises:
            ValueError: If security violations are detected
        """
        if not isinstance(agent_context, dict):
            raise ValueError("SECURITY VIOLATION: agent_context must be a dictionary")

        # Check for dangerous keys
        dangerous_keys = [
            'exec', 'eval', 'import', '__class__', '__globals__',
            'bypass_permissions', 'admin_override', 'backdoor_access',
            'system_commands', 'shell_access'
        ]

        for key in agent_context.keys():
            if any(dangerous in str(key).lower() for dangerous in dangerous_keys):
                raise ValueError(f"SECURITY VIOLATION: Dangerous key '{key}' detected in agent_context")

        # Validate all string values for injection attacks
        self._validate_context_values_recursively(agent_context, f"agent_context for user {expected_user_id}")

    def _validate_context_values_recursively(self, data: Any, path: str) -> None:
        """Recursively validate context values for security threats.

        Args:
            data: The data structure to validate
            path: Current path in the data structure for error reporting
        """
        if isinstance(data, dict):
            for key, value in data.items():
                self._validate_context_values_recursively(value, f"{path}.{key}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._validate_context_values_recursively(item, f"{path}[{i}]")
        elif isinstance(data, str):
            if self._contains_dangerous_content(data):
                raise ValueError(f"SECURITY VIOLATION: Dangerous content detected in {path}")

    def _contains_dangerous_content(self, value: str) -> bool:
        """Check if a string contains dangerous content.

        Args:
            value: String value to check

        Returns:
            True if dangerous content is detected
        """
        dangerous_patterns = [
            r'rm\s+-rf\s*/',  # Destructive file operations
            r'exec\s*\(',     # Code execution
            r'eval\s*\(',     # Code evaluation
            r'import\s+os',   # OS module imports
            r'__class__',     # Python introspection
            r'__globals__',   # Global access
            r'cat\s+/etc/passwd',  # System file access
            r'<script>',      # XSS
            r'javascript:',   # JavaScript injection
            r'DROP\s+TABLE',  # SQL injection
        ]

        value_lower = value.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True

        return False

    def _sanitize_user_prompt(self, user_prompt: str) -> str:
        """Sanitize user prompt to remove dangerous content.

        SECURITY FIX: Issue #1017 - Sanitizes user input to prevent injection attacks.

        Args:
            user_prompt: The user prompt to sanitize

        Returns:
            Sanitized user prompt
        """
        if not isinstance(user_prompt, str):
            return str(user_prompt)

        # Remove dangerous patterns
        sanitized = user_prompt

        # Remove script tags and JavaScript
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '[REMOVED]', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'javascript:', '[REMOVED]', sanitized, flags=re.IGNORECASE)

        # Remove potential SQL injection
        sanitized = re.sub(r'(DROP|DELETE|INSERT|UPDATE)\s+TABLE', '[REMOVED]', sanitized, flags=re.IGNORECASE)

        # Remove shell commands
        sanitized = re.sub(r'rm\s+-rf\s*/', '[REMOVED]', sanitized, flags=re.IGNORECASE)

        return sanitized

    def _validate_extracted_context_isolation(self, extracted_data: Dict[str, Any], expected_user_id: str) -> None:
        """Validate extracted context maintains user isolation.

        SECURITY FIX: Issue #1017 - Validates that extracted execution context
        only contains data for the expected user and no cross-user contamination.

        Args:
            extracted_data: The extracted context data
            expected_user_id: The expected user ID

        Raises:
            ValueError: If user isolation violations are detected
        """
        # Verify user_id matches expected
        if extracted_data.get('user_id') != expected_user_id:
            raise ValueError(
                f"SECURITY VIOLATION: User isolation breach - expected user {expected_user_id}, "
                f"got {extracted_data.get('user_id')}"
            )

        # Check for other user IDs in the data
        data_str = str(extracted_data)

        # Pattern to detect other user IDs (assuming format like "user_123", "enterprise_user_001", etc.)
        user_id_patterns = [
            r'user_\w+',
            r'enterprise_user_\w+',
            r'classified_\w+_\d+',
            r'admin_user_\w+',
            r'gov_user_\w+',
            r'corp_user_\w+'
        ]

        for pattern in user_id_patterns:
            matches = re.findall(pattern, data_str, re.IGNORECASE)
            for match in matches:
                if match != expected_user_id:
                    logger.warning(
                        f"SECURITY WARNING: Potential cross-user data detected - "
                        f"found '{match}' in context for user {expected_user_id}"
                    )

    def _sanitize_execution_result(self, result: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Sanitize execution result to prevent information disclosure.

        SECURITY FIX: Issue #1017 - Sanitizes execution results to prevent
        cross-user data contamination and sensitive information disclosure.

        Args:
            result: The execution result to sanitize
            user_id: The user ID for context

        Returns:
            Sanitized execution result
        """
        if not isinstance(result, dict):
            return {"result": str(result)}

        sanitized_result = copy.deepcopy(result)

        # Remove sensitive fields that might contain cross-user data
        sensitive_fields = [
            'internal_system_data', 'debug_info', 'raw_execution_context',
            'full_state_dump', 'system_metadata'
        ]

        for field in sensitive_fields:
            if field in sanitized_result:
                sanitized_result[field] = '[REDACTED]'

        # Recursively sanitize nested data
        self._sanitize_nested_result_data(sanitized_result, user_id)

        return sanitized_result

    def _sanitize_nested_result_data(self, data: Any, user_id: str) -> None:
        """Recursively sanitize nested result data.

        Args:
            data: The data structure to sanitize (modified in place)
            user_id: The user ID for context
        """
        if isinstance(data, dict):
            # Check for sensitive keys
            sensitive_patterns = ['secret', 'password', 'token', 'key', 'credential']

            keys_to_redact = []
            for key in data.keys():
                key_lower = str(key).lower()
                if any(pattern in key_lower for pattern in sensitive_patterns):
                    keys_to_redact.append(key)
                elif isinstance(data[key], (dict, list)):
                    self._sanitize_nested_result_data(data[key], user_id)
                elif isinstance(data[key], str):
                    # Check for other user IDs in string values
                    if self._contains_other_user_references(data[key], user_id):
                        data[key] = '[REDACTED - USER ISOLATION]'

            # Redact sensitive keys
            for key in keys_to_redact:
                data[key] = '[REDACTED]'

        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    self._sanitize_nested_result_data(item, user_id)
                elif isinstance(item, str) and self._contains_other_user_references(item, user_id):
                    data[i] = '[REDACTED - USER ISOLATION]'

    def _contains_other_user_references(self, value: str, current_user_id: str) -> bool:
        """Check if a string contains references to other users.

        Args:
            value: String value to check
            current_user_id: The current user's ID

        Returns:
            True if other user references are detected
        """
        # Pattern to detect user ID formats
        user_id_patterns = [
            r'user_\w+',
            r'enterprise_user_\w+',
            r'classified_\w+_\d+',
            r'admin_user_\w+',
            r'gov_user_\w+',
            r'corp_user_\w+'
        ]

        for pattern in user_id_patterns:
            matches = re.findall(pattern, value, re.IGNORECASE)
            for match in matches:
                if match != current_user_id:
                    return True

        return False

    def _sanitize_supervisor_result(self, result: Any, user_id: str) -> Any:
        """Sanitize supervisor execution result to prevent cross-user contamination.

        SECURITY FIX: Issue #1017 - Sanitizes supervisor execution results to prevent
        cross-user data contamination and sensitive information disclosure.

        Args:
            result: The supervisor execution result to sanitize
            user_id: The user ID for context validation

        Returns:
            Sanitized result safe for user consumption
        """
        if result is None:
            return result

        # Handle different result types
        if hasattr(result, 'to_dict'):
            # If result has to_dict method, use it and sanitize the dict
            result_dict = result.to_dict()
            return self._sanitize_execution_result(result_dict, user_id)
        elif isinstance(result, dict):
            # If result is already a dict, sanitize directly
            return self._sanitize_execution_result(result, user_id)
        elif isinstance(result, str):
            # If result is a string, check for cross-user contamination
            return self._sanitize_string_result(result, user_id)
        else:
            # For other types, convert to string and sanitize
            string_result = str(result)
            return self._sanitize_string_result(string_result, user_id)

    def _sanitize_string_result(self, result_str: str, user_id: str) -> str:
        """Sanitize string result to prevent cross-user data exposure.

        Args:
            result_str: String result to sanitize
            user_id: The user ID for context validation

        Returns:
            Sanitized string result
        """
        if not isinstance(result_str, str):
            result_str = str(result_str)

        # Check for other user references and redact them
        if self._contains_other_user_references(result_str, user_id):
            # Rather than redacting the entire string, try to remove specific user references
            sanitized = result_str

            # Remove other user IDs
            user_id_patterns = [
                r'user_\w+',
                r'enterprise_user_\w+',
                r'classified_\w+_\d+',
                r'admin_user_\w+',
                r'gov_user_\w+',
                r'corp_user_\w+'
            ]

            for pattern in user_id_patterns:
                matches = re.findall(pattern, sanitized, re.IGNORECASE)
                for match in matches:
                    if match != user_id:
                        sanitized = sanitized.replace(match, '[REDACTED_USER_ID]')

            # Remove sensitive clearance and classification terms
            sensitive_terms = [
                'top_secret', 'classified', 'confidential', 'secret',
                'clearance_level', 'security_clearance', 'classification'
            ]

            for term in sensitive_terms:
                if term in sanitized.lower() and term not in user_id.lower():
                    # Replace the term while preserving context
                    sanitized = re.sub(
                        rf'\b{re.escape(term)}\b',
                        '[REDACTED_CLASSIFICATION]',
                        sanitized,
                        flags=re.IGNORECASE
                    )

            return sanitized

        return result_str

    def _convert_and_validate_context(self, context) -> UserExecutionContext:
        """Convert and validate context for security compliance.

        SECURITY FIX: Issue #1017 - Converts legacy DeepAgentState to secure
        UserExecutionContext and validates for security threats.

        Args:
            context: Input context (UserExecutionContext or DeepAgentState)

        Returns:
            Validated UserExecutionContext

        Raises:
            ValueError: If context contains security violations
        """
        # Check if it's already a UserExecutionContext
        if isinstance(context, UserExecutionContext):
            return self._validate_user_context_security(context)

        # Handle legacy DeepAgentState conversion
        from netra_backend.app.schemas.agent_models import DeepAgentState

        if isinstance(context, DeepAgentState):
            logger.warning(
                f"SECURITY WARNING: Legacy DeepAgentState used for user {context.user_id}. "
                f"Converting to secure UserExecutionContext for Issue #1017 compliance."
            )

            # Validate DeepAgentState for security violations first
            self._validate_deep_agent_state_security(context)

            # Convert to UserExecutionContext
            user_context = UserExecutionContext(
                user_id=context.user_id,
                thread_id=context.chat_thread_id,
                run_id=context.run_id or f"converted_run_{context.user_id}",
                agent_context=copy.deepcopy(context.agent_context)
            )

            return self._validate_user_context_security(user_context)

        # Reject invalid types
        raise ValueError(
            f"SECURITY VIOLATION: Invalid context type {type(context)}. "
            f"Only UserExecutionContext or DeepAgentState (legacy) allowed."
        )

    def _validate_deep_agent_state_security(self, state: 'DeepAgentState') -> None:
        """Validate DeepAgentState for security violations.

        SECURITY FIX: Issue #1017 - Validates legacy DeepAgentState objects
        for security threats before conversion.

        Args:
            state: DeepAgentState to validate

        Raises:
            ValueError: If security violations are detected
        """
        # Validate required fields
        if not state.user_id:
            raise ValueError("SECURITY VIOLATION: Missing user_id required for user isolation")

        # Generate thread_id if missing (for legacy compatibility)
        if not state.chat_thread_id:
            import uuid
            state.chat_thread_id = f"legacy_thread_{state.user_id}_{uuid.uuid4().hex[:8]}"
            logger.warning(
                f"SECURITY WARNING: Generated thread_id for legacy DeepAgentState for user {state.user_id}. "
                f"Consider updating to use proper UserExecutionContext."
            )

        # Validate agent_context if present
        if state.agent_context:
            self._validate_agent_context_security(state.agent_context, state.user_id)

        # Validate that agent_input doesn't contain dangerous content
        if hasattr(state, 'agent_input') and state.agent_input:
            self._validate_agent_context_security(state.agent_input, state.user_id)