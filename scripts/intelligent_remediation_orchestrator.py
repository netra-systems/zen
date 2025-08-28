#!/usr/bin/env python3
"""
Intelligent Remediation Orchestrator - Multi-Agent Team Coordination

This orchestrator implements the two operational modes defined in 
SPEC/intelligent_remediation_architecture.xml:

1. Tool Mode: LLM agents as information providers to Claude
2. Orchestrator Mode: Spawning autonomous Claude instances

V1 Critical Implementation - Focused on core orchestration capabilities
"""

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.intelligent_docker_remediation import (
    DockerRemediationSystem,
    DockerIssue,
    IssueCategory,
    IssueSeverity
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OperationalMode(Enum):
    """Operational modes for the remediation system"""
    TOOL_MODE = "tool"  # LLM agents provide analysis to Claude
    ORCHESTRATOR_MODE = "orchestrator"  # Spawn autonomous Claude instances


@dataclass
class AgentTask:
    """Represents a task for an LLM agent"""
    agent_type: str
    issue: DockerIssue
    prompt: str
    mode: OperationalMode
    task_id: str
    created_at: datetime
    completed: bool = False
    result: Optional[Dict[str, Any]] = None


class IntelligentRemediationOrchestrator:
    """
    Orchestrates multi-agent remediation using classical and LLM components
    as defined in SPEC/intelligent_remediation_architecture.xml
    """
    
    def __init__(self, mode: OperationalMode = OperationalMode.TOOL_MODE):
        self.mode = mode
        self.remediation_system = DockerRemediationSystem(safe_mode=True)
        self.agent_tasks: List[AgentTask] = []
        self.task_counter = 0
        
        # Agent type mappings (as per spec)
        self.agent_types = {
            IssueCategory.DATABASE_CONNECTIVITY: "database_specialist",
            IssueCategory.AUTH_PERMISSION: "security_specialist",
            IssueCategory.NETWORK_CONNECTIVITY: "network_specialist",
            IssueCategory.RESOURCE_EXHAUSTION: "performance_specialist",
            IssueCategory.CONFIGURATION_ERROR: "configuration_specialist",
            IssueCategory.STARTUP_FAILURE: "critical_response_specialist"
        }
        
        logger.info(f"Orchestrator initialized in {mode.value} mode")
    
    def run_introspection(self) -> Dict[str, Any]:
        """
        CLASSICAL COMPONENT: Run system introspection
        Uses deterministic patterns to collect data
        """
        logger.info("Running classical introspection...")
        
        # Check Docker availability
        if not self.remediation_system.check_docker_availability():
            return {
                "status": "error",
                "message": "Docker not available",
                "issues": []
            }
        
        # Discover and analyze containers
        containers = self.remediation_system.discover_containers()
        all_issues = []
        
        for container in containers:
            container_name = container['Names']
            logs = self.remediation_system.analyze_container_logs(container_name)
            issues = self.remediation_system.categorize_issues(container_name, logs, container)
            all_issues.extend(issues)
        
        return {
            "status": "success",
            "containers_analyzed": len(containers),
            "issues": all_issues,
            "timestamp": datetime.now().isoformat()
        }
    
    def create_agent_prompt(self, issue: DockerIssue, agent_type: str) -> str:
        """
        Create focused prompt for LLM agent based on issue type
        Critical for V1: Narrow, specific prompts prevent agent confusion
        """
        base_context = f"""
You are a specialized {agent_type} agent.
Analyze this specific Docker container issue and provide remediation strategy.

ISSUE DETAILS:
- Container: {issue.container_name}
- Category: {issue.category.value}
- Severity: {issue.severity.value}
- Description: {issue.description}
- Root Cause: {issue.root_cause}

LOG EXCERPT:
{issue.log_excerpt[:500]}

TASK: Provide specific remediation steps for this issue.
"""
        
        if agent_type == "database_specialist":
            return base_context + """
Focus on:
1. Database connectivity diagnostics
2. Connection string validation
3. SSL/TLS configuration checks
4. Specific docker/SQL commands to fix the issue
"""
        elif agent_type == "security_specialist":
            return base_context + """
Focus on:
1. Authentication flow analysis
2. Permission and access control checks
3. Certificate validation
4. Specific security configuration fixes
"""
        elif agent_type == "critical_response_specialist":
            return base_context + """
This is a CRITICAL issue. Focus on:
1. Immediate stabilization steps
2. Quick workarounds if needed
3. Root cause identification
4. Permanent fix implementation
"""
        else:
            return base_context + """
Provide:
1. Diagnostic commands to run
2. Configuration changes needed
3. Service restart sequence
4. Validation steps
"""
    
    def deploy_agent_tool_mode(self, task: AgentTask) -> Dict[str, Any]:
        """
        TOOL MODE: Deploy agent as information provider
        Agent analyzes and returns recommendations to orchestrator
        """
        logger.info(f"Deploying {task.agent_type} in TOOL mode for task {task.task_id}")
        
        # In real implementation, this would use Claude's Task tool
        # For V1, we simulate with structured analysis
        analysis_result = {
            "task_id": task.task_id,
            "agent_type": task.agent_type,
            "container": task.issue.container_name,
            "analysis": {
                "root_cause": task.issue.root_cause,
                "severity_assessment": task.issue.severity.value,
                "recommended_actions": []
            },
            "commands": []
        }
        
        # Generate remediation commands based on issue type
        if task.issue.category == IssueCategory.DATABASE_CONNECTIVITY:
            analysis_result["commands"] = [
                "docker restart netra-postgres",
                "docker exec netra-postgres pg_isready",
                "docker logs --tail 50 netra-postgres"
            ]
            analysis_result["analysis"]["recommended_actions"] = [
                "Restart database container",
                "Verify connection parameters",
                "Check SSL certificate validity"
            ]
        elif task.issue.category == IssueCategory.STARTUP_FAILURE:
            analysis_result["commands"] = [
                f"docker-compose restart {task.issue.container_name}",
                f"docker logs --tail 100 {task.issue.container_name}",
                f"docker inspect {task.issue.container_name}"
            ]
            analysis_result["analysis"]["recommended_actions"] = [
                "Restart failed container",
                "Check dependency services",
                "Verify environment variables"
            ]
        
        # Save analysis to file for audit
        task_file = Path("SPEC/learnings") / f"agent_task_{task.task_id}_{task.agent_type}.json"
        task_file.parent.mkdir(exist_ok=True)
        with open(task_file, 'w') as f:
            json.dump(analysis_result, f, indent=2, default=str)
        
        logger.info(f"Agent analysis saved to {task_file}")
        return analysis_result
    
    def deploy_agent_orchestrator_mode(self, task: AgentTask) -> subprocess.Popen:
        """
        ORCHESTRATOR MODE: Spawn autonomous Claude instance
        Critical V1: Creates new terminal with focused Claude agent
        """
        logger.info(f"Spawning autonomous Claude for task {task.task_id}")
        
        # Save prompt to file
        prompt_file = Path("SPEC/learnings") / f"agent_prompt_{task.task_id}.txt"
        prompt_file.parent.mkdir(exist_ok=True)
        prompt_file.write_text(task.prompt)
        
        # Detect platform and spawn appropriate terminal
        if sys.platform == "win32":
            # Windows: Use cmd with start
            cmd = [
                'cmd', '/c', 'start',
                f'Claude Agent - {task.agent_type}',
                'cmd', '/k',
                'claude', '--dangerously-skip-permissions',
                '--prompt-file', str(prompt_file)
            ]
        elif sys.platform == "darwin":
            # macOS: Use Terminal.app
            cmd = [
                'open', '-a', 'Terminal', '--args',
                'claude', '--dangerously-skip-permissions',
                '--prompt-file', str(prompt_file)
            ]
        else:
            # Linux: Try gnome-terminal
            cmd = [
                'gnome-terminal', '--',
                'claude', '--dangerously-skip-permissions',
                '--prompt-file', str(prompt_file)
            ]
        
        try:
            process = subprocess.Popen(cmd)
            logger.info(f"Spawned Claude agent with PID {process.pid}")
            return process
        except Exception as e:
            logger.error(f"Failed to spawn Claude agent: {e}")
            # Fallback: Log the command that would be run
            logger.info(f"Would execute: {' '.join(cmd)}")
            return None
    
    def execute_remediation(self, commands: List[str]) -> Dict[str, Any]:
        """
        CLASSICAL COMPONENT: Execute remediation commands
        Direct system interaction, no decision making
        """
        results = []
        for cmd in commands:
            logger.info(f"Executing: {cmd}")
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                results.append({
                    "command": cmd,
                    "success": result.returncode == 0,
                    "output": result.stdout[:500] if result.stdout else "",
                    "error": result.stderr[:500] if result.stderr else ""
                })
            except subprocess.TimeoutExpired:
                results.append({
                    "command": cmd,
                    "success": False,
                    "error": "Command timeout"
                })
            except Exception as e:
                results.append({
                    "command": cmd,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "executed": len(results),
            "successful": sum(1 for r in results if r["success"]),
            "results": results
        }
    
    def orchestrate_remediation(self, max_iterations: int = 3) -> Dict[str, Any]:
        """
        Main orchestration loop - coordinates classical and LLM components
        V1 Critical: Simple, focused orchestration for reliability
        """
        logger.info(f"Starting orchestration in {self.mode.value} mode")
        
        orchestration_results = {
            "mode": self.mode.value,
            "iterations": [],
            "total_issues": 0,
            "issues_resolved": 0,
            "start_time": datetime.now().isoformat()
        }
        
        spawned_processes = []
        
        for iteration in range(max_iterations):
            logger.info(f"\n=== ITERATION {iteration + 1}/{max_iterations} ===")
            
            # CLASSICAL: Introspection
            introspection = self.run_introspection()
            if introspection["status"] != "success":
                logger.error(f"Introspection failed: {introspection.get('message')}")
                break
            
            issues = introspection["issues"]
            if not issues:
                logger.info("No issues detected - system healthy")
                break
            
            iteration_result = {
                "iteration": iteration + 1,
                "issues_found": len(issues),
                "agents_deployed": [],
                "remediations_applied": 0
            }
            
            # Process critical issues first
            critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
            high_issues = [i for i in issues if i.severity == IssueSeverity.HIGH]
            priority_issues = critical_issues + high_issues
            
            for issue in priority_issues[:5]:  # Limit to 5 issues per iteration for V1
                # Determine agent type
                agent_type = self.agent_types.get(
                    issue.category, 
                    "general_specialist"
                )
                
                # Create agent task
                self.task_counter += 1
                task = AgentTask(
                    agent_type=agent_type,
                    issue=issue,
                    prompt=self.create_agent_prompt(issue, agent_type),
                    mode=self.mode,
                    task_id=f"task_{self.task_counter:04d}",
                    created_at=datetime.now()
                )
                self.agent_tasks.append(task)
                
                if self.mode == OperationalMode.TOOL_MODE:
                    # LLM analyzes, returns recommendations
                    analysis = self.deploy_agent_tool_mode(task)
                    
                    # CLASSICAL: Execute recommended commands
                    if analysis.get("commands"):
                        execution_result = self.execute_remediation(analysis["commands"])
                        iteration_result["remediations_applied"] += execution_result["successful"]
                    
                    iteration_result["agents_deployed"].append({
                        "type": agent_type,
                        "container": issue.container_name,
                        "commands_executed": len(analysis.get("commands", []))
                    })
                    
                elif self.mode == OperationalMode.ORCHESTRATOR_MODE:
                    # Spawn autonomous Claude
                    process = self.deploy_agent_orchestrator_mode(task)
                    if process:
                        spawned_processes.append(process)
                    
                    iteration_result["agents_deployed"].append({
                        "type": agent_type,
                        "container": issue.container_name,
                        "pid": process.pid if process else None
                    })
            
            orchestration_results["iterations"].append(iteration_result)
            orchestration_results["total_issues"] += len(issues)
            
            # Brief pause between iterations
            if iteration < max_iterations - 1:
                time.sleep(5)
        
        # Wait for spawned processes in orchestrator mode
        if self.mode == OperationalMode.ORCHESTRATOR_MODE and spawned_processes:
            logger.info(f"Waiting for {len(spawned_processes)} spawned agents to complete...")
            for process in spawned_processes:
                try:
                    process.wait(timeout=60)  # Wait up to 60 seconds per agent
                except subprocess.TimeoutExpired:
                    logger.warning(f"Agent PID {process.pid} did not complete in time")
        
        orchestration_results["end_time"] = datetime.now().isoformat()
        orchestration_results["total_agents_deployed"] = len(self.agent_tasks)
        
        # Save orchestration report
        self.save_orchestration_report(orchestration_results)
        
        return orchestration_results
    
    def save_orchestration_report(self, results: Dict[str, Any]) -> None:
        """
        CLASSICAL COMPONENT: Save structured report
        Template-based report generation, no analysis
        """
        report_file = Path(f"orchestration_report_{int(time.time())}.json")
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Orchestration report saved to {report_file}")
        
        # Also create markdown summary
        md_file = report_file.with_suffix('.md')
        with open(md_file, 'w') as f:
            f.write("# Intelligent Remediation Orchestration Report\n\n")
            f.write(f"**Mode:** {results['mode']}\n")
            f.write(f"**Start Time:** {results['start_time']}\n")
            f.write(f"**End Time:** {results.get('end_time', 'In Progress')}\n")
            f.write(f"**Total Issues:** {results['total_issues']}\n")
            f.write(f"**Agents Deployed:** {results['total_agents_deployed']}\n\n")
            
            f.write("## Iterations\n\n")
            for iteration in results['iterations']:
                f.write(f"### Iteration {iteration['iteration']}\n")
                f.write(f"- Issues Found: {iteration['issues_found']}\n")
                f.write(f"- Agents Deployed: {len(iteration['agents_deployed'])}\n")
                if self.mode == OperationalMode.TOOL_MODE:
                    f.write(f"- Remediations Applied: {iteration['remediations_applied']}\n")
                f.write("\n")
        
        logger.info(f"Markdown report saved to {md_file}")


def main():
    """Main entry point for the orchestrator"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Intelligent Remediation Orchestrator - Multi-Agent Coordination"
    )
    parser.add_argument(
        "--mode",
        choices=["tool", "orchestrator"],
        default="tool",
        help="Operational mode: 'tool' for analysis mode, 'orchestrator' for autonomous agents"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        help="Maximum remediation iterations (default: 3 for V1)"
    )
    
    args = parser.parse_args()
    
    try:
        mode = OperationalMode.TOOL_MODE if args.mode == "tool" else OperationalMode.ORCHESTRATOR_MODE
        
        logger.info("=" * 80)
        logger.info("INTELLIGENT REMEDIATION ORCHESTRATOR V1")
        logger.info("=" * 80)
        logger.info(f"Mode: {mode.value}")
        logger.info(f"Max Iterations: {args.max_iterations}")
        logger.info("=" * 80)
        
        if mode == OperationalMode.ORCHESTRATOR_MODE:
            logger.warning("ORCHESTRATOR MODE: Will spawn autonomous Claude instances")
            logger.warning("Ensure 'claude' CLI is installed and configured")
            response = input("Continue? (y/n): ")
            if response.lower() != 'y':
                logger.info("Aborted by user")
                return 0
        
        orchestrator = IntelligentRemediationOrchestrator(mode=mode)
        results = orchestrator.orchestrate_remediation(max_iterations=args.max_iterations)
        
        logger.info("\n" + "=" * 80)
        logger.info("ORCHESTRATION COMPLETE")
        logger.info(f"Total Issues Processed: {results['total_issues']}")
        logger.info(f"Total Agents Deployed: {results['total_agents_deployed']}")
        logger.info("=" * 80)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nOrchestration interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Orchestration error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())