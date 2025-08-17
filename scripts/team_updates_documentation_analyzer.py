"""Documentation Analyzer - Tracks documentation and spec updates."""

import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import re
import xml.etree.ElementTree as ET


class DocumentationAnalyzer:
    """Analyzes documentation and specification changes."""
    
    def __init__(self, project_root: Path):
        """Initialize with project root."""
        self.project_root = project_root
        self.docs_dir = project_root / "docs"
        self.spec_dir = project_root / "SPEC"
        self.learnings_dir = self.spec_dir / "learnings"
    
    async def analyze(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Track documentation and spec updates."""
        doc_changes = await self.find_doc_changes(start, end)
        spec_updates = await self.find_spec_updates(start, end)
        learnings = self.extract_learnings(start, end)
        
        return {
            "doc_changes": doc_changes,
            "spec_updates": spec_updates,
            "new_learnings": learnings,
            "documentation_health": self._assess_doc_health()
        }
    
    async def find_doc_changes(self, start: datetime, end: datetime) -> List[Dict]:
        """Identify changed documentation files."""
        changes = []
        
        # Get git log for docs directory
        since = start.strftime("%Y-%m-%d")
        cmd = [
            "git", "log", f"--since={since}",
            "--name-status", "--pretty=format:%h|%s",
            "--", "docs/", "*.md", "README*"
        ]
        
        result = await self._run_git_command(cmd)
        changes = self._parse_doc_changes(result)
        
        return changes[:10]  # Limit to top 10
    
    async def find_spec_updates(self, start: datetime, end: datetime) -> List[Dict]:
        """Track SPEC/ directory changes."""
        updates = []
        
        # Get git log for SPEC directory
        since = start.strftime("%Y-%m-%d")
        cmd = [
            "git", "log", f"--since={since}",
            "--name-status", "--pretty=format:%h|%s",
            "--", "SPEC/"
        ]
        
        result = await self._run_git_command(cmd)
        updates = self._parse_spec_updates(result)
        
        return updates[:10]  # Limit to top 10
    
    def extract_learnings(self, start: datetime, end: datetime) -> List[Dict]:
        """Highlight new learnings added."""
        learnings = []
        
        if self.learnings_dir.exists():
            for xml_file in self.learnings_dir.glob("*.xml"):
                try:
                    stat = xml_file.stat()
                    mod_time = datetime.fromtimestamp(stat.st_mtime)
                    
                    if start <= mod_time <= end:
                        learning = self._extract_learning_from_xml(xml_file)
                        if learning:
                            learnings.append(learning)
                except Exception:
                    continue
        
        return learnings[:5]  # Limit to top 5
    
    async def _run_git_command(self, cmd: List[str]) -> str:
        """Execute git command and return output."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, cwd=self.project_root,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            return stdout.decode() if proc.returncode == 0 else ""
        except Exception:
            return ""
    
    def _parse_doc_changes(self, git_output: str) -> List[Dict]:
        """Parse documentation changes from git output."""
        changes = []
        current_commit = None
        
        for line in git_output.strip().split('\n'):
            if not line: continue
            
            if '|' in line:
                parts = line.split('|')
                current_commit = {
                    "hash": parts[0],
                    "message": parts[1] if len(parts) > 1 else ""
                }
            elif line[0] in 'MAD' and current_commit:
                status, file_path = line.split(None, 1)
                changes.append({
                    "file": file_path,
                    "action": self._status_to_action(status),
                    "summary": self._simplify_message(current_commit["message"])
                })
        
        return changes
    
    def _parse_spec_updates(self, git_output: str) -> List[Dict]:
        """Parse SPEC updates from git output."""
        updates = []
        current_commit = None
        
        for line in git_output.strip().split('\n'):
            if not line: continue
            
            if '|' in line:
                parts = line.split('|')
                current_commit = {
                    "hash": parts[0],
                    "message": parts[1] if len(parts) > 1 else ""
                }
            elif line[0] in 'MAD' and current_commit:
                status, file_path = line.split(None, 1)
                if file_path.endswith('.xml'):
                    spec_name = Path(file_path).stem
                    updates.append({
                        "spec": spec_name,
                        "action": self._status_to_action(status),
                        "summary": self._simplify_message(current_commit["message"])
                    })
        
        return updates
    
    def _extract_learning_from_xml(self, xml_file: Path) -> Optional[Dict]:
        """Extract learning content from XML file."""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            category = xml_file.stem
            learnings = root.findall('.//learning')
            
            if learnings:
                latest = learnings[-1]  # Get most recent
                return {
                    "category": category,
                    "problem": latest.findtext('problem', ''),
                    "solution": latest.findtext('solution', ''),
                    "prevention": latest.findtext('prevention', '')
                }
        except Exception:
            pass
        
        return None
    
    def _status_to_action(self, status: str) -> str:
        """Convert git status to human-readable action."""
        return {
            'A': 'added',
            'M': 'updated',
            'D': 'removed'
        }.get(status, 'changed')
    
    def _simplify_message(self, message: str) -> str:
        """Simplify commit message for readability."""
        # Remove prefixes like feat:, fix:, docs:
        message = re.sub(r'^(feat|fix|docs|chore|refactor)[:\(\)]?\s*', '', message, flags=re.I)
        # Limit length
        return message[:80] if message else "Updated"
    
    def _assess_doc_health(self) -> str:
        """Assess overall documentation health."""
        critical_docs = [
            self.project_root / "README.md",
            self.project_root / "CLAUDE.md",
            self.docs_dir / "ARCHITECTURE.md",
            self.docs_dir / "API_DOCUMENTATION.md"
        ]
        
        missing = sum(1 for doc in critical_docs if not doc.exists())
        
        if missing == 0:
            return "excellent"
        elif missing == 1:
            return "good"
        elif missing == 2:
            return "needs_attention"
        else:
            return "poor"