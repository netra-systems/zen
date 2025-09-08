"""Unified ID Generation - SSOT for all ID generation across services.

This module provides the single source of truth for ID generation,
eliminating scattered uuid.uuid4().hex[:8] patterns throughout the codebase.

Usage:
    from shared.id_generation import UnifiedIdGenerator
    
    # Generate user context IDs
    thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(user_id, "operation")
    
    # Generate WebSocket IDs
    ws_conn_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
    
    # Replace uuid.uuid4().hex[:8] patterns
    from shared.id_generation import generate_uuid_replacement
    unique_id = generate_uuid_replacement()
"""

from .unified_id_generator import (
    UnifiedIdGenerator,
    generate_uuid_replacement,
    create_user_execution_context_factory,
    TestIdUtils,
    IdComponents
)

__all__ = [
    'UnifiedIdGenerator',
    'generate_uuid_replacement',
    'create_user_execution_context_factory', 
    'TestIdUtils',
    'IdComponents'
]