"""
Agent Startup Test Integration Hook

Provides integration between agent startup tests and the main test_runner.py framework.
Enables execution of agent startup tests through standard test runner interface.

Business Value Justification (BVJ):
1. Segment: ALL segments - testing infrastructure
2. Business Goal: Seamless integration of agent startup validation
3. Value Impact: Enables easy execution of critical startup tests
4. Revenue Impact: Protects revenue by ensuring reliable startup testing

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Integrates with existing test framework
- Supports all test runner flags and options
"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from netra_backend.tests.unified.run_agent_startup_tests import (
    run_agent_startup_test_suite,
    print_startup_test_summary
)


class AgentStartupIntegration:
    """Integration layer for agent startup tests with test runner."""
    
    def __init__(self):
        """Initialize integration handler."""
        self.last_report: Optional[Dict[str, Any]] = None
    
    async def run_agent_startup_suite(self, real_llm: bool = False, 
                                      parallel: bool = True) -> int:
        """Run agent startup test suite and return exit code."""
        try:
            report = await run_agent_startup_test_suite(real_llm, parallel)
            self.last_report = report
            
            self._print_integration_summary(report)
            return self._calculate_exit_code(report)
        except Exception as e:
            print(f"[ERROR] Agent startup test suite failed: {e}")
            return 1
    
    def _print_integration_summary(self, report: Dict[str, Any]) -> None:
        """Print integration summary for test runner."""
        print("\n" + "=" * 80)
        print("AGENT STARTUP TESTS INTEGRATION SUMMARY")
        print("=" * 80)
        
        summary = report.get("summary", {})
        config = report.get("configuration", {})
        
        print(f"Real LLM Enabled: {config.get('real_llm_enabled', False)}")
        print(f"Parallel Execution: {config.get('parallel_execution', True)}")
        print(f"Test Categories: {config.get('total_categories', 0)}")
        
        if summary:
            print(f"Pass Rate: {summary.get('pass_rate', 0):.1f}%")
            print(f"Execution Time: {report.get('execution_time', 0):.2f}s")
    
    def _calculate_exit_code(self, report: Dict[str, Any]) -> int:
        """Calculate appropriate exit code from test results."""
        summary = report.get("summary", {})
        failed_count = summary.get("failed", 0)
        return 0 if failed_count == 0 else 1
    
    def get_test_categories(self) -> list:
        """Get list of available test categories."""
        return [
            "cold_start",
            "concurrent_startup", 
            "tier_startup",
            "agent_isolation",
            "routing_startup",
            "performance_startup"
        ]
    
    def supports_real_llm(self) -> bool:
        """Check if agent startup tests support real LLM testing."""
        return True
    
    def get_estimated_duration(self, real_llm: bool = False) -> int:
        """Get estimated test duration in seconds."""
        return 120 if real_llm else 60  # 2 minutes with real LLM, 1 minute without


def create_integration_handler() -> AgentStartupIntegration:
    """Create agent startup integration handler."""
    return AgentStartupIntegration()


async def run_startup_tests_integration(real_llm: bool = False, 
                                        parallel: bool = True) -> int:
    """Main integration function for test runner."""
    handler = create_integration_handler()
    return await handler.run_agent_startup_suite(real_llm, parallel)


def get_startup_test_info() -> Dict[str, Any]:
    """Get information about agent startup tests for discovery."""
    return {
        "name": "Agent Startup E2E Tests",
        "description": "Comprehensive agent initialization and startup validation",
        "categories": [
            {
                "name": "cold_start",
                "description": "Agent cold start from zero state",
                "requires_real_llm": True,
                "timeout": 30
            },
            {
                "name": "concurrent_startup", 
                "description": "Concurrent agent startup isolation",
                "requires_real_llm": True,
                "timeout": 45
            },
            {
                "name": "tier_startup",
                "description": "Startup across different user tiers",
                "requires_real_llm": True, 
                "timeout": 60
            },
            {
                "name": "agent_isolation",
                "description": "Agent state isolation validation",
                "requires_real_llm": False,
                "timeout": 30
            },
            {
                "name": "routing_startup",
                "description": "Message routing during startup",
                "requires_real_llm": False,
                "timeout": 25
            },
            {
                "name": "performance_startup",
                "description": "Performance metrics under startup load",
                "requires_real_llm": True,
                "timeout": 40
            }
        ],
        "supports_real_llm": True,
        "supports_parallel": True,
        "estimated_duration": 120,  # seconds
        "business_value": "Protects entire $200K+ MRR by ensuring reliable agent startup"
    }


# Command-line interface for direct execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Startup Test Integration")
    parser.add_argument("--real-llm", action="store_true", 
                        help="Enable real LLM testing")
    parser.add_argument("--no-parallel", action="store_true",
                        help="Disable parallel execution")
    parser.add_argument("--info", action="store_true",
                        help="Show test information")
    
    args = parser.parse_args()
    
    if args.info:
        info = get_startup_test_info()
        print("Agent Startup Test Information:")
        print(f"Name: {info['name']}")
        print(f"Description: {info['description']}")
        print(f"Categories: {len(info['categories'])}")
        print(f"Supports Real LLM: {info['supports_real_llm']}")
        print(f"Estimated Duration: {info['estimated_duration']}s")
        print(f"Business Value: {info['business_value']}")
        sys.exit(0)
    
    async def main():
        """Main async execution for integration."""
        exit_code = await run_startup_tests_integration(
            real_llm=args.real_llm,
            parallel=not args.no_parallel
        )
        sys.exit(exit_code)
    
    asyncio.run(main())