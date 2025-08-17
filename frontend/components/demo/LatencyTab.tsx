import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'

interface LatencyStage {
  name: string
  p50: number
  p95: number
  p99: number
  progress: number
}

function getLatencyStages(): LatencyStage[] {
  const stages = ['Model Loading', 'Preprocessing', 'Inference', 'Postprocessing']
  return stages.map(stage => ({
    name: stage,
    p50: Math.floor(20 + Math.random() * 30),
    p95: Math.floor(50 + Math.random() * 50),
    p99: Math.floor(100 + Math.random() * 100),
    progress: Math.random() * 100
  }))
}

function LatencyMetrics({ stage }: { stage: LatencyStage }) {
  return (
    <div className="flex gap-4 text-xs">
      <span>P50: {stage.p50}ms</span>
      <span>P95: {stage.p95}ms</span>
      <span>P99: {stage.p99}ms</span>
    </div>
  )
}

function LatencyStageRow({ stage }: { stage: LatencyStage }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{stage.name}</span>
        <LatencyMetrics stage={stage} />
      </div>
      <Progress value={stage.progress} className="h-2" />
    </div>
  )
}

export function LatencyTab() {
  const latencyStages = getLatencyStages()
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Latency Breakdown</CardTitle>
        <CardDescription>P50, P95, and P99 latencies across different operations</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {latencyStages.map((stage) => (
            <LatencyStageRow key={stage.name} stage={stage} />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}