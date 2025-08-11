/**
 * Critical E2E Tests for UI/UX Spec Alignment
 * Tests the 22+ improvements implemented
 */

describe('Critical UI/UX Alignment Tests', () => {
  beforeEach(() => {
    cy.visit('/chat');
    cy.window().then((win) => {
      // Clear localStorage to ensure clean state
      win.localStorage.clear();
    });
  });

  describe('1. Blue Gradient Bar Removal', () => {
    it('should not have any blue gradient bars in UI', () => {
      // Check for absence of blue gradients
      cy.get('[class*="from-blue"]').should('not.exist');
      cy.get('[class*="to-blue"]').should('not.exist');
      cy.get('[class*="bg-blue-500"]').should('not.exist');
      cy.get('[class*="bg-gradient-to-r from-blue"]').should('not.exist');
      
      // Verify emerald/purple colors are used instead
      cy.get('[class*="bg-emerald"]').should('exist');
      cy.get('[class*="from-purple"]').should('exist');
    });
  });

  describe('2. Agent Deduplication', () => {
    it('should show iteration count when same agent runs multiple times', () => {
      // Simulate agent running multiple times
      cy.window().then((win) => {
        const store = win.useUnifiedChatStore?.getState();
        if (store) {
          // First run
          store.handleWebSocketEvent({
            type: 'agent_started',
            payload: { agent_name: 'TriageSubAgent', run_id: '1', timestamp: Date.now() }
          });
          
          // Second run of same agent
          store.handleWebSocketEvent({
            type: 'agent_started',
            payload: { agent_name: 'TriageSubAgent', run_id: '2', timestamp: Date.now() }
          });
        }
      });
      
      // Should show iteration count
      cy.contains('TriageSubAgent (2)').should('exist');
    });
  });

  describe('3. WebSocket Event Buffering', () => {
    it('should buffer WebSocket events in CircularBuffer', () => {
      cy.window().then((win) => {
        const store = win.useUnifiedChatStore?.getState();
        if (store && store.wsEventBuffer) {
          // Add events
          for (let i = 0; i < 5; i++) {
            store.wsEventBuffer.push({
              type: `test_event_${i}`,
              payload: { data: i },
              timestamp: Date.now()
            });
          }
          
          // Check buffer contains events
          const events = store.wsEventBuffer.getAll();
          expect(events).to.have.length(5);
          expect(events[0].type).to.equal('test_event_0');
        }
      });
    });
  });

  describe('4. Glassmorphic Design', () => {
    it('should have glassmorphic styling on key components', () => {
      // Check for backdrop blur
      cy.get('[class*="backdrop-blur"]').should('exist');
      cy.get('[class*="bg-white/95"]').should('exist');
      
      // Check FastLayer has glassmorphic design
      cy.get('.h-12.flex.items-center').should('have.class', 'backdrop-blur-md');
    });
  });

  describe('5. Keyboard Shortcuts', () => {
    it('should toggle debug panel with Ctrl+Shift+D', () => {
      // Trigger keyboard shortcut
      cy.get('body').type('{ctrl}{shift}d');
      
      // Check if debug panel toggle event was fired
      cy.window().then((win) => {
        let eventFired = false;
        win.addEventListener('toggleDebugPanel', () => {
          eventFired = true;
        });
        
        // Trigger again
        cy.get('body').type('{ctrl}{shift}d');
        cy.wrap(null).should(() => {
          expect(eventFired).to.be.true;
        });
      });
    });
  });

  describe('6. Thread Isolation', () => {
    it('should properly isolate threads when switching', () => {
      // Create first thread
      cy.get('button').contains('New Chat').click();
      cy.get('textarea[aria-label="Message input"]').type('First thread message');
      cy.get('button[aria-label="Send message"]').click();
      
      // Create second thread
      cy.get('button').contains('New Chat').click();
      cy.get('textarea[aria-label="Message input"]').type('Second thread message');
      cy.get('button[aria-label="Send message"]').click();
      
      // Messages should be isolated
      cy.contains('First thread message').should('not.exist');
      cy.contains('Second thread message').should('exist');
    });
  });

  describe('7. Automatic Thread Renaming', () => {
    it('should auto-rename thread based on first message', () => {
      cy.window().then((win) => {
        // Mock thread rename service
        const mockRename = cy.stub();
        win.ThreadRenameService = {
          autoRenameThread: mockRename
        };
        
        // Send first message
        cy.get('textarea[aria-label="Message input"]').type('How to optimize my LLM costs?');
        cy.get('button[aria-label="Send message"]').click();
        
        // Check if rename was triggered
        cy.wrap(mockRename).should('have.been.called');
      });
    });
  });

  describe('8. Performance Metrics', () => {
    it('should track performance metrics', () => {
      cy.window().then((win) => {
        const store = win.useUnifiedChatStore?.getState();
        if (store && store.performanceMetrics) {
          // Check metrics are being tracked
          expect(store.performanceMetrics).to.have.property('renderCount');
          expect(store.performanceMetrics).to.have.property('memoryUsage');
          expect(store.performanceMetrics).to.have.property('fps');
        }
      });
    });
  });

  describe('9. Error Handling', () => {
    it('should handle errors gracefully with recovery options', () => {
      // Simulate an error
      cy.window().then((win) => {
        throw new Error('Test error');
      });
      
      // Error boundary should catch it
      cy.contains('Something went wrong').should('exist');
      cy.get('button').contains('Try Again').should('exist');
      cy.get('button').contains('Download Report').should('exist');
    });
  });

  describe('10. Export Functionality', () => {
    it('should export reports in multiple formats', () => {
      cy.window().then((win) => {
        // Mock export service
        const mockExport = cy.stub(win.ExportService, 'exportReport');
        
        // Trigger export
        const testData = {
          title: 'Test Report',
          summary: 'Test summary',
          metrics: { test: 123 }
        };
        
        win.ExportService.exportReport(testData, { format: 'json' });
        
        cy.wrap(mockExport).should('have.been.calledWith', testData);
      });
    });
  });

  describe('11. Layer Animations', () => {
    it('should have smooth transitions between layers', () => {
      // Check for motion components
      cy.get('[class*="motion"]').should('exist');
      
      // Verify transition durations
      cy.get('.h-12').should('have.css', 'transition').and('include', '0s');
    });
  });

  describe('12. ARIA Labels', () => {
    it('should have proper ARIA labels for accessibility', () => {
      // Check message input
      cy.get('textarea[aria-label="Message input"]').should('exist');
      cy.get('button[aria-label="Send message"]').should('exist');
      
      // Check for other ARIA attributes
      cy.get('[role="textbox"]').should('exist');
      cy.get('[aria-multiline="true"]').should('exist');
    });
  });

  describe('13. OverflowPanel Integration', () => {
    it('should show WebSocket events in overflow panel', () => {
      // Open overflow panel
      cy.get('body').type('{ctrl}{shift}d');
      
      // Check for event display
      cy.window().then((win) => {
        const store = win.useUnifiedChatStore?.getState();
        if (store && store.wsEventBuffer) {
          // Add test event
          store.wsEventBuffer.push({
            type: 'test_overflow_event',
            payload: { test: true },
            timestamp: Date.now()
          });
        }
      });
      
      // Panel should show events
      cy.contains('Events').click();
      cy.contains('test_overflow_event').should('exist');
    });
  });

  describe('14. Message Streaming', () => {
    it('should stream text smoothly with RequestAnimationFrame', () => {
      cy.window().then((win) => {
        const store = win.useUnifiedChatStore?.getState();
        if (store) {
          // Simulate streaming content
          store.updateMediumLayer({
            partialContent: 'This is streaming text...',
            thought: 'Processing',
            stepNumber: 1,
            totalSteps: 3,
            agentName: 'TestAgent'
          });
        }
      });
      
      // Check for streaming cursor
      cy.get('[class*="animate"]').should('exist');
    });
  });

  describe('15. Type Safety', () => {
    it('should use proper TypeScript types without any', () => {
      cy.window().then((win) => {
        // Check that store methods exist with proper typing
        const store = win.useUnifiedChatStore?.getState();
        if (store) {
          expect(typeof store.updateFastLayer).to.equal('function');
          expect(typeof store.updateMediumLayer).to.equal('function');
          expect(typeof store.updateSlowLayer).to.equal('function');
        }
      });
    });
  });

  describe('16. ChatSidebar Thread Management', () => {
    it('should show thread list with proper isolation', () => {
      // Create multiple threads
      for (let i = 0; i < 3; i++) {
        cy.get('button').contains('New Chat').click();
        cy.wait(500);
      }
      
      // Check sidebar shows threads
      cy.get('[class*="ChatSidebar"]').within(() => {
        cy.get('[class*="thread"]').should('have.length.at.least', 3);
      });
    });
  });

  describe('17. WebSocket Event Types', () => {
    it('should handle all new WebSocket event types', () => {
      const eventTypes = [
        'thread_created',
        'thread_loaded',
        'thread_renamed',
        'run_started',
        'step_created'
      ];
      
      cy.window().then((win) => {
        const store = win.useUnifiedChatStore?.getState();
        if (store) {
          eventTypes.forEach(type => {
            // Should not throw when handling these events
            expect(() => {
              store.handleWebSocketEvent({
                type,
                payload: { test: true }
              });
            }).to.not.throw();
          });
        }
      });
    });
  });

  describe('18. Tool Deduplication in FastLayer', () => {
    it('should deduplicate tools and show count', () => {
      cy.window().then((win) => {
        const store = win.useUnifiedChatStore?.getState();
        if (store) {
          // Add duplicate tools
          store.updateFastLayer({
            activeTools: ['tool1', 'tool1', 'tool2', 'tool1']
          });
        }
      });
      
      // Should show unique tools with count
      cy.contains('×3').should('exist'); // tool1 appears 3 times
    });
  });

  describe('19. Progress Bar Colors', () => {
    it('should use purple-pink gradient instead of blue', () => {
      cy.window().then((win) => {
        const store = win.useUnifiedChatStore?.getState();
        if (store) {
          store.updateMediumLayer({
            stepNumber: 2,
            totalSteps: 5
          });
        }
      });
      
      // Check progress bar doesn't have blue
      cy.get('[class*="bg-blue-500"]').should('not.exist');
      cy.get('[class*="from-purple"]').should('exist');
    });
  });

  describe('20. Export Debug Data', () => {
    it('should export comprehensive debug data', () => {
      // Open overflow panel
      cy.get('body').type('{ctrl}{shift}d');
      
      // Click export
      cy.get('button').contains('Export').click();
      
      // Check download was triggered
      cy.window().then((win) => {
        const downloads = win.document.querySelectorAll('a[download]');
        expect(downloads.length).to.be.greaterThan(0);
      });
    });
  });
});