'use client'

import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { CheckCircle, AlertCircle, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { WorkflowStep, Agent } from './types'

interface WorkflowStepProps {
  step: WorkflowStep
  index: number
  agents: Agent[]
  isLast: boolean
}

export default function WorkflowStepComponent({ step, index, agents, isLast }: WorkflowStepProps) {
  const getStepIconClass = () => {
    return cn(
      "w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium",
      step.status === 'completed' && "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
      step.status === 'active' && "bg-primary text-primary-foreground animate-pulse",
      step.status === 'pending' && "bg-gray-100 text-gray-500 dark:bg-gray-800"
    )
  }

  const getConnectorClass = () => {
    return cn(
      "w-0.5 h-16 mt-1",
      step.status === 'completed' ? "bg-green-500" : "bg-gray-300 dark:bg-gray-700"
    )
  }

  const getAgentName = () => {
    return agents.find(a => a.id === step.agent)?.name
  }

  return (
    <div className="flex items-start gap-3">
      <div className="flex flex-col items-center">
        <div className={getStepIconClass()}>
          {step.status === 'completed' ? <CheckCircle className="w-4 h-4" /> : index + 1}
        </div>
        {!isLast && <div className={getConnectorClass()} />}
      </div>
      
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <h4 className={cn(
            "font-medium text-sm",
            step.status === 'active' && "text-primary"
          )}>
            {step.name}
          </h4>
          {step.duration && (
            <Badge variant="outline" className="text-xs">
              <Clock className="w-3 h-3 mr-1" />
              {step.duration}ms
            </Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground mb-1">
          Agent: {getAgentName()}
        </p>
        {step.output && (
          <Alert className="mt-2">
            <AlertCircle className="h-3 w-3" />
            <AlertDescription className="text-xs">
              {step.output}
            </AlertDescription>
          </Alert>
        )}
      </div>
    </div>
  )
}