async def wait_for_agent_completion(
    websocket,
    connection_id: str,
    timeout: float = 30.0,
    expected_events: Optional[List[str]] = None
) -> bool:
    """
    Wait for agent completion by monitoring WebSocket events.
    
    This function waits for the agent_completed event or all expected events
    to be received through the WebSocket connection, confirming that an agent
    has successfully completed its execution.
    
    Args:
        websocket: WebSocket connection to monitor
        connection_id: Connection ID for the agent execution
        timeout: Maximum time to wait for completion (default: 30 seconds)
        expected_events: Optional list of specific events to wait for
                        (default: waits for 'agent_completed')
    
    Returns:
        bool: True if agent completed successfully, False if timeout
        
    Raises:
        RuntimeError: If WebSocket connection fails during monitoring
        asyncio.TimeoutError: If timeout is reached without completion
    """
    if expected_events is None:
        expected_events = ["agent_completed"]
    
    received_events = []
    start_time = time.time()
    
    try:
        while time.time() - start_time < timeout:
            try:
                # Receive message with short timeout to check regularly
                message = await WebSocketTestHelpers.receive_test_message(
                    websocket, timeout=1.0
                )
                
                if message and isinstance(message, dict):
                    event_type = message.get("type")
                    if event_type:
                        received_events.append(event_type)
                        logger.debug(f"Received WebSocket event: {event_type}")
                        
                        # Check if we've received all expected events
                        if all(event in received_events for event in expected_events):
                            logger.info(f"Agent completion confirmed - received all expected events: {expected_events}")
                            return True
                            
            except asyncio.TimeoutError:
                # Continue checking - this is expected for the short timeout
                continue
            except Exception as e:
                logger.warning(f"Error receiving WebSocket message during agent completion wait: {e}")
                # Continue trying unless it's a connection error
                if "connection" in str(e).lower() or "closed" in str(e).lower():
                    raise RuntimeError(f"WebSocket connection failed during agent completion wait: {e}")
                continue
    
    except asyncio.TimeoutError:
        logger.error(f"Timeout waiting for agent completion after {timeout}s. Expected events: {expected_events}, Received: {received_events}")
        return False
    except Exception as e:
        logger.error(f"Error during agent completion wait: {e}")
        raise RuntimeError(f"Failed to wait for agent completion: {e}")
    
    logger.error(f"Agent completion timeout after {timeout}s. Expected events: {expected_events}, Received: {received_events}")
    return False