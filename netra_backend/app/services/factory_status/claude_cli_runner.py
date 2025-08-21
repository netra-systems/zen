"""Claude CLI runner for deep compliance review."""

import asyncio
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


class ClaudeCLIRunner:
    """Runs Claude CLI for deep compliance review (dev only)."""
    
    def __init__(self, enabled: bool = False):
        """Initialize Claude CLI runner."""
        from netra_backend.app.core.configuration import unified_config_manager
        config = unified_config_manager.get_config()
        env = getattr(config, 'environment', 'staging')  # Default to staging for safety
        self.enabled = enabled and env != "production"
    
    async def run_compliance_review(self, module_path: Path) -> Optional[Dict[str, Any]]:
        """Run Claude CLI compliance review."""
        if not self.enabled:
            return None
        try:
            response = await self._execute_claude_cli(module_path)
            return self._process_claude_response(response)
        except Exception as e:
            self._log_claude_error(e)
            return None
    
    def _log_claude_error(self, error: Exception) -> None:
        """Log Claude CLI error."""
        print(f"Claude CLI error: {error}")
    
    async def _execute_claude_cli(self, module_path: Path) -> str:
        """Execute Claude CLI command and return response."""
        prompt = f"Review {module_path} for SPEC compliance. Score 0-100."
        cmd = ["claude", "code", "--path", str(module_path), "--prompt", prompt]
        result = await self._create_subprocess(cmd)
        stdout, _ = await result.communicate()
        return stdout.decode()
    
    async def _create_subprocess(self, cmd: list) -> Any:
        """Create subprocess for Claude CLI execution."""
        return await asyncio.create_subprocess_exec(
            *cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    
    def _process_claude_response(self, response: str) -> Dict[str, Any]:
        """Process Claude CLI response."""
        score = self._extract_score(response)
        return {"score": score, "insights": response[:500]}
    
    def _extract_score(self, response: str) -> float:
        """Extract score from Claude response."""
        # Simple extraction - look for number between 0-100
        match = re.search(r'\b([0-9]{1,2}|100)\b', response)
        return float(match.group(1)) if match else 75.0