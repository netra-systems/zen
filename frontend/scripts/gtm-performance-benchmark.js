#!/usr/bin/env node

/**
 * GTM Performance Benchmark Script
 * 
 * Measures and tracks performance metrics for GTM integration.
 * Creates baseline measurements and detects performance regressions.
 */

const fs = require('fs');
const path = require('path');
const chalk = require('chalk');
const { performance } = require('perf_hooks');

// Configuration
const BENCHMARK_CONFIG = {
  outputDir: './test-reports/gtm/performance',
  baselineFile: 'gtm-performance-baseline.json',
  reportFile: 'gtm-performance-report.json',
  iterations: 10,
  warmupIterations: 3,
  thresholds: {
    scriptLoadTime: 100,     // ms
    eventProcessingTime: 5,  // ms per event
    memoryIncrease: 20,      // MB
    regressionThreshold: 20  // % increase from baseline
  },
  scenarios: {
    scriptLoad: {
      name: 'GTM Script Loading',
      description: 'Time to load and initialize GTM script'
    },
    singleEvent: {
      name: 'Single Event Processing',
      description: 'Time to process a single GTM event'
    },
    bulkEvents: {
      name: 'Bulk Event Processing',
      description: 'Time to process 100 events in sequence',
      eventCount: 100
    },
    heavyEvents: {
      name: 'Heavy Event Processing',
      description: 'Time to process events with large payloads',
      eventCount: 20,
      payloadSize: 10000 // bytes
    },
    memoryUsage: {
      name: 'Memory Usage Test',
      description: 'Memory consumption during GTM operations'
    }
  }
};

// Utilities
const logger = {
  info: (msg) => console.log(chalk.blue('ℹ'), msg),
  success: (msg) => console.log(chalk.green('✓'), msg),
  error: (msg) => console.log(chalk.red('✗'), msg),
  warn: (msg) => console.log(chalk.yellow('⚠'), msg),
  debug: (msg) => process.env.DEBUG && console.log(chalk.gray('🔍'), msg),
  section: (msg) => console.log(chalk.bold.cyan(`\n${'='.repeat(60)}\n${msg}\n${'='.repeat(60)}`))
};

const ensureDirectory = (dir) => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
};

// Mock GTM environment for benchmarking
class MockGTMEnvironment {
  constructor() {
    this.dataLayer = [];
    this.scriptLoaded = false;
    this.loadTime = 0;
    this.eventProcessingTimes = [];
    this.memoryUsage = {
      initial: 10000000, // 10MB baseline
      current: 10000000
    };
  }

  // Simulate GTM script loading
  async loadScript() {
    const startTime = performance.now();
    
    // Simulate network delay and script parsing
    await new Promise(resolve => {
      const delay = 30 + Math.random() * 40; // 30-70ms
      setTimeout(resolve, delay);
    });
    
    const endTime = performance.now();
    this.loadTime = endTime - startTime;
    this.scriptLoaded = true;
    
    // Simulate memory allocation for GTM
    this.memoryUsage.current += 2000000; // 2MB for GTM
    
    return this.loadTime;
  }

  // Simulate event processing
  processEvent(event, options = {}) {
    if (!this.scriptLoaded) {
      throw new Error('GTM script not loaded');
    }

    const startTime = performance.now();
    
    // Simulate event processing logic
    const processingTime = 1 + Math.random() * 3; // 1-4ms base time
    
    // Add complexity for large events
    if (options.payloadSize) {
      const additionalTime = (options.payloadSize / 1000) * 0.1; // 0.1ms per KB
      setTimeout(() => {}, additionalTime);
    }
    
    // Simulate dataLayer push
    this.dataLayer.push({
      ...event,
      timestamp: new Date().toISOString(),
      processingTime: processingTime
    });
    
    // Simulate memory allocation for event
    const eventMemory = 1000 + (options.payloadSize || 0) * 1.2; // Base + payload
    this.memoryUsage.current += eventMemory;
    
    const endTime = performance.now();
    const totalTime = endTime - startTime;
    
    this.eventProcessingTimes.push(totalTime);
    return totalTime;
  }

  // Simulate garbage collection
  garbageCollect() {
    const beforeGC = this.memoryUsage.current;
    
    // Simulate GC reclaiming some memory
    const reclaimedMemory = this.memoryUsage.current * 0.2; // 20% reclaimed
    this.memoryUsage.current = Math.max(
      this.memoryUsage.current - reclaimedMemory,
      this.memoryUsage.initial
    );
    
    return beforeGC - this.memoryUsage.current;
  }

