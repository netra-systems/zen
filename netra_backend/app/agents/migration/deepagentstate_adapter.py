"""DeepAgentState to UserExecutionContext Migration Adapter

This module provides utilities to safely migrate from the deprecated DeepAgentState
pattern to the modern UserExecutionContext pattern, ensuring complete user isolation
and request security.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) - SECURITY CRITICAL
- Business Goal: Eliminate user data leakage risks through proper migration
- Value Impact: Enables safe multi-user operations, prevents security breaches
- Revenue Impact: CRITICAL - Protects business from data breach liability

Key Features:
- Bidirectional conversion between DeepAgentState and UserExecutionContext
- Validation and safety checks during migration
- Backward compatibility preservation during transition period
- Comprehensive logging and error handling for migration troubleshooting
"""

import uuid
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union, List, Set
import logging
from dataclasses import asdict

from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, 
    InvalidContextError
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MigrationValidationError(Exception):
    """Raised when migration validation fails."""
    pass


class DeepAgentStateAdapter:
    """Adapter to bridge DeepAgentState to UserExecutionContext during migration.
    
    This adapter provides safe, validated conversion between the deprecated
    DeepAgentState pattern and the modern UserExecutionContext pattern,
    ensuring no data loss and proper user isolation.
    
    Usage:
        # Convert DeepAgentState to UserExecutionContext
        context = DeepAgentStateAdapter.from_deep_agent_state(
            state=old_state,
            user_id="user123",
            thread_id="thread456", 
            run_id="run789"
        )
        
        # Convert back if needed for legacy compatibility
        state = DeepAgentStateAdapter.to_deep_agent_state(context)
    """
    
    # Fields that should be migrated to agent_context
    AGENT_CONTEXT_FIELDS = {
        'user_request', 'agent_input', 'step_count', 'messages',
        'context_tracking', 'quality_metrics'
    }
    
    # Fields that should be migrated to audit_metadata  
    AUDIT_METADATA_FIELDS = {
        'chat_thread_id', 'user_id', 'run_id', 'final_report'
    }
    
    # Result fields that contain agent execution results
    RESULT_FIELDS = {
        'triage_result', 'data_result', 'optimizations_result',
        'action_plan_result', 'report_result', 'synthetic_data_result',
        'supply_research_result', 'corpus_admin_result', 'corpus_admin_error'
    }
    
    @classmethod
    def from_deep_agent_state(
        cls,
        state: DeepAgentState,
        user_id: str,
        thread_id: str,
        run_id: str,
        websocket_client_id: Optional[str] = None,
        validate_isolation: bool = True
    ) -> UserExecutionContext:
        """Convert DeepAgentState to UserExecutionContext with full validation.
        
        This method safely extracts data from DeepAgentState and creates a new
        UserExecutionContext with proper isolation guarantees.
        
        Args:
            state: The DeepAgentState to convert
            user_id: User identifier for the new context
            thread_id: Thread identifier for the new context
            run_id: Run identifier for the new context
            websocket_client_id: Optional WebSocket connection ID
            validate_isolation: Whether to perform isolation validation
            
        Returns:
            New UserExecutionContext with converted data
            
        Raises:
            MigrationValidationError: If migration validation fails
            InvalidContextError: If context creation fails
        """
        # Issue deprecation warning
        warnings.warn(
            "Converting from DeepAgentState to UserExecutionContext. "
            "DeepAgentState is deprecated and will be removed in v3.0.0. "
            "Update your code to use UserExecutionContext directly.",
            DeprecationWarning,
            stacklevel=2
        )
        
        logger.info(
            f"Migrating DeepAgentState to UserExecutionContext: "
            f"user_id={user_id}, thread_id={thread_id}, run_id={run_id}"
        )
        
        try:
            # Extract and categorize data from DeepAgentState
            agent_context = cls._extract_agent_context(state)
            audit_metadata = cls._extract_audit_metadata(state, user_id, thread_id, run_id)
            
            # Create UserExecutionContext
            context = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                websocket_client_id=websocket_client_id,
                agent_context=agent_context,
                audit_metadata=audit_metadata
            )
            
            # Perform validation if requested
            if validate_isolation:
                cls._validate_migration(state, context)
            
            logger.debug(
                f"Successfully migrated DeepAgentState to UserExecutionContext: "
                f"request_id={context.request_id}"
            )
            
            return context
            
        except Exception as e:
            error_msg = f"Failed to migrate DeepAgentState to UserExecutionContext: {e}"
            logger.error(error_msg, exc_info=True)
            raise MigrationValidationError(error_msg) from e
    
    @classmethod
    def to_deep_agent_state(
        cls,
        context: UserExecutionContext,
        preserve_results: bool = True
    ) -> DeepAgentState:
        """Convert UserExecutionContext back to DeepAgentState (temporary bridge).
        
        This method provides backward compatibility during the migration period
        by converting UserExecutionContext data back to DeepAgentState format.
        
         WARNING: [U+FE0F] WARNING: This method is for TEMPORARY backward compatibility only.
        It will be removed when DeepAgentState migration is complete.
        
        Args:
            context: The UserExecutionContext to convert
            preserve_results: Whether to preserve result fields from metadata
            
        Returns:
            DeepAgentState with data from UserExecutionContext
            
        Raises:
            MigrationValidationError: If conversion fails
        """
        warnings.warn(
            "Converting UserExecutionContext to DeepAgentState for backward compatibility. "
            "This is a temporary migration bridge that will be removed in v3.0.0. "
            "Update dependent code to use UserExecutionContext directly.",
            DeprecationWarning,
            stacklevel=2
        )
        
        logger.warning(
            f"Converting UserExecutionContext to DeepAgentState (TEMPORARY): "
            f"request_id={context.request_id}"
        )
        
        try:
            # Extract data from UserExecutionContext
            state_data = cls._extract_state_data(context, preserve_results)
            
            # Create DeepAgentState
            state = DeepAgentState(**state_data)
            
            logger.debug(
                f"Converted UserExecutionContext to DeepAgentState: "
                f"user_id={state.user_id}"
            )
            
            return state
            
        except Exception as e:
            error_msg = f"Failed to convert UserExecutionContext to DeepAgentState: {e}"
            logger.error(error_msg, exc_info=True)
            raise MigrationValidationError(error_msg) from e
    
    @classmethod
    def _extract_agent_context(cls, state: DeepAgentState) -> Dict[str, Any]:
        """Extract agent context data from DeepAgentState."""
        agent_context = {}
        
        for field in cls.AGENT_CONTEXT_FIELDS:
            if hasattr(state, field):
                value = getattr(state, field)
                if value is not None:
                    agent_context[field] = value
        
        # Add result fields to agent context for agent processing
        for field in cls.RESULT_FIELDS:
            if hasattr(state, field):
                value = getattr(state, field)
                if value is not None:
                    # Convert Pydantic models to dict for serialization
                    if hasattr(value, 'model_dump'):
                        value = value.model_dump(mode='json', exclude_none=True)
                    agent_context[field] = value
        
        # Add metadata if present
        if hasattr(state, 'metadata') and state.metadata:
            if hasattr(state.metadata, 'model_dump'):
                agent_context['legacy_metadata'] = state.metadata.model_dump(
                    mode='json', exclude_none=True
                )
            else:
                agent_context['legacy_metadata'] = state.metadata
        
        return agent_context
    
    @classmethod  
    def _extract_audit_metadata(
        cls, 
        state: DeepAgentState, 
        user_id: str, 
        thread_id: str, 
        run_id: str
    ) -> Dict[str, Any]:
        """Extract audit metadata from DeepAgentState."""
        audit_metadata = {
            'migration_timestamp': datetime.now(timezone.utc).isoformat(),
            'migration_source': 'DeepAgentState',
            'original_user_id': user_id,
            'original_thread_id': thread_id,
            'original_run_id': run_id
        }
        
        # Add audit-relevant fields
        for field in cls.AUDIT_METADATA_FIELDS:
            if hasattr(state, field):
                value = getattr(state, field)
                if value is not None:
                    audit_metadata[f'legacy_{field}'] = value
        
        # Add quality metrics if present
        if hasattr(state, 'quality_metrics') and state.quality_metrics:
            audit_metadata['quality_metrics'] = state.quality_metrics
        
        return audit_metadata
    
    @classmethod
    def _extract_state_data(
        cls, 
        context: UserExecutionContext, 
        preserve_results: bool = True
    ) -> Dict[str, Any]:
        """Extract data from UserExecutionContext for DeepAgentState creation."""
        state_data = {
            'user_request': context.agent_context.get('user_request', ''),
            'chat_thread_id': context.thread_id,
            'user_id': context.user_id,
            'run_id': context.run_id,
            'step_count': context.agent_context.get('step_count', 0),
            'messages': context.agent_context.get('messages', []),
            'context_tracking': context.agent_context.get('context_tracking', {}),
            'quality_metrics': context.agent_context.get('quality_metrics', {})
        }
        
        # Add agent input if present
        if 'agent_input' in context.agent_context:
            state_data['agent_input'] = context.agent_context['agent_input']
        
        # Add result fields if requested and present
        if preserve_results:
            for field in cls.RESULT_FIELDS:
                if field in context.agent_context:
                    state_data[field] = context.agent_context[field]
        
        # Add final report if in metadata
        final_report = (
            context.agent_context.get('final_report') or 
            context.audit_metadata.get('final_report')
        )
        if final_report:
            state_data['final_report'] = final_report
        
        return state_data
    
    @classmethod
    def _validate_migration(
        cls, 
        original_state: DeepAgentState, 
        converted_context: UserExecutionContext
    ) -> None:
        """Validate that migration preserved critical data."""
        validation_errors = []
        
        # Validate user identification consistency
        if hasattr(original_state, 'user_id') and original_state.user_id:
            if converted_context.user_id != original_state.user_id:
                validation_errors.append(
                    f"User ID mismatch: {original_state.user_id} != {converted_context.user_id}"
                )
        
        # Validate thread consistency
        if hasattr(original_state, 'chat_thread_id') and original_state.chat_thread_id:
            if converted_context.thread_id != original_state.chat_thread_id:
                validation_errors.append(
                    f"Thread ID mismatch: {original_state.chat_thread_id} != {converted_context.thread_id}"
                )
        
        # Validate run consistency
        if hasattr(original_state, 'run_id') and original_state.run_id:
            if converted_context.run_id != original_state.run_id:
                validation_errors.append(
                    f"Run ID mismatch: {original_state.run_id} != {converted_context.run_id}"
                )
        
        # Validate critical data preservation
        user_request = (
            original_state.user_request if hasattr(original_state, 'user_request') 
            else None
        )
        if user_request and user_request != converted_context.agent_context.get('user_request'):
            validation_errors.append("User request not preserved during migration")
        
        # Validate result data preservation
        for field in cls.RESULT_FIELDS:
            if hasattr(original_state, field):
                original_value = getattr(original_state, field)
                if original_value is not None:
                    if field not in converted_context.agent_context:
                        validation_errors.append(f"Result field {field} not preserved")
        
        if validation_errors:
            error_msg = "Migration validation failed:\n" + "\n".join(validation_errors)
            raise MigrationValidationError(error_msg)
        
        logger.debug("Migration validation passed successfully")


