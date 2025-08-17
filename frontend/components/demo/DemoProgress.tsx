'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Users, TrendingUp, Sparkles, BarChart3, FileDown, CheckCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface DemoStep {
  id: string
  title: string
  description: string
  icon: React.ReactNode
  status: 'pending' | 'active' | 'completed'
}

interface DemoProgressProps {
  demoProgress: number
  completedSteps: Set<string>
  selectedIndustry: string
  demoStarted: boolean
}

export default function DemoProgress({ 
  demoProgress, 
  completedSteps, 
  selectedIndustry, 
  demoStarted 
}: DemoProgressProps) {
  
  const createDemoSteps = (): DemoStep[] => [
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

  const getStepIconStyle = (status: string): string => {
    if (status === 'completed') return 'bg-green-100 dark:bg-green-900'
    if (status === 'active') return 'bg-primary/10'
    return 'bg-gray-100 dark:bg-gray-800'
  }

  const getStepTextStyle = (status: string): string => {
    if (status === 'completed') return 'text-green-600'
    if (status === 'active') return 'text-primary font-semibold'
    return 'text-muted-foreground'
  }

  const renderStepIcon = (step: DemoStep) => (
    <div className={cn('rounded-full p-2 mb-1', getStepIconStyle(step.status))}>
      {step.status === 'completed' ? <CheckCircle className="w-4 h-4" /> : step.icon}
    </div>
  )

  const renderStep = (step: DemoStep) => (
    <div
      key={step.id}
      className={cn('flex flex-col items-center text-xs', getStepTextStyle(step.status))}
    >
      {renderStepIcon(step)}
      <span className="text-center max-w-[80px]">{step.title}</span>
    </div>
  )

  if (!demoStarted) return null

  return (
    <Card className="mb-6">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Demo Progress</CardTitle>
      </CardHeader>
      <CardContent>
        <Progress value={demoProgress} className="mb-4" />
        <div className="flex justify-between">
          {createDemoSteps().map(renderStep)}
        </div>
      </CardContent>
    </Card>
  )
}