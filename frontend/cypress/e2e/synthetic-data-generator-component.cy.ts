/// <reference types="cypress" />

describe('SyntheticDataGenerator Component E2E Tests', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/synthetic-data-generation')
    cy.wait(500)
  })

  describe('Component Initialization', () => {
    it('should render SyntheticDataGenerator component', () => {
      cy.get('[data-testid="synthetic-data-generator"]').should('be.visible')
    })

    it('should display component title', () => {
      cy.contains('h2', 'Synthetic Data Generator').should('be.visible')
    })

    it('should show component description', () => {
      cy.contains('Generate realistic test data').should('be.visible')
    })

    it('should have glassmorphic styling', () => {
      cy.get('.backdrop-blur-sm').should('exist')
      cy.get('.bg-white/5').should('exist')
    })

    it('should display all main sections', () => {
      cy.contains('Configuration').should('be.visible')
      cy.contains('Output').should('be.visible')
      cy.contains('Actions').should('be.visible')
    })
  })

  describe('Configuration Panel', () => {
    it('should display trace count input', () => {
      cy.contains('label', 'Number of Traces').should('be.visible')
      cy.get('input[name="traceCount"]').should('be.visible')
    })

    it('should have default trace count', () => {
      cy.get('input[name="traceCount"]').should('have.value', '1000')
    })

    it('should update trace count', () => {
      cy.get('input[name="traceCount"]').clear().type('5000')
      cy.get('input[name="traceCount"]').should('have.value', '5000')
    })

    it('should display user count input', () => {
      cy.contains('label', 'Number of Users').should('be.visible')
      cy.get('input[name="userCount"]').should('be.visible')
    })

    it('should update user count', () => {
      cy.get('input[name="userCount"]').clear().type('250')
      cy.get('input[name="userCount"]').should('have.value', '250')
    })

    it('should display error rate slider', () => {
      cy.contains('label', 'Error Rate (%)').should('be.visible')
      cy.get('input[type="range"][name="errorRate"]').should('be.visible')
    })

    it('should show error rate value', () => {
      cy.get('input[type="range"][name="errorRate"]').invoke('val', 10).trigger('input')
      cy.get('[data-testid="error-rate-value"]').should('contain', '10%')
    })

    it('should validate minimum values', () => {
      cy.get('input[name="traceCount"]').clear().type('0')
      cy.contains('Minimum value is 1').should('be.visible')
    })

    it('should validate maximum values', () => {
      cy.get('input[name="traceCount"]').clear().type('1000001')
      cy.contains('Maximum value is 1000000').should('be.visible')
    })
  })

  describe('Workload Pattern Selection', () => {
    it('should display workload pattern dropdown', () => {
      cy.contains('label', 'Workload Pattern').should('be.visible')
      cy.get('select[name="workloadPattern"]').should('be.visible')
    })

    it('should show pattern options', () => {
      cy.get('select[name="workloadPattern"]').click()
      const patterns = ['Steady', 'Burst', 'Growth', 'Periodic', 'Random', 'Custom']
      patterns.forEach(pattern => {
        cy.get('select[name="workloadPattern"]').contains(pattern).should('exist')
      })
    })

    it('should select workload pattern', () => {
      cy.get('select[name="workloadPattern"]').select('Burst')
      cy.get('select[name="workloadPattern"]').should('have.value', 'burst')
    })

    it('should show pattern preview', () => {
      cy.get('select[name="workloadPattern"]').select('Periodic')
      cy.get('[data-testid="pattern-preview-chart"]').should('be.visible')
    })

    it('should display pattern description', () => {
      cy.get('select[name="workloadPattern"]').select('Growth')
      cy.contains('Gradually increasing load').should('be.visible')
    })

    it('should enable custom pattern editor', () => {
      cy.get('select[name="workloadPattern"]').select('Custom')
      cy.get('[data-testid="custom-pattern-editor"]').should('be.visible')
    })
  })

  describe('Table Configuration', () => {
    it('should display table selection', () => {
      cy.contains('label', 'Target Table').should('be.visible')
      cy.get('select[name="targetTable"]').should('be.visible')
    })

    it('should show existing tables', () => {
      cy.get('select[name="targetTable"]').click()
      cy.contains('traces_synthetic').should('exist')
      cy.contains('metrics_synthetic').should('exist')
    })

    it('should allow creating new table', () => {
      cy.get('[data-testid="create-table-btn"]').click()
      cy.get('[data-testid="table-name-input"]').type('test_table')
      cy.get('[data-testid="create-table-confirm"]').click()
      cy.contains('test_table').should('be.visible')
    })

    it('should validate table name', () => {
      cy.get('[data-testid="create-table-btn"]').click()
      cy.get('[data-testid="table-name-input"]').type('123-invalid!')
      cy.contains('Invalid table name').should('be.visible')
    })

    it('should display table schema', () => {
      cy.get('select[name="targetTable"]').select('traces_synthetic')
      cy.get('[data-testid="schema-preview"]').click()
      cy.contains('trace_id').should('be.visible')
      cy.contains('timestamp').should('be.visible')
      cy.contains('duration').should('be.visible')
    })

    it('should manage table retention', () => {
      cy.get('[data-testid="table-settings"]').click()
      cy.contains('Retention Period').should('be.visible')
      cy.get('select[name="retention"]').select('7 days')
    })
  })

  describe('Generation Controls', () => {
    it('should display generate button', () => {
      cy.get('[data-testid="generate-btn"]').should('be.visible')
      cy.contains('Generate Data').should('be.visible')
    })

    it('should enable generate with valid config', () => {
      cy.get('input[name="traceCount"]').clear().type('100')
      cy.get('[data-testid="generate-btn"]').should('not.be.disabled')
    })

    it('should disable generate with invalid config', () => {
      cy.get('input[name="traceCount"]').clear()
      cy.get('[data-testid="generate-btn"]').should('be.disabled')
    })

    it('should show estimated time', () => {
      cy.get('input[name="traceCount"]').clear().type('10000')
      cy.contains('Estimated time').should('be.visible')
      cy.contains(/\d+ seconds?/).should('be.visible')
    })

    it('should show estimated size', () => {
      cy.get('input[name="traceCount"]').clear().type('10000')
      cy.contains('Estimated size').should('be.visible')
      cy.contains(/\d+\.?\d* MB/).should('be.visible')
    })

    it('should display warning for large datasets', () => {
      cy.get('input[name="traceCount"]').clear().type('100000')
      cy.contains('Large dataset warning').should('be.visible')
    })
  })

  describe('Generation Process', () => {
    it('should start generation', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.contains('Generating').should('be.visible')
    })

    it('should show progress bar', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.get('[data-testid="progress-bar"]').should('be.visible')
    })

    it('should display progress percentage', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.get('[data-testid="progress-percent"]').should('contain', '%')
    })

    it('should show records generated count', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.get('[data-testid="records-count"]').should('contain', /\d+/)
    })

    it('should display generation speed', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.contains('records/sec').should('be.visible')
    })

    it('should allow canceling generation', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.get('[data-testid="cancel-btn"]').should('be.visible')
      cy.get('[data-testid="cancel-btn"]').click()
      cy.contains('Cancelled').should('be.visible')
    })

    it('should complete generation', () => {
      cy.get('input[name="traceCount"]').clear().type('10')
      cy.get('[data-testid="generate-btn"]').click()
      cy.wait(3000)
      cy.contains('Generation Complete').should('be.visible')
    })
  })

  describe('Output Display', () => {
    beforeEach(() => {
      cy.get('input[name="traceCount"]').clear().type('10')
      cy.get('[data-testid="generate-btn"]').click()
      cy.wait(3000)
    })

    it('should display output section', () => {
      cy.get('[data-testid="output-section"]').should('be.visible')
    })

    it('should show data preview table', () => {
      cy.get('[data-testid="preview-table"]').should('be.visible')
      cy.get('[data-testid="preview-row"]').should('have.length.at.least', 5)
    })

    it('should display column headers', () => {
      cy.contains('th', 'Trace ID').should('be.visible')
      cy.contains('th', 'Timestamp').should('be.visible')
      cy.contains('th', 'Duration').should('be.visible')
      cy.contains('th', 'Status').should('be.visible')
    })

    it('should show generated statistics', () => {
      cy.contains('Statistics').should('be.visible')
      cy.contains('Total Records').should('be.visible')
      cy.contains('Success Rate').should('be.visible')
      cy.contains('Avg Duration').should('be.visible')
    })

    it('should allow pagination', () => {
      cy.get('[data-testid="next-page"]').click()
      cy.get('[data-testid="page-indicator"]').should('contain', '2')
    })

    it('should refresh preview', () => {
      cy.get('[data-testid="refresh-preview"]').click()
      cy.get('[data-testid="preview-loading"]').should('be.visible')
    })
  })

  describe('Data Validation', () => {
    beforeEach(() => {
      cy.get('input[name="traceCount"]').clear().type('10')
      cy.get('[data-testid="generate-btn"]').click()
      cy.wait(3000)
    })

    it('should display validation button', () => {
      cy.get('[data-testid="validate-btn"]').should('be.visible')
    })

    it('should run validation', () => {
      cy.get('[data-testid="validate-btn"]').click()
      cy.contains('Validating').should('be.visible')
    })

    it('should show validation results', () => {
      cy.get('[data-testid="validate-btn"]').click()
      cy.wait(2000)
      cy.contains('Validation Complete').should('be.visible')
    })

    it('should display validation checks', () => {
      cy.get('[data-testid="validate-btn"]').click()
      cy.wait(2000)
      cy.contains('Schema Compliance').should('be.visible')
      cy.contains('Data Integrity').should('be.visible')
      cy.contains('Range Validation').should('be.visible')
    })

    it('should show validation errors if any', () => {
      cy.get('input[name="errorRate"]').invoke('val', 100).trigger('input')
      cy.get('[data-testid="generate-btn"]').click()
      cy.wait(3000)
      cy.get('[data-testid="validate-btn"]').click()
      cy.wait(2000)
      cy.contains('Warning').should('be.visible')
    })
  })

  describe('Export Functions', () => {
    beforeEach(() => {
      cy.get('input[name="traceCount"]').clear().type('10')
      cy.get('[data-testid="generate-btn"]').click()
      cy.wait(3000)
    })

    it('should display export options', () => {
      cy.get('[data-testid="export-menu"]').click()
      cy.contains('CSV').should('be.visible')
      cy.contains('JSON').should('be.visible')
      cy.contains('Parquet').should('be.visible')
    })

    it('should export as CSV', () => {
      cy.get('[data-testid="export-menu"]').click()
      cy.contains('CSV').click()
      cy.readFile('cypress/downloads/synthetic_data.csv').should('exist')
    })

    it('should export as JSON', () => {
      cy.get('[data-testid="export-menu"]').click()
      cy.contains('JSON').click()
      cy.readFile('cypress/downloads/synthetic_data.json').should('exist')
    })

    it('should show export progress', () => {
      cy.get('[data-testid="export-menu"]').click()
      cy.contains('CSV').click()
      cy.contains('Exporting').should('be.visible')
    })

    it('should copy to clipboard', () => {
      cy.get('[data-testid="copy-data"]').click()
      cy.contains('Copied to clipboard').should('be.visible')
    })
  })

  describe('Advanced Configuration', () => {
    it('should show advanced options toggle', () => {
      cy.get('[data-testid="advanced-toggle"]').should('be.visible')
    })

    it('should expand advanced options', () => {
      cy.get('[data-testid="advanced-toggle"]').click()
      cy.get('[data-testid="advanced-options"]').should('be.visible')
    })

    it('should display latency distribution settings', () => {
      cy.get('[data-testid="advanced-toggle"]').click()
      cy.contains('Latency Distribution').should('be.visible')
      cy.get('input[name="minLatency"]').should('be.visible')
      cy.get('input[name="maxLatency"]').should('be.visible')
    })

    it('should configure service names', () => {
      cy.get('[data-testid="advanced-toggle"]').click()
      cy.get('[data-testid="add-service"]').click()
      cy.get('input[name="serviceName"]').type('api-gateway')
      cy.get('[data-testid="add-service-confirm"]').click()
      cy.contains('api-gateway').should('be.visible')
    })

    it('should set custom fields', () => {
      cy.get('[data-testid="advanced-toggle"]').click()
      cy.get('[data-testid="add-field"]').click()
      cy.get('input[name="fieldName"]').type('region')
      cy.get('select[name="fieldType"]').select('string')
      cy.get('[data-testid="add-field-confirm"]').click()
      cy.contains('region').should('be.visible')
    })

    it('should configure data distribution', () => {
      cy.get('[data-testid="advanced-toggle"]').click()
      cy.get('select[name="distribution"]').select('normal')
      cy.get('input[name="mean"]').type('100')
      cy.get('input[name="stddev"]').type('20')
    })
  })

  describe('Templates and Presets', () => {
    it('should display preset selector', () => {
      cy.get('[data-testid="preset-selector"]').should('be.visible')
    })

    it('should show preset options', () => {
      cy.get('[data-testid="preset-selector"]').click()
      cy.contains('E-commerce').should('be.visible')
      cy.contains('IoT Sensors').should('be.visible')
      cy.contains('API Gateway').should('be.visible')
    })

    it('should apply preset configuration', () => {
      cy.get('[data-testid="preset-selector"]').select('E-commerce')
      cy.get('input[name="traceCount"]').should('have.value', '5000')
      cy.get('select[name="workloadPattern"]').should('have.value', 'periodic')
    })

    it('should save custom template', () => {
      cy.get('input[name="traceCount"]').clear().type('2500')
      cy.get('[data-testid="save-template"]').click()
      cy.get('input[name="templateName"]').type('My Template')
      cy.get('[data-testid="save-template-confirm"]').click()
      cy.contains('Template saved').should('be.visible')
    })

    it('should load custom template', () => {
      cy.get('[data-testid="template-menu"]').click()
      cy.contains('My Template').click()
      cy.get('input[name="traceCount"]').should('have.value', '2500')
    })

    it('should delete template', () => {
      cy.get('[data-testid="template-menu"]').click()
      cy.get('[data-testid="delete-template"]').first().click()
      cy.contains('Confirm').click()
      cy.contains('Template deleted').should('be.visible')
    })
  })

  describe('Real-time Monitoring', () => {
    it('should display monitoring panel during generation', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.get('[data-testid="monitoring-panel"]').should('be.visible')
    })

    it('should show CPU usage', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.contains('CPU Usage').should('be.visible')
      cy.get('[data-testid="cpu-meter"]').should('be.visible')
    })

    it('should display memory usage', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.contains('Memory').should('be.visible')
      cy.get('[data-testid="memory-meter"]').should('be.visible')
    })

    it('should show throughput graph', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.get('[data-testid="throughput-graph"]').should('be.visible')
    })

    it('should display error count', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.contains('Errors').should('be.visible')
      cy.get('[data-testid="error-count"]').should('contain', '0')
    })
  })

  describe('History and Logs', () => {
    it('should display history tab', () => {
      cy.get('[data-testid="history-tab"]').should('be.visible')
    })

    it('should show generation history', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.wait(3000)
      cy.get('[data-testid="history-tab"]').click()
      cy.get('[data-testid="history-item"]').should('have.length.at.least', 1)
    })

    it('should display history details', () => {
      cy.get('[data-testid="history-tab"]').click()
      cy.get('[data-testid="history-item"]').first().should('contain', 'traces')
      cy.get('[data-testid="history-item"]').first().should('contain', 'ago')
    })

    it('should allow reusing history config', () => {
      cy.get('[data-testid="history-tab"]').click()
      cy.get('[data-testid="reuse-config"]').first().click()
      cy.get('input[name="traceCount"]').should('have.value')
    })

    it('should show generation logs', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.get('[data-testid="logs-tab"]').click()
      cy.get('[data-testid="log-entry"]').should('have.length.at.least', 1)
    })

    it('should clear history', () => {
      cy.get('[data-testid="history-tab"]').click()
      cy.get('[data-testid="clear-history"]').click()
      cy.contains('Confirm').click()
      cy.contains('History cleared').should('be.visible')
    })
  })

  describe('API Integration', () => {
    it('should display API endpoint info', () => {
      cy.get('[data-testid="api-info"]').click()
      cy.contains('/api/synthetic-data/generate').should('be.visible')
    })

    it('should show API request example', () => {
      cy.get('[data-testid="api-info"]').click()
      cy.contains('POST').should('be.visible')
      cy.get('code').should('contain', 'traceCount')
    })

    it('should display API response format', () => {
      cy.get('[data-testid="api-info"]').click()
      cy.contains('Response').should('be.visible')
      cy.get('code').should('contain', 'success')
    })

    it('should copy API snippet', () => {
      cy.get('[data-testid="api-info"]').click()
      cy.get('[data-testid="copy-snippet"]').click()
      cy.contains('Copied').should('be.visible')
    })
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt to mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="synthetic-data-generator"]').should('be.visible')
    })

    it('should stack configuration fields', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="config-section"]').should('have.css', 'flex-direction', 'column')
    })

    it('should show mobile-friendly controls', () => {
      cy.viewport('iphone-x')
      cy.get('input[type="range"]').should('have.css', 'width', '100%')
    })

    it('should handle mobile generation', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="generate-btn"]').click()
      cy.get('[data-testid="progress-bar"]').should('be.visible')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      cy.get('[aria-label]').should('have.length.at.least', 10)
    })

    it('should support keyboard navigation', () => {
      cy.get('input[name="traceCount"]').focus()
      cy.focused().tab()
      cy.focused().should('have.attr', 'name', 'userCount')
    })

    it('should announce generation status', () => {
      cy.get('[data-testid="generate-btn"]').click()
      cy.get('[role="status"]').should('contain', 'Generating')
    })

    it('should have form labels', () => {
      cy.get('label[for="traceCount"]').should('contain', 'Traces')
      cy.get('label[for="userCount"]').should('contain', 'Users')
    })
  })

  describe('Error Handling', () => {
    it('should handle generation failures', () => {
      cy.intercept('POST', '/api/synthetic-data/generate', { statusCode: 500 })
      cy.get('[data-testid="generate-btn"]').click()
      cy.contains('Generation failed').should('be.visible')
    })

    it('should show retry option', () => {
      cy.intercept('POST', '/api/synthetic-data/generate', { statusCode: 500 })
      cy.get('[data-testid="generate-btn"]').click()
      cy.contains('Retry').should('be.visible')
    })

    it('should validate configuration before generation', () => {
      cy.get('input[name="traceCount"]').clear()
      cy.get('[data-testid="generate-btn"]').click()
      cy.contains('Invalid configuration').should('be.visible')
    })

    it('should handle timeout', () => {
      cy.intercept('POST', '/api/synthetic-data/generate', (req) => {
        req.reply((res) => {
          res.delay(30000)
        })
      })
      cy.get('[data-testid="generate-btn"]').click()
      cy.wait(10000)
      cy.contains('Request timed out').should('be.visible')
    })
  })
})