# Canonical Type Registry Architecture for Netra Apex

**BUSINESS VALUE JUSTIFICATION (BVJ):**
- **Segment**: All (Free, Early, Mid, Enterprise)
- **Business Goal**: Reduce bugs by 40% and speed development by 25%
- **Value Impact**: Type safety prevents runtime errors that damage user experience and trust
- **Revenue Impact**: Faster feature delivery and lower maintenance costs increase conversion rates

## Executive Summary

This document outlines the canonical type registry architecture for Netra Apex to eliminate 201 duplicate type definitions across frontend and backend. The design follows the 300-line file limit and 8-line function limit mandates while ensuring backward compatibility during migration.

## Current State Analysis

### Identified Duplications
- **Message types**: 8 definitions across frontend/backend
- **User types**: 13 definitions in various locations
- **Agent types**: 15+ scattered definitions
- **WebSocket types**: 10+ fragmented definitions
- **Tool types**: 20+ duplicated interfaces

### Pain Points
1. Type mismatches between frontend/backend causing runtime errors
2. Development confusion about which type to use
3. Maintenance overhead for keeping types in sync
4. Inconsistent property names and structures

## 1. FRONTEND TYPE REGISTRY ARCHITECTURE

### 1.1 Directory Structure
```
frontend/types/
├── index.ts                    # Main barrel export (Central Registry)
├── registry.ts                 # Core type registry (<300 lines)
├── domains/                    # Domain-specific types
│   ├── auth.ts                # Authentication types
│   ├── agents.ts              # Agent-related types
│   ├── chat.ts                # Chat/messaging types
│   ├── tools.ts               # Tool execution types
│   ├── websocket.ts           # WebSocket communication
│   ├── performance.ts         # Performance metrics
│   └── admin.ts               # Admin interface types
├── shared/                     # Cross-domain types
│   ├── base.ts                # Base interfaces
│   ├── api.ts                 # API request/response
│   ├── errors.ts              # Error handling
│   └── events.ts              # Event types
├── backend-sync/              # Auto-generated from backend
│   ├── schemas.ts             # Backend schema types
│   ├── models.ts              # Database model types
│   └── api-contracts.ts       # API contract types
└── legacy/                    # Deprecated types (migration only)
    └── deprecated.ts          # Types being phased out
```

### 1.2 Type Registry Pattern (registry.ts)

```typescript
/**
 * Core Type Registry - Single Source of Truth
 * Max 300 lines - splits into domains when exceeded
 */

// Re-export canonical types from domains
export * from './domains/auth';
export * from './domains/agents';
export * from './domains/chat';
export * from './domains/tools';
export * from './domains/websocket';

// Re-export shared types
export * from './shared/base';
export * from './shared/api';

// Re-export backend-synced types
export * from './backend-sync/schemas';

// Type aliases for backward compatibility
export type { Message as ChatMessage } from './domains/chat';
export type { User as AuthUser } from './domains/auth';
```

### 1.3 Domain Type Organization (Each <300 lines)

#### domains/chat.ts
```typescript
/**
 * Chat Domain Types - Consolidated from all sources
 * BVJ: Unified chat experience across all customer segments
 */

import type { BaseTimestampEntity, BaseMetadata } from '../shared/base';
import type { User } from './auth';
import type { Agent } from './agents';

export interface Message extends BaseTimestampEntity {
  id: string;
  content: string;
  role: MessageRole;
  threadId: string;
  author: User | Agent;
  metadata?: MessageMetadata;
}

export type MessageRole = 'user' | 'assistant' | 'system' | 'agent';

export interface MessageMetadata extends BaseMetadata {
  subAgent?: string;
  toolName?: string;
  executionTimeMs?: number;
  tokenCount?: number;
  modelUsed?: string;
  confidenceScore?: number;
}
```

#### domains/auth.ts
```typescript
/**
 * Authentication Domain Types
 * BVJ: Secure user management for all tiers
 */

import type { BaseEntity } from '../shared/base';

export interface User extends BaseEntity {
  id: string;
  email: string;
  name: string;
  plan: UserPlan;
  permissions: Permission[];
}

export type UserPlan = 'free' | 'early' | 'mid' | 'enterprise';

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}
```

### 1.4 Export Strategy

#### Main Index (index.ts)
```typescript
/**
 * Main Type Registry Export
 * Single import point for all types
 */

// Primary exports (no conflicts)
export * from './registry';

// Namespaced exports for conflicts
export * as Auth from './domains/auth';
export * as Chat from './domains/chat';
export * as Agents from './domains/agents';

// Direct exports for commonly used types
export type { 
  User,
  Message,
  Agent,
  WebSocketMessage 
} from './registry';
```

## 2. BACKEND TYPE REGISTRY ARCHITECTURE

