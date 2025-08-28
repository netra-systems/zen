#!/usr/bin/env python3
"""
Claude Log Analyzer - Simplified V1 Implementation

Primary purpose: Get Docker logs to Claude for analysis and spawn specialized agents

Two modes:
1. Analysis Mode: Pass logs to Claude for analysis via function calls
2. Spawn Mode: Create new Claude instances to handle specific issues
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

def get_docker_logs(container_name: str = None, tail: int = 500) -> Dict[str, str]:
    """Get Docker logs from containers"""
    logs = {}
    
    try:
        # Get list of all containers if none specified
        if container_name:
            containers = [container_name]
        else:
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            containers = result.stdout.strip().split('\n') if result.returncode == 0 else []
        
        # Collect logs from each container
        for container in containers:
            if not container:
                continue
                
            try:
                result = subprocess.run(
                    ["docker", "logs", "--tail", str(tail), container],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Combine stdout and stderr
                log_content = ""
                if result.stdout:
                    log_content += f"=== STDOUT ===\n{result.stdout}\n"
                if result.stderr:
                    log_content += f"=== STDERR ===\n{result.stderr}\n"
                
                logs[container] = log_content if log_content else "No logs available"
                
            except Exception as e:
                logs[container] = f"Error getting logs: {e}"
        
    except Exception as e:
        print(f"Error accessing Docker: {e}")
        return {"error": str(e)}
    
    return logs


def prepare_claude_prompt(logs: Dict[str, str], issue_type: str = "general") -> str:
    """Prepare a focused prompt for Claude with logs"""
    
    prompt = f"""You are analyzing Docker container logs to identify and fix issues.

CURRENT TIMESTAMP: {datetime.now().isoformat()}

CONTAINER LOGS:
"""
    
    for container, log_content in logs.items():
        prompt += f"\n=== CONTAINER: {container} ===\n"
        prompt += log_content[:2000]  # Limit per container to avoid token overflow
        prompt += "\n"
    
    prompt += """
TASK: Analyze these logs and:
1. Identify any errors, failures, or issues
2. Determine root causes
3. Provide specific Docker commands to fix each issue
4. Prioritize critical issues first

