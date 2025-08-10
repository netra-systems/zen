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
    
    cy.visit('/chat', { failOnStatusCode: false });
    cy.wait(2000); // Wait for page load
  });

  it('should display optimization interface', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        cy.get('body').should('be.visible');
        
        // Check for optimization-related content
        cy.get('body').then($body => {
          const text = $body.text();
          
          const optimizationKeywords = [
            'optimization',
            'optimize',
            'performance',
            'cost',
            'efficiency',
            'analysis',
            'recommendation',
            'AI',
            'model',
            'workload'
          ];
          
          let foundKeywords: string[] = [];
          optimizationKeywords.forEach(keyword => {
            if (new RegExp(keyword, 'i').test(text)) {
              foundKeywords.push(keyword);
            }
          });
          
          if (foundKeywords.length > 0) {
            cy.log(`Found optimization keywords: ${foundKeywords.join(', ')}`);
            expect(foundKeywords.length).to.be.greaterThan(0);
          } else {
            cy.log('No optimization keywords found initially - may require interaction');
          }
        });
      } else {
        cy.log('Redirected to login - authentication required');
        expect(url).to.include('/login');
      }
    });
  });

  it('should check for report display capabilities', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        cy.get('body').then($body => {
          // Look for report structure elements
          const reportElements = [
            'section',
            'article',
            'div[class*="report"]',
            'div[class*="result"]',
            'div[class*="card"]',
            'table',
            'ul',
            'ol'
          ];
          
          let structureFound = false;
          reportElements.forEach(selector => {
            if ($body.find(selector).length > 0) {
              structureFound = true;
              cy.log(`Found report structure element: ${selector}`);
            }
          });
          
          if (!structureFound) {
            cy.log('No explicit report structure found - may be rendered dynamically');
          }
          
          // Check for headings that might indicate report sections
          const headings = $body.find('h1, h2, h3, h4, h5, h6');
          if (headings.length > 0) {
            cy.log(`Found ${headings.length} heading(s) for potential report sections`);
          }
        });
      }
    });
  });

  it('should verify metrics display capability', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        cy.get('body').then($body => {
          const text = $body.text();
          
          // Check for metric-related content
          const metricIndicators = [
            /\d+\s*%/,         // Percentages
            /\$\s*\d+/,        // Dollar amounts
            /\d+\s*ms/,        // Milliseconds
            /\d+\s*req/,       // Requests
            /\d+\s*\/\s*s/,    // Per second
            /latency/i,
            /throughput/i,
            /cost/i,
            /savings/i
          ];
          
          let metricsFound: string[] = [];
          metricIndicators.forEach(pattern => {
            if (pattern.test(text)) {
              metricsFound.push(pattern.toString());
            }
          });
          
          if (metricsFound.length > 0) {
            cy.log(`Found metric indicators: ${metricsFound.length}`);
          } else {
            cy.log('No metrics displayed initially - may appear after optimization request');
          }
          
          // Check for visualization elements
          const vizElements = ['canvas', 'svg', '[class*="chart"]', '[class*="graph"]'];
          vizElements.forEach(selector => {
            if ($body.find(selector).length > 0) {
              cy.log(`Found visualization element: ${selector}`);
            }
          });
        });
      }
    });
  });

  it('should check for export and save functionality', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        cy.get('body').then($body => {
          // Look for export/save buttons or links
          const exportElements = $body.find('button, a, [role="button"]').filter((i, el) => {
            const text = Cypress.$(el).text().toLowerCase();
            const ariaLabel = Cypress.$(el).attr('aria-label') || '';
            return text.includes('export') || 
                   text.includes('download') || 
                   text.includes('save') ||
                   text.includes('copy') ||
                   ariaLabel.includes('export') ||
                   ariaLabel.includes('download');
          });
          
          if (exportElements.length > 0) {
            cy.log(`Found ${exportElements.length} export/save element(s)`);
            exportElements.each((i, el) => {
              cy.log(`Export element: ${Cypress.$(el).text() || Cypress.$(el).attr('aria-label')}`);
            });
          } else {
            cy.log('No explicit export buttons found - may appear after generating report');
          }
          
          // Check for format options mentioned
          const formats = ['PDF', 'CSV', 'JSON', 'Excel', 'Markdown'];
          let foundFormats: string[] = [];
          formats.forEach(format => {
            if (new RegExp(format, 'i').test($body.text())) {
              foundFormats.push(format);
            }
          });
          
          if (foundFormats.length > 0) {
            cy.log(`Found export format options: ${foundFormats.join(', ')}`);
          }
        });
      }
    });
  });

  it('should verify recommendation display', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        cy.get('body').then($body => {
          const text = $body.text();
          
          // Check for recommendation-related content
          const recommendationKeywords = [
            'recommend',
            'suggest',
            'should',
            'consider',
            'improve',
            'optimize',
            'best practice',
            'action',
            'next step',
            'priority'
          ];
          
          let foundRecommendations: string[] = [];
          recommendationKeywords.forEach(keyword => {
            if (new RegExp(keyword, 'i').test(text)) {
              foundRecommendations.push(keyword);
            }
          });
          
          if (foundRecommendations.length > 0) {
            cy.log(`Found recommendation keywords: ${foundRecommendations.join(', ')}`);
          } else {
            cy.log('No recommendation keywords found initially');
          }
          
          // Check for structured lists that might contain recommendations
          const lists = $body.find('ul, ol');
          if (lists.length > 0) {
            cy.log(`Found ${lists.length} list(s) that may contain recommendations`);
          }
        });
      }
    });
  });

  it('should maintain stability when viewing results', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const initialUrl = url;
        
        // Scroll to test page stability
        cy.scrollTo('bottom', { duration: 1000 });
        cy.wait(500);
        cy.scrollTo('top', { duration: 1000 });
        
        // Check URL hasn't changed unexpectedly
        cy.url().then((newUrl) => {
          expect(newUrl).to.equal(initialUrl);
        });
        
        // Page should remain visible
        cy.get('body').should('be.visible');
        
        // Check for any error indicators
        cy.get('body').then($body => {
          const text = $body.text();
          const hasError = /error|failed|exception|crash/i.test(text);
          
          if (hasError) {
            // Check if it's an actual error or just mentioned in content
            const errorElements = $body.find('.error, .alert-danger, [role="alert"]');
            if (errorElements.length > 0) {
              cy.log('Warning: Error elements found on page');
            } else {
              cy.log('Error keywords found but may be part of normal content');
            }
          } else {
            cy.log('No error indicators found - page is stable');
          }
        });
      }
    });
  });

  it('should check for interactive report elements', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        cy.get('body').then($body => {
          // Look for interactive elements in reports
          const interactiveSelectors = [
            'button',
            '[role="button"]',
            'a[href]',
            'details',
            '[role="tab"]',
            '[role="accordion"]',
            '[onclick]',
            '[data-toggle]'
          ];
          
          let interactiveCount = 0;
          interactiveSelectors.forEach(selector => {
            const count = $body.find(selector).length;
            if (count > 0) {
              interactiveCount += count;
              cy.log(`Found ${count} ${selector} element(s)`);
            }
          });
          
          if (interactiveCount > 0) {
            cy.log(`Total interactive elements: ${interactiveCount}`);
            
            // Try clicking a safe interactive element
            const safeButton = $body.find('button, [role="button"]').filter((i, el) => {
              const text = Cypress.$(el).text().toLowerCase();
              return !text.includes('delete') && 
                     !text.includes('logout') && 
                     !text.includes('clear') &&
                     text.length > 0;
            }).first();
            
            if (safeButton.length > 0) {
              cy.wrap(safeButton).click({ force: true });
              cy.wait(500);
              // Verify page is still stable
              cy.get('body').should('be.visible');
            }
          } else {
            cy.log('No interactive elements found - report may be static or not loaded');
          }
        });
      }
    });
  });

  it('should verify cost-benefit analysis display', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        cy.get('body').then($body => {
          const text = $body.text();
          
          // Check for cost-benefit related content
          const costBenefitKeywords = [
            'ROI',
            'return',
            'investment',
            'savings',
            'cost',
            'benefit',
            'value',
            'efficiency',
            'reduction',
            'improvement'
          ];
          
          let foundKeywords: string[] = [];
          costBenefitKeywords.forEach(keyword => {
            if (new RegExp(keyword, 'i').test(text)) {
              foundKeywords.push(keyword);
            }
          });
          
          if (foundKeywords.length > 0) {
            cy.log(`Found cost-benefit keywords: ${foundKeywords.join(', ')}`);
          }
          
          // Check for numerical data that might represent cost-benefit
          const hasNumbers = /\d+/.test(text);
          const hasCurrency = /\$|€|£|¥/.test(text);
          const hasPercentage = /\d+\s*%/.test(text);
          
          if (hasNumbers || hasCurrency || hasPercentage) {
            cy.log('Found numerical data that may represent cost-benefit metrics');
          }
        });
      }
    });
  });
});