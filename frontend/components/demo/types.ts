export interface PerformanceMetricsProps {
  industry: string
  onView?: () => void
}

export interface Metric {
  label: string
  current: number
  optimized: number
  unit: string
  improvement: number
  status: 'improved' | 'degraded' | 'neutral'
}

export interface Benchmark {
  name: string
  score: number
  percentile: number
  category: string
}

export interface RealTimeMetric {
  label: string
  value: number
  change: number
  trend: 'up' | 'down'
}