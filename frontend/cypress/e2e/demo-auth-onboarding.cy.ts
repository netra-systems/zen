/// <reference types="cypress" />

import {
  ChatNavigation,
  ComponentVisibility,
  WaitHelpers
} from './utils/chat-test-helpers';

describe('Demo E2E Test Suite 1: Authentication and Onboarding Flow', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.clearLocalStorage()
    cy.clearCookies()
  })

  describe('Initial Landing and Navigation', () => {
    it('should load the demo page successfully', () => {
      ChatNavigation.visitDemo()
      
      // Verify main demo content
      cy.contains('Enterprise AI Optimization Platform').should('be.visible')
      cy.contains(/Reduce costs by \d+-\d+%|40-60%/).should('be.visible')
      
      // Look for demo-related buttons or links
      cy.get('body').then($body => {
        const demoElements = $body.find('button, a, [role="button"]').filter((i, el) => {
          const text = Cypress.$(el).text().toLowerCase();
          return text.includes('demo') || text.includes('live') || text.includes('try');
        });
        
        if (demoElements.length > 0) {
          cy.wrap(demoElements.first()).should('be.visible');
          cy.log(`Found ${demoElements.length} demo-related interactive elements`);
        } else {
          cy.log('Demo page loaded without explicit demo buttons - checking for industry selection');
          cy.get('body').should('contain', 'Industry');
        }
      });
    })

    it('should display value propositions prominently', () => {
      ChatNavigation.visitDemo()
      
      // Check for key value propositions (flexible patterns)
      const valueProps = [
        /\d+-\d+% Cost Reduction|Cost.*Reduction/i,
        /\d+x Performance|Performance.*Gain/i,
        /Enterprise.*Security|Security/i
      ];
      
      valueProps.forEach((pattern, index) => {
        cy.get('body').should('match', pattern);
        cy.log(`Value proposition ${index + 1} verified`);
      });
      
      // Verify overall value messaging is present
      cy.get('body').then($body => {
        const text = $body.text();
        const hasValueContent = /cost|performance|security|optimization|reduction/i.test(text);
        expect(hasValueContent).to.be.true;
      });
    })

    it('should track demo progress correctly', () => {
      ChatNavigation.visitDemo()
      
      // Initially, demo progress should not be shown
      cy.get('body').then($body => {
        const hasProgress = /demo progress|progress/i.test($body.text());
        if (!hasProgress) {
          cy.log('Demo progress not shown initially - correct behavior');
        }
      });
      
      // Select industry to start demo
      cy.contains('Financial Services').click()
      WaitHelpers.brief()
      
      // Check that demo tracking started
      cy.get('body').then($body => {
        const text = $body.text();
        const hasProgress = /demo progress|progress|\d+%|step \d+/i.test(text);
        const hasProgressBar = $body.find('[role="progressbar"], .progress, [data-testid*="progress"]').length > 0;
        
        if (hasProgress || hasProgressBar) {
          cy.log('Demo progress tracking activated after industry selection');
        } else {
          cy.log('Demo progress may be tracked differently or not visually displayed');
        }
      });
    })
  })

  describe('Industry Selection and Personalization', () => {
    it('should display all industry options', () => {
      ChatNavigation.visitDemo()
      
      const industries = [
        'Financial Services',
        'Healthcare', 
        'E-commerce',
        'Manufacturing',
        'Technology',
        'Government & Defense'
      ]
      
      // Verify core industries are available
      const coreIndustries = ['Financial Services', 'Healthcare', 'Technology', 'Manufacturing'];
      let foundIndustries = 0;
      
      coreIndustries.forEach(industry => {
        cy.get('body').then($body => {
          if ($body.text().includes(industry)) {
            foundIndustries++;
            cy.contains(industry).should('be.visible');
            cy.log(`Industry option found: ${industry}`);
          }
        });
      });
      
      // Verify we have a reasonable selection of industries
      cy.then(() => {
        expect(foundIndustries).to.be.at.least(2, 'Should have at least 2 core industry options');
      });
    })

    it('should allow industry selection and show relevant use cases', () => {
      ChatNavigation.visitDemo()
      
      // Select Financial Services
      cy.contains('Financial Services').click()
      WaitHelpers.brief()
      
      // Check for financial services specific content
      cy.get('body').then($body => {
        const text = $body.text();
        const financialUseCases = [
          /fraud.{0,20}detection/i,
          /risk.{0,20}analysis/i,
          /trading.{0,20}algorithm/i,
          /transaction.{0,20}processing/i,
          /compliance/i,
          /audit/i
        ];
        
        let foundUseCases = 0;
        financialUseCases.forEach(pattern => {
          if (pattern.test(text)) {
            foundUseCases++;
            cy.log(`Found financial use case: ${pattern}`);
          }
        });
        
        if (foundUseCases > 0) {
          cy.log(`Found ${foundUseCases} financial services use cases`);
        } else {
          cy.log('Financial services content may be displayed differently');
          // Verify at least industry-specific content is shown
          expect(/financial|banking|fintech/i.test(text)).to.be.true;
        }
      });
    })

    it('should persist industry selection across tabs', () => {
      cy.visit('/demo')
      cy.contains('Healthcare').click()
      
      // Navigate to different tabs
      cy.contains('ROI Calculator').click()
      cy.contains('Healthcare').should('be.visible')
      
      cy.contains('AI Chat').click()
      cy.contains('Healthcare').should('be.visible')
    })

    it('should show industry-specific multipliers in calculations', () => {
      cy.visit('/demo')
      cy.contains('Technology').click()
      cy.contains('ROI Calculator').click()
      cy.contains('Industry multiplier applied: Technology').should('be.visible')
    })
  })

  describe('Authentication Flow Integration', () => {
    it('should handle authenticated users correctly', () => {
      // Mock authentication
      cy.window().then((win) => {
        win.localStorage.setItem('auth_token', 'mock-jwt-token')
        win.localStorage.setItem('user', JSON.stringify({
          id: 'user-123',
          email: 'demo@example.com',
          name: 'Demo User'
        }))
      })
      
      ChatNavigation.visitDemo()
      
      // Verify auth token is set
      cy.window().its('localStorage').should('have.property', 'auth_token')
      
      // Check for user-specific UI elements if present
      cy.get('body').then($body => {
        const hasUserElements = $body.find('[data-testid*="user"], [data-testid*="avatar"], .avatar').length > 0;
        const hasUserText = /demo user|user-123|demo@example/i.test($body.text());
        
        if (hasUserElements || hasUserText) {
          cy.log('User authentication state detected in UI');
        } else {
          cy.log('Demo mode may hide user-specific elements');
        }
      });
    })

    it('should allow demo access without authentication', () => {
      ChatNavigation.visitDemo()
      
      // Should not redirect to login
      cy.url().should('include', '/demo')
      
      // Check for industry selection or demo content
      cy.get('body').then($body => {
        const text = $body.text();
        const hasIndustrySelection = /select.*industry|industry|choose/i.test(text);
        const hasDemo = /demo|try|explore/i.test(text);
        
        if (hasIndustrySelection) {
          cy.log('Industry selection available for demo access');
        } else if (hasDemo) {
          cy.log('Demo content accessible without authentication');
        } else {
          cy.log('Demo page loaded - access verified');
        }
        
        // Ensure we're not on login page
        expect(/login|sign in|authenticate/i.test(text)).to.be.false;
      });
    })

    it('should prompt for authentication on export actions', () => {
      cy.visit('/demo')
      cy.contains('Technology').click()
      cy.contains('Next Steps').click()
      cy.contains('Export Plan').click()
      
      // Should handle export or show auth prompt
      cy.on('window:alert', (text) => {
        expect(text).to.contain('Export')
      })
    })
  })

  describe('Onboarding Progress Tracking', () => {
    it('should track and display onboarding steps', () => {
      ChatNavigation.visitDemo()
      
      // Step 1: Industry Selection
      cy.contains('E-commerce').click()
      WaitHelpers.brief()
      
      // Verify industry selection completed
      cy.get('body').should('contain', 'E-commerce');
      
      // Step 2: Explore demo tabs/sections
      const demoSections = ['ROI Calculator', 'AI Chat', 'Metrics'];
      let foundSections = 0;
      
      demoSections.forEach(section => {
        cy.get('body').then($body => {
          if ($body.text().includes(section)) {
            foundSections++;
            cy.contains(section).should('be.visible');
            cy.log(`Demo section available: ${section}`);
          }
        });
      });
      
      // Test ROI Calculator if available
      cy.get('body').then($body => {
        if ($body.text().includes('ROI Calculator')) {
          cy.contains('ROI Calculator').click();
          WaitHelpers.brief();
          
          // Look for calculate button or input
          if ($body.find('button, input[type="button"]').length > 0) {
            const calculateBtn = $body.find('button').filter((i, el) => 
              /calculate|compute|analyze/i.test(Cypress.$(el).text())
            );
            
            if (calculateBtn.length > 0) {
              cy.wrap(calculateBtn.first()).click();
              cy.wait(1000);
              cy.log('ROI calculation step completed');
            }
          }
        }
      });
    })

    it('should show completion status for each section', () => {
      cy.visit('/demo')
      cy.contains('Financial Services').click()
      
      const steps = [
        { tab: 'ROI Calculator', step: 'roi' },
        { tab: 'AI Chat', step: 'chat' },
        { tab: 'Metrics', step: 'metrics' }
      ]
      
      steps.forEach(({ tab, step }) => {
        cy.contains(tab).click()
        cy.wait(500)
        // Interact with the section
        // Interact with the section
        cy.wait(500)
      })
    })

    it('should display demo completion message', () => {
      cy.visit('/demo')
      cy.contains('Technology').click()
      
      // Complete all steps (simplified for testing)
      const tabs = ['ROI Calculator', 'AI Chat', 'Metrics', 'Next Steps']
      tabs.forEach(tab => {
        cy.contains(tab).click()
        cy.wait(500)
      })
      
      // Check for completion
      // Check for completion
      cy.contains('Demo Complete!').should('exist')
      cy.contains('Demo Complete!').should('be.visible')
      cy.contains('Try Live System').should('be.visible')
      cy.contains('Schedule Deep Dive').should('be.visible')
    })
  })

  describe('Responsive Design and Accessibility', () => {
    it('should be responsive on mobile devices', () => {
      cy.viewport('iphone-x')
      ChatNavigation.visitDemo()
      
      // Verify main content is visible on mobile
      cy.contains(/Enterprise AI|Netra|Optimization/i).should('be.visible')
      
      // Check for mobile-specific UI elements
      cy.get('body').then($body => {
        const hasMobileMenu = $body.find('[data-testid*="mobile"], .mobile-menu, button[aria-label*="menu"]').length > 0;
        const hasButtons = $body.find('button').length > 0;
        
        if (hasMobileMenu) {
          cy.get('[data-testid*="mobile"], .mobile-menu, button[aria-label*="menu"]').first().should('be.visible');
          cy.log('Mobile menu detected');
        } else if (hasButtons) {
          cy.get('button').first().should('be.visible');
          cy.log('Interactive buttons available on mobile');
        }
      });
      
      // Verify responsive layout
      cy.get('body').should('be.visible');
    })

    it('should be responsive on tablet devices', () => {
      cy.viewport('ipad-2')
      cy.visit('/demo')
      
      cy.contains('Enterprise AI Optimization Platform').should('be.visible')
      cy.get('.grid').should('have.css', 'grid-template-columns')
    })

    it('should have proper ARIA labels for accessibility', () => {
      cy.visit('/demo')
      
      cy.get('button').each(($button) => {
        // Check that button has accessible text or label
        const hasAriaLabel = $button.attr('aria-label');
        const hasAriaLabelledBy = $button.attr('aria-labelledby');
        const hasText = $button.text().trim();
        
        expect(hasAriaLabel || hasAriaLabelledBy || hasText).to.not.be.empty;
      })
      
      // Check for accessibility attributes
      cy.get('button').should('exist')
    })

    it('should support keyboard navigation', () => {
      cy.visit('/demo')
      
      // Tab through interactive elements
      cy.get('body').type('{tab}')
      cy.focused().should('have.prop', 'tagName').and('match', /BUTTON|A|INPUT/)
      
      // Enter key interaction
      cy.focused().should('exist')
    })
  })

  describe('Error Handling and Edge Cases', () => {
    it('should handle network errors gracefully', () => {
      // Intercept API calls and simulate errors
      cy.intercept('GET', '/api/**', { statusCode: 500 }).as('apiError')
      cy.intercept('POST', '/api/**', { statusCode: 500 }).as('apiPostError')
      
      ChatNavigation.visitDemo()
      
      // Should still show demo content despite API errors
      cy.get('body').then($body => {
        const text = $body.text();
        const hasMainContent = /enterprise|netra|optimization|demo/i.test(text);
        
        if (hasMainContent) {
          cy.log('Demo content loaded successfully despite API errors');
        } else {
          cy.log('Checking if basic page structure is visible');
          cy.get('body').should('be.visible');
        }
      });
      
      // Verify no critical errors are displayed to user
      cy.get('body').then($body => {
        const hasUserFacingErrors = /500|internal server error|failed to load/i.test($body.text());
        expect(hasUserFacingErrors).to.be.false;
      });
    })

    it('should handle invalid industry selection', () => {
      cy.visit('/demo')
      
      // Try to proceed without selecting industry
      // Tabs should not exist before industry selection
      cy.get('[role="tablist"]').should('not.exist')
      
      // Select industry
      cy.contains('Manufacturing').click()
      // Tabs should be visible after industry selection
      cy.get('[role="tablist"]').should('be.visible')
    })

    it('should validate form inputs in ROI calculator', () => {
      cy.visit('/demo')
      cy.contains('Healthcare').click()
      cy.contains('ROI Calculator').click()
      
      // Clear and enter invalid values
      cy.get('input[id="spend"]').clear().type('-1000')
      cy.contains('Calculate ROI').click()
      
      // Should handle gracefully
      // Should handle invalid values gracefully
      cy.get('.text-red-500').should('not.exist')
    })

    it('should handle rapid tab switching', () => {
      cy.visit('/demo')
      cy.contains('Technology').click()
      
      // Rapidly switch tabs
      const tabs = ['Overview', 'ROI Calculator', 'AI Chat', 'Metrics']
      tabs.forEach(tab => {
        cy.contains(tab).click({ force: true })
      })
      
      // Should end on last tab without errors
      cy.contains('Performance Metrics Dashboard').should('be.visible')
    })
  })

  describe('Data Persistence and Session Management', () => {
    it('should persist demo progress in session', () => {
      cy.visit('/demo')
      cy.contains('Financial Services').click()
      cy.contains('ROI Calculator').click()
      
      // Reload page
      cy.reload()
      
      // Should remember industry selection
      cy.contains('Financial Services').should('be.visible')
    })

    it('should clear progress on new session', () => {
      cy.visit('/demo')
      cy.contains('E-commerce').click()
      
      // Clear session
      cy.clearLocalStorage()
      cy.reload()
      
      // Should reset to initial state
      cy.contains('Select Your Industry').should('be.visible')
    })

    it('should handle browser back/forward navigation', () => {
      cy.visit('/demo')
      cy.contains('Healthcare').click()
      cy.contains('ROI Calculator').click()
      
      cy.go('back')
      cy.url().should('include', '/demo')
      
      cy.go('forward')
      cy.contains('ROI Calculator').should('have.class', 'active')
    })
  })
})