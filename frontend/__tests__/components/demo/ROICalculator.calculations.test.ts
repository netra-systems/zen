/**
 * ROI Calculator Calculations Unit Tests
 * ====================================
 * Business-critical testing for individual calculation functions
 * 
 * BVJ: Growth & Enterprise - Revenue-critical sales tool validation
 * Value Impact: Ensures 100% accuracy for Enterprise deal justification
 * Revenue Impact: Prevents lost $50K+ ARR deals due to calculation errors
 * 
 * Modular design: ≤300 lines, functions ≤8 lines
 */

import { 
  calculateInfrastructureSavings,
  calculateOperationalSavings,
  calculatePerformanceValue,
  calculatePaybackPeriod,
  calculateThreeYearROI,
  buildFallbackSavings,
  buildCalculationInput,
  mapApiResponseToSavings
} from '@/components/demo/ROICalculator.calculations';

import { 
  Metrics, 
  INDUSTRY_MULTIPLIERS, 
  DEFAULT_METRICS,
  ROIApiResponse 
} from '@/components/demo/ROICalculator.types';

import { describeFeature, testTDD } from '@/test-utils/feature-flags';

describeFeature('roi_calculator', 'ROI Calculator Individual Functions', () => {
  const createTestMetrics = (overrides: Partial<Metrics> = {}): Metrics => ({
    ...DEFAULT_METRICS,
    ...overrides
  });

  const createMockAPIResponse = (overrides: any = {}): ROIApiResponse => ({
    current_annual_cost: 600000,
    optimized_annual_cost: 390000,
    annual_savings: 210000,
    roi_months: 4,
    three_year_tco_reduction: 630000,
    ...overrides
  });

  describe('calculateInfrastructureSavings', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    const originalRandom = Math.random;

    beforeEach(() => {
      Math.random = () => 0.5; // Consistent results
    });

    afterEach(() => {
      Math.random = originalRandom;
        // Clean up timers to prevent hanging
        jest.clearAllTimers();
        jest.useFakeTimers();
        jest.runOnlyPendingTimers();
        jest.useRealTimers();
        cleanupAntiHang();
    });

    it('should calculate infrastructure savings with base formula', () => {
      const metrics = createTestMetrics({ currentMonthlySpend: 100000 });
      const multiplier = 1.0;
      
      const result = calculateInfrastructureSavings(metrics, multiplier);
      
      // Base: 45% + (0.5 * 15%) = 52.5% savings
      const expectedPercent = 0.45 + (0.5 * 0.15);
      const expected = 100000 * expectedPercent * 1.0;
      expect(result).toBe(expected);
    });

    it('should apply industry multiplier correctly', () => {
      const metrics = createTestMetrics({ currentMonthlySpend: 50000 });
      const techMultiplier = INDUSTRY_MULTIPLIERS['Technology']; // 1.35
      
      const result = calculateInfrastructureSavings(metrics, techMultiplier);
      
      const expectedPercent = 0.45 + (0.5 * 0.15);
      const expected = 50000 * expectedPercent * 1.35;
      expect(result).toBeCloseTo(expected, 2);
    });

    it('should handle zero spend gracefully', () => {
      const metrics = createTestMetrics({ currentMonthlySpend: 0 });
      const result = calculateInfrastructureSavings(metrics, 1.0);
      expect(result).toBe(0);
    });

    it('should produce different results with real randomization', () => {
      Math.random = originalRandom; // Use real randomization
      const metrics = createTestMetrics({ currentMonthlySpend: 100000 });
      
      const results = Array.from({ length: 10 }, () => 
        calculateInfrastructureSavings(metrics, 1.0)
      );
      
      const uniqueResults = new Set(results);
      expect(uniqueResults.size).toBeGreaterThan(1);
    });
  });

  describe('calculateOperationalSavings', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should calculate operational savings based on team size', () => {
      const metrics = createTestMetrics({ teamSize: 10 });
      const result = calculateOperationalSavings(metrics);
      
      // Formula: teamSize * 10000 * 0.25
      const expected = 10 * 10000 * 0.25;
      expect(result).toBe(expected);
    });

    it('should handle small teams', () => {
      const metrics = createTestMetrics({ teamSize: 1 });
      const result = calculateOperationalSavings(metrics);
      expect(result).toBe(2500); // 1 * 10000 * 0.25
    });

    it('should handle large enterprise teams', () => {
      const metrics = createTestMetrics({ teamSize: 100 });
      const result = calculateOperationalSavings(metrics);
      expect(result).toBe(250000); // 100 * 10000 * 0.25
    });

    it('should handle zero team size', () => {
      const metrics = createTestMetrics({ teamSize: 0 });
      const result = calculateOperationalSavings(metrics);
      expect(result).toBe(0);
    });
  });

  describe('calculatePerformanceValue', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should calculate performance value from request volume', () => {
      const metrics = createTestMetrics({ requestsPerMonth: 10000000 });
      const result = calculatePerformanceValue(metrics);
      
      // Formula: (requests / 1M) * 500 * 0.6
      const expected = (10000000 / 1000000) * 500 * 0.6;
      expect(result).toBe(expected);
    });

    it('should handle low volume requests', () => {
      const metrics = createTestMetrics({ requestsPerMonth: 100000 });
      const result = calculatePerformanceValue(metrics);
      expect(result).toBe(30); // (0.1M / 1M) * 500 * 0.6
    });

    it('should handle high enterprise volume', () => {
      const metrics = createTestMetrics({ requestsPerMonth: 100000000 });
      const result = calculatePerformanceValue(metrics);
      expect(result).toBe(30000); // (100M / 1M) * 500 * 0.6
    });

    it('should handle zero requests', () => {
      const metrics = createTestMetrics({ requestsPerMonth: 0 });
      const result = calculatePerformanceValue(metrics);
      expect(result).toBe(0);
    });
  });

  describe('calculatePaybackPeriod', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should calculate payback period correctly', () => {
      const implementationCost = 100000;
      const monthlySavings = 25000;
      const result = calculatePaybackPeriod(implementationCost, monthlySavings);
      expect(result).toBe(4); // 100000 / 25000
    });

    it('should handle fractional months', () => {
      const implementationCost = 75000;
      const monthlySavings = 20000;
      const result = calculatePaybackPeriod(implementationCost, monthlySavings);
      expect(result).toBe(3.75);
    });

    it('should handle zero monthly savings', () => {
      const implementationCost = 100000;
      const monthlySavings = 0;
      const result = calculatePaybackPeriod(implementationCost, monthlySavings);
      expect(result).toBe(Infinity);
    });

    it('should handle zero implementation cost', () => {
      const implementationCost = 0;
      const monthlySavings = 25000;
      const result = calculatePaybackPeriod(implementationCost, monthlySavings);
      expect(result).toBe(0);
    });
  });

  describe('calculateThreeYearROI', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should calculate three-year ROI percentage', () => {
      const annualSavings = 100000;
      const implementationCost = 50000;
      const result = calculateThreeYearROI(annualSavings, implementationCost);
      
      // Formula: ((3 * 100000 - 50000) / 50000) * 100 = 500%
      const expected = ((300000 - 50000) / 50000) * 100;
      expect(result).toBe(expected);
    });

    it('should handle break-even scenarios', () => {
      const annualSavings = 50000;
      const implementationCost = 150000;
      const result = calculateThreeYearROI(annualSavings, implementationCost);
      
      const expected = ((150000 - 150000) / 150000) * 100;
      expect(result).toBe(expected); // 0% ROI
    });

    it('should handle negative ROI scenarios', () => {
      const annualSavings = 25000;
      const implementationCost = 100000;
      const result = calculateThreeYearROI(annualSavings, implementationCost);
      
      const expected = ((75000 - 100000) / 100000) * 100;
      expect(result).toBe(expected); // -25% ROI
    });
  });

  describe('buildCalculationInput', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should build calculation input from metrics and industry', () => {
      const metrics = createTestMetrics({
        currentMonthlySpend: 75000,
        requestsPerMonth: 15000000,
        averageLatency: 300
      });
      
      const result = buildCalculationInput(metrics, 'Financial Services');
      
      expect(result).toEqual({
        current_spend: 75000,
        request_volume: 15000000,
        average_latency: 300,
        industry: 'Financial Services'
      });
    });

    it('should handle default metrics', () => {
      const result = buildCalculationInput(DEFAULT_METRICS, 'Technology');
      
      expect(result.current_spend).toBe(DEFAULT_METRICS.currentMonthlySpend);
      expect(result.request_volume).toBe(DEFAULT_METRICS.requestsPerMonth);
      expect(result.average_latency).toBe(DEFAULT_METRICS.averageLatency);
      expect(result.industry).toBe('Technology');
    });
  });

  describe('mapApiResponseToSavings', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should map API response to savings structure correctly', () => {
      const apiResponse = createMockAPIResponse();
      const metrics = createTestMetrics({ currentMonthlySpend: 50000 });
      
      const result = mapApiResponseToSavings(apiResponse, metrics);
      
      const annualSavingsDiff = 600000 - 390000; // 210000
      const monthlySavings = 210000 / 12; // 17500
      
      expect(result.infrastructureCost).toBe((annualSavingsDiff / 12) * 0.7);
      expect(result.operationalCost).toBe((annualSavingsDiff / 12) * 0.2);
      expect(result.performanceGain).toBe((annualSavingsDiff / 12) * 0.1);
      expect(result.totalMonthlySavings).toBe(monthlySavings);
      expect(result.totalAnnualSavings).toBe(210000);
      expect(result.paybackPeriod).toBe(4);
    });

    it('should calculate three-year ROI from API data', () => {
      const apiResponse = createMockAPIResponse({
        three_year_tco_reduction: 750000
      });
      const metrics = createTestMetrics({ currentMonthlySpend: 25000 });
      
      const result = mapApiResponseToSavings(apiResponse, metrics);
      
      const expectedROI = (750000 / (25000 * 2)) * 100;
      expect(result.threeYearROI).toBe(expectedROI);
    });
  });

  describe('buildFallbackSavings - Enterprise Sales Critical', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should build complete fallback savings for Technology industry', () => {
      const metrics = createTestMetrics({
        currentMonthlySpend: 100000,
        requestsPerMonth: 50000000,
        teamSize: 25
      });
      
      const originalRandom = Math.random;
      Math.random = () => 0.5; // Consistent results
      
      const result = buildFallbackSavings(metrics, 'Technology');
      
      expect(result).toHaveProperty('infrastructureCost');
      expect(result).toHaveProperty('operationalCost');
      expect(result).toHaveProperty('performanceGain');
      expect(result).toHaveProperty('totalMonthlySavings');
      expect(result).toHaveProperty('totalAnnualSavings');
      expect(result).toHaveProperty('paybackPeriod');
      expect(result).toHaveProperty('threeYearROI');
      
      // Validate calculation accuracy for sales presentations
      const expectedOperational = 25 * 10000 * 0.25; // 62500
      const expectedPerformance = (50000000 / 1000000) * 500 * 0.6; // 15000
      
      expect(result.operationalCost).toBe(expectedOperational);
      expect(result.performanceGain).toBe(expectedPerformance);
      expect(result.totalAnnualSavings).toBe(result.totalMonthlySavings * 12);
      
      Math.random = originalRandom;
    });

    it('should apply correct industry multipliers for all industries', () => {
      const metrics = createTestMetrics({ currentMonthlySpend: 50000 });
      const originalRandom = Math.random;
      Math.random = () => 0.5;
      
      const techResult = buildFallbackSavings(metrics, 'Technology');
      const healthcareResult = buildFallbackSavings(metrics, 'Healthcare');
      const defaultResult = buildFallbackSavings(metrics, 'Unknown');
      
      expect(techResult.totalMonthlySavings).toBeGreaterThan(healthcareResult.totalMonthlySavings);
      expect(healthcareResult.totalMonthlySavings).toBeGreaterThan(defaultResult.totalMonthlySavings);
      
      Math.random = originalRandom;
    });
  });
});