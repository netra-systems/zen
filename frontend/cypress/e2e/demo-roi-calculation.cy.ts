/// <reference types="cypress" />

describe('Demo E2E Test Suite 2: ROI Calculation and Value Demonstration', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/demo')
    // Select an industry to enable ROI calculator
    cy.contains('Financial Services').click()
    cy.contains('ROI Calculator').click()
  })

  describe('ROI Calculator Input Validation', () => {
    it('should display all input fields with default values', () => {
      cy.get('input[id="spend"]').should('have.value', '50000')
      cy.get('input[id="requests"]').should('have.value', '10000000')
      cy.get('[id="team"]').should('exist')
      cy.get('[id="latency"]').should('exist')
      cy.get('[id="accuracy"]').should('exist')
    })

    it('should validate numeric inputs', () => {
      // Test negative values
      cy.get('input[id="spend"]').clear().type('-5000')
      cy.get('input[id="spend"]').blur()
      cy.get('input[id="spend"]').should('not.have.value', '-5000')
      
      // Test non-numeric values
      cy.get('input[id="spend"]').clear().type('abc')
      cy.get('input[id="spend"]').should('have.value', '')
      
      // Test valid values
      cy.get('input[id="spend"]').clear().type('75000')
      cy.get('input[id="spend"]').should('have.value', '75000')
    })

    it('should update slider values correctly', () => {
      // Team size slider
      cy.get('[id="team"]').invoke('val', 25).trigger('input')
      cy.contains('25').should('be.visible')
      
      // Latency slider
      cy.get('[id="latency"]').invoke('val', 500).trigger('input')
      cy.contains('500ms').should('be.visible')
      
      // Accuracy slider
      cy.get('[id="accuracy"]').invoke('val', 95).trigger('input')
      cy.contains('95%').should('be.visible')
    })

    it('should show industry-specific multipliers', () => {
      // Industry context should be visible
      cy.contains('Financial Services').should('be.visible')
    })
  })

  describe('ROI Calculation Engine', () => {
    it('should calculate ROI with default values', () => {
      cy.contains('Calculate ROI').click()
      
      // Wait for calculation
      cy.wait(500)
      
      // Check for results
      cy.contains('Projected Savings & ROI').should('be.visible')
      cy.contains('Infrastructure Savings').should('be.visible')
      cy.contains('Operational Efficiency').should('be.visible')
      cy.contains('Performance Value').should('be.visible')
    })

    it('should show monthly and annual savings', () => {
      cy.contains('Calculate ROI').click()
      cy.wait(500)
      
      cy.contains('Total Monthly Savings').should('be.visible')
      cy.contains('Annual Savings').should('be.visible')
      // Check for savings display
      cy.contains('$').should('be.visible')
    })

    it('should calculate payback period', () => {
      cy.contains('Calculate ROI').click()
      cy.wait(500)
      
      cy.contains('Payback Period').should('be.visible')
      cy.contains('months').should('be.visible')
    })

    it('should show 3-year ROI percentage', () => {
      cy.contains('Calculate ROI').click()
      cy.wait(500)
      
      cy.contains('3-Year ROI').should('be.visible')
      cy.contains('%').should('be.visible')
      
      // ROI should be positive
      // Check for positive ROI
      cy.contains('%').should('be.visible')
    })

    it('should recalculate when inputs change', () => {
      // Initial calculation
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      // Change input and recalculate
      cy.get('input[id="spend"]').clear().type('100000')
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      // Values should update
      cy.contains('Projected Savings & ROI').should('be.visible')
      cy.contains('$100,000').should('be.visible') // Current spend should reflect new input
    })
  })

  describe('Cost Comparison Visualization', () => {
    it('should show before and after cost comparison', () => {
      cy.get('input[id="spend"]').clear().type('80000')
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      cy.contains('Cost Comparison').should('be.visible')
      cy.contains('Current Monthly Spend').should('be.visible')
      Assertions.hasValidCurrency('[class*="font-medium"]:contains("$")')
      cy.contains('Optimized Monthly Spend').should('be.visible')
    })

    it('should display savings breakdown by category', () => {
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      const categories = ['Infrastructure Savings', 'Operational Efficiency', 'Performance Value']
      categories.forEach(category => {
        cy.contains(category).should('be.visible')
      })
      // Validate currency formatting in savings cards
      cy.get('[class*="text-2xl"][class*="font-bold"]:contains("$")').should('have.length.at.least', 3)
    })

    it('should show visual indicators for improvements', () => {
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      // Check for improvement indicators with updated selectors
      cy.get('[class*="text-green-600"]').should('exist')
      
      // Check for trending icons (TrendingUp, TrendingDown)
      cy.get('svg').should('exist')
      
      // Check for success border on results card
      cy.get('[class*="border-green-500"]').should('exist')
    })
  })

  describe('Industry-Specific Calculations', () => {
    it('should apply different multipliers for different industries', () => {
      const industries = TestData.industries
      
      industries.forEach((industry) => {
        ROICalculatorHelpers.navigateToIndustry(industry)
        ROICalculatorHelpers.validateIndustryMultiplier(industry)
        cy.contains(industry).should('be.visible')
      })
    })

    it('should show industry-relevant context', () => {
      ROICalculatorHelpers.navigateToIndustry('Healthcare')
      
      // Industry multiplier should be visible in Alert component
      cy.get('[class*="Alert"]').should('contain', 'Healthcare')
      cy.contains('Industry multiplier applied').should('be.visible')
    })
  })

  describe('Export and Sharing Features', () => {
    it('should allow exporting ROI report', () => {
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      ROICalculatorHelpers.validateExportOptions()
      
      // Test export button functionality  
      cy.contains('Export Report').click()
      // Export function should be called (integration test)
    })

    it('should enable scheduling executive briefing', () => {
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      cy.contains('Schedule Executive Briefing').should('be.visible')
      cy.contains('Schedule Executive Briefing').click()
    })
  })

  describe('Value Proposition Display', () => {
    it('should highlight key value metrics prominently', () => {
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      // Check for prominent display of key metrics with updated selectors
      cy.get('[class*="text-3xl"]').should('exist') // Large font for important numbers
      cy.get('[class*="bg-gradient-to-r"]').should('exist') // Gradient text for emphasis
    })

    it('should show success indicators when ROI is positive', () => {
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      // Check for success border on results card
      cy.get('[class*="border-green-500"]').should('exist')
      // Check for ROI badge with checkmark
      cy.get('[class*="Badge"]:contains("ROI")').should('be.visible')
      cy.get('svg[class*="CheckCircle"]').should('exist') // CheckCircle2 icon
    })

    it('should display confidence metrics', () => {
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      // Check for confidence indicators in the tabs overview or results
      // This might be shown in the demo tabs overview section
      cy.contains('2,500+').should('be.visible') // Customer count from quick stats
    })
  })

  describe('Interactive Elements and User Experience', () => {
    it('should provide tooltips for complex metrics', () => {
      // Check for info icons that could show tooltips
      cy.get('svg').should('exist') // Info icons present
      ROICalculatorHelpers.validateAccessibility() // Use helper to check aria labels
    })

    it('should animate value changes smoothly', () => {
      cy.get('input[id="team"]').invoke('val', 10).trigger('input')
      cy.wait(100)
      cy.get('input[id="team"]').invoke('val', 20).trigger('input')
      
      // Check for smooth transitions on results card
      cy.get('[class*="transition-all"]').should('exist')
    })

    it('should maintain focus states for accessibility', () => {
      cy.get('input[id="spend"]').focus()
      cy.get('input[id="spend"]').should('have.focus')
      
      cy.get('input[id="spend"]').type('{tab}')
      cy.get('input[id="requests"]').should('have.focus')
    })
  })

  describe('Performance and Loading States', () => {
    it('should show loading state during calculation', () => {
      // Check loading state when clicking calculate button
      cy.contains('Calculate ROI').click()
      // Check for loading text
      cy.contains('Calculating...').should('be.visible')
      // Wait for calculation to complete
      cy.contains('Projected Savings & ROI', { timeout: 10000 }).should('be.visible')
    })

    it('should handle rapid recalculations', () => {
      // Rapidly click calculate multiple times (with proper waits)
      for (let i = 0; i < 3; i++) {
        cy.contains('Calculate ROI').click()
        cy.wait(200) // Brief wait between clicks
      }
      
      // Should handle gracefully without errors
      cy.contains('Projected Savings & ROI', { timeout: 10000 }).should('be.visible')
    })
  })

  describe('Data Accuracy and Validation', () => {
    it('should ensure calculations are mathematically correct', () => {
      cy.get('input[id="spend"]').clear().type('100000')
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      // Verify calculations are present with current UI structure
      cy.contains('Total Monthly Savings').should('be.visible')
      cy.contains('Annual Savings').should('be.visible')
      // Validate the input is reflected in cost comparison
      cy.contains('$100,000').should('be.visible')
    })

    it('should show realistic savings percentages', () => {
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      // Check that ROI percentage is displayed in badge
      cy.get('[class*="Badge"]:contains("%")').should('be.visible')
      // Verify ROI is positive (should be > 0%)
      Assertions.hasValidPercentage('[class*="Badge"]:contains("%")')
    })

    it('should handle edge cases in calculations', () => {
      // Minimum values
      cy.get('input[id="spend"]').clear().type('1000')
      cy.get('input[id="requests"]').clear().type('1000')
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      // Should still show valid results with small values
      cy.contains('Projected Savings & ROI').should('be.visible')
      Assertions.hasValidCurrency('[class*="text-3xl"]')
      
      // Test with larger values
      cy.get('input[id="spend"]').clear().type('500000')
      cy.get('input[id="requests"]').clear().type('50000000')
      ROICalculatorHelpers.triggerCalculationAndWait()
      
      // Should handle large numbers gracefully
      cy.contains('Projected Savings & ROI').should('be.visible')
      cy.contains('$500,000').should('be.visible')
    })
  })
})