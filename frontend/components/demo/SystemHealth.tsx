import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Cpu, HardDrive, Server, Network } from 'lucide-react'

interface SystemMetric {
  icon: any
  label: string
  value: number
}

function getSystemMetrics(): SystemMetric[] {
  return [
    { icon: Cpu, label: 'CPU Usage', value: 65 },
    { icon: HardDrive, label: 'Memory', value: 42 },
    { icon: Server, label: 'GPU Utilization', value: 85 },
    { icon: Network, label: 'Network I/O', value: 58 }
  ]
}

function SystemMetricRow({ metric }: { metric: SystemMetric }) {
  const Icon = metric.icon
  
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4 text-muted-foreground" />
        <span className="text-sm">{metric.label}</span>
      </div>
      <div className="flex items-center gap-2 flex-1 max-w-xs ml-4">
        <Progress value={metric.value} className="flex-1" />
        <span className="text-sm font-medium">{metric.value}%</span>
      </div>
    </div>
  )
}

export function SystemHealth() {
  const systemMetrics = getSystemMetrics()
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">System Health</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {systemMetrics.map((metric, idx) => (
            <SystemMetricRow key={idx} metric={metric} />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}