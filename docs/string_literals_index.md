# String Literals Index

Comprehensive index of all string literals in the Netra platform codebase.

*Generated on 2025-08-21 22:09:14*

## 📊 Statistics Dashboard

| Metric | Value |
|--------|-------|
| Total Literals | 29,589 |
| Unique Categories | 17 |
| Unique Subcategories | 54 |
| Files Analyzed | 328 |
| Categorization Rate | 96.6% |
| Average Confidence | 0.643 |

### Confidence Distribution

- 🟢 High (≥0.8): 4,348 literals (14.7%)
- 🟡 Medium (0.5-0.8): 17,847 literals (60.3%)
- 🔴 Low (<0.5): 7,394 literals (25.0%)

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
  - [💬 Messages](#category-messages)
  - [📋 Metadata](#category-metadata)
  - [📊 Metrics](#category-metrics)
  - [🛤️ Paths](#category-paths)
  - [🔄 States](#category-states)
  - [📄 Tests](#category-tests)
  - [❓ Uncategorized](#category-uncategorized)
  - [🌍 Web](#category-web)

## 🔍 Quick Reference

### Most Used Literals

| Literal | Category | Confidence | Usage |
|---------|----------|------------|-------|
| `utf\-8` | uncategorized | 🔴 Low (<0.5) | 364 |
| `store\_true` | configuration | 🟡 Medium (0.5-0.8) | 207 |
| `name` | database | 🟢 High (≥0.8) | 190 |
| `tests` | configuration | 🟡 Medium (0.5-0.8) | 133 |
| `summary` | configuration | 🟡 Medium (0.5-0.8) | 129 |
| `critical` | configuration | 🟡 Medium (0.5-0.8) | 124 |
| `file` | configuration | 🟡 Medium (0.5-0.8) | 102 |
| `\.1f` | tests | 🟡 Medium (0.5-0.8) | 96 |
| `status` | configuration | 🟡 Medium (0.5-0.8) | 96 |
| `error` | states | 🟢 High (≥0.8) | 90 |

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

**Count**: 523 literals

**Description**: Command line arguments and CLI-related strings

**Subcategories**:

- `argument`: 523 literals

**Top Examples**:

- `\-\-version` - *cli.argument* 🟢 High (≥0.8)
- `\-W` - *cli.argument* 🟢 High (≥0.8)
- `\-j` - *cli.argument* 🟢 High (≥0.8)
- `\-\-secret\-file` - *cli.argument* 🟢 High (≥0.8)
- `\-\-env\-file` - *cli.argument* 🟢 High (≥0.8)

📄 **[View detailed cli documentation](string_literals/cli.md)**

---

### ⚙️ Configuration {category-configuration}

**Count**: 10,066 literals

**Description**: System configuration keys, environment variables, and settings

**Subcategories**:

- `config_key`: 340 literals
- `connection`: 40 literals
- `env_var`: 8957 literals
- `general`: 716 literals
- `setting`: 13 literals

**Top Examples**:

- `db\_` - *configuration.env_var* 🟢 High (≥0.8)
- `netra\_backend` - *configuration.env_var* 🟢 High (≥0.8)
- `netra\_backend/tests` - *configuration.env_var* 🟢 High (≥0.8)
- `netra\_backend/tests/conftest\.py` - *configuration.env_var* 🟢 High (≥0.8)
- `netra\_backend` - *configuration.env_var* 🟢 High (≥0.8)

📄 **[View detailed configuration documentation](string_literals/configuration.md)**

---

### 🔒 Constants {category-constants}

**Count**: 17 literals

**Description**: Enumeration values and constant definitions

**Subcategories**:

- `enum`: 10 literals
- `number`: 7 literals

**Top Examples**:

- `"JWT\_SECRET\_KEY"` - *constants.enum* 🟡 Medium (0.5-0.8)
- `"FERNET\_KEY"` - *constants.enum* 🟡 Medium (0.5-0.8)
- `"GEMINI\_API\_KEY"` - *constants.enum* 🟡 Medium (0.5-0.8)
- `"DATABASE\_URL"` - *constants.enum* 🟡 Medium (0.5-0.8)
- `NEXT\_PUBLIC\_API\_URL=` - *constants.enum* 🟡 Medium (0.5-0.8)

📄 **[View detailed constants documentation](string_literals/constants.md)**

---

### 📄 Content {category-content}

**Count**: 668 literals

**Description**: General text content and user-facing text

**Subcategories**:

- `text`: 668 literals

**Top Examples**:

- `class TestSyntaxFix:` - *content.text* 🔴 Low (<0.5)
- `    """Generated test class"""` - *content.text* 🔴 Low (<0.5)
- `class TestSyntaxFix:` - *content.text* 🔴 Low (<0.5)
- `    """Generated test class"""` - *content.text* 🔴 Low (<0.5)
- ` \# Possibly broken comprehension` - *content.text* 🔴 Low (<0.5)

📄 **[View detailed content documentation](string_literals/content.md)**

---

### 🗄️ Database {category-database}

**Count**: 646 literals

**Description**: Table names, column names, SQL keywords, and database queries

**Subcategories**:

- `column`: 441 literals
- `general`: 122 literals
- `query`: 11 literals
- `sql`: 29 literals
- `table`: 43 literals

**Top Examples**:

- `delete` - *database.sql* 🟢 High (≥0.8)
- `delete` - *database.sql* 🟢 High (≥0.8)
- `update` - *database.sql* 🟢 High (≥0.8)
- `delete` - *database.sql* 🟢 High (≥0.8)
- `delete` - *database.sql* 🟢 High (≥0.8)

📄 **[View detailed database documentation](string_literals/database.md)**

---

### 📝 Documentation {category-documentation}

**Count**: 1,632 literals

**Description**: Docstrings, comments, and markdown content

**Subcategories**:

- `comment`: 307 literals
- `docstring`: 939 literals
- `general`: 57 literals
- `markdown`: 329 literals

**Top Examples**:

- `warning` - *documentation.comment* 🟢 High (≥0.8)
- `todo` - *documentation.comment* 🟢 High (≥0.8)
- `fixme` - *documentation.comment* 🟢 High (≥0.8)
- `WARNING` - *documentation.comment* 🟢 High (≥0.8)
- `warning` - *documentation.comment* 🟢 High (≥0.8)

📄 **[View detailed documentation documentation](string_literals/documentation.md)**

---

### ⚡ Events {category-events}

**Count**: 406 literals

**Description**: Event handlers, event types, and lifecycle events

**Subcategories**:

- `general`: 369 literals
- `handler`: 6 literals
- `lifecycle`: 7 literals
- `type`: 24 literals

**Top Examples**:

- `handle\_` - *events.handler* 🟢 High (≥0.8)
- `on\_` - *events.handler* 🟢 High (≥0.8)
- `new\_files\_created` - *events.type* 🟢 High (≥0.8)
- `new\_files\_created` - *events.type* 🟢 High (≥0.8)
- `files\_created` - *events.type* 🟢 High (≥0.8)

📄 **[View detailed events documentation](string_literals/events.md)**

---

### 📋 Formats {category-formats}

**Count**: 1,903 literals

**Description**: Template strings, regex patterns, JSON, and datetime formats

**Subcategories**:

- `datetime`: 58 literals
- `json`: 110 literals
- `mime_type`: 10 literals
- `regex`: 1576 literals
- `template`: 149 literals

**Top Examples**:

- `2022\-11\-28` - *formats.datetime* 🟢 High (≥0.8)
- `2022\-11\-28` - *formats.datetime* 🟢 High (≥0.8)
- `2025\-08\-16` - *formats.datetime* 🟢 High (≥0.8)
- `2025\-08\-16` - *formats.datetime* 🟢 High (≥0.8)
- `\[/cyan\]` - *formats.json* 🟢 High (≥0.8)

📄 **[View detailed formats documentation](string_literals/formats.md)**

---

### 🏷️ Identifiers {category-identifiers}

**Count**: 612 literals

**Description**: Component names, class names, field names, and identifiers

**Subcategories**:

- `class`: 41 literals
- `component`: 70 literals
- `field`: 34 literals
- `function`: 146 literals
- `hash`: 5 literals
- `name`: 316 literals

**Top Examples**:

- `auth\_service` - *identifiers.component* 🟢 High (≥0.8)
- `auth\_service` - *identifiers.component* 🟢 High (≥0.8)
- `auth\_service` - *identifiers.component* 🟢 High (≥0.8)
- `auth\_service` - *identifiers.component* 🟢 High (≥0.8)
- `auth\_service` - *identifiers.component* 🟢 High (≥0.8)

📄 **[View detailed identifiers documentation](string_literals/identifiers.md)**

---

### 💬 Messages {category-messages}

**Count**: 4,764 literals

**Description**: Log messages, user messages, error messages, and notifications

**Subcategories**:

- `error`: 409 literals
- `log`: 129 literals
- `success`: 45 literals
- `user`: 4181 literals

**Top Examples**:

- `Error:` - *messages.log* 🟢 High (≥0.8)
- `error:` - *messages.log* 🟢 High (≥0.8)
- `exception` - *messages.error* 🟢 High (≥0.8)
- `exception` - *messages.error* 🟢 High (≥0.8)
- `exception` - *messages.error* 🟢 High (≥0.8)

📄 **[View detailed messages documentation](string_literals/messages.md)**

---

### 📋 Metadata {category-metadata}

**Count**: 12 literals

**Description**: Version numbers, hashes, and metadata information

**Subcategories**:

- `version`: 12 literals

**Top Examples**:

- `1\.0\.0` - *metadata.version* 🟡 Medium (0.5-0.8)
- `1\.0\.0` - *metadata.version* 🟡 Medium (0.5-0.8)
- `0\.0\.0\.0` - *metadata.version* 🟡 Medium (0.5-0.8)
- `192\.168\.1\.1` - *metadata.version* 🟡 Medium (0.5-0.8)
- `1\.0\.0` - *metadata.version* 🟡 Medium (0.5-0.8)

📄 **[View detailed metadata documentation](string_literals/metadata.md)**

---

### 📊 Metrics {category-metrics}

**Count**: 445 literals

**Description**: Performance metrics, measurements, and monitoring data

**Subcategories**:

- `general`: 154 literals
- `measurement`: 211 literals
- `performance`: 8 literals
- `status`: 72 literals

**Top Examples**:

- `time\_saved\_seconds` - *metrics.performance* 🟢 High (≥0.8)
- `time\_saved\_seconds` - *metrics.performance* 🟢 High (≥0.8)
- `time\_saved\_seconds` - *metrics.performance* 🟢 High (≥0.8)
- `time\_saved\_seconds` - *metrics.performance* 🟢 High (≥0.8)
- `request\_duration\_seconds` - *metrics.performance* 🟢 High (≥0.8)

📄 **[View detailed metrics documentation](string_literals/metrics.md)**

---

### 🛤️ Paths {category-paths}

**Count**: 1,489 literals

**Description**: API endpoints, file paths, directories, and URLs

**Subcategories**:

- `api`: 77 literals
- `directory`: 154 literals
- `file`: 1170 literals
- `url`: 63 literals
- `websocket`: 25 literals

**Top Examples**:

- `\.yml` - *paths.file* 🟢 High (≥0.8)
- `\.yaml` - *paths.file* 🟢 High (≥0.8)
- `\.yml` - *paths.file* 🟢 High (≥0.8)
- `\.yaml` - *paths.file* 🟢 High (≥0.8)
- `\.env` - *paths.file* 🟢 High (≥0.8)

📄 **[View detailed paths documentation](string_literals/paths.md)**

---

### 🔄 States {category-states}

**Count**: 461 literals

**Description**: Status values, boolean states, and lifecycle states

**Subcategories**:

- `boolean`: 87 literals
- `general`: 69 literals
- `lifecycle`: 9 literals
- `status`: 296 literals

**Top Examples**:

- `false` - *states.boolean* 🟢 High (≥0.8)
- `yes` - *states.boolean* 🟢 High (≥0.8)
- `yes` - *states.boolean* 🟢 High (≥0.8)
- `yes` - *states.boolean* 🟢 High (≥0.8)
- `enabled` - *states.boolean* 🟢 High (≥0.8)

📄 **[View detailed states documentation](string_literals/states.md)**

---

### 📄 Tests {category-tests}

**Count**: 4,911 literals

**Description**: No description available

**Top Examples**:

- `
Script to add pytest markers to test files based on their d...` - *tests* 🟡 Medium (0.5-0.8)
- `Adds appropriate pytest markers to test files` - *tests* 🟡 Medium (0.5-0.8)
- `Error: test\_categorization\.json not found\. Run categorize\_te...` - *tests* 🟡 Medium (0.5-0.8)
- `Determine which markers should be added to a test file` - *tests* 🟡 Medium (0.5-0.8)
- `@pytest\.mark\.real\_llm` - *tests* 🟡 Medium (0.5-0.8)

📄 **[View detailed tests documentation](string_literals/tests.md)**

---

### ❓ Uncategorized {category-uncategorized}

**Count**: 1,012 literals

**Description**: Strings that could not be automatically categorized

**Subcategories**:

- `unknown`: 1012 literals

**Top Examples**:

- `\.github` - *uncategorized.unknown* 🔴 Low (<0.5)
- `\.act\.secrets` - *uncategorized.unknown* 🔴 Low (<0.5)
- `utf\-8` - *uncategorized.unknown* 🔴 Low (<0.5)
- `staging\-deploy` - *uncategorized.unknown* 🔴 Low (<0.5)
- `staging\-deploy` - *uncategorized.unknown* 🔴 Low (<0.5)

📄 **[View detailed uncategorized documentation](string_literals/uncategorized.md)**

---

### 🌍 Web {category-web}

**Count**: 22 literals

**Description**: Query parameters, form fields, and web-related strings

**Subcategories**:

- `parameter`: 22 literals

**Top Examples**:

- `
    <script>
        const data = ` - *web.parameter* 🟡 Medium (0.5-0.8)
- `
<\!DOCTYPE html>
<html lang="en">
<head>
    ` - *web.parameter* 🟡 Medium (0.5-0.8)
- `
        <div class="main\-content">` - *web.parameter* 🟡 Medium (0.5-0.8)
- `
                <div class="metric\-card ` - *web.parameter* 🟡 Medium (0.5-0.8)
- `">
                    <div class="metric\-value">` - *web.parameter* 🟡 Medium (0.5-0.8)

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