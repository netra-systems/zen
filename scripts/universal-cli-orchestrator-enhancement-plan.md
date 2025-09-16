# Universal CLI Orchestrator Enhancement Plan

## Overview

This plan enhances the existing `claude-instance-orchestrator.py` to support:
1. **Single Instance Mode**: Run individual CLI commands (including `scripts/claude`)
2. **Universal CLI Support**: Execute ANY command-line tool (Claude, OpenAI, Docker, etc.)
3. **Dependent Command Chaining**: Conditional execution with graph-based logic

## Current State Analysis

### Existing Architecture Strengths
- ✅ **JSON Token Parsing**: Modern stream-json support with fallback regex
- ✅ **Async Processing**: Efficient parallel execution with staggered startup
- ✅ **Database Integration**: CloudSQL metrics storage via NetraOptimizer
- ✅ **Real-time Monitoring**: Rolling status reports and WebSocket-style formatting
- ✅ **Mac Compatibility**: Auto-detection of Claude executable paths
- ✅ **Comprehensive Metrics**: Token usage, cost calculation, cache hit rates

### Current Limitations
- ❌ **Claude-Only**: Hardcoded for Claude Code slash commands
- ❌ **No Single Mode**: Can't run one-off commands
- ❌ **No Dependencies**: Commands run independently in parallel
- ❌ **Limited CLI Support**: No support for other AI tools (OpenAI, Anthropic API, etc.)

## Enhancement Architecture

### Core Design Principles
1. **Backward Compatibility**: Existing configs continue to work unchanged
2. **Progressive Enhancement**: Add features without breaking current functionality
3. **Universal Abstraction**: Abstract CLI execution from specific tools
4. **Dependency Management**: Graph-based execution with conditional logic
5. **Metric Standardization**: Common metrics format across all CLI tools

## Feature Implementation Plan

### Phase 1: Universal CLI Foundation (Week 1-2)

#### 1.1 Generic Command Abstraction
```python
@dataclass
class UniversalCommandConfig:
    """Universal command configuration supporting any CLI tool"""
    command: str                    # Full command (e.g., "openai api chat.completions.create")
    name: Optional[str] = None      # Display name
    tool_type: str = "generic"      # claude, openai, docker, generic
    working_dir: Optional[str] = None
    environment: Dict[str, str] = None
    timeout: int = 300

    # Execution options
    capture_output: bool = True
    stream_output: bool = False
    shell: bool = False

    # Metrics and parsing
    metrics_parser: Optional[str] = None  # "claude_json", "openai_json", "custom"
    success_patterns: List[str] = None    # Regex patterns for success detection
    failure_patterns: List[str] = None    # Regex patterns for failure detection
```

#### 1.2 CLI Tool Registry
```python
class CLIToolRegistry:
    """Registry of supported CLI tools with their specific configurations"""

    SUPPORTED_TOOLS = {
        "claude": {
            "executable_paths": ["/opt/homebrew/bin/claude", "claude.exe", "claude"],
            "default_args": ["--output-format=stream-json", "--verbose"],
            "metrics_parser": "claude_json",
            "cost_calculator": "claude_pricing"
        },
        "openai": {
            "executable_paths": ["openai"],
            "metrics_parser": "openai_json",
            "cost_calculator": "openai_pricing"
        },
        "docker": {
            "executable_paths": ["docker"],
            "metrics_parser": "generic"
        }
    }
```

#### 1.3 Single Instance Mode
Add command-line flag for single execution:
```bash
# Single Claude command
python claude-instance-orchestrator.py --single --command "/gitcommitgardener"

# Single OpenAI command
python claude-instance-orchestrator.py --single --tool openai --command "api chat.completions.create -m gpt-4"

# Generic command
python claude-instance-orchestrator.py --single --command "docker ps -a"
```

### Phase 2: Dependency Chain Engine (Week 3-4)

#### 2.1 Dependency Graph Definition
```python
@dataclass
class CommandDependency:
    """Defines conditional relationships between commands"""
    depends_on: List[str]           # Command names this depends on
    condition: str = "success"      # success, failure, always, custom
    custom_condition: Optional[str] = None  # Python expression for custom logic
    delay: float = 0.0             # Delay before execution (seconds)

@dataclass
class EnhancedCommandConfig(UniversalCommandConfig):
    """Extended config with dependency support"""
    dependencies: Optional[CommandDependency] = None
    priority: int = 0               # Execution priority (higher = earlier)
    retry_count: int = 0           # Number of retries on failure
    retry_delay: float = 1.0       # Delay between retries
```

