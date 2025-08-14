/// <reference types="cypress" />

describe('ROICalculator Component E2E Tests', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/demo')
    cy.contains('Technology').click()
    cy.contains('ROI Calculator').click()
    cy.wait(500)
  })

  describe('Component Initialization', () => {
    it('should render ROI Calculator component', () => {
      cy.get('[data-testid="roi-calculator"]').should('be.visible')
    })

    it('should display calculator heading', () => {
      cy.contains('h2', 'Calculate Your AI Optimization Savings').should('be.visible')
    })

    it('should show industry context', () => {
      cy.contains('Technology').should('be.visible')
      cy.contains('industry-specific').should('be.visible')
    })

    it('should display all input sections', () => {
      cy.contains('Infrastructure Metrics').should('be.visible')
      cy.contains('Operational Metrics').should('be.visible')
      cy.contains('AI Workload Details').should('be.visible')
    })

    it('should have glassmorphic styling', () => {
      cy.get('.backdrop-blur-md').should('exist')
      cy.get('.bg-opacity-10').should('exist')
    })
  })

  describe('Infrastructure Metrics Inputs', () => {
    it('should display monthly spend slider', () => {
      cy.contains('Current Monthly AI Spend').should('be.visible')
      cy.get('input[type="range"][data-testid="monthly-spend"]').should('be.visible')
    })

    it('should update spend value on slider change', () => {
      cy.get('input[type="range"][data-testid="monthly-spend"]')
        .invoke('val', 75000)
        .trigger('input')
      cy.contains('$75,000').should('be.visible')
    })

    it('should display number of models input', () => {
      cy.contains('Number of AI Models').should('be.visible')
      cy.get('input[type="number"][data-testid="model-count"]').should('be.visible')
    })

    it('should update model count', () => {
      cy.get('input[type="number"][data-testid="model-count"]').clear().type('25')
      cy.get('input[type="number"][data-testid="model-count"]').should('have.value', '25')
    })

    it('should display average latency slider', () => {
      cy.contains('Average Latency').should('be.visible')
      cy.get('input[type="range"][data-testid="latency"]').should('be.visible')
    })

    it('should show latency in milliseconds', () => {
      cy.get('input[type="range"][data-testid="latency"]')
        .invoke('val', 250)
        .trigger('input')
      cy.contains('250ms').should('be.visible')
    })
  })

  describe('Operational Metrics Inputs', () => {
    it('should display engineering hours slider', () => {
      cy.contains('Engineering Hours/Month').should('be.visible')
      cy.get('input[type="range"][data-testid="engineering-hours"]').should('be.visible')
    })

    it('should update engineering hours', () => {
      cy.get('input[type="range"][data-testid="engineering-hours"]')
        .invoke('val', 200)
        .trigger('input')
      cy.contains('200 hours').should('be.visible')
    })

    it('should display team size input', () => {
      cy.contains('Team Size').should('be.visible')
      cy.get('input[type="number"][data-testid="team-size"]').should('be.visible')
    })

    it('should validate team size input', () => {
      cy.get('input[type="number"][data-testid="team-size"]').clear().type('0')
      cy.contains('Minimum 1').should('be.visible')
    })

    it('should display deployment frequency', () => {
      cy.contains('Deployment Frequency').should('be.visible')
      cy.get('select[data-testid="deployment-frequency"]').should('be.visible')
    })

    it('should allow selecting deployment frequency', () => {
      cy.get('select[data-testid="deployment-frequency"]').select('Daily')
      cy.get('select[data-testid="deployment-frequency"]').should('have.value', 'daily')
    })
  })

  describe('AI Workload Details', () => {
    it('should display requests per day slider', () => {
      cy.contains('Requests/Day').should('be.visible')
      cy.get('input[type="range"][data-testid="requests-per-day"]').should('be.visible')
    })

    it('should format large request numbers', () => {
      cy.get('input[type="range"][data-testid="requests-per-day"]')
        .invoke('val', 5000000)
        .trigger('input')
      cy.contains('5M').should('be.visible')
    })

    it('should display model types selection', () => {
      cy.contains('Model Types').should('be.visible')
      cy.get('[data-testid="model-type-checkbox"]').should('have.length.at.least', 3)
    })

    it('should allow selecting multiple model types', () => {
      cy.get('input[value="llm"]').check()
      cy.get('input[value="vision"]').check()
      cy.get('input[value="embedding"]').check()
      cy.get('input:checked').should('have.length', 3)
    })

    it('should display cloud provider selection', () => {
      cy.contains('Cloud Provider').should('be.visible')
      cy.get('select[data-testid="cloud-provider"]').should('be.visible')
    })

    it('should show provider-specific optimizations', () => {
      cy.get('select[data-testid="cloud-provider"]').select('AWS')
      cy.contains('AWS optimization').should('be.visible')
    })
  })

  describe('Calculation Process', () => {
    it('should have calculate button', () => {
      cy.contains('button', 'Calculate ROI').should('be.visible')
    })

    it('should enable calculate button with valid inputs', () => {
      cy.get('input[type="range"][data-testid="monthly-spend"]').invoke('val', 50000).trigger('input')
      cy.contains('button', 'Calculate ROI').should('not.be.disabled')
    })

    it('should trigger calculation on button click', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.contains('Calculating').should('be.visible')
      cy.get('.animate-spin').should('exist')
    })

    it('should show progress during calculation', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.get('[data-testid="calculation-progress"]').should('be.visible')
    })

    it('should complete calculation', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Results').should('be.visible')
    })
  })

  describe('Results Display', () => {
    beforeEach(() => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
    })

    it('should display monthly savings', () => {
      cy.contains('Monthly Savings').should('be.visible')
      cy.contains(/\$[\d,]+/).should('be.visible')
    })

    it('should show percentage reduction', () => {
      cy.contains('Cost Reduction').should('be.visible')
      cy.contains(/\d+%/).should('be.visible')
    })

    it('should display annual savings', () => {
      cy.contains('Annual Savings').should('be.visible')
      cy.contains(/\$[\d,]+K/).should('be.visible')
    })

    it('should show ROI percentage', () => {
      cy.contains('ROI').should('be.visible')
      cy.contains(/\d+%/).should('be.visible')
    })

    it('should display payback period', () => {
      cy.contains('Payback Period').should('be.visible')
      cy.contains(/\d+ months?/).should('be.visible')
    })

    it('should show 3-year projection', () => {
      cy.contains('3-Year TCO Reduction').should('be.visible')
      cy.contains(/\$[\d,]+[KM]/).should('be.visible')
    })
  })

  describe('Breakdown Analysis', () => {
    beforeEach(() => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
    })

    it('should display savings breakdown', () => {
      cy.contains('Savings Breakdown').should('be.visible')
    })

    it('should show infrastructure savings', () => {
      cy.contains('Infrastructure Optimization').should('be.visible')
      cy.contains('infrastructure').parent().contains(/\$[\d,]+/).should('be.visible')
    })

    it('should show operational savings', () => {
      cy.contains('Operational Efficiency').should('be.visible')
      cy.contains('operational').parent().contains(/\$[\d,]+/).should('be.visible')
    })

    it('should show performance improvements', () => {
      cy.contains('Performance Gains').should('be.visible')
      cy.contains('Latency Reduction').should('be.visible')
      cy.contains(/\d+% faster/).should('be.visible')
    })

    it('should display visual chart', () => {
      cy.get('[data-testid="savings-chart"]').should('be.visible')
      cy.get('svg').should('exist')
    })
  })

  describe('Industry Multipliers', () => {
    it('should apply Technology industry multiplier', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Technology Optimization').should('be.visible')
    })

    it('should show different results for Healthcare', () => {
      cy.visit('/demo')
      cy.contains('Healthcare').click()
      cy.contains('ROI Calculator').click()
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Healthcare Compliance').should('be.visible')
    })

    it('should show different results for Financial Services', () => {
      cy.visit('/demo')
      cy.contains('Financial Services').click()
      cy.contains('ROI Calculator').click()
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Financial Regulations').should('be.visible')
    })

    it('should display industry-specific benefits', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Industry Benefits').should('be.visible')
      cy.get('[data-testid="industry-benefit"]').should('have.length.at.least', 3)
    })
  })

  describe('Export and Sharing', () => {
    beforeEach(() => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
    })

    it('should display export options', () => {
      cy.contains('Export Results').should('be.visible')
    })

    it('should allow downloading PDF report', () => {
      cy.contains('Download PDF').click()
      cy.readFile('cypress/downloads/roi-report.pdf').should('exist')
    })

    it('should allow exporting to Excel', () => {
      cy.contains('Export to Excel').click()
      cy.readFile('cypress/downloads/roi-analysis.xlsx').should('exist')
    })

    it('should allow sharing via email', () => {
      cy.contains('Share via Email').click()
      cy.get('[data-testid="email-modal"]').should('be.visible')
      cy.get('input[type="email"]').should('be.visible')
    })

    it('should generate shareable link', () => {
      cy.contains('Get Shareable Link').click()
      cy.get('[data-testid="share-link"]').should('be.visible')
      cy.contains('Copy Link').should('be.visible')
    })

    it('should copy link to clipboard', () => {
      cy.contains('Get Shareable Link').click()
      cy.contains('Copy Link').click()
      cy.contains('Copied!').should('be.visible')
    })
  })

  describe('Comparison Features', () => {
    beforeEach(() => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
    })

    it('should show comparison with competitors', () => {
      cy.contains('Compare with Alternatives').should('be.visible')
    })

    it('should display competitor pricing', () => {
      cy.contains('Compare with Alternatives').click()
      cy.contains('Competitor A').should('be.visible')
      cy.contains('Competitor B').should('be.visible')
    })

    it('should highlight Netra advantages', () => {
      cy.contains('Compare with Alternatives').click()
      cy.contains('Netra Advantage').should('be.visible')
      cy.get('[data-testid="advantage-badge"]').should('have.class', 'bg-green-500')
    })

    it('should show feature comparison matrix', () => {
      cy.contains('Compare with Alternatives').click()
      cy.get('[data-testid="comparison-table"]').should('be.visible')
      cy.contains('Multi-agent').should('be.visible')
      cy.contains('Real-time').should('be.visible')
    })
  })

  describe('Validation and Error Handling', () => {
    it('should validate minimum spend', () => {
      cy.get('input[type="range"][data-testid="monthly-spend"]')
        .invoke('val', 0)
        .trigger('input')
      cy.contains('button', 'Calculate ROI').should('be.disabled')
      cy.contains('Minimum spend required').should('be.visible')
    })

    it('should validate model count', () => {
      cy.get('input[type="number"][data-testid="model-count"]').clear().type('-5')
      cy.contains('Invalid model count').should('be.visible')
    })

    it('should require at least one model type', () => {
      cy.get('input[type="checkbox"]:checked').uncheck()
      cy.contains('button', 'Calculate ROI').click()
      cy.contains('Select at least one model type').should('be.visible')
    })

    it('should handle API errors gracefully', () => {
      cy.intercept('POST', '/api/demo/roi', { statusCode: 500 })
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(2000)
      cy.contains('Using estimated values').should('be.visible')
    })

    it('should show fallback calculations on error', () => {
      cy.intercept('POST', '/api/demo/roi', { statusCode: 500 })
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Monthly Savings').should('be.visible')
      cy.contains(/\$[\d,]+/).should('be.visible')
    })
  })

  describe('Interactive Features', () => {
    it('should allow recalculation with new values', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Adjust Values').click()
      cy.get('input[type="range"][data-testid="monthly-spend"]')
        .invoke('val', 100000)
        .trigger('input')
      cy.contains('button', 'Recalculate').click()
      cy.wait(3000)
      cy.contains('Updated Results').should('be.visible')
    })

    it('should show tooltips on hover', () => {
      cy.get('[data-testid="info-icon"]').first().trigger('mouseenter')
      cy.contains('This represents').should('be.visible')
    })

    it('should expand/collapse sections', () => {
      cy.contains('Advanced Options').click()
      cy.contains('GPU Utilization').should('be.visible')
      cy.contains('Advanced Options').click()
      cy.contains('GPU Utilization').should('not.be.visible')
    })

    it('should save calculation history', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('View History').click()
      cy.get('[data-testid="history-item"]').should('have.length.at.least', 1)
    })
  })

  describe('Visual Indicators', () => {
    beforeEach(() => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
    })

    it('should show green indicators for savings', () => {
      cy.get('[data-testid="savings-indicator"]').should('have.class', 'text-green-500')
    })

    it('should display progress bars', () => {
      cy.get('[data-testid="savings-progress"]').should('be.visible')
      cy.get('[data-testid="savings-progress"]').should('have.css', 'width')
    })

    it('should animate value changes', () => {
      cy.get('[data-testid="animated-value"]').should('have.class', 'animate-pulse')
    })

    it('should show check marks for benefits', () => {
      cy.get('[data-testid="benefit-check"]').should('have.length.at.least', 5)
      cy.get('[data-testid="benefit-check"]').first().should('have.class', 'text-green-500')
    })
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt to mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="roi-calculator"]').should('be.visible')
      cy.contains('Calculate Your AI Optimization Savings').should('be.visible')
    })

    it('should stack inputs vertically on mobile', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="input-section"]').should('have.css', 'flex-direction', 'column')
    })

    it('should show mobile-optimized sliders', () => {
      cy.viewport('iphone-x')
      cy.get('input[type="range"]').first().should('have.css', 'width', '100%')
    })

    it('should handle mobile calculation', () => {
      cy.viewport('iphone-x')
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Monthly Savings').should('be.visible')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      cy.get('[aria-label="Monthly spend slider"]').should('exist')
      cy.get('[aria-label="Calculate ROI"]').should('exist')
    })

    it('should support keyboard navigation', () => {
      cy.get('input[type="range"][data-testid="monthly-spend"]').focus()
      cy.focused().type('{rightarrow}{rightarrow}')
      cy.contains('$52,000').should('be.visible')
    })

    it('should have proper form labels', () => {
      cy.get('label[for="monthly-spend"]').should('contain', 'Monthly')
      cy.get('label[for="model-count"]').should('contain', 'Models')
    })

    it('should announce results to screen readers', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.get('[role="alert"]').should('contain', 'Calculation complete')
    })
  })

  describe('Performance', () => {
    it('should calculate quickly', () => {
      const start = Date.now()
      cy.contains('button', 'Calculate ROI').click()
      cy.contains('Results').should('be.visible')
      const duration = Date.now() - start
      expect(duration).to.be.lessThan(5000)
    })

    it('should handle rapid input changes', () => {
      for(let i = 0; i < 10; i++) {
        cy.get('input[type="range"][data-testid="monthly-spend"]')
          .invoke('val', 30000 + i * 5000)
          .trigger('input')
      }
      cy.get('[data-testid="roi-calculator"]').should('not.have.class', 'error')
    })

    it('should debounce slider inputs', () => {
      cy.get('input[type="range"][data-testid="monthly-spend"]')
        .invoke('val', 60000)
        .trigger('input')
        .trigger('input')
        .trigger('input')
      cy.wait(500)
      cy.get('[data-testid="api-calls"]').should('have.text', '1')
    })
  })
})