import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { TrendingUp, TrendingDown, ArrowUp, ArrowDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Metric } from './types'

function getMetricIcon(isImproved: boolean) {
  return isImproved ? TrendingUp : TrendingDown
}

function getMetricColor(isImproved: boolean) {
  return isImproved ? 'text-green-600' : 'text-red-600'
}

function getArrowIcon(isImproved: boolean) {
  return isImproved ? ArrowUp : ArrowDown
}

function getBadgeVariant(isImproved: boolean) {
  return isImproved ? 'secondary' : 'destructive'
}

function calculateProgress(metric: Metric) {
  return (metric.optimized / metric.current) * 100
}

function MetricHeader({ metric, isImproved }: { metric: Metric; isImproved: boolean }) {
  const ArrowIcon = getArrowIcon(isImproved)
  
  return (
    <div className="flex items-center justify-between">
      <CardTitle className="text-sm font-medium">{metric.label}</CardTitle>
      <Badge variant={getBadgeVariant(isImproved)} className="text-xs">
        <ArrowIcon className="w-3 h-3 mr-1" />
        {Math.abs(metric.improvement)}%
      </Badge>
    </div>
  )
}

function MetricValues({ metric, Icon, color }: { metric: Metric; Icon: any; color: string }) {
  return (
    <div className="flex items-baseline justify-between">
      <div>
        <p className="text-xs text-muted-foreground">Current</p>
        <p className="text-lg font-semibold">{metric.current}{metric.unit}</p>
      </div>
      <Icon className={cn("w-5 h-5", color)} />
      <div className="text-right">
        <p className="text-xs text-muted-foreground">Optimized</p>
        <p className={cn("text-lg font-bold", color)}>{metric.optimized}{metric.unit}</p>
      </div>
    </div>
  )
}

export function MetricCard({ metric }: { metric: Metric }) {
  const isImproved = metric.status === 'improved'
  const Icon = getMetricIcon(isImproved)
  const color = getMetricColor(isImproved)
  
  return (
    <Card>
      <CardHeader className="pb-2">
        <MetricHeader metric={metric} isImproved={isImproved} />
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <MetricValues metric={metric} Icon={Icon} color={color} />
          <Progress value={calculateProgress(metric)} className="h-2" />
        </div>
      </CardContent>
    </Card>
  )
}