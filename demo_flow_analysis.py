#!/usr/bin/env python3
"""
Demo Flow Static Analysis and Validation

This script performs comprehensive static analysis of the demo WebSocket flow
to identify potential issues and validate the implementation without requiring
a running backend server.
"""

import ast
import inspect
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

class DemoFlowAnalyzer:
    """Analyzes the demo flow implementation for completeness and correctness"""
    
    def __init__(self):
        self.issues = []
        self.validation_results = {}
        self.flow_analysis = {}
        
    def analyze_demo_websocket_endpoint(self) -> Dict[str, Any]:
        """Analyze the demo WebSocket endpoint implementation"""
        print("🔍 Analyzing Demo WebSocket Endpoint Implementation")
        print("-" * 60)
        
        try:
            # Read and parse the demo WebSocket file
            demo_file = Path("netra_backend/app/routes/demo_websocket.py")
            if not demo_file.exists():
                return {"error": f"Demo WebSocket file not found: {demo_file}"}
            
            with open(demo_file, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            analysis = {
                "file_exists": True,
                "functions": [],
                "classes": [],
                "imports": [],
                "websocket_endpoint": None,
                "real_agent_workflow": None,
                "event_emissions": [],
                "error_handling": [],
            }
            
            # Analyze AST nodes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis["functions"].append({
                        "name": node.name,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "docstring": ast.get_docstring(node),
                        "line_number": node.lineno
                    })
                    
                    # Special analysis for key functions
                    if node.name == "demo_websocket_endpoint":
                        analysis["websocket_endpoint"] = self._analyze_websocket_endpoint_function(node)
                    elif node.name == "execute_real_agent_workflow":
                        analysis["real_agent_workflow"] = self._analyze_agent_workflow_function(node)
                        
                elif isinstance(node, ast.ClassDef):
                    analysis["classes"].append({
                        "name": node.name,
                        "methods": [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                        "line_number": node.lineno
                    })
                    
                elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    import_info = self._extract_import_info(node)
                    if import_info:
                        analysis["imports"].append(import_info)
            
            # Check for WebSocket event emissions
            analysis["event_emissions"] = self._find_event_emissions(content)
            
            # Check error handling patterns
            analysis["error_handling"] = self._find_error_handling_patterns(tree)
            
            return analysis
            
        except Exception as e:
            return {"error": f"Analysis failed: {e}", "traceback": traceback.format_exc()}
    
    def _analyze_websocket_endpoint_function(self, node: ast.AsyncFunctionDef) -> Dict[str, Any]:
        """Analyze the main WebSocket endpoint function"""
        analysis = {
            "is_async": True,
            "accepts_websocket": False,
            "has_message_loop": False,
            "handles_disconnection": False,
            "calls_agent_workflow": False,
            "sends_connection_confirmation": False,
        }
        
        # Check function parameters
        for arg in node.args.args:
            if arg.arg == "websocket":
                analysis["accepts_websocket"] = True
        
        # Analyze function body
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call):
                if hasattr(stmt.func, 'attr'):
                    if stmt.func.attr in ["accept", "receive_json", "send_json"]:
                        if stmt.func.attr == "accept":
                            pass  # WebSocket accept
                        elif stmt.func.attr == "receive_json":
                            analysis["has_message_loop"] = True
                        elif stmt.func.attr == "send_json":
                            analysis["sends_connection_confirmation"] = True
                    elif stmt.func.attr == "execute_real_agent_workflow":
                        analysis["calls_agent_workflow"] = True
            
            elif isinstance(stmt, ast.ExceptHandler):
                if any(exc.id == "WebSocketDisconnect" for exc in ast.walk(stmt) if isinstance(exc, ast.Name)):
                    analysis["handles_disconnection"] = True
        
        return analysis
    
    def _analyze_agent_workflow_function(self, node: ast.AsyncFunctionDef) -> Dict[str, Any]:
        """Analyze the real agent workflow execution function"""
        analysis = {
            "creates_user_context": False,
            "creates_database_session": False,
            "instantiates_supervisor": False,
            "has_websocket_adapter": False,
            "emits_websocket_events": False,
            "has_error_handling": False,
        }
        
        # Analyze function body for key patterns
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call):
                if hasattr(stmt.func, 'id'):
                    if stmt.func.id == "UserExecutionContext":
                        analysis["creates_user_context"] = True
                elif hasattr(stmt.func, 'attr'):
                    if stmt.func.attr == "get_async_session":
                        analysis["creates_database_session"] = True
                    elif "SupervisorAgent" in str(stmt.func):
                        analysis["instantiates_supervisor"] = True
            
            elif isinstance(stmt, ast.ClassDef):
                if stmt.name in ["WebSocketAdapter", "DemoWebSocketBridge"]:
                    analysis["has_websocket_adapter"] = True
            
            elif isinstance(stmt, ast.ExceptHandler):
                analysis["has_error_handling"] = True
        
        # Check for WebSocket event emissions in function (simplified check)
        try:
            with open("netra_backend/app/routes/demo_websocket.py", 'r') as f:
                full_content = f.read()
            if any(event in full_content for event in ["notify_agent_started", "notify_agent_thinking", "notify_agent_completed"]):
                analysis["emits_websocket_events"] = True
        except Exception:
            pass  # Skip if file reading fails
        
        return analysis
    
    def _extract_import_info(self, node) -> Optional[Dict[str, Any]]:
        """Extract import information from AST node"""
        if isinstance(node, ast.Import):
            return {
                "type": "import",
                "names": [alias.name for alias in node.names],
                "line": node.lineno
            }
        elif isinstance(node, ast.ImportFrom):
            return {
                "type": "from_import", 
                "module": node.module,
                "names": [alias.name for alias in node.names],
                "line": node.lineno
            }
        return None
    
    def _find_event_emissions(self, content: str) -> List[Dict[str, Any]]:
        """Find WebSocket event emissions in the code"""
        events = []
        required_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        for event in required_events:
            if f'notify_{event}' in content:
                events.append({
                    "event_type": event,
                    "has_notification_method": True,
                    "found_in_code": True
                })
            else:
                events.append({
                    "event_type": event,
                    "has_notification_method": False,
                    "found_in_code": False
                })
        
        return events
    
    def _find_error_handling_patterns(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Find error handling patterns in the code"""
        error_handlers = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                handler_info = {
                    "line": node.lineno,
                    "exception_type": None,
                    "has_logging": False,
                    "has_websocket_error_send": False
                }
                
                if node.type:
                    if hasattr(node.type, 'id'):
                        handler_info["exception_type"] = node.type.id
                    elif hasattr(node.type, 'attr'):
                        handler_info["exception_type"] = node.type.attr
                
                # Check if error handler logs or sends WebSocket errors
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Call):
                        if hasattr(stmt.func, 'attr'):
                            if stmt.func.attr in ["error", "critical", "warning"]:
                                handler_info["has_logging"] = True
                            elif stmt.func.attr == "send_json":
                                handler_info["has_websocket_error_send"] = True
                
                error_handlers.append(handler_info)
        
        return error_handlers
    
    def analyze_supervisor_agent_integration(self) -> Dict[str, Any]:
        """Analyze the SupervisorAgent integration"""
        print("🤖 Analyzing SupervisorAgent Integration")
        print("-" * 60)
        
        try:
            supervisor_file = Path("netra_backend/app/agents/supervisor_ssot.py")
            if not supervisor_file.exists():
                return {"error": f"SupervisorAgent file not found: {supervisor_file}"}
            
            with open(supervisor_file, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            analysis = {
                "file_exists": True,
                "has_execute_method": False,
                "emits_websocket_events": False,
                "has_orchestration_workflow": False,
                "creates_execution_engine": False,
                "required_event_emissions": []
            }
            
            # Look for key methods and patterns
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name == "execute":
                        analysis["has_execute_method"] = True
                        # Check for WebSocket event emissions in execute method
                        func_text = ast.get_source_segment(content, node) if hasattr(ast, 'get_source_segment') else ""
                        if any(event in func_text for event in ["notify_agent_started", "notify_agent_thinking", "notify_agent_completed"]):
                            analysis["emits_websocket_events"] = True
                    elif node.name == "_execute_orchestration_workflow":
                        analysis["has_orchestration_workflow"] = True
                    elif node.name == "_create_user_execution_engine":
                        analysis["creates_execution_engine"] = True
            
            # Check for required event emissions
            required_events = ["agent_started", "agent_thinking", "agent_completed", "agent_error"]
            for event in required_events:
                found = f"notify_{event}" in content
                analysis["required_event_emissions"].append({
                    "event": event,
                    "found": found
                })
            
            return analysis
            
        except Exception as e:
            return {"error": f"SupervisorAgent analysis failed: {e}"}
    
    def analyze_websocket_bridge_integration(self) -> Dict[str, Any]:
        """Analyze WebSocket bridge integration"""
        print("🌉 Analyzing WebSocket Bridge Integration")
        print("-" * 60)
        
        try:
            bridge_file = Path("netra_backend/app/services/agent_websocket_bridge.py")
            if not bridge_file.exists():
                return {"error": f"WebSocket bridge file not found: {bridge_file}"}
            
            # Due to file size, let's do a text-based analysis
            with open(bridge_file, 'r') as f:
                content = f.read()
            
            analysis = {
                "file_exists": True,
                "has_notification_methods": [],
                "has_user_context_support": False,
                "has_retry_logic": False,
                "has_error_tracking": False,
            }
            
            # Check for required notification methods
            required_methods = [
                "notify_agent_started",
                "notify_agent_thinking", 
                "notify_tool_executing",
                "notify_tool_completed",
                "notify_agent_completed",
                "notify_agent_error"
            ]
            
            for method in required_methods:
                found = f"async def {method}" in content
                analysis["has_notification_methods"].append({
                    "method": method,
                    "found": found
                })
            
            # Check for user context support
            analysis["has_user_context_support"] = "UserExecutionContext" in content
            
            # Check for retry logic
            analysis["has_retry_logic"] = "retry" in content.lower() and "attempt" in content.lower()
            
            # Check for error tracking
            analysis["has_error_tracking"] = "EventDeliveryTracker" in content
            
            return analysis
            
        except Exception as e:
            return {"error": f"WebSocket bridge analysis failed: {e}"}
    
    def validate_complete_flow(self) -> Dict[str, Any]:
        """Validate the complete demo flow end-to-end"""
        print("🔄 Validating Complete Demo Flow")
        print("=" * 80)
        
        validation = {
            "overall_score": 0,
            "max_score": 100,
            "critical_issues": [],
            "warnings": [],
            "validations": {}
        }
        
        # Analyze each component
        demo_analysis = self.analyze_demo_websocket_endpoint()
        supervisor_analysis = self.analyze_supervisor_agent_integration()
        bridge_analysis = self.analyze_websocket_bridge_integration()
        
        validation["validations"] = {
            "demo_endpoint": demo_analysis,
            "supervisor_agent": supervisor_analysis,
            "websocket_bridge": bridge_analysis
        }
        
        score = 0
        
        # Validate demo endpoint (30 points)
        if demo_analysis.get("websocket_endpoint"):
            endpoint = demo_analysis["websocket_endpoint"]
            if endpoint and endpoint.get("accepts_websocket"): score += 5
            if endpoint and endpoint.get("has_message_loop"): score += 5  
            if endpoint and endpoint.get("calls_agent_workflow"): score += 10
            if endpoint and endpoint.get("sends_connection_confirmation"): score += 5
            if endpoint and endpoint.get("handles_disconnection"): score += 5
        
        # Validate agent workflow (40 points)
        if demo_analysis.get("real_agent_workflow"):
            workflow = demo_analysis["real_agent_workflow"]
            if workflow and workflow.get("creates_user_context"): score += 10
            if workflow and workflow.get("creates_database_session"): score += 5
            if workflow and workflow.get("instantiates_supervisor"): score += 10
            if workflow and workflow.get("has_websocket_adapter"): score += 10
            if workflow and workflow.get("has_error_handling"): score += 5
        
        # Validate WebSocket events (20 points)
        if demo_analysis.get("event_emissions"):
            events = demo_analysis["event_emissions"]
            required_events = ["agent_started", "agent_thinking", "agent_completed"]
            for event_info in events:
                if event_info["event_type"] in required_events and event_info["found_in_code"]:
                    score += 6  # 18 points total for 3 critical events
        
        # Validate SupervisorAgent (10 points)
        if supervisor_analysis.get("has_execute_method"): score += 3
        if supervisor_analysis.get("emits_websocket_events"): score += 4
        if supervisor_analysis.get("has_orchestration_workflow"): score += 3
        
        validation["overall_score"] = min(score, 100)
        
        # Identify critical issues
        endpoint = demo_analysis.get("websocket_endpoint") or {}
        workflow = demo_analysis.get("real_agent_workflow") or {}
        
        if not endpoint.get("calls_agent_workflow"):
            validation["critical_issues"].append("Demo endpoint does not call real agent workflow")
        
        if not workflow.get("creates_user_context"):
            validation["critical_issues"].append("Agent workflow does not create UserExecutionContext")
            
        if not supervisor_analysis.get("emits_websocket_events"):
            validation["critical_issues"].append("SupervisorAgent does not emit WebSocket events")
        
        # Check for missing required events
        missing_events = []
        for event_info in demo_analysis.get("event_emissions", []):
            if event_info["event_type"] in ["agent_started", "agent_thinking", "agent_completed"] and not event_info["found_in_code"]:
                missing_events.append(event_info["event_type"])
        
        if missing_events:
            validation["critical_issues"].append(f"Missing required events: {missing_events}")
        
        return validation
    
    def generate_recommendations(self, validation: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving the demo flow"""
        recommendations = []
        
        score = validation["overall_score"]
        
        if score < 70:
            recommendations.append("🚨 CRITICAL: Demo flow has major implementation gaps - not ready for production")
        elif score < 85:
            recommendations.append("⚠️  WARNING: Demo flow has some issues that should be addressed")
        else:
            recommendations.append("✅ GOOD: Demo flow implementation looks solid")
        
        # Specific recommendations based on issues
        for issue in validation["critical_issues"]:
            if "does not call real agent workflow" in issue:
                recommendations.append("🔧 FIX: Ensure demo endpoint calls execute_real_agent_workflow function")
            elif "does not create UserExecutionContext" in issue:
                recommendations.append("🔧 FIX: Add UserExecutionContext creation with proper metadata")
            elif "does not emit WebSocket events" in issue:
                recommendations.append("🔧 FIX: Add WebSocket event emissions in SupervisorAgent.execute method")
            elif "Missing required events" in issue:
                recommendations.append("🔧 FIX: Implement all 5 required WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)")
        
        # General recommendations
        demo_validation = validation["validations"].get("demo_endpoint") or {}
        workflow_validation = demo_validation.get("real_agent_workflow") or {}
        if workflow_validation.get("creates_database_session"):
            recommendations.append("💡 ENSURE: Database session is properly managed with async context manager")
        
        recommendations.append("🧪 TEST: Validate error handling with network failures and database issues")
        recommendations.append("🔍 MONITOR: Add logging for debugging WebSocket event delivery")
        
        return recommendations
    
    def print_detailed_analysis(self, validation: Dict[str, Any], recommendations: List[str]):
        """Print detailed analysis results"""
        print("\n" + "="*80)
        print("📊 DEMO FLOW COMPREHENSIVE ANALYSIS RESULTS")
        print("="*80)
        
        score = validation["overall_score"]
        if score >= 85:
            status_emoji = "🟢"
            status_text = "EXCELLENT"
        elif score >= 70:
            status_emoji = "🟡" 
            status_text = "GOOD"
        elif score >= 50:
            status_emoji = "🟠"
            status_text = "NEEDS WORK"
        else:
            status_emoji = "🔴"
            status_text = "CRITICAL ISSUES"
        
        print(f"{status_emoji} Overall Score: {score}/100 ({status_text})")
        print()
        
        # Show critical issues
        if validation["critical_issues"]:
            print("🚨 CRITICAL ISSUES:")
            for i, issue in enumerate(validation["critical_issues"], 1):
                print(f"   {i}. {issue}")
            print()
        
        # Show component analysis
        print("📋 COMPONENT ANALYSIS:")
        print("-" * 40)
        
        # Demo endpoint analysis
        demo_endpoint = validation["validations"]["demo_endpoint"]
        if demo_endpoint.get("websocket_endpoint"):
            endpoint = demo_endpoint["websocket_endpoint"]
            print("🌐 Demo WebSocket Endpoint:")
            print(f"   ✅ Accepts WebSocket: {endpoint.get('accepts_websocket', False)}")
            print(f"   ✅ Has Message Loop: {endpoint.get('has_message_loop', False)}")
            print(f"   ✅ Calls Agent Workflow: {endpoint.get('calls_agent_workflow', False)}")
            print(f"   ✅ Sends Connection Confirmation: {endpoint.get('sends_connection_confirmation', False)}")
            print(f"   ✅ Handles Disconnection: {endpoint.get('handles_disconnection', False)}")
        
        # Agent workflow analysis
        if demo_endpoint.get("real_agent_workflow"):
            workflow = demo_endpoint["real_agent_workflow"]
            print("\n🤖 Real Agent Workflow:")
            print(f"   ✅ Creates User Context: {workflow.get('creates_user_context', False)}")
            print(f"   ✅ Creates Database Session: {workflow.get('creates_database_session', False)}")
            print(f"   ✅ Instantiates Supervisor: {workflow.get('instantiates_supervisor', False)}")
            print(f"   ✅ Has WebSocket Adapter: {workflow.get('has_websocket_adapter', False)}")
            print(f"   ✅ Has Error Handling: {workflow.get('has_error_handling', False)}")
        
        # WebSocket events analysis
        if demo_endpoint.get("event_emissions"):
            print("\n📡 WebSocket Events:")
            for event_info in demo_endpoint["event_emissions"]:
                status = "✅" if event_info["found_in_code"] else "❌"
                print(f"   {status} {event_info['event_type']}: {event_info['found_in_code']}")
        
        # SupervisorAgent analysis
        supervisor = validation["validations"]["supervisor_agent"]
        if not supervisor.get("error"):
            print("\n🧠 SupervisorAgent:")
            print(f"   ✅ Has Execute Method: {supervisor.get('has_execute_method', False)}")
            print(f"   ✅ Emits WebSocket Events: {supervisor.get('emits_websocket_events', False)}")
            print(f"   ✅ Has Orchestration Workflow: {supervisor.get('has_orchestration_workflow', False)}")
            print(f"   ✅ Creates Execution Engine: {supervisor.get('creates_execution_engine', False)}")
        
        # Recommendations
        print("\n" + "="*80)
        print("💡 RECOMMENDATIONS:")
        print("-" * 40)
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
        
        print("\n" + "="*80)
        if score >= 85:
            print("🎉 DEMO FLOW ANALYSIS: EXCELLENT")
            print("✅ The demo implementation looks solid and ready for production!")
        elif score >= 70:
            print("👍 DEMO FLOW ANALYSIS: GOOD")  
            print("⚠️  The demo has minor issues but should work for most scenarios.")
        else:
            print("⚠️ DEMO FLOW ANALYSIS: NEEDS ATTENTION")
            print("❌ Please address the critical issues before going live.")
        print("="*80)


def main():
    """Main analysis function"""
    print("🚀 Demo Flow Comprehensive Static Analysis")
    print("🎯 Validating implementation without requiring running backend")
    print()
    
    analyzer = DemoFlowAnalyzer()
    
    # Perform comprehensive validation
    validation_results = analyzer.validate_complete_flow()
    
    # Generate recommendations  
    recommendations = analyzer.generate_recommendations(validation_results)
    
    # Print detailed analysis
    analyzer.print_detailed_analysis(validation_results, recommendations)
    
    # Return appropriate exit code
    score = validation_results["overall_score"]
    critical_issues = len(validation_results["critical_issues"])
    
    if score >= 85 and critical_issues == 0:
        sys.exit(0)  # Success
    elif score >= 70 and critical_issues <= 1:
        sys.exit(1)  # Warning 
    else:
        sys.exit(2)  # Critical issues


if __name__ == "__main__":
    main()