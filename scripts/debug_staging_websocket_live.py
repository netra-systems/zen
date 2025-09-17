#!/usr/bin/env python3
"""
Debug WebSocket connection to staging environment with detailed logging
"""

import asyncio
import json
import os
import sys
import websockets
from tests.e2e.staging_test_config import get_staging_config
from tests.helpers.auth_test_utils import TestAuthHelper

async def debug_staging_websocket():
    """Debug WebSocket connection to staging with full logging"""

    print("=== DEBUGGING STAGING WEBSOCKET CONNECTION ===")

    # Set up config and auth
    config = get_staging_config()
    auth_helper = TestAuthHelper(environment="staging")
    test_token = auth_helper.create_test_token("debug_user", "debug@test.netrasystems.ai")

    # Get WebSocket headers
    headers = config.get_websocket_headers(test_token)

    print(f"WebSocket URL: {config.websocket_url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print()

    # Extract the exact subprotocol value being sent
    subprotocol_header = headers.get("sec-websocket-protocol", "")
    print(f"Subprotocol header: {subprotocol_header}")

    # Parse the subprotocols like the server would
    if subprotocol_header:
        client_protocols = [p.strip() for p in subprotocol_header.split(",")]
        print(f"Client protocols: {client_protocols}")

        # Test the negotiation function with these exact protocols
        from netra_backend.app.websocket_core.unified_jwt_protocol_handler import negotiate_websocket_subprotocol
        accepted_protocol = negotiate_websocket_subprotocol(client_protocols)
        print(f"Negotiation result: {accepted_protocol}")
    print()

    try:
        print("Attempting WebSocket connection...")
        # Try connecting with full debug info
        async with websockets.connect(
            config.websocket_url,
            additional_headers=headers,
            # Enable detailed client-side logging
            ping_interval=None,
            ping_timeout=None,
            close_timeout=10
        ) as ws:
            print("✅ WebSocket connection successful!")

            # Send a test message
            test_message = {"type": "ping", "timestamp": asyncio.get_event_loop().time()}
            await ws.send(json.dumps(test_message))
            print(f"Sent: {test_message}")

            # Wait for response
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=10)
                print(f"Received: {response}")
            except asyncio.TimeoutError:
                print("No response received (timeout)")

    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        print(f"Error type: {type(e).__name__}")

        # If it's a subprotocol negotiation error, let's investigate
        if "subprotocol" in str(e).lower():
            print("\n=== SUBPROTOCOL NEGOTIATION ERROR ANALYSIS ===")
            print("This indicates the server is rejecting the subprotocol negotiation")
            print("Possible causes:")
            print("1. Server negotiate_websocket_subprotocol() returning None")
            print("2. WebSocket route not calling negotiation correctly")
            print("3. Mismatch between what client sends and server expects")
            print()
            print("Debug steps:")
            print("1. Check server logs for negotiation debug messages")
            print("2. Verify WebSocket route is using negotiate_websocket_subprotocol")
            print("3. Check if websocket.accept(subprotocol=...) is being called")

        return False

    return True

if __name__ == "__main__":
    # Set up environment
    os.chdir(os.path.dirname(__file__))

    # Run the debug test
    success = asyncio.run(debug_staging_websocket())

    if success:
        print("\n✅ WebSocket debug test PASSED")
        sys.exit(0)
    else:
        print("\n❌ WebSocket debug test FAILED")
        sys.exit(1)