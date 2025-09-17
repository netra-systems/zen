# Zen Orchestrator Changelog

## [v1.1.0] - 2024-2025

### Changed
#### Simplified Token Metrics Display
- **Breaking Change**: Updated status table column headers and metrics calculation
- Changed column structure from `Status | Name | Model | Duration | Tokens | vs Med | Cache | Tools` to `Status | Name | Model | Duration | Overall | Tokens | Cache | Tools`
- **Metrics Definitions**:
  - **Overall**: Total tokens including all types (input + output + cache_read + cache_creation) - previously called "Tokens"
  - **Tokens**: Core processing tokens only (input + output) - new simplified metric
  - **Cache**: Cache tokens only (cache_read + cache_creation) - unchanged
- **User Benefit**: Provides intuitive breakdown where `Overall = Tokens + Cache`
- **Impact**: More user-friendly display without changing underlying calculations

#### Fixed Token Accounting Bug
- **Bug Fix**: Corrected double-counting of cache tokens in budget tracking
- Previously: `current_billable_tokens = status.total_tokens + status.cached_tokens` (incorrect)
- Now: `current_billable_tokens = status.total_tokens` (correct)
- **Reason**: `total_tokens` already includes all token types including cache tokens
- **Impact**: Accurate budget tracking and cost calculations

### Added
#### Enhanced Documentation
- Added comprehensive pricing strategy documentation in `/zen/docs/pricing_strategy.md`
- Documented all token calculation formulas and cache pricing strategies
- Added tool cost calculation methods and transparency features
- Included example status table and tool usage table formats

#### Tool Usage Transparency
- Enhanced tool usage details table with token counts and costs
- Added per-tool cost calculation at model-specific input rates
- Improved instance tracking showing tool usage per command

### Technical Details
#### Token Calculation Compliance
- All calculations remain compliant with official Claude pricing documentation
- Cache read cost: 10% of input token rate
- Cache creation cost: 25% premium (5-min) or 100% premium (1-hour)
- Tool tokens charged at input token rate for the respective model

#### Display Format Changes
```
# Before
║ Tokens: 100.5K | vs Med: +0% | Cache: 99.4K

# After
║ Overall: 100.5K | Tokens: 1.1K | Cache: 99.4K
```

This change improves user understanding while maintaining full accuracy in cost calculations and token tracking.

---

## Previous Versions

### [v1.0.0] - Initial Release
- Basic token tracking and cost calculation
- Claude pricing engine integration
- Budget management system
- WebSocket agent orchestration