  getStats() {
    const eventTimes = this.eventProcessingTimes;
    return {
      scriptLoadTime: this.loadTime,
      totalEvents: this.dataLayer.length,
      averageEventTime: eventTimes.length > 0 
        ? eventTimes.reduce((sum, time) => sum + time, 0) / eventTimes.length 
        : 0,
      minEventTime: Math.min(...eventTimes) || 0,
      maxEventTime: Math.max(...eventTimes) || 0,
      memoryUsage: {
        initial: this.memoryUsage.initial,
        current: this.memoryUsage.current,
        increase: this.memoryUsage.current - this.memoryUsage.initial
      }
    };
  }

  reset() {
    this.dataLayer = [];
    this.scriptLoaded = false;
    this.loadTime = 0;
    this.eventProcessingTimes = [];
    this.memoryUsage.current = this.memoryUsage.initial;
  }
}

// Benchmark scenarios
class GTMBenchmarkRunner {
  constructor() {
    this.results = {};
    this.baseline = null;
    this.gtm = null;
  }

  async loadBaseline() {
    const baselinePath = path.join(BENCHMARK_CONFIG.outputDir, BENCHMARK_CONFIG.baselineFile);
    
    if (fs.existsSync(baselinePath)) {
      try {
        const baselineData = fs.readFileSync(baselinePath, 'utf8');
        this.baseline = JSON.parse(baselineData);
        logger.info(`Loaded performance baseline from ${baselinePath}`);
      } catch (error) {
        logger.warn('Failed to load baseline, will create new baseline');
        this.baseline = null;
      }
    }
  }

  async saveBaseline() {
    const baselinePath = path.join(BENCHMARK_CONFIG.outputDir, BENCHMARK_CONFIG.baselineFile);
    
    try {
      fs.writeFileSync(baselinePath, JSON.stringify(this.results, null, 2));
      logger.success(`Baseline saved to ${baselinePath}`);
    } catch (error) {
      logger.error(`Failed to save baseline: ${error.message}`);
    }
  }

  async runScenario(scenarioKey, scenario) {
    logger.info(`Running scenario: ${scenario.name}`);
    const results = [];

    // Warmup iterations
    for (let i = 0; i < BENCHMARK_CONFIG.warmupIterations; i++) {
      this.gtm = new MockGTMEnvironment();
      await this.executeScenario(scenarioKey, scenario);
      logger.debug(`Warmup ${i + 1}/${BENCHMARK_CONFIG.warmupIterations} completed`);
    }

    // Actual benchmark iterations
    for (let i = 0; i < BENCHMARK_CONFIG.iterations; i++) {
      this.gtm = new MockGTMEnvironment();
      const result = await this.executeScenario(scenarioKey, scenario);
      results.push(result);
      logger.debug(`Iteration ${i + 1}/${BENCHMARK_CONFIG.iterations}: ${JSON.stringify(result)}`);
    }

    return this.calculateStatistics(results);
  }

