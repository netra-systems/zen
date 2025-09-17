# Netra Orchestrator Client - Documentation Index

> **Service Overview**: Standalone orchestration service for managing multiple Claude Code instances with advanced scheduling, monitoring, and metrics collection.

**Service Version**: 1.0.0
**Last Updated**: 2025-09-15
**Maintainer**: Netra Systems

## 🚀 Quick Navigation

### Essential Starting Points
- **[Service README](README.md)** 📖 - Service overview, quick start, and basic usage
- **[Core Orchestrator](claude_instance_orchestrator.py)** ⚙️ - Main service implementation
- **[Configuration Example](config_example.json)** ⚙️ - Sample configuration template
- **[Test Suite](tests/)** 🧪 - Complete test infrastructure
- **[Navigation Guide](docs/NAVIGATION.md)** 🧭 - Cross-service navigation hub

### Main Documentation Hub
- **[Main Netra Documentation](../docs/index.md)** 🏠 - Return to main project documentation
- **[COMMAND_INDEX.md](../docs/COMMAND_INDEX.md)** 📋 - Master command reference
- **[SSOT Import Registry](../SSOT_IMPORT_REGISTRY.md)** 📋 - Import mappings

---

## 📁 Service Structure

### Core Service Files
| File | Purpose | Documentation |
|------|---------|---------------|
| [`claude_instance_orchestrator.py`](claude_instance_orchestrator.py) | Main orchestrator service | [Enhancement Plan](docs/claude-instance-orchestrator-enhancement-plan.md) |
| [`config_example.json`](config_example.json) | Configuration template | [README](README.md#configuration) |
| [`__init__.py`](__init__.py) | Python package definition | [Setup Guide](setup.py) |
| [`setup.py`](setup.py) | Package installation script | [Requirements](requirements.txt) |
| [`requirements.txt`](requirements.txt) | Core dependencies | [Dev Requirements](requirements-dev.txt) |

### Documentation Library
| Document | Focus Area | Related Docs |
|----------|------------|--------------|
| **[TESTING.md](docs/TESTING.md)** | Test execution guide | [Test Runner](tests/test_runner.py) |
| **[Enhancement Plan](docs/claude-instance-orchestrator-enhancement-plan.md)** | Service roadmap | [Token Budget Plan](docs/claude-instance-orchestrator-token-budget-codex-plan.md) |
| **[Deployment Strategy](docs/claude-orchestrator-deployment-strategy-plan.md)** | Production deployment | [CloudSQL Integration](../scripts/ORCHESTRATOR_CLOUDSQL_INTEGRATION.md) |
| **[README-orchestrator.md](docs/README-orchestrator.md)** | Detailed service guide | [Modernization Summary](docs/claude-orchestrator-modernization-summary.md) |
| **[Universal CLI Plan](docs/universal-cli-orchestrator-enhancement-plan.md)** | CLI enhancement strategy | [Main README](README.md) |

### Test Infrastructure
| Test File | Coverage Area | Documentation |
|-----------|---------------|---------------|
| **[test_runner.py](tests/test_runner.py)** | Test execution coordination | [TESTING.md](docs/TESTING.md) |
| **[Unit Tests](tests/test_claude_instance_orchestrator_unit.py)** | Core functionality | [Service README](README.md#testing) |
| **[Command Tests](tests/test_claude_instance_orchestrator_commands.py)** | Command discovery/validation | [Enhancement Plan](docs/claude-instance-orchestrator-enhancement-plan.md) |
| **[Metrics Tests](tests/test_claude_instance_orchestrator_metrics.py)** | Token parsing/metrics | [Token Budget Plan](docs/claude-instance-orchestrator-token-budget-codex-plan.md) |
| **[Integration Tests](tests/test_claude_instance_orchestrator_integration.py)** | End-to-end workflows | [Deployment Strategy](docs/claude-orchestrator-deployment-strategy-plan.md) |

---

## 🔗 Cross-Service Integration

### Main Project Integration
- **[Main Backend](../netra_backend/)** - Primary Netra system
- **[Auth Service](../auth_service/)** - Authentication service
- **[Frontend](../frontend/)** - User interface
- **[Shared Libraries](../shared/)** - Common utilities

### External Dependencies
- **Claude Code CLI** - Required for orchestration
- **[NetraOptimizer](../netraoptimizer/)** - Optional CloudSQL integration
- **Python 3.8+** - Runtime requirement

---

## 🎯 Service Capabilities

### Core Features
- **Multi-Instance Management** - Parallel Claude Code execution
- **Advanced Scheduling** - Flexible timing and delay options
- **Real-Time Monitoring** - Status reporting and progress tracking
- **Metrics Collection** - Token usage and performance analytics
- **CloudSQL Integration** - Optional database persistence

### Supported Operations
- **Parallel Execution** - Run multiple instances concurrently
- **Command Discovery** - Auto-detect available slash commands
- **Session Management** - Handle Claude Code sessions
- **Error Handling** - Robust failure recovery
- **Result Aggregation** - Combine outputs and metrics

---

## 📊 Usage Patterns

### Development Workflows
```bash
# Quick development test
python claude_instance_orchestrator.py --dry-run --workspace ~/project

# Scheduled execution
python claude_instance_orchestrator.py --start-at "2h" --workspace ~/project

# CloudSQL metrics tracking
python claude_instance_orchestrator.py --use-cloud-sql --workspace ~/project
```

### Testing Workflows
```bash
# Run all tests
cd tests && python test_runner.py

# Run specific test category
python test_runner.py unit
python test_runner.py integration
```

### Production Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Production run with custom config
python claude_instance_orchestrator.py --config production_config.json --workspace /app
```

---

## 🔧 Configuration Reference

### Environment Variables
- `NETRA_DB_PORT` - Database port (optional)
- `NETRA_DB_USER` - Database user (optional)
- `POSTGRES_*` - PostgreSQL connection settings
- `ENVIRONMENT` - Environment designation

### Configuration Files
- **[config_example.json](config_example.json)** - Template configuration
- **[requirements.txt](requirements.txt)** - Python dependencies
- **[setup.py](setup.py)** - Package configuration

---

## 🚨 Critical Information

### Service Independence
⚠️ **This service is completely independent** from the main Netra backend and can be deployed separately.

### SSOT Compliance
✅ **Single Source of Truth** - This service follows SSOT principles for orchestration functionality.

### Business Impact
💰 **High Value** - Orchestration enables parallel execution for faster development cycles.

---

## 🔄 Service Maintenance

### Regular Tasks
- Monitor test suite health
- Update dependencies
- Review configuration templates
- Validate cross-service integration

### Documentation Updates
- Keep INDEX.md current with new features
- Update cross-references when services change
- Maintain test documentation
- Review and update README files

---

## 📞 Support & References

### Internal Documentation
- **[Main Documentation Hub](../docs/index.md)** - Project-wide documentation
- **[Architecture Guides](../reports/)** - System architecture
- **[SSOT Standards](../CLAUDE.md)** - Development standards

### External Resources
- **Claude Code Documentation** - CLI usage and commands
- **Python AsyncIO** - Asynchronous programming patterns
- **NetraOptimizer** - Database integration library

---

**🏠 [Return to Main Documentation](../docs/index.md) | 📋 [View All Commands](../docs/COMMAND_INDEX.md) | 🚀 [Get Started](README.md)**