"""
Agent Startup Test Handler - Specialized E2E test execution and performance tracking

Business Value Justification (BVJ):
1. Segment: ALL customer segments (Free, Early, Mid, Enterprise)  
2. Business Goal: Protect 100% of agent functionality revenue
3. Value Impact: Prevents agent initialization failures that block user interactions
4. Revenue Impact: Protects entire $200K+ MRR by ensuring reliable cold start process

Architectural Compliance:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY) 
- Modular design for agent startup testing
- Performance tracking and reporting
"""

import re
import time
from typing import Dict, List, Optional, Tuple


class AgentStartupTestHandler:
    """Handles agent startup E2E tests with performance tracking."""
    
    def __init__(self):
        """Initialize agent startup test handler."""
        self.performance_metrics = self._init_performance_structure()
    
    def _init_performance_structure(self) -> Dict:
        """Initialize performance metrics structure."""
        return {
            'cold_start_time': None,
            'first_response_time': None,
            'connection_establishment_time': None,
            'agent_coordination_time': None
        }
    
    def execute_agent_startup_tests(self, args, config: Dict, runner, real_llm_config: Optional[Dict], speed_opts: Optional[Dict]) -> int:
        """Execute agent startup E2E tests with performance tracking."""
        self._print_startup_header()
        self._setup_performance_tracking(runner)
        return self._run_tests_with_tracking(config, runner, real_llm_config, speed_opts)
    
    def _print_startup_header(self):
        """Print agent startup test header."""
        print("\n" + "=" * 80)
        print("AGENT STARTUP E2E TESTS - Real Services & Performance Tracking")
        print("=" * 80)
        print("[INFO] Running comprehensive agent cold start validation")
        print("[INFO] Testing: Agent initialization, WebSocket connections, real LLM integration")
    
    def _setup_performance_tracking(self, runner):
        """Setup performance tracking in runner results."""
        if not hasattr(runner.results, 'agent_performance'):
            runner.results['agent_performance'] = self.performance_metrics.copy()
    
    def _run_tests_with_tracking(self, config: Dict, runner, real_llm_config: Optional[Dict], speed_opts: Optional[Dict]) -> int:
        """Run tests with performance tracking."""
        start_time = time.time()
        backend_exit, output = runner.run_backend_tests(
            config['backend_args'],
            config.get('timeout', 300),
            real_llm_config,
            speed_opts
        )
        
        self._process_test_results(runner, output, start_time)
        return backend_exit
    
    def _process_test_results(self, runner, output: str, start_time: float):
        """Process test results and extract performance metrics."""
        # Use the performance analyzer to extract metrics
        analyzer = AgentPerformanceAnalyzer()
        analyzer.extract_performance_metrics(output, runner.results)
        runner.results['agent_performance']['total_e2e_duration'] = time.time() - start_time
        duration = runner.results['agent_performance']['total_e2e_duration']
        print(f"\n[PERFORMANCE] Agent startup E2E completed in {duration:.2f}s")


class AgentPerformanceAnalyzer:
    """Analyzes and extracts agent performance metrics."""
    
    def extract_performance_metrics(self, output: str, results: Dict):
        """Extract performance metrics from agent startup test output."""
        if not output or 'agent_performance' not in results:
            return
        
        # Extract all performance metrics using regex patterns
        self._extract_cold_start_time(output, results)
        self._extract_first_response_time(output, results)
        self._extract_connection_time(output, results)
        self._extract_coordination_time(output, results)
    
    def _extract_cold_start_time(self, output: str, results: Dict):
        """Extract cold start time from test output."""
        match = re.search(r'Cold start completed in (\d+\.?\d*)s', output)
        if match:
            results['agent_performance']['cold_start_time'] = float(match.group(1))
    
    def _extract_first_response_time(self, output: str, results: Dict):
        """Extract first response time from test output."""
        match = re.search(r'First agent response in (\d+\.?\d*)s', output)
        if match:
            results['agent_performance']['first_response_time'] = float(match.group(1))
    
    def _extract_connection_time(self, output: str, results: Dict):
        """Extract connection establishment time from test output."""
        match = re.search(r'WebSocket connection established in (\d+\.?\d*)s', output)
        if match:
            results['agent_performance']['connection_establishment_time'] = float(match.group(1))
    
    def _extract_coordination_time(self, output: str, results: Dict):
        """Extract agent coordination time from test output."""
        match = re.search(r'Agent coordination completed in (\d+\.?\d*)s', output)
        if match:
            results['agent_performance']['agent_coordination_time'] = float(match.group(1))


class AgentPerformanceSummaryReporter:
    """Reports agent performance summary and assessments."""
    
    def print_performance_summary(self, performance_metrics: Dict):
        """Print detailed agent performance summary."""
        self._print_summary_header()
        self._print_performance_metrics(performance_metrics)
        self._print_performance_assessment(performance_metrics)
        self._print_summary_footer()
    
    def _print_summary_header(self):
        """Print performance summary header."""
        print("\n" + "=" * 80)
        print("AGENT PERFORMANCE SUMMARY")
        print("=" * 80)
    
    def _print_performance_metrics(self, performance_metrics: Dict):
        """Print individual performance metrics."""
        total_duration = performance_metrics.get('total_e2e_duration')
        if total_duration:
            print(f"Total E2E Test Duration:        {total_duration:.3f}s")
        
        self._print_optional_metric(performance_metrics, 'cold_start_time', 'Cold Start Time:')
        self._print_optional_metric(performance_metrics, 'first_response_time', 'First Agent Response:')
        self._print_optional_metric(performance_metrics, 'connection_establishment_time', 'WebSocket Connection:')
        self._print_optional_metric(performance_metrics, 'agent_coordination_time', 'Agent Coordination:')
    
    def _print_optional_metric(self, metrics: Dict, key: str, label: str):
        """Print optional metric if available."""
        value = metrics.get(key)
        if value:
            print(f"{label:<31} {value:.3f}s")
    
    def _print_performance_assessment(self, performance_metrics: Dict):
        """Print performance assessment based on duration."""
        print("\nPERFORMANCE ASSESSMENT:")
        total_duration = performance_metrics.get('total_e2e_duration')
        if not total_duration:
            return
            
        if total_duration < 30:
            print("[U+2713] EXCELLENT - Total duration under 30s")
        elif total_duration < 60:
            print("[U+2713] GOOD - Total duration under 60s")
        elif total_duration < 120:
            print(f" WARNING:  ACCEPTABLE - Duration {total_duration:.1f}s (consider optimization)")
        else:
            print(f"[U+2717] NEEDS OPTIMIZATION - Duration {total_duration:.1f}s exceeds target")
    
    def _print_summary_footer(self):
        """Print performance summary footer."""
        print("=" * 80)


# Create singleton instances for easy access
agent_startup_handler = AgentStartupTestHandler()
performance_analyzer = AgentPerformanceAnalyzer()
performance_reporter = AgentPerformanceSummaryReporter()


def execute_agent_startup_tests(args, config: Dict, runner, real_llm_config: Optional[Dict], speed_opts: Optional[Dict]) -> int:
    """Main entry point for agent startup test execution."""
    return agent_startup_handler.execute_agent_startup_tests(args, config, runner, real_llm_config, speed_opts)

def extract_agent_performance_metrics(output: str, results: Dict):
    """Extract performance metrics from test output."""
    return performance_analyzer.extract_performance_metrics(output, results)

def print_agent_performance_summary(performance_metrics: Dict):
    """Print agent performance summary."""
    return performance_reporter.print_performance_summary(performance_metrics)