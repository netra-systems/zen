# Contributing to Netra Apex - Revenue-Driven Development

## 🔴 CRITICAL: Business Value Required

**Every contribution must demonstrate clear business value and revenue impact.**

## Table of Contents

- [Business Value Justification](#business-value-justification) **← REQUIRED**
- [Code Standards](#code-standards) **← 300/8 Rule**
- [Development Process](#development-process)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Testing Requirements](#testing-requirements) **← 97% Coverage**
- [Review Process](#review-process)

## Business Value Justification

### Required BVJ Template

**EVERY PR must include this in the description:**

```markdown
## Business Value Justification (BVJ)

**Customer Segment**: [Free/Early/Mid/Enterprise]
**Business Goal**: [Increase savings/conversion/retention]
**Value Impact**: [Estimated % improvement]
**Revenue Impact**: [Estimated MRR increase]
**Implementation Cost**: [Dev hours]
**ROI**: [Revenue Impact / Implementation Cost]

### Success Metrics
- [ ] Metric 1: [e.g., 10% reduction in API costs]
- [ ] Metric 2: [e.g., 5% increase in Free→Early conversion]
- [ ] Metric 3: [e.g., 15ms latency improvement]
```

### Example BVJ

```markdown
## Business Value Justification

**Customer Segment**: Mid-tier ($10K-100K monthly AI spend)
**Business Goal**: Increase savings through intelligent model routing
**Value Impact**: 15% additional cost reduction
**Revenue Impact**: +$45K MRR (15 customers × $3K savings × 20% fee)
**Implementation Cost**: 40 dev hours
**ROI**: 27:1 (first month)

### Success Metrics
- [ ] 15% cost reduction for text generation workloads
- [ ] <100ms routing decision latency
- [ ] 95% routing accuracy
```

## Code Standards

### 🔴 MANDATORY: 300/8 Rule

```python
# BEFORE EVERY COMMIT - NO EXCEPTIONS
python scripts/check_architecture_compliance.py

# Must show:
# ✓ All files ≤ 300 lines
# ✓ All functions ≤ 8 lines
# ✓ No violations found
```

### Module Design Requirements

1. **File Size**: Maximum 300 lines per file
2. **Function Size**: Maximum 8 lines per function
3. **Single Responsibility**: Each module does ONE thing
4. **Type Safety**: All parameters must have type hints
5. **No Duplicates**: Reuse existing code, extend don't duplicate

### Code Style

```python
# GOOD: 8-line function with clear purpose
def calculate_optimization_savings(
    original_cost: float,
    optimized_cost: float
) -> OptimizationResult:
    """Calculate customer savings and Netra revenue."""
    savings = original_cost - optimized_cost
    percentage = (savings / original_cost * 100) if original_cost else 0
    netra_fee = savings * 0.20  # 20% performance fee
    return OptimizationResult(
        savings=savings,
        percentage=percentage,
        fee=netra_fee
    )

# BAD: Function exceeds 8 lines
def process_optimization_request(request):
    # 15 lines of code...
    # VIOLATION: Split into smaller functions
```

## Development Process

### 1. Pre-Development Checklist

- [ ] Read `CLAUDE.md` for business requirements
- [ ] Check `SPEC/learnings/` for related issues
- [ ] Verify feature aligns with customer segment strategy
- [ ] Calculate expected ROI
- [ ] Plan module boundaries (300-line limit)

### 2. Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/revenue-optimization-routing

# 2. Check current compliance
python scripts/check_architecture_compliance.py

# 3. Develop with continuous testing
python test_runner.py --level unit  # Run frequently

# 4. Verify compliance before commit
python scripts/check_architecture_compliance.py

# 5. Run comprehensive tests
python test_runner.py --level integration

# 6. Create PR with BVJ
```

### 3. Commit Message Format

```
<type>(<segment>): <description> [<revenue-impact>]

feat(enterprise): Add HSM key management [$15K MRR]
fix(mid): Resolve model routing latency [Retention]
perf(all): Optimize cache hit rate [20% cost reduction]
test(critical): Add savings calculation tests [Revenue protection]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `perf`: Performance improvement
- `refactor`: Code restructuring
- `test`: Testing improvements
- `docs`: Documentation
- `chore`: Maintenance

## Pull Request Guidelines

### PR Template

```markdown
## Summary
Brief description of changes

## Business Value Justification
[Include full BVJ template]

## Changes
- [ ] Change 1
- [ ] Change 2

## Testing
- [ ] Unit tests pass (97% coverage for revenue paths)
- [ ] Integration tests pass
- [ ] Manual testing completed

## Compliance
- [ ] All files ≤ 300 lines
- [ ] All functions ≤ 8 lines
- [ ] Type safety verified
- [ ] No code duplication

## Screenshots/Demos
[If applicable]
```

### PR Size Guidelines

- **Small**: < 100 lines (preferred)
- **Medium**: 100-300 lines (acceptable)
- **Large**: > 300 lines (requires justification)

## Testing Requirements

### Coverage Requirements by Component Type

| Component Type | Required Coverage | Enforcement |
|---------------|------------------|-------------|
| **Revenue Critical** | 100% | Blocks merge |
| **Customer Facing** | 97% | Blocks merge |
| **Core Features** | 95% | Blocks merge |
| **Supporting** | 90% | Warning |

### Test Categories

```python
# Revenue-critical test (MUST HAVE 100% coverage)
@pytest.mark.revenue_critical
def test_calculate_customer_savings():
    """Test accuracy of savings calculations for billing."""
    pass

# Customer-critical test (97% coverage)
@pytest.mark.customer_critical  
def test_api_rate_limiting():
    """Test rate limiting by customer tier."""
    pass
```

## Review Process

### Review Checklist

**Business Review**:
- [ ] BVJ demonstrates positive ROI
- [ ] Aligns with customer segment strategy
- [ ] Revenue impact validated

**Code Review**:
- [ ] 300/8 rule compliance verified
- [ ] Type safety confirmed
- [ ] No code duplication
- [ ] Tests achieve required coverage

**Security Review** (for customer data paths):
- [ ] Input validation
- [ ] Authentication/authorization
- [ ] Audit logging

### Approval Requirements

| PR Type | Required Approvals | Reviewers |
|---------|-------------------|-----------|
| **Revenue Path** | 2 senior engineers | Platform team |
| **Customer API** | 1 senior + 1 any | API team |
| **Internal Tool** | 1 engineer | Any team |
| **Documentation** | 1 engineer | Any team |

## Getting Help

- **Slack**: #netra-dev
- **Email**: dev@netrasystems.ai
- **Docs**: See `/docs` directory
- **Specs**: Read `/SPEC` files

## License

By contributing to Netra Apex, you agree that your contributions will be licensed under the project's proprietary license.

---

**Remember**: Every line of code should make money or save money. If it doesn't, don't write it.