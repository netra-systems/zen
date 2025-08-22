# 📚 Index of Indexes - Master Navigation Hub

> **The single source of truth for all documentation, specifications, and navigation indexes in the Netra Apex platform**

## 🎯 Primary Navigation Indexes

### Core Development Indexes
| Index | Purpose | Key Contents |
|-------|---------|--------------|
| **[LLM_MASTER_INDEX.md](LLM_MASTER_INDEX.md)** | Complete file navigation index | Service architecture, component mapping, agent system docs |
| **[CLAUDE.md](CLAUDE.md)** | Principal engineering philosophy | AI factory patterns, BVJ methodology, development principles |
| **[README.md](README.md)** | Project overview & quick start | Installation, features, developer guidelines |

### System Status & Compliance
| Index | Purpose | Key Contents |
|-------|---------|--------------|
| **[MASTER_WIP_STATUS.md](MASTER_WIP_STATUS.md)** | Real-time system health metrics | Compliance scores, critical violations, action items |
| **[SPEC/master_wip_index.xml](SPEC/master_wip_index.xml)** | WIP scoring methodology | Process definitions, scoring criteria |

### Testing & Quality Indexes
| Index | Purpose | Key Contents |
|-------|---------|--------------|
| **[MASTER_TEST_INDEX.md](MASTER_TEST_INDEX.md)** | Comprehensive test documentation | Test categories, coverage metrics, test plans |
| **[TESTING.md](TESTING.md)** | Testing guide & unified runner | Test levels, execution commands, best practices |
| **[tests/test_reports/TEST_INDEX.md](tests/test_reports/TEST_INDEX.md)** | Test execution reports | Latest test results, failure analysis |

### Deployment & Operations
| Index | Purpose | Key Contents |
|-------|---------|--------------|
| **[DEPLOYMENT_INDEX.md](DEPLOYMENT_INDEX.md)** | Deployment documentation | GCP staging, production deployment, CI/CD pipelines |
| **[TOOLING_INDEX.md](TOOLING_INDEX.md)** | AI Native centric tools | Development tools, automation scripts, utilities |

## 📋 Specification Indexes

### Core Specifications
| Spec Index | Purpose | Priority |
|------------|---------|----------|
| **[SPEC/learnings/index.xml](SPEC/learnings/index.xml)** | Index of all system learnings | ALWAYS check first |
| **[SPEC/string_literals_index.xml](SPEC/string_literals_index.xml)** | Platform constants index (35,000+ entries) | Before using any string literal |
| **[SPEC/generated/string_literals.json](SPEC/generated/string_literals.json)** | Generated string literals database | Auto-generated index |

### Architecture & Compliance
| Document | Purpose | When to Check |
|----------|---------|---------------|
| **[SPEC/type_safety.xml](SPEC/type_safety.xml)** | Type safety, duplication-free code | BEFORE any code |
| **[SPEC/conventions.xml](SPEC/conventions.xml)** | Code standards and patterns | BEFORE implementation |
| **[SPEC/independent_services.xml](SPEC/independent_services.xml)** | Microservice independence | When modifying services |
| **[SPEC/ai_factory_patterns.xml](SPEC/ai_factory_patterns.xml)** | AI factory patterns & multi-agent collaboration | Complex coding processes |

## 🔧 Utility & Script Indexes

### Architecture Compliance
```bash
python scripts/check_architecture_compliance.py  # Check module/function limits
python scripts/generate_wip_report.py           # Generate WIP status report
```

### String Literal Management
```bash
python scripts/query_string_literals.py validate "literal"  # Validate literals
python scripts/scan_string_literals.py                     # Update index
```

## 📂 Directory Structure References

### Service-Specific Documentation
| Service | Documentation Path | Test Path |
|---------|-------------------|-----------|
| **Main Backend** | `/netra_backend/` | `/netra_backend/tests/` |
| **Auth Service** | `/auth_service/` | `/auth_service/tests/` |
| **Frontend** | `/frontend/` | `/frontend/__tests__/` |

