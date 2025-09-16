"""Critical test helpers."""

import asyncio
from typing import Any, Dict, List

async def run_critical_test_scenario(steps: List[callable]) -> List[Any]:
    """Run a critical test scenario."""
    results = []
    for step in steps:
        if asyncio.iscoroutinefunction(step):
            result == await step()
        else:
            result = step()
        results.append(result)
    return results

def validate_critical_response(response: Dict[str, Any]) -> bool:
    """Validate a critical response."""
    return response.get("status") == "success"
