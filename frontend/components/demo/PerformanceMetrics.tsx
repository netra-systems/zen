'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Clock, BarChart3, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import { PerformanceMetricsProps } from './types'
import { OverviewTab } from './OverviewTab'
import { LatencyTab } from './LatencyTab'
import { CostTab } from './CostTab'
import { BenchmarksTab } from './BenchmarksTab'

function useAutoRefresh() {
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(new Date())
  
  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(() => {
      setLastUpdated(new Date())
    }, 5000)
    return () => clearInterval(interval)
  }, [autoRefresh])
  
  return { autoRefresh, setAutoRefresh, lastUpdated }
}

function useLoadingState(onView?: () => void) {
  const [isLoading, setIsLoading] = useState(true)
  
  useEffect(() => {
    if (onView) {
      onView()
    }
    setTimeout(() => setIsLoading(false), 1500)
  }, [onView])
  
  return isLoading
}

function LoadingCard() {
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

function HeaderCard({ industry, autoRefresh, setAutoRefresh, lastUpdated }: {
  industry: string
  autoRefresh: boolean
  setAutoRefresh: (value: boolean) => void
  lastUpdated: Date
}) {
  return (
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
  )
}

function TabsNavigation({ activeTab, setActiveTab }: {
  activeTab: string
  setActiveTab: (value: string) => void
}) {
  return (
    <TabsList className="grid w-full grid-cols-4">
      <TabsTrigger value="overview">Overview</TabsTrigger>
      <TabsTrigger value="latency">Latency</TabsTrigger>
      <TabsTrigger value="cost">Cost Analysis</TabsTrigger>
      <TabsTrigger value="benchmarks">Benchmarks</TabsTrigger>
    </TabsList>
  )
}

export default function PerformanceMetrics({ industry, onView }: PerformanceMetricsProps) {
  const [activeTab, setActiveTab] = useState('overview')
  const isLoading = useLoadingState(onView)
  const { autoRefresh, setAutoRefresh, lastUpdated } = useAutoRefresh()

  if (isLoading) {
    return <LoadingCard />
  }

  return (
    <div className="space-y-6">
      <HeaderCard 
        industry={industry} 
        autoRefresh={autoRefresh} 
        setAutoRefresh={setAutoRefresh} 
        lastUpdated={lastUpdated} 
      />
      
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsNavigation activeTab={activeTab} setActiveTab={setActiveTab} />
        
        <TabsContent value="overview" className="space-y-6">
          <OverviewTab />
        </TabsContent>
        
        <TabsContent value="latency" className="space-y-6">
          <LatencyTab />
        </TabsContent>
        
        <TabsContent value="cost" className="space-y-6">
          <CostTab />
        </TabsContent>
        
        <TabsContent value="benchmarks" className="space-y-6">
          <BenchmarksTab industry={industry} />
        </TabsContent>
      </Tabs>
    </div>
  )
}