### 2.1 Directory Structure
```
app/schemas/
├── __init__.py                 # Main exports (Barrel pattern)
├── registry.py                 # Core type registry (<300 lines)
├── domains/                    # Domain modules (<300 lines each)
│   ├── auth.py                # Authentication schemas
│   ├── agents.py              # Agent schemas
│   ├── chat.py                # Chat/messaging schemas
│   ├── tools.py               # Tool execution schemas
│   ├── websocket.py           # WebSocket schemas
│   ├── performance.py         # Performance metrics
│   └── admin.py               # Admin schemas
├── shared/                     # Cross-domain schemas
│   ├── base.py                # Base Pydantic models
│   ├── api.py                 # API patterns
│   ├── errors.py              # Error schemas
│   └── validation.py          # Validation schemas
├── internal/                   # Internal-only types
│   ├── database.py            # DB-specific models
│   ├── llm.py                 # LLM integration types
│   └── services.py            # Service layer types
└── generated/                  # Auto-generated schemas
    └── openapi.py             # OpenAPI schema exports
```

### 2.2 Registry Pattern (registry.py)

```python
"""
Core Schema Registry - Single Source of Truth
Max 300 lines - splits into domains when exceeded
"""

# Re-export all domain schemas
from .domains.auth import *
from .domains.agents import *
from .domains.chat import *
from .domains.tools import *
from .domains.websocket import *

# Re-export shared schemas
from .shared.base import *
from .shared.api import *

# Define type unions for common patterns
MessageUnion = Union[UserMessage, AgentMessage, SystemMessage]
WebSocketPayloadUnion = Union[StartAgentPayload, UserMessagePayload, StopAgentPayload]
```

### 2.3 Domain Schema Organization

#### domains/chat.py
```python
"""
Chat Domain Schemas
BVJ: Consistent messaging across all customer segments
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime
from ..shared.base import BaseTimestampEntity, BaseMetadata

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant" 
    SYSTEM = "system"
    AGENT = "agent"

class MessageMetadata(BaseMetadata):
    """Message metadata - consolidated from all sources"""
    sub_agent: Optional[str] = None
    tool_name: Optional[str] = None
    execution_time_ms: Optional[int] = None
    token_count: Optional[int] = None
    model_used: Optional[str] = None
    confidence_score: Optional[float] = None

class Message(BaseTimestampEntity):
    """Core message schema - single source of truth"""
    id: str
    content: str
    role: MessageRole
    thread_id: str
    author_id: str
    metadata: Optional[MessageMetadata] = None
```

### 2.4 Pydantic Organization Strategy

```python
# shared/base.py - Foundation schemas
class BaseEntity(BaseModel):
    """Base for all entities with ID"""
    id: str
    
class BaseTimestampEntity(BaseEntity):
    """Base with timestamps"""
    created_at: datetime
    updated_at: datetime
    
class BaseMetadata(BaseModel):
    """Base metadata pattern"""
    source: Optional[str] = None
    version: Optional[str] = None
```

## 3. SHARED TYPES COORDINATION

### 3.1 Type Synchronization Strategy

#### Backend Schema Generation
```python
# scripts/generate_frontend_types.py
"""
Auto-generate TypeScript types from Pydantic models
Max 8 lines per function, modular approach
"""

def generate_type_files() -> None:
    """Generate all TypeScript type files"""
    schemas = extract_schemas()
    domains = group_by_domain(schemas)
    write_domain_files(domains)
    update_registry_exports()

def extract_schemas() -> List[PydanticModel]:
    """Extract Pydantic models from backend"""
    return get_pydantic_models_from_app()

def group_by_domain(schemas: List[PydanticModel]) -> Dict[str, List]:
    """Group schemas by domain for file organization"""
    return categorize_schemas(schemas)

def write_domain_files(domains: Dict[str, List]) -> None:
    """Write TypeScript files for each domain"""
    for domain, models in domains.items():
        write_domain_file(domain, models)
```

### 3.2 Validation Strategy

#### Type Consistency Validation
```python
# scripts/validate_type_consistency.py

def validate_type_alignment() -> ValidationResult:
    """Validate backend-frontend type alignment"""
    backend_types = extract_backend_types()
    frontend_types = parse_frontend_types()
    return compare_type_structures(backend_types, frontend_types)

def check_duplicate_definitions() -> List[Duplicate]:
    """Find duplicate type definitions across codebase"""
    definitions = scan_type_definitions()
    return identify_duplicates(definitions)
```

## 4. MIGRATION STRATEGY

### Phase 1: Create Canonical Types (Week 1)
**Goal**: Establish new registry without breaking existing code

**Tasks**:
1. Create new registry structure in parallel
2. Implement backend domain schemas
3. Generate initial frontend types
4. Add backward compatibility aliases

**Success Criteria**:
- New registry contains all consolidated types
- All tests pass with existing imports
- No runtime errors in development

### Phase 2: Update Imports Gradually (Week 2-3)
**Goal**: Migrate imports module by module

**Strategy**:
```typescript
// Migration pattern - update imports gradually
// Old import
import { Message } from '../components/chat/types';

// New import  
import { Message } from '@/types/registry';
```

