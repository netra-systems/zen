from shared.isolated_environment import get_env
"""
STDIO transport client for MCP using asyncio.subprocess.
Handles JSON-RPC communication over stdin/stdout with external processes.
"""

import asyncio
import json
import logging
import os
import signal
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from netra_backend.app.db.base import (
    MCPConnectionError,
    MCPProtocolError,
    MCPTimeoutError,
    MCPTransport,
)

logger = logging.getLogger(__name__)


class StdioTransport(MCPTransport):
    """
    STDIO transport for MCP using subprocess communication.
    Manages process lifecycle and JSON-RPC over stdin/stdout.
    """
    
    def __init__(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        timeout: int = 30000
    ) -> None:
        """Initialize STDIO transport with process configuration."""
        super().__init__(timeout)
        self._init_command_config(command, args, env, cwd)
        self._init_runtime_state()

    def _init_command_config(self, command: str, args: Optional[List[str]], env: Optional[Dict[str, str]], cwd: Optional[str]) -> None:
        """Initialize command configuration."""
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.cwd = cwd

    def _init_runtime_state(self) -> None:
        """Initialize runtime state variables."""
        self.process: Optional[asyncio.subprocess.Process] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._read_task: Optional[asyncio.Task] = None
        self._buffer = ""

    async def connect(self) -> None:
        """Start subprocess and establish communication."""
        if self._connected:
            return
        await self._establish_connection()

    async def _establish_connection(self) -> None:
        """Establish the subprocess connection."""
        try:
            await self._start_process()
            await self._start_reader()
            self._connected = True
            logger.info(f"STDIO transport connected: {self.command}")
        except Exception as e:
            await self._cleanup()
            raise MCPConnectionError(f"Failed to connect: {e}")

    async def _start_process(self) -> None:
        """Start the subprocess with proper configuration."""
        full_env = self._build_environment()
        cmd_args = self._build_command_args()
        self.process = await self._create_subprocess(cmd_args, full_env)

    def _build_environment(self) -> Dict[str, str]:
        """Build environment variables for subprocess."""
        # @marked: Subprocess environment inheritance for MCP server execution
        from shared.isolated_environment import IsolatedEnvironment
        env_manager = IsolatedEnvironment.get_instance()
        return env_manager.get_subprocess_env(additional_vars=self.env)

    def _build_command_args(self) -> List[str]:
        """Build command arguments list."""
        return [self.command] + self.args

    async def _create_subprocess(self, cmd_args: List[str], env: Dict[str, str]) -> asyncio.subprocess.Process:
        """Create the subprocess with given arguments and environment."""
        return await asyncio.create_subprocess_exec(
            *cmd_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=self.cwd
        )

    async def _start_reader(self) -> None:
        """Start background task to read responses."""
        if not self.process:
            raise MCPConnectionError("Process not started")
            
        self._read_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        """Continuously read and process responses from subprocess."""
        if not self._can_read():
            return
        await self._read_data_loop()

    def _can_read(self) -> bool:
        """Check if process stdout is available for reading."""
        return bool(self.process and self.process.stdout)

    async def _read_data_loop(self) -> None:
        """Main data reading loop."""
        try:
            while self._connected:
                data = await self.process.stdout.read(4096)
                if not data:
                    break
                await self._process_data(data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Reader error: {e}")
        finally:
            await self._handle_disconnect()

    async def _process_data(self, data: str) -> None:
        """Process incoming data and handle complete JSON messages."""
        self._buffer += data
        
        while '\n' in self._buffer:
            line, self._buffer = self._buffer.split('\n', 1)
            if line.strip():
                await self._handle_message(line.strip())

    async def _handle_message(self, message: str) -> None:
        """Parse and handle a complete JSON-RPC message."""
        try:
            data = json.loads(message)
            await self._process_response(data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")

    async def _process_response(self, data: Dict[str, Any]) -> None:
        """Process JSON-RPC response and resolve pending request."""
        request_id = data.get('id')
        if request_id and request_id in self._pending_requests:
            future = self._pending_requests.pop(request_id)
            if not future.cancelled():
                future.set_result(data)

    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send JSON-RPC request and wait for response."""
        self._validate_connection()
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        request_id = UnifiedIdGenerator.generate_base_id("mcp_stdio_req")
        request = await self._build_request(request_id, method, params)
        return await self._execute_request(request_id, request, method)

    def _validate_connection(self) -> None:
        """Validate that connection is active."""
        if not self._connected or not self.process:
            raise MCPConnectionError("Not connected")

    async def _execute_request(self, request_id: str, request: str, method: str) -> Dict[str, Any]:
        """Execute the request and wait for response."""
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        try:
            await self._send_data(request)
            response = await asyncio.wait_for(future, timeout=self.timeout / 1000)
            return await self._validate_response(response)
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise MCPTimeoutError(f"Request timeout: {method}")

    async def _build_request(self, request_id: str, method: str, params: Optional[Dict[str, Any]]) -> str:
        """Build JSON-RPC 2.0 request message."""
        request_obj = self._create_request_object(request_id, method, params)
        return json.dumps(request_obj) + '\n'

    def _create_request_object(self, request_id: str, method: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create request object with proper JSON-RPC format."""
        request_obj = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }
        if params is not None:
            request_obj["params"] = params
        return request_obj

    async def _send_data(self, data: str) -> None:
        """Send data to subprocess stdin."""
        if not self.process or not self.process.stdin:
            raise MCPConnectionError("Process stdin not available")
            
        self.process.stdin.write(data.encode('utf-8'))
        await self.process.stdin.drain()

    async def _validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JSON-RPC response format."""
        self._check_response_error(response)
        self._check_response_result(response)
        return response

    def _check_response_error(self, response: Dict[str, Any]) -> None:
        """Check if response contains an error."""
        if 'error' in response:
            error_info = response['error']
            raise MCPProtocolError(f"RPC Error: {error_info}")

    def _check_response_result(self, response: Dict[str, Any]) -> None:
        """Check if response contains a result."""
        if 'result' not in response:
            raise MCPProtocolError("Invalid response: missing result")

    async def disconnect(self) -> None:
        """Terminate subprocess and cleanup resources."""
        if not self._connected:
            return
            
        self._connected = False
        await self._cleanup()
        logger.info("STDIO transport disconnected")

    async def _cleanup(self) -> None:
        """Clean up all resources and terminate process."""
        await self._cancel_read_task()
        await self._terminate_process()
        self._cancel_pending_requests()

    async def _cancel_read_task(self) -> None:
        """Cancel the background reader task."""
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

    async def _terminate_process(self) -> None:
        """Terminate the subprocess gracefully."""
        if not self.process:
            return
        await self._graceful_termination()

    async def _graceful_termination(self) -> None:
        """Attempt graceful process termination."""
        try:
            await self._close_stdin()
            await asyncio.wait_for(self.process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            await self._force_termination()
        except Exception:
            await self._kill_process()

    async def _close_stdin(self) -> None:
        """Close process stdin."""
        if self.process.stdin and not self.process.stdin.is_closing():
            self.process.stdin.close()
            await self.process.stdin.wait_closed()

    async def _force_termination(self) -> None:
        """Force terminate the process."""
        self.process.terminate()
        await asyncio.wait_for(self.process.wait(), timeout=5.0)

    async def _kill_process(self) -> None:
        """Kill the process if return code is None."""
        if self.process.returncode is None:
            self.process.kill()

    def _cancel_pending_requests(self) -> None:
        """Cancel all pending requests."""
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

    async def _handle_disconnect(self) -> None:
        """Handle unexpected disconnection."""
        if self._connected:
            self._connected = False
            self._cancel_pending_requests()
            logger.warning("STDIO transport disconnected unexpectedly")


class StdioTransportError(MCPConnectionError):
    """STDIO transport specific error."""
    pass
