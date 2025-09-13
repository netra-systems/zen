"""

Chat and WebSocket Helper Functions



Helper functions for chat interactions and WebSocket communication testing.

Extracted from test_complete_oauth_chat_journey.py for modularity.

"""



import asyncio

import json

import time

import uuid

from typing import Any, Dict, Optional



import httpx

try:

    import websockets

except ImportError:

    websockets = None





class WebSocketConnectionHelper:

    """Helper for WebSocket connection operations."""

    

    @staticmethod

    async def execute_websocket_connection(

        services_manager,

        tokens: Dict[str, str]

    ) -> Dict[str, Any]:

        """Execute WebSocket connection with OAuth-derived token."""

        websocket_start = time.time()

        websocket = None

        

        try:

            access_token = tokens.get("access_token")

            service_urls = services_manager.get_service_urls()

            backend_url = service_urls["backend"]

            

            # Convert HTTP URL to WebSocket URL

            ws_url = backend_url.replace("http://", "ws://") + f"/ws?token={access_token}"

            

            # Connect to WebSocket

            if websockets:

                websocket = await asyncio.wait_for(

                    websockets.connect(ws_url),

                    timeout=10.0

                )

            else:

                # WebSocket library not available, simulate connection

                websocket = None

            

            # Test connection with ping

            ping_message = {"type": "ping", "timestamp": time.time()}

            await websocket.send(json.dumps(ping_message))

            

            # Wait for response

            try:

                response = await asyncio.wait_for(

                    websocket.recv(),

                    timeout=5.0

                )

                pong_response = json.loads(response)

            except asyncio.TimeoutError:

                pong_response = None

            

            websocket_time = time.time() - websocket_start

            

            return {

                "success": True,

                "connected": True,

                "websocket_url": ws_url,

                "ping_successful": pong_response is not None,

                "pong_response": pong_response,

                "websocket_time": websocket_time,

                "websocket": websocket

            }

            

        except Exception as e:

            if websocket:

                await websocket.close()

            return {

                "success": False,

                "connected": False,

                "error": str(e),

                "websocket_time": time.time() - websocket_start

            }





class ChatInteractionHelper:

    """Helper for chat interaction operations."""

    

    @staticmethod

    async def execute_chat_interaction(

        websocket,

        user_id: str

    ) -> Dict[str, Any]:

        """Execute chat message and receive AI response."""

        chat_start = time.time()

        

        try:

            thread_id = str(uuid.uuid4())

            

            chat_message = {

                "type": "chat",

                "message": "Help me optimize my AI infrastructure costs for enterprise deployment",

                "thread_id": thread_id,

                "user_id": user_id,

                "timestamp": time.time()

            }

            

            await websocket.send(json.dumps(chat_message))

            

            # Wait for AI response

            try:

                response_raw = await asyncio.wait_for(

                    websocket.recv(),

                    timeout=15.0

                )

                response = json.loads(response_raw)

            except asyncio.TimeoutError:

                response = None

            except json.JSONDecodeError:

                response = {"raw": response_raw, "type": "raw_response"}

            

            chat_time = time.time() - chat_start

            

            return {

                "success": True,

                "message_sent": chat_message["message"],

                "thread_id": thread_id,

                "user_id": user_id,

                "response_received": response is not None,

                "response": response,

                "chat_time": chat_time,

                "agent_responded": response and response.get("type") in ["agent_response", "message", "chat_response"]

            }

            

        except Exception as e:

            return {

                "success": False,

                "error": str(e),

                "chat_time": time.time() - chat_start

            }





class ConversationPersistenceHelper:

    """Helper for conversation persistence verification."""

    

    @staticmethod

    async def verify_conversation_persistence(

        http_client: httpx.AsyncClient,

        services_manager,

        tokens: Dict[str, str],

        thread_id: str

    ) -> Dict[str, Any]:

        """Verify conversation is properly persisted in database."""

        persistence_start = time.time()

        

        try:

            access_token = tokens.get("access_token")

            service_urls = services_manager.get_service_urls()

            backend_url = service_urls["backend"]

            

            # Query chat history to verify persistence

            history_response = await http_client.get(

                f"{backend_url}/api/chat/history",

                headers={"Authorization": f"Bearer {access_token}"}

            )

            

            persistence_time = time.time() - persistence_start

            

            if history_response.status_code == 200:

                history_data = history_response.json()

                

                # Check if our conversation exists

                conversations = history_data.get("conversations", [])

                conversation_found = any(

                    conv.get("thread_id") == thread_id 

                    for conv in conversations

                )

                

                return {

                    "success": True,

                    "history_status": history_response.status_code,

                    "conversation_count": len(conversations),

                    "conversation_found": conversation_found,

                    "thread_id": thread_id,

                    "persistence_time": persistence_time

                }

            else:

                return {

                    "success": False,

                    "history_status": history_response.status_code,

                    "error": "Failed to retrieve chat history",

                    "persistence_time": persistence_time

                }

                

        except Exception as e:

            return {

                "success": False,

                "error": str(e),

                "persistence_time": time.time() - persistence_start

            }

