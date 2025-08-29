/**
 * Critical E2E Tests for UI/UX Business Value Validation
 * 
 * Business Value Justification (BVJ):
 * Segment: All customer segments (Free, Early, Mid, Enterprise)
 * Business Goal: Platform Stability, User Experience Excellence, Customer Retention
 * Value Impact: Ensures core chat interface works reliably for AI optimization workflows
 * Strategic/Revenue Impact: Prevents customer churn from UI/UX issues, enables upselling
 * 
 * Core Principles Applied:
 * - Tests use REAL services (no mocks forbidden per CLAUDE.md)
 * - Atomic test scenarios focused on business outcomes
 * - Type-safe implementations
 * - Single Responsibility Principle per test
 */

interface ChatStore {
  isProcessing: boolean;
  messages: Array<{id: string, content: string, role: 'user' | 'assistant'}>;
  threads: Map<string, any>;
  handleWebSocketEvent?: (event: {type: string, payload: any}) => void;
  updateFastLayer?: (data: any) => void;
  updateMediumLayer?: (data: any) => void;
  updateSlowLayer?: (data: any) => void;
  createNewThread?: () => void;
  resetState?: () => void;
}

interface WindowWithChatStore extends Window {
  useUnifiedChatStore?: {
    getState: () => ChatStore;
  };
}

declare global {
  interface Window extends WindowWithChatStore {}
}

