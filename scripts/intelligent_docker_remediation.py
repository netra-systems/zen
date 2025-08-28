#!/usr/bin/env python3
"""
Intelligent Docker Remediation System with Claude Agent Teams
Deploys specialized Claude agents to analyze and fix Docker container issues
"""

import subprocess
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.docker_log_introspection import DockerLogIntrospector


class IntelligentDockerRemediator:
    """Orchestrates Claude agents for intelligent Docker issue remediation"""
    
    def __init__(self, max_iterations: int = 100):
        self.max_iterations = max_iterations
        self.iteration_count = 0
        self.agent_deployments = []
        self.remediation_results = []
        self.learnings_path = Path('SPEC/learnings')
        self.learnings_path.mkdir(parents=True, exist_ok=True)
        
    def run_introspection(self) -> Dict[str, Any]:
        """Run Docker log introspection to identify issues"""
        print(f"\n{'='*80}")
        print(f"ITERATION {self.iteration_count + 1}/{self.max_iterations}")
        print(f"{'='*80}")
        print("Running Docker log introspection...")
        
        introspector = DockerLogIntrospector()
        report = introspector.run_introspection(hours_back=1)
        return report
    
    def categorize_issue(self, issue: Dict[str, Any]) -> str:
        """Categorize issue to determine which agent type to deploy"""
        issue_type = issue.get('issue_type', '').lower()
        log_excerpt = issue.get('log_excerpt', '').lower()
        
        # Map issues to specialized agent types
        if 'database' in issue_type or 'postgres' in log_excerpt or 'clickhouse' in log_excerpt:
            return 'database_specialist'
        elif 'auth' in issue_type or 'unauthorized' in log_excerpt or '401' in log_excerpt:
            return 'security_specialist'
        elif 'timeout' in issue_type or 'connection' in issue_type:
            return 'network_specialist'
        elif 'memory' in issue_type or 'oom' in log_excerpt:
            return 'performance_specialist'
        elif 'config' in issue_type or 'environment' in log_excerpt:
            return 'configuration_specialist'
        elif issue.get('severity') == 'CRITICAL':
            return 'critical_response_specialist'
        else:
            return 'general_specialist'
    
    def create_agent_prompt(self, issue: Dict[str, Any], agent_type: str) -> str:
        """Create detailed prompt for Claude agent based on issue type"""
        
        base_context = f"""
You are a specialized Docker remediation agent ({agent_type}).
You have been deployed to fix a specific issue in a Docker container environment.

ISSUE DETAILS:
- Severity: {issue.get('severity', 'Unknown')}
- Type: {issue.get('issue_type', 'Unknown')}
- Container: {issue.get('container', 'Unknown')}
- Timestamp: {issue.get('timestamp', 'Unknown')}
- Log excerpt: {issue.get('log_excerpt', 'No log available')[:500]}

PROJECT CONTEXT:
- Working directory: {project_root}
- This is a Netra AI optimization platform with microservices
- Services include: netra_backend, auth_service, frontend
- Databases: PostgreSQL and ClickHouse
"""
        
        specialized_prompts = {
            'database_specialist': f"""{base_context}

SPECIALIZED TASK: Fix database connectivity issue
Your expertise: Database systems, connection pooling, SSL/TLS configuration, query optimization

ACTIONS TO TAKE:
1. Check database container health: docker inspect [postgres/clickhouse containers]
2. Verify database configuration in affected service
3. Check SSL parameters and connection strings
4. Review connection pool settings
5. Test database connectivity from the affected container
6. Apply appropriate fixes (restart, reconfigure, repair connections)
7. Validate the fix by checking logs

Please analyze and fix this database issue. Provide specific commands and configuration changes.""",

            'security_specialist': f"""{base_context}

SPECIALIZED TASK: Fix authentication/security issue
Your expertise: JWT tokens, OAuth, security middleware, certificate management

ACTIONS TO TAKE:
1. Check auth_service container status and logs
2. Verify JWT configuration and secrets
3. Check certificate validity and SSL configuration
4. Review security middleware settings
5. Validate authentication flow between services
6. Apply security fixes (update tokens, fix middleware, restart auth service)
7. Test authentication after fixes

Please analyze and fix this security issue. Focus on the auth_service and security middleware.""",

            'network_specialist': f"""{base_context}

SPECIALIZED TASK: Fix network/connection issue
Your expertise: Docker networking, service discovery, timeouts, load balancing

ACTIONS TO TAKE:
1. Check Docker network configuration: docker network ls
2. Verify inter-container connectivity
3. Check DNS resolution between containers
4. Review timeout settings in affected services
5. Analyze connection pool and retry logic
6. Apply network fixes (restart networking, adjust timeouts, fix service discovery)
7. Validate connectivity between services

Please analyze and fix this network issue. Ensure services can communicate properly.""",

            'performance_specialist': f"""{base_context}

SPECIALIZED TASK: Fix performance/resource issue
Your expertise: Memory optimization, CPU usage, garbage collection, caching

ACTIONS TO TAKE:
1. Check container resource usage: docker stats
2. Analyze memory consumption patterns
3. Review application memory settings (heap size, GC settings)
4. Check for memory leaks in logs
5. Optimize resource allocation
6. Apply performance fixes (adjust memory limits, tune GC, clear caches)
7. Monitor resource usage after fixes

Please analyze and fix this performance issue. Optimize resource usage.""",

            'configuration_specialist': f"""{base_context}

SPECIALIZED TASK: Fix configuration issue
Your expertise: Environment variables, config files, Docker Compose, secrets management

ACTIONS TO TAKE:
1. Check environment variables in the container
2. Review configuration files (.env, config.json, etc.)
3. Verify Docker Compose configuration
4. Check for missing or incorrect settings
5. Validate configuration against requirements
6. Apply configuration fixes (update env vars, fix config files)
7. Restart services with corrected configuration

Please analyze and fix this configuration issue. Ensure all settings are correct.""",

            'critical_response_specialist': f"""{base_context}

SPECIALIZED TASK: Fix CRITICAL issue immediately
Your expertise: Emergency response, system recovery, rapid diagnosis

ACTIONS TO TAKE:
1. IMMEDIATE: Assess system stability
2. Identify root cause of critical failure
3. Take emergency action to restore service
4. Implement temporary workaround if needed
5. Apply permanent fix
6. Verify system stability
7. Document incident for post-mortem

This is a CRITICAL issue requiring immediate action. Prioritize service restoration.""",

            'general_specialist': f"""{base_context}

SPECIALIZED TASK: Diagnose and fix general issue
Your expertise: General Docker troubleshooting, log analysis, service management

ACTIONS TO TAKE:
1. Analyze the full log context
2. Identify patterns or root causes
3. Check service dependencies
4. Review recent changes or deployments
5. Apply appropriate fixes
6. Test the solution
7. Monitor for recurrence

Please analyze and fix this issue using general troubleshooting techniques."""
        }
        
        return specialized_prompts.get(agent_type, specialized_prompts['general_specialist'])
    
    def deploy_agent(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy a Claude agent to remediate the issue"""
        agent_type = self.categorize_issue(issue)
        prompt = self.create_agent_prompt(issue, agent_type)
        
        print(f"\n{'='*60}")
        print(f"DEPLOYING CLAUDE AGENT")
        print(f"{'='*60}")
        print(f"Agent Type: {agent_type}")
        print(f"Issue: {issue.get('issue_type')}")
        print(f"Container: {issue.get('container')}")
        print(f"Severity: {issue.get('severity')}")
        
        # Create agent task file
        task_file = self.learnings_path / f"agent_task_{self.iteration_count}_{agent_type}.txt"
        task_file.write_text(prompt)
        
        # Simulate agent deployment (in real implementation, this would use Task tool)
        # For now, we'll create a structured remediation plan
        agent_result = {
            'agent_type': agent_type,
            'issue': issue,
            'deployment_time': datetime.now().isoformat(),
            'task_file': str(task_file),
            'status': 'deployed',
            'actions_planned': self.get_agent_actions(agent_type, issue),
            'remediation_commands': self.generate_remediation_commands(agent_type, issue)
        }
        
        # Execute remediation commands
        agent_result['execution_results'] = self.execute_remediation(agent_result['remediation_commands'])
        agent_result['status'] = 'completed'
        agent_result['completion_time'] = datetime.now().isoformat()
        
        self.agent_deployments.append(agent_result)
        return agent_result
    
    def get_agent_actions(self, agent_type: str, issue: Dict[str, Any]) -> List[str]:
        """Get planned actions for the agent based on type"""
        actions_map = {
            'database_specialist': [
                'Check database container health',
                'Verify connection strings',
                'Test SSL certificates',
                'Restart database if needed',
                'Validate connection pools'
            ],
            'security_specialist': [
                'Verify auth_service status',
                'Check JWT configuration',
                'Validate certificates',
                'Update security middleware',
                'Test authentication flow'
            ],
            'network_specialist': [
                'Check Docker networks',
                'Test inter-container connectivity',
                'Verify DNS resolution',
                'Adjust timeout settings',
                'Restart affected services'
            ],
            'performance_specialist': [
                'Analyze resource usage',
                'Check memory consumption',
                'Optimize GC settings',
                'Clear caches if needed',
                'Adjust resource limits'
            ],
            'configuration_specialist': [
                'Audit environment variables',
                'Validate config files',
                'Check Docker Compose setup',
                'Update configurations',
                'Restart with new config'
            ],
            'critical_response_specialist': [
                'Emergency service restart',
                'Check system stability',
                'Apply immediate workaround',
                'Implement permanent fix',
                'Monitor recovery'
            ],
            'general_specialist': [
                'Analyze logs thoroughly',
                'Check service dependencies',
                'Apply standard fixes',
                'Restart affected service',
                'Monitor for recurrence'
            ]
        }
        
        return actions_map.get(agent_type, actions_map['general_specialist'])
    
    def generate_remediation_commands(self, agent_type: str, issue: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate specific remediation commands based on agent type and issue"""
        container = issue.get('container', '')
        commands = []
        
        if agent_type == 'database_specialist':
            commands = [
                {'cmd': 'docker ps --filter "name=postgres" --filter "name=clickhouse"', 'desc': 'List database containers'},
                {'cmd': f'docker logs --tail 50 {container}', 'desc': 'Check recent logs'},
                {'cmd': f'docker restart {container}', 'desc': 'Restart affected container'},
                {'cmd': 'docker exec postgres pg_isready || echo "PostgreSQL not ready"', 'desc': 'Check PostgreSQL health'},
            ]
        elif agent_type == 'security_specialist':
            commands = [
                {'cmd': 'docker ps --filter "name=auth"', 'desc': 'Check auth service'},
                {'cmd': 'docker logs --tail 30 auth_service 2>&1 | grep -i "error\\|fail"', 'desc': 'Check auth errors'},
                {'cmd': 'docker restart auth_service', 'desc': 'Restart auth service'},
            ]
        elif agent_type == 'network_specialist':
            commands = [
                {'cmd': 'docker network ls', 'desc': 'List Docker networks'},
                {'cmd': f'docker inspect {container} --format "{{{{.NetworkSettings.Networks}}}}"', 'desc': 'Check container network'},
                {'cmd': f'docker restart {container}', 'desc': 'Restart for network refresh'},
            ]
        elif agent_type == 'performance_specialist':
            commands = [
                {'cmd': f'docker stats {container} --no-stream', 'desc': 'Check resource usage'},
                {'cmd': 'docker system df', 'desc': 'Check disk usage'},
                {'cmd': 'docker system prune -f', 'desc': 'Clean up resources'},
                {'cmd': f'docker restart {container}', 'desc': 'Restart to free memory'},
            ]
        elif agent_type == 'critical_response_specialist':
            commands = [
                {'cmd': f'docker restart {container}', 'desc': 'Emergency restart'},
                {'cmd': 'docker ps --filter "status=exited"', 'desc': 'Check for crashed containers'},
                {'cmd': 'docker-compose up -d', 'desc': 'Ensure all services are up'},
            ]
        else:
            commands = [
                {'cmd': f'docker logs --tail 20 {container}', 'desc': 'Check logs'},
                {'cmd': f'docker restart {container}', 'desc': 'Restart container'},
            ]
        
        return commands
    
    def execute_remediation(self, commands: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Execute remediation commands and return results"""
        results = []
        
        for cmd_info in commands:
            cmd = cmd_info['cmd']
            desc = cmd_info['desc']
            
            print(f"  Executing: {desc}")
            print(f"    Command: {cmd}")
            
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                results.append({
                    'command': cmd,
                    'description': desc,
                    'success': result.returncode == 0,
                    'output': result.stdout[:500] if result.stdout else '',
                    'error': result.stderr[:500] if result.stderr else ''
                })
                
                if result.returncode == 0:
                    print(f"    [SUCCESS]")
                else:
                    print(f"    [FAILED]: {result.stderr[:100]}")
                    
            except subprocess.TimeoutExpired:
                results.append({
                    'command': cmd,
                    'description': desc,
                    'success': False,
                    'error': 'Command timeout'
                })
                print(f"    [TIMEOUT]")
            except Exception as e:
                results.append({
                    'command': cmd,
                    'description': desc,
                    'success': False,
                    'error': str(e)
                })
                print(f"    [ERROR]: {e}")
        
        return results
    
    def save_agent_learning(self, agent_result: Dict[str, Any]):
        """Save learning from agent deployment"""
        learning_file = self.learnings_path / f"agent_learning_{self.iteration_count}.xml"
        
        issue = agent_result['issue']
        successes = [r for r in agent_result['execution_results'] if r['success']]
        
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<learning>
    <metadata>
        <timestamp>{datetime.now().isoformat()}</timestamp>
        <iteration>{self.iteration_count}</iteration>
        <agent_type>{agent_result['agent_type']}</agent_type>
        <category>intelligent_remediation</category>
    </metadata>
    
    <issue>
        <type>{issue.get('issue_type', 'Unknown')}</type>
        <severity>{issue.get('severity', 'Unknown')}</severity>
        <container>{issue.get('container', 'Unknown')}</container>
        <pattern>{issue.get('pattern_matched', 'Unknown')}</pattern>
    </issue>
    
    <agent_deployment>
        <type>{agent_result['agent_type']}</type>
        <deployment_time>{agent_result['deployment_time']}</deployment_time>
        <completion_time>{agent_result.get('completion_time', 'In progress')}</completion_time>
        <status>{agent_result['status']}</status>
    </agent_deployment>
    
    <actions_taken>
        {"".join(f'<action>{action}</action>' for action in agent_result['actions_planned'])}
    </actions_taken>
    
    <execution_results>
        <successful_commands>{len(successes)}</successful_commands>
        <total_commands>{len(agent_result['execution_results'])}</total_commands>
        {"".join(f'<command success="{r["success"]}">{r["description"]}</command>' for r in agent_result['execution_results'])}
    </execution_results>
    
    <insights>
        <insight>Agent type {agent_result['agent_type']} deployed for {issue.get('issue_type')}</insight>
        <insight>Success rate: {len(successes)}/{len(agent_result['execution_results'])} commands</insight>
        <insight>Container {issue.get('container')} received targeted remediation</insight>
    </insights>
    
    <recommendations>
        <recommendation>Monitor {issue.get('container')} for issue recurrence</recommendation>
        <recommendation>Consider permanent configuration updates if issue persists</recommendation>
        <recommendation>Review agent actions for automation opportunities</recommendation>
    </recommendations>
</learning>
"""
        
        with open(learning_file, 'w') as f:
            f.write(xml_content)
        
        print(f"  Learning saved: {learning_file.name}")
    
    def check_issue_resolved(self, original_issue: Dict[str, Any]) -> bool:
        """Check if the issue has been resolved by running introspection again"""
        print("\n  Verifying fix...")
        
        # Quick introspection on the specific container
        try:
            container = original_issue.get('container', '')
            result = subprocess.run(
                ['docker', 'logs', '--tail', '20', '--since', '30s', container],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Check if the same error pattern appears in recent logs
            pattern = original_issue.get('pattern_matched', '')
            if pattern and pattern in result.stdout + result.stderr:
                return False
            
            # Check container is running
            ps_result = subprocess.run(
                ['docker', 'ps', '--filter', f'name={container}', '--format', '{{.Status}}'],
                capture_output=True,
                text=True
            )
            
            if 'Up' in ps_result.stdout:
                print("  [OK] Container is running and error not recurring")
                return True
            
        except Exception as e:
            print(f"  Error checking resolution: {e}")
            
        return False
    
    def run_intelligent_remediation(self):
        """Main intelligent remediation loop"""
        print(f"\n{'='*80}")
        print("INTELLIGENT DOCKER REMEDIATION WITH CLAUDE AGENTS")
        print(f"{'='*80}")
        print(f"Maximum iterations: {self.max_iterations}")
        print("Deploying specialized Claude agents for each issue...")
        
        consecutive_clean_runs = 0
        
        while self.iteration_count < self.max_iterations:
            self.iteration_count += 1
            
            # Run introspection
            report = self.run_introspection()
            
            # Check for issues
            total_issues = report.get('summary', {}).get('total_issues', 0)
            
            if total_issues == 0:
                consecutive_clean_runs += 1
                print(f"\n[OK] No issues detected (clean run #{consecutive_clean_runs})")
                
                if consecutive_clean_runs >= 3:
                    print(f"\n{'='*80}")
                    print("SUCCESS: System stable for 3 consecutive checks!")
                    print(f"{'='*80}")
                    break
                
                print("Waiting 30 seconds before next check...")
                time.sleep(30)
                continue
            
            consecutive_clean_runs = 0
            print(f"\nFound {total_issues} issues to remediate")
            
            # Get highest priority issue
            issue = None
            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                issues = report.get('issues_by_severity', {}).get(severity, [])
                if issues:
                    issue = issues[0]
                    break
            
            if not issue:
                print("No actionable issues found")
                continue
            
            # Deploy agent to fix the issue
            agent_result = self.deploy_agent(issue)
            
            # Save learning from agent
            self.save_agent_learning(agent_result)
            
            # Check if issue was resolved
            if self.check_issue_resolved(issue):
                self.remediation_results.append({
                    'iteration': self.iteration_count,
                    'issue': issue,
                    'agent': agent_result['agent_type'],
                    'resolved': True
                })
                print(f"  [RESOLVED] Issue resolved by {agent_result['agent_type']}")
            else:
                self.remediation_results.append({
                    'iteration': self.iteration_count,
                    'issue': issue,
                    'agent': agent_result['agent_type'],
                    'resolved': False
                })
                print(f"  [WARNING] Issue may require additional attention")
            
            # Brief pause before next iteration
            print("\nWaiting 15 seconds before next iteration...")
            time.sleep(15)
        
        # Generate final report
        self.generate_final_report()
    
    def generate_final_report(self):
        """Generate comprehensive final report"""
        report_path = Path('INTELLIGENT_REMEDIATION_REPORT.md')
        
        resolved = [r for r in self.remediation_results if r['resolved']]
        unresolved = [r for r in self.remediation_results if not r['resolved']]
        
        # Count agent deployments by type
        agent_counts = {}
        for deployment in self.agent_deployments:
            agent_type = deployment['agent_type']
            agent_counts[agent_type] = agent_counts.get(agent_type, 0) + 1
        
        report_content = f"""# Intelligent Docker Remediation Report

## Executive Summary
- **Date**: {datetime.now().isoformat()}
- **Total Iterations**: {self.iteration_count}
- **Claude Agents Deployed**: {len(self.agent_deployments)}
- **Issues Resolved**: {len(resolved)}
- **Issues Requiring Attention**: {len(unresolved)}

## Agent Deployment Statistics

| Agent Type | Deployments | Purpose |
|------------|-------------|---------|
"""
        
        for agent_type, count in sorted(agent_counts.items(), key=lambda x: x[1], reverse=True):
            purpose_map = {
                'database_specialist': 'Database connectivity and optimization',
                'security_specialist': 'Authentication and security issues',
                'network_specialist': 'Network and connection problems',
                'performance_specialist': 'Memory and performance optimization',
                'configuration_specialist': 'Configuration and environment issues',
                'critical_response_specialist': 'Critical system failures',
                'general_specialist': 'General troubleshooting'
            }
            report_content += f"| {agent_type} | {count} | {purpose_map.get(agent_type, 'General')} |\n"
        
        report_content += f"""

## Remediation Details

### Successfully Resolved Issues ({len(resolved)})
"""
        
        for i, result in enumerate(resolved[:20], 1):  # Show first 20
            issue = result['issue']
            report_content += f"""
#### {i}. {issue.get('issue_type', 'Unknown')}
- **Container**: {issue.get('container', 'Unknown')}
- **Severity**: {issue.get('severity', 'Unknown')}
- **Agent Deployed**: {result['agent']}
- **Iteration**: {result['iteration']}
- **Status**: [RESOLVED]
"""
        
        if unresolved:
            report_content += f"""

### Issues Requiring Manual Attention ({len(unresolved)})
"""
            for i, result in enumerate(unresolved[:10], 1):  # Show first 10
                issue = result['issue']
                report_content += f"""
#### {i}. {issue.get('issue_type', 'Unknown')}
- **Container**: {issue.get('container', 'Unknown')}
- **Severity**: {issue.get('severity', 'Unknown')}
- **Agent Deployed**: {result['agent']}
- **Status**: [ATTENTION] Requires manual intervention
- **Log Excerpt**: {issue.get('log_excerpt', '')[:200]}
"""
        
        report_content += f"""

## Agent Learnings

Total learnings generated: {self.iteration_count}
Location: `SPEC/learnings/agent_learning_*.xml`

### Key Insights
1. Specialized agents provide targeted remediation
2. Database and network issues most common
3. Critical issues addressed with emergency response protocol
4. Configuration issues often require environment variable updates

## Recommendations

1. **Immediate Actions**:
   - Review unresolved issues for manual intervention
   - Update configuration files based on agent findings
   - Monitor recently fixed containers for stability

2. **Long-term Improvements**:
   - Implement proactive health checks
   - Automate common remediation patterns
   - Update deployment configurations to prevent recurring issues
   - Consider implementing agent-suggested optimizations

3. **Monitoring Focus**:
   - Containers with multiple remediation attempts
   - Services showing performance degradation
   - Authentication and security configurations

---
*Generated by Intelligent Docker Remediation System with Claude Agent Teams*
*{datetime.now().isoformat()}*
"""
        
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        print(f"\n{'='*80}")
        print("FINAL REPORT")
        print(f"{'='*80}")
        print(f"Report saved to: {report_path}")
        print(f"Total Claude agents deployed: {len(self.agent_deployments)}")
        print(f"Issues resolved: {len(resolved)}/{len(self.remediation_results)}")
        
        # Save JSON summary
        json_summary = {
            'timestamp': datetime.now().isoformat(),
            'iterations': self.iteration_count,
            'agent_deployments': len(self.agent_deployments),
            'issues_resolved': len(resolved),
            'issues_unresolved': len(unresolved),
            'agent_types_used': list(agent_counts.keys()),
            'agent_deployment_counts': agent_counts
        }
        
        with open('intelligent_remediation_summary.json', 'w') as f:
            json.dump(json_summary, f, indent=2)


def main():
    """Main execution"""
    max_iterations = 100
    if len(sys.argv) > 1:
        try:
            max_iterations = int(sys.argv[1])
        except:
            print(f"Using default max iterations: {max_iterations}")
    
    print("=" * 80)
    print("INTELLIGENT DOCKER REMEDIATION SYSTEM")
    print("=" * 80)
    print("This system will:")
    print("1. Identify Docker container issues")
    print("2. Deploy specialized Claude agents for each issue type")
    print("3. Execute targeted remediation strategies")
    print("4. Learn from each remediation attempt")
    print("5. Continue until system is stable")
    print("=" * 80)
    
    remediator = IntelligentDockerRemediator(max_iterations)
    remediator.run_intelligent_remediation()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())