/// <reference types="cypress" />

describe('Enterprise Demo Page E2E Tests', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/enterprise-demo')
  })

  describe('Page Load and Authentication', () => {
    it('should load the enterprise demo page', () => {
      cy.url().should('include', '/enterprise-demo')
      cy.contains('Enterprise AI Optimization Platform').should('be.visible')
    })

    it('should display executive-level messaging', () => {
      cy.contains('Transform Your AI Infrastructure').should('be.visible')
      cy.contains('Enterprise-Grade').should('be.visible')
      cy.contains('ROI').should('be.visible')
    })

    it('should show authentication gate for protected features', () => {
      cy.contains('Schedule Executive Briefing').click()
      cy.contains('Authentication Required').should('be.visible')
    })

    it('should display enterprise security badges', () => {
      cy.contains('SOC 2').should('be.visible')
      cy.contains('ISO 27001').should('be.visible')
      cy.contains('HIPAA').should('be.visible')
    })
  })

  describe('Live Performance Metrics Dashboard', () => {
    it('should display real-time metrics', () => {
      cy.contains('Live Performance').should('be.visible')
      cy.get('[data-testid="metric-card"]').should('have.length.at.least', 4)
    })

    it('should show cost savings metrics', () => {
      cy.contains('Cost Reduction').should('be.visible')
      cy.contains('$').should('be.visible')
      cy.contains('%').should('be.visible')
    })

    it('should display latency improvements', () => {
      cy.contains('Latency').should('be.visible')
      cy.contains('ms').should('be.visible')
      cy.contains('reduction').should('be.visible')
    })

    it('should show throughput metrics', () => {
      cy.contains('Throughput').should('be.visible')
      cy.contains('requests/sec').should('be.visible')
    })

    it('should auto-refresh metrics', () => {
      cy.get('[data-testid="metric-value"]').then($initial => {
        const initialValue = $initial.text()
        cy.wait(5000)
        cy.get('[data-testid="metric-value"]').should($updated => {
          expect($updated.text()).to.not.equal(initialValue)
        })
      })
    })

    it('should display metric trends with charts', () => {
      cy.get('[data-testid="trend-chart"]').should('be.visible')
      cy.get('svg').should('exist')
    })
  })

  describe('Customer Success Stories', () => {
    it('should display testimonial carousel', () => {
      cy.contains('Customer Success').should('be.visible')
      cy.get('[data-testid="testimonial-card"]').should('have.length.at.least', 3)
    })

    it('should show Fortune 500 logos', () => {
      cy.get('[data-testid="customer-logo"]').should('have.length.at.least', 5)
    })

    it('should display case study metrics', () => {
      cy.contains('75% Cost Reduction').should('be.visible')
      cy.contains('10x Performance').should('be.visible')
      cy.contains('2 Week Implementation').should('be.visible')
    })

    it('should navigate testimonial carousel', () => {
      cy.get('[aria-label="Next testimonial"]').click()
      cy.wait(500)
      cy.get('[aria-label="Previous testimonial"]').click()
    })

    it('should link to detailed case studies', () => {
      cy.contains('Read Case Study').should('have.attr', 'href')
    })
  })

  describe('Feature Showcase', () => {
    it('should display enterprise features grid', () => {
      cy.contains('Enterprise Features').should('be.visible')
      cy.get('[data-testid="feature-tile"]').should('have.length.at.least', 6)
    })

    it('should highlight multi-agent orchestration', () => {
      cy.contains('Multi-Agent Orchestration').should('be.visible')
      cy.contains('Coordinate multiple AI agents').should('be.visible')
    })

    it('should showcase security features', () => {
      cy.contains('Enterprise Security').should('be.visible')
      cy.contains('End-to-end encryption').should('be.visible')
      cy.contains('Role-based access').should('be.visible')
    })

    it('should display integration capabilities', () => {
      cy.contains('Seamless Integration').should('be.visible')
      cy.contains('API').should('be.visible')
      cy.contains('SDK').should('be.visible')
    })

    it('should show feature details on hover', () => {
      cy.contains('Multi-Agent Orchestration').trigger('mouseenter')
      cy.contains('Learn More').should('be.visible')
    })

    it('should open feature modal on click', () => {
      cy.contains('Enterprise Security').click()
      cy.get('[data-testid="feature-modal"]').should('be.visible')
      cy.contains('Advanced Security Features').should('be.visible')
    })
  })

  describe('Executive Dashboard Preview', () => {
    it('should display dashboard preview section', () => {
      cy.contains('Executive Dashboard').should('be.visible')
      cy.get('[data-testid="dashboard-preview"]').should('be.visible')
    })

    it('should show KPI widgets', () => {
      cy.contains('Key Performance Indicators').should('be.visible')
      cy.get('[data-testid="kpi-widget"]').should('have.length.at.least', 4)
    })

    it('should display cost analysis chart', () => {
      cy.contains('Cost Analysis').should('be.visible')
      cy.get('[data-testid="cost-chart"]').should('be.visible')
    })

    it('should show ROI projections', () => {
      cy.contains('ROI Projection').should('be.visible')
      cy.contains('3-Year').should('be.visible')
      cy.contains('5-Year').should('be.visible')
    })

    it('should have interactive dashboard elements', () => {
      cy.get('[data-testid="date-range-selector"]').should('be.visible')
      cy.get('[data-testid="metric-filter"]').should('be.visible')
    })
  })

  describe('Implementation Timeline', () => {
    it('should display implementation phases', () => {
      cy.contains('Implementation Timeline').should('be.visible')
      cy.get('[data-testid="timeline-phase"]').should('have.length', 4)
    })

    it('should show phase details', () => {
      const phases = ['Discovery', 'Pilot', 'Rollout', 'Optimization']
      phases.forEach(phase => {
        cy.contains(phase).should('be.visible')
      })
    })

    it('should display timeline duration', () => {
      cy.contains('Week 1-2').should('be.visible')
      cy.contains('Week 3-4').should('be.visible')
      cy.contains('Week 5-8').should('be.visible')
    })

    it('should highlight current phase', () => {
      cy.get('[data-testid="current-phase"]').should('have.class', 'ring-2')
    })

    it('should show phase deliverables on click', () => {
      cy.contains('Discovery').click()
      cy.contains('Requirements Analysis').should('be.visible')
      cy.contains('Architecture Review').should('be.visible')
    })
  })

  describe('Pricing and Packages', () => {
    it('should display enterprise pricing tiers', () => {
      cy.contains('Enterprise Pricing').should('be.visible')
      cy.get('[data-testid="pricing-tier"]').should('have.length', 3)
    })

    it('should show tier features', () => {
      cy.contains('Professional').should('be.visible')
      cy.contains('Enterprise').should('be.visible')
      cy.contains('Enterprise Plus').should('be.visible')
    })

    it('should display custom pricing option', () => {
      cy.contains('Custom Pricing').should('be.visible')
      cy.contains('Contact Sales').should('be.visible')
    })

    it('should highlight recommended tier', () => {
      cy.get('[data-testid="recommended-tier"]').should('have.class', 'scale-105')
    })

    it('should open pricing calculator', () => {
      cy.contains('Calculate Pricing').click()
      cy.get('[data-testid="pricing-calculator"]').should('be.visible')
    })
  })

  describe('Call-to-Action Sections', () => {
    it('should display primary CTA buttons', () => {
      cy.contains('button', 'Schedule Demo').should('be.visible')
      cy.contains('button', 'Request Trial').should('be.visible')
      cy.contains('button', 'Contact Sales').should('be.visible')
    })

    it('should show demo scheduling form', () => {
      cy.contains('Schedule Demo').click()
      cy.get('[data-testid="demo-form"]').should('be.visible')
      cy.get('input[name="company"]').should('be.visible')
      cy.get('input[name="email"]').should('be.visible')
    })

    it('should validate form inputs', () => {
      cy.contains('Schedule Demo').click()
      cy.get('button[type="submit"]').click()
      cy.contains('Required').should('be.visible')
    })

    it('should submit demo request', () => {
      cy.contains('Schedule Demo').click()
      cy.get('input[name="company"]').type('Test Corp')
      cy.get('input[name="email"]').type('test@example.com')
      cy.get('input[name="name"]').type('John Doe')
      cy.get('button[type="submit"]').click()
      cy.contains('Thank you').should('be.visible')
    })

    it('should open contact sales modal', () => {
      cy.contains('Contact Sales').click()
      cy.get('[data-testid="sales-modal"]').should('be.visible')
      cy.contains('Enterprise Sales Team').should('be.visible')
    })
  })

  describe('Technical Specifications', () => {
    it('should display technical specs section', () => {
      cy.contains('Technical Specifications').should('be.visible')
      cy.get('[data-testid="spec-category"]').should('have.length.at.least', 4)
    })

    it('should show infrastructure requirements', () => {
      cy.contains('Infrastructure').should('be.visible')
      cy.contains('Cloud').should('be.visible')
      cy.contains('On-premises').should('be.visible')
      cy.contains('Hybrid').should('be.visible')
    })

    it('should display supported platforms', () => {
      cy.contains('Supported Platforms').should('be.visible')
      cy.contains('AWS').should('be.visible')
      cy.contains('Azure').should('be.visible')
      cy.contains('GCP').should('be.visible')
    })

    it('should show API documentation link', () => {
      cy.contains('API Documentation').should('have.attr', 'href', '/docs/api')
    })
  })

  describe('Compliance and Certifications', () => {
    it('should display compliance badges', () => {
      cy.contains('Compliance').should('be.visible')
      cy.get('[data-testid="compliance-badge"]').should('have.length.at.least', 6)
    })

    it('should show certification details on click', () => {
      cy.contains('SOC 2').click()
      cy.get('[data-testid="cert-modal"]').should('be.visible')
      cy.contains('Type II').should('be.visible')
    })

    it('should link to compliance documentation', () => {
      cy.contains('Compliance Documentation').should('have.attr', 'href')
    })

    it('should display data residency options', () => {
      cy.contains('Data Residency').should('be.visible')
      cy.contains('US').should('be.visible')
      cy.contains('EU').should('be.visible')
      cy.contains('APAC').should('be.visible')
    })
  })

  describe('Resource Center', () => {
    it('should display resource links', () => {
      cy.contains('Resources').should('be.visible')
      cy.contains('Whitepapers').should('be.visible')
      cy.contains('Webinars').should('be.visible')
      cy.contains('Documentation').should('be.visible')
    })

    it('should show downloadable resources', () => {
      cy.contains('Download Whitepaper').should('be.visible')
      cy.contains('ROI Guide').should('be.visible')
      cy.contains('Implementation Guide').should('be.visible')
    })

    it('should require form for downloads', () => {
      cy.contains('Download Whitepaper').click()
      cy.get('[data-testid="download-form"]').should('be.visible')
    })

    it('should link to video demos', () => {
      cy.contains('Watch Demo').should('have.attr', 'href')
    })
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt to mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.contains('Enterprise AI Optimization').should('be.visible')
      cy.get('[data-testid="mobile-menu"]').should('be.visible')
    })

    it('should stack features on mobile', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="feature-tile"]').should('have.css', 'width', '100%')
    })

    it('should show mobile-optimized CTAs', () => {
      cy.viewport('iphone-x')
      cy.contains('Schedule Demo').should('be.visible')
      cy.get('button').should('have.css', 'width', '100%')
    })

    it('should handle mobile navigation', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="mobile-menu"]').click()
      cy.contains('Features').should('be.visible')
      cy.contains('Pricing').should('be.visible')
    })
  })

  describe('Performance and Analytics', () => {
    it('should track page view analytics', () => {
      cy.window().then(win => {
        expect(win.dataLayer).to.exist
      })
    })

    it('should track CTA clicks', () => {
      cy.window().then(win => {
        const initialLength = win.dataLayer?.length || 0
        cy.contains('Schedule Demo').click()
        expect(win.dataLayer?.length).to.be.greaterThan(initialLength)
      })
    })

    it('should load within performance budget', () => {
      cy.visit('/enterprise-demo', {
        onBeforeLoad: (win) => {
          win.performance.mark('start')
        },
        onLoad: (win) => {
          win.performance.mark('end')
          win.performance.measure('load', 'start', 'end')
          const measure = win.performance.getEntriesByType('measure')[0]
          expect(measure.duration).to.be.lessThan(4000)
        }
      })
    })

    it('should lazy load heavy components', () => {
      cy.get('[data-testid="dashboard-preview"]').scrollIntoView()
      cy.get('[data-testid="dashboard-chart"]').should('be.visible')
    })
  })

  describe('Accessibility', () => {
    it('should have proper heading hierarchy', () => {
      cy.get('h1').should('have.length', 1)
      cy.get('h2').should('have.length.at.least', 5)
    })

    it('should have ARIA labels for interactive elements', () => {
      cy.get('button[aria-label]').should('have.length.at.least', 5)
    })

    it('should support keyboard navigation', () => {
      cy.get('body').tab()
      cy.focused().should('have.attr', 'href').or('have.attr', 'type', 'button')
    })

    it('should have sufficient color contrast', () => {
      cy.get('.text-white').should('have.css', 'background-color')
        .and('not.equal', 'rgb(255, 255, 255)')
    })
  })
})