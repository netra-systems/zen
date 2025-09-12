#!/usr/bin/env python3
"""
AI Agent File Metadata Tracking System
Generates and manages metadata headers for AI-modified files
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class MetadataHeaderGenerator:
    """Generates metadata headers for AI-modified files"""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.sequence_number = 0
        self.agent_info = self._get_agent_info()
        self.git_state = self._get_git_state()
        
    def _get_agent_info(self) -> Dict[str, str]:
        """Get current AI agent information"""
        return {
            "name": "Claude Opus 4.1",
            "version": "claude-opus-4-1-20250805",
            "tool": "claude-code",
            "tool_version": "v1.2.3"
        }
    
    def _get_git_state(self) -> Dict[str, Any]:
        """Get current git repository state"""
        try:
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
            
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()[:8]
            
            # Check if working directory is clean
            status = subprocess.check_output(
                ["git", "status", "--porcelain"],
                text=True, stderr=subprocess.DEVNULL
            )
            
            uncommitted_count = len([l for l in status.splitlines() if l.strip()])
            status_text = "clean" if uncommitted_count == 0 else f"dirty ({uncommitted_count} uncommitted)"
            
            return {
                "branch": branch,
                "commit": commit,
                "status": status_text,
                "uncommitted_count": uncommitted_count
            }
        except subprocess.CalledProcessError:
            return {
                "branch": "unknown",
                "commit": "unknown",
                "status": "unknown",
                "uncommitted_count": 0
            }
    
    def generate_metadata(
        self,
        task_description: str,
        change_type: str = "Feature",
        scope: str = "Component",
        risk_level: str = "Medium",
        breaking_change: bool = False,
        dependencies_modified: bool = False
    ) -> Dict[str, Any]:
        """Generate metadata for a file modification"""
        
        self.sequence_number += 1
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": self.agent_info,
            "context": {
                "task_description": task_description[:200],
                "execution_plan": "Add baseline agent tracking metadata",
                "parent_task_id": None,
                "user_intent": "Implement AI agent file tracking"
            },
            "git_state": self.git_state,
            "change_classification": {
                "type": change_type,
                "scope": scope,
                "breaking": breaking_change,
                "dependencies_modified": dependencies_modified
            },
            "risk_assessment": {
                "level": risk_level,
                "auto_detection": "Based on file path and change type"
            },
            "review_tracking": {
                "status": "Pending",
                "reviewer": None,
                "comments": None,
                "auto_score": 85
            },
            "session_tracking": {
                "session_id": self.session_id,
                "conversation_id": "baseline_tracking_implementation",
                "sequence_number": self.sequence_number,
                "total_files_modified": self.sequence_number
            },
            "quality_metrics": {
                "lines_added": 0,
                "lines_modified": 0,
                "lines_deleted": 0,
                "complexity_delta": None,
                "coverage_delta": None,
                "lint_issues": 0
            },
            "rollback_info": {
                "previous_version": self.git_state.get("commit"),
                "rollback_command": f"git checkout {self.git_state.get('commit')} -- {{file_path}}",
                "backup_location": None,
                "recovery_instructions": "Use rollback command or restore from git history"
            }
        }
    
    def format_python_header(self, metadata: Dict[str, Any]) -> str:
        """Format metadata as Python comment header"""
        header = [
            "# AI AGENT MODIFICATION METADATA",
            "# ================================",
            f"# Timestamp: {metadata['timestamp']}",
            f"# Agent: {metadata['agent']['name']} {metadata['agent']['version']}",
            f"# Context: {metadata['context']['task_description']}",
            f"# Git: {metadata['git_state']['branch']} | {metadata['git_state']['commit']} | {metadata['git_state']['status']}",
            f"# Change: {metadata['change_classification']['type']} | Scope: {metadata['change_classification']['scope']} | Risk: {metadata['risk_assessment']['level']}",
            f"# Session: {metadata['session_tracking']['session_id']} | Seq: {metadata['session_tracking']['sequence_number']}",
            f"# Review: {metadata['review_tracking']['status']} | Score: {metadata['review_tracking']['auto_score']}",
            "# ================================",
            ""
        ]
        return "\n".join(header)
    
    def format_javascript_header(self, metadata: Dict[str, Any]) -> str:
        """Format metadata as JavaScript comment header"""
        header = [
            "/**",
            " * AI AGENT MODIFICATION METADATA",
            " * ================================",
            f" * Timestamp: {metadata['timestamp']}",
            f" * Agent: {metadata['agent']['name']} {metadata['agent']['version']}",
            f" * Context: {metadata['context']['task_description']}",
            f" * Git: {metadata['git_state']['branch']} | {metadata['git_state']['commit']} | {metadata['git_state']['status']}",
            f" * Change: {metadata['change_classification']['type']} | Scope: {metadata['change_classification']['scope']} | Risk: {metadata['risk_assessment']['level']}",
            f" * Session: {metadata['session_tracking']['session_id']} | Seq: {metadata['session_tracking']['sequence_number']}",
            f" * Review: {metadata['review_tracking']['status']} | Score: {metadata['review_tracking']['auto_score']}",
            " * ================================",
            " */",
            ""
        ]
        return "\n".join(header)
    
    def get_header_for_file(self, file_path: str, metadata: Dict[str, Any]) -> str:
        """Get appropriate header format based on file extension"""
        ext = Path(file_path).suffix.lower()
        
        if ext in ['.py']:
            return self.format_python_header(metadata)
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            return self.format_javascript_header(metadata)
        elif ext in ['.css', '.scss', '.sass']:
            return self.format_javascript_header(metadata)  # CSS uses /* */ comments
        elif ext in ['.html', '.xml']:
            return self._format_html_header(metadata)
        elif ext in ['.sql']:
            return self._format_sql_header(metadata)
        elif ext in ['.yaml', '.yml']:
            return self._format_yaml_header(metadata)
        else:
            # Default to Python style for unknown types
            return self.format_python_header(metadata)
    
    def _format_html_header(self, metadata: Dict[str, Any]) -> str:
        """Format metadata as HTML comment header"""
        header = [
            "<!--",
            "  AI AGENT MODIFICATION METADATA",
            "  ================================",
            f"  Timestamp: {metadata['timestamp']}",
            f"  Agent: {metadata['agent']['name']} {metadata['agent']['version']}",
            f"  Context: {metadata['context']['task_description']}",
            f"  Git: {metadata['git_state']['branch']} | {metadata['git_state']['commit']} | {metadata['git_state']['status']}",
            f"  Change: {metadata['change_classification']['type']} | Scope: {metadata['change_classification']['scope']} | Risk: {metadata['risk_assessment']['level']}",
            f"  Session: {metadata['session_tracking']['session_id']} | Seq: {metadata['session_tracking']['sequence_number']}",
            f"  Review: {metadata['review_tracking']['status']} | Score: {metadata['review_tracking']['auto_score']}",
            "  ================================",
            "-->",
            ""
        ]
        return "\n".join(header)
    
    def _format_sql_header(self, metadata: Dict[str, Any]) -> str:
        """Format metadata as SQL comment header"""
        header = [
            "-- AI AGENT MODIFICATION METADATA",
            "-- ================================",
            f"-- Timestamp: {metadata['timestamp']}",
            f"-- Agent: {metadata['agent']['name']} {metadata['agent']['version']}",
            f"-- Context: {metadata['context']['task_description']}",
            f"-- Git: {metadata['git_state']['branch']} | {metadata['git_state']['commit']} | {metadata['git_state']['status']}",
            f"-- Change: {metadata['change_classification']['type']} | Scope: {metadata['change_classification']['scope']} | Risk: {metadata['risk_assessment']['level']}",
            f"-- Session: {metadata['session_tracking']['session_id']} | Seq: {metadata['session_tracking']['sequence_number']}",
            f"-- Review: {metadata['review_tracking']['status']} | Score: {metadata['review_tracking']['auto_score']}",
            "-- ================================",
            ""
        ]
        return "\n".join(header)
    
    def _format_yaml_header(self, metadata: Dict[str, Any]) -> str:
        """Format metadata as YAML comment header"""
        header = [
            "# AI AGENT MODIFICATION METADATA",
            "# ================================",
            "# metadata:",
            f"#   timestamp: {metadata['timestamp']}",
            f"#   agent: {metadata['agent']['name']} {metadata['agent']['version']}",
            f"#   context: {metadata['context']['task_description']}",
            "#   git:",
            f"#     branch: {metadata['git_state']['branch']}",
            f"#     commit: {metadata['git_state']['commit']}",
            f"#     status: {metadata['git_state']['status']}",
            "#   change:",
            f"#     type: {metadata['change_classification']['type']}",
            f"#     scope: {metadata['change_classification']['scope']}",
            f"#     risk: {metadata['risk_assessment']['level']}",
            "#   session:",
            f"#     id: {metadata['session_tracking']['session_id']}",
            f"#     sequence: {metadata['session_tracking']['sequence_number']}",
            "#   review:",
            f"#     status: {metadata['review_tracking']['status']}",
            f"#     score: {metadata['review_tracking']['auto_score']}",
            "# ================================",
            ""
        ]
        return "\n".join(header)
    
    def add_header_to_file(
        self,
        file_path: str,
        metadata: Dict[str, Any],
        preserve_shebang: bool = True
    ) -> bool:
        """Add metadata header to a file"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"File not found: {file_path}")
                return False
            
            # Read existing content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if header already exists
            if "AI AGENT MODIFICATION METADATA" in content[:1000]:
                print(f"Header already exists in {file_path}")
                return False
            
            # Get appropriate header
            header = self.get_header_for_file(str(file_path), metadata)
            
            # Handle shebang lines
            lines = content.splitlines(keepends=True)
            if lines and preserve_shebang:
                first_line = lines[0]
                if first_line.startswith('#!') or first_line.startswith('#!/'):
                    # Insert header after shebang
                    new_content = first_line + header + ''.join(lines[1:])
                else:
                    # Insert header at beginning
                    new_content = header + content
            else:
                new_content = header + content
            
            # Write updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"Added metadata header to {file_path}")
            return True
            
        except Exception as e:
            print(f"Error adding header to {file_path}: {e}")
            return False
    
    def add_headers_to_batch(
        self,
        file_paths: List[str],
        task_description: str,
        **metadata_kwargs
    ) -> Dict[str, bool]:
        """Add headers to multiple files"""
        results = {}
        
        for file_path in file_paths:
            # Generate fresh metadata for each file
            metadata = self.generate_metadata(task_description, **metadata_kwargs)
            
            # Determine risk level based on file path
            if 'auth' in file_path.lower() or 'security' in file_path.lower():
                metadata['risk_assessment']['level'] = 'High'
            elif 'core' in file_path.lower() or 'supervisor' in file_path.lower():
                metadata['risk_assessment']['level'] = 'High'
            elif 'test' in file_path.lower():
                metadata['risk_assessment']['level'] = 'Low'
            
            success = self.add_header_to_file(file_path, metadata)
            results[file_path] = success
        
        return results
    
    def save_metadata_log(self, metadata: Dict[str, Any], file_path: str = "metadata_log.json"):
        """Save metadata to a log file for audit purposes"""
        log_entry = {
            "file_path": file_path,
            "metadata": metadata,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        log_path = Path(file_path)
        
        # Load existing log if it exists
        if log_path.exists():
            with open(log_path, 'r') as f:
                log_data = json.load(f)
        else:
            log_data = []
        
        # Add new entry
        log_data.append(log_entry)
        
        # Save updated log
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)


