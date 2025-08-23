import { useEffect, useRef, useCallback } from 'react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import type { 
  PerformanceMetrics, 
  MetricsOptions
} from '@/types/unified';
import { DEFAULT_PERFORMANCE_METRICS } from '@/types/unified';

export const usePerformanceMetrics = (
  componentName?: string, 
  options: MetricsOptions = {}
) => {
  const {
    trackMemory = true,
    trackFPS = true,
    trackComponents = true,
    updateInterval = 1000
  } = options;

  const metricsRef = useRef<PerformanceMetrics>({
    ...DEFAULT_PERFORMANCE_METRICS
  });

  const frameCountRef = useRef(0);
  const lastFrameTimeRef = useRef(performance.now());
  const renderStartRef = useRef<number>(0);
  const responseTimes = useRef<number[]>([]);

  // Track component render
  useEffect(() => {
    if (!trackComponents || !componentName) return;

    const renderStart = performance.now();
    renderStartRef.current = renderStart;
    metricsRef.current.renderCount++;

    return () => {
      const renderEnd = performance.now();
      const renderTime = renderEnd - renderStart;
      metricsRef.current.componentRenderTimes.set(
        componentName,
        renderTime
      );
      metricsRef.current.lastRenderTime = renderTime;
    };
  }, [componentName, trackComponents]);

  // Track FPS
  useEffect(() => {
    if (!trackFPS) return;

    let animationFrameId: number;
    
    const trackFrame = () => {
      frameCountRef.current++;
      const now = performance.now();
      const elapsed = now - lastFrameTimeRef.current;
      
      if (elapsed >= 1000) {
        metricsRef.current.fps = Math.round(
          (frameCountRef.current * 1000) / elapsed
        );
        frameCountRef.current = 0;
        lastFrameTimeRef.current = now;
      }
      
      animationFrameId = requestAnimationFrame(trackFrame);
    };
    
    animationFrameId = requestAnimationFrame(trackFrame);
    
    return () => cancelAnimationFrame(animationFrameId);
  }, [trackFPS]);

  // Track memory usage
  useEffect(() => {
    if (!trackMemory) return;

    const trackMemoryUsage = () => {
      if ('memory' in performance) {
        const memInfo = (performance as any).memory;
        metricsRef.current.memoryUsage = Math.round(
          memInfo.usedJSHeapSize / 1048576 // Convert to MB
        );
      }
    };

    const intervalId = setInterval(trackMemoryUsage, updateInterval);
    trackMemoryUsage(); // Initial measurement

    return () => clearInterval(intervalId);
  }, [trackMemory, updateInterval]);

  // Track WebSocket latency
  const trackWSLatency = useCallback((startTime: number) => {
    const latency = performance.now() - startTime;
    metricsRef.current.wsLatency = Math.round(latency);
    
    // Update average response time
    responseTimes.current.push(latency);
    if (responseTimes.current.length > 100) {
      responseTimes.current.shift();
    }
    
    const avg = responseTimes.current.reduce((a, b) => a + b, 0) / 
                responseTimes.current.length;
    metricsRef.current.averageResponseTime = Math.round(avg);
  }, []);

  // Track errors
  const trackError = useCallback(() => {
    metricsRef.current.errorCount++;
  }, []);

  // Track cache hit
  const trackCacheHit = useCallback((hit: boolean) => {
    // Simple cache hit rate calculation
    const total = metricsRef.current.renderCount;
    const currentRate = metricsRef.current.cacheHitRate;
    const newRate = ((currentRate * (total - 1)) + (hit ? 100 : 0)) / total;
    metricsRef.current.cacheHitRate = Math.round(newRate);
  }, []);

  // Get current metrics
  const getMetrics = useCallback((): PerformanceMetrics => {
    return { ...metricsRef.current };
  }, []);

  // Export metrics for debugging
  const exportMetrics = useCallback(() => {
    const metrics = getMetrics();
    const exportData = {
      timestamp: new Date().toISOString(),
      metrics,
      componentRenderTimes: Array.from(metrics.componentRenderTimes.entries()),
      userAgent: navigator.userAgent,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      }
    };

    return JSON.stringify(exportData, null, 2);
  }, [getMetrics]);

  // Update store with metrics periodically
  useEffect(() => {
    const updateStore = () => {
      const store = useUnifiedChatStore.getState();
      if (store.performanceMetrics) {
        store.performanceMetrics = {
          ...store.performanceMetrics,
          ...metricsRef.current
        };
      }
    };

    const intervalId = setInterval(updateStore, updateInterval);
    return () => clearInterval(intervalId);
  }, [updateInterval]);

  return {
    metrics: metricsRef.current,
    trackWSLatency,
    trackError,
    trackCacheHit,
    getMetrics,
    exportMetrics
  };
};

// Global performance monitor
export class PerformanceMonitor {
  private static instance: PerformanceMonitor;
  private metrics: Map<string, PerformanceMetrics> = new Map();
  private observers: Set<(metrics: Map<string, PerformanceMetrics>) => void> = new Set();

  static getInstance(): PerformanceMonitor {
    if (!this.instance) {
      this.instance = new PerformanceMonitor();
    }
    return this.instance;
  }

  updateMetrics(component: string, metrics: Partial<PerformanceMetrics>) {
    const current = this.metrics.get(component) || {
      ...DEFAULT_PERFORMANCE_METRICS
    };

    this.metrics.set(component, { ...current, ...metrics });
    this.notifyObservers();
  }

  getMetrics(component?: string): PerformanceMetrics | Map<string, PerformanceMetrics> | null {
    if (component) {
      return this.metrics.get(component) || null;
    }
    return new Map(this.metrics);
  }

  subscribe(observer: (metrics: Map<string, PerformanceMetrics>) => void) {
    this.observers.add(observer);
    return () => this.observers.delete(observer);
  }

  private notifyObservers() {
    this.observers.forEach(observer => observer(new Map(this.metrics)));
  }

  exportReport(): string {
    const report = {
      timestamp: new Date().toISOString(),
      globalMetrics: {
        totalComponents: this.metrics.size,
        totalRenderCount: Array.from(this.metrics.values())
          .reduce((sum, m) => sum + m.renderCount, 0),
        averageFPS: Array.from(this.metrics.values())
          .reduce((sum, m, _, arr) => sum + m.fps / arr.length, 0),
        totalMemoryUsage: Array.from(this.metrics.values())
          .reduce((max, m) => Math.max(max, m.memoryUsage), 0)
      },
      componentMetrics: Array.from(this.metrics.entries()).map(([name, metrics]) => ({
        component: name,
        ...metrics,
        componentRenderTimes: Array.from(metrics.componentRenderTimes.entries())
      }))
    };

    return JSON.stringify(report, null, 2);
  }
}