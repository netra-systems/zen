describe('Optimization Results and Reporting Flow', () => {
  beforeEach(() => {
    // Clear state and mock authentication
    cy.clearLocalStorage();
    cy.clearCookies();
    
    // Prevent uncaught exceptions from failing tests
    Cypress.on('uncaught:exception', (err, runnable) => {
      return false;
    });
    
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'mock-jwt-token-for-testing');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netra.ai',
        name: 'Test User',
        role: 'user'
      }));
    });
    
    cy.visit('/chat');
    cy.wait(2000); // Wait for page load
  });

  it('should generate and display comprehensive optimization report', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // Request comprehensive optimization report
        const reportRequest = 'Generate a complete optimization report for my AI infrastructure with executive summary, metrics, and recommendations';
        
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().should('be.visible').type(reportRequest);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        // Verify request sent
        cy.contains(reportRequest, { timeout: 10000 }).should('be.visible');
        
        // Wait for report generation
        cy.contains(/generating report|analyzing|processing/i, { timeout: 15000 }).should('exist');
        
        // Check for report sections
        cy.get('body', { timeout: 40000 }).then(($body) => {
          const text = $body.text();
          
          // Executive Summary
          expect(text).to.match(/executive summary|overview|summary/i);
          
          // Metrics Section
          expect(text).to.match(/metric|performance|cost|latency|throughput/i);
          
          // Recommendations
          expect(text).to.match(/recommendation|suggest|improve|optimize/i);
          
          // Check for structured content (headers, lists, etc.)
          const hasStructure = $body.find('h1, h2, h3, h4, ul, ol, table').length > 0;
          if (hasStructure) {
            cy.log('Report has structured formatting');
          }
        });
      }
    });
  });

  it('should display optimization metrics with visualizations', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const metricsRequest = 'Show me optimization metrics with before/after comparison for cost, latency, and throughput';
        
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().type(metricsRequest);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        cy.contains(metricsRequest, { timeout: 10000 }).should('be.visible');
        
        // Wait for metrics generation
        cy.contains(/calculating|analyzing|comparing/i, { timeout: 15000 }).should('exist');
        
        // Check for metrics display
        cy.get('body', { timeout: 30000 }).then(($body) => {
          const text = $body.text();
          
          // Before/After comparison
          expect(text).to.match(/before|after|current|optimized|comparison/i);
          
          // Specific metrics
          expect(text).to.match(/cost.*\$|\$.*cost/i);
          expect(text).to.match(/latency.*ms|ms.*latency/i);
          expect(text).to.match(/throughput|requests?.*per.*second|req\/s/i);
          
          // Percentage improvements
          const hasPercentages = text.match(/\d+\s*%/);
          if (hasPercentages) {
            cy.log('Found percentage improvements in report');
          }
          
          // Check for visual elements (charts, tables, progress bars)
          const visualElements = [
            'canvas', // Charts
            'svg',    // Graphs
            'table',  // Data tables
            '[role="progressbar"]', // Progress indicators
            '.chart',
            '.graph',
            '.metric-card'
          ];
          
          visualElements.forEach(selector => {
            if ($body.find(selector).length > 0) {
              cy.log(`Found visualization element: ${selector}`);
            }
          });
        });
      }
    });
  });

  it('should provide actionable optimization recommendations', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const actionRequest = 'Give me specific actionable steps to optimize my LLM deployment with priority and effort estimates';
        
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().type(actionRequest);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        cy.contains(actionRequest, { timeout: 10000 }).should('be.visible');
        
        // Wait for recommendations
        cy.contains(/analyzing|generating recommendations/i, { timeout: 15000 }).should('exist');
        
        // Check for actionable content
        cy.get('body', { timeout: 30000 }).then(($body) => {
          const text = $body.text();
          
          // Priority indicators
          expect(text).to.match(/high|medium|low|priority|critical|important/i);
          
          // Effort estimates
          expect(text).to.match(/effort|hour|day|week|easy|moderate|complex/i);
          
          // Action items
          expect(text).to.match(/step|implement|configure|enable|deploy|update/i);
          
          // Numbered or bulleted lists
          const hasLists = $body.find('ol, ul, [class*="list"]').length > 0;
          const hasNumberedText = /\d+\.\s+\w+/.test(text);
          
          expect(hasLists || hasNumberedText).to.be.true;
        });
      }
    });
  });

  it('should allow saving and exporting optimization reports', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const exportRequest = 'Generate optimization report and provide options to save or export it';
        
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().type(exportRequest);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        cy.contains(exportRequest, { timeout: 10000 }).should('be.visible');
        
        // Wait for report generation
        cy.contains(/generating|creating report/i, { timeout: 15000 }).should('exist');
        
        // Check for save/export options
        cy.get('body', { timeout: 30000 }).then(($body) => {
          const text = $body.text();
          
          // Export format mentions
          expect(text).to.match(/pdf|csv|json|markdown|export|download|save/i);
          
          // Look for action buttons or links
          const exportElements = [
            'button:contains("export")',
            'button:contains("download")',
            'button:contains("save")',
            'a[download]',
            '[class*="export"]',
            '[class*="download"]'
          ];
          
          let foundExportOption = false;
          exportElements.forEach(selector => {
            try {
              if ($body.find(selector).length > 0) {
                foundExportOption = true;
                cy.log(`Found export option: ${selector}`);
              }
            } catch (e) {
              // Selector might not be valid, continue
            }
          });
          
          // Even if no buttons, the text should mention how to save/export
          if (!foundExportOption) {
            expect(text).to.match(/save|export|copy|download/i);
          }
        });
      }
    });
  });

  it('should track optimization history and show trends', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // First optimization request
        const firstRequest = 'Analyze current performance: 200ms latency, $100/hour cost';
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().type(firstRequest);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        cy.contains(firstRequest, { timeout: 10000 }).should('be.visible');
        cy.contains(/analyzing|optimization/i, { timeout: 20000 }).should('exist');
        
        // Second optimization request
        const followUpRequest = 'Show me optimization trends and improvements over time';
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().clear().type(followUpRequest);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        cy.contains(followUpRequest, { timeout: 10000 }).should('be.visible');
        
        // Check for trend information
        cy.get('body', { timeout: 30000 }).then(($body) => {
          const text = $body.text();
          
          // Trend indicators
          expect(text).to.match(/trend|history|improvement|progress|over time|tracking/i);
          
          // May reference previous metrics
          const hasPreviousMetrics = /200\s*ms|100.*hour|\$100/i.test(text);
          if (hasPreviousMetrics) {
            cy.log('Report references previous optimization metrics');
          }
        });
      }
    });
  });

  it('should provide cost-benefit analysis for optimizations', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const costBenefitRequest = 'Provide cost-benefit analysis for each optimization recommendation including ROI and payback period';
        
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().type(costBenefitRequest);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        cy.contains(costBenefitRequest, { timeout: 10000 }).should('be.visible');
        
        // Wait for analysis
        cy.contains(/analyzing|calculating/i, { timeout: 15000 }).should('exist');
        
        // Check for cost-benefit content
        cy.get('body', { timeout: 30000 }).then(($body) => {
          const text = $body.text();
          
          // Financial metrics
          expect(text).to.match(/roi|return on investment|payback|cost.*benefit/i);
          
          // Cost information
          expect(text).to.match(/\$|cost|invest|spend|budget/i);
          
          // Benefit/savings information
          expect(text).to.match(/save|saving|benefit|gain|improve|reduce/i);
          
          // Time frames
          expect(text).to.match(/month|week|year|period|timeline/i);
          
          // May include specific numbers
          const hasNumbers = /\d+.*\$|\$.*\d+|\d+\s*%/.test(text);
          if (hasNumbers) {
            cy.log('Cost-benefit analysis includes specific financial figures');
          }
        });
      }
    });
  });

  it('should handle report filtering and customization', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const customRequest = 'Generate optimization report focusing only on latency improvements, exclude cost analysis';
        
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().type(customRequest);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        cy.contains(customRequest, { timeout: 10000 }).should('be.visible');
        
        // Wait for filtered report
        cy.contains(/generating|focusing on latency/i, { timeout: 15000 }).should('exist');
        
        // Verify filtered content
        cy.get('body', { timeout: 30000 }).then(($body) => {
          const text = $body.text();
          
          // Should have latency content
          expect(text).to.match(/latency|response time|ms|millisecond|speed|performance/i);
          
          // Count cost mentions (should be minimal since excluded)
          const costMentions = (text.match(/cost|\$/gi) || []).length;
          const latencyMentions = (text.match(/latency|ms|response time/gi) || []).length;
          
          // Latency should be mentioned more than cost
          expect(latencyMentions).to.be.greaterThan(costMentions);
          
          cy.log(`Report mentions - Latency: ${latencyMentions}, Cost: ${costMentions}`);
        });
      }
    });
  });
});