#### 2.2 Graph Execution Engine
```python
class DependencyGraphExecutor:
    """Executes commands based on dependency graph"""

    async def build_execution_graph(self, commands: List[EnhancedCommandConfig]) -> nx.DiGraph:
        """Build directed graph from command dependencies"""

    async def execute_with_dependencies(self) -> Dict[str, bool]:
        """Execute commands respecting dependency constraints"""

    def validate_graph(self) -> List[str]:
        """Validate no circular dependencies exist"""
```

#### 2.3 Enhanced Configuration Format
```json
{
  "execution_mode": "dependency_graph",
  "commands": [
    {
      "name": "setup-env",
      "command": "docker-compose up -d postgres redis",
      "tool_type": "docker",
      "priority": 100
    },
    {
      "name": "run-tests",
      "command": "/test-real unit",
      "tool_type": "claude",
      "dependencies": {
        "depends_on": ["setup-env"],
        "condition": "success"
      }
    },
    {
      "name": "deploy-staging",
      "command": "/deploy-gcp staging",
      "tool_type": "claude",
      "dependencies": {
        "depends_on": ["run-tests"],
        "condition": "success"
      }
    },
    {
      "name": "cleanup",
      "command": "docker-compose down",
      "tool_type": "docker",
      "dependencies": {
        "depends_on": ["deploy-staging"],
        "condition": "always"
      }
    }
  ]
}
```

### Phase 3: Advanced Logic & Integrations (Week 5-6)

#### 3.1 Conditional Logic Engine
```python
class ConditionalLogicEngine:
    """Supports complex conditional execution logic"""

    def evaluate_condition(self, condition: str, context: Dict) -> bool:
        """Evaluate Python expression in secure sandbox"""
        # Examples:
        # "success and tokens_used < 10000"
        # "failure or (success and cost < 5.0)"
        # "exit_code == 0 and 'PASS' in output"
```

#### 3.2 Multi-Tool Pipelines
```yaml
# Example: AI-powered development pipeline
pipeline:
  - name: "analyze-code"
    tool: "claude"
    command: "/analyze src/"
    capture_output: true

  - name: "generate-tests"
    tool: "openai"
    command: "api chat.completions.create -m gpt-4 --input '{{analyze-code.output}}'"
    dependencies:
      depends_on: ["analyze-code"]
      condition: "success and 'analysis complete' in output"

  - name: "run-tests"
    tool: "generic"
    command: "pytest tests/"
    dependencies:
      depends_on: ["generate-tests"]

  - name: "deploy"
    tool: "claude"
    command: "/deploy-gcp staging"
    dependencies:
      depends_on: ["run-tests"]
      condition: "exit_code == 0"
```

#### 3.3 Integration with Existing Scripts
Integrate with current `scripts/claude` wrapper:
```python
# Enhanced orchestrator detects and uses existing wrapper
if Path("scripts/claude").exists():
    claude_command = "scripts/claude"  # Use wrapper for metrics
else:
    claude_command = find_claude_executable()  # Direct execution
```

## Implementation Timeline

### Week 1: Foundation
- [ ] Create `UniversalCommandConfig` and base abstractions
- [ ] Implement `CLIToolRegistry` with Claude, OpenAI, Docker support
- [ ] Add `--single` mode for one-off executions
- [ ] Update argument parsing and help text

### Week 2: Single Mode Polish
- [ ] Implement metrics parsing for different CLI tools
- [ ] Add cost calculation for OpenAI API calls
- [ ] Test single mode with various tools
- [ ] Maintain backward compatibility with existing configs

### Week 3: Dependency Foundation
- [ ] Design and implement `CommandDependency` structure
- [ ] Create `DependencyGraphExecutor` class
- [ ] Implement basic dependency resolution (success/failure conditions)
- [ ] Add graph validation (circular dependency detection)

### Week 4: Advanced Dependencies
- [ ] Implement conditional logic engine
- [ ] Add support for complex condition expressions
- [ ] Implement retry mechanisms and failure handling
- [ ] Add priority-based execution ordering

