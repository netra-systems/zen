# Use backend-specific isolated environment
try:
    from netra_backend.app.core.isolated_environment import get_env
except ImportError:
    # Production fallback if isolated_environment module unavailable
    import os
    def get_env():
        """Fallback environment accessor for production."""
        class FallbackEnv:
            def get(self, key, default=None):
                return os.environ.get(key, default)
            def set(self, key, value, source="production"):
                os.environ[key] = value
        return FallbackEnv()
except ImportError:
    # Production fallback if isolated_environment module unavailable
    import os
    def get_env():
        """Fallback environment accessor for production."""
        class FallbackEnv:
            def get(self, key, default=None):
                return os.environ.get(key, default)
            def set(self, key, value, source="production"):
                os.environ[key] = value
        return FallbackEnv()
"""Sandboxed Python interpreter for secure code execution.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Enables safe execution of calculations and analysis code
with strict resource limits and isolation.
"""

import asyncio
import json
import os
import tempfile
from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SandboxedInterpreter:
    """Secure Python execution environment using Docker (<300 lines)."""
    
    def __init__(self, docker_image: Optional[str] = None):
        self._init_sandbox_config(docker_image)
        self._init_resource_limits()
        self._init_security_settings()
    
    def _init_sandbox_config(self, docker_image: Optional[str]) -> None:
        """Initialize sandbox configuration."""
        self.docker_image = docker_image or get_env().get(
            "SANDBOX_DOCKER_IMAGE", "python:3.11-slim"
        )
        self.container_name_prefix = "nacis_sandbox_"
        self.working_dir = "/sandbox"
    
    def _init_resource_limits(self) -> None:
        """Initialize resource limits."""
        self.max_memory = get_env().get("SANDBOX_MAX_MEMORY", "512m")
        self.max_cpu = get_env().get("SANDBOX_MAX_CPU", "0.5")
        self.default_timeout = 10000  # 10 seconds
        self.network_mode = "none"  # No network access
    
    def _init_security_settings(self) -> None:
        """Initialize security settings."""
        self.read_only = True
        self.user = "nobody"
        self.allowed_packages = ["numpy", "pandas", "math"]
    
    async def execute(self, code: str, timeout_ms: int = None) -> Dict[str, Any]:
        """Execute Python code in sandboxed environment."""
        try:
            timeout = (timeout_ms or self.default_timeout) / 1000
            prepared_code = self._prepare_code(code)
            result = await self._run_in_sandbox(prepared_code, timeout)
            return self._format_success_result(result)
        except Exception as e:
            return self._format_error_result(str(e))
    
    def _prepare_code(self, code: str) -> str:
        """Prepare code for execution."""
        imports = self._generate_safe_imports()
        wrapped = self._wrap_code_safely(code)
        return f"{imports}\n{wrapped}"
    
    def _generate_safe_imports(self) -> str:
        """Generate safe import statements."""
        imports = [
            "import json",
            "import math",
            "from decimal import Decimal"
        ]
        return "\n".join(imports)
    
    def _wrap_code_safely(self, code: str) -> str:
        """Wrap code for safe execution."""
        return f"""
def safe_execute():
    result = {{}}
    {self._indent_code(code)}
    return result

try:
    output = safe_execute()
    print(json.dumps(output))
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
"""
    
    def _indent_code(self, code: str) -> str:
        """Indent code for wrapping."""
        lines = code.split('\n')
        return '\n    '.join(lines)
    
    async def _run_in_sandbox(self, code: str, timeout: float) -> str:
        """Run code in Docker sandbox."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as f:
            f.write(code)
            f.flush()
            return await self._execute_docker_command(f.name, timeout)
    
    async def _execute_docker_command(self, script_path: str, timeout: float) -> str:
        """Execute Docker command with script."""
        cmd = self._build_docker_command(script_path)
        return await self._run_command_with_timeout(cmd, timeout)
    
    def _build_docker_command(self, script_path: str) -> list:
        """Build Docker run command."""
        return [
            "docker", "run",
            "--rm",  # Remove container after execution
            "--network", self.network_mode,
            "--memory", self.max_memory,
            "--cpus", self.max_cpu,
            "--read-only" if self.read_only else "",
            "-v", f"{script_path}:/sandbox/script.py:ro",
            self.docker_image,
            "python", "/sandbox/script.py"
        ]
    
    async def _run_command_with_timeout(self, cmd: list, timeout: float) -> str:
        """Run command with timeout."""
        try:
            process = await asyncio.create_subprocess_exec(
                *[c for c in cmd if c],  # Filter empty strings
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            return self._process_command_output(stdout, stderr)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Execution exceeded {timeout}s limit")
    
    def _process_command_output(self, stdout: bytes, stderr: bytes) -> str:
        """Process command output."""
        if stderr:
            logger.warning(f"Sandbox stderr: {stderr.decode()}")
        return stdout.decode().strip()
    
    def _format_success_result(self, output: str) -> Dict[str, Any]:
        """Format successful execution result."""
        try:
            parsed = json.loads(output)
            return {"status": "success", "output": parsed}
        except json.JSONDecodeError:
            return {"status": "success", "output": {"raw": output}}
    
    def _format_error_result(self, error: str) -> Dict[str, Any]:
        """Format error result."""
        return {
            "status": "error",
            "error": error,
            "output": {}
        }
    
    async def validate_environment(self) -> bool:
        """Validate sandbox environment is ready."""
        test_code = "print('sandbox_ready')"
        result = await self.execute(test_code, 5000)
        return result.get("status") == "success"