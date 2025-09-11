#!/usr/bin/env python3
"""
GitCommitGardener Continuous Monitoring System
============================================

Mission: Monitor repository for changes and automatically commit them following
atomic units principles from SPEC/git_commit_atomic_units.xml

CRITICAL REQUIREMENTS:
- Monitor for at least 8 hours, target 20+ hours
- Check for changes every 2 minutes
- Follow atomic commit principles exactly
- Group by CONCEPT not file count
- Preserve repository history and safety
- Stay on develop-long-lived branch ONLY
"""

import os
import sys
import time
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Set
import logging

# Setup logging for monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - GitCommitGardener - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('git_commit_gardener.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GitCommitGardenerMonitor:
    """Continuous monitoring system for automatic atomic commits"""
    
    def __init__(self, repo_path: str, monitoring_hours: int = 20):
        self.repo_path = Path(repo_path)
        self.monitoring_hours = monitoring_hours
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=monitoring_hours)
        self.check_interval = 120  # 2 minutes in seconds
        self.commits_created = 0
        self.cycles_completed = 0
        self.emergency_stop = False
        
        # Safety protocols
        self.required_branch = "develop-long-lived"
        self.merge_log_dir = Path("merges")
        self.merge_log_dir.mkdir(exist_ok=True)
        
        logger.info(f"GitCommitGardener Monitor initialized")
        logger.info(f"Repository: {self.repo_path}")
        logger.info(f"Monitoring duration: {monitoring_hours} hours")
        logger.info(f"Target end time: {self.end_time}")
        logger.info(f"Check interval: {self.check_interval} seconds")
    
    def run_git_command(self, cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Execute git command with safety checks"""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=capture_output,
                text=True,
                check=False
            )
            return result
        except Exception as e:
            logger.error(f"Git command failed: {' '.join(cmd)} - {e}")
            raise
    
    def check_repository_safety(self) -> bool:
        """Verify repository is in safe state for monitoring"""
        try:
            # Check current branch
            result = self.run_git_command(["git", "branch", "--show-current"])
            current_branch = result.stdout.strip()
            
            if current_branch != self.required_branch:
                logger.error(f"SAFETY VIOLATION: On branch '{current_branch}', required '{self.required_branch}'")
                self.emergency_stop = True
                return False
            
            # Check for merge conflicts
            result = self.run_git_command(["git", "status", "--porcelain"])
            for line in result.stdout.split('\n'):
                if line.startswith('UU ') or line.startswith('AA '):
                    logger.error(f"SAFETY VIOLATION: Merge conflict detected: {line}")
                    self.emergency_stop = True
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Repository safety check failed: {e}")
            self.emergency_stop = True
            return False
    
    def get_repository_changes(self) -> Dict[str, List[str]]:
        """Analyze current repository changes"""
        try:
            # Get git status
            result = self.run_git_command(["git", "status", "--porcelain"])
            status_lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            
            changes = {
                'modified': [],
                'untracked': [],
                'deleted': [],
                'renamed': [],
                'added': []
            }
            
            for line in status_lines:
                if not line:
                    continue
                    
                status = line[:2]
                filepath = line[3:]
                
                if status.startswith('M'):
                    changes['modified'].append(filepath)
                elif status.startswith('??'):
                    changes['untracked'].append(filepath)
                elif status.startswith('D'):
                    changes['deleted'].append(filepath)
                elif status.startswith('R'):
                    changes['renamed'].append(filepath)
                elif status.startswith('A'):
                    changes['added'].append(filepath)
            
            return changes
            
        except Exception as e:
            logger.error(f"Failed to get repository changes: {e}")
            return {}
    
    def analyze_change_concepts(self, changes: Dict[str, List[str]]) -> List[Dict]:
        """Analyze changes and group by conceptual units following atomic principles"""
        try:
            all_files = []
            for change_type, files in changes.items():
                all_files.extend([(f, change_type) for f in files])
            
            if not all_files:
                return []
            
            logger.info(f"Analyzing {len(all_files)} changed files for conceptual grouping")
            
            # Group files by conceptual relationships
            concept_groups = []
            
            # Service/module groupings
            services = {}
            for filepath, change_type in all_files:
                parts = filepath.split('/')
                if len(parts) > 1:
                    service = parts[0]
                    if service not in services:
                        services[service] = []
                    services[service].append((filepath, change_type))
                else:
                    # Root level files
                    if 'root' not in services:
                        services['root'] = []
                    services['root'].append((filepath, change_type))
            
            # Create conceptual groups based on atomic principles
            for service, service_files in services.items():
                # Determine if files represent single or multiple concepts
                concepts = self.identify_concepts_in_service(service, service_files)
                concept_groups.extend(concepts)
            
            logger.info(f"Identified {len(concept_groups)} conceptual groups for atomic commits")
            return concept_groups
            
        except Exception as e:
            logger.error(f"Failed to analyze change concepts: {e}")
            return []
    
    def identify_concepts_in_service(self, service: str, files: List[Tuple[str, str]]) -> List[Dict]:
        """Identify conceptual units within a service following atomic principles"""
        concepts = []
        
        try:
            # Group by file patterns and purposes
            documentation = []
            tests = []
            source_code = []
            config = []
            
            for filepath, change_type in files:
                if any(doc_pattern in filepath.lower() for doc_pattern in ['.md', 'readme', 'docs/', 'spec/']):
                    documentation.append((filepath, change_type))
                elif any(test_pattern in filepath.lower() for test_pattern in ['test_', '_test', 'tests/']):
                    tests.append((filepath, change_type))
                elif any(config_pattern in filepath.lower() for config_pattern in ['config', '.json', '.yaml', '.yml', '.toml']):
                    config.append((filepath, change_type))
                else:
                    source_code.append((filepath, change_type))
            
            # Create atomic concepts following SPEC principles
            
            # Documentation updates (usually single concept)
            if documentation:
                concepts.append({
                    'type': 'docs',
                    'scope': service,
                    'files': documentation,
                    'description': f'Update {service} documentation',
                    'reasoning': 'Documentation updates form coherent information unit'
                })
            
            # Configuration changes (careful grouping)
            if config:
                concepts.append({
                    'type': 'chore',
                    'scope': service,
                    'files': config,
                    'description': f'Update {service} configuration',
                    'reasoning': 'Configuration changes affect service behavior as unit'
                })
            
            # Source code changes (analyze for feature coherence)
            if source_code:
                # For now, group source code changes as single concept per service
                # In production, would analyze imports/dependencies for better grouping
                concepts.append({
                    'type': 'refactor',  # Conservative choice
                    'scope': service,
                    'files': source_code,
                    'description': f'Update {service} implementation',
                    'reasoning': 'Source code changes in service represent coherent update'
                })
            
            # Tests (should accompany implementation when possible)
            if tests and not source_code:
                concepts.append({
                    'type': 'test',
                    'scope': service,
                    'files': tests,
                    'description': f'Update {service} tests',
                    'reasoning': 'Test updates form coherent validation unit'
                })
            elif tests and source_code:
                # Merge tests with last source concept (dependency coupling)
                if concepts and concepts[-1]['type'] in ['refactor', 'feat', 'fix']:
                    concepts[-1]['files'].extend(tests)
                    concepts[-1]['reasoning'] += ' (includes test coupling)'
            
            return concepts
            
        except Exception as e:
            logger.error(f"Failed to identify concepts in service {service}: {e}")
            return [{
                'type': 'chore',
                'scope': service,
                'files': files,
                'description': f'Update {service} files',
                'reasoning': 'Fallback grouping due to analysis error'
            }]
    
    def create_atomic_commit(self, concept: Dict) -> bool:
        """Create atomic commit following SPEC principles"""
        try:
            files_to_stage = [f[0] for f in concept['files']]
            logger.info(f"Creating atomic commit for concept: {concept['description']}")
            logger.info(f"Files involved: {len(files_to_stage)} files")
            
            # Stage files
            stage_cmd = ["git", "add"] + files_to_stage
            result = self.run_git_command(stage_cmd)
            if result.returncode != 0:
                logger.error(f"Failed to stage files: {result.stderr}")
                return False
            
            # Create commit message following SPEC template
            commit_message = self.generate_commit_message(concept)
            
            # Create commit
            commit_cmd = ["git", "commit", "-m", commit_message]
            result = self.run_git_command(commit_cmd)
            if result.returncode != 0:
                logger.error(f"Failed to create commit: {result.stderr}")
                return False
            
            logger.info(f"✅ Atomic commit created successfully")
            self.commits_created += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to create atomic commit: {e}")
            return False
    
    def generate_commit_message(self, concept: Dict) -> str:
        """Generate commit message following SPEC standards"""
        commit_type = concept['type']
        scope = concept['scope']
        description = concept['description']
        reasoning = concept.get('reasoning', '')
        files = concept['files']
        
        # Header line (50 chars max, imperative mood)
        header = f"{commit_type}({scope}): {description}"
        if len(header) > 50:
            # Truncate description to fit
            max_desc_len = 50 - len(f"{commit_type}({scope}): ")
            description_truncated = description[:max_desc_len-3] + "..."
            header = f"{commit_type}({scope}): {description_truncated}"
        
        # Body with business value and technical details
        body_parts = []
        body_parts.append(f"- Automated commit by GitCommitGardener monitoring system")
        body_parts.append(f"- Conceptual grouping: {reasoning}")
        body_parts.append(f"- Files modified: {len(files)} files")
        
        if len(files) <= 10:
            body_parts.append("- File list:")
            for filepath, change_type in files:
                body_parts.append(f"  {change_type}: {filepath}")
        
        body_parts.append("")
        body_parts.append("BVJ: [Segment: Platform, Goal: Stability, Impact: Atomic change management]")
        
        # Claude attribution footer (mandatory)
        footer = """
🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"""
        
        return f"{header}\n\n" + "\n".join(body_parts) + footer
    
    def handle_merge_conflicts(self) -> bool:
        """Handle merge conflicts safely with logging"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            merge_log_file = self.merge_log_dir / f"merge_conflict_{timestamp}.log"
            
            # Get current status
            status_result = self.run_git_command(["git", "status"])
            
            with open(merge_log_file, 'w') as f:
                f.write(f"Merge Conflict Detected: {datetime.now()}\n")
                f.write("=" * 50 + "\n")
                f.write("Git Status:\n")
                f.write(status_result.stdout)
                f.write("\n" + "=" * 50 + "\n")
                f.write("DECISION: Emergency stop due to merge conflicts\n")
                f.write("REASON: Complex merge conflicts require manual resolution\n")
            
            logger.error(f"Merge conflicts detected, logged to {merge_log_file}")
            logger.error("EMERGENCY STOP: Manual intervention required")
            self.emergency_stop = True
            return False
            
        except Exception as e:
            logger.error(f"Failed to handle merge conflicts: {e}")
            self.emergency_stop = True
            return False
    
    def monitoring_cycle(self) -> bool:
        """Execute one monitoring cycle"""
        try:
            cycle_start = datetime.now()
            self.cycles_completed += 1
            
            logger.info(f"=== Monitoring Cycle {self.cycles_completed} ===")
            logger.info(f"Cycle start: {cycle_start}")
            logger.info(f"Commits created so far: {self.commits_created}")
            
            # Safety checks
            if not self.check_repository_safety():
                return False
            
            # Get current changes
            changes = self.get_repository_changes()
            total_changes = sum(len(files) for files in changes.values())
            
            if total_changes == 0:
                logger.info("No changes detected in repository")
                return True
            
            logger.info(f"Changes detected: {total_changes} files")
            for change_type, files in changes.items():
                if files:
                    logger.info(f"  {change_type}: {len(files)} files")
            
            # Analyze and group changes by concepts
            concept_groups = self.analyze_change_concepts(changes)
            
            if not concept_groups:
                logger.warning("No conceptual groups identified, skipping commit")
                return True
            
            # Create atomic commits for each concept
            successful_commits = 0
            for concept in concept_groups:
                if self.create_atomic_commit(concept):
                    successful_commits += 1
                else:
                    logger.warning(f"Failed to commit concept: {concept['description']}")
            
            logger.info(f"Cycle completed: {successful_commits}/{len(concept_groups)} commits successful")
            
            cycle_duration = datetime.now() - cycle_start
            logger.info(f"Cycle duration: {cycle_duration}")
            
            return True
            
        except Exception as e:
            logger.error(f"Monitoring cycle failed: {e}")
            return False
    
    def run_continuous_monitoring(self):
        """Main monitoring loop - runs for specified duration"""
        logger.info("🚀 Starting GitCommitGardener Continuous Monitoring")
        logger.info(f"Monitoring will run until: {self.end_time}")
        
        try:
            while datetime.now() < self.end_time and not self.emergency_stop:
                current_time = datetime.now()
                elapsed = current_time - self.start_time
                remaining = self.end_time - current_time
                
                logger.info(f"📊 Monitoring Status - Elapsed: {elapsed}, Remaining: {remaining}")
                
                # Execute monitoring cycle
                cycle_success = self.monitoring_cycle()
                
                if not cycle_success:
                    logger.error("Monitoring cycle failed")
                    if self.emergency_stop:
                        break
                
                # Sleep until next cycle
                logger.info(f"💤 Sleeping for {self.check_interval} seconds until next check")
                time.sleep(self.check_interval)
            
            # Final status report
            total_duration = datetime.now() - self.start_time
            logger.info("🏁 GitCommitGardener Monitoring Complete")
            logger.info(f"Total duration: {total_duration}")
            logger.info(f"Cycles completed: {self.cycles_completed}")
            logger.info(f"Commits created: {self.commits_created}")
            
            if self.emergency_stop:
                logger.warning("⚠️ Monitoring stopped due to emergency condition")
            else:
                logger.info("✅ Monitoring completed successfully")
                
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped by user interrupt")
        except Exception as e:
            logger.error(f"❌ Monitoring failed with critical error: {e}")


def main():
    """Main entry point for GitCommitGardener Monitor"""
    repo_path = os.getcwd()
    monitoring_hours = 20  # Target 20 hours, minimum 8
    
    print("GitCommitGardener Continuous Monitoring System")
    print("=" * 50)
    print(f"Repository: {repo_path}")
    print(f"Monitoring Duration: {monitoring_hours} hours")
    print(f"Check Interval: 2 minutes")
    print("=" * 50)
    
    # Create and run monitor
    monitor = GitCommitGardenerMonitor(repo_path, monitoring_hours)
    monitor.run_continuous_monitoring()


if __name__ == "__main__":
    main()