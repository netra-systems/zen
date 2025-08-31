#!/usr/bin/env python3
"""
Comprehensive audit tool to detect unused code across the entire Netra codebase.
Identifies functions, methods, and event handlers that are defined but never called.
"""

import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from datetime import datetime
from collections import defaultdict

class UnusedCodeAuditor:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.findings = []
        self.websocket_analysis = {
            "backend_events_defined": [],
            "backend_events_emitted": [],
            "frontend_handlers_defined": [],
            "missing_emissions": [],
            "orphaned_handlers": []
        }
        self.function_definitions = defaultdict(list)
        self.function_calls = defaultdict(set)
        self.imports_map = defaultdict(list)
        self.api_endpoints = []
        self.api_calls = []
        
    def run_audit(self) -> Dict[str, Any]:
        """Run the complete audit process."""
        print("[AUDIT] Starting comprehensive unused code audit...")
        
        # Step 1: Collect all Python definitions and usages
        print("\n[PYTHON] Analyzing Python files...")
        self.analyze_python_files()
        
        # Step 2: Analyze WebSocket event chain
        print("\n[WEBSOCKET] Analyzing WebSocket communication chain...")
        self.analyze_websocket_chain()
        
        # Step 3: Analyze API endpoints
        print("\n[API] Analyzing API endpoints...")
        self.analyze_api_endpoints()
        
        # Step 4: Analyze database operations
        print("\n[DATABASE] Analyzing database operations...")
        self.analyze_database_operations()
        
        # Step 5: Analyze frontend JavaScript/TypeScript
        print("\n[FRONTEND] Analyzing frontend code...")
        self.analyze_frontend_code()
        
        # Step 6: Cross-reference and identify unused code
        print("\n[XREF] Cross-referencing definitions and usages...")
        self.identify_unused_code()
        
        # Step 7: Generate report
        print("\n[REPORT] Generating audit report...")
        return self.generate_report()
    
    def analyze_python_files(self):
        """Analyze all Python files for definitions and usages."""
        python_files = list(self.base_path.rglob("*.py"))
        
        for file_path in python_files:
            # Skip test files and migrations for initial analysis
            if "test" in str(file_path).lower() or "migration" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Parse AST
                tree = ast.parse(content, filename=str(file_path))
                
                # Extract function/method definitions
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.function_definitions[node.name].append({
                            "file": str(file_path.relative_to(self.base_path)),
                            "line": node.lineno,
                            "type": "async" if isinstance(node, ast.AsyncFunctionDef) else "sync",
                            "is_method": self._is_method(node),
                            "decorators": [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list]
                        })
                    
                    # Extract function calls
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            self.function_calls[node.func.id].add(str(file_path.relative_to(self.base_path)))
                        elif isinstance(node.func, ast.Attribute):
                            self.function_calls[node.func.attr].add(str(file_path.relative_to(self.base_path)))
                            
            except Exception as e:
                print(f"  [WARNING] Error analyzing {file_path}: {e}")
    
    def _is_method(self, node: ast.FunctionDef) -> bool:
        """Check if a function is a method (has 'self' or 'cls' as first param)."""
        if node.args.args:
            first_arg = node.args.args[0].arg
            return first_arg in ('self', 'cls')
        return False
    
    def analyze_websocket_chain(self):
        """Analyze WebSocket event definitions and emissions."""
        # Backend WebSocket manager analysis
        ws_manager_path = self.base_path / "netra_backend" / "app" / "services" / "websocket_manager.py"
        agent_manager_path = self.base_path / "netra_backend" / "app" / "services" / "agent_manager.py"
        
        # Find all notify_* methods in WebSocket manager
        if ws_manager_path.exists():
            with open(ws_manager_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find all notification methods
            notify_methods = re.findall(r'async def (notify_\w+)\(', content)
            for method in notify_methods:
                event_name = method.replace('notify_', '')
                self.websocket_analysis["backend_events_defined"].append({
                    "method": method,
                    "event": event_name,
                    "file": "netra_backend/app/services/websocket_manager.py"
                })
                
            # Check where these methods are called
            for method in notify_methods:
                # Search for calls in agent manager and other services
                call_pattern = rf'\b{method}\s*\('
                found_calls = []
                
                for py_file in (self.base_path / "netra_backend").rglob("*.py"):
                    if py_file == ws_manager_path:
                        continue
                    with open(py_file, 'r', encoding='utf-8') as f:
                        if re.search(call_pattern, f.read()):
                            found_calls.append(str(py_file.relative_to(self.base_path)))
                
                if found_calls:
                    self.websocket_analysis["backend_events_emitted"].append({
                        "method": method,
                        "called_from": found_calls
                    })
                else:
                    self.findings.append({
                        "type": "missing_websocket_emission",
                        "severity": "CRITICAL",
                        "location": {
                            "file": "netra_backend/app/services/websocket_manager.py",
                            "function": method
                        },
                        "description": f"WebSocket notification method '{method}' is defined but never called",
                        "suggested_action": f"Add calls to {method} in agent execution flow"
                    })
        
        # Frontend WebSocket handler analysis
        frontend_ws_path = self.base_path / "frontend" / "src" / "services" / "websocket.js"
        if frontend_ws_path.exists():
            with open(frontend_ws_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find all event handlers
            handlers = re.findall(r"on\('(\w+)'", content) + re.findall(r'on\("(\w+)"', content)
            for handler in handlers:
                self.websocket_analysis["frontend_handlers_defined"].append({
                    "event": handler,
                    "file": "frontend/src/services/websocket.js"
                })
                
                # Check if backend emits this event
                backend_emits = any(
                    e["event"] == handler 
                    for e in self.websocket_analysis["backend_events_defined"]
                )
                
                if not backend_emits:
                    self.websocket_analysis["orphaned_handlers"].append(handler)
                    self.findings.append({
                        "type": "orphaned_websocket_handler",
                        "severity": "HIGH",
                        "location": {
                            "file": "frontend/src/services/websocket.js",
                            "event": handler
                        },
                        "description": f"Frontend has handler for '{handler}' event but backend never emits it",
                        "suggested_action": f"Either remove handler or implement backend emission for '{handler}'"
                    })
    
    def analyze_api_endpoints(self):
        """Analyze API endpoint definitions and their usage."""
        # Find all API endpoint definitions
        api_dirs = [
            self.base_path / "netra_backend" / "app" / "api",
            self.base_path / "auth_service" / "app" / "api"
        ]
        
        for api_dir in api_dirs:
            if not api_dir.exists():
                continue
                
            for py_file in api_dir.rglob("*.py"):
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Find FastAPI route definitions
                routes = re.findall(r'@router\.(get|post|put|delete|patch)\("([^"]+)"', content)
                for method, path in routes:
                    self.api_endpoints.append({
                        "method": method.upper(),
                        "path": path,
                        "file": str(py_file.relative_to(self.base_path))
                    })
        
        # Find API calls in frontend
        frontend_dir = self.base_path / "frontend" / "src"
        if frontend_dir.exists():
            for js_file in frontend_dir.rglob("*.js"):
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Find fetch/axios calls
                api_calls = re.findall(r'fetch\(["\']([^"\']+)["\']', content)
                api_calls += re.findall(r'axios\.(get|post|put|delete)\(["\']([^"\']+)["\']', content)
                
                for call in api_calls:
                    if isinstance(call, tuple):
                        self.api_calls.append(call[1])
                    else:
                        self.api_calls.append(call)
        
        # Check for unused endpoints
        for endpoint in self.api_endpoints:
            path_pattern = endpoint["path"].replace("{", "").replace("}", "")
            used = any(path_pattern in call for call in self.api_calls)
            
            if not used:
                self.findings.append({
                    "type": "unused_api_endpoint",
                    "severity": "MEDIUM",
                    "location": {
                        "file": endpoint["file"],
                        "endpoint": f"{endpoint['method']} {endpoint['path']}"
                    },
                    "description": f"API endpoint {endpoint['method']} {endpoint['path']} is defined but never called from frontend",
                    "suggested_action": "Remove endpoint or add frontend integration"
                })
    
    def analyze_database_operations(self):
        """Analyze database operations for unused methods."""
        db_files = [
            self.base_path / "netra_backend" / "app" / "services" / "database_manager.py",
            *list((self.base_path / "netra_backend" / "app" / "repositories").rglob("*.py"))
        ]
        
        for db_file in db_files:
            if not db_file.exists():
                continue
                
            with open(db_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find database operation methods
            db_methods = re.findall(r'async def ((?:get|create|update|delete|query|insert)_\w+)\(', content)
            
            for method in db_methods:
                # Check if method is called anywhere
                method_calls = self.function_calls.get(method, set())
                
                if not method_calls:
                    self.findings.append({
                        "type": "unused_database_method",
                        "severity": "MEDIUM",
                        "location": {
                            "file": str(db_file.relative_to(self.base_path)),
                            "function": method
                        },
                        "description": f"Database method '{method}' is defined but never called",
                        "suggested_action": "Remove method or implement calling code"
                    })
    
    def analyze_frontend_code(self):
        """Analyze frontend JavaScript/TypeScript code."""
        frontend_src = self.base_path / "frontend" / "src"
        if not frontend_src.exists():
            return
            
        # Analyze store actions
        stores_dir = frontend_src / "stores"
        if stores_dir.exists():
            for store_file in stores_dir.rglob("*.js"):
                with open(store_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Find action definitions
                actions = re.findall(r'(\w+):\s*action\(', content)
                
                for action in actions:
                    # Search for dispatch calls
                    action_used = False
                    for js_file in frontend_src.rglob("*.js"):
                        if js_file == store_file:
                            continue
                        with open(js_file, 'r', encoding='utf-8') as f:
                            if action in f.read():
                                action_used = True
                                break
                    
                    if not action_used:
                        self.findings.append({
                            "type": "unused_store_action",
                            "severity": "LOW",
                            "location": {
                                "file": str(store_file.relative_to(self.base_path)),
                                "action": action
                            },
                            "description": f"Store action '{action}' is defined but never dispatched",
                            "suggested_action": "Remove action or implement usage"
                        })
    
    def identify_unused_code(self):
        """Cross-reference definitions and calls to identify unused code."""
        # Check all function definitions against calls
        for func_name, definitions in self.function_definitions.items():
            # Skip special methods
            if func_name.startswith('__') or func_name in ('setUp', 'tearDown', 'setUpClass', 'tearDownClass'):
                continue
                
            # Skip if it's a known entry point (main, decorated with @app, @router, etc.)
            is_entry_point = any(
                any(dec in str(d["decorators"]) for dec in ['app', 'router', 'click', 'cli'])
                for d in definitions
            )
            
            if is_entry_point:
                continue
                
            # Check if function is called
            if func_name not in self.function_calls:
                for definition in definitions:
                    self.findings.append({
                        "type": "unused_function",
                        "severity": "LOW" if definition["is_method"] else "MEDIUM",
                        "location": {
                            "file": definition["file"],
                            "line": definition["line"],
                            "function": func_name
                        },
                        "description": f"{'Method' if definition['is_method'] else 'Function'} '{func_name}' is defined but never called",
                        "suggested_action": "Remove function or add calling code"
                    })
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate the final audit report."""
        # Count findings by type
        findings_by_type = defaultdict(list)
        for finding in self.findings:
            findings_by_type[finding["type"]].append(finding)
        
        # Identify critical issues
        critical_issues = [f for f in self.findings if f["severity"] == "CRITICAL"]
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_unused_functions": len([f for f in self.findings if f["type"] == "unused_function"]),
                "total_missing_websocket_emissions": len([f for f in self.findings if f["type"] == "missing_websocket_emission"]),
                "total_orphaned_handlers": len(self.websocket_analysis["orphaned_handlers"]),
                "total_unused_api_endpoints": len([f for f in self.findings if f["type"] == "unused_api_endpoint"]),
                "total_unused_database_methods": len([f for f in self.findings if f["type"] == "unused_database_method"]),
                "critical_issues": len(critical_issues),
                "findings_by_type": {k: len(v) for k, v in findings_by_type.items()}
            },
            "findings": self.findings,
            "websocket_analysis": self.websocket_analysis
        }
        
        return report

def main():
    """Main execution function."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Create auditor and run audit
    auditor = UnusedCodeAuditor(project_root)
    report = auditor.run_audit()
    
    # Save report to file
    report_path = project_root / "audit_report_unused_code.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n[SUCCESS] Audit complete! Report saved to: {report_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("AUDIT SUMMARY")
    print("="*60)
    print(f"Total unused functions: {report['summary']['total_unused_functions']}")
    print(f"Missing WebSocket emissions: {report['summary']['total_missing_websocket_emissions']}")
    print(f"Orphaned WebSocket handlers: {report['summary']['total_orphaned_handlers']}")
    print(f"Unused API endpoints: {report['summary']['total_unused_api_endpoints']}")
    print(f"Unused database methods: {report['summary']['total_unused_database_methods']}")
    print(f"Critical issues: {report['summary']['critical_issues']}")
    
    if report['summary']['critical_issues'] > 0:
        print("\n[CRITICAL] CRITICAL ISSUES FOUND:")
        for issue in report['findings']:
            if issue['severity'] == 'CRITICAL':
                print(f"  - {issue['description']}")
                print(f"    Location: {issue['location']['file']}")
                print(f"    Action: {issue['suggested_action']}")
    
    return 0 if report['summary']['critical_issues'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())