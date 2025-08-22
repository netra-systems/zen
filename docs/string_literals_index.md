# String Literals Index

Comprehensive index of all string literals in the Netra platform codebase.

*Generated on 2025-08-21 22:07:40*

## 📊 Statistics Dashboard

| Metric | Value |
|--------|-------|
| Total Literals | 271,918 |
| Unique Categories | 19 |
| Unique Subcategories | 56 |
| Files Analyzed | 3358 |
| Categorization Rate | 99.0% |
| Average Confidence | 0.703 |

### Confidence Distribution

- 🟢 High (≥0.8): 48,538 literals (17.9%)
- 🟡 Medium (0.5-0.8): 184,723 literals (67.9%)
- 🔴 Low (<0.5): 38,657 literals (14.2%)

## 📋 Table of Contents

- [Quick Reference](#quick-reference)
  - [Most Used Literals](#most-used-literals)
  - [Search Patterns](#search-patterns)

- [Categories](#categories)
  - [💻 Cli](#category-cli)
  - [⚙️ Configuration](#category-configuration)
  - [🔒 Constants](#category-constants)
  - [📄 Content](#category-content)
  - [🗄️ Database](#category-database)
  - [📝 Documentation](#category-documentation)
  - [⚡ Events](#category-events)
  - [📋 Formats](#category-formats)
  - [🏷️ Identifiers](#category-identifiers)
  - [🐍 Language](#category-language)
  - [💬 Messages](#category-messages)
  - [📋 Metadata](#category-metadata)
  - [📊 Metrics](#category-metrics)
  - [🌐 Network](#category-network)
  - [🛤️ Paths](#category-paths)
  - [🔄 States](#category-states)
  - [📄 Tests](#category-tests)
  - [❓ Uncategorized](#category-uncategorized)
  - [🌍 Web](#category-web)

## 🔍 Quick Reference

### Most Used Literals

| Literal | Category | Confidence | Usage |
|---------|----------|------------|-------|
| `success` | states | 🟢 High (≥0.8) | 3158 |
| `error` | states | 🟢 High (≥0.8) | 2224 |
| `type` | configuration | 🟡 Medium (0.5-0.8) | 2183 |
| `status` | configuration | 🟡 Medium (0.5-0.8) | 1904 |
| `user\_id` | database | 🟢 High (≥0.8) | 1714 |
| `timestamp` | configuration | 🟡 Medium (0.5-0.8) | 1397 |
| `name` | database | 🟢 High (≥0.8) | 1201 |
| `id` | database | 🟡 Medium (0.5-0.8) | 1196 |
| `data` | configuration | 🟡 Medium (0.5-0.8) | 1084 |
| `email` | database | 🟢 High (≥0.8) | 886 |

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

### 💻 Cli {category-cli}

**Count**: 707 literals

**Description**: Command line arguments and CLI-related strings

**Subcategories**:

- `argument`: 707 literals

**Top Examples**:

- `  \- prompt: The user's question or request` - *cli.argument* 🟢 High (≥0.8)
- `  \- response: The system's answer` - *cli.argument* 🟢 High (≥0.8)
- `
\-\-\- New Corpus Entry \-\-\-` - *cli.argument* 🟢 High (≥0.8)
- `
\-\-\- Entry ` - *cli.argument* 🟢 High (≥0.8)
- ` \-\-\-` - *cli.argument* 🟢 High (≥0.8)

📄 **[View detailed cli documentation](string_literals/cli.md)**

---

### ⚙️ Configuration {category-configuration}

**Count**: 112,921 literals

**Description**: System configuration keys, environment variables, and settings

**Subcategories**:

- `config_key`: 4181 literals
- `connection`: 811 literals
- `env_var`: 104586 literals
- `general`: 2976 literals
- `setting`: 367 literals

**Top Examples**:

- `log\_` - *configuration.env_var* 🟢 High (≥0.8)
- `db\_` - *configuration.env_var* 🟢 High (≥0.8)
- `db\_` - *configuration.env_var* 🟢 High (≥0.8)
- `log\_` - *configuration.env_var* 🟢 High (≥0.8)
- `log\_` - *configuration.env_var* 🟢 High (≥0.8)

📄 **[View detailed configuration documentation](string_literals/configuration.md)**

---

### 🔒 Constants {category-constants}

**Count**: 77 literals

**Description**: Enumeration values and constant definitions

**Subcategories**:

- `enum`: 40 literals
- `number`: 37 literals

**Top Examples**:

- `NIST\_ID\_001` - *constants.enum* 🟡 Medium (0.5-0.8)
- `NIST\_ID\_001` - *constants.enum* 🟡 Medium (0.5-0.8)
- `NIST\_PR\_001` - *constants.enum* 🟡 Medium (0.5-0.8)
- `NIST\_PR\_001` - *constants.enum* 🟡 Medium (0.5-0.8)
- `AUTH\_001` - *constants.enum* 🟡 Medium (0.5-0.8)

📄 **[View detailed constants documentation](string_literals/constants.md)**

---

### 📄 Content {category-content}

**Count**: 1,259 literals

**Description**: General text content and user-facing text

**Subcategories**:

- `text`: 1259 literals

**Top Examples**:

- `30 days` - *content.text* 🔴 Low (<0.5)
- ` result in ` - *content.text* 🔴 Low (<0.5)
- `corpus\_id required` - *content.text* 🔴 Low (<0.5)
- `setting\_name required` - *content.text* 🔴 Low (<0.5)
- ` checking entry conditions for run\_id: ` - *content.text* 🔴 Low (<0.5)

📄 **[View detailed content documentation](string_literals/content.md)**

---

### 🗄️ Database {category-database}

**Count**: 15,884 literals

**Description**: Table names, column names, SQL keywords, and database queries

**Subcategories**:

- `column`: 13527 literals
- `general`: 1284 literals
- `query`: 111 literals
- `sql`: 327 literals
- `table`: 635 literals

**Top Examples**:

- `\_deleted` - *database.column* 🟢 High (≥0.8)
- `\_deleted` - *database.column* 🟢 High (≥0.8)
- `\_at` - *database.column* 🟢 High (≥0.8)
- `\_at` - *database.column* 🟢 High (≥0.8)
- `agents` - *database.table* 🟢 High (≥0.8)

📄 **[View detailed database documentation](string_literals/database.md)**

---

### 📝 Documentation {category-documentation}

**Count**: 15,414 literals

**Description**: Docstrings, comments, and markdown content

**Subcategories**:

- `comment`: 765 literals
- `docstring`: 14100 literals
- `general`: 145 literals
- `markdown`: 404 literals

**Top Examples**:

- `warning` - *documentation.comment* 🟢 High (≥0.8)
- `warning` - *documentation.comment* 🟢 High (≥0.8)
- `warning` - *documentation.comment* 🟢 High (≥0.8)
- `warning` - *documentation.comment* 🟢 High (≥0.8)
- `warning` - *documentation.comment* 🟢 High (≥0.8)

📄 **[View detailed documentation documentation](string_literals/documentation.md)**

---

### ⚡ Events {category-events}

**Count**: 3,998 literals

**Description**: Event handlers, event types, and lifecycle events

**Subcategories**:

- `general`: 3196 literals
- `handler`: 74 literals
- `lifecycle`: 74 literals
- `type`: 654 literals

**Top Examples**:

- `handle\_` - *events.handler* 🟢 High (≥0.8)
- `handle\_` - *events.handler* 🟢 High (≥0.8)
- `on\_` - *events.handler* 🟢 High (≥0.8)
- `fields\_updated` - *events.type* 🟢 High (≥0.8)
- `last\_updated` - *events.type* 🟢 High (≥0.8)

📄 **[View detailed events documentation](string_literals/events.md)**

---

### 📋 Formats {category-formats}

**Count**: 4,495 literals

**Description**: Template strings, regex patterns, JSON, and datetime formats

**Subcategories**:

- `datetime`: 360 literals
- `json`: 215 literals
- `mime_type`: 33 literals
- `regex`: 3282 literals
- `template`: 605 literals

**Top Examples**:

- `2025\-08\-10` - *formats.datetime* 🟢 High (≥0.8)
- `2025\-08\-11` - *formats.datetime* 🟢 High (≥0.8)
- `2025\-08\-13` - *formats.datetime* 🟢 High (≥0.8)
- `2024\-01\-01` - *formats.datetime* 🟢 High (≥0.8)
- `2024\-01\-02` - *formats.datetime* 🟢 High (≥0.8)

📄 **[View detailed formats documentation](string_literals/formats.md)**

---

### 🏷️ Identifiers {category-identifiers}

**Count**: 8,291 literals

**Description**: Component names, class names, field names, and identifiers

**Subcategories**:

- `class`: 222 literals
- `component`: 2476 literals
- `field`: 2693 literals
- `function`: 2225 literals
- `hash`: 25 literals
- `name`: 650 literals

**Top Examples**:

- `auth\_service` - *identifiers.component* 🟢 High (≥0.8)
- `\_executor` - *identifiers.component* 🟢 High (≥0.8)
- `\_executor` - *identifiers.component* 🟢 High (≥0.8)
- `auth\_service` - *identifiers.component* 🟢 High (≥0.8)
- `auth\_service` - *identifiers.component* 🟢 High (≥0.8)

📄 **[View detailed identifiers documentation](string_literals/identifiers.md)**

---

### 🐍 Language {category-language}

**Count**: 2 literals

**Description**: Python keywords and language constructs

**Subcategories**:

- `keyword`: 2 literals

**Top Examples**:

- `  None` - *language.keyword* 🟢 High (≥0.8)
- `  None` - *language.keyword* 🟢 High (≥0.8)

📄 **[View detailed language documentation](string_literals/language.md)**

---

### 💬 Messages {category-messages}

**Count**: 28,686 literals

**Description**: Log messages, user messages, error messages, and notifications

**Subcategories**:

- `error`: 3452 literals
- `log`: 2348 literals
- `success`: 904 literals
- `user`: 21982 literals

**Top Examples**:

- `Error:` - *messages.log* 🟢 High (≥0.8)
- `error:` - *messages.log* 🟢 High (≥0.8)
- `invalid` - *messages.error* 🟢 High (≥0.8)
- `exception` - *messages.error* 🟢 High (≥0.8)
- `exception` - *messages.error* 🟢 High (≥0.8)

📄 **[View detailed messages documentation](string_literals/messages.md)**

---

### 📋 Metadata {category-metadata}

**Count**: 59 literals

**Description**: Version numbers, hashes, and metadata information

**Subcategories**:

- `version`: 59 literals

**Top Examples**:

- `1\.0\.0` - *metadata.version* 🟡 Medium (0.5-0.8)
- `127\.0\.0\.1` - *metadata.version* 🟡 Medium (0.5-0.8)
- `127\.0\.0\.1` - *metadata.version* 🟡 Medium (0.5-0.8)
- `1\.0\.0` - *metadata.version* 🟡 Medium (0.5-0.8)
- `1\.0\.0` - *metadata.version* 🟡 Medium (0.5-0.8)

📄 **[View detailed metadata documentation](string_literals/metadata.md)**

---

### 📊 Metrics {category-metrics}

**Count**: 6,280 literals

**Description**: Performance metrics, measurements, and monitoring data

**Subcategories**:

- `general`: 646 literals
- `measurement`: 4024 literals
- `performance`: 442 literals
- `status`: 1168 literals

**Top Examples**:

- `success\_` - *metrics.status* 🟢 High (≥0.8)
- `\_failures` - *metrics.status* 🟢 High (≥0.8)
- `\_failures` - *metrics.status* 🟢 High (≥0.8)
- `\_failures` - *metrics.status* 🟢 High (≥0.8)
- `error\_` - *metrics.status* 🟢 High (≥0.8)

📄 **[View detailed metrics documentation](string_literals/metrics.md)**

---

### 🌐 Network {category-network}

**Count**: 2 literals

**Description**: IP addresses, ports, and network-related constants

**Subcategories**:

- `port`: 2 literals

**Top Examples**:

- `:00` - *network.port* 🟢 High (≥0.8)
- `:6379` - *network.port* 🟢 High (≥0.8)

📄 **[View detailed network documentation](string_literals/network.md)**

---

### 🛤️ Paths {category-paths}

**Count**: 5,700 literals

**Description**: API endpoints, file paths, directories, and URLs

**Subcategories**:

- `api`: 2549 literals
- `directory`: 264 literals
- `file`: 1806 literals
- `url`: 938 literals
- `websocket`: 143 literals

**Top Examples**:

- `\.txt` - *paths.file* 🟢 High (≥0.8)
- `\.md` - *paths.file* 🟢 High (≥0.8)
- `\.json` - *paths.file* 🟢 High (≥0.8)
- `\.xml` - *paths.file* 🟢 High (≥0.8)
- `\.xml` - *paths.file* 🟢 High (≥0.8)

📄 **[View detailed paths documentation](string_literals/paths.md)**

---

### 🔄 States {category-states}

**Count**: 8,480 literals

**Description**: Status values, boolean states, and lifecycle states

**Subcategories**:

- `boolean`: 394 literals
- `general`: 308 literals
- `lifecycle`: 184 literals
- `status`: 7594 literals

**Top Examples**:

- `error` - *states.status* 🟢 High (≥0.8)
- `completed` - *states.status* 🟢 High (≥0.8)
- `completed` - *states.status* 🟢 High (≥0.8)
- `failed` - *states.status* 🟢 High (≥0.8)
- `error` - *states.status* 🟢 High (≥0.8)

📄 **[View detailed states documentation](string_literals/states.md)**

---

### 📄 Tests {category-tests}

**Count**: 56,977 literals

**Description**: No description available

**Top Examples**:

- `Test Agent Initialization \- Verify robust startup mechanisms...` - *tests* 🟡 Medium (0.5-0.8)
- `\.\.` - *tests* 🟡 Medium (0.5-0.8)
- `Test the AgentInitializationManager\.` - *tests* 🟡 Medium (0.5-0.8)
- `Test agent` - *tests* 🟡 Medium (0.5-0.8)
- `✓ Initialization result: ` - *tests* 🟡 Medium (0.5-0.8)

📄 **[View detailed tests documentation](string_literals/tests.md)**

---

### ❓ Uncategorized {category-uncategorized}

**Count**: 2,616 literals

**Description**: Strings that could not be automatically categorized

**Subcategories**:

- `unknown`: 2616 literals

**Top Examples**:

- ` execution: ` - *uncategorized.unknown* 🔴 Low (<0.5)
- `
Example:` - *uncategorized.unknown* 🔴 Low (<0.5)
- `  Type: ` - *uncategorized.unknown* 🔴 Low (<0.5)
- `\.\.\.` - *uncategorized.unknown* 🔴 Low (<0.5)
- `utf\-8` - *uncategorized.unknown* 🔴 Low (<0.5)

📄 **[View detailed uncategorized documentation](string_literals/uncategorized.md)**

---

### 🌍 Web {category-web}

**Count**: 70 literals

**Description**: Query parameters, form fields, and web-related strings

**Subcategories**:

- `parameter`: 70 literals

**Top Examples**:

- ` AND metric\_name = '` - *web.parameter* 🟡 Medium (0.5-0.8)
- ` AND workload\_id = '` - *web.parameter* 🟡 Medium (0.5-0.8)
- ` AND workload\_id = '` - *web.parameter* 🟡 Medium (0.5-0.8)
- ` AND metric\_name = '` - *web.parameter* 🟡 Medium (0.5-0.8)
- `functions=` - *web.parameter* 🟡 Medium (0.5-0.8)

📄 **[View detailed web documentation](string_literals/web.md)**

---

## 🔗 Navigation

- 🏠 [Back to Top](#string-literals-index)
- 📂 [Browse Categories by File](string_literals/)
- 🔍 [Query String Literals](../../scripts/query_string_literals.py)
- ⚙️ [Scan for New Literals](../../scripts/scan_string_literals.py)

---

*This documentation is automatically generated from the string literals index.*
*For questions or improvements, see the [String Literals System Documentation](../string_literals_index.xml).*