def main():
    """Command-line interface for metadata header generator"""
    parser = argparse.ArgumentParser(description="AI Agent File Metadata Header Generator")
    parser.add_argument("--file", help="Single file to add header to")
    parser.add_argument("--batch", nargs="+", help="Multiple files to add headers to")
    parser.add_argument("--task", default="Add baseline agent tracking", help="Task description")
    parser.add_argument("--change-type", default="Feature", help="Change type (Feature/Bugfix/Refactor/etc)")
    parser.add_argument("--scope", default="Component", help="Change scope (File/Component/Module/System)")
    parser.add_argument("--risk", default="Medium", help="Risk level (Low/Medium/High/Critical)")
    
    args = parser.parse_args()
    
    generator = MetadataHeaderGenerator()
    
    if args.file:
        metadata = generator.generate_metadata(
            task_description=args.task,
            change_type=args.change_type,
            scope=args.scope,
            risk_level=args.risk
        )
        success = generator.add_header_to_file(args.file, metadata)
        print(f"Success: {success}")
    
    elif args.batch:
        results = generator.add_headers_to_batch(
            file_paths=args.batch,
            task_description=args.task,
            change_type=args.change_type,
            scope=args.scope,
            risk_level=args.risk
        )
        print("\nBatch Results:")
        for file_path, success in results.items():
            status = "[U+2713]" if success else "[U+2717]"
            print(f"  {status} {file_path}")
    
    else:
        print("Please specify --file or --batch")
        parser.print_help()


if __name__ == "__main__":
    main()