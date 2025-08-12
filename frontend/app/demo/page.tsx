'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Sparkles, TrendingUp, Shield, Users, Zap, BarChart3, FileDown, PlayCircle, CheckCircle } from 'lucide-react'
import DemoChat from '@/components/demo/DemoChat'
import ROICalculator from '@/components/demo/ROICalculator'
import PerformanceMetrics from '@/components/demo/PerformanceMetrics'
import SyntheticDataViewer from '@/components/demo/SyntheticDataViewer'
import ImplementationRoadmap from '@/components/demo/ImplementationRoadmap'
import IndustrySelector from '@/components/demo/IndustrySelector'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

interface DemoStep {
  id: string
  title: string
  description: string
  icon: React.ReactNode
  status: 'pending' | 'active' | 'completed'
}

export default function EnterpriseDemo() {
  const router = useRouter()
  const { } = useAuthStore()
  const [activeTab, setActiveTab] = useState('overview')
  const [selectedIndustry, setSelectedIndustry] = useState<string>('')
  const [demoProgress, setDemoProgress] = useState(0)
  const [demoStarted, setDemoStarted] = useState(false)
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set())

  const demoSteps: DemoStep[] = [
    {
      id: 'industry',
      title: 'Industry Selection',
      description: 'Customize demo for your sector',
      icon: <Users className="w-4 h-4" />,
      status: selectedIndustry ? 'completed' : 'active'
    },
    {
      id: 'roi',
      title: 'ROI Analysis',
      description: 'Calculate your cost savings',
      icon: <TrendingUp className="w-4 h-4" />,
      status: completedSteps.has('roi') ? 'completed' : selectedIndustry ? 'active' : 'pending'
    },
    {
      id: 'chat',
      title: 'AI Optimization',
      description: 'Experience intelligent workload optimization',
      icon: <Sparkles className="w-4 h-4" />,
      status: completedSteps.has('chat') ? 'completed' : completedSteps.has('roi') ? 'active' : 'pending'
    },
    {
      id: 'metrics',
      title: 'Performance Metrics',
      description: 'View real-time improvements',
      icon: <BarChart3 className="w-4 h-4" />,
      status: completedSteps.has('metrics') ? 'completed' : completedSteps.has('chat') ? 'active' : 'pending'
    },
    {
      id: 'export',
      title: 'Export Report',
      description: 'Get your optimization plan',
      icon: <FileDown className="w-4 h-4" />,
      status: completedSteps.has('export') ? 'completed' : completedSteps.has('metrics') ? 'active' : 'pending'
    }
  ]

  useEffect(() => {
    const progress = (completedSteps.size / demoSteps.length) * 100
    setDemoProgress(progress)
  }, [completedSteps, demoSteps.length])

  const handleStepComplete = (stepId: string) => {
    setCompletedSteps(prev => new Set(prev).add(stepId))
    const stepIndex = demoSteps.findIndex(s => s.id === stepId)
    if (stepIndex < demoSteps.length - 1) {
      const nextStep = demoSteps[stepIndex + 1]
      if (nextStep.id === 'roi') setActiveTab('roi')
      if (nextStep.id === 'chat') setActiveTab('optimization')
      if (nextStep.id === 'metrics') setActiveTab('performance')
      if (nextStep.id === 'export') setActiveTab('roadmap')
    }
  }

  // Removed unused function - demo state handled inline

  const valueProps = [
    {
      icon: <TrendingUp className="w-5 h-5 text-green-500" />,
      title: '40-60% Cost Reduction',
      description: 'Optimize AI infrastructure spending'
    },
    {
      icon: <Zap className="w-5 h-5 text-yellow-500" />,
      title: '2-3x Performance Gain',
      description: 'Accelerate model inference and training'
    },
    {
      icon: <Shield className="w-5 h-5 text-blue-500" />,
      title: 'Enterprise Security',
      description: 'SOC2, HIPAA, GDPR compliant'
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-black">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-emerald-600 to-purple-600 bg-clip-text text-transparent">
                Enterprise AI Optimization Platform
              </h1>
              <p className="text-lg text-muted-foreground mt-2">
                Reduce costs by 40-60% while improving performance by 2-3x
              </p>
            </div>
            <Badge variant="outline" className="px-4 py-2">
              <Sparkles className="w-4 h-4 mr-2" />
              Live Demo
            </Badge>
          </div>

          {/* Value Propositions */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {valueProps.map((prop, idx) => (
              <Card key={idx} className="border-2 hover:border-primary transition-colors">
                <CardHeader className="pb-3">
                  <div className="flex items-center space-x-3">
                    {prop.icon}
                    <CardTitle className="text-lg">{prop.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{prop.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Demo Progress */}
          {demoStarted && (
            <Card className="mb-6">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Demo Progress</CardTitle>
              </CardHeader>
              <CardContent>
                <Progress value={demoProgress} className="mb-4" />
                <div className="flex justify-between">
                  {demoSteps.map((step) => (
                    <div
                      key={step.id}
                      className={cn(
                        "flex flex-col items-center text-xs",
                        step.status === 'completed' && "text-green-600",
                        step.status === 'active' && "text-primary font-semibold",
                        step.status === 'pending' && "text-muted-foreground"
                      )}
                    >
                      <div className={cn(
                        "rounded-full p-2 mb-1",
                        step.status === 'completed' && "bg-green-100 dark:bg-green-900",
                        step.status === 'active' && "bg-primary/10",
                        step.status === 'pending' && "bg-gray-100 dark:bg-gray-800"
                      )}>
                        {step.status === 'completed' ? <CheckCircle className="w-4 h-4" /> : step.icon}
                      </div>
                      <span className="text-center max-w-[80px]">{step.title}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Industry Selection (if not started) */}
        {!selectedIndustry && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Select Your Industry</CardTitle>
              <CardDescription>
                Customize the demo experience for your specific sector
              </CardDescription>
            </CardHeader>
            <CardContent>
              <IndustrySelector
                onSelect={(industry) => {
                  setSelectedIndustry(industry)
                  handleStepComplete('industry')
                  setDemoStarted(true)
                }}
              />
            </CardContent>
          </Card>
        )}

        {/* Main Demo Content */}
        {selectedIndustry && (
          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
            <TabsList className="grid grid-cols-6 w-full">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="roi">ROI Calculator</TabsTrigger>
              <TabsTrigger value="optimization">AI Chat</TabsTrigger>
              <TabsTrigger value="performance">Metrics</TabsTrigger>
              <TabsTrigger value="data">Data Insights</TabsTrigger>
              <TabsTrigger value="roadmap">Next Steps</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
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
                  </div>

                  <div className="flex justify-end space-x-4 pt-4">
                    <Button 
                      size="lg" 
                      onClick={() => setActiveTab('roi')}
                      className="glass-button-primary hover:shadow-lg"
                    >
                      <PlayCircle className="w-4 h-4 mr-2" />
                      Start ROI Analysis
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="roi">
              <ROICalculator 
                industry={selectedIndustry}
                onComplete={() => handleStepComplete('roi')}
              />
            </TabsContent>

            <TabsContent value="optimization">
              <DemoChat 
                industry={selectedIndustry}
                useWebSocket={true}
                onInteraction={() => {
                  if (!completedSteps.has('chat')) {
                    handleStepComplete('chat')
                  }
                }}
              />
            </TabsContent>

            <TabsContent value="performance">
              <PerformanceMetrics 
                industry={selectedIndustry}
                onView={() => handleStepComplete('metrics')}
              />
            </TabsContent>

            <TabsContent value="data">
              <SyntheticDataViewer industry={selectedIndustry} />
            </TabsContent>

            <TabsContent value="roadmap">
              <ImplementationRoadmap 
                industry={selectedIndustry}
                completedSteps={Array.from(completedSteps)}
                onExport={() => handleStepComplete('export')}
              />
            </TabsContent>
          </Tabs>
        )}

        {/* Completion Card */}
        {demoProgress === 100 && (
          <Card className="mt-6 border-green-500 bg-green-50 dark:bg-green-950">
            <CardHeader>
              <CardTitle className="text-green-700 dark:text-green-300">
                <CheckCircle className="w-5 h-5 inline mr-2" />
                Demo Complete!
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4">
                Congratulations! You&apos;ve experienced the full power of our AI Optimization Platform.
              </p>
              <div className="flex space-x-4">
                <Button onClick={() => router.push('/chat')}>
                  Try Live System
                </Button>
                <Button variant="outline">
                  Schedule Deep Dive
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}