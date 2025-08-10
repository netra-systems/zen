'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Activity,
  TrendingUp,
  TrendingDown,
  Zap,
  Clock,
  DollarSign,
  Server,
  Cpu,
  HardDrive,
  Network,
  BarChart3,
  ArrowUp,
  ArrowDown,
  AlertCircle,
  CheckCircle,
  RefreshCw
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface PerformanceMetricsProps {
  industry: string
  onView?: () => void
}

interface Metric {
  label: string
  current: number
  optimized: number
  unit: string
  improvement: number
  status: 'improved' | 'degraded' | 'neutral'
}

interface Benchmark {
  name: string
  score: number
  percentile: number
  category: string
}

export default function PerformanceMetrics({ industry, onView }: PerformanceMetricsProps) {
  const [activeTab, setActiveTab] = useState('overview')
  const [isLoading, setIsLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(new Date())

  useEffect(() => {
    if (onView) {
      onView()
    }
    // Simulate loading metrics
    setTimeout(() => setIsLoading(false), 1500)
  }, [onView])

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        setLastUpdated(new Date())
      }, 5000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const metrics: Metric[] = [
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

  const benchmarks: Benchmark[] = [
    { name: 'BERT Inference', score: 95, percentile: 98, category: 'NLP' },
    { name: 'ResNet-50', score: 92, percentile: 95, category: 'Vision' },
    { name: 'GPT-3.5 Turbo', score: 88, percentile: 92, category: 'Generation' },
    { name: 'Whisper Large', score: 90, percentile: 94, category: 'Audio' }
  ]

  const realTimeMetrics = [
    { label: 'Active Models', value: 12, change: 2, trend: 'up' },
    { label: 'Queue Depth', value: 145, change: -23, trend: 'down' },
    { label: 'Error Rate', value: 0.02, change: -0.01, trend: 'down' },
    { label: 'Cache Hit Rate', value: 87, change: 5, trend: 'up' }
  ]

  const MetricCard = ({ metric }: { metric: Metric }) => {
    const isImproved = metric.status === 'improved'
    const Icon = isImproved ? TrendingUp : TrendingDown
    const color = isImproved ? 'text-green-600' : 'text-red-600'
    
    return (
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium">{metric.label}</CardTitle>
            <Badge variant={isImproved ? 'success' : 'destructive'} className="text-xs">
              {isImproved ? <ArrowUp className="w-3 h-3 mr-1" /> : <ArrowDown className="w-3 h-3 mr-1" />}
              {Math.abs(metric.improvement)}%
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
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
            <Progress 
              value={(metric.optimized / metric.current) * 100} 
              className="h-2"
            />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-[400px]">
          <div className="text-center space-y-4">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-primary" />
            <p className="text-muted-foreground">Loading performance metrics...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Performance Metrics Dashboard
              </CardTitle>
              <CardDescription>
                Real-time optimization metrics for {industry}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                <Clock className="w-3 h-3 mr-1" />
                Updated {lastUpdated.toLocaleTimeString()}
              </Badge>
              <Button
                variant={autoRefresh ? 'default' : 'outline'}
                size="sm"
                onClick={() => setAutoRefresh(!autoRefresh)}
              >
                <RefreshCw className={cn("w-4 h-4 mr-1", autoRefresh && "animate-spin")} />
                {autoRefresh ? 'Auto' : 'Manual'}
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="latency">Latency</TabsTrigger>
          <TabsTrigger value="cost">Cost Analysis</TabsTrigger>
          <TabsTrigger value="benchmarks">Benchmarks</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Real-time Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {realTimeMetrics.map((stat, idx) => (
              <Card key={idx}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-muted-foreground">{stat.label}</p>
                      <p className="text-2xl font-bold">
                        {stat.value}{stat.label.includes('Rate') ? '%' : ''}
                      </p>
                    </div>
                    <div className={cn(
                      "text-xs font-medium",
                      stat.trend === 'up' ? 'text-green-600' : 'text-red-600'
                    )}>
                      {stat.trend === 'up' ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
                      {Math.abs(stat.change)}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {metrics.map((metric, idx) => (
              <MetricCard key={idx} metric={metric} />
            ))}
          </div>

          {/* System Health */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">System Health</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">CPU Usage</span>
                  </div>
                  <div className="flex items-center gap-2 flex-1 max-w-xs ml-4">
                    <Progress value={65} className="flex-1" />
                    <span className="text-sm font-medium">65%</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <HardDrive className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">Memory</span>
                  </div>
                  <div className="flex items-center gap-2 flex-1 max-w-xs ml-4">
                    <Progress value={42} className="flex-1" />
                    <span className="text-sm font-medium">42%</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Server className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">GPU Utilization</span>
                  </div>
                  <div className="flex items-center gap-2 flex-1 max-w-xs ml-4">
                    <Progress value={85} className="flex-1" />
                    <span className="text-sm font-medium">85%</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Network className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">Network I/O</span>
                  </div>
                  <div className="flex items-center gap-2 flex-1 max-w-xs ml-4">
                    <Progress value={58} className="flex-1" />
                    <span className="text-sm font-medium">58%</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="latency" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Latency Breakdown</CardTitle>
              <CardDescription>P50, P95, and P99 latencies across different operations</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {['Model Loading', 'Preprocessing', 'Inference', 'Postprocessing'].map((stage) => (
                  <div key={stage} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{stage}</span>
                      <div className="flex gap-4 text-xs">
                        <span>P50: {Math.floor(20 + Math.random() * 30)}ms</span>
                        <span>P95: {Math.floor(50 + Math.random() * 50)}ms</span>
                        <span>P99: {Math.floor(100 + Math.random() * 100)}ms</span>
                      </div>
                    </div>
                    <Progress value={Math.random() * 100} className="h-2" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="cost" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Cost Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Compute</span>
                    <span className="text-sm font-semibold">$12,500/mo</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Storage</span>
                    <span className="text-sm font-semibold">$2,300/mo</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Network</span>
                    <span className="text-sm font-semibold">$1,800/mo</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">API Calls</span>
                    <span className="text-sm font-semibold">$8,400/mo</span>
                  </div>
                  <div className="border-t pt-3 flex justify-between items-center">
                    <span className="text-sm font-medium">Total Optimized</span>
                    <span className="text-lg font-bold text-green-600">$25,000/mo</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Savings Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Month 1</span>
                    <span className="text-sm font-semibold text-green-600">+$15,000</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Month 3</span>
                    <span className="text-sm font-semibold text-green-600">+$45,000</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Month 6</span>
                    <span className="text-sm font-semibold text-green-600">+$90,000</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Year 1</span>
                    <span className="text-sm font-semibold text-green-600">+$180,000</span>
                  </div>
                  <div className="border-t pt-3 flex justify-between items-center">
                    <span className="text-sm font-medium">3-Year Total</span>
                    <span className="text-lg font-bold text-green-600">+$540,000</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="benchmarks" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Industry Benchmarks</CardTitle>
              <CardDescription>Performance compared to industry standards</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {benchmarks.map((benchmark, idx) => (
                  <div key={idx} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-sm font-medium">{benchmark.name}</span>
                        <Badge variant="outline" className="ml-2 text-xs">
                          {benchmark.category}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">
                          Top {100 - benchmark.percentile}%
                        </span>
                        <Badge variant="success">
                          {benchmark.score}/100
                        </Badge>
                      </div>
                    </div>
                    <Progress value={benchmark.score} className="h-2" />
                  </div>
                ))}
              </div>
              
              <div className="mt-6 p-4 bg-green-50 dark:bg-green-950 rounded-lg">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <p className="text-sm font-medium">
                    Your optimized system ranks in the top 5% for {industry} workloads
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}