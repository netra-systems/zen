import { Card, CardContent } from '@/components/ui/card'
import { ArrowUp, ArrowDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { MetricCard } from './MetricCard'
import { SystemHealth } from './SystemHealth'
import { metrics, realTimeMetrics } from './data'
import { RealTimeMetric } from './types'

function getRateUnit(label: string): string {
  return label.includes('Rate') ? '%' : ''
}

function getTrendColor(trend: string): string {
  return trend === 'up' ? 'text-green-600' : 'text-red-600'
}

function getTrendIcon(trend: string) {
  return trend === 'up' ? ArrowUp : ArrowDown
}

function RealTimeStatCard({ stat }: { stat: RealTimeMetric }) {
  const TrendIcon = getTrendIcon(stat.trend)
  const trendColor = getTrendColor(stat.trend)
  
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">{stat.label}</p>
            <p className="text-2xl font-bold">
              {stat.value}{getRateUnit(stat.label)}
            </p>
          </div>
          <div className={cn("text-xs font-medium", trendColor)}>
            <TrendIcon className="w-4 h-4" />
            {Math.abs(stat.change)}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function RealTimeStats() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="real-time-stats">
      {realTimeMetrics.map((stat, idx) => (
        <RealTimeStatCard key={idx} stat={stat} />
      ))}
    </div>
  )
}

function KeyMetricsGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="metrics-grid">
      {metrics.map((metric, idx) => (
        <MetricCard key={idx} metric={metric} />
      ))}
    </div>
  )
}

export function OverviewTab() {
  return (
    <div className="space-y-6">
      <RealTimeStats />
      <KeyMetricsGrid />
      <SystemHealth />
    </div>
  )
}