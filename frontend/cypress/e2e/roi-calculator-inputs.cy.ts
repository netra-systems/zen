/// <reference types="cypress" />

import { ROICalculatorHelpers, TestData } from '../support/roi-calculator-helpers'

// ROI Calculator Input Validation Tests
// BVJ: Enterprise segment - validates input accuracy for decision maker confidence  
// Updated for current SUT: 5 simple inputs (spend, requests, team size, latency, accuracy)
// Updated for current system: WebSocket events, /api/agents/execute, auth endpoints

describe('ROI Calculator Input Validation Tests', () => {
  beforeEach(() => {
    // Set up current authentication system
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-roi-calculator');
      win.localStorage.setItem('refresh_token', 'test-refresh-roi-calculator');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-roi',
        email: 'test@netrasystems.ai',
        name: 'Test User'
      }));
    });
    
    // Mock current authentication endpoints
    cy.intercept('GET', '/auth/config', {
      statusCode: 200,
      body: {
        oauth_enabled: false,
        password_auth_enabled: true,
        registration_enabled: true,
        demo_mode: false
      }
    }).as('authConfig');
    
    cy.intercept('GET', '/auth/me', {
      statusCode: 200,
      body: {
        id: 'test-user-roi',
        email: 'test@netrasystems.ai',
        name: 'Test User'
      }
    }).as('authMe');
    
    ROICalculatorHelpers.navigateToCalculator()
  })

  describe('Primary Input Fields', () => {
    it('should display monthly spend input', () => {
      cy.contains('Current Monthly AI Infrastructure Spend').should('be.visible')
      cy.get('input[id="spend"]').should('be.visible')
    })

    it('should update spend value', () => {
      cy.get('input[id="spend"]').clear().type('75000')
      cy.get('input[id="spend"]').should('have.value', '75000')
    })

    it('should display monthly requests input', () => {
      cy.contains('Monthly AI Requests').should('be.visible')
      cy.get('input[id="requests"]').should('be.visible')
    })

    it('should update requests value', () => {
      cy.get('input[id="requests"]').clear().type('25000000')
      cy.get('input[id="requests"]').should('have.value', '25000000')
    })

    it('should display average latency slider', () => {
      cy.contains('Average Latency (ms)').should('be.visible')
      cy.get('input[id="latency"]').should('be.visible')
    })

    it('should show latency value in real-time', () => {
      cy.get('input[id="latency"]').invoke('val', 300).trigger('input')
      cy.contains('300ms').should('be.visible')
    })
  })

  describe('Team and Performance Inputs', () => {
    it('should display team size slider', () => {
      cy.contains('AI/ML Team Size').should('be.visible')
      cy.get('input[id="team"]').should('be.visible')
    })

    it('should update team size value', () => {
      cy.get('input[id="team"]').invoke('val', 20).trigger('input')
      cy.contains('20').should('be.visible')
    })

    it('should display model accuracy slider', () => {
      cy.contains('Model Accuracy (%)').should('be.visible')
      cy.get('input[id="accuracy"]').should('be.visible')
    })

    it('should update accuracy percentage', () => {
      cy.get('input[id="accuracy"]').invoke('val', 88).trigger('input')
      cy.contains('88%').should('be.visible')
    })

    it('should validate slider ranges', () => {
      // Team size should be between 1-50
      cy.get('input[id="team"]').should('have.attr', 'min', '1')
      cy.get('input[id="team"]').should('have.attr', 'max', '50')
      
      // Accuracy should be between 70-99
      cy.get('input[id="accuracy"]').should('have.attr', 'min', '70')
      cy.get('input[id="accuracy"]').should('have.attr', 'max', '99')
    })
  })

  describe('Input Labels and Help Text', () => {
    it('should display proper input labels', () => {
      cy.get('label[for="spend"]').should('contain', 'Infrastructure Spend')
      cy.get('label[for="requests"]').should('contain', 'Monthly AI Requests')
      cy.get('label[for="team"]').should('contain', 'AI/ML Team Size')
      cy.get('label[for="latency"]').should('contain', 'Average Latency')
      cy.get('label[for="accuracy"]').should('contain', 'Model Accuracy')
    })

    it('should show helpful input descriptions', () => {
      cy.contains('Include compute, storage, and API costs').should('be.visible')
      cy.contains('Total inference and training requests').should('be.visible')
    })

    it('should display dollar sign icon for spend', () => {
      cy.get('svg').should('exist') // DollarSign icon
    })

    it('should show units for each input', () => {
      cy.contains('ms').should('be.visible') // latency
      cy.contains('%').should('be.visible')  // accuracy
    })

    it('should display industry multiplier information', () => {
      cy.contains('Industry multiplier applied').should('be.visible')
      cy.contains('Technology').should('be.visible')
      cy.contains('35% boost').should('be.visible')
    })
  })

  describe('Input Validation and Error Handling', () => {
    it('should handle empty spend input', () => {
      cy.get('input[id="spend"]').clear()
      cy.get('input[id="spend"]').should('have.value', '')
      // Calculator should handle gracefully
    })

    it('should handle negative spend values', () => {
      cy.get('input[id="spend"]').clear().type('-1000')
      cy.get('input[id="spend"]').should('have.value', '-1000')
    })

    it('should handle very large request values', () => {
      cy.get('input[id="requests"]').clear().type('999999999')
      cy.get('input[id="requests"]').should('have.value', '999999999')
    })

    it('should respect slider constraints', () => {
      // Test team size bounds
      cy.get('input[id="team"]').invoke('val', 0).trigger('input')
      cy.get('input[id="team"]').should('have.value', '1') // Should enforce minimum
      
      cy.get('input[id="team"]').invoke('val', 100).trigger('input')
      cy.get('input[id="team"]').should('have.value', '50') // Should enforce maximum
    })

    it('should handle basic API errors', () => {
      // Mock current agent execution endpoint for ROI calculation
      cy.intercept('POST', '/api/agents/execute', {
        statusCode: 500,
        body: { error: 'ROI calculation agent failed' }
      }).as('roiAgentError')
      
      // Mock WebSocket errors
      cy.intercept('/ws*', { statusCode: 500 }).as('wsError')
      
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      // Should not crash the interface
      cy.contains('ROI Calculator').should('be.visible')
    })

    it('should validate numeric inputs', () => {
      cy.get('input[id="spend"]').should('have.attr', 'type', 'number')
      cy.get('input[id="requests"]').should('have.attr', 'type', 'number')
    })

    it('should handle decimal values', () => {
      cy.get('input[id="spend"]').clear().type('50000.50')
      cy.get('input[id="spend"]').should('have.value', '50000.5')
    })
  })

  describe('Input Interaction Flows', () => {
    it('should maintain state during interaction', () => {
      cy.get('input[id="spend"]').clear().type('60000')
      cy.get('input[id="requests"]').clear().type('15000000')
      cy.get('input[id="team"]').invoke('val', 12).trigger('input')
      
      // Verify values are maintained
      cy.get('input[id="spend"]').should('have.value', '60000')
      cy.get('input[id="requests"]').should('have.value', '15000000')
      cy.contains('12').should('be.visible')
    })

    it('should enable calculation with valid inputs', () => {
      // Mock successful agent execution for ROI calculation
      cy.intercept('POST', '/api/agents/execute', {
        statusCode: 200,
        body: {
          agent_id: 'roi-calculator-agent',
          status: 'started',
          run_id: 'roi-calc-run',
          agent_type: 'ROICalculatorAgent'
        }
      }).as('roiAgentExecute')
      
      // Mock WebSocket connection for real-time updates
      cy.intercept('/ws*', {
        statusCode: 101,
        headers: { 'upgrade': 'websocket' }
      }).as('wsConnection')
      
      cy.get('input[id="spend"]').clear().type('50000')
      cy.get('input[id="requests"]').clear().type('10000000')
      
      cy.contains('button', 'Calculate ROI').should('not.be.disabled')
    })

    it('should update display values in real-time', () => {
      cy.get('input[id="latency"]').invoke('val', 350).trigger('input')
      cy.contains('350ms').should('be.visible')
      
      cy.get('input[id="accuracy"]').invoke('val', 94).trigger('input')
      cy.contains('94%').should('be.visible')
    })

    it('should handle rapid slider changes', () => {
      for(let i = 5; i <= 25; i += 5) {
        cy.get('input[id="team"]').invoke('val', i).trigger('input')
        cy.contains(i.toString()).should('be.visible')
      }
    })

    it('should validate input combinations work together', () => {
      // Mock WebSocket events for ROI calculation process
      cy.window().then((win) => {
        const store = (win as any).useUnifiedChatStore?.getState();
        if (store && store.handleWebSocketEvent) {
          setTimeout(() => {
            const roiEvents = [
              {
                type: 'agent_started',
                payload: {
                  agent_id: 'roi-calc-agent',
                  agent_type: 'ROICalculatorAgent'
                }
              },
              {
                type: 'tool_executing',
                payload: {
                  tool_name: 'roi_calculator',
                  agent_id: 'roi-calc-agent'
                }
              },
              {
                type: 'agent_thinking',
                payload: {
                  thought: 'Calculating ROI based on provided inputs...',
                  agent_id: 'roi-calc-agent'
                }
              },
              {
                type: 'tool_completed',
                payload: {
                  result: { roi: 250, monthly_savings: 12500 },
                  agent_id: 'roi-calc-agent'
                }
              },
              {
                type: 'agent_completed',
                payload: {
                  agent_id: 'roi-calc-agent',
                  result: { status: 'success' }
                }
              }
            ];
            
            roiEvents.forEach((event, index) => {
              setTimeout(() => {
                store.handleWebSocketEvent(event);
              }, index * 300);
            });
          }, 500);
        }
      });
      
      cy.get('input[id="spend"]').clear().type('25000')
      cy.get('input[id="requests"]').clear().type('5000000')
      cy.get('input[id="team"]').invoke('val', 3).trigger('input')
      cy.get('input[id="latency"]').invoke('val', 150).trigger('input')
      cy.get('input[id="accuracy"]').invoke('val', 90).trigger('input')
      
      cy.contains('button', 'Calculate ROI').should('not.be.disabled')
    })

    it('should provide visual feedback for inputs', () => {
      cy.get('input[id="spend"]').focus()
      cy.focused().should('have.attr', 'id', 'spend')
    })

    it('should handle keyboard navigation', () => {
      cy.get('input[id="spend"]').focus()
      cy.focused().tab()
      cy.focused().should('have.attr', 'id', 'requests')
    })

    it('should validate default values are loaded', () => {
      cy.get('input[id="spend"]').should('have.value', '50000')
      cy.get('input[id="requests"]').should('have.value', '10000000')
    })
  })

})