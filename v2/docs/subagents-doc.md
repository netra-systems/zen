# SubAgents Documentation

## Overview

The Netra AI Workload Optimization Platform uses a multi-agent system with a supervisor pattern to handle complex optimization tasks. The system consists of a Supervisor agent that orchestrates specialized sub-agents, each responsible for a specific aspect of the optimization process.

## Architecture

### Supervisor Agent
- **Location**: `app/agents/supervisor.py`
- **Role**: Orchestrates the flow between sub-agents and manages the overall execution lifecycle
- **Responsibilities**:
  - Manages sub-agent execution order
  - Handles WebSocket communication for real-time updates
  - Maintains run states and lifecycle management
  - Coordinates data flow between sub-agents through DeepAgentState

### Sub-Agents

#### 1. TriageSubAgent
- **Location**: `app/agents/triage_sub_agent.py`
- **Purpose**: Analyzes incoming user requests and categorizes them for appropriate processing
- **Key Features**:
  - Categorizes requests into: Workload Analysis, Cost Optimization, Performance Optimization, Quality Optimization, Model Selection, Supply Catalog Management, Monitoring & Reporting, Configuration & Settings
  - Determines priority levels (high/medium/low)
  - Extracts key parameters and entities from user requests
  - Identifies required tools and data gathering needs

#### 2. DataSubAgent
- **Location**: `app/agents/data_sub_agent.py`
- **Purpose**: Gathers and enriches data from various sources
- **Data Sources**:
  - ClickHouse: Time-series workload event data
  - PostgreSQL: Supply catalog and configurations
  - Redis: Cached metrics and temporary state
  - Real-time monitoring systems
- **Key Features**:
  - Collects workload metrics (latency, throughput, errors, costs)
  - Analyzes usage patterns and trends
  - Detects anomalies and optimization opportunities
  - Provides data quality assessments

#### 3. OptimizationsCoreSubAgent
- **Location**: `app/agents/optimizations_core_sub_agent.py`
- **Purpose**: The "brain" of the optimization system - formulates comprehensive optimization strategies
- **Optimization Techniques**:
  - Model Routing Optimization
  - Load Balancing
  - Caching Strategies
  - Batch Processing
  - Quality Tiering
  - Cost Arbitrage
  - Predictive Scaling
  - Fallback Strategies
- **Key Features**:
  - Multi-objective optimization balancing cost, performance, and quality
  - Risk assessment and trade-off analysis
  - Implementation phasing and complexity evaluation
  - Alternative approach consideration

#### 4. ActionsToMeetGoalsSubAgent
- **Location**: `app/agents/actions_to_meet_goals_sub_agent.py`
- **Purpose**: Converts optimization strategies into concrete, executable actions
- **Action Types**:
  - Configuration Updates
  - Supply Catalog Changes
  - Routing Rule Updates
  - Monitoring Setup
  - Automation Scripts
  - API Integrations
  - Database Operations
  - Cache Management
- **Key Features**:
  - Detailed implementation steps with specific changes
  - Validation and rollback procedures
  - Risk assessments for each action
  - Cost-benefit analysis
  - Execution timeline with dependencies

#### 5. ReportingSubAgent
- **Location**: `app/agents/reporting_sub_agent.py`
- **Purpose**: Creates comprehensive, executive-ready reports
- **Report Sections**:
  - Executive Summary
  - Current State Analysis
  - Recommendations
  - Implementation Roadmap
  - Projected Outcomes
  - Risk Analysis
  - Success Metrics
  - Stakeholder Actions
- **Key Features**:
  - Multi-audience reporting (technical and non-technical)
  - ROI and impact projections
  - Success metrics and KPIs
  - Communication plans and approval workflows

## Data Flow

1. **User Request** → WebSocket → AgentService
2. **Supervisor** receives request and creates DeepAgentState
3. **TriageSubAgent** categorizes request → updates state.triage_result
4. **DataSubAgent** gathers data → updates state.data_result
5. **OptimizationsCoreSubAgent** formulates strategies → updates state.optimizations_result
6. **ActionsToMeetGoalsSubAgent** creates action plan → updates state.action_plan_result
7. **ReportingSubAgent** generates final report → updates state.report_result
8. **Supervisor** sends completed state back via WebSocket

## State Management

### DeepAgentState
- **Location**: `app/agents/state.py`
- **Fields**:
  - `user_request`: Original user request string
  - `triage_result`: Categorization and analysis from TriageSubAgent
  - `data_result`: Enriched data from DataSubAgent
  - `optimizations_result`: Strategies from OptimizationsCoreSubAgent
  - `action_plan_result`: Concrete actions from ActionsToMeetGoalsSubAgent
  - `report_result`: Final report from ReportingSubAgent
  - `final_report`: Optional consolidated report

### Lifecycle States
- **PENDING**: Agent initialized but not started
- **RUNNING**: Agent actively processing
- **COMPLETED**: Agent finished successfully
- **FAILED**: Agent encountered an error
- **SHUTDOWN**: Agent has been shut down

## WebSocket Integration

### Message Types
- `user_message`: User sends a text message with optional references
- `start_agent`: Initiates agent processing with a request model
- `stop_agent`: Requests agent termination
- `agent_started`: Notifies client that agent has started
- `sub_agent_update`: Updates on sub-agent lifecycle changes
- `sub_agent_completed`: Sub-agent has finished processing
- `agent_completed`: All processing complete with final results

### Real-time Updates
The system streams real-time updates through WebSocket including:
- Sub-agent lifecycle transitions
- Processing progress
- Intermediate results
- Error messages

## Configuration

### LLM Configuration
Each sub-agent can have its own LLM configuration specified in the LLMManager:
- `triage`: Configuration for TriageSubAgent
- `data`: Configuration for DataSubAgent
- `optimizations_core`: Configuration for OptimizationsCoreSubAgent
- `actions_to_meet_goals`: Configuration for ActionsToMeetGoalsSubAgent
- `reporting`: Configuration for ReportingSubAgent

### Tool Integration
Sub-agents have access to the ToolDispatcher for executing various tools:
- Database queries (PostgreSQL, ClickHouse)
- API calls to external services
- Cache operations (Redis)
- File system operations
- Monitoring and metrics collection

## Error Handling

- Each sub-agent includes try-catch blocks with fallback responses
- Errors are logged using CentralLogger
- Failed sub-agents don't stop the entire flow - graceful degradation
- Error messages are propagated through WebSocket to the client

## Usage Example

```python
# Initialize the supervisor with dependencies
supervisor = Supervisor(db_session, llm_manager, websocket_manager, tool_dispatcher)

# Process a user request
user_request = "Optimize my AI workload costs while maintaining 99% availability"
run_id = "unique_run_identifier"
result = await supervisor.run(user_request, run_id, stream_updates=True)

# Result contains the complete DeepAgentState with all sub-agent outputs
print(result.report_result)  # Final comprehensive report
```

## Testing

To test the complete flow:

1. Start the backend server: `python run_server.py`
2. Connect via WebSocket with authentication token
3. Send a user_message with optimization request
4. Monitor real-time updates as each sub-agent processes
5. Receive final report with recommendations and action plan

## Future Enhancements

- Additional specialized sub-agents for specific optimization scenarios
- Machine learning models for pattern recognition and prediction
- Integration with more data sources and monitoring tools
- Advanced scheduling and orchestration capabilities
- A/B testing frameworks for optimization validation