### Week 5: Integration & Testing
- [ ] Integrate with existing `scripts/claude` wrapper
- [ ] Add YAML configuration support
- [ ] Create comprehensive test suite
- [ ] Update documentation and examples

### Week 6: Polish & Performance
- [ ] Optimize graph execution performance
- [ ] Add advanced monitoring and debugging
- [ ] Create migration guide for existing users
- [ ] Performance benchmarking and optimization

## Configuration Examples

### Single Execution
```bash
# Run one Claude command
python universal-orchestrator.py --single --tool claude --command "/gitcommitgardener"

# Run OpenAI API call
python universal-orchestrator.py --single --tool openai \
  --command "api chat.completions.create -m gpt-4 --messages '[{\"role\":\"user\",\"content\":\"Hello\"}]'"

# Run generic command
python universal-orchestrator.py --single --command "docker ps -a"
```

### Parallel Execution (Current)
```json
{
  "execution_mode": "parallel",
  "instances": [
    {"command": "/gitcommitgardener", "tool_type": "claude"},
    {"command": "/ssotgardener", "tool_type": "claude"}
  ]
}
```

### Dependency Chain
```json
{
  "execution_mode": "dependency_graph",
  "commands": [
    {
      "name": "build",
      "command": "npm run build",
      "tool_type": "generic"
    },
    {
      "name": "test",
      "command": "/test-real unit",
      "tool_type": "claude",
      "dependencies": {
        "depends_on": ["build"],
        "condition": "success"
      }
    }
  ]
}
```

## Backward Compatibility

### Existing Configs Continue Working
- Current JSON format remains fully supported
- `InstanceConfig` becomes alias for `UniversalCommandConfig`
- Default `tool_type: "claude"` for unspecified tools
- All current command-line arguments preserved

### Migration Path
1. **Phase 1**: Existing users see no changes
2. **Phase 2**: Optional new features available
3. **Phase 3**: Gradual migration to new config format
4. **Documentation**: Clear migration examples and benefits

## Benefits

### For Current Users
- ✅ **Zero Breaking Changes**: Existing workflows continue unchanged
- ✅ **Enhanced Capabilities**: Add dependency logic to existing flows
- ✅ **Better Debugging**: Improved error handling and reporting

### For New Use Cases
- ✅ **Universal Tool Support**: OpenAI, Docker, npm, any CLI tool
- ✅ **Complex Workflows**: Multi-stage pipelines with conditional logic
- ✅ **Single Command Mode**: Simple one-off executions
- ✅ **Cross-Tool Integration**: Chain different AI tools together

### For Development Teams
- ✅ **Standardized Metrics**: Common format across all tools
- ✅ **Cost Tracking**: Unified cost tracking for all AI services
- ✅ **Workflow Automation**: Complex CI/CD pipeline support
- ✅ **Debugging**: Enhanced logging and dependency visualization

## Risk Mitigation

### Compatibility Risks
- **Mitigation**: Comprehensive backward compatibility testing
- **Fallback**: Version pinning for critical production workflows

### Performance Risks
- **Mitigation**: Lazy loading of dependency features
- **Optimization**: Graph execution algorithms optimized for common cases

### Complexity Risks
- **Mitigation**: Progressive disclosure - advanced features optional
- **Documentation**: Clear examples from simple to complex

## Success Metrics

### Technical Metrics
- [ ] 100% backward compatibility maintained
- [ ] <100ms overhead for single command execution
- [ ] Support for 5+ CLI tools (Claude, OpenAI, Docker, npm, generic)
- [ ] Dependency graphs up to 50 nodes execute efficiently

### User Adoption Metrics
- [ ] Existing users migrate smoothly (0 reported breaking changes)
- [ ] New single-mode usage (target: 25% of executions)
- [ ] Dependency chain usage (target: 10% of workflows)
- [ ] Cross-tool integration examples (target: 3+ documented patterns)

## Future Extensibility

### Planned Enhancements
- **Web UI**: Visual dependency graph editor
- **Plugin System**: Custom tool integrations
- **Cloud Execution**: Distributed orchestration
- **Scheduling**: Cron-like recurring executions

This enhancement plan transforms the Claude-specific orchestrator into a universal CLI automation platform while preserving all existing functionality and patterns.