class MigrationDetector:
    """Utility to detect and analyze DeepAgentState usage in the codebase."""
    
    @classmethod
    def find_deepagentstate_usage(cls, file_path: str) -> List[Dict[str, Any]]:
        """Find DeepAgentState usage patterns in a Python file.
        
        Args:
            file_path: Path to the Python file to analyze
            
        Returns:
            List of usage patterns found
        """
        usage_patterns = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Check for imports
                if 'DeepAgentState' in line_stripped:
                    if (line_stripped.startswith('from') and 'import' in line_stripped and 
                        'DeepAgentState' in line_stripped):
                        usage_patterns.append({
                            'type': 'import',
                            'line': line_num,
                            'content': line_stripped,
                            'file': file_path
                        })
                    
                    # Check for class definitions
                    elif line_stripped.startswith('class') and 'DeepAgentState' in line_stripped:
                        usage_patterns.append({
                            'type': 'class_inheritance',
                            'line': line_num,
                            'content': line_stripped,
                            'file': file_path
                        })
                    
                    # Check for instantiation
                    elif 'DeepAgentState(' in line_stripped:
                        usage_patterns.append({
                            'type': 'instantiation',
                            'line': line_num,
                            'content': line_stripped,
                            'file': file_path
                        })
                    
                    # Check for type annotations
                    elif ':' in line_stripped and 'DeepAgentState' in line_stripped:
                        usage_patterns.append({
                            'type': 'type_annotation',
                            'line': line_num,
                            'content': line_stripped,
                            'file': file_path
                        })
                        
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            
        return usage_patterns
    
    @classmethod
    def generate_migration_report(cls, usage_patterns: List[Dict[str, Any]]) -> str:
        """Generate a migration report from usage patterns.
        
        Args:
            usage_patterns: List of usage patterns from find_deepagentstate_usage
            
        Returns:
            Formatted migration report string
        """
        if not usage_patterns:
            return " PASS:  No DeepAgentState usage found."
        
        # Group by file
        files_by_usage = {}
        for pattern in usage_patterns:
            file_path = pattern['file']
            if file_path not in files_by_usage:
                files_by_usage[file_path] = []
            files_by_usage[file_path].append(pattern)
        
        # Generate report
        report = f" ALERT:  Found {len(usage_patterns)} DeepAgentState usage patterns in {len(files_by_usage)} files:\n\n"
        
        for file_path, patterns in files_by_usage.items():
            report += f"[U+1F4C1] {file_path}\n"
            for pattern in patterns:
                report += f"  Line {pattern['line']} ({pattern['type']}): {pattern['content']}\n"
            report += "\n"
        
        return report


# Export all public classes and functions
__all__ = [
    'DeepAgentStateAdapter',
    'MigrationDetector', 
    'MigrationValidationError'
]