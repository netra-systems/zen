"""Context Serialization Utilities for Background Task Security

SECURITY CRITICAL: This module provides secure serialization and deserialization
of UserExecutionContext for background task queuing while maintaining user isolation.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Enable secure context propagation in async/background tasks
- Value Impact: Prevents user data mixing in queued operations
- Revenue Impact: Maintains security compliance and user trust

Key Security Features:
- Secure context serialization with validation
- Context deserialization with integrity checking
- Protection against context tampering and injection
- Audit trail preservation across serialization boundaries
- Context versioning for backwards compatibility

Architecture:
This module provides the core utilities needed to safely serialize UserExecutionContext
for transmission across async boundaries, Redis queues, and background task systems.
"""

import json
import hashlib
import hmac
import base64
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone

from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError

logger = logging.getLogger(__name__)


class ContextSerializationError(Exception):
    """Raised when context serialization/deserialization fails."""
    pass


class ContextIntegrityError(Exception):
    """Raised when context integrity validation fails."""
    pass


class SecureContextSerializer:
    """Secure serializer for UserExecutionContext with integrity validation."""
    
    SERIALIZATION_VERSION = "1.0"
    
    def __init__(self, secret_key: Optional[str] = None):
        """Initialize secure context serializer.
        
        Args:
            secret_key: Optional secret key for context integrity verification.
                       If None, uses a default key (less secure).
        """
        # SECURITY CRITICAL: Use provided key or fallback to environment-based key
        self.secret_key = secret_key or self._get_default_secret_key()
    
    def _get_default_secret_key(self) -> str:
        """Get default secret key for integrity verification."""
        # In production, this should come from environment or secure configuration
        # For now, use a deterministic key based on the application
        return hashlib.sha256(b"netra_context_serialization_v1").hexdigest()
    
    def serialize_context(self, context: UserExecutionContext) -> str:
        """Serialize UserExecutionContext to secure string format.
        
        Args:
            context: UserExecutionContext to serialize
            
        Returns:
            Base64-encoded JSON string with integrity hash
            
        Raises:
            ContextSerializationError: If serialization fails
        """
        try:
            # SECURITY CRITICAL: Validate context before serialization
            context.verify_isolation()
            
            # Extract serializable data
            context_data = {
                'user_id': context.user_id,
                'thread_id': context.thread_id,
                'run_id': context.run_id,
                'request_id': context.request_id,
                'websocket_client_id': context.websocket_client_id,
                'created_at': context.created_at.isoformat(),
                'agent_context': context.agent_context.copy(),
                'audit_metadata': context.audit_metadata.copy(),
                'operation_depth': context.operation_depth,
                'parent_request_id': context.parent_request_id
            }
            
            # Add serialization metadata
            serialization_metadata = {
                'serialization_version': self.SERIALIZATION_VERSION,
                'serialized_at': datetime.now(timezone.utc).isoformat(),
                'serializer_id': 'SecureContextSerializer'
            }
            
            # Create complete payload
            payload = {
                'context_data': context_data,
                'metadata': serialization_metadata
            }
            
            # Generate JSON
            json_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
            
            # Generate integrity hash
            integrity_hash = self._generate_integrity_hash(json_str)
            
            # Create final payload with integrity verification
            final_payload = {
                'payload': json_str,
                'integrity_hash': integrity_hash,
                'hash_algorithm': 'sha256_hmac'
            }
            
            # Encode to base64 for safe transport
            final_json = json.dumps(final_payload, separators=(',', ':'))
            encoded_context = base64.b64encode(final_json.encode('utf-8')).decode('utf-8')
            
            logger.debug(f"Serialized context for user {context.user_id} (request: {context.request_id})")
            return encoded_context
            
        except Exception as e:
            logger.error(f"Failed to serialize context: {e}")
            raise ContextSerializationError(f"Context serialization failed: {e}")
    
    def deserialize_context(self, serialized_context: str) -> UserExecutionContext:
        """Deserialize UserExecutionContext from secure string format.
        
        Args:
            serialized_context: Base64-encoded serialized context
            
        Returns:
            Reconstructed UserExecutionContext
            
        Raises:
            ContextSerializationError: If deserialization fails
            ContextIntegrityError: If integrity verification fails
        """
        try:
            # Decode from base64
            decoded_bytes = base64.b64decode(serialized_context.encode('utf-8'))
            final_payload = json.loads(decoded_bytes.decode('utf-8'))
            
            # Extract components
            json_str = final_payload['payload']
            expected_hash = final_payload['integrity_hash']
            hash_algorithm = final_payload.get('hash_algorithm', 'sha256_hmac')
            
            # SECURITY CRITICAL: Verify integrity
            if not self._verify_integrity_hash(json_str, expected_hash, hash_algorithm):
                raise ContextIntegrityError("Context integrity verification failed")
            
            # Parse payload
            payload = json.loads(json_str)
            context_data = payload['context_data']
            metadata = payload['metadata']
            
            # Validate serialization version
            if metadata.get('serialization_version') != self.SERIALIZATION_VERSION:
                logger.warning(
                    f"Context serialization version mismatch: "
                    f"expected {self.SERIALIZATION_VERSION}, "
                    f"got {metadata.get('serialization_version')}"
                )
            
            # Reconstruct datetime objects
            created_at = datetime.fromisoformat(context_data['created_at'].replace('Z', '+00:00'))
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            # Reconstruct UserExecutionContext
            reconstructed_context = UserExecutionContext(
                user_id=context_data['user_id'],
                thread_id=context_data['thread_id'],
                run_id=context_data['run_id'],
                request_id=context_data['request_id'],
                websocket_client_id=context_data.get('websocket_client_id'),
                created_at=created_at,
                agent_context=context_data.get('agent_context', {}),
                audit_metadata=context_data.get('audit_metadata', {}),
                operation_depth=context_data.get('operation_depth', 0),
                parent_request_id=context_data.get('parent_request_id')
            )
            
            # SECURITY CRITICAL: Verify reconstructed context integrity
            reconstructed_context.verify_isolation()
            
            logger.debug(
                f"Deserialized context for user {reconstructed_context.user_id} "
                f"(request: {reconstructed_context.request_id})"
            )
            
            return reconstructed_context
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to deserialize context: {e}")
            raise ContextSerializationError(f"Context deserialization failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during context deserialization: {e}")
            raise ContextSerializationError(f"Context deserialization failed: {e}")
    
    def _generate_integrity_hash(self, data: str) -> str:
        """Generate HMAC-SHA256 integrity hash for data."""
        hash_obj = hmac.new(
            self.secret_key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        )
        return hash_obj.hexdigest()
    
    def _verify_integrity_hash(self, data: str, expected_hash: str, algorithm: str) -> bool:
        """Verify integrity hash for data."""
        if algorithm != 'sha256_hmac':
            logger.warning(f"Unsupported hash algorithm: {algorithm}")
            return False
        
        actual_hash = self._generate_integrity_hash(data)
        return hmac.compare_digest(actual_hash, expected_hash)


