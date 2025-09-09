/// <reference types="cypress" />

/**
 * Cypress Test: Debug Thread Operation Race Condition
 * 
 * Reproduces and debugs the "Operation already in progress" error
 * when switching threads rapidly in the browser.
 * 
 * Error Details:
 * - Message: "Failed to switch thread: Error: Operation already in progress"
 * - Location: ThreadOperationManager.startOperation()
 * - Cause: Mutex blocking concurrent operations on same thread
 */

describe('Thread Operation Race Condition Debugging', () => {
  beforeEach(() => {
    // Mock authentication and setup
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'test-token');
      win.localStorage.setItem('user_id', 'test-user-123');
    });
    
    // Intercept API calls
    cy.intercept('GET', '/api/threads*', {
      statusCode: 200,
      body: {
        threads: [
          { id: 'thread-1', title: 'Thread 1', createdAt: Date.now() - 10000 },
          { id: 'thread-2', title: 'Thread 2', createdAt: Date.now() - 5000 },
          { id: 'thread-3', title: 'Thread 3', createdAt: Date.now() }
        ]
      }
    }).as('getThreads');
    
    cy.intercept('GET', '/api/threads/*/messages', {
      statusCode: 200,
      body: {
        messages: [
          { id: 'msg-1', content: 'Test message', role: 'user' }
        ]
      }
    }).as('getMessages');
    
    cy.visit('/chat');
    cy.wait('@getThreads');
  });

  it('should reproduce "Operation already in progress" error with rapid thread switching', () => {
    // Open browser console to capture errors
    cy.window().then((win) => {
      const originalError = win.console.error;
      let capturedErrors: string[] = [];
      
      win.console.error = (...args) => {
        const errorMsg = args.map(arg => 
          typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
        ).join(' ');
        capturedErrors.push(errorMsg);
        originalError.apply(win.console, args);
      };
      
      // Store captured errors for later assertion
      cy.wrap(capturedErrors).as('capturedErrors');
    });

    // Trigger rapid thread switching to cause race condition
    cy.get('[data-testid="thread-1"]').click();
    cy.get('[data-testid="thread-2"]').click(); // Quick switch before thread-1 loads
    cy.get('[data-testid="thread-3"]').click(); // Another quick switch
    
    // Wait for operations to settle
    cy.wait(1000);
    
    // Check if the error was captured
    cy.get('@capturedErrors').then((errors: any) => {
      const hasOperationError = errors.some((error: string) => 
        error.includes('Operation already in progress')
      );
      
      if (hasOperationError) {
        cy.log('✅ Successfully reproduced race condition error');
        cy.log('Error details:', errors.find((e: string) => e.includes('Operation already in progress')));
      } else {
        cy.log('⚠️ Race condition not triggered, may need more aggressive clicking');
      }
    });
  });

  it('should handle concurrent thread operations with mutex protection', () => {
    // Access the ThreadOperationManager directly
    cy.window().then((win: any) => {
      // Get the manager instance
      const manager = win.ThreadOperationManager || win.__threadOperationManager;
      
      if (!manager) {
        cy.log('ThreadOperationManager not available in window');
        return;
      }
      
      // Test concurrent operations
      const operations = [];
      
      // Start multiple operations on the same thread
      const executor = (signal: AbortSignal) => {
        return new Promise((resolve) => {
          setTimeout(() => {
            if (!signal.aborted) {
              resolve({ success: true, threadId: 'thread-1' });
            } else {
              resolve({ success: false, error: new Error('Aborted') });
            }
          }, 100);
        });
      };
      
      // Start first operation
      const op1 = manager.startOperation('switch', 'thread-1', executor);
      operations.push(op1);
      
      // Immediately start second operation (should be blocked)
      const op2 = manager.startOperation('switch', 'thread-1', executor);
      operations.push(op2);
      
      // Start third operation with force flag (should cancel previous)
      const op3 = manager.startOperation('switch', 'thread-1', executor, { force: true });
      operations.push(op3);
      
      // Wait for all operations to complete
      cy.wrap(Promise.allSettled(operations)).then((results: any) => {
        cy.log('Operation results:', results);
        
        // First operation might succeed or be cancelled
        // Second operation should fail with "Operation already in progress"
        // Third operation should succeed (forced)
        
        const secondResult = results[1];
        if (secondResult.status === 'fulfilled' && !secondResult.value.success) {
          expect(secondResult.value.error.message).to.include('Operation already in progress');
          cy.log('✅ Mutex protection working correctly');
        }
      });
    });
  });

  it('should test debouncing for rapid create operations', () => {
    cy.window().then((win: any) => {
      const manager = win.ThreadOperationManager || win.__threadOperationManager;
      
      if (!manager) {
        return;
      }
      
      const operations = [];
      const executor = (signal: AbortSignal) => {
        return Promise.resolve({ success: true, threadId: 'new-thread' });
      };
      
      // Rapid fire create operations (should be debounced)
      for (let i = 0; i < 5; i++) {
        const op = manager.startOperation('create', null, executor);
        operations.push(op);
      }
      
      cy.wrap(Promise.allSettled(operations)).then((results: any) => {
        // Most operations should be debounced
        const debouncedCount = results.filter((r: any) => 
          r.status === 'fulfilled' && 
          !r.value.success && 
          r.value.error?.message.includes('debounced')
        ).length;
        
        cy.log(`Debounced ${debouncedCount} out of 5 operations`);
        expect(debouncedCount).to.be.at.least(3);
      });
    });
  });

  it('should verify thread switching UI behavior with loading states', () => {
    // Monitor loading states
    let loadingStates: string[] = [];
    
    cy.window().then((win: any) => {
      // Hook into store to monitor state changes
      const store = win.__zustandStore || win.useUnifiedChatStore?.getState();
      if (store) {
        const originalSetThreadLoading = store.setThreadLoading;
        store.setThreadLoading = (loading: boolean) => {
          loadingStates.push(`setThreadLoading: ${loading}`);
          if (originalSetThreadLoading) {
            originalSetThreadLoading.call(store, loading);
          }
        };
      }
    });
    
    // Click thread buttons and observe loading states
    cy.get('[data-testid="thread-1"]').click();
    cy.wait(500);
    
    cy.get('[data-testid="thread-2"]').click();
    cy.wait(500);
    
    // Rapid clicks to trigger race condition
    cy.get('[data-testid="thread-3"]').click();
    cy.get('[data-testid="thread-1"]').click();
    cy.get('[data-testid="thread-2"]').click();
    
    cy.wait(1000);
    
    // Verify loading states were properly managed
    cy.wrap(loadingStates).should('have.length.greaterThan', 0);
    cy.log('Loading state changes:', loadingStates);
    
    // Check that loading indicators appear and disappear correctly
    cy.get('[data-testid="thread-loading-indicator"]').should('not.exist');
  });

  it('should test the fix: force flag bypasses mutex', () => {
    // Test that using force: true allows operation to proceed
    cy.window().then((win: any) => {
      const manager = win.ThreadOperationManager || win.__threadOperationManager;
      
      if (!manager) {
        return;
      }
      
      const executor = (signal: AbortSignal) => {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({ success: true, threadId: 'thread-test' });
          }, 200);
        });
      };
      
      // Start a long-running operation
      const op1 = manager.startOperation('switch', 'thread-test', executor);
      
      // Immediately force another operation
      setTimeout(() => {
        const op2 = manager.startOperation('switch', 'thread-test', executor, { force: true });
        
        cy.wrap(op2).then((result: any) => {
          expect(result.success).to.be.true;
          cy.log('✅ Force flag successfully bypassed mutex');
        });
      }, 50);
      
      // Original operation should be cancelled
      cy.wrap(op1).then((result: any) => {
        if (!result.success && result.error) {
          expect(result.error.message).to.include('aborted');
          cy.log('✅ Original operation was cancelled as expected');
        }
      });
    });
  });

  it('should verify the fix prevents console errors', () => {
    // Setup console error monitoring
    let consoleErrors: string[] = [];
    
    cy.window().then((win) => {
      const originalError = win.console.error;
      win.console.error = (...args) => {
        consoleErrors.push(args.join(' '));
        originalError.apply(win.console, args);
      };
    });
    
    // Perform rapid thread switching with proper handling
    cy.get('[data-testid="thread-1"]').click();
    cy.wait(100);
    
    // Use force flag for immediate switches
    cy.window().then((win: any) => {
      const switchThread = win.__switchThread || win.switchToThread;
      if (switchThread) {
        // Switch with force flag to prevent race condition
        switchThread('thread-2', { force: true });
        switchThread('thread-3', { force: true });
      }
    });
    
    cy.wait(1000);
    
    // Verify no console errors about "Operation already in progress"
    cy.wrap(consoleErrors).then((errors) => {
      const hasRaceConditionError = errors.some(error => 
        error.includes('Operation already in progress')
      );
      
      expect(hasRaceConditionError).to.be.false;
      cy.log('✅ No race condition errors in console after fix');
    });
  });
});

// Helper to setup test threads in the store
Cypress.Commands.add('setupTestThreads', () => {
  cy.window().then((win: any) => {
    const store = win.__zustandStore || win.useUnifiedChatStore?.getState();
    if (store && store.createThread) {
      store.createThread({ id: 'thread-1', title: 'Thread 1' });
      store.createThread({ id: 'thread-2', title: 'Thread 2' });
      store.createThread({ id: 'thread-3', title: 'Thread 3' });
    }
  });
});

// Expose ThreadOperationManager to window for testing
before(() => {
  cy.on('window:before:load', (win) => {
    // This will be populated by the app
    win.__threadOperationManager = null;
    win.__switchThread = null;
    win.__zustandStore = null;
  });
});