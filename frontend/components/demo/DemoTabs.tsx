'use client'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Sparkles, PlayCircle } from 'lucide-react'
import DemoChat from '@/components/demo/DemoChat'
import ROICalculator from '@/components/demo/ROICalculator'
import PerformanceMetrics from '@/components/demo/PerformanceMetrics'
import SyntheticDataViewer from '@/components/demo/SyntheticDataViewer'
import ImplementationRoadmap from '@/components/demo/ImplementationRoadmap'

interface DemoTabsProps {
  activeTab: string
  selectedIndustry: string
  completedSteps: Set<string>
  onTabChange: (tab: string) => void
  onStepComplete: (stepId: string) => void
}

export default function DemoTabs({
  activeTab,
  selectedIndustry,
  completedSteps,
  onTabChange,
  onStepComplete
}: DemoTabsProps) {

  const renderTabsList = () => (
    <TabsList className="grid grid-cols-6 w-full">
      <TabsTrigger value="overview">Overview</TabsTrigger>
      <TabsTrigger value="roi">ROI Calculator</TabsTrigger>
      <TabsTrigger value="optimization">AI Chat</TabsTrigger>
      <TabsTrigger value="performance">Metrics</TabsTrigger>
      <TabsTrigger value="data">Data Insights</TabsTrigger>
      <TabsTrigger value="roadmap">Next Steps</TabsTrigger>
    </TabsList>
  )

  const renderQuickStats = () => (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Quick Stats</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex justify-between">
            <span className="text-sm text-muted-foreground">Active Customers</span>
            <span className="font-semibold">2,500+</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-muted-foreground">Requests Optimized</span>
            <span className="font-semibold">10B+/month</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-muted-foreground">Average ROI</span>
            <span className="font-semibold text-green-600">380%</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )

  const renderIntegrationPartners = () => (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Integration Partners</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-2">
          {['OpenAI', 'Anthropic', 'AWS', 'Azure', 'GCP', 'Kubernetes'].map((partner) => (
            <Badge key={partner} variant="secondary" className="justify-center">
              {partner}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  )

  const renderOverviewContent = () => (
    <Card>
      <CardHeader>
        <CardTitle>Welcome to Netra AI Optimization Platform</CardTitle>
        <CardDescription>
          The enterprise-grade solution trusted by Fortune 500 companies
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Alert>
          <Sparkles className="h-4 w-4" />
          <AlertTitle>Personalized for {selectedIndustry}</AlertTitle>
          <AlertDescription>
            This demo has been customized with use cases and data patterns specific to your industry.
          </AlertDescription>
        </Alert>

        <div className="grid grid-cols-2 gap-4">
          {renderQuickStats()}
          {renderIntegrationPartners()}
        </div>

        <div className="flex justify-end space-x-4 pt-4">
          <Button 
            size="lg" 
            onClick={() => onTabChange('roi')}
            className="glass-button-primary hover:shadow-lg"
          >
            <PlayCircle className="w-4 h-4 mr-2" />
            Start ROI Analysis
          </Button>
        </div>
      </CardContent>
    </Card>
  )

  const handleChatInteraction = () => {
    if (!completedSteps.has('chat')) {
      onStepComplete('chat')
    }
  }

  return (
    <Tabs value={activeTab} onValueChange={onTabChange} className="space-y-6">
      {renderTabsList()}

      <TabsContent value="overview" className="space-y-6">
        {renderOverviewContent()}
      </TabsContent>

      <TabsContent value="roi">
        <ROICalculator 
          industry={selectedIndustry}
          onComplete={() => onStepComplete('roi')}
        />
      </TabsContent>

      <TabsContent value="optimization">
        <DemoChat 
          industry={selectedIndustry}
          useWebSocket={true}
          onInteraction={handleChatInteraction}
        />
      </TabsContent>

      <TabsContent value="performance">
        <PerformanceMetrics 
          industry={selectedIndustry}
          onView={() => onStepComplete('metrics')}
        />
      </TabsContent>

      <TabsContent value="data">
        <SyntheticDataViewer industry={selectedIndustry} />
      </TabsContent>

      <TabsContent value="roadmap">
        <ImplementationRoadmap 
          industry={selectedIndustry}
          completedSteps={Array.from(completedSteps)}
          onExport={() => onStepComplete('export')}
        />
      </TabsContent>
    </Tabs>
  )
}