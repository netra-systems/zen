/**
 * ROI Calculator Input Form Component
 * Business Value: Enterprise metrics input for ROI calculation
 */

import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { DollarSign, Info } from 'lucide-react'
import { Metrics, INDUSTRY_MULTIPLIERS } from './ROICalculator.types'

interface ROIInputFormProps {
  metrics: Metrics
  industry: string
  onMetricsChange: (metrics: Metrics) => void
}

const updateCurrentSpend = (metrics: Metrics, value: number, onChange: (m: Metrics) => void): void => {
  onChange({ ...metrics, currentMonthlySpend: value })
}

const updateRequests = (metrics: Metrics, value: number, onChange: (m: Metrics) => void): void => {
  onChange({ ...metrics, requestsPerMonth: value })
}

const updateTeamSize = (metrics: Metrics, value: number, onChange: (m: Metrics) => void): void => {
  onChange({ ...metrics, teamSize: value })
}

const updateLatency = (metrics: Metrics, value: number, onChange: (m: Metrics) => void): void => {
  onChange({ ...metrics, averageLatency: value })
}

const updateAccuracy = (metrics: Metrics, value: number, onChange: (m: Metrics) => void): void => {
  onChange({ ...metrics, modelAccuracy: value })
}

export default function ROIInputForm({ metrics, industry, onMetricsChange }: ROIInputFormProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="spend">Current Monthly AI Infrastructure Spend</Label>
          <div className="flex items-center space-x-2">
            <DollarSign className="w-4 h-4 text-muted-foreground" />
            <Input
              id="spend"
              type="number"
              value={metrics.currentMonthlySpend}
              onChange={(e) => updateCurrentSpend(metrics, Number(e.target.value), onMetricsChange)}
              className="flex-1"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Include compute, storage, and API costs
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="requests">Monthly AI Requests</Label>
          <Input
            id="requests"
            type="number"
            value={metrics.requestsPerMonth}
            onChange={(e) => updateRequests(metrics, Number(e.target.value), onMetricsChange)}
          />
          <p className="text-xs text-muted-foreground">
            Total inference and training requests
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="team">AI/ML Team Size</Label>
          <div className="flex items-center space-x-4">
            <Slider
              id="team"
              min={1}
              max={50}
              step={1}
              value={[metrics.teamSize]}
              onValueChange={(value) => updateTeamSize(metrics, value[0], onMetricsChange)}
              className="flex-1"
            />
            <span className="w-12 text-right font-medium">{metrics.teamSize}</span>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="latency">Average Latency (ms)</Label>
          <div className="flex items-center space-x-4">
            <Slider
              id="latency"
              min={50}
              max={1000}
              step={10}
              value={[metrics.averageLatency]}
              onValueChange={(value) => updateLatency(metrics, value[0], onMetricsChange)}
              className="flex-1"
            />
            <span className="w-16 text-right font-medium">{metrics.averageLatency}ms</span>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="accuracy">Model Accuracy (%)</Label>
          <div className="flex items-center space-x-4">
            <Slider
              id="accuracy"
              min={70}
              max={99}
              step={1}
              value={[metrics.modelAccuracy]}
              onValueChange={(value) => updateAccuracy(metrics, value[0], onMetricsChange)}
              className="flex-1"
            />
            <span className="w-12 text-right font-medium">{metrics.modelAccuracy}%</span>
          </div>
        </div>

        <Alert className="mt-4">
          <Info className="h-4 w-4" />
          <AlertDescription>
            Industry multiplier applied: <strong>{industry}</strong> ({((INDUSTRY_MULTIPLIERS[industry] || 1.0) - 1) * 100}% boost)
          </AlertDescription>
        </Alert>
      </div>
    </div>
  )
}