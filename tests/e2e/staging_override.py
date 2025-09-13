
def is_staging_available():
    """Override function to bypass staging health check for testing"""
    print("[TEST OVERRIDE] Bypassing staging health check for WebSocket subprotocol validation")
    return True
