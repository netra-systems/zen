/**
 * Performance Monitoring Integration Tests
 * Tests for tracking and reporting performance metrics
 */

import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import test utilities
import { TestProviders } from '../../test-utils/providers';

describe('Performance Monitoring Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Metrics Tracking', () => {
    it('should track and report performance metrics', async () => {
      const metrics = {
        websocket_latency: [] as number[],
        api_response_time: [] as number[],
        render_time: [] as number[]
      };
      
      const TestComponent = () => {
        const startTime = performance.now();
        
        React.useEffect(() => {
          const renderTime = performance.now() - startTime;
          metrics.render_time.push(renderTime);
        }, [startTime]);
        
        const measureApiCall = async () => {
          const start = performance.now();
          await fetch('/api/test');
          const duration = performance.now() - start;
          metrics.api_response_time.push(duration);
        };
        
        return (
          <div>
            <button onClick={measureApiCall}>API Call</button>
            <div data-testid="metrics">
              Render: {metrics.render_time[0]?.toFixed(2)}ms
            </div>
          </div>
        );
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      });
      
      const { getByText } = render(<TestComponent />);
      
      fireEvent.click(getByText('API Call'));
      
      await waitFor(() => {
        expect(metrics.api_response_time.length).toBeGreaterThan(0);
      });
    });

    it('should detect and report performance degradation', async () => {
      const performanceThresholds: Record<string, number> = {
        api_latency: 1000,
        websocket_latency: 100,
        render_time: 16
      };
      
      const checkPerformance = (metric: string, value: number) => {
        const threshold = performanceThresholds[metric];
        if (value > threshold) {
          // test debug removed: console.log(`Performance degradation: ${metric} = ${value}ms (threshold: ${threshold}ms)`);
          return false;
        }
        return true;
      };
      
      const slowApiCall = 1500;
      const result = checkPerformance('api_latency', slowApiCall);
      
      expect(result).toBe(false);
    });
  });
});