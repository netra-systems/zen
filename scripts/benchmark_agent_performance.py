#!/usr/bin/env python3
"""
Agent Performance Benchmarking System

This script measures and ranks the performance of all sub-agents in isolation.
It creates controlled test scenarios to benchmark each agent's execution speed.

Business Value Justification (BVJ):
- Segment: Enterprise, Mid
- Business Goal: Platform Stability, Development Velocity  
- Value Impact: Identifies performance bottlenecks for AI optimization
- Strategic Impact: Enables data-driven optimization of agent architecture
"""

import asyncio
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

# Add netra_backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from netra_backend.app.agents.base_sub_agent import BaseAgent
from netra_backend.app.agents.corpus_admin_sub_agent import CorpusAdminSubAgent
from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
from netra_backend.app.agents.supply_researcher_sub_agent import SupplyResearcherAgent
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.config import get_settings
from netra_backend.app.db.session import get_session_local
from netra_backend.app.services.llm_client import LLMClientInterface, get_llm_client


@dataclass
class AgentBenchmark:
    """Results for a single agent benchmark"""
    agent_name: str
    agent_type: str
    initialization_time: float
    execution_times: List[float] = field(default_factory=list)
    memory_usage: Dict[str, Any] = field(default_factory=dict)
    error_count: int = 0
    errors: List[str] = field(default_factory=list)
    test_scenarios: List[str] = field(default_factory=list)
    
    @property
    def avg_execution_time(self) -> float:
        """Average execution time across all scenarios"""
        return sum(self.execution_times) / len(self.execution_times) if self.execution_times else 0
    
    @property
    def min_execution_time(self) -> float:
        """Minimum execution time"""
        return min(self.execution_times) if self.execution_times else 0
    
    @property
    def max_execution_time(self) -> float:
        """Maximum execution time"""
        return max(self.execution_times) if self.execution_times else 0
    
    @property
    def total_time(self) -> float:
        """Total time including initialization"""
        return self.initialization_time + sum(self.execution_times)


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs"""
    iterations_per_scenario: int = 3
    warmup_iterations: int = 1
    timeout_seconds: float = 60.0  # Increased for real LLM
    measure_memory: bool = True
    verbose: bool = True


class AgentPerformanceBenchmark:
    """Main benchmarking system for agents"""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.env = IsolatedEnvironment()
        self.env.setup()
        self.settings = get_settings()
        self.results: Dict[str, AgentBenchmark] = {}
        # ALWAYS use real LLM client for accurate benchmarking
        self.llm_client = get_llm_client()
    
    def _get_test_scenarios(self, agent_type: str) -> List[Dict[str, Any]]:
        """Get test scenarios for each agent type"""
        scenarios = {
            "supervisor": [
                {
                    "name": "Simple Query Processing",
                    "input": {"query": "Analyze system performance", "thread_id": str(uuid4())}
                },
                {
                    "name": "Multi-Agent Coordination",
                    "input": {"query": "Generate report with optimization suggestions", "thread_id": str(uuid4())}
                },
                {
                    "name": "Error Recovery",
                    "input": {"query": "Process with simulated error", "thread_id": str(uuid4()), "simulate_error": True}
                }
            ],
            "corpus_admin": [
                {
                    "name": "Document Processing",
                    "input": {"action": "process_documents", "documents": ["doc1", "doc2"]}
                },
                {
                    "name": "Index Update",
                    "input": {"action": "update_index", "index_name": "test_index"}
                },
                {
                    "name": "Search Query",
                    "input": {"action": "search", "query": "test query"}
                }
            ],
            "synthetic_data": [
                {
                    "name": "Generate Small Dataset",
                    "input": {"records": 10, "schema": {"name": "string", "value": "number"}}
                },
                {
                    "name": "Generate Medium Dataset",
                    "input": {"records": 100, "schema": {"name": "string", "value": "number", "timestamp": "datetime"}}
                },
                {
                    "name": "Validation Scenario",
                    "input": {"action": "validate", "data": [{"name": "test", "value": 123}]}
                }
            ],
            "supply_researcher": [
                {
                    "name": "Market Analysis",
                    "input": {"topic": "AI infrastructure costs", "depth": "basic"}
                },
                {
                    "name": "Vendor Research",
                    "input": {"vendors": ["AWS", "GCP", "Azure"], "comparison": True}
                },
                {
                    "name": "Cost Optimization",
                    "input": {"current_spend": 10000, "optimize_for": "performance"}
                }
            ],
            "actions_to_meet_goals": [
                {
                    "name": "Goal Planning",
                    "input": {"goal": "Reduce costs by 20%", "constraints": ["maintain SLA"]}
                },
                {
                    "name": "Action Generation",
                    "input": {"objective": "Improve performance", "resources": ["team", "budget"]}
                },
                {
                    "name": "Priority Ranking",
                    "input": {"actions": ["optimize", "scale", "refactor"], "criteria": "impact"}
                }
            ],
            "optimizations_core": [
                {
                    "name": "Simple Optimization",
                    "input": {"target": "latency", "current_value": 100, "target_value": 50}
                },
                {
                    "name": "Complex Optimization",
                    "input": {"targets": ["cost", "performance"], "constraints": ["reliability > 99.9%"]}
                },
                {
                    "name": "Resource Allocation",
                    "input": {"resources": 100, "demands": [30, 40, 50], "priorities": [1, 2, 3]}
                }
            ],
            "reporting": [
                {
                    "name": "Generate Summary Report",
                    "input": {"type": "summary", "period": "daily", "metrics": ["performance", "cost"]}
                },
                {
                    "name": "Generate Detailed Report",
                    "input": {"type": "detailed", "include_charts": True, "format": "json"}
                },
                {
                    "name": "Real-time Dashboard",
                    "input": {"type": "dashboard", "refresh_rate": 5, "widgets": ["cpu", "memory", "requests"]}
                }
            ],
        }
        return scenarios.get(agent_type, [])
    
    async def benchmark_agent(self, agent_class: type, agent_type: str) -> AgentBenchmark:
        """Benchmark a single agent type"""
        benchmark = AgentBenchmark(
            agent_name=agent_class.__name__,
            agent_type=agent_type
        )
        
        if self.config.verbose:
            print(f"\n{'='*60}")
            print(f"Benchmarking: {agent_class.__name__}")
            print(f"{'='*60}")
        
        try:
            # Measure initialization time
            init_start = time.perf_counter()
            
            # Initialize agent with proper dependencies
            if agent_type == "supervisor":
                agent = agent_class(
                    llm_client=self.llm_client,
                    db_session=get_session_local(),
                    user_id="benchmark_user",
                    thread_id=str(uuid4())
                )
            else:
                agent = agent_class(llm_client=self.llm_client)
            
            benchmark.initialization_time = time.perf_counter() - init_start
            
            if self.config.verbose:
                print(f"  Initialization: {benchmark.initialization_time:.3f}s")
            
            # Get test scenarios
            scenarios = self._get_test_scenarios(agent_type)
            
            # Run warmup iterations
            if self.config.warmup_iterations > 0 and scenarios:
                if self.config.verbose:
                    print(f"  Running {self.config.warmup_iterations} warmup iterations...")
                for _ in range(self.config.warmup_iterations):
                    await self._execute_scenario(agent, scenarios[0])
            
            # Benchmark each scenario
            for scenario in scenarios:
                scenario_times = []
                
                if self.config.verbose:
                    print(f"\n  Scenario: {scenario['name']}")
                
                for iteration in range(self.config.iterations_per_scenario):
                    exec_start = time.perf_counter()
                    
                    try:
                        # Execute scenario with timeout
                        await asyncio.wait_for(
                            self._execute_scenario(agent, scenario),
                            timeout=self.config.timeout_seconds
                        )
                        exec_time = time.perf_counter() - exec_start
                        scenario_times.append(exec_time)
                        
                        if self.config.verbose:
                            print(f"    Iteration {iteration + 1}: {exec_time:.3f}s")
                    
                    except asyncio.TimeoutError:
                        error_msg = f"Timeout in {scenario['name']} (iteration {iteration + 1})"
                        benchmark.errors.append(error_msg)
                        benchmark.error_count += 1
                        if self.config.verbose:
                            print(f"    Iteration {iteration + 1}: TIMEOUT")
                    
                    except Exception as e:
                        error_msg = f"Error in {scenario['name']}: {str(e)}"
                        benchmark.errors.append(error_msg)
                        benchmark.error_count += 1
                        if self.config.verbose:
                            print(f"    Iteration {iteration + 1}: ERROR - {str(e)}")
                
                if scenario_times:
                    avg_time = sum(scenario_times) / len(scenario_times)
                    benchmark.execution_times.append(avg_time)
                    benchmark.test_scenarios.append(scenario['name'])
                    
                    if self.config.verbose:
                        print(f"    Average: {avg_time:.3f}s")
            
            # Measure memory usage if configured
            if self.config.measure_memory:
                benchmark.memory_usage = await self._measure_memory_usage(agent)
        
        except Exception as e:
            benchmark.errors.append(f"Fatal error: {str(e)}")
            benchmark.error_count += 1
            if self.config.verbose:
                print(f"  FATAL ERROR: {str(e)}")
                traceback.print_exc()
        
        return benchmark
    
    async def _execute_scenario(self, agent: BaseAgent, scenario: Dict[str, Any]) -> Any:
        """Execute a single test scenario"""
        # Different execution based on agent type
        if isinstance(agent, SupervisorAgent):
            # Supervisor has different interface
            return await agent.process_query(
                scenario['input'].get('query', 'test query'),
                scenario['input'].get('thread_id', str(uuid4()))
            )
        else:
            # Most sub-agents have execute method
            if hasattr(agent, 'execute'):
                return await agent.execute(scenario['input'])
            elif hasattr(agent, 'process'):
                return await agent.process(scenario['input'])
            else:
                # Fallback for agents with different interfaces
                return {"status": "completed", "mock": True}
    
    async def _measure_memory_usage(self, agent: Any) -> Dict[str, Any]:
        """Measure memory usage of an agent"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent()
            }
        except ImportError:
            return {"error": "psutil not installed"}
    
    async def run_benchmarks(self) -> Dict[str, AgentBenchmark]:
        """Run benchmarks for all agents"""
        agent_configs = [
            (SupervisorAgent, "supervisor"),
            (CorpusAdminSubAgent, "corpus_admin"),
            (SyntheticDataSubAgent, "synthetic_data"),
            (SupplyResearcherAgent, "supply_researcher"),
            (ActionsToMeetGoalsSubAgent, "actions_to_meet_goals"),
            (OptimizationsCoreSubAgent, "optimizations_core"),
            (ReportingSubAgent, "reporting"),
        ]
        
        print("\n" + "="*80)
        print("NETRA APEX AI - AGENT PERFORMANCE BENCHMARK")
        print("="*80)
        print(f"Configuration:")
        print(f"  - LLM Mode: REAL LLM (Production)")
        print(f"  - Iterations: {self.config.iterations_per_scenario}")
        print(f"  - Warmup: {self.config.warmup_iterations}")
        print(f"  - Timeout: {self.config.timeout_seconds}s")
        print(f"  - Memory Tracking: {self.config.measure_memory}")
        
        for agent_class, agent_type in agent_configs:
            try:
                benchmark = await self.benchmark_agent(agent_class, agent_type)
                self.results[agent_type] = benchmark
            except Exception as e:
                print(f"\nFailed to benchmark {agent_class.__name__}: {str(e)}")
                self.results[agent_type] = AgentBenchmark(
                    agent_name=agent_class.__name__,
                    agent_type=agent_type,
                    initialization_time=0,
                    errors=[f"Benchmark failed: {str(e)}"],
                    error_count=1
                )
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate performance report with rankings"""
        if not self.results:
            return "No benchmark results available"
        
        # Create rankings
        rankings = []
        for agent_type, benchmark in self.results.items():
            if benchmark.execution_times:
                rankings.append({
                    "agent": benchmark.agent_name,
                    "type": agent_type,
                    "avg_time": benchmark.avg_execution_time,
                    "min_time": benchmark.min_execution_time,
                    "max_time": benchmark.max_execution_time,
                    "init_time": benchmark.initialization_time,
                    "total_time": benchmark.total_time,
                    "scenarios": len(benchmark.test_scenarios),
                    "errors": benchmark.error_count
                })
        
        # Sort by average execution time
        rankings.sort(key=lambda x: x['avg_time'])
        
        # Generate report
        report = []
        report.append("\n" + "="*80)
        report.append("AGENT PERFORMANCE BENCHMARK REPORT")
        report.append("="*80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Performance Rankings
        report.append("\n CHART:  PERFORMANCE RANKINGS (by average execution time)")
        report.append("-" * 60)
        
        for rank, data in enumerate(rankings, 1):
            medal = "[U+1F947]" if rank == 1 else "[U+1F948]" if rank == 2 else "[U+1F949]" if rank == 3 else f"{rank}."
            report.append(f"\n{medal} {data['agent']}")
            report.append(f"   Type: {data['type']}")
            report.append(f"   Avg Time: {data['avg_time']:.3f}s")
            report.append(f"   Min/Max: {data['min_time']:.3f}s / {data['max_time']:.3f}s")
            report.append(f"   Init Time: {data['init_time']:.3f}s")
            report.append(f"   Total Time: {data['total_time']:.3f}s")
            report.append(f"   Scenarios: {data['scenarios']}")
            if data['errors'] > 0:
                report.append(f"    WARNING: [U+FE0F] Errors: {data['errors']}")
        
        # Detailed Results
        report.append("\n\n" + "="*60)
        report.append("DETAILED RESULTS")
        report.append("="*60)
        
        for agent_type, benchmark in self.results.items():
            report.append(f"\n### {benchmark.agent_name} ({agent_type})")
            report.append("-" * 40)
            
            if benchmark.test_scenarios:
                report.append("Scenarios Tested:")
                for i, scenario in enumerate(benchmark.test_scenarios):
                    exec_time = benchmark.execution_times[i] if i < len(benchmark.execution_times) else 0
                    report.append(f"  [U+2022] {scenario}: {exec_time:.3f}s")
            
            if benchmark.memory_usage and "error" not in benchmark.memory_usage:
                report.append("\nMemory Usage:")
                report.append(f"  [U+2022] RSS: {benchmark.memory_usage.get('rss_mb', 0):.1f} MB")
                report.append(f"  [U+2022] VMS: {benchmark.memory_usage.get('vms_mb', 0):.1f} MB")
                report.append(f"  [U+2022] Percent: {benchmark.memory_usage.get('percent', 0):.1f}%")
            
            if benchmark.errors:
                report.append("\n WARNING: [U+FE0F] Errors Encountered:")
                for error in benchmark.errors[:5]:  # Show first 5 errors
                    report.append(f"  [U+2022] {error}")
                if len(benchmark.errors) > 5:
                    report.append(f"  [U+2022] ... and {len(benchmark.errors) - 5} more")
        
        # Summary Statistics
        report.append("\n\n" + "="*60)
        report.append("SUMMARY STATISTICS")
        report.append("="*60)
        
        total_scenarios = sum(len(b.test_scenarios) for b in self.results.values())
        total_errors = sum(b.error_count for b in self.results.values())
        avg_init_time = sum(b.initialization_time for b in self.results.values()) / len(self.results)
        
        report.append(f"\nTotal Agents Tested: {len(self.results)}")
        report.append(f"Total Scenarios Run: {total_scenarios}")
        report.append(f"Total Errors: {total_errors}")
        report.append(f"Average Init Time: {avg_init_time:.3f}s")
        
        if rankings:
            fastest = rankings[0]
            slowest = rankings[-1]
            report.append(f"\n[U+1F680] Fastest Agent: {fastest['agent']} ({fastest['avg_time']:.3f}s avg)")
            report.append(f"[U+1F40C] Slowest Agent: {slowest['agent']} ({slowest['avg_time']:.3f}s avg)")
            report.append(f" LIGHTNING:  Speed Difference: {(slowest['avg_time'] / fastest['avg_time']):.1f}x")
        
        return "\n".join(report)
    
    def save_results(self, output_dir: Path = None):
        """Save benchmark results to files"""
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "benchmark_results"
        
        output_dir.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON data
        json_file = output_dir / f"agent_benchmarks_{timestamp}.json"
        json_data = {}
        for agent_type, benchmark in self.results.items():
            json_data[agent_type] = {
                "agent_name": benchmark.agent_name,
                "initialization_time": benchmark.initialization_time,
                "execution_times": benchmark.execution_times,
                "avg_execution_time": benchmark.avg_execution_time,
                "min_execution_time": benchmark.min_execution_time,
                "max_execution_time": benchmark.max_execution_time,
                "total_time": benchmark.total_time,
                "memory_usage": benchmark.memory_usage,
                "test_scenarios": benchmark.test_scenarios,
                "error_count": benchmark.error_count,
                "errors": benchmark.errors
            }
        
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        # Save text report
        report_file = output_dir / f"agent_performance_report_{timestamp}.md"
        with open(report_file, 'w') as f:
            f.write(self.generate_report())
        
        print(f"\n PASS:  Results saved to:")
        print(f"  [U+2022] JSON: {json_file}")
        print(f"  [U+2022] Report: {report_file}")
        
        return json_file, report_file


async def main():
    """Main entry point"""
    # Configure benchmark with REAL LLM
    config = BenchmarkConfig(
        iterations_per_scenario=2,  # Reduced for real LLM to save time/cost
        warmup_iterations=0,  # Skip warmup for real LLM
        timeout_seconds=60.0,  # Increased timeout for real LLM responses
        measure_memory=True,
        verbose=True
    )
    
    # Run benchmarks
    benchmark = AgentPerformanceBenchmark(config)
    results = await benchmark.run_benchmarks()
    
    # Generate and display report
    report = benchmark.generate_report()
    print(report)
    
    # Save results
    benchmark.save_results()


if __name__ == "__main__":
    asyncio.run(main())