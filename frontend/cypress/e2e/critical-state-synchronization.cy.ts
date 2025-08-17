/// <reference types="cypress" />

describe('CRITICAL: State Management & Synchronization', () => {
  // Test configuration
  const LAYER_UPDATE_TIMEOUT = 5000;
  const STATE_SYNC_DELAY = 1000;
  const MAX_CONCURRENT_UPDATES = 10;
  
  beforeEach(() => {
    cy.viewport(1920, 1080);
    
    // Set up auth and initial state
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'test-token');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user',
        email: 'test@netrasystems.ai',
        name: 'Test User'
      }));
      
      // Clear any existing state
      win.localStorage.removeItem('unified-chat-storage');
      win.localStorage.removeItem('chat_state');
      win.sessionStorage.clear();
    });
    
    // Visit demo and navigate to chat
    cy.visit('/demo');
    cy.contains('Technology').click();
    cy.contains('AI Chat').click({ force: true });
    cy.wait(1000);
  });
  
  describe('Zustand Store Race Conditions', () => {
    it('CRITICAL: Should handle concurrent state updates without data loss', () => {
      // Generate concurrent update events
      const updates: any[] = [];
      for (let i = 0; i < MAX_CONCURRENT_UPDATES; i++) {
        updates.push({
          type: 'message',
          id: `msg_${Date.now()}_${i}`,
          content: `Concurrent message ${i}`,
          timestamp: Date.now() + i
        });
      }
      
      // Trigger all updates simultaneously
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        
        if (store) {
          // Launch all updates in parallel
          const promises = updates.map(update => {
            return new Promise((resolve) => {
              setTimeout(() => {
                store.getState().addMessage({
                  id: update.id,
                  content: update.content,
                  role: 'user',
                  timestamp: update.timestamp
                });
                resolve(null);
              }, Math.random() * 100); // Random delay to increase collision chance
            });
          });
          
          return Promise.all(promises);
        }
      });
      
      // Wait for all updates to process
      cy.wait(2000);
      
      // Verify all messages were added
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          const state = store.getState();
          const messages = state.messages || [];
          
          // Check that all updates were preserved
          updates.forEach(update => {
            const found = messages.find((m: any) => m.id === update.id);
            expect(found).to.not.be.undefined;
            if (found) {
              expect(found.content).to.equal(update.content);
            }
          });
          
          // Verify no duplicates
          const uniqueIds = new Set(messages.map((m: any) => m.id));
          expect(uniqueIds.size).to.equal(messages.length);
        }
      });
    });
    
    it('CRITICAL: Should prevent update loops in cross-component sync', () => {
      let updateCount = 0;
      let lastUpdateTime = 0;
      
      // Monitor state updates
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          // Subscribe to state changes
          store.subscribe(() => {
            updateCount++;
            lastUpdateTime = Date.now();
          });
        }
      });
      
      // Trigger circular update scenario
      cy.window().then((win) => {
        // Simulate component A updating state
        win.dispatchEvent(new CustomEvent('netra:state:update', {
          detail: { source: 'componentA', data: { value: 1 } }
        }));
        
        // Simulate component B reacting to A's update
        win.dispatchEvent(new CustomEvent('netra:state:update', {
          detail: { source: 'componentB', data: { value: 2 } }
        }));
        
        // Simulate component A reacting to B's update (potential loop)
        win.dispatchEvent(new CustomEvent('netra:state:update', {
          detail: { source: 'componentA', data: { value: 3 } }
        }));
      });
      
      // Wait for updates to settle
      cy.wait(2000);
      
      // Verify no runaway updates
      cy.wrap(null).then(() => {
        expect(updateCount).to.be.lessThan(
          20,
          'Should not have excessive updates (indicates update loop)'
        );
        
        const timeSinceLastUpdate = Date.now() - lastUpdateTime;
        expect(timeSinceLastUpdate).to.be.greaterThan(
          500,
          'Updates should have stopped (no ongoing loop)'
        );
      });
    });
  });
  
  describe('Layer Data Synchronization', () => {
    it('CRITICAL: Should properly accumulate partial content in medium layer', () => {
      const chunks = [
        'This is ',
        'a test of ',
        'partial content ',
        'accumulation in ',
        'the medium layer.'
      ];
      
      let accumulatedContent = '';
      
      // Simulate streaming partial content
      chunks.forEach((chunk, index) => {
        cy.window().then((win) => {
          const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
          if (store) {
            accumulatedContent += chunk;
            
            store.getState().updateMediumLayer({
              partialContent: accumulatedContent,
              isStreaming: index < chunks.length - 1,
              timestamp: Date.now()
            });
          }
        });
        
        cy.wait(100); // Simulate streaming delay
      });
      
      // Verify final accumulated content
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          const state = store.getState();
          const mediumLayer = state.mediumLayerData;
          
          expect(mediumLayer).to.not.be.null;
          expect(mediumLayer.partialContent).to.equal(
            chunks.join(''),
            'Content should be properly accumulated'
          );
          expect(mediumLayer.isStreaming).to.be.false;
        }
      });
    });
    
    it('CRITICAL: Should not lose data when layers update simultaneously', () => {
      const testData = {
        fast: { status: 'processing', startTime: Date.now() },
        medium: { progress: 50, message: 'Analyzing...' },
        slow: { completedAgents: ['agent1'], totalAgents: 3 }
      };
      
      // Update all layers simultaneously
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          // Fire updates in parallel
          Promise.all([
            new Promise((resolve) => {
              store.getState().updateFastLayer(testData.fast);
              resolve(null);
            }),
            new Promise((resolve) => {
              store.getState().updateMediumLayer(testData.medium);
              resolve(null);
            }),
            new Promise((resolve) => {
              store.getState().updateSlowLayer(testData.slow);
              resolve(null);
            })
          ]);
        }
      });
      
      cy.wait(1000);
      
      // Verify all layer data is preserved
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          const state = store.getState();
          
          // Check fast layer
          expect(state.fastLayerData).to.deep.include(testData.fast);
          
          // Check medium layer
          expect(state.mediumLayerData).to.deep.include(testData.medium);
          
          // Check slow layer
          expect(state.slowLayerData).to.deep.include(testData.slow);
        }
      });
    });
    
    it('CRITICAL: Should handle completed agents accumulation correctly', () => {
      const agents = [
        { name: 'TriageAgent', result: 'Categorized as optimization request' },
        { name: 'DataAgent', result: 'Collected performance metrics' },
        { name: 'OptimizationAgent', result: 'Generated optimization plan' }
      ];
      
      // Add agents one by one
      agents.forEach((agent, index) => {
        cy.window().then((win) => {
          const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
          if (store) {
            const currentAgents = store.getState().slowLayerData?.completedAgents || [];
            
            store.getState().updateSlowLayer({
              completedAgents: [...currentAgents, agent],
              progress: ((index + 1) / agents.length) * 100
            });
          }
        });
        
        cy.wait(500);
      });
      
      // Verify all agents accumulated
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          const state = store.getState();
          const completedAgents = state.slowLayerData?.completedAgents || [];
          
          expect(completedAgents).to.have.length(agents.length);
          agents.forEach((agent, index) => {
            expect(completedAgents[index]).to.deep.include(agent);
          });
          
          expect(state.slowLayerData?.progress).to.equal(100);
        }
      });
    });
  });
  
  describe('LocalStorage Persistence & Recovery', () => {
    it('CRITICAL: Should recover from corrupted localStorage data', () => {
      // Corrupt localStorage deliberately
      cy.window().then((win) => {
        win.localStorage.setItem('unified-chat-storage', '{{invalid json}}');
        win.localStorage.setItem('chat_state', 'null{broken}');
      });
      
      // Reload the page
      cy.reload();
      
      // Navigate back to chat
      cy.contains('Technology').click();
      cy.contains('AI Chat').click({ force: true });
      cy.wait(1000);
      
      // Verify app recovered and is functional
      const testMessage = `Recovery test ${Date.now()}`;
      cy.get('textarea').type(testMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(testMessage).should('be.visible');
      
      // Verify clean state was initialized
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          const state = store.getState();
          expect(state).to.not.be.null;
          expect(state.messages).to.be.an('array');
        }
      });
    });
    
    it('CRITICAL: Should maintain state consistency across tabs', () => {
      const sharedMessage = `Shared message ${Date.now()}`;
      
      // Send message in current tab
      cy.get('textarea').type(sharedMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(sharedMessage).should('be.visible');
      
      // Simulate state change from another tab
      cy.window().then((win) => {
        const otherTabMessage = {
          id: `other_tab_${Date.now()}`,
          content: 'Message from another tab',
          role: 'user',
          timestamp: Date.now()
        };
        
        // Update localStorage as if from another tab
        const currentState = win.localStorage.getItem('chat_state');
        let state = currentState ? JSON.parse(currentState) : { messages: [] };
        state.messages = state.messages || [];
        state.messages.push(otherTabMessage);
        win.localStorage.setItem('chat_state', JSON.stringify(state));
        
        // Trigger storage event
        win.dispatchEvent(new StorageEvent('storage', {
          key: 'chat_state',
          newValue: JSON.stringify(state),
          oldValue: currentState,
          storageArea: win.localStorage
        }));
      });
      
      // Wait for sync
      cy.wait(1000);
      
      // Verify both messages are visible
      cy.contains(sharedMessage).should('be.visible');
      cy.contains('Message from another tab').should('be.visible');
      
      // Verify state consistency
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          const messages = store.getState().messages;
          expect(messages.length).to.be.at.least(2);
        }
      });
    });
  });
  
  describe('Thread Management State', () => {
    it('CRITICAL: Should handle concurrent thread creation without conflicts', () => {
      const threadCount = 10;
      const threads: any[] = [];
      
      // Create multiple threads rapidly
      for (let i = 0; i < threadCount; i++) {
        threads.push({
          id: `thread_${Date.now()}_${i}`,
          title: `Thread ${i}`,
          createdAt: Date.now() + i
        });
        
        cy.window().then((win) => {
          const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
          if (store) {
            store.getState().createThread(threads[i]);
          }
        });
      }
      
      cy.wait(1000);
      
      // Verify all threads created
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          const state = store.getState();
          const threadMap = state.threads;
          
          expect(threadMap.size).to.equal(threadCount);
          
          threads.forEach(thread => {
            expect(threadMap.has(thread.id)).to.be.true;
            const stored = threadMap.get(thread.id);
            expect(stored.title).to.equal(thread.title);
          });
        }
      });
    });
    
    it('CRITICAL: Should prevent message crossover between threads', () => {
      // Create two threads
      const thread1 = { id: 'thread1', title: 'Thread 1' };
      const thread2 = { id: 'thread2', title: 'Thread 2' };
      
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          store.getState().createThread(thread1);
          store.getState().createThread(thread2);
        }
      });
      
      // Add messages to thread1
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          store.getState().setActiveThread(thread1.id);
          store.getState().addMessage({
            id: 'msg1_thread1',
            content: 'Message for thread 1',
            threadId: thread1.id
          });
        }
      });
      
      // Switch to thread2 and add messages
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          store.getState().setActiveThread(thread2.id);
          store.getState().addMessage({
            id: 'msg1_thread2',
            content: 'Message for thread 2',
            threadId: thread2.id
          });
        }
      });
      
      // Verify messages are in correct threads
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          const state = store.getState();
          const messages = state.messages;
          
          const thread1Messages = messages.filter((m: any) => m.threadId === thread1.id);
          const thread2Messages = messages.filter((m: any) => m.threadId === thread2.id);
          
          expect(thread1Messages).to.have.length(1);
          expect(thread2Messages).to.have.length(1);
          
          expect(thread1Messages[0].content).to.include('thread 1');
          expect(thread2Messages[0].content).to.include('thread 2');
        }
      });
    });
  });
  
  describe('State Migration & Compatibility', () => {
    it('CRITICAL: Should migrate old state schema to new format', () => {
      // Set old format state
      const oldStateFormat = {
        messages: [
          { text: 'Old message 1', timestamp: Date.now() - 10000 },
          { text: 'Old message 2', timestamp: Date.now() - 5000 }
        ],
        user: 'test-user',
        session: 'old-session'
      };
      
      cy.window().then((win) => {
        win.localStorage.setItem('legacy_chat_state', JSON.stringify(oldStateFormat));
      });
      
      // Trigger migration
      cy.window().then((win) => {
        win.dispatchEvent(new CustomEvent('netra:migrate:state'));
      });
      
      cy.wait(1000);
      
      // Verify migration completed
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          const state = store.getState();
          const messages = state.messages;
          
          // Old messages should be migrated with proper structure
          expect(messages).to.have.length.at.least(2);
          messages.forEach((msg: any) => {
            expect(msg).to.have.property('id');
            expect(msg).to.have.property('content');
            expect(msg).to.have.property('timestamp');
            expect(msg).to.have.property('role');
          });
        }
      });
    });
  });
  
  describe('Performance & Memory Management', () => {
    it('CRITICAL: Should handle 1000+ messages without performance degradation', () => {
      const messageCount = 1000;
      const startTime = Date.now();
      
      // Add many messages
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          for (let i = 0; i < messageCount; i++) {
            store.getState().addMessage({
              id: `perf_test_${i}`,
              content: `Performance test message ${i}`,
              role: i % 2 === 0 ? 'user' : 'assistant',
              timestamp: Date.now() + i
            });
          }
        }
      });
      
      const addTime = Date.now() - startTime;
      
      // Verify performance
      expect(addTime).to.be.lessThan(
        5000,
        `Adding ${messageCount} messages should take less than 5 seconds`
      );
      
      // Test state access performance
      const accessStartTime = Date.now();
      
      cy.window().then((win) => {
        const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
        if (store) {
          const state = store.getState();
          const messages = state.messages;
          
          // Access all messages
          messages.forEach((msg: any) => {
            const _ = msg.content; // Force access
          });
        }
      });
      
      const accessTime = Date.now() - accessStartTime;
      
      expect(accessTime).to.be.lessThan(
        1000,
        'Accessing all messages should take less than 1 second'
      );
      
      // Check memory usage
      cy.window().then((win) => {
        if ((win.performance as any).memory) {
          const memoryUsed = (win.performance as any).memory.usedJSHeapSize;
          const memoryPerMessage = memoryUsed / messageCount;
          
          // Each message should use less than 10KB on average
          expect(memoryPerMessage).to.be.lessThan(
            10 * 1024,
            'Memory usage per message should be reasonable'
          );
        }
      });
    });
  });
  
  afterEach(() => {
    // Clean up state
    cy.window().then((win) => {
      win.localStorage.removeItem('unified-chat-storage');
      win.localStorage.removeItem('chat_state');
      win.localStorage.removeItem('legacy_chat_state');
      win.sessionStorage.clear();
      
      // Reset store if available
      const store = (win as any).__NETRA_STORE || (win as any).unifiedChatStore;
      if (store && store.getState().reset) {
        store.getState().reset();
      }
    });
  });
});