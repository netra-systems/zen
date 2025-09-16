"""Example Message WebSocket Routes

WebSocket endpoints for handling example messages in DEV MODE.
Integrates with the WebSocket manager and example message handler.

Business Value: Enables real-time AI optimization demonstrations
"""

import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

# WebSocket authentication is handled by the WebSocket manager
from netra_backend.app.handlers.example_message_handler import (
    get_example_message_handler,
    handle_example_message,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.websocket_message_types import WebSocketMessage
from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager as get_manager

logger = central_logger.get_logger(__name__)
router = APIRouter(prefix="/api/example-messages", tags=["example-messages"])


@router.websocket("/ws/{user_id}")
async def example_message_websocket(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for example message processing"""
    
    # CRITICAL FIX: Accept WebSocket connection BEFORE any operations
    # This prevents "WebSocket is not connected. Need to call 'accept' first" errors
    await websocket.accept()
    
    ws_manager = get_manager()
    handler = get_example_message_handler()
    
    try:
        # Connect user to WebSocket (now safe after accept)
        connection_info = await ws_manager.connect_user(user_id, websocket)
        logger.info(f"Example message WebSocket connected for user {user_id}")
        
        while True:
            try:
                # Receive message from frontend
                raw_data = await websocket.receive_text()
                message_data = json.loads(raw_data)
                
                logger.debug(f"Received example message", {
                    'user_id': user_id,
                    'message_type': message_data.get('type'),
                    'message_id': message_data.get('payload', {}).get('example_message_id')
                })
                
                # Check if this is an example message
                if (message_data.get('type') == 'chat_message' and 
                    message_data.get('payload', {}).get('example_message_id')):
                    
                    # Process example message
                    payload = message_data.get('payload', {})
                    payload['user_id'] = user_id  # Ensure user_id is set
                    
                    # Handle the example message asynchronously
                    response = await handle_example_message(payload)
                    
                    logger.info(f"Example message processed", {
                        'user_id': user_id,
                        'message_id': response.message_id,
                        'status': response.status,
                        'processing_time': response.processing_time_ms
                    })
                    
                else:
                    # Handle other message types (regular chat, etc.)
                    await ws_manager.handle_message(user_id, websocket, message_data)
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in WebSocket message: {e}")
                await ws_manager.send_error_to_user(
                    user_id, 
                    f"Invalid message format: {str(e)}"
                )
                
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await ws_manager.send_error_to_user(
                    user_id,
                    f"Message processing failed: {str(e)}"
                )
                
    except WebSocketDisconnect:
        logger.info(f"Example message WebSocket disconnected for user {user_id}")
        
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        
    finally:
        try:
            await ws_manager.disconnect_user(user_id, websocket)
        except Exception as e:
            logger.error(f"Error disconnecting user {user_id}: {e}")


@router.get("/stats")
async def get_example_message_stats():
    """Get statistics about example message processing"""
    
    handler = get_example_message_handler()
    
    try:
        stats = handler.get_session_stats()
        active_sessions = handler.get_active_sessions()
        
        # Aggregate statistics
        category_stats = {}
        complexity_stats = {}
        
        for session in active_sessions.values():
            metadata = session.get('metadata', {})
            category = metadata.get('category', 'unknown')
            complexity = metadata.get('complexity', 'unknown')
            
            category_stats[category] = category_stats.get(category, 0) + 1
            complexity_stats[complexity] = complexity_stats.get(complexity, 0) + 1
        
        return JSONResponse({
            'session_stats': stats,
            'active_sessions_count': len(active_sessions),
            'category_breakdown': category_stats,
            'complexity_breakdown': complexity_stats,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error getting example message stats: {e}")
        return JSONResponse(
            status_code=500,
            content={
                'error': 'Failed to get statistics',
                'status': 'error'
            }
        )


@router.get("/status")
async def example_message_status():
    """Status check for example message system"""
    
    try:
        handler = get_example_message_handler()
        ws_manager = get_manager()
        
        # Basic health checks
        handler_active = handler is not None
        ws_manager_active = ws_manager is not None
        
        # Get current load
        session_stats = handler.get_session_stats() if handler_active else {}
        
        health_status = {
            'handler_active': handler_active,
            'websocket_manager_active': ws_manager_active,
            'current_load': session_stats.get('processing_sessions', 0),
            'status': 'healthy' if (handler_active and ws_manager_active) else 'degraded'
        }
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        
        return JSONResponse(
            status_code=status_code,
            content=health_status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                'status': 'unhealthy',
                'error': str(e)
            }
        )