  async executeScenario(scenarioKey, scenario) {
    const startTime = performance.now();
    let result = {};

    try {
      switch (scenarioKey) {
        case 'scriptLoad':
          result.loadTime = await this.gtm.loadScript();
          break;

        case 'singleEvent':
          await this.gtm.loadScript();
          result.eventTime = this.gtm.processEvent({
            event: 'test_event',
            category: 'benchmark'
          });
          break;

        case 'bulkEvents':
          await this.gtm.loadScript();
          const bulkStartTime = performance.now();
          
          for (let i = 0; i < scenario.eventCount; i++) {
            this.gtm.processEvent({
              event: `bulk_event_${i}`,
              category: 'benchmark',
              index: i
            });
          }
          
          const bulkEndTime = performance.now();
          result.totalTime = bulkEndTime - bulkStartTime;
          result.averageEventTime = result.totalTime / scenario.eventCount;
          break;

        case 'heavyEvents':
          await this.gtm.loadScript();
          const heavyStartTime = performance.now();
          
          for (let i = 0; i < scenario.eventCount; i++) {
            this.gtm.processEvent({
              event: `heavy_event_${i}`,
              category: 'benchmark',
              payload: 'x'.repeat(scenario.payloadSize),
              index: i
            }, { payloadSize: scenario.payloadSize });
          }
          
          const heavyEndTime = performance.now();
          result.totalTime = heavyEndTime - heavyStartTime;
          result.averageEventTime = result.totalTime / scenario.eventCount;
          break;

        case 'memoryUsage':
          await this.gtm.loadScript();
          const initialMemory = this.gtm.memoryUsage.current;
          
          // Process many events to test memory usage
          for (let i = 0; i < 100; i++) {
            this.gtm.processEvent({
              event: `memory_test_${i}`,
              category: 'benchmark',
              data: 'x'.repeat(1000) // 1KB per event
            }, { payloadSize: 1000 });
          }
          
          const peakMemory = this.gtm.memoryUsage.current;
          this.gtm.garbageCollect();
          const afterGCMemory = this.gtm.memoryUsage.current;
          
          result.initialMemory = initialMemory;
          result.peakMemory = peakMemory;
          result.afterGCMemory = afterGCMemory;
          result.memoryIncrease = peakMemory - initialMemory;
          result.memoryRecovered = peakMemory - afterGCMemory;
          break;

        default:
          throw new Error(`Unknown scenario: ${scenarioKey}`);
      }

      const endTime = performance.now();
      result.totalDuration = endTime - startTime;
      result.success = true;

    } catch (error) {
      logger.error(`Scenario ${scenarioKey} failed: ${error.message}`);
      result.success = false;
      result.error = error.message;
    }

    // Get overall GTM stats
    if (this.gtm) {
      result.gtmStats = this.gtm.getStats();
    }

    return result;
  }

  calculateStatistics(results) {
    const successfulResults = results.filter(r => r.success);
    
    if (successfulResults.length === 0) {
      return { error: 'All iterations failed' };
    }

    const getMetricValues = (metricPath) => {
      return successfulResults.map(result => {
        const keys = metricPath.split('.');
        return keys.reduce((obj, key) => obj?.[key], result);
      }).filter(val => val !== undefined && val !== null);
    };

    const calculateStats = (values) => {
      if (values.length === 0) return null;
      
      const sorted = [...values].sort((a, b) => a - b);
      const sum = values.reduce((acc, val) => acc + val, 0);
      
      return {
        min: Math.min(...values),
        max: Math.max(...values),
        mean: sum / values.length,
        median: sorted[Math.floor(sorted.length / 2)],
        p95: sorted[Math.floor(sorted.length * 0.95)],
        p99: sorted[Math.floor(sorted.length * 0.99)],
        stdDev: Math.sqrt(values.reduce((acc, val) => acc + Math.pow(val - sum / values.length, 2), 0) / values.length)
      };
    };

    const stats = {
      iterations: {
        total: results.length,
        successful: successfulResults.length,
        failed: results.length - successfulResults.length
      },
      metrics: {}
    };

    // Calculate statistics for different metrics based on scenario
    const firstResult = successfulResults[0];
    
    if (firstResult.loadTime !== undefined) {
      stats.metrics.loadTime = calculateStats(getMetricValues('loadTime'));
    }
    
    if (firstResult.eventTime !== undefined) {
      stats.metrics.eventTime = calculateStats(getMetricValues('eventTime'));
    }
    
    if (firstResult.averageEventTime !== undefined) {
      stats.metrics.averageEventTime = calculateStats(getMetricValues('averageEventTime'));
    }
    
    if (firstResult.memoryIncrease !== undefined) {
      stats.metrics.memoryIncrease = calculateStats(getMetricValues('memoryIncrease'));
    }
    
    if (firstResult.totalDuration !== undefined) {
      stats.metrics.totalDuration = calculateStats(getMetricValues('totalDuration'));
    }

    return stats;
  }

