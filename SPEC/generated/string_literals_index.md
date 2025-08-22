# String Literals Index

Comprehensive index of all string literals in the Netra platform codebase.

*Generated on 2025-08-21 21:55:53*

## 📊 Statistics Dashboard

| Metric | Value |
|--------|-------|
| Total Literals | 11,641 |
| Unique Categories | 8 |
| Unique Subcategories | 21 |
| Files Analyzed | 430 |
| Categorization Rate | 40.0% |
| Average Confidence | 0.538 |

### Confidence Distribution

- 🟢 High (≥0.8): 4,651 literals (40.0%)
- 🟡 Medium (0.5-0.8): 0 literals (0.0%)
- 🔴 Low (<0.5): 6,990 literals (60.0%)

## 📋 Table of Contents

- [Quick Reference](#quick-reference)
  - [Most Used Literals](#most-used-literals)
  - [Search Patterns](#search-patterns)

- [Categories](#categories)
  - [⚙️ Configuration](#category-configuration)
  - [🗄️ Database](#category-database)
  - [📄 Environment](#category-environment)
  - [⚡ Events](#category-events)
  - [🏷️ Identifiers](#category-identifiers)
  - [📊 Metrics](#category-metrics)
  - [🛤️ Paths](#category-paths)
  - [❓ Uncategorized](#category-uncategorized)

## 🔍 Quick Reference

### Most Used Literals

| Literal | Category | Confidence | Usage |
|---------|----------|------------|-------|
| `/auth/health` | configuration | 🟢 High (≥0.8) | 4 |
| `/auth/login` | configuration | 🟢 High (≥0.8) | 4 |
| `  ` | configuration | 🟢 High (≥0.8) | 3 |
| `    \[OK\] ` | configuration | 🟢 High (≥0.8) | 3 |
| ` \(` | configuration | 🟢 High (≥0.8) | 3 |
| `, ` | configuration | 🟢 High (≥0.8) | 3 |
| `\-\-output` | configuration | 🟢 High (≥0.8) | 3 |
| `\.\.\.` | configuration | 🟢 High (≥0.8) | 3 |
| `/auth/callback` | configuration | 🟢 High (≥0.8) | 3 |
| `/auth/logout` | configuration | 🟢 High (≥0.8) | 3 |

### Search Patterns

Use these patterns to quickly find specific types of literals:

- **API Endpoints**: `/api/`, `websocket` → *paths.api, paths.websocket*
- **Configuration Keys**: `_config`, `_url`, `_key` → *configuration.config_key*
- **Database Elements**: `SELECT`, table names, `_id` → *database.sql, database.table, database.column*
- **Event Names**: `_created`, `_updated`, `websocket_` → *events.type*
- **Error Messages**: `Error`, `Failed`, `Exception` → *messages.error*
- **Environment Variables**: `NETRA_`, `APP_`, `DB_` → *configuration.env_var*

## 📂 Categories

Detailed breakdown of all string literal categories found in the codebase.

### ⚙️ Configuration {category-configuration}

**Count**: 3,546 literals

**Description**: System configuration keys, environment variables, and settings

**Subcategories**:

- `config_key`: 17 literals
- `config_name`: 2 literals
- `config_param`: 1 literals
- `config_value`: 461 literals
- `env_var`: 3065 literals

**Top Examples**:

- `
   Configuring local ` - *configuration.config_value* 🟢 High (≥0.8)
- `
  Authentication:` - *configuration.config_value* 🟢 High (≥0.8)
- `
  Database:` - *configuration.config_value* 🟢 High (≥0.8)
- `
  Environment: ` - *configuration.config_value* 🟢 High (≥0.8)
- `
  LLM Configurations:` - *configuration.config_value* 🟢 High (≥0.8)

📄 **[View detailed configuration documentation](string_literals/configuration.md)**

---

### 🗄️ Database {category-database}

**Count**: 250 literals

**Description**: Table names, column names, SQL keywords, and database queries

**Subcategories**:

- `column_name`: 11 literals
- `sql_keyword`: 234 literals
- `table_name`: 5 literals

**Top Examples**:

- `AgentStarted\(` - *database.table_name* 🟢 High (≥0.8)
- `AgentStarted\\s\*\\\(\[^\)\]\*\\\)` - *database.table_name* 🟢 High (≥0.8)
- `agents/` - *database.table_name* 🟢 High (≥0.8)
- `agents/corpus\_admin` - *database.table_name* 🟢 High (≥0.8)
- `agents/supervisor` - *database.table_name* 🟢 High (≥0.8)

📄 **[View detailed database documentation](string_literals/database.md)**

---

### 📄 Environment {category-environment}

**Count**: 43 literals

**Description**: No description available

**Subcategories**:

- `env_var_name`: 43 literals

**Top Examples**:

- `netra\_backend\.` - *environment.env_var_name* 🟢 High (≥0.8)
- `netra\_backend\.app` - *environment.env_var_name* 🟢 High (≥0.8)
- `netra\_backend\.app\.` - *environment.env_var_name* 🟢 High (≥0.8)
- `netra\_backend\.app\.agents\.corpus\_admin\.agent` - *environment.env_var_name* 🟢 High (≥0.8)
- `netra\_backend\.app\.agents\.supervisor\.agent` - *environment.env_var_name* 🟢 High (≥0.8)

📄 **[View detailed environment documentation](string_literals/environment.md)**

---

### ⚡ Events {category-events}

**Count**: 118 literals

**Description**: Event handlers, event types, and lifecycle events

**Subcategories**:

- `event_name`: 116 literals
- `websocket_event`: 2 literals

**Top Examples**:

- `
\[FAIL\] ` - *events.event_name* 🟢 High (≥0.8)
- `
📁 ` - *events.event_name* 🟢 High (≥0.8)
- `
🛑` - *events.event_name* 🟢 High (≥0.8)
- `  ` - *events.event_name* 🟢 High (≥0.8)
- ` signal` - *events.event_name* 🟢 High (≥0.8)

📄 **[View detailed events documentation](string_literals/events.md)**

---

### 🏷️ Identifiers {category-identifiers}

**Count**: 30 literals

**Description**: Component names, class names, field names, and identifiers

**Subcategories**:

- `component_name`: 27 literals
- `id_field`: 3 literals

**Top Examples**:

- `= get\_connection\_manager` - *identifiers.component_name* 🟢 High (≥0.8)
- `HeaderConstants\.USER\_AGENT` - *identifiers.component_name* 🟢 High (≥0.8)
- `JWTConstants\.NETRA\_AUTH\_SERVICE` - *identifiers.component_name* 🟢 High (≥0.8)
- `agents/data\_sub\_agent` - *identifiers.component_name* 🟢 High (≥0.8)
- `agents/triage\_sub\_agent` - *identifiers.component_name* 🟢 High (≥0.8)

📄 **[View detailed identifiers documentation](string_literals/identifiers.md)**

---

### 📊 Metrics {category-metrics}

**Count**: 1 literals

**Description**: Performance metrics, measurements, and monitoring data

**Subcategories**:

- `metric_name`: 1 literals

**Top Examples**:

- `/metricDescriptors/run\.googleapis\.com/request\_count` - *metrics.metric_name* 🟢 High (≥0.8)

📄 **[View detailed metrics documentation](string_literals/metrics.md)**

---

### 🛤️ Paths {category-paths}

**Count**: 663 literals

**Description**: API endpoints, file paths, directories, and URLs

**Subcategories**:

- `api_endpoint`: 4 literals
- `dir_path`: 69 literals
- `endpoint`: 61 literals
- `file_path`: 451 literals
- `url`: 74 literals
- `websocket_endpoint`: 4 literals

**Top Examples**:

- `    \[OK\] ` - *paths.endpoint* 🟢 High (≥0.8)
- ` \!= ` - *paths.endpoint* 🟢 High (≥0.8)
- ` \(` - *paths.endpoint* 🟢 High (≥0.8)
- ` \-> ` - *paths.endpoint* 🟢 High (≥0.8)
- ` WebSocket endpoints` - *paths.endpoint* 🟢 High (≥0.8)

📄 **[View detailed paths documentation](string_literals/paths.md)**

---

### ❓ Uncategorized {category-uncategorized}

**Count**: 6,990 literals

**Description**: Strings that could not be automatically categorized

**Subcategories**:

- `unknown`: 6990 literals

**Top Examples**:

- `	` - *uncategorized.unknown* 🔴 Low (<0.5)
- `
` - *uncategorized.unknown* 🔴 Low (<0.5)
- `

` - *uncategorized.unknown* 🔴 Low (<0.5)
- `


` - *uncategorized.unknown* 🔴 Low (<0.5)
- `


class ` - *uncategorized.unknown* 🔴 Low (<0.5)

📄 **[View detailed uncategorized documentation](string_literals/uncategorized.md)**

---

## 🔗 Navigation

- 🏠 [Back to Top](#string-literals-index)
- 📂 [Browse Categories by File](string_literals/)
- 🔍 [Query String Literals](../../scripts/query_string_literals.py)
- ⚙️ [Scan for New Literals](../../scripts/scan_string_literals.py)

---

*This documentation is automatically generated from the string literals index.*
*For questions or improvements, see the [String Literals System Documentation](../string_literals_index.xml).*