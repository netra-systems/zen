#!/usr/bin/env python3
"""
Debug WebSocket subprotocol negotiation in staging environment
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'netra_backend'))

from netra_backend.app.websocket_core.unified_jwt_protocol_handler import negotiate_websocket_subprotocol

def test_subprotocol_negotiation():
    """Test the subprotocol negotiation function with staging test data"""

    # Test case 1: Staging test format
    staging_protocols = ["e2e-testing", "jwt.ZXlKaGJHY2lPaUpJVXpJ"]
    result1 = negotiate_websocket_subprotocol(staging_protocols)
    print(f"Test 1 - Staging format: {staging_protocols}")
    print(f"Result: {result1}")
    print()

    # Test case 2: Simple JWT format
    simple_protocols = ["jwt.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"]
    result2 = negotiate_websocket_subprotocol(simple_protocols)
    print(f"Test 2 - Simple JWT: {simple_protocols}")
    print(f"Result: {result2}")
    print()

    # Test case 3: Direct protocol names only
    direct_protocols = ["e2e-testing", "jwt-auth"]
    result3 = negotiate_websocket_subprotocol(direct_protocols)
    print(f"Test 3 - Direct protocols: {direct_protocols}")
    print(f"Result: {result3}")
    print()

    # Test case 4: Mixed formats
    mixed_protocols = ["e2e-testing", "jwt.TOKEN123", "jwt-auth"]
    result4 = negotiate_websocket_subprotocol(mixed_protocols)
    print(f"Test 4 - Mixed formats: {mixed_protocols}")
    print(f"Result: {result4}")
    print()

if __name__ == "__main__":
    test_subprotocol_negotiation()