**Priority Order**:
1. Core domain types (auth, chat, agents)
2. Shared utilities and services
3. Component prop interfaces
4. Test files and mocks

### Phase 3: Remove Duplicates (Week 4)
**Goal**: Remove all duplicate definitions

**Actions**:
1. Delete old type files after migration
2. Remove legacy import paths
3. Update documentation
4. Run comprehensive validation

**Rollback Plan**:
- Keep legacy files in `/legacy` folder for 1 release
- Maintain import aliases for 2 releases
- Comprehensive test coverage for rollback scenarios

## 5. MODULE BOUNDARIES (300-LINE COMPLIANCE)

### 5.1 File Size Management

Each domain file MUST stay under 300 lines:

```typescript
// When domains/chat.ts approaches 300 lines, split into:
domains/chat/
├── index.ts           # Main exports
├── core.ts           # Core message types  
├── metadata.ts       # Message metadata
├── threads.ts        # Thread management
└── websocket.ts      # WebSocket message types
```

### 5.2 Function Decomposition (8-LINE COMPLIANCE)

```typescript
// Type generation functions - each ≤8 lines
function generateChatTypes(): string {
  const models = getChatModels();
  const interfaces = convertToInterfaces(models);
  const exports = createExportStatements(interfaces);
  return combineTypeDefinitions(exports);
}

function getChatModels(): PydanticModel[] {
  return extractModelsFromDomain('chat');
}

function convertToInterfaces(models: PydanticModel[]): TypeInterface[] {
  return models.map(model => convertModel(model));
}
```

## 6. AUTOMATED VALIDATION

### 6.1 Pre-commit Hooks
```bash
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: type-validation
      name: Type Registry Validation
      entry: python scripts/validate_types.py
      language: system
      
    - id: duplicate-detection
      name: Duplicate Type Detection
      entry: python scripts/check_duplicates.py
      language: system
```

### 6.2 CI/CD Integration
```yaml
# .github/workflows/type-safety.yml
name: Type Safety Validation
on: [push, pull_request]

jobs:
  validate-types:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check Type Consistency
        run: python scripts/validate_type_consistency.py
      - name: Detect Duplicates
        run: python scripts/check_duplicates.py
      - name: TypeScript Type Check
        run: npx tsc --noEmit
```

## 7. IMPLEMENTATION TOOLING

### 7.1 Type Registry CLI
```python
# scripts/type_registry_cli.py

@click.group()
def cli():
    """Type Registry Management CLI"""
    pass

@cli.command()
def validate():
    """Validate type consistency"""
    result = validate_type_alignment()
    display_validation_results(result)

@cli.command()
def migrate():
    """Migrate imports to registry"""
    files = find_files_to_migrate()
    update_imports_in_files(files)

@cli.command()
def generate():
    """Generate frontend types from backend"""
    generate_frontend_types_from_backend()
```

### 7.2 VSCode Integration
```json
// .vscode/settings.json
{
  "typescript.preferences.includePackageJsonAutoImports": "auto",
  "typescript.suggest.autoImports": true,
  "typescript.preferences.importModuleSpecifier": "relative",
  "typescript.suggest.paths": {
    "@/types/*": ["./frontend/types/*"]
  }
}
```

## 8. SUCCESS METRICS

### 8.1 Quantitative Metrics
- **Type Duplications**: 201 → 0 (100% reduction)
- **TypeScript Compilation Errors**: Reduce by 80%
- **Import Statement Count**: Reduce by 60%
- **File Count in types/**: Consolidate to ~15 organized files

### 8.2 Quality Metrics
- **Type Coverage**: 95%+ across all domains
- **Backend-Frontend Alignment**: 100% for API contracts
- **Documentation**: Complete type documentation for all public interfaces

### 8.3 Development Experience
- **Import Simplicity**: Single import for most use cases
- **IDE Support**: Full autocomplete and type checking
- **Error Clarity**: Clear error messages for type mismatches

## 9. MAINTENANCE STRATEGY

### 9.1 Ownership Model
- **Registry Maintainer**: Senior Frontend Engineer
- **Domain Owners**: Feature team leads
- **Sync Process**: Automated with manual review

### 9.2 Evolution Process
1. New types must be added to registry first
2. Breaking changes require deprecation period
3. Monthly registry health reviews
4. Quarterly architecture review

## 10. RISK MITIGATION

### 10.1 Technical Risks
- **Import Conflicts**: Namespaced exports and clear naming
- **Circular Dependencies**: Strict dependency graph validation
- **Performance**: Lazy loading for large type sets

### 10.2 Migration Risks
- **Breaking Changes**: Comprehensive backward compatibility
- **Team Coordination**: Clear migration timeline and communication
- **Rollback Capability**: Maintain legacy imports for safe rollback

This architecture provides a comprehensive solution for eliminating type duplication while maintaining strict architectural compliance and enabling smooth migration. The modular design ensures each component stays within the 300-line limit while providing clear separation of concerns and strong type safety across the entire Netra Apex platform.