class ContextQueue:
    """Queue for UserExecutionContext with secure serialization."""
    
    def __init__(self, serializer: Optional[SecureContextSerializer] = None):
        """Initialize context queue.
        
        Args:
            serializer: Optional custom serializer. If None, uses default.
        """
        self.serializer = serializer or SecureContextSerializer()
        self._queue: List[str] = []
    
    async def put(self, context: UserExecutionContext, task_data: Optional[Dict[str, Any]] = None):
        """Add context and task data to queue with secure serialization.
        
        Args:
            context: UserExecutionContext to queue
            task_data: Optional additional task data
        """
        try:
            # Serialize context
            serialized_context = self.serializer.serialize_context(context)
            
            # Create queue item
            queue_item = {
                'context': serialized_context,
                'task_data': task_data or {},
                'queued_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Add to queue (in production, this would be Redis/RabbitMQ/etc.)
            self._queue.append(json.dumps(queue_item))
            
            logger.debug(f"Queued context for user {context.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to queue context: {e}")
            raise
    
    async def get(self) -> Optional[tuple[UserExecutionContext, Dict[str, Any]]]:
        """Get context and task data from queue with secure deserialization.
        
        Returns:
            Tuple of (UserExecutionContext, task_data) or None if queue empty
        """
        if not self._queue:
            return None
        
        try:
            # Get item from queue
            queue_item_str = self._queue.pop(0)
            queue_item = json.loads(queue_item_str)
            
            # Deserialize context
            context = self.serializer.deserialize_context(queue_item['context'])
            task_data = queue_item.get('task_data', {})
            
            logger.debug(f"Dequeued context for user {context.user_id}")
            
            return context, task_data
            
        except Exception as e:
            logger.error(f"Failed to dequeue context: {e}")
            return None
    
    def size(self) -> int:
        """Get queue size."""
        return len(self._queue)
    
    def clear(self):
        """Clear the queue."""
        self._queue.clear()


# Module-level utilities

def serialize_context_for_task(context: UserExecutionContext) -> str:
    """Utility function to serialize context for background tasks."""
    serializer = SecureContextSerializer()
    return serializer.serialize_context(context)


def deserialize_context_from_task(serialized_context: str) -> UserExecutionContext:
    """Utility function to deserialize context from background tasks."""
    serializer = SecureContextSerializer()
    return serializer.deserialize_context(serialized_context)


def create_secure_task_payload(
    context: UserExecutionContext,
    task_name: str,
    task_parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Create secure task payload with serialized context.
    
    Args:
        context: UserExecutionContext for the task
        task_name: Name of the task to execute
        task_parameters: Parameters for the task
        
    Returns:
        Dictionary containing secure task payload
    """
    return {
        'task_name': task_name,
        'task_parameters': task_parameters,
        'user_context': serialize_context_for_task(context),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'security_version': SecureContextSerializer.SERIALIZATION_VERSION
    }


def extract_context_from_task_payload(payload: Dict[str, Any]) -> tuple[str, Dict[str, Any], UserExecutionContext]:
    """Extract context and task data from secure task payload.
    
    Args:
        payload: Secure task payload
        
    Returns:
        Tuple of (task_name, task_parameters, user_context)
    """
    task_name = payload['task_name']
    task_parameters = payload['task_parameters']
    user_context = deserialize_context_from_task(payload['user_context'])
    
    return task_name, task_parameters, user_context


# Export public classes and functions
__all__ = [
    'SecureContextSerializer',
    'ContextQueue',
    'ContextSerializationError',
    'ContextIntegrityError',
    'serialize_context_for_task',
    'deserialize_context_from_task',
    'create_secure_task_payload',
    'extract_context_from_task_payload'
]