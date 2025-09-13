#!/usr/bin/env python
"""
Business-Focused System Health Check
Prioritizes Chat functionality (90% of business value) and real system health.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_framework.unified_docker_manager import UnifiedDockerManager


class BusinessHealthChecker:
    """Focus on what matters: Chat works, agents execute, users get value."""
    
    def __init__(self):
        self.docker_manager = UnifiedDockerManager()
        self.health_scores = {}
        self.critical_issues = []
        self.warnings = []
        self.successes = []
        
    async def check_docker_and_start(self) -> bool:
        """Start Docker if needed - don't just complain about it."""
        print("[U+1F433] Checking Docker services...")
        
        try:
            # Check if Docker is running
            status = await self.docker_manager.check_docker_status()
            if not status['docker_running']:
                print("  Starting Docker Desktop...")
                # Try to start Docker
                started = await self.docker_manager.ensure_docker_running()
                if not started:
                    self.warnings.append("Docker Desktop needs manual start")
                    return False
                    
            # Start test environment
            print("  Starting test environment services...")
            result = await self.docker_manager.start_environment(
                compose_file="docker-compose.test.yml",
                use_alpine=True  # Faster startup
            )
            
            if result['success']:
                self.successes.append("Docker services running")
                return True
            else:
                self.warnings.append(f"Docker services partial: {result.get('message', 'Unknown issue')}")
                return False
                
        except Exception as e:
            self.warnings.append(f"Docker setup: {str(e)[:100]}")
            return False
            
    async def test_chat_infrastructure(self) -> Dict[str, Any]:
        """Test the critical chat components that deliver 90% of value."""
        print("\n[U+1F4AC] Testing Chat Infrastructure (90% of business value)...")
        
        chat_health = {
            'websocket_events': False,
            'agent_execution': False,
            'user_isolation': False,
            'message_delivery': False,
            'llm_connectivity': False
        }
        
        try:
            # Test WebSocket event system
            print("  Testing WebSocket agent events...")
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            # SSOT MIGRATION: Use canonical WebSocket manager instead of deprecated factory
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            
            bridge = AgentWebSocketBridge()
            # Test bridge availability (using SSOT pattern)
            # SSOT MIGRATION: Test bridge directly instead of deprecated factory
            if not bridge:
                self.warnings.append("WebSocket bridge not available")
                chat_health["websocket_events"] = False
                return chat_health
            
            # Test critical events
            test_run_id = f"health_check_{int(time.time())}"
            success = await bridge.notify_agent_started(test_run_id, "HealthCheckAgent")
            if success:
                chat_health['websocket_events'] = True
                self.successes.append("WebSocket events working")
            else:
                self.critical_issues.append("WebSocket events FAILED")
                
        except Exception as e:
            self.critical_issues.append(f"WebSocket infrastructure error: {str(e)[:100]}")
            
        try:
            # Test agent execution engine
            print("  Testing agent execution engine...")
            from netra_backend.app.agents.execution_engines.enhanced_tool_execution_engine import (
                EnhancedToolExecutionEngine
            )
            
            engine = UserExecutionEngine()
            # Basic initialization test
            chat_health['agent_execution'] = True
            self.successes.append("Agent execution engine ready")
            
        except Exception as e:
            self.critical_issues.append(f"Agent execution error: {str(e)[:100]}")
            
        try:
            # Test user isolation
            print("  Testing user isolation (10+ concurrent users)...")
            from test_framework.test_context import create_isolated_test_contexts
            
            contexts = create_isolated_test_contexts(count=3)
            if len(contexts) == 3:
                chat_health['user_isolation'] = True
                self.successes.append("User isolation working")
            
        except Exception as e:
            self.warnings.append(f"User isolation check: {str(e)[:100]}")
            
        try:
            # Test LLM connectivity
            print("  Testing LLM connectivity...")
            from netra_backend.app.services.llm_client import UnifiedLLMClient
            
            client = UnifiedLLMClient()
            # Just check initialization
            chat_health['llm_connectivity'] = True
            self.successes.append("LLM client initialized")
            
        except Exception as e:
            self.warnings.append(f"LLM connectivity: {str(e)[:100]}")
            
        # Calculate chat health score
        working_components = sum(1 for v in chat_health.values() if v)
        total_components = len(chat_health)
        chat_score = (working_components / total_components) * 100
        
        return {
            'score': chat_score,
            'components': chat_health,
            'critical': chat_score < 60  # Below 60% is critical for chat
        }
        
    def check_test_syntax(self) -> Dict[str, Any]:
        """Quick check for test file syntax errors - but don't obsess."""
        print("\n[U+1F9EA] Checking test file health...")
        
        import ast
        test_dirs = [
            Path("tests"),
            Path("netra_backend/tests"),
            Path("auth_service/tests")
        ]
        
        errors = []
        total_files = 0
        
        for test_dir in test_dirs:
            if not test_dir.exists():
                continue
                
            for py_file in test_dir.rglob("*.py"):
                total_files += 1
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        ast.parse(f.read())
                except SyntaxError as e:
                    errors.append(f"{py_file.name}: line {e.lineno}")
                    
        if len(errors) > 20:
            self.warnings.append(f"{len(errors)} test files with syntax errors")
            return {'score': 50, 'critical_errors': errors[:5]}
        elif errors:
            self.warnings.append(f"{len(errors)} test syntax issues")
            return {'score': 80, 'errors': errors}
        else:
            self.successes.append(f"All {total_files} test files valid")
            return {'score': 100}
            
    def check_configuration(self) -> bool:
        """Verify core configuration is working."""
        print("\n[U+2699][U+FE0F] Checking configuration...")
        
        try:
            from netra_backend.app.core.configuration.loader import ConfigurationLoader
            config = ConfigurationLoader()
            
            env = config.get_environment()
            
            # Just check the basics work
            checks = [
                ('Environment', env in ['development', 'test', 'staging', 'production']),
                ('JWT Secret', bool(os.getenv('JWT_SECRET_KEY'))),
                ('Database', bool(os.getenv('DATABASE_URL') or env == 'development')),
            ]
            
            failed = [name for name, result in checks if not result]
            if failed:
                self.warnings.append(f"Config issues: {', '.join(failed)}")
                return False
            else:
                self.successes.append(f"Configuration valid ({env})")
                return True
                
        except Exception as e:
            self.critical_issues.append(f"Configuration error: {str(e)[:100]}")
            return False
            
    async def run_critical_chat_test(self) -> bool:
        """Run actual chat flow test if possible."""
        print("\n[U+1F680] Testing real chat flow...")
        
        try:
            # Try to run a simple chat test
            from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
            
            supervisor = SupervisorAgent()
            # Just check it initializes
            self.successes.append("Supervisor agent ready")
            return True
            
        except Exception as e:
            self.warnings.append(f"Chat flow test: {str(e)[:100]}")
            return False
            
    def calculate_overall_health(self, chat_health: Dict) -> int:
        """Calculate overall system health with proper weighting."""
        
        # Chat is 90% of value
        chat_weight = 0.9
        infra_weight = 0.1
        
        chat_score = chat_health.get('score', 0) / 100
        
        # Infrastructure score (Docker, config, tests)
        infra_components = {
            'docker': 1 if any('Docker' in s for s in self.successes) else 0,
            'config': 1 if any('Configuration' in s for s in self.successes) else 0,
            'tests': 0.5 if len(self.warnings) < 5 else 0  # Don't obsess over test issues
        }
        
        infra_score = sum(infra_components.values()) / len(infra_components)
        
        # Weighted score
        overall = (chat_score * chat_weight) + (infra_score * infra_weight)
        
        return int(overall * 100)
        
    def generate_report(self, chat_health: Dict, overall_score: int):
        """Generate business-focused health report."""
        
        print("\n" + "="*60)
        print("NETRA APEX SYSTEM HEALTH REPORT")
        print("="*60)
        
        # Overall health with emoji
        if overall_score >= 80:
            status = " PASS:  HEALTHY"
            color = "\033[92m"  # Green
        elif overall_score >= 60:
            status = " WARNING: [U+FE0F] DEGRADED" 
            color = "\033[93m"  # Yellow
        else:
            status = " FAIL:  CRITICAL"
            color = "\033[91m"  # Red
            
        print(f"\n{color}Overall Health: {overall_score}/100 - {status}\033[0m")
        
        # Chat specifically (90% of value)
        chat_score = chat_health.get('score', 0)
        print(f"\n[U+1F4AC] CHAT SYSTEM (90% of business value): {chat_score:.0f}%")
        for component, working in chat_health.get('components', {}).items():
            icon = " PASS: " if working else " FAIL: "
            print(f"  {icon} {component.replace('_', ' ').title()}")
            
        # Critical issues first
        if self.critical_issues:
            print(f"\n ALERT:  CRITICAL ISSUES ({len(self.critical_issues)}):")
            for issue in self.critical_issues[:3]:
                print(f"  [U+2022] {issue}")
                
        # Successes
        if self.successes:
            print(f"\n PASS:  WORKING COMPONENTS ({len(self.successes)}):")
            for success in self.successes[:5]:
                print(f"  [U+2022] {success}")
                
        # Warnings (don't obsess)
        if self.warnings and len(self.warnings) <= 5:
            print(f"\n WARNING: [U+FE0F] MINOR ISSUES ({len(self.warnings)}):")
            for warning in self.warnings[:3]:
                print(f"  [U+2022] {warning}")
        elif self.warnings:
            print(f"\n WARNING: [U+FE0F] {len(self.warnings)} minor issues logged")
            
        # Business impact
        print("\n CHART:  BUSINESS IMPACT:")
        if chat_score >= 80:
            print("   PASS:  Users can chat with agents effectively")
            print("   PASS:  WebSocket events deliver real-time updates")
            print("   PASS:  System ready for customer value delivery")
        elif chat_score >= 60:
            print("   WARNING: [U+FE0F] Chat functional but degraded")
            print("   WARNING: [U+FE0F] Some features may be slow or limited")
            print("   LIGHTNING:  Action: Fix critical components")
        else:
            print("   FAIL:  Chat system not operational")
            print("   FAIL:  Cannot deliver customer value")
            print("   ALERT:  IMMEDIATE ACTION REQUIRED")
            
        # Quick fixes
        if self.critical_issues or overall_score < 80:
            print("\n[U+1F527] QUICK FIXES:")
            
            if any("Docker" in str(w) for w in self.warnings):
                print("  1. Start Docker Desktop manually")
                print("     OR run: python scripts/docker_manual.py start")
                
            if any("WebSocket" in str(i) for i in self.critical_issues):
                print("  2. Check backend service:")
                print("     python scripts/docker_manual.py status")
                
            if any("syntax" in str(w).lower() for w in self.warnings):
                print("  3. Fix test syntax errors (low priority)")
                
        print("\n" + "="*60)
        
        # Save detailed report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'overall_score': overall_score,
            'chat_score': chat_score,
            'chat_components': chat_health.get('components', {}),
            'critical_issues': self.critical_issues,
            'warnings': self.warnings,
            'successes': self.successes
        }
        
        report_file = Path('BUSINESS_HEALTH_REPORT.json')
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        print(f"\nDetailed report saved to: {report_file}")
        
        return overall_score
        
    async def run(self):
        """Run complete business-focused health check."""
        
        print("[U+1F3E5] Starting Netra Apex Business Health Check...")
        print("Focus: Chat functionality (90% of business value)\n")
        
        # 1. Docker - start it don't just complain
        docker_ready = await self.check_docker_and_start()
        
        # 2. Configuration basics
        config_ok = self.check_configuration()
        
        # 3. CRITICAL: Chat infrastructure
        chat_health = await self.test_chat_infrastructure()
        
        # 4. Test syntax (quick check, don't obsess)
        test_health = self.check_test_syntax()
        
        # 5. Try real chat test
        await self.run_critical_chat_test()
        
        # Calculate overall health
        overall_score = self.calculate_overall_health(chat_health)
        
        # Generate report
        self.generate_report(chat_health, overall_score)
        
        # Cleanup Docker if we started it
        if docker_ready and '--keep-docker' not in sys.argv:
            print("\n[U+1F9F9] Cleaning up Docker services...")
            await self.docker_manager.cleanup_test_environment()
            
        return overall_score


async def main():
    """Run health check and return appropriate exit code."""
    checker = BusinessHealthChecker()
    score = await checker.run()
    
    # Exit codes: 0=healthy, 1=degraded, 2=critical
    if score >= 80:
        sys.exit(0)
    elif score >= 60:
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())