Focus on actionable remediation steps using docker and docker-compose commands.
"""
    
    if issue_type == "database":
        prompt += "\nSPECIAL FOCUS: Database connectivity and PostgreSQL/ClickHouse issues"
    elif issue_type == "auth":
        prompt += "\nSPECIAL FOCUS: Authentication, permissions, and security issues"
    elif issue_type == "network":
        prompt += "\nSPECIAL FOCUS: Network connectivity and service discovery"
    elif issue_type == "startup":
        prompt += "\nSPECIAL FOCUS: Container startup failures and health checks"
    
    return prompt


def spawn_claude_agent(prompt: str, agent_name: str = "remediation_agent") -> Optional[subprocess.Popen]:
    """Spawn a new Claude instance with the given prompt"""
    
    # Save prompt to file
    prompt_dir = Path("claude_prompts")
    prompt_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompt_file = prompt_dir / f"{agent_name}_{timestamp}.txt"
    prompt_file.write_text(prompt)
    
    print(f"Saved prompt to: {prompt_file}")
    
    # Platform-specific terminal spawning
    if sys.platform == "win32":
        # Windows
        cmd = [
            'cmd', '/c', 'start',
            f'Claude - {agent_name}',
            'cmd', '/k',
            f'claude --dangerously-skip-permissions < "{prompt_file}"'
        ]
        shell = True
    elif sys.platform == "darwin":
        # macOS
        cmd = [
            'osascript', '-e',
            f'tell app "Terminal" to do script "claude --dangerously-skip-permissions < {prompt_file}"'
        ]
        shell = False
    else:
        # Linux
        cmd = [
            'x-terminal-emulator', '-e',
            f'bash -c "claude --dangerously-skip-permissions < {prompt_file}; read -p \'Press enter to close\'"'
        ]
        shell = False
    
    try:
        process = subprocess.Popen(cmd, shell=shell)
        print(f"Spawned Claude agent: PID {process.pid}")
        return process
    except Exception as e:
        print(f"Failed to spawn Claude agent: {e}")
        print(f"Manual command: claude --dangerously-skip-permissions < {prompt_file}")
        return None


def analyze_with_claude(logs: Dict[str, str]) -> Dict[str, any]:
    """
    Analysis mode: Format logs for Claude to analyze
    This would be called by Claude using function tools
    """
    
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "containers_analyzed": len(logs),
        "issues_detected": [],
        "recommended_commands": []
    }
    
    # Pattern detection (classical component)
    for container, log_content in logs.items():
        log_lower = log_content.lower()
        
        # Critical patterns
        if "connection refused" in log_lower:
            analysis["issues_detected"].append({
                "container": container,
                "type": "database_connectivity",
                "severity": "critical",
                "pattern": "connection refused"
            })
            analysis["recommended_commands"].append(f"docker restart {container}")
            
        if "permission denied" in log_lower:
            analysis["issues_detected"].append({
                "container": container,
                "type": "auth_permission",
                "severity": "high",
                "pattern": "permission denied"
            })
            
        if "cannot allocate memory" in log_lower:
            analysis["issues_detected"].append({
                "container": container,
                "type": "resource_exhaustion",
                "severity": "critical",
                "pattern": "out of memory"
            })
            analysis["recommended_commands"].append("docker system prune -f")
            
        if "unhealthy" in log_lower or "exited" in log_lower:
            analysis["issues_detected"].append({
                "container": container,
                "type": "health_check_failure",
                "severity": "high",
                "pattern": "container unhealthy or exited"
            })
            analysis["recommended_commands"].append(f"docker-compose restart {container}")
    
    # Add the full logs for Claude to analyze
    analysis["logs"] = logs
    
    return analysis


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Claude Log Analyzer - Get logs to Claude")
    parser.add_argument("--mode", choices=["analyze", "spawn"], default="analyze",
                       help="Mode: 'analyze' returns data, 'spawn' creates Claude instances")
    parser.add_argument("--container", help="Specific container to analyze")
    parser.add_argument("--tail", type=int, default=500, help="Number of log lines to fetch")
    parser.add_argument("--issue-type", choices=["general", "database", "auth", "network", "startup"],
                       default="general", help="Type of issue to focus on")
    parser.add_argument("--spawn-multiple", action="store_true",
                       help="Spawn separate Claude instance for each container with issues")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("CLAUDE LOG ANALYZER V1")
    print("=" * 80)
    print(f"Mode: {args.mode}")
    print(f"Container: {args.container or 'All containers'}")
    print(f"Log tail: {args.tail} lines")
    print("=" * 80)
    
    # Get Docker logs
    print("\nFetching Docker logs...")
    logs = get_docker_logs(args.container, args.tail)
    
    if "error" in logs:
        print(f"Error: {logs['error']}")
        return 1
    
    print(f"Retrieved logs from {len(logs)} container(s)")
    
    if args.mode == "analyze":
        # Analysis mode: Return structured data for Claude
        analysis = analyze_with_claude(logs)
        
        # Save analysis
        output_file = f"log_analysis_{int(time.time())}.json"
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        print(f"\nAnalysis saved to: {output_file}")
        print(f"Issues detected: {len(analysis['issues_detected'])}")
        
        # Print summary
        if analysis['issues_detected']:
            print("\nISSUES FOUND:")
            for issue in analysis['issues_detected']:
                print(f"  - {issue['container']}: {issue['type']} ({issue['severity']})")
        
        if analysis['recommended_commands']:
            print("\nRECOMMENDED COMMANDS:")
            for cmd in analysis['recommended_commands']:
                print(f"  {cmd}")
        
        # Return the analysis for Claude to use
        return analysis
        
    elif args.mode == "spawn":
        # Spawn mode: Create Claude instances
        if args.spawn_multiple:
            # Spawn one agent per container with issues
            spawned = []
            for container, log_content in logs.items():
                if any(pattern in log_content.lower() 
                       for pattern in ["error", "failed", "refused", "denied", "unhealthy"]):
                    
                    prompt = prepare_claude_prompt({container: log_content}, args.issue_type)
                    process = spawn_claude_agent(prompt, f"agent_{container}")
                    if process:
                        spawned.append(process)
                    time.sleep(2)  # Brief pause between spawns
            
            print(f"\nSpawned {len(spawned)} Claude agents")
            
        else:
            # Spawn single agent with all logs
            prompt = prepare_claude_prompt(logs, args.issue_type)
            process = spawn_claude_agent(prompt, "main_agent")
            
            if process:
                print("\nClaude agent spawned successfully")
                print("The agent will analyze logs and execute remediation")
            else:
                print("\nFailed to spawn Claude agent")
                print("You can manually run the command shown above")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())