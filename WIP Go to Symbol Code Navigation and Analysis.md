## WIP Go to Symbol: Code Navigation and Analysis

The **Go to Symbol** feature provides powerful code navigation and symbol search capabilities across indexed codebases, enabling IDE-like functionality within the Netra platform.

**Purpose:** Extract, index, and search code symbols (functions, classes, methods, interfaces, types) from Python, JavaScript, and TypeScript files for rapid code navigation and analysis.

**Key Components:**
*   **Symbol Extractor:** `netra_backend/app/services/corpus/symbol_extractor.py` - Core symbol extraction engine
*   **Search Operations:** `netra_backend/app/services/corpus/search_operations.py` - Symbol search and ranking functionality
*   **API Endpoints:** `/api/corpus/symbols/search` - RESTful symbol search interface
*   **Test Suite:** `netra_backend/tests/services/test_symbol_extractor.py` - Comprehensive test coverage

**Supported Languages and Symbol Types:**
*   **Python:** Classes, functions, methods, variables, async functions
*   **JavaScript/TypeScript:** Classes, functions, methods, interfaces, types, enums, constants, arrow functions
*   **Symbol Categories:** `class`, `function`, `method`, `variable`, `interface`, `type`, `enum`, `const`

**API Endpoints:**
*   **GET/POST** `/api/corpus/symbols/search` - Search symbols by name with optional type filtering
*   **GET** `/api/corpus/{corpus_id}/document/{document_id}/symbols` - Get all symbols from a specific document

**Usage Examples:**
```bash
# Search for function symbols containing "auth"
curl -X GET "/api/corpus/symbols/search?q=auth&symbol_type=function&limit=20"

# Search all symbols in a specific corpus
curl -X POST "/api/corpus/symbols/search" -d '{"query": "User", "corpus_id": "main", "limit": 50}'
```