'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { CheckCircle, Cpu } from 'lucide-react'
import { Agent } from './types'

interface CompletionSummaryProps {
  agents: Agent[]
  completedTasks: number
  totalTasks: number
  industry: string
}

export default function CompletionSummary({ 
  agents, 
  completedTasks, 
  totalTasks, 
  industry 
}: CompletionSummaryProps) {
  const getTotalProcessingTime = () => {
    return agents.reduce((sum, a) => sum + (a.processingTime || 0), 0)
  }

  const getActiveAgentsCount = () => {
    return agents.filter(a => a.tasks > 0).length
  }

  const getAverageConfidence = () => {
    const confidenceAgents = agents.filter(a => a.confidence)
    const totalConfidence = confidenceAgents.reduce((sum, a) => sum + (a.confidence || 0), 0)
    return confidenceAgents.length > 0 ? Math.round(totalConfidence / confidenceAgents.length) : 0
  }

  if (completedTasks !== totalTasks || totalTasks === 0) {
    return null
  }

  return (
    <Card className="border-green-500">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-600" />
          Workflow Complete
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-muted-foreground">Total Processing Time</p>
            <p className="text-lg font-bold">{getTotalProcessingTime()}ms</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Agents Involved</p>
            <p className="text-lg font-bold">{getActiveAgentsCount()}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Tasks Completed</p>
            <p className="text-lg font-bold">{completedTasks}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Avg Confidence</p>
            <p className="text-lg font-bold">{getAverageConfidence()}%</p>
          </div>
        </div>
        
        <Alert className="mt-4">
          <Cpu className="h-4 w-4" />
          <AlertDescription>
            The multi-agent system successfully analyzed your {industry} workload and generated optimization strategies with high confidence. View the detailed report in the Implementation Roadmap.
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  )
}