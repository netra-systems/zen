import { Metric, Benchmark, RealTimeMetric } from './types'

export const metrics: Metric[] = [
  {
    label: 'Inference Latency',
    current: 250,
    optimized: 95,
    unit: 'ms',
    improvement: 62,
    status: 'improved'
  },
  {
    label: 'Throughput',
    current: 1000,
    optimized: 2800,
    unit: 'req/s',
    improvement: 180,
    status: 'improved'
  },
  {
    label: 'Cost per 1M Requests',
    current: 450,
    optimized: 180,
    unit: '$',
    improvement: 60,
    status: 'improved'
  },
  {
    label: 'Model Accuracy',
    current: 92.5,
    optimized: 94.2,
    unit: '%',
    improvement: 1.8,
    status: 'improved'
  },
  {
    label: 'GPU Utilization',
    current: 45,
    optimized: 85,
    unit: '%',
    improvement: 89,
    status: 'improved'
  },
  {
    label: 'Memory Usage',
    current: 32,
    optimized: 18,
    unit: 'GB',
    improvement: 44,
    status: 'improved'
  }
]

export const benchmarks: Benchmark[] = [
  { name: 'BERT Inference', score: 95, percentile: 98, category: 'NLP' },
  { name: 'ResNet-50', score: 92, percentile: 95, category: 'Vision' },
  { name: 'GPT-3.5 Turbo', score: 88, percentile: 92, category: 'Generation' },
  { name: 'Whisper Large', score: 90, percentile: 94, category: 'Audio' }
]

export const realTimeMetrics: RealTimeMetric[] = [
  { label: 'Active Models', value: 12, change: 2, trend: 'up' },
  { label: 'Queue Depth', value: 145, change: -23, trend: 'down' },
  { label: 'Error Rate', value: 0.02, change: -0.01, trend: 'down' },
  { label: 'Cache Hit Rate', value: 87, change: 5, trend: 'up' }
]