  compareWithBaseline(currentResults) {
    if (!this.baseline) {
      logger.info('No baseline available for comparison');
      return null;
    }

    const comparisons = {};

    Object.keys(currentResults).forEach(scenarioKey => {
      const current = currentResults[scenarioKey];
      const baseline = this.baseline[scenarioKey];
      
      if (!baseline || !current.metrics) {
        return;
      }

      comparisons[scenarioKey] = {};

      Object.keys(current.metrics).forEach(metricKey => {
        const currentMetric = current.metrics[metricKey];
        const baselineMetric = baseline.metrics?.[metricKey];
        
        if (!baselineMetric || !currentMetric) {
          return;
        }

        const comparison = {
          current: currentMetric.mean,
          baseline: baselineMetric.mean,
          change: currentMetric.mean - baselineMetric.mean,
          changePercent: ((currentMetric.mean - baselineMetric.mean) / baselineMetric.mean) * 100,
          regression: false
        };

        // Check for regression
        if (comparison.changePercent > BENCHMARK_CONFIG.thresholds.regressionThreshold) {
          comparison.regression = true;
          logger.warn(`Regression detected in ${scenarioKey}.${metricKey}: ${comparison.changePercent.toFixed(1)}% increase`);
        }

        comparisons[scenarioKey][metricKey] = comparison;
      });
    });

    return comparisons;
  }

  generateReport(results, comparisons) {
    const report = {
      timestamp: new Date().toISOString(),
      configuration: BENCHMARK_CONFIG,
      results: results,
      comparisons: comparisons,
      summary: {
        totalScenarios: Object.keys(results).length,
        successfulScenarios: Object.keys(results).filter(key => !results[key].error).length,
        regressions: 0,
        recommendations: []
      }
    };

    // Count regressions and generate recommendations
    if (comparisons) {
      Object.values(comparisons).forEach(scenario => {
        Object.values(scenario).forEach(metric => {
          if (metric.regression) {
            report.summary.regressions++;
          }
        });
      });
    }

    // Generate recommendations based on results
    Object.keys(results).forEach(scenarioKey => {
      const scenario = results[scenarioKey];
      const thresholds = BENCHMARK_CONFIG.thresholds;

      if (scenario.metrics?.loadTime?.mean > thresholds.scriptLoadTime) {
        report.summary.recommendations.push({
          type: 'performance',
          scenario: scenarioKey,
          message: `Script load time (${scenario.metrics.loadTime.mean.toFixed(1)}ms) exceeds threshold (${thresholds.scriptLoadTime}ms)`
        });
      }

      if (scenario.metrics?.eventTime?.mean > thresholds.eventProcessingTime) {
        report.summary.recommendations.push({
          type: 'performance',
          scenario: scenarioKey,
          message: `Event processing time (${scenario.metrics.eventTime.mean.toFixed(1)}ms) exceeds threshold (${thresholds.eventProcessingTime}ms)`
        });
      }

      if (scenario.metrics?.memoryIncrease?.mean > thresholds.memoryIncrease * 1024 * 1024) {
        report.summary.recommendations.push({
          type: 'memory',
          scenario: scenarioKey,
          message: `Memory increase (${(scenario.metrics.memoryIncrease.mean / 1024 / 1024).toFixed(1)}MB) exceeds threshold (${thresholds.memoryIncrease}MB)`
        });
      }
    });

    return report;
  }

  async saveReport(report) {
    const reportPath = path.join(BENCHMARK_CONFIG.outputDir, BENCHMARK_CONFIG.reportFile);
    
    try {
      fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
      logger.success(`Performance report saved to ${reportPath}`);

      // Also save as HTML
      const htmlReport = this.generateHTMLReport(report);
      const htmlPath = path.join(BENCHMARK_CONFIG.outputDir, 'gtm-performance-report.html');
      fs.writeFileSync(htmlPath, htmlReport);
      logger.success(`HTML report saved to ${htmlPath}`);

    } catch (error) {
      logger.error(`Failed to save report: ${error.message}`);
    }
  }

