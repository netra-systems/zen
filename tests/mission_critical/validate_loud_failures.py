class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks."

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        ""Send JSON message."
        if self._closed:
        raise RuntimeError(WebSocket is closed)"
        raise RuntimeError(WebSocket is closed)"
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = Normal closure"):"
        Close WebSocket connection.""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        Get all sent messages."
        Get all sent messages."
        return self.messages_sent.copy()

        '''
        '''
        Direct validation script for loud WebSocket failures
        '''
        '''

        import asyncio
        import sys
        import os

    # Set UTF-8 encoding for Windows
        if sys.platform == 'win32':
        os.system('chcp 65001 > nul 2>&1')
        sys.stdout.reconfigure(encoding='utf-8')

        # Add paths for imports
        sys.path.insert(0, r"C:\Users\antho\OneDrive\Desktop\Netra )"
        etra-core-generation-1)

        from netra_backend.app.core.websocket_exceptions import ( )
        WebSocketBridgeUnavailableError,
        WebSocketContextValidationError,
        WebSocketSendFailureError,
        WebSocketBufferOverflowError,
        AgentCommunicationFailureError
        
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as UserWebSocketEmitter
        from netra_backend.app.websocket_core.message_buffer import WebSocketMessageBuffer, BufferConfig, BufferPriority
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


    async def test_tool_execution_without_context():
        Test that tool execution without context raises WebSocketContextValidationError.""
        print()
        PASS:  Testing: Tool execution without context...)

        engine = UnifiedToolExecutionEngine()
        engine.notification_monitor = Magic
        try:
        await engine._send_tool_executing( )
        context=None,
        tool_name="TestTool,"
        tool_input={param: value}
                
        print( FAIL:  FAILED: Should have raised WebSocketContextValidationError)
        return False
        except WebSocketContextValidationError as e:
        print("")
        assert Missing execution context in str(e")"
        return True
        except Exception as e:
        print()
        return False


    async def test_tool_execution_without_bridge():
        "Test that tool execution without WebSocket bridge raises exception."
        print()
        PASS:  Testing: Tool execution without bridge...)

        engine = UnifiedToolExecutionEngine()
        engine.websocket_bridge = None  # No bridge available
        engine.notification_monitor = Magic
                            # Create mock context
        mock_context = Magic    mock_context.run_id = test-run-123""
        mock_context.user_id = user-456
        mock_context.thread_id = thread-789"
        mock_context.thread_id = thread-789"
        mock_context.agent_name = "TestAgent"

        try:
        await engine._send_tool_executing( )
        context=mock_context,
        tool_name=TestTool,
        tool_input={"param: value}"
                                
        print( FAIL:  FAILED: Should have raised WebSocketBridgeUnavailableError)
        return False
        except WebSocketBridgeUnavailableError as e:
        print(formatted_string"")
        assert WebSocket bridge unavailable in str(e)
        assert e.user_id == user-456""
        assert e.thread_id == thread-789
        return True
        except Exception as e:
        print(formatted_string")"
        return False


    async def test_agent_notification_failure():
        Test that failed agent notifications raise WebSocketSendFailureError."
        Test that failed agent notifications raise WebSocketSendFailureError."
        print("")
        PASS:  Testing: Agent notification failure...)"
        PASS:  Testing: Agent notification failure...)"

                                            # Create mock WebSocket bridge that returns failure
        websocket = TestWebSocketConnection()
        mock_bridge.notify_agent_started = AsyncMock(return_value=False)

        emitter = UserWebSocketEmitter( )
        user_id=user-123,
        thread_id="thread-456,"
        run_id=run-789,
        websocket_bridge=mock_bridge
                                            

        try:
        await emitter.notify_agent_started(TestAgent, {context: "data)"
        print( FAIL:  FAILED: Should have raised WebSocketSendFailureError)
        return False
        except WebSocketSendFailureError as e:
        print()
        assert WebSocket bridge returned failure in str(e)
        assert e.user_id == "user-123"
        return True
        except Exception as e:
        print(formatted_string)
        return False


    async def test_message_buffer_overflow():
        Test that message buffer overflow raises WebSocketBufferOverflowError."
        Test that message buffer overflow raises WebSocketBufferOverflowError."
        print()
        PASS:  Testing: Message buffer overflow...")"

        config = BufferConfig( )
        max_message_size_bytes=100,  # Small limit for testing
        max_buffer_size_per_user=10,
        max_buffer_size_global=1000
                                                            

        buffer = WebSocketMessageBuffer(config=config)

                                                            # Create a message that's too large'
        large_message = {data: x * 200}  # Exceeds 100 byte limit

        try:
        await buffer.buffer_message( )
        user_id="user-123,"
        message=large_message,
        priority=BufferPriority.HIGH
                                                                
        print( FAIL:  FAILED: Should have raised WebSocketBufferOverflowError)
        return False
        except WebSocketBufferOverflowError as e:
        print("")
        assert Message buffer overflow in str(e)"
        assert Message buffer overflow in str(e)"
        assert e.user_id == "user-123"
        return True
        except Exception as e:
        print(formatted_string)"
        print(formatted_string)"
        return False


    async def main():
        "Run all validation tests."
        print(=" * 80)"
        print(VALIDATING LOUD WEBSOCKET FAILURES)"
        print(VALIDATING LOUD WEBSOCKET FAILURES)"
        print(=" * 80)"

        results = []

    # Run all tests
        results.append(await test_tool_execution_without_context())
        results.append(await test_tool_execution_without_bridge())
        results.append(await test_agent_notification_failure())
        results.append(await test_message_buffer_overflow())

    # Summary
        print(")"
         + = * 80)
        print(VALIDATION SUMMARY)
        print(=" * 80)"

        passed = sum(results)
        failed = len(results) - passed

        if failed == 0:
        print(formatted_string")"
        print()
        TARGET:  WebSocket failures are now LOUD and visible!)
        print([U+1F50A] No more silent failures - users will be informed of issues!"")
        else:
        print(")"
        print()
        WARNING: [U+FE0F] Some silent failures may still exist!")"

        return failed == 0


        if __name__ == "__main__:"
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
