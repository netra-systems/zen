/// <reference types="cypress" />

describe('Synthetic Data Generation Page E2E Tests', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/synthetic-data-generation')
  })

  describe('Page Load and Initial State', () => {
    it('should load the synthetic data generation page', () => {
      cy.url().should('include', '/synthetic-data-generation')
      cy.contains('Synthetic Data Generation').should('be.visible')
    })

    it('should display the main generator component', () => {
      cy.get('[data-testid="synthetic-data-generator"]').should('be.visible')
    })

    it('should show configuration panel', () => {
      cy.contains('Configuration').should('be.visible')
      cy.contains('Parameters').should('be.visible')
    })

    it('should display glassmorphic design elements', () => {
      cy.get('.backdrop-blur').should('exist')
      cy.get('.bg-opacity-20').should('exist')
    })
  })

  describe('Configuration Parameters', () => {
    it('should display all configuration fields', () => {
      cy.contains('Number of Traces').should('be.visible')
      cy.contains('Number of Users').should('be.visible')
      cy.contains('Error Rate').should('be.visible')
      cy.contains('Workload Pattern').should('be.visible')
    })

    it('should have default values set', () => {
      cy.get('input[name="traces"]').should('have.value', '1000')
      cy.get('input[name="users"]').should('have.value', '100')
      cy.get('input[name="errorRate"]').should('have.value', '5')
    })

    it('should allow updating trace count', () => {
      cy.get('input[name="traces"]').clear().type('5000')
      cy.get('input[name="traces"]').should('have.value', '5000')
    })

    it('should allow updating user count', () => {
      cy.get('input[name="users"]').clear().type('500')
      cy.get('input[name="users"]').should('have.value', '500')
    })

    it('should allow updating error rate with slider', () => {
      cy.get('input[type="range"][name="errorRate"]').invoke('val', 15).trigger('input')
      cy.contains('15%').should('be.visible')
    })

    it('should validate input ranges', () => {
      cy.get('input[name="traces"]').clear().type('-100')
      cy.contains('Must be positive').should('be.visible')
    })

    it('should show tooltips for parameters', () => {
      cy.get('[data-testid="traces-tooltip"]').trigger('mouseenter')
      cy.contains('Number of synthetic traces to generate').should('be.visible')
    })
  })

  describe('Workload Pattern Selection', () => {
    it('should display workload pattern options', () => {
      const patterns = ['Steady', 'Burst', 'Growth', 'Periodic', 'Random']
      patterns.forEach(pattern => {
        cy.contains(pattern).should('be.visible')
      })
    })

    it('should allow selecting workload pattern', () => {
      cy.contains('Burst').click()
      cy.contains('Burst').parent().should('have.class', 'ring-2')
    })

    it('should show pattern description on hover', () => {
      cy.contains('Periodic').trigger('mouseenter')
      cy.contains('Regular cycles of high and low activity').should('be.visible')
    })

    it('should update preview based on pattern', () => {
      cy.contains('Growth').click()
      cy.get('[data-testid="pattern-preview"]').should('contain', 'Growth')
    })

    it('should allow pattern customization', () => {
      cy.contains('Burst').click()
      cy.contains('Customize Pattern').click()
      cy.get('[data-testid="burst-intensity"]').should('be.visible')
      cy.get('[data-testid="burst-frequency"]').should('be.visible')
    })
  })

  describe('Table Management', () => {
    it('should display table selection dropdown', () => {
      cy.contains('Target Table').should('be.visible')
      cy.get('select[name="targetTable"]').should('be.visible')
    })

    it('should show available tables', () => {
      cy.get('select[name="targetTable"]').click()
      cy.contains('traces_synthetic').should('be.visible')
      cy.contains('metrics_synthetic').should('be.visible')
      cy.contains('logs_synthetic').should('be.visible')
    })

    it('should allow creating new table', () => {
      cy.contains('Create New Table').click()
      cy.get('[data-testid="new-table-modal"]').should('be.visible')
      cy.get('input[name="tableName"]').type('custom_synthetic_table')
      cy.contains('button', 'Create').click()
      cy.contains('custom_synthetic_table').should('be.visible')
    })

    it('should show table schema preview', () => {
      cy.get('select[name="targetTable"]').select('traces_synthetic')
      cy.contains('Schema Preview').should('be.visible')
      cy.contains('trace_id').should('be.visible')
      cy.contains('timestamp').should('be.visible')
    })

    it('should validate table name format', () => {
      cy.contains('Create New Table').click()
      cy.get('input[name="tableName"]').type('invalid-table-name!')
      cy.contains('Invalid table name').should('be.visible')
    })
  })

  describe('Data Generation Process', () => {
    it('should have generate button', () => {
      cy.contains('button', 'Generate Data').should('be.visible')
    })

    it('should disable generate button without configuration', () => {
      cy.get('input[name="traces"]').clear()
      cy.contains('button', 'Generate Data').should('be.disabled')
    })

    it('should start generation on button click', () => {
      cy.contains('button', 'Generate Data').click()
      cy.contains('Generating').should('be.visible')
      cy.get('[data-testid="progress-bar"]').should('be.visible')
    })

    it('should show progress during generation', () => {
      cy.contains('button', 'Generate Data').click()
      cy.get('[data-testid="progress-percentage"]').should('be.visible')
      cy.contains('%').should('be.visible')
    })

    it('should display estimated time', () => {
      cy.contains('button', 'Generate Data').click()
      cy.contains('Estimated time').should('be.visible')
      cy.contains(/\d+ seconds?/).should('be.visible')
    })

    it('should show completion message', () => {
      cy.contains('button', 'Generate Data').click()
      cy.wait(5000)
      cy.contains('Generation Complete').should('be.visible')
      cy.contains('1000 traces generated').should('be.visible')
    })

    it('should allow canceling generation', () => {
      cy.contains('button', 'Generate Data').click()
      cy.contains('button', 'Cancel').should('be.visible')
      cy.contains('button', 'Cancel').click()
      cy.contains('Generation Cancelled').should('be.visible')
    })
  })

  describe('Preview and Validation', () => {
    it('should show data preview section', () => {
      cy.contains('Data Preview').should('be.visible')
      cy.get('[data-testid="data-preview-table"]').should('be.visible')
    })

    it('should display sample records after generation', () => {
      cy.contains('button', 'Generate Data').click()
      cy.wait(3000)
      cy.get('[data-testid="preview-row"]').should('have.length.at.least', 5)
    })

    it('should show data statistics', () => {
      cy.contains('button', 'Generate Data').click()
      cy.wait(3000)
      cy.contains('Statistics').should('be.visible')
      cy.contains('Total Records').should('be.visible')
      cy.contains('Average Latency').should('be.visible')
      cy.contains('Error Count').should('be.visible')
    })

    it('should allow refreshing preview', () => {
      cy.contains('button', 'Generate Data').click()
      cy.wait(3000)
      cy.contains('button', 'Refresh Preview').click()
      cy.get('[data-testid="preview-loading"]').should('be.visible')
    })

    it('should validate generated data format', () => {
      cy.contains('button', 'Generate Data').click()
      cy.wait(3000)
      cy.contains('Validate Data').click()
      cy.contains('Validation Successful').should('be.visible')
    })
  })

  describe('Export and Download', () => {
    it('should show export options after generation', () => {
      cy.contains('button', 'Generate Data').click()
      cy.wait(3000)
      cy.contains('Export Options').should('be.visible')
    })

    it('should allow exporting as CSV', () => {
      cy.contains('button', 'Generate Data').click()
      cy.wait(3000)
      cy.contains('Export as CSV').click()
      cy.readFile('cypress/downloads/synthetic_data.csv').should('exist')
    })

    it('should allow exporting as JSON', () => {
      cy.contains('button', 'Generate Data').click()
      cy.wait(3000)
      cy.contains('Export as JSON').click()
      cy.readFile('cypress/downloads/synthetic_data.json').should('exist')
    })

    it('should allow copying to clipboard', () => {
      cy.contains('button', 'Generate Data').click()
      cy.wait(3000)
      cy.contains('Copy to Clipboard').click()
      cy.contains('Copied!').should('be.visible')
    })

    it('should show export size warning for large datasets', () => {
      cy.get('input[name="traces"]').clear().type('100000')
      cy.contains('button', 'Generate Data').click()
      cy.wait(3000)
      cy.contains('Export as CSV').click()
      cy.contains('Large dataset warning').should('be.visible')
    })
  })

  describe('Advanced Configuration', () => {
    it('should show advanced options toggle', () => {
      cy.contains('Advanced Options').should('be.visible')
    })

    it('should expand advanced configuration', () => {
      cy.contains('Advanced Options').click()
      cy.contains('Latency Distribution').should('be.visible')
      cy.contains('Service Names').should('be.visible')
      cy.contains('Custom Fields').should('be.visible')
    })

    it('should allow configuring latency distribution', () => {
      cy.contains('Advanced Options').click()
      cy.get('input[name="minLatency"]').type('10')
      cy.get('input[name="maxLatency"]').type('1000')
      cy.get('select[name="distribution"]').select('normal')
    })

    it('should allow adding custom service names', () => {
      cy.contains('Advanced Options').click()
      cy.get('input[name="serviceName"]').type('api-gateway')
      cy.contains('button', 'Add Service').click()
      cy.contains('api-gateway').should('be.visible')
    })

    it('should allow defining custom fields', () => {
      cy.contains('Advanced Options').click()
      cy.contains('Add Custom Field').click()
      cy.get('input[name="fieldName"]').type('region')
      cy.get('select[name="fieldType"]').select('string')
      cy.contains('button', 'Add Field').click()
      cy.contains('region').should('be.visible')
    })

    it('should save configuration as template', () => {
      cy.contains('Advanced Options').click()
      cy.contains('Save as Template').click()
      cy.get('input[name="templateName"]').type('My Config')
      cy.contains('button', 'Save').click()
      cy.contains('Template Saved').should('be.visible')
    })
  })

  describe('Real-time Status and Monitoring', () => {
    it('should show generation status in real-time', () => {
      cy.contains('button', 'Generate Data').click()
      cy.contains('Initializing').should('be.visible')
      cy.contains('Generating').should('be.visible')
    })

    it('should display records per second metric', () => {
      cy.contains('button', 'Generate Data').click()
      cy.contains('Records/sec').should('be.visible')
      cy.get('[data-testid="throughput-metric"]').should('contain', /\d+/)
    })

    it('should show memory usage indicator', () => {
      cy.contains('button', 'Generate Data').click()
      cy.contains('Memory Usage').should('be.visible')
      cy.get('[data-testid="memory-bar"]').should('be.visible')
    })

    it('should display error log if generation fails', () => {
      cy.get('input[name="traces"]').clear().type('999999999')
      cy.contains('button', 'Generate Data').click()
      cy.wait(2000)
      cy.contains('Error').should('be.visible')
      cy.get('[data-testid="error-log"]').should('be.visible')
    })

    it('should show warning for high resource usage', () => {
      cy.get('input[name="traces"]').clear().type('50000')
      cy.contains('button', 'Generate Data').click()
      cy.contains('High resource usage').should('be.visible')
    })
  })

  describe('History and Previous Generations', () => {
    it('should display generation history tab', () => {
      cy.contains('History').should('be.visible')
    })

    it('should show previous generations list', () => {
      cy.contains('History').click()
      cy.get('[data-testid="history-item"]').should('have.length.at.least', 0)
    })

    it('should display generation metadata', () => {
      cy.contains('button', 'Generate Data').click()
      cy.wait(3000)
      cy.contains('History').click()
      cy.get('[data-testid="history-item"]').first().should('contain', 'traces')
      cy.get('[data-testid="history-item"]').first().should('contain', 'ago')
    })

    it('should allow reusing previous configuration', () => {
      cy.contains('button', 'Generate Data').click()
      cy.wait(3000)
      cy.contains('History').click()
      cy.get('[data-testid="reuse-config"]').first().click()
      cy.get('input[name="traces"]').should('have.value', '1000')
    })

    it('should allow deleting history items', () => {
      cy.contains('History').click()
      cy.get('[data-testid="delete-history"]').first().click()
      cy.contains('Confirm Delete').click()
      cy.contains('Deleted').should('be.visible')
    })
  })

  describe('Integration with Other Components', () => {
    it('should integrate with demo chat', () => {
      cy.contains('Use in Demo').should('be.visible')
      cy.contains('Use in Demo').click()
      cy.url().should('include', '/demo')
    })

    it('should provide API endpoint information', () => {
      cy.contains('API Integration').click()
      cy.contains('/api/synthetic-data').should('be.visible')
      cy.contains('POST').should('be.visible')
    })

    it('should show code examples', () => {
      cy.contains('Code Examples').click()
      cy.contains('Python').should('be.visible')
      cy.contains('JavaScript').should('be.visible')
      cy.contains('curl').should('be.visible')
    })

    it('should copy code snippets', () => {
      cy.contains('Code Examples').click()
      cy.contains('Python').click()
      cy.get('[data-testid="copy-code"]').click()
      cy.contains('Copied').should('be.visible')
    })
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt to mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.contains('Synthetic Data Generation').should('be.visible')
      cy.get('[data-testid="synthetic-data-generator"]').should('be.visible')
    })

    it('should stack configuration fields on mobile', () => {
      cy.viewport('iphone-x')
      cy.get('input[name="traces"]').should('have.css', 'width', '100%')
    })

    it('should show mobile-optimized controls', () => {
      cy.viewport('iphone-x')
      cy.get('input[type="range"]').should('be.visible')
      cy.contains('button', 'Generate Data').should('have.css', 'width', '100%')
    })

    it('should handle mobile pattern selection', () => {
      cy.viewport('iphone-x')
      cy.contains('Burst').click()
      cy.contains('Burst').parent().should('have.class', 'ring-2')
    })
  })

  describe('Performance and Error Handling', () => {
    it('should handle network errors gracefully', () => {
      cy.intercept('POST', '/api/synthetic-data/generate', { statusCode: 500 })
      cy.contains('button', 'Generate Data').click()
      cy.contains('Generation failed').should('be.visible')
      cy.contains('Retry').should('be.visible')
    })

    it('should timeout long-running generations', () => {
      cy.intercept('POST', '/api/synthetic-data/generate', (req) => {
        req.reply((res) => {
          res.delay(30000)
          res.send({ success: true })
        })
      })
      cy.contains('button', 'Generate Data').click()
      cy.wait(10000)
      cy.contains('Generation timed out').should('be.visible')
    })

    it('should handle invalid server responses', () => {
      cy.intercept('POST', '/api/synthetic-data/generate', { body: null })
      cy.contains('button', 'Generate Data').click()
      cy.contains('Invalid response').should('be.visible')
    })

    it('should prevent duplicate submissions', () => {
      cy.contains('button', 'Generate Data').click()
      cy.contains('button', 'Generate Data').should('be.disabled')
    })

    it('should validate maximum limits', () => {
      cy.get('input[name="traces"]').clear().type('10000000')
      cy.contains('Exceeds maximum limit').should('be.visible')
      cy.contains('button', 'Generate Data').should('be.disabled')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      cy.get('[aria-label]').should('have.length.at.least', 10)
    })

    it('should support keyboard navigation', () => {
      cy.get('body').tab()
      cy.focused().should('have.attr', 'name', 'traces')
      cy.focused().tab()
      cy.focused().should('have.attr', 'name', 'users')
    })

    it('should announce status changes to screen readers', () => {
      cy.get('[role="status"]').should('exist')
      cy.contains('button', 'Generate Data').click()
      cy.get('[role="status"]').should('contain', 'Generating')
    })

    it('should have proper form labels', () => {
      cy.get('label[for="traces"]').should('contain', 'Number of Traces')
      cy.get('label[for="users"]').should('contain', 'Number of Users')
    })
  })
})