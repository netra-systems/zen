# Performance Metrics Test Suite

**BVJ**: Enterprise segment - validates platform performance, supports SLA compliance

## Modular Test Architecture

This test suite has been split into focused modules following the 300-line limit:

### Core Test Files

| File | Lines | Purpose | Functions |
|------|-------|---------|-----------|
| `performance-metrics-core.cy.ts` | ~280 | Component initialization, navigation | ≤8 lines each |
| `performance-metrics-data.cy.ts` | ~290 | Metrics data validation, thresholds | ≤8 lines each |
| `performance-metrics-features.cy.ts` | ~295 | Advanced features, real-time updates | ≤8 lines each |
| `performance-metrics-quality.cy.ts` | ~285 | QA, accessibility, error handling | ≤8 lines each |

### Test Utilities

**File**: `cypress/support/metrics-test-utils.ts`
- Shared test helpers and constants
- Performance thresholds for Enterprise SLA compliance
- Reusable test patterns
- Metric validation functions

## Performance Thresholds

### Enterprise SLA Compliance
```typescript
PERFORMANCE_THRESHOLDS = {
  HEALTH_SCORE_MIN: 95,      // System health minimum
  UPTIME_MIN: 99.9,          // Availability requirement
  ERROR_RATE_MAX: 0.1,       // Maximum error rate %
  LATENCY_P99_MAX: 500,      // P99 latency limit (ms)
  LATENCY_P95_MAX: 200,      // P95 latency limit (ms)
  COST_PER_1K_REQUESTS_MAX: 5.0  // Cost efficiency limit
}
```

### SLA Thresholds
```typescript
SLA_THRESHOLDS = {
  AVAILABILITY: 99.95,       // Enterprise availability
  RESPONSE_TIME_P95: 150,    // Response time SLA
  ERROR_RATE: 0.05,          // Error rate SLA
  THROUGHPUT_MIN: 1000       // Minimum throughput
}
```

## Test Categories

### 1. Core Component Tests (`core.cy.ts`)
- Component initialization and rendering
- Tab navigation functionality
- Basic layout and styling verification
- State management across navigation

### 2. Data Validation Tests (`data.cy.ts`)
- Metric accuracy and format validation
- Threshold compliance checking
- Business KPI verification
- Data freshness and quality indicators

### 3. Advanced Features Tests (`features.cy.ts`)
- Real-time updates and WebSocket handling
- Data visualization and charting
- Filtering and time range controls
- Export and reporting capabilities
- Drill-down and correlation analysis

### 4. Quality Assurance Tests (`quality.cy.ts`)
- Mobile responsiveness across devices
- Accessibility compliance (WCAG 2.1)
- Error handling and resilience
- Performance and load testing
- Security and data protection
- Cross-browser compatibility

## Usage

### Run Specific Test Categories
```bash
# Core functionality only
npx cypress run --spec "cypress/e2e/performance-metrics-core.cy.ts"

# Data validation and thresholds
npx cypress run --spec "cypress/e2e/performance-metrics-data.cy.ts"

# Advanced features
npx cypress run --spec "cypress/e2e/performance-metrics-features.cy.ts"

# Quality assurance
npx cypress run --spec "cypress/e2e/performance-metrics-quality.cy.ts"

# All performance metrics tests
npx cypress run --spec "cypress/e2e/performance-metrics-*.cy.ts"
```

### Test Helper Usage
```typescript
import { MetricsTestHelper, PERFORMANCE_THRESHOLDS } from '../support/metrics-test-utils'

// Setup and navigation
MetricsTestHelper.setupViewport()
MetricsTestHelper.navigateToMetrics()
MetricsTestHelper.switchToTab('Latency')

// Validation
MetricsTestHelper.verifyThresholdCompliance('[data-testid="p99-latency"]', 
  PERFORMANCE_THRESHOLDS.LATENCY_P99_MAX)
```

## Business Value Alignment

### Enterprise Customer Focus
- **SLA Compliance**: Validates 99.95% availability requirement
- **Performance Monitoring**: Ensures sub-200ms P95 latency
- **Cost Optimization**: Validates cost efficiency metrics
- **Quality Assurance**: Enterprise-grade accessibility and security

### Revenue Impact
- **Customer Retention**: Performance validation prevents churn
- **Premium Pricing**: Quality metrics support enterprise pricing
- **Scalability Proof**: Load testing validates platform capabilities
- **Compliance**: Accessibility and security tests support enterprise sales

## Maintenance Guidelines

### Adding New Tests
1. Choose appropriate module based on test purpose
2. Ensure functions remain ≤8 lines
3. Use shared utilities from `metrics-test-utils.ts`
4. Validate against business thresholds
5. Update this documentation

### Threshold Updates
1. Modify constants in `metrics-test-utils.ts`
2. Update validation logic in test files
3. Verify Enterprise SLA alignment
4. Document business justification

### Performance Considerations
- Tests should complete within 2 minutes
- Use data fixtures for large datasets
- Implement proper wait strategies
- Monitor test execution time trends

## Architecture Compliance

✅ **300-Line Limit**: All files under 300 lines
✅ **8-Line Functions**: All functions ≤8 lines
✅ **Modular Design**: Clear separation of concerns
✅ **Single Responsibility**: Each module has focused purpose
✅ **Business Value**: Aligned with Enterprise segment needs