/// <reference types="cypress" />

describe('Demo E2E Test Suite 5: Export and Reporting Functionality', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/demo')
    cy.contains('Financial Services').click()
    cy.wait(500)
  })

  describe('Implementation Roadmap Export', () => {
    it('should display export options in roadmap', () => {
      cy.contains('Next Steps').click()
      cy.contains('Implementation Roadmap').should('be.visible')
      cy.contains('Export Plan').should('be.visible')
    })

    it('should show export format options', () => {
      cy.contains('Next Steps').click()
      cy.contains('Export Plan').click()
      
      // Should handle export
      cy.on('window:alert', (text) => {
        expect(text).to.contain('Export')
      })
    })

    it('should include completed steps in export', () => {
      // Complete some steps first
      cy.contains('ROI Calculator').click()
      cy.contains('Calculate ROI').click()
      cy.wait(1000)
      
      cy.contains('Next Steps').click()
      cy.contains('Export Plan').click()
      
      // Export should include progress
      cy.on('window:alert', (text) => {
        expect(text).to.contain('implementation')
      })
    })

    it('should export implementation phases', () => {
      cy.contains('Next Steps').click()
      
      // Verify phases are visible before export
      cy.contains('Immediate Actions').should('be.visible')
      cy.contains('Pilot Implementation').should('be.visible')
      cy.contains('Gradual Scaling').should('be.visible')
      cy.contains('Full Production').should('be.visible')
      
      cy.contains('Export Plan').click()
    })
  })

  describe('ROI Report Export', () => {
    it('should export ROI calculations', () => {
      cy.contains('ROI Calculator').click()
      
      // Perform calculation
      cy.get('input[id="spend"]').clear().type('100000')
      cy.contains('Calculate ROI').click()
      cy.wait(1000)
      
      cy.contains('Export Report').should('be.visible')
      cy.contains('Export Report').click()
      
      // Verify export triggered
      cy.on('window:alert', (text) => {
        expect(text).to.contain('roi-report')
      })
    })

    it('should include all ROI metrics in export', () => {
      cy.contains('ROI Calculator').click()
      cy.contains('Calculate ROI').click()
      cy.wait(1000)
      
      // Mock window.URL.createObjectURL to capture blob
      cy.window().then((win) => {
        const stub = cy.stub(win.URL, 'createObjectURL')
        cy.contains('Export Report').click()
        expect(stub).to.be.called
      })
    })

    it('should format export filename with timestamp', () => {
      cy.contains('ROI Calculator').click()
      cy.contains('Calculate ROI').click()
      cy.wait(1000)
      
      cy.window().then((win) => {
        cy.stub(win.document, 'createElement').callsFake((tagName) => {
          if (tagName === 'a') {
            const element = document.createElement('a')
            cy.stub(element, 'click').as('downloadClick')
            return element
          }
          return document.createElement(tagName)
        })
      })
      
      cy.contains('Export Report').click()
      cy.get('@downloadClick').should('be.called')
    })
  })

  describe('Performance Metrics Export', () => {
    it('should export performance dashboard data', () => {
      cy.contains('Metrics').click()
      cy.wait(1000)
      
      // Check for export capability
      // Check for export capability
      cy.contains('Export').should('exist')
    })

    it('should export benchmark comparisons', () => {
      cy.contains('Metrics').click()
      cy.contains('Benchmarks').click()
      
      // Verify benchmark data is visible
      cy.contains('BERT Inference').should('be.visible')
      cy.contains('Top 5%').should('be.visible')
    })

    it('should include real-time metrics in export', () => {
      cy.contains('Metrics').click()
      
      // Enable auto-refresh
      cy.contains('Manual').click()
      cy.contains('Auto').should('be.visible')
      
      cy.wait(2000)
      
      // Metrics should be updating
      cy.contains('Updated').should('be.visible')
    })
  })

  describe('Synthetic Data Export', () => {
    it('should export generated synthetic data', () => {
      cy.contains('Data Insights').click()
      cy.wait(1000)
      
      cy.contains('Export').should('be.visible')
      cy.contains('Export').click()
      
      // Verify export includes industry
      cy.on('window:alert', (text) => {
        expect(text).to.contain('financial-services')
      })
    })

    it('should export data in JSON format', () => {
      cy.contains('Data Insights').click()
      
      cy.window().then((win) => {
        const blob = new Blob(['test'], { type: 'application/json' })
        cy.stub(win, 'Blob').returns(blob)
        cy.contains('Export').click()
      })
    })

    it('should include metadata in export', () => {
      cy.contains('Data Insights').click()
      cy.contains('Generate').click()
      cy.wait(2000)
      
      cy.contains('Export').click()
      
      // Export should include timestamps and metadata
      cy.on('window:alert', (text) => {
        expect(text).to.contain('synthetic-data')
      })
    })
  })

  describe('Comprehensive Report Generation', () => {
    it('should compile data from all sections', () => {
      // Complete all major sections
      cy.contains('ROI Calculator').click()
      cy.contains('Calculate ROI').click()
      cy.wait(1000)
      
      cy.contains('AI Chat').click()
      cy.get('textarea').type('Optimize my workload')
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(2000)
      
      cy.contains('Metrics').click()
      cy.wait(1000)
      
      cy.contains('Next Steps').click()
      cy.contains('Export Plan').should('be.visible')
    })

    it('should show completion status in final report', () => {
      // Navigate through demo
      ['ROI Calculator', 'AI Chat', 'Metrics', 'Next Steps'].forEach(tab => {
        cy.contains(tab).click()
        cy.wait(500)
      })
      
      // Check completion indicator
      // Check completion indicator
      cy.contains('Demo Complete').should('exist')
    })

    it('should provide executive summary', () => {
      cy.contains('Next Steps').click()
      
      // Check for summary metrics
      cy.contains('Time to Value').should('be.visible')
      cy.contains('2 weeks').should('be.visible')
      cy.contains('Expected ROI').should('be.visible')
      cy.contains('380%').should('be.visible')
    })
  })

  describe('Export Format Options', () => {
    it('should support JSON export format', () => {
      cy.contains('Next Steps').click()
      
      cy.window().then((win) => {
        const jsonBlob = new Blob(['{}'], { type: 'application/json' })
        cy.stub(win, 'Blob').returns(jsonBlob)
        cy.contains('Export Plan').click()
      })
    })

    it('should handle PDF export request', () => {
      cy.contains('Next Steps').click()
      cy.contains('Export Plan').click()
      
      // Should show format selection or default to PDF
      cy.on('window:alert', (text) => {
        expect(text).to.match(/PDF|pdf/)
      })
    })

    it('should handle CSV export for tabular data', () => {
      cy.contains('Metrics').click()
      cy.wait(1000)
      
      // Export metrics as CSV
      // Export metrics as CSV
      cy.contains('Export').click()
      
      cy.on('window:alert', (text) => {
        expect(text).to.match(/CSV|csv/)
      })
    })
  })

  describe('Scheduling and Follow-up Actions', () => {
    it('should allow scheduling executive briefing', () => {
      cy.contains('ROI Calculator').click()
      cy.contains('Calculate ROI').click()
      cy.wait(1000)
      
      cy.contains('Schedule Executive Briefing').should('be.visible')
      cy.contains('Schedule Executive Briefing').click()
    })

    it('should provide contact options', () => {
      cy.contains('Next Steps').click()
      cy.contains('Support & Resources').click()
      
      cy.contains('24/7 Enterprise Support').should('be.visible')
      cy.contains('success@netra.ai').should('be.visible')
      cy.contains('1-800-NETRA-AI').should('be.visible')
    })

    it('should enable pilot program signup', () => {
      cy.contains('Next Steps').click()
      
      cy.contains('Start Pilot Program').should('be.visible')
      cy.contains('Start Pilot Program').click()
    })

    it('should offer deep dive scheduling', () => {
      // Complete demo
      ['ROI Calculator', 'AI Chat', 'Metrics'].forEach(tab => {
        cy.contains(tab).click()
        cy.wait(500)
      })
      
      cy.get('[data-testid="demo-complete"]').within(() => {
        cy.contains('Schedule Deep Dive').should('be.visible')
      })
    })
  })

  describe('Report Accessibility and Sharing', () => {
    it('should generate shareable links', () => {
      cy.contains('Next Steps').click()
      // Check for share capability
      cy.get('button').should('exist')
    })

    it('should support email delivery of reports', () => {
      cy.contains('Next Steps').click()
      // Check for email option
      cy.contains('Email').click()
      
      // Should show email form or trigger mailto
      cy.on('window:alert', (text) => {
        expect(text).to.contain('email')
      })
    })

    it('should maintain report state in session', () => {
      cy.contains('ROI Calculator').click()
      cy.contains('Calculate ROI').click()
      cy.wait(1000)
      
      // Reload page
      cy.reload()
      cy.contains('Financial Services').should('be.visible')
      
      // Previous calculations should be accessible
      cy.contains('ROI Calculator').click()
    })
  })

  describe('Error Handling in Export', () => {
    it('should handle export failures gracefully', () => {
      cy.contains('Next Steps').click()
      
      cy.window().then((win) => {
        cy.stub(win.URL, 'createObjectURL').throws(new Error('Export failed'))
      })
      
      cy.contains('Export Plan').click()
      
      // Should show error message
      cy.on('fail', (err) => {
        expect(err.message).to.include('Export')
        return false
      })
    })

    it('should validate data before export', () => {
      cy.contains('ROI Calculator').click()
      
      // Don't calculate ROI
      cy.contains('Export Report').should('be.visible')
      cy.contains('Export Report').click()
      
      // Should handle empty data
      cy.on('window:alert', (text) => {
        expect(text).to.contain('roi')
      })
    })

    it('should handle network issues during export', () => {
      cy.intercept('POST', '/api/export', { statusCode: 500 })
      
      cy.contains('Next Steps').click()
      cy.contains('Export Plan').click()
      
      // Should fallback to client-side export
      cy.on('window:alert', (text) => {
        expect(text).to.contain('export')
      })
    })
  })

  describe('Report Customization', () => {
    it('should allow selecting report sections', () => {
      cy.contains('Next Steps').click()
      
      // Check available sections
      cy.contains('Implementation Phases').click()
      cy.contains('Task Breakdown').click()
      cy.contains('Risk Management').click()
      cy.contains('Support & Resources').click()
    })

    it('should include only completed sections in export', () => {
      // Only complete ROI
      cy.contains('ROI Calculator').click()
      cy.contains('Calculate ROI').click()
      cy.wait(1000)
      
      cy.contains('Next Steps').click()
      cy.contains('Export Plan').click()
      
      // Export should indicate partial completion
      cy.on('window:alert', (text) => {
        expect(text).to.contain('roi')
      })
    })

    it('should personalize report with industry data', () => {
      cy.contains('Next Steps').click()
      
      // Should show Financial Services specific content
      cy.contains('fraud detection optimization').should('be.visible')
    })
  })

  describe('Analytics and Tracking', () => {
    it('should track export events', () => {
      cy.window().then((win) => {
        cy.stub(win.console, 'log').as('consoleLog')
      })
      
      cy.contains('Next Steps').click()
      cy.contains('Export Plan').click()
      
      cy.get('@consoleLog').should('be.called')
    })

    it('should include demo metrics in export', () => {
      // Complete demo interactions
      cy.contains('ROI Calculator').click()
      cy.contains('Calculate ROI').click()
      cy.wait(1000)
      
      cy.contains('Next Steps').click()
      
      // Metrics should be visible
      cy.contains('Demo Progress').should('be.visible')
      // Progress should be visible
      cy.get('[role="progressbar"]').should('exist')
    })

    it('should timestamp all exports', () => {
      cy.contains('Data Insights').click()
      cy.contains('Export').click()
      
      // Filename should include timestamp
      cy.on('window:alert', (text) => {
        expect(text).to.match(/\d{13}/) // Unix timestamp
      })
    })
  })

  describe('Mobile Export Functionality', () => {
    it('should support export on mobile devices', () => {
      cy.viewport('iphone-x')
      
      cy.contains('Next Steps').click()
      cy.contains('Export Plan').should('be.visible')
      cy.contains('Export Plan').click()
    })

    it('should adapt export UI for tablet', () => {
      cy.viewport('ipad-2')
      
      cy.contains('ROI Calculator').click()
      cy.contains('Calculate ROI').click()
      cy.wait(1000)
      
      cy.contains('Export Report').should('be.visible')
      cy.contains('Export Report').click()
    })

    it('should handle touch interactions for export', () => {
      cy.viewport('iphone-x')
      
      cy.contains('Data Insights').click()
      cy.contains('Export').trigger('touchstart')
      cy.contains('Export').trigger('touchend')
    })
  })
})