  generateHTMLReport(report) {
    const formatNumber = (num) => typeof num === 'number' ? num.toFixed(2) : 'N/A';
    const formatPercent = (num) => typeof num === 'number' ? `${num > 0 ? '+' : ''}${num.toFixed(1)}%` : 'N/A';

    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GTM Performance Benchmark Report</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f8fafc; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; }
        .header h1 { margin: 0 0 10px 0; font-size: 2.5em; }
        .header .meta { opacity: 0.9; font-size: 1.1em; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric-card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07); border-left: 4px solid #3b82f6; }
        .metric-card h3 { margin: 0 0 10px 0; color: #1f2937; font-size: 1.1em; }
        .metric-card .value { font-size: 2.5em; font-weight: bold; color: #1f2937; margin: 10px 0; }
        .metric-card.warning { border-left-color: #f59e0b; }
        .metric-card.error { border-left-color: #ef4444; }
        .metric-card.success { border-left-color: #10b981; }
        .section { background: white; margin-bottom: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07); overflow: hidden; }
        .section-header { background: #f8fafc; padding: 20px; border-bottom: 1px solid #e5e7eb; }
        .section-header h2 { margin: 0; color: #1f2937; }
        .section-content { padding: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }
        th { background: #f8fafc; font-weight: 600; color: #374151; }
        .metric-good { color: #059669; }
        .metric-warning { color: #d97706; }
        .metric-bad { color: #dc2626; }
        .regression { background: #fef2f2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; }
        .improvement { background: #f0fdf4; color: #166534; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; }
        .recommendation { background: #fffbeb; border: 1px solid #fbbf24; border-radius: 8px; padding: 15px; margin-bottom: 15px; }
        .recommendation.error { background: #fef2f2; border-color: #f87171; }
        .recommendation h4 { margin: 0 0 8px 0; color: #92400e; }
        .recommendation.error h4 { color: #991b1b; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>GTM Performance Benchmark</h1>
            <div class="meta">
                Generated: ${report.timestamp}<br>
                Iterations per scenario: ${BENCHMARK_CONFIG.iterations}
            </div>
        </div>

        <div class="summary">
            <div class="metric-card ${report.summary.regressions > 0 ? 'error' : 'success'}">
                <h3>Regressions Detected</h3>
                <div class="value">${report.summary.regressions}</div>
            </div>
            <div class="metric-card">
                <h3>Scenarios Tested</h3>
                <div class="value">${report.summary.totalScenarios}</div>
            </div>
            <div class="metric-card ${report.summary.successfulScenarios === report.summary.totalScenarios ? 'success' : 'warning'}">
                <h3>Successful Tests</h3>
                <div class="value">${report.summary.successfulScenarios}</div>
            </div>
            <div class="metric-card">
                <h3>Recommendations</h3>
                <div class="value">${report.summary.recommendations.length}</div>
            </div>
        </div>

        ${Object.keys(report.results).map(scenarioKey => {
          const scenario = report.results[scenarioKey];
          const scenarioComparison = report.comparisons?.[scenarioKey] || {};

          return `
        <div class="section">
            <div class="section-header">
                <h2>${BENCHMARK_CONFIG.scenarios[scenarioKey]?.name || scenarioKey}</h2>
            </div>
            <div class="section-content">
                ${scenario.error ? `
                    <div class="recommendation error">
                        <h4>Test Failed</h4>
                        <p>${scenario.error}</p>
                    </div>
                ` : ''}
                
                ${scenario.metrics ? `
                    <table>
                        <thead>
                            <tr>
                                <th>Metric</th>
                                <th>Mean</th>
                                <th>Min</th>
                                <th>Max</th>
                                <th>P95</th>
                                <th>Std Dev</th>
                                ${report.comparisons ? '<th>Baseline Comparison</th>' : ''}
                            </tr>
                        </thead>
                        <tbody>
                            ${Object.keys(scenario.metrics).map(metricKey => {
                              const metric = scenario.metrics[metricKey];
                              const comparison = scenarioComparison[metricKey];
                              
                              return `
                                <tr>
                                    <td><strong>${metricKey}</strong></td>
                                    <td>${formatNumber(metric.mean)}</td>
                                    <td>${formatNumber(metric.min)}</td>
                                    <td>${formatNumber(metric.max)}</td>
                                    <td>${formatNumber(metric.p95)}</td>
                                    <td>${formatNumber(metric.stdDev)}</td>
                                    ${comparison ? `
                                        <td>
                                            <span class="${comparison.regression ? 'regression' : comparison.changePercent < -5 ? 'improvement' : ''}">
                                                ${formatPercent(comparison.changePercent)}
                                            </span>
                                        </td>
                                    ` : report.comparisons ? '<td>-</td>' : ''}
                                </tr>
                              `;
                            }).join('')}
                        </tbody>
                    </table>
                ` : ''}
            </div>
        </div>
          `;
        }).join('')}

        ${report.summary.recommendations.length > 0 ? `
        <div class="section">
            <div class="section-header">
                <h2>Recommendations</h2>
            </div>
            <div class="section-content">
                ${report.summary.recommendations.map(rec => `
                    <div class="recommendation ${rec.type === 'memory' ? 'error' : ''}">
                        <h4>${rec.scenario} - ${rec.type === 'memory' ? 'Memory' : 'Performance'} Issue</h4>
                        <p>${rec.message}</p>
                    </div>
                `).join('')}
            </div>
        </div>
        ` : ''}

        <div class="section">
            <div class="section-header">
                <h2>Performance Thresholds</h2>
            </div>
            <div class="section-content">
                <table>
                    <tr><th>Metric</th><th>Threshold</th><th>Description</th></tr>
                    <tr><td>Script Load Time</td><td>${BENCHMARK_CONFIG.thresholds.scriptLoadTime}ms</td><td>Maximum acceptable GTM script loading time</td></tr>
                    <tr><td>Event Processing</td><td>${BENCHMARK_CONFIG.thresholds.eventProcessingTime}ms</td><td>Maximum time to process a single event</td></tr>
                    <tr><td>Memory Increase</td><td>${BENCHMARK_CONFIG.thresholds.memoryIncrease}MB</td><td>Maximum acceptable memory increase</td></tr>
                    <tr><td>Regression Alert</td><td>${BENCHMARK_CONFIG.thresholds.regressionThreshold}%</td><td>Performance degradation threshold</td></tr>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
    `;
  }
}

// Main execution
async function main() {
  const args = process.argv.slice(2);
  const createBaseline = args.includes('--create-baseline');
  const scenarios = args.filter(arg => !arg.startsWith('--'));
  
  logger.section('GTM Performance Benchmark');
  logger.info('Initializing performance benchmarking suite...');
  
  // Ensure output directory exists
  ensureDirectory(BENCHMARK_CONFIG.outputDir);
  
  const runner = new GTMBenchmarkRunner();
  
  // Load existing baseline unless creating new one
  if (!createBaseline) {
    await runner.loadBaseline();
  }
  
  // Determine which scenarios to run
  const scenariosToRun = scenarios.length > 0 
    ? scenarios.filter(s => BENCHMARK_CONFIG.scenarios[s])
    : Object.keys(BENCHMARK_CONFIG.scenarios);
    
  logger.info(`Running scenarios: ${scenariosToRun.join(', ')}`);
  
  // Run benchmarks
  const results = {};
  
  for (const scenarioKey of scenariosToRun) {
    const scenario = BENCHMARK_CONFIG.scenarios[scenarioKey];
    logger.section(`Benchmarking: ${scenario.name}`);
    logger.info(scenario.description);
    
    try {
      const result = await runner.runScenario(scenarioKey, scenario);
      results[scenarioKey] = result;
      
      if (result.error) {
        logger.error(`Scenario failed: ${result.error}`);
      } else {
        logger.success('Scenario completed successfully');
        if (result.metrics) {
          Object.entries(result.metrics).forEach(([metric, stats]) => {
            logger.info(`${metric}: ${stats.mean.toFixed(2)} (±${stats.stdDev.toFixed(2)})`);
          });
        }
      }
    } catch (error) {
      logger.error(`Failed to run scenario ${scenarioKey}: ${error.message}`);
      results[scenarioKey] = { error: error.message };
    }
  }
  
  // Compare with baseline
  logger.section('Performance Analysis');
  const comparisons = runner.compareWithBaseline(results);
  
  // Generate and save report
  const report = runner.generateReport(results, comparisons);
  await runner.saveReport(report);
  
  // Save as baseline if requested
  if (createBaseline) {
    await runner.saveBaseline();
    logger.success('New performance baseline created');
  }
  
  // Summary
  logger.section('Benchmark Summary');
  
  if (report.summary.regressions > 0) {
    logger.error(`${report.summary.regressions} performance regressions detected!`);
    logger.warn('Review the detailed report for recommendations');
  } else {
    logger.success('No performance regressions detected');
  }
  
  if (report.summary.recommendations.length > 0) {
    logger.warn(`${report.summary.recommendations.length} performance recommendations available`);
  }
  
  logger.info(`Detailed report: ${path.join(BENCHMARK_CONFIG.outputDir, 'gtm-performance-report.html')}`);
  
  // Exit with appropriate code
  if (report.summary.regressions > 0) {
    process.exit(1);
  }
}

// Execute if run directly
if (require.main === module) {
  main().catch(error => {
    logger.error('Benchmark failed:', error.message);
    if (process.env.DEBUG) {
      console.error(error.stack);
    }
    process.exit(1);
  });
}

module.exports = {
  GTMBenchmarkRunner,
  MockGTMEnvironment,
  BENCHMARK_CONFIG
};