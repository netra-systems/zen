#!/usr/bin/env python3
"""
Simple WebSocket test server for testing WebSocket connectivity without Docker.
This bypasses all the complex startup processes and just starts a basic server.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set minimal environment variables
os.environ['NETRA_ENV'] = 'testing'
os.environ['TESTING'] = '1'
os.environ['SKIP_STARTUP_CHECKS'] = 'true'
os.environ['DISABLE_STARTUP_CHECKS'] = 'true'
os.environ['SERVICE_ID'] = 'test-websocket-server'
os.environ['SERVICE_SECRET'] = 'test-secret'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret'
os.environ['REDIS_MODE'] = 'disabled'
os.environ['CLICKHOUSE_MODE'] = 'disabled'
os.environ['LLM_MODE'] = 'disabled'
os.environ['AUTH_ENABLED'] = 'false'
os.environ['AUTH_SERVICE_ENABLED'] = 'false'

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

# Create a simple FastAPI app with just WebSocket functionality
app = FastAPI(title="Test WebSocket Server")

@app.get("/")
async def root():
    return {"message": "Test WebSocket Server Running", "status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy", "websocket": "available"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Simple WebSocket endpoint for testing connectivity."""
    await websocket.accept()
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "server_message",
            "data": {
                "message": "WebSocket connection established successfully!",
                "timestamp": str(asyncio.get_event_loop().time())
            }
        })
        
        # Keep connection alive and echo messages
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "type": "echo",
                "data": {
                    "received": data,
                    "timestamp": str(asyncio.get_event_loop().time())
                }
            })
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()

if __name__ == "__main__":
    print("Starting Test WebSocket Server...")
    print("WebSocket endpoint: ws://127.0.0.1:8080/ws")
    print("Health check: http://127.0.0.1:8080/health")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8080,
        log_level="info"
    )