### Shared Resources
| Resource | Path | Purpose |
|----------|------|---------|
| **Specifications** | `/SPEC/` | Living source of truth (XML) |
| **Documentation** | `/docs/` | User-facing documentation |
| **Scripts** | `/scripts/` | Automation and utilities |
| **Test Framework** | `/test_framework/` | Shared test utilities |
| **E2E Tests** | `/tests/e2e/` | Cross-service integration tests |

## 🚀 Quick Access Commands

### Development Workflow
```bash
# Start development environment
python scripts/dev_launcher.py

# Run tests (fast feedback)
python unified_test_runner.py --level integration --no-coverage --fast-fail

# Check compliance before commit
python scripts/check_architecture_compliance.py
```

### Testing Commands
```bash
# Test agent changes
python unified_test_runner.py --level agents --real-llm

# Pre-release validation (includes staging)
python unified_test_runner.py --level integration --real-llm --env staging
```

### Deployment
```bash
# Quick deploy to staging
python organized_root/deployment_configs/deploy_staging.py

# Fix auth issues
python organized_root/deployment_configs/setup_staging_auth.py --force-new-key
```

## 📊 Status Reports & Metrics

### Compliance Reports
- **[reports/compliance_report.json](reports/compliance_report.json)** - Latest compliance metrics
- **[SPEC/compliance_reporting.xml](SPEC/compliance_reporting.xml)** - Compliance tracking system
- **[SPEC/test_reporting.xml](SPEC/test_reporting.xml)** - Testing metrics and coverage

### Architecture Health
- **[SPEC/ai_factory_status_report.xml](SPEC/ai_factory_status_report.xml)** - AI factory patterns status
- **[reports/ARCHITECTURE_COMPLIANCE_REPORT.md](reports/ARCHITECTURE_COMPLIANCE_REPORT.md)** - Architecture compliance details
- **[SPEC/folder_structure_rules.md](SPEC/folder_structure_rules.md)** - Directory organization guidelines

## 🔍 Search & Discovery Tools

### Finding Files & Code
```bash
# Find files by pattern
python scripts/query_string_literals.py search "pattern"

# Architecture scanner
python scripts/architecture_scanner.py

# Test discovery
python test_framework/test_discovery.py
```

## 📝 Key Documentation Categories

### Business & Strategy
- **Business Value Justification (BVJ)** - Every feature must demonstrate ROI
- **[SPEC/app_business_value.xml](SPEC/app_business_value.xml)** - Business value tracking

### Agent System
- **[docs/agents/AGENT_SYSTEM.md](docs/agents/AGENT_SYSTEM.md)** - Agent architecture overview
- **[SPEC/unified_agent_architecture.xml](SPEC/unified_agent_architecture.xml)** - Unified agent specs

### Security & Auth
- **[SPEC/security.xml](SPEC/security.xml)** - Security specifications
- **[SPEC/PRODUCTION_SECRETS_ISOLATION.xml](SPEC/PRODUCTION_SECRETS_ISOLATION.xml)** - Secret management

### Frontend & UI/UX
- **[SPEC/ui_ux_master.xml](SPEC/ui_ux_master.xml)** - UI/UX master specifications
- **[SPEC/websockets.xml](SPEC/websockets.xml)** - WebSocket implementation

## 🎓 Learning Resources

### Getting Started
1. Start with **[README.md](README.md)** for project overview
2. Read **[CLAUDE.md](CLAUDE.md)** for engineering philosophy
3. Check **[LLM_MASTER_INDEX.md](LLM_MASTER_INDEX.md)** before searching for files
4. Review **[MASTER_WIP_STATUS.md](MASTER_WIP_STATUS.md)** for system health

### Before Making Changes
1. Check **[SPEC/learnings/index.xml](SPEC/learnings/index.xml)** for insights
2. Validate strings with `python scripts/query_string_literals.py`
3. Review **[SPEC/type_safety.xml](SPEC/type_safety.xml)** and **[SPEC/conventions.xml](SPEC/conventions.xml)**
4. Run compliance checks with `python scripts/check_architecture_compliance.py`

---

**Remember:** This index is the starting point for all navigation. When in doubt, start here to find the right documentation or specification for your task.