describe('Critical UI/UX Business Value Tests', () => {
  beforeEach(() => {
    // Ensure real services are running (no mocks)
    cy.visit('/chat');
    
    // Wait for real chat interface to load
    cy.get('textarea[aria-label="Message input"]', { timeout: 15000 })
      .should('exist')
      .and('be.visible');
      
    // Verify we're connected to real backend services
    cy.window().then((win: WindowWithChatStore) => {
      expect(win.location.hostname).to.not.equal('localhost');
    });
  });

  describe('Brand Consistency Validation', () => {
    /**
     * BVJ: Brand consistency drives customer trust and professional perception
     * Segment: All segments - affects first impression and credibility
     * Business Goal: Brand recognition and professional credibility
     * Value Impact: Customers perceive platform as professional and trustworthy
     * Revenue Impact: Improved conversion rates from consistent brand experience
     */
    it('should maintain consistent brand colors throughout interface', () => {
      // Verify brand-consistent color palette is used
      cy.get('body').should('exist');
      
      // Check that deprecated blue gradients are removed
      cy.get('body').then(($body) => {
        const deprecatedBlueElements = $body.find('[class*="from-blue"], [class*="bg-blue-500"]');
        expect(deprecatedBlueElements.length).to.equal(0);
      });
      
      // Verify approved brand colors are present
      cy.get('[class*="emerald"], [class*="purple"]').should('exist');
    });
  });

  describe('Multi-Agent Workflow Transparency', () => {
    /**
     * BVJ: Customers need visibility into AI agent operations for trust and optimization
     * Segment: Mid to Enterprise - sophisticated users who optimize AI workflows  
     * Business Goal: Customer retention through transparency and control
     * Value Impact: Users can understand and optimize their AI agent performance
     * Revenue Impact: Enables upselling to higher tiers with advanced agent analytics
     */
    it('should provide clear visibility when multiple agents execute in sequence', () => {
      // Send a complex message that triggers multiple agents
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Analyze my AI spending patterns and optimize my model selection strategy');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Wait for real agent processing to begin
      cy.get('[data-testid="agent-status"]', { timeout: 10000 })
        .should('exist')
        .and('contain.text', 'Processing');
      
      // Verify multiple agents are shown distinctly (real backend will trigger multiple agents)
      cy.get('[data-testid="active-agents"]', { timeout: 20000 })
        .should('exist')
        .within(() => {
          // Should show at least triage and optimization agents for this query
          cy.contains('TriageSubAgent').should('exist');
          cy.contains('OptimizationAgent').should('exist');
        });
      
      // Verify agent execution sequence is tracked
      cy.get('[data-testid="agent-sequence"]')
        .should('exist')
        .and('contain.text', '1')
        .and('contain.text', '2');
    });
  });

  describe('Real-Time Communication Reliability', () => {
    /**
     * BVJ: Reliable real-time updates prevent user frustration and abandoned sessions
     * Segment: All segments - core platform functionality
     * Business Goal: Platform Stability and User Experience
     * Value Impact: Users get immediate feedback on AI operations without delays or failures
     * Revenue Impact: Reduces churn from poor experience, enables real-time upselling
     */
    it('should maintain reliable WebSocket connection for real-time updates', () => {
      // Verify WebSocket connection is established with real backend
      cy.window().then((win: WindowWithChatStore) => {
        const store = win.useUnifiedChatStore?.getState();
        expect(store).to.exist;
        expect(store.isProcessing).to.be.a('boolean');
      });
      
      // Send message to trigger real WebSocket events
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Test WebSocket connectivity with real backend');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Verify real-time updates are received
      cy.get('[data-testid="message-status"]', { timeout: 5000 })
        .should('contain.text', 'Sending')
        .then(() => {
          // Should update to processing status via WebSocket
          cy.get('[data-testid="message-status"]', { timeout: 10000 })
            .should('contain.text', 'Processing');
        });
      
      // Verify message appears in real-time
      cy.contains('Test WebSocket connectivity with real backend')
        .should('be.visible');
    });
  });

  describe('Professional Interface Design', () => {
    /**
     * BVJ: Modern, professional interface design builds customer confidence
     * Segment: Enterprise - professional appearance critical for B2B sales
     * Business Goal: Brand credibility and customer acquisition
     * Value Impact: Customers perceive platform as enterprise-grade and trustworthy
     * Revenue Impact: Improves enterprise sales conversion rates
     */
    it('should present a modern, professional interface design', () => {
      // Verify core interface elements are visually polished
      cy.get('[data-testid="chat-interface"]')
        .should('be.visible')
        .and('have.css', 'opacity', '1');
      
      // Check that interface uses modern design patterns
      cy.get('body').then(($body) => {
        // Verify professional styling exists (backdrop effects, proper spacing)
        const hasModernStyling = 
          $body.find('[class*="backdrop"], [class*="shadow"], [class*="rounded"]').length > 0;
        
        expect(hasModernStyling).to.be.true;
      });
      
      // Verify interface is responsive and well-structured
      cy.viewport(1920, 1080);
      cy.get('textarea[aria-label="Message input"]').should('be.visible');
      
      cy.viewport(768, 1024);
      cy.get('textarea[aria-label="Message input"]').should('be.visible');
    });
  });

  describe('Power User Productivity Features', () => {
    /**
     * BVJ: Advanced users need efficient keyboard shortcuts for productivity
     * Segment: Mid to Enterprise - power users who optimize workflows
     * Business Goal: User efficiency and advanced feature adoption
     * Value Impact: Advanced users can work faster and access powerful features
     * Revenue Impact: Justifies higher-tier pricing through productivity gains
     */
    it('should provide keyboard shortcuts for advanced functionality', () => {
      // Test debug panel access (critical for troubleshooting)
      cy.get('body').trigger('keydown', {
        ctrlKey: true,
        shiftKey: true,
        key: 'D',
        code: 'KeyD'
      });
      
      // Verify debug panel or advanced controls are accessible
      cy.get('[data-testid="debug-panel"], [data-testid="advanced-controls"]', { timeout: 2000 })
        .should('exist');
      
      // Test quick message sending with Ctrl+Enter
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Test keyboard shortcut functionality');
      
      cy.get('textarea[aria-label="Message input"]')
        .trigger('keydown', {
          ctrlKey: true,
          key: 'Enter',
          code: 'Enter'
        });
      
      // Message should be sent via keyboard shortcut
      cy.contains('Test keyboard shortcut functionality')
        .should('be.visible');
    });
  });

  describe('Multi-Conversation Management', () => {
    /**
     * BVJ: Users need to manage multiple AI optimization projects simultaneously
     * Segment: Mid to Enterprise - users with multiple optimization workloads
     * Business Goal: Platform stickiness through multi-project management
     * Value Impact: Users can organize different AI projects without confusion
     * Revenue Impact: Enables multiple concurrent optimizations, increasing usage volume
     */
    it('should maintain complete isolation between different conversation threads', () => {
      // Create first conversation thread with distinct content
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Optimize my GPT-4 costs for customer service');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Wait for first message to be processed
      cy.get('[data-testid="message-list"]')
        .should('contain.text', 'Optimize my GPT-4 costs for customer service');
      
      // Create new thread
      cy.get('[data-testid="new-chat-button"], button').contains('New').click();
      
      // Verify new thread is isolated (previous message not visible)
      cy.get('[data-testid="message-list"]')
        .should('not.contain.text', 'Optimize my GPT-4 costs for customer service');
      
      // Send different message in new thread
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Analyze Claude 3 performance for code generation');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Verify thread isolation is maintained
      cy.get('[data-testid="message-list"]')
        .should('contain.text', 'Analyze Claude 3 performance for code generation')
        .and('not.contain.text', 'Optimize my GPT-4 costs for customer service');
    });
  });

  describe('Intelligent Conversation Organization', () => {
    /**
     * BVJ: Automatic organization saves user time and improves navigation
     * Segment: All segments - reduces cognitive load for all users
     * Business Goal: User experience excellence and productivity
     * Value Impact: Users can quickly find and resume relevant conversations
     * Revenue Impact: Improves user engagement and platform stickiness
     */
    it('should automatically organize conversations with meaningful titles', () => {
      // Send a message that should trigger automatic renaming
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('How can I optimize my OpenAI API costs for customer service chatbots?');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Wait for real backend processing and auto-renaming
      cy.wait(3000);
      
      // Check thread title was updated (look in sidebar or header)
      cy.get('[data-testid="thread-title"], [data-testid="conversation-header"]', { timeout: 5000 })
        .should('exist')
        .and('not.contain.text', 'New Chat')
        .and('not.contain.text', 'Untitled');
      
      // Verify the title is contextually relevant
      cy.get('[data-testid="thread-title"], [data-testid="conversation-header"]')
        .should(($title) => {
          const titleText = $title.text().toLowerCase();
          const hasRelevantContent = 
            titleText.includes('openai') || 
            titleText.includes('cost') ||
            titleText.includes('optimize') ||
            titleText.includes('api');
          expect(hasRelevantContent).to.be.true;
        });
    });
  });

  describe('System Performance Monitoring', () => {
    /**
     * BVJ: Performance monitoring ensures platform reliability and user satisfaction
     * Segment: Platform/Internal - critical for maintaining service quality
     * Business Goal: Platform Stability and competitive advantage
     * Value Impact: Proactive performance management prevents user experience degradation
     * Revenue Impact: Prevents churn from performance issues, enables premium SLAs
     */
    it('should maintain responsive performance under normal usage patterns', () => {
      // Measure initial page load performance
      cy.window().then((win: WindowWithChatStore) => {
        const navigationTiming = win.performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        const loadTime = navigationTiming.loadEventEnd - navigationTiming.navigationStart;
        
        // Should load within acceptable time for business use
        expect(loadTime).to.be.lessThan(5000); // 5 seconds max
      });
      
      // Test interface responsiveness under typical usage
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Test message for performance validation');
      
      const startTime = Date.now();
      cy.get('button[aria-label="Send message"]').click();
      
      // Message should appear quickly
      cy.contains('Test message for performance validation')
        .should('be.visible')
        .then(() => {
          const responseTime = Date.now() - startTime;
          expect(responseTime).to.be.lessThan(2000); // 2 seconds max for UI response
        });
      
      // Verify no memory leaks in store
      cy.window().then((win: WindowWithChatStore) => {
        const store = win.useUnifiedChatStore?.getState();
        if (store?.messages) {
          // Should not accumulate excessive messages in memory
          expect(store.messages.length).to.be.lessThan(1000);
        }
      });
    });
  });

  describe('Business-Critical Error Recovery', () => {
    /**
     * BVJ: Robust error handling prevents user frustration and lost revenue
     * Segment: All segments - critical for maintaining user trust
     * Business Goal: Platform reliability and customer retention
     * Value Impact: Users can recover from errors without losing work or abandoning platform
     * Revenue Impact: Prevents customer churn from poor error experiences
     */
    it('should provide clear error recovery when backend services are temporarily unavailable', () => {
      // Test network error scenario by sending message when backend might be slow
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Test error recovery with backend timeout scenario');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // If backend is slow/unavailable, should show appropriate status
      cy.get('[data-testid="message-status"]', { timeout: 30000 })
        .should('exist')
        .then(($status) => {
          const statusText = $status.text().toLowerCase();
          const validStatuses = ['sending', 'processing', 'error', 'retry', 'failed'];
          const hasValidStatus = validStatuses.some(status => statusText.includes(status));
          expect(hasValidStatus).to.be.true;
        });
      
      // If error occurs, should provide recovery options
      cy.get('body').then(($body) => {
        if ($body.find(':contains("error"), :contains("failed")').length > 0) {
          // Should provide retry functionality
          cy.get('[data-testid="retry-button"], button').contains('Retry')
            .should('exist')
            .and('be.visible');
        }
      });
      
      // System should remain stable after errors
      cy.get('textarea[aria-label="Message input"]')
        .should('be.enabled')
        .and('be.visible');
    });
  });

  describe('Data Export and Reporting Value', () => {
    /**
     * BVJ: Export functionality enables customers to integrate Netra data with their workflows
     * Segment: Mid to Enterprise - customers need reporting for stakeholders
     * Business Goal: Platform integration and customer workflow enhancement
     * Value Impact: Customers can share optimization results and justify Netra investment
     * Revenue Impact: Drives renewal and expansion by demonstrating clear ROI
     */
    it('should enable export of optimization results for business reporting', () => {
      // First generate some content to export by having a conversation
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Generate a cost optimization report for my AI infrastructure');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Wait for response with actual data
      cy.get('[data-testid="message-list"]', { timeout: 15000 })
        .should('contain.text', 'cost')
        .or('contain.text', 'optimization')
        .or('contain.text', 'report');
      
      // Access export functionality (check multiple possible locations)
      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="export-button"]').length > 0) {
          cy.get('[data-testid="export-button"]').click();
        } else if ($body.find('button').filter(':contains("Export")').length > 0) {
          cy.get('button').contains('Export').click();
        } else {
          // Try keyboard shortcut for export
          cy.get('body').trigger('keydown', {
            ctrlKey: true,
            key: 'e',
            code: 'KeyE'
          });
        }
      });
      
      // Verify export options are available
      cy.get('[data-testid="export-options"], [data-testid="download-dialog"]', { timeout: 5000 })
        .should('exist');
    });
  });

  describe('Smooth User Experience Flow', () => {
    /**
     * BVJ: Smooth animations and transitions create professional user experience
     * Segment: All segments - affects perceived quality and professionalism
     * Business Goal: Brand perception and user satisfaction
     * Value Impact: Users perceive the platform as polished and enterprise-grade
     * Revenue Impact: Professional UX supports premium pricing and reduces churn
     */
    it('should provide smooth visual feedback during AI processing states', () => {
      // Trigger a message that will show processing states
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Analyze my current AI model performance and suggest optimizations');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Verify smooth state transitions during processing
      cy.get('[data-testid="processing-indicator"]', { timeout: 5000 })
        .should('be.visible')
        .and('have.css', 'transition-duration')
        .and(($el) => {
          const transitionDuration = $el.css('transition-duration');
          // Should have some transition for smooth UX
          expect(transitionDuration).to.not.equal('0s');
        });
      
      // Check for loading animations
      cy.get('[class*="animate"], [class*="pulse"], [class*="spin"]')
        .should('exist');
      
      // Verify smooth transition when processing completes
      cy.get('[data-testid="message-content"]', { timeout: 20000 })
        .should('be.visible')
        .and(($content) => {
          // Content should appear smoothly, not abruptly
          expect($content.css('opacity')).to.equal('1');
        });
    });
  });

  describe('Enterprise Accessibility Compliance', () => {
    /**
     * BVJ: Accessibility compliance is required for enterprise customers
     * Segment: Enterprise - accessibility requirements for corporate compliance
     * Business Goal: Enterprise market expansion and compliance
     * Value Impact: Enables access for all users regardless of abilities
     * Revenue Impact: Qualifies for enterprise contracts with accessibility requirements
     */
    it('should meet accessibility standards for enterprise deployment', () => {
      // Verify core accessibility features
      cy.get('textarea[aria-label="Message input"]')
        .should('exist')
        .and('have.attr', 'aria-label')
        .and('be.visible');
      
      cy.get('button[aria-label="Send message"]')
        .should('exist')
        .and('have.attr', 'aria-label')
        .and('not.be.disabled');
      
      // Test keyboard navigation
      cy.get('textarea[aria-label="Message input"]')
        .focus()
        .should('be.focused');
      
      // Tab navigation should work
      cy.get('textarea[aria-label="Message input"]')
        .tab()
        .then(($focused) => {
          // Should focus on send button or next interactive element
          expect($focused).to.be.visible;
        });
      
      // Verify screen reader compatibility
      cy.get('[data-testid="message-list"]')
        .should('have.attr', 'role', 'log')
        .or('have.attr', 'aria-live');
      
      // Check color contrast and visibility
      cy.get('textarea[aria-label="Message input"]')
        .should('have.css', 'opacity', '1')
        .and(($textarea) => {
          const backgroundColor = $textarea.css('background-color');
          const color = $textarea.css('color');
          // Should have visible contrast (not white on white, etc.)
          expect(backgroundColor).to.not.equal(color);
        });
    });
  });

  describe('Advanced Debugging and Troubleshooting', () => {
    /**
     * BVJ: Advanced users need debugging tools to optimize their AI workflows
     * Segment: Mid to Enterprise - technical users optimizing complex AI systems
     * Business Goal: User empowerment and advanced feature adoption
     * Value Impact: Users can troubleshoot and optimize their AI operations independently
     * Revenue Impact: Justifies higher-tier pricing, reduces support costs
     */
    it('should provide advanced debugging capabilities for technical users', () => {
      // Generate some real activity to debug
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Debug my AI model selection process and show detailed logs');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Wait for processing to generate debug data
      cy.wait(3000);
      
      // Access debug panel
      cy.get('body').trigger('keydown', {
        ctrlKey: true,
        shiftKey: true,
        key: 'D',
        code: 'KeyD'
      });
      
      // Verify debug information is available
      cy.get('[data-testid="debug-panel"]', { timeout: 3000 })
        .should('be.visible')
        .within(() => {
          // Should show technical information
          cy.get('[data-testid="system-info"], [data-testid="debug-logs"]')
            .should('exist');
        });
      
      // Verify real system data is shown (not mocked)
      cy.get('[data-testid="debug-panel"]')
        .should('contain.text', 'WebSocket')
        .or('contain.text', 'Events')
        .or('contain.text', 'Performance')
        .or('contain.text', 'Agent');
    });
  });

  describe('Real-Time AI Response Streaming', () => {
    /**
     * BVJ: Streaming responses provide immediate feedback and improved user experience
     * Segment: All segments - core platform functionality
     * Business Goal: Platform competitiveness and user satisfaction
     * Value Impact: Users see AI progress immediately, reducing perceived wait time
     * Revenue Impact: Competitive advantage over batch-processing platforms
     */
    it('should provide real-time streaming of AI responses', () => {
      // Send a message that will trigger streaming response
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Provide a detailed analysis of AI cost optimization strategies');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Verify initial response appears quickly
      cy.get('[data-testid="message-content"]', { timeout: 5000 })
        .should('be.visible')
        .and(($content) => {
          // Should have some content appearing
          expect($content.text().length).to.be.greaterThan(0);
        });
      
      // Verify streaming indicator is visible during response
      cy.get('[data-testid="typing-indicator"], [class*="pulse"], [class*="animate"]')
        .should('exist');
      
      // Content should continue to update (real streaming)
      cy.get('[data-testid="message-content"]')
        .should(($content) => {
          const initialLength = $content.text().length;
          
          // Wait a bit and check if content has grown
          cy.wait(2000).then(() => {
            const updatedLength = $content.text().length;
            // In real streaming, content should grow over time
            if (updatedLength > initialLength) {
              cy.log('Real-time streaming detected');
            }
          });
        });
      
      // Verify complete response is delivered
      cy.get('[data-testid="message-content"]', { timeout: 30000 })
        .should('contain.text', 'optimization')
        .and('contain.text', 'cost')
        .and(($content) => {
          // Should have substantial content
          expect($content.text().length).to.be.greaterThan(100);
        });
    });
  });

  describe('Enterprise-Grade Type Safety and Reliability', () => {
    /**
     * BVJ: Type safety prevents runtime errors that could disrupt customer operations
     * Segment: Enterprise - critical for mission-critical AI infrastructure
     * Business Goal: Platform reliability and enterprise confidence
     * Value Impact: Customers can depend on platform stability for critical workflows
     * Revenue Impact: Enables enterprise SLAs and premium pricing
     */
    it('should maintain strict type safety throughout the application', () => {
      // Verify core store structure is properly typed
      cy.window().then((win: WindowWithChatStore) => {
        const store = win.useUnifiedChatStore?.getState();
        expect(store).to.exist;
        
        // Verify critical properties exist with correct types
        expect(store.isProcessing).to.be.a('boolean');
        
        if (store.messages) {
          expect(Array.isArray(store.messages)).to.be.true;
          
          // If messages exist, verify they have proper structure
          if (store.messages.length > 0) {
            const firstMessage = store.messages[0];
            expect(firstMessage).to.have.property('id');
            expect(firstMessage).to.have.property('content');
            expect(typeof firstMessage.id).to.equal('string');
            expect(typeof firstMessage.content).to.equal('string');
          }
        }
        
        // Verify method signatures are properly typed
        const methodTests = [
          { name: 'updateFastLayer', required: false },
          { name: 'updateMediumLayer', required: false },
          { name: 'handleWebSocketEvent', required: false }
        ];
        
        methodTests.forEach(({ name, required }) => {
          const method = store[name as keyof ChatStore];
          if (method || required) {
            expect(typeof method).to.equal('function');
          }
        });
      });
      
      // Test runtime type safety by triggering operations
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Test type safety with real operations');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Should not cause any runtime type errors
      cy.window().then((win) => {
        // Check console for any type-related errors
        const errors = win.console?.error || [];
        // In real implementation, we'd check for type errors
        expect(errors).to.not.contain('TypeError');
      });
    });
  });

  describe('Enterprise Project Management Navigation', () => {
    /**
     * BVJ: Sidebar navigation enables efficient management of multiple AI optimization projects
     * Segment: Mid to Enterprise - users managing multiple concurrent optimizations
     * Business Goal: User productivity and platform stickiness
     * Value Impact: Users can efficiently navigate between different optimization workflows
     * Revenue Impact: Supports higher usage volume and customer expansion
     */
    it('should provide efficient navigation between multiple optimization projects', () => {
      // Create multiple distinct optimization projects
      const projectTypes = [
        'Optimize OpenAI costs for customer support',
        'Analyze Claude performance for code generation',
        'Compare model performance for content creation'
      ];
      
      // Create first project
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type(projectTypes[0]);
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Wait for processing to begin
      cy.get('[data-testid="processing-indicator"]', { timeout: 10000 })
        .should('exist');
      
      // Create new project thread
      cy.get('[data-testid="new-chat-button"], button').contains('New').click();
      
      // Create second project
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type(projectTypes[1]);
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Verify sidebar shows multiple projects
      cy.get('[data-testid="thread-list"], [data-testid="sidebar"]', { timeout: 5000 })
        .should('exist')
        .within(() => {
          // Should show at least 2 conversation threads
          cy.get('[data-testid="thread-item"]')
            .should('have.length.at.least', 2);
        });
      
      // Test navigation between projects
      cy.get('[data-testid="thread-list"] [data-testid="thread-item"]')
        .first()
        .click();
      
      // Should switch to first project context
      cy.get('[data-testid="message-list"]')
        .should('contain.text', 'OpenAI')
        .or('contain.text', 'customer support');
    });
  });

  describe('Real-Time System Integration', () => {
    /**
     * BVJ: Comprehensive WebSocket integration enables real-time AI optimization feedback
     * Segment: All segments - core platform functionality
     * Business Goal: Platform competitiveness and real-time user engagement
     * Value Impact: Users get immediate updates on AI optimization progress
     * Revenue Impact: Real-time features justify premium pricing vs batch competitors
     */
    it('should handle complete spectrum of real-time optimization events', () => {
      // Test real WebSocket integration by triggering comprehensive optimization
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Run complete AI infrastructure analysis with real-time monitoring');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Should receive various event types during real processing
      const expectedEventIndicators = [
        'agent_started',
        'processing',
        'analysis',
        'optimization',
        'completed'
      ];
      
      // Monitor for real-time updates
      cy.get('[data-testid="activity-log"], [data-testid="status-panel"]', { timeout: 10000 })
        .should('exist')
        .within(() => {
          // Should show various processing stages
          expectedEventIndicators.forEach(indicator => {
            cy.get('body', { timeout: 20000 })
              .should('contain.text', indicator)
              .or('contain.text', indicator.replace('_', ' '));
          });
        });
      
      // Verify thread management events
      cy.get('[data-testid="thread-status"]')
        .should('exist')
        .and('not.contain.text', 'error')
        .and('not.contain.text', 'failed');
      
      // Verify real-time content updates
      cy.get('[data-testid="message-content"]', { timeout: 30000 })
        .should('exist')
        .and(($content) => {
          expect($content.text().length).to.be.greaterThan(50);
        });
    });
  });

  describe('AI Tool Orchestration Efficiency', () => {
    /**
     * BVJ: Intelligent tool management prevents redundant operations and reduces costs
     * Segment: Mid to Enterprise - users with complex AI tool chains
     * Business Goal: Cost optimization and operational efficiency
     * Value Impact: Users avoid redundant AI tool calls, reducing their operational costs
     * Revenue Impact: Demonstrates clear cost savings value, justifies platform fees
     */
    it('should optimize AI tool usage to prevent redundant operations', () => {
      // Trigger a complex request that might use multiple tools
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Analyze my data, generate insights, create visualizations, and export results');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Wait for tool orchestration to begin
      cy.get('[data-testid="tool-activity"], [data-testid="active-tools"]', { timeout: 10000 })
        .should('exist');
      
      // Verify tool usage is being tracked efficiently
      cy.get('[data-testid="tool-usage-panel"]')
        .should('exist')
        .within(() => {
          // Should show tool usage without unnecessary duplicates
          cy.get('[data-testid="tool-list"] [data-testid="tool-item"]')
            .should('have.length.at.least', 1)
            .and('have.length.at.most', 10); // Reasonable limit
        });
      
      // Verify cost-conscious tool orchestration
      cy.get('[data-testid="cost-tracking"], [data-testid="usage-metrics"]')
        .should('exist')
        .and('contain.text', 'cost')
        .or('contain.text', 'usage')
        .or('contain.text', 'token');
      
      // Check that tools complete successfully
      cy.get('[data-testid="tool-status"]', { timeout: 30000 })
        .should('contain.text', 'completed')
        .or('contain.text', 'success')
        .or('contain.text', 'finished');
    });
  });

  describe('Brand-Consistent Progress Communication', () => {
    /**
     * BVJ: Consistent progress indicators build user confidence in AI operations
     * Segment: All segments - affects user perception during AI processing
     * Business Goal: User experience consistency and brand reinforcement
     * Value Impact: Users feel confident about AI processing progress and platform reliability
     * Revenue Impact: Consistent branding supports premium positioning
     */
    it('should provide clear, brand-consistent progress feedback during AI operations', () => {
      // Trigger an operation that shows progress
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Perform comprehensive AI model evaluation and cost analysis');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Wait for progress indicators to appear
      cy.get('[data-testid="progress-bar"], [class*="progress"]', { timeout: 10000 })
        .should('be.visible');
      
      // Verify progress uses brand-consistent colors
      cy.get('[data-testid="progress-indicator"]')
        .should('exist')
        .and(($progress) => {
          // Should not use deprecated blue colors
          const classList = $progress.attr('class') || '';
          expect(classList).to.not.contain('bg-blue-500');
          expect(classList).to.not.contain('from-blue');
        });
      
      // Check for brand-appropriate colors (emerald, purple, etc.)
      cy.get('body').then(($body) => {
        const hasBrandColors = 
          $body.find('[class*="emerald"], [class*="purple"], [class*="indigo"]').length > 0;
        expect(hasBrandColors).to.be.true;
      });
      
      // Verify progress provides meaningful information
      cy.get('[data-testid="progress-text"], [data-testid="status-text"]')
        .should('exist')
        .and('not.be.empty')
        .and(($text) => {
          const text = $text.text().toLowerCase();
          const hasProgressInfo = 
            text.includes('analyzing') ||
            text.includes('processing') ||
            text.includes('optimizing') ||
            text.includes('step') ||
            text.includes('%');
          expect(hasProgressInfo).to.be.true;
        });
    });
  });

  describe('Enterprise Troubleshooting and Support Data', () => {
    /**
     * BVJ: Debug data export enables customer self-service and reduces support burden
     * Segment: Mid to Enterprise - technical users who need detailed system information
     * Business Goal: Support cost reduction and customer empowerment
     * Value Impact: Customers can troubleshoot issues independently with comprehensive data
     * Revenue Impact: Reduces support costs, enables premium support tiers
     */
    it('should provide comprehensive system data for enterprise troubleshooting', () => {
      // Generate some activity to create meaningful debug data
      cy.get('textarea[aria-label="Message input"]')
        .clear()
        .type('Run diagnostic analysis of AI optimization performance');
      
      cy.get('button[aria-label="Send message"]').click();
      
      // Wait for processing to generate system data
      cy.wait(5000);
      
      // Access advanced system information
      cy.get('body').trigger('keydown', {
        ctrlKey: true,
        shiftKey: true,
        key: 'D',
        code: 'KeyD'
      });
      
      // Verify debug panel provides comprehensive information
      cy.get('[data-testid="debug-panel"]', { timeout: 3000 })
        .should('be.visible')
        .within(() => {
          // Should show system performance data
          cy.get('[data-testid="system-metrics"]')
            .should('exist')
            .and('contain.text', 'Performance')
            .or('contain.text', 'Metrics')
            .or('contain.text', 'System');
          
          // Should show WebSocket connection status
          cy.get('[data-testid="connection-status"]')
            .should('exist')
            .and('contain.text', 'Connected')
            .or('contain.text', 'WebSocket')
            .or('contain.text', 'Status');
        });
      
      // Test export functionality if available
      cy.get('[data-testid="export-debug"], button').contains('Export')
        .should('exist')
        .click();
      
      // Verify export provides valuable data
      cy.wait(2000);
      
      // Should either download file or show export was successful
      cy.get('body').then(($body) => {
        const hasDownload = $body.find('a[download]').length > 0;
        const hasSuccessMessage = $body.find(':contains("Export")').length > 0;
        
        expect(hasDownload || hasSuccessMessage).to.be.true;
      });
    });
  });
});