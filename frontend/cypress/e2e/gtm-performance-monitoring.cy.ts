/// <reference types="cypress" />

interface PerformanceMetrics {
  loadTime: number;
  firstContentfulPaint: number;
  largestContentfulPaint: number;
  cumulativeLayoutShift: number;
  firstInputDelay: number;
  memoryUsage: number;
}

describe('GTM Performance Monitoring E2E Tests', () => {
  let performanceMetrics: PerformanceMetrics;
  let gtmDataLayer: any[] = [];

  beforeEach(() => {
    gtmDataLayer = [];
    performanceMetrics = {
      loadTime: 0,
      firstContentfulPaint: 0,
      largestContentfulPaint: 0,
      cumulativeLayoutShift: 0,
      firstInputDelay: 0,
      memoryUsage: 0
    };

    cy.visit('/', {
      onBeforeLoad: (win) => {
        // Initialize performance monitoring
        win.dataLayer = gtmDataLayer;
        
        // Mock performance observer for Core Web Vitals
        const originalObserver = win.PerformanceObserver;
        win.PerformanceObserver = class MockPerformanceObserver {
          constructor(callback: PerformanceObserverCallback) {
            // Simulate performance entries
            setTimeout(() => {
              const mockEntries = [
                {
                  name: 'first-contentful-paint',
                  startTime: 800,
                  entryType: 'paint'
                },
                {
                  name: 'largest-contentful-paint', 
                  startTime: 1200,
                  entryType: 'largest-contentful-paint'
                }
              ] as PerformanceEntry[];
              
              callback({ getEntries: () => mockEntries } as any, this as any);
            }, 100);
          }
          observe() {}
          disconnect() {}
          static supportedEntryTypes = ['paint', 'largest-contentful-paint', 'layout-shift', 'first-input'];
        };

        // Mock memory API
        Object.defineProperty(win.performance, 'memory', {
          value: {
            get usedJSHeapSize() { return Math.random() * 50000000; },
            get totalJSHeapSize() { return Math.random() * 100000000; },
            get jsHeapSizeLimit() { return 2147483648; }
          }
        });

        // Override dataLayer.push to capture performance events
        const originalPush = win.dataLayer.push;
        win.dataLayer.push = function(...args) {
          gtmDataLayer.push(...args);
          
          // Extract performance data if present
          args.forEach(event => {
            if (event.event === 'web_vitals') {
              if (event.metric_name === 'FCP') performanceMetrics.firstContentfulPaint = event.value;
              if (event.metric_name === 'LCP') performanceMetrics.largestContentfulPaint = event.value;
              if (event.metric_name === 'CLS') performanceMetrics.cumulativeLayoutShift = event.value;
              if (event.metric_name === 'FID') performanceMetrics.firstInputDelay = event.value;
            }
            if (event.event === 'performance_timing') {
              performanceMetrics.loadTime = event.load_time || 0;
              performanceMetrics.memoryUsage = event.memory_usage || 0;
            }
          });
          
          return originalPush.apply(this, args);
        };
      }
    });

    // Wait for app and GTM to load
    cy.get('[data-testid="app-container"]').should('be.visible');
    cy.window().should('have.property', 'dataLayer');
  });

  describe('Core Web Vitals Tracking', () => {
    it('should track First Contentful Paint (FCP) metrics', () => {
      // Trigger FCP measurement
      cy.get('[data-testid="main-content"]').should('be.visible');
      
      // Wait for performance metrics to be collected
      cy.wait(2000);
      
      // Check if FCP event was tracked
      cy.window().then((win) => {
        const fcpEvent = win.dataLayer.find((item: any) => 
          item.event === 'web_vitals' && item.metric_name === 'FCP'
        );
        
        if (fcpEvent) {
          expect(fcpEvent).to.exist;
          expect(fcpEvent.value).to.be.a('number');
          expect(fcpEvent.value).to.be.greaterThan(0);
          expect(fcpEvent.metric_name).to.equal('FCP');
          expect(fcpEvent.page_path).to.equal('/');
          
          // FCP should be under 2.5s for good performance
          expect(fcpEvent.value).to.be.lessThan(2500);
        }
      });
    });

    it('should track Largest Contentful Paint (LCP) metrics', () => {
      // Navigate to content-heavy page
      cy.visit('/features');
      cy.get('[data-testid="features-hero"]').should('be.visible');
      
      // Wait for LCP measurement
      cy.wait(3000);
      
      cy.window().then((win) => {
        const lcpEvent = win.dataLayer.find((item: any) => 
          item.event === 'web_vitals' && item.metric_name === 'LCP'
        );
        
        if (lcpEvent) {
          expect(lcpEvent).to.exist;
          expect(lcpEvent.value).to.be.a('number');
          expect(lcpEvent.value).to.be.greaterThan(0);
          expect(lcpEvent.metric_name).to.equal('LCP');
          
          // LCP should be under 2.5s for good performance
          expect(lcpEvent.value).to.be.lessThan(2500);
          
          // Should include element information
          expect(lcpEvent.element).to.exist;
        }
      });
    });

    it('should track Cumulative Layout Shift (CLS) metrics', () => {
      // Navigate to page that might have layout shifts
      cy.visit('/dashboard');
      
      // Simulate layout shifts by interacting with dynamic content
      cy.get('[data-testid="dashboard-sidebar"]').should('be.visible');
      cy.get('[data-testid="dashboard-main"]').should('be.visible');
      
      // Wait for CLS measurement
      cy.wait(2000);
      
      cy.window().then((win) => {
        const clsEvent = win.dataLayer.find((item: any) => 
          item.event === 'web_vitals' && item.metric_name === 'CLS'
        );
        
        if (clsEvent) {
          expect(clsEvent).to.exist;
          expect(clsEvent.value).to.be.a('number');
          expect(clsEvent.value).to.be.at.least(0);
          expect(clsEvent.metric_name).to.equal('CLS');
          
          // CLS should be under 0.1 for good performance
          expect(clsEvent.value).to.be.lessThan(0.1);
        }
      });
    });

    it('should track First Input Delay (FID) metrics', () => {
      cy.visit('/chat');
      
      // Wait for page to be interactive
      cy.get('[data-testid="new-chat-btn"]').should('be.visible');
      
      // Perform first user interaction
      cy.get('[data-testid="new-chat-btn"]').click();
      
      // Wait for FID measurement
      cy.wait(1000);
      
      cy.window().then((win) => {
        const fidEvent = win.dataLayer.find((item: any) => 
          item.event === 'web_vitals' && item.metric_name === 'FID'
        );
        
        if (fidEvent) {
          expect(fidEvent).to.exist;
          expect(fidEvent.value).to.be.a('number');
          expect(fidEvent.value).to.be.at.least(0);
          expect(fidEvent.metric_name).to.equal('FID');
          
          // FID should be under 100ms for good performance
          expect(fidEvent.value).to.be.lessThan(100);
          
          // Should include interaction details
          expect(fidEvent.interaction_type).to.exist;
        }
      });
    });
  });

  describe('Page Load Performance', () => {
    it('should track detailed page load timing metrics', () => {
      cy.visit('/');
      
      // Wait for load event
      cy.window().its('document.readyState').should('equal', 'complete');
      
      // Check for performance timing events
      cy.window().then((win) => {
        const performanceEvent = win.dataLayer.find((item: any) => 
          item.event === 'performance_timing'
        );
        
        if (performanceEvent) {
          expect(performanceEvent).to.exist;
          expect(performanceEvent.load_time).to.be.a('number');
          expect(performanceEvent.load_time).to.be.greaterThan(0);
          
          // Should include detailed timing breakdown
          expect(performanceEvent.dns_time).to.be.a('number');
          expect(performanceEvent.tcp_time).to.be.a('number');
          expect(performanceEvent.request_time).to.be.a('number');
          expect(performanceEvent.response_time).to.be.a('number');
          expect(performanceEvent.dom_processing_time).to.be.a('number');
          
          // Page should load within reasonable time
          expect(performanceEvent.load_time).to.be.lessThan(5000);
        }
      });
    });

    it('should track resource loading performance', () => {
      // Navigate to resource-heavy page
      cy.visit('/features');
      
      // Wait for all resources to load
      cy.get('img').should('be.visible');
      cy.wait(2000);
      
      cy.window().then((win) => {
        const resourceEvents = win.dataLayer.filter((item: any) => 
          item.event === 'resource_timing'
        );
        
        if (resourceEvents.length > 0) {
          resourceEvents.forEach((event: any) => {
            expect(event.resource_type).to.be.oneOf(['image', 'script', 'css', 'fetch']);
            expect(event.load_time).to.be.a('number');
            expect(event.load_time).to.be.greaterThan(0);
            expect(event.url).to.be.a('string');
            
            // Resources should load within reasonable time
            expect(event.load_time).to.be.lessThan(3000);
          });
        }
      });
    });

    it('should track bundle size impact', () => {
      cy.visit('/');
      
      // Monitor network activity
      cy.window().then((win) => {
        // Check for bundle size tracking
        const bundleEvent = win.dataLayer.find((item: any) => 
          item.event === 'bundle_metrics'
        );
        
        if (bundleEvent) {
          expect(bundleEvent).to.exist;
          expect(bundleEvent.bundle_size).to.be.a('number');
          expect(bundleEvent.bundle_size).to.be.greaterThan(0);
          expect(bundleEvent.gzip_size).to.be.a('number');
          
          // Bundle should be reasonably sized
          expect(bundleEvent.bundle_size).to.be.lessThan(1000000); // 1MB limit
        }
      });
    });
  });

  describe('Memory Usage Monitoring', () => {
    it('should track JavaScript memory usage', () => {
      cy.visit('/chat');
      
      // Perform memory-intensive operations
      cy.get('[data-testid="new-chat-btn"]').click();
      
      // Generate multiple messages to increase memory usage
      for (let i = 0; i < 5; i++) {
        cy.get('[data-testid="message-input"]').type(`Memory test message ${i}`);
        cy.get('[data-testid="send-message-btn"]').click();
        cy.wait(500);
      }
      
      // Wait for memory metrics
      cy.wait(2000);
      
      cy.window().then((win) => {
        const memoryEvent = win.dataLayer.find((item: any) => 
          item.event === 'memory_usage'
        );
        
        if (memoryEvent && win.performance.memory) {
          expect(memoryEvent).to.exist;
          expect(memoryEvent.used_heap_size).to.be.a('number');
          expect(memoryEvent.total_heap_size).to.be.a('number');
          expect(memoryEvent.heap_size_limit).to.be.a('number');
          
          // Memory usage should be reasonable
          expect(memoryEvent.used_heap_size).to.be.lessThan(memoryEvent.total_heap_size);
          expect(memoryEvent.memory_pressure).to.be.oneOf(['low', 'medium', 'high']);
        }
      });
    });

    it('should detect memory leaks during navigation', () => {
      const pages = ['/chat', '/features', '/pricing', '/dashboard', '/chat'];
      let initialMemory = 0;
      
      // Record initial memory
      cy.window().then((win) => {
        if (win.performance.memory) {
          initialMemory = win.performance.memory.usedJSHeapSize;
        }
      });
      
      // Navigate through pages
      pages.forEach((page) => {
        cy.visit(page);
        cy.wait(1000);
      });
      
      // Check final memory usage
      cy.window().then((win) => {
        if (win.performance.memory && initialMemory > 0) {
          const finalMemory = win.performance.memory.usedJSHeapSize;
          const memoryIncrease = finalMemory - initialMemory;
          const memoryIncreasePercentage = (memoryIncrease / initialMemory) * 100;
          
          // Memory shouldn't increase by more than 50% after navigation
          expect(memoryIncreasePercentage).to.be.lessThan(50);
          
          // Track memory leak event if increase is significant
          if (memoryIncreasePercentage > 20) {
            const memoryLeakEvent = win.dataLayer.find((item: any) => 
              item.event === 'memory_leak_detected'
            );
            
            if (memoryLeakEvent) {
              expect(memoryLeakEvent.memory_increase).to.equal(memoryIncrease);
              expect(memoryLeakEvent.pages_visited).to.equal(pages.length);
            }
          }
        }
      });
    });
  });

  describe('Error Performance Impact', () => {
    it('should track performance impact of JavaScript errors', () => {
      cy.visit('/');
      
      // Trigger JavaScript error
      cy.window().then((win) => {
        // Simulate error that might affect performance
        try {
          throw new Error('Test performance error');
        } catch (error) {
          // Error should be caught and tracked
          win.dataLayer.push({
            event: 'javascript_error',
            error_message: (error as Error).message,
            error_stack: (error as Error).stack,
            performance_impact: 'measured',
            timestamp: new Date().toISOString()
          });
        }
      });
      
      // Continue using app to measure performance impact
      cy.get('[data-testid="start-trial-btn"]').click();
      
      // Check if error performance impact was tracked
      cy.window().then((win) => {
        const errorEvent = win.dataLayer.find((item: any) => 
          item.event === 'javascript_error'
        );
        
        if (errorEvent) {
          expect(errorEvent).to.exist;
          expect(errorEvent.error_message).to.equal('Test performance error');
          expect(errorEvent.performance_impact).to.exist;
          expect(errorEvent.timestamp).to.exist;
        }
      });
    });

    it('should track GTM script loading impact on performance', () => {
      let loadStartTime: number;
      let loadEndTime: number;
      
      cy.visit('/', {
        onBeforeLoad: (win) => {
          loadStartTime = Date.now();
          
          // Monitor when GTM script finishes loading
          win.addEventListener('load', () => {
            loadEndTime = Date.now();
          });
        }
      });
      
      // Wait for page to fully load
      cy.window().its('document.readyState').should('equal', 'complete');
      
      cy.window().then((win) => {
        const totalLoadTime = loadEndTime - loadStartTime;
        
        // Track GTM loading impact
        const gtmImpactEvent = win.dataLayer.find((item: any) => 
          item.event === 'gtm_performance_impact'
        );
        
        if (gtmImpactEvent) {
          expect(gtmImpactEvent).to.exist;
          expect(gtmImpactEvent.gtm_load_time).to.be.a('number');
          expect(gtmImpactEvent.total_load_time).to.be.a('number');
          expect(gtmImpactEvent.gtm_impact_percentage).to.be.a('number');
          
          // GTM should not significantly impact load time
          expect(gtmImpactEvent.gtm_impact_percentage).to.be.lessThan(20);
        }
        
        // Total load time should still be reasonable with GTM
        expect(totalLoadTime).to.be.lessThan(5000);
      });
    });
  });

  describe('Real User Monitoring (RUM)', () => {
    it('should collect real user performance metrics', () => {
      cy.login('test@netra.com', 'password');
      cy.visit('/dashboard');
      
      // Simulate real user interactions
      cy.get('[data-testid="dashboard-sidebar"]').click();
      cy.get('[data-testid="performance-metrics"]').click();
      cy.get('[data-testid="user-profile"]').click();
      
      // Wait for RUM data collection
      cy.wait(3000);
      
      cy.window().then((win) => {
        const rumEvent = win.dataLayer.find((item: any) => 
          item.event === 'rum_metrics'
        );
        
        if (rumEvent) {
          expect(rumEvent).to.exist;
          expect(rumEvent.user_id).to.exist;
          expect(rumEvent.session_id).to.exist;
          expect(rumEvent.page_views).to.be.a('number');
          expect(rumEvent.interactions).to.be.a('number');
          expect(rumEvent.avg_response_time).to.be.a('number');
          expect(rumEvent.error_count).to.be.a('number');
          
          // RUM metrics should show reasonable user experience
          expect(rumEvent.avg_response_time).to.be.lessThan(1000);
          expect(rumEvent.error_count).to.be.lessThan(5);
        }
      });
    });

    it('should track performance across different user segments', () => {
      const userSegments = [
        { tier: 'free', path: '/chat' },
        { tier: 'premium', path: '/dashboard' },
        { tier: 'enterprise', path: '/admin' }
      ];
      
      userSegments.forEach((segment) => {
        // Simulate different user types
        cy.window().then((win) => {
          win.dataLayer.push({
            event: 'user_segment',
            user_tier: segment.tier,
            page_path: segment.path
          });
        });
        
        cy.visit(segment.path);
        cy.wait(1000);
        
        // Performance should be tracked per segment
        cy.window().then((win) => {
          const segmentPerformance = win.dataLayer.find((item: any) => 
            item.event === 'segment_performance' && item.user_tier === segment.tier
          );
          
          if (segmentPerformance) {
            expect(segmentPerformance.user_tier).to.equal(segment.tier);
            expect(segmentPerformance.avg_load_time).to.be.a('number');
            expect(segmentPerformance.page_path).to.equal(segment.path);
          }
        });
      });
    });
  });

  describe('Performance Alerts and Thresholds', () => {
    it('should trigger performance alerts for slow pages', () => {
      // Simulate slow page load
      cy.intercept('GET', '**/api/**', (req) => {
        req.reply((res) => {
          // Add delay to simulate slow API
          return new Promise((resolve) => {
            setTimeout(() => resolve(res), 3000);
          });
        });
      }).as('slowAPI');
      
      cy.visit('/dashboard');
      
      // Wait for slow loading
      cy.wait('@slowAPI');
      cy.wait(4000);
      
      cy.window().then((win) => {
        const performanceAlert = win.dataLayer.find((item: any) => 
          item.event === 'performance_alert'
        );
        
        if (performanceAlert) {
          expect(performanceAlert).to.exist;
          expect(performanceAlert.alert_type).to.equal('slow_page_load');
          expect(performanceAlert.threshold_exceeded).to.be.true;
          expect(performanceAlert.actual_time).to.be.greaterThan(2500);
          expect(performanceAlert.threshold_time).to.be.a('number');
        }
      });
    });

    it('should track performance regression over time', () => {
      const performanceBaseline = {
        fcp: 1200,
        lcp: 1800,
        cls: 0.05,
        fid: 50
      };
      
      cy.visit('/');
      cy.wait(2000);
      
      cy.window().then((win) => {
        // Simulate performance regression detection
        win.dataLayer.push({
          event: 'performance_regression',
          metric_type: 'LCP',
          baseline_value: performanceBaseline.lcp,
          current_value: 2500,
          regression_percentage: 38.9,
          page_path: '/',
          timestamp: new Date().toISOString()
        });
        
        const regressionEvent = win.dataLayer.find((item: any) => 
          item.event === 'performance_regression'
        );
        
        expect(regressionEvent).to.exist;
        expect(regressionEvent.regression_percentage).to.be.greaterThan(0);
        expect(regressionEvent.current_value).to.be.greaterThan(regressionEvent.baseline_value);
      });
    });
  });

  afterEach(() => {
    // Clean up performance observers and data
    cy.window().then((win) => {
      if (win.dataLayer) {
        // Clear performance-related events
        win.dataLayer.length = 0;
      }
    });
  });
});