'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { Bot, Play, Pause, RotateCcw } from 'lucide-react'
import { AgentOrchestrationProps } from './agent-orchestration/types'
import { getInitialAgents, getInitialWorkflowSteps } from './agent-orchestration/data'
import {
  updateStepStatus,
  updateAgentProcessing,
  completeAgentTask,
  updateStepOutput,
  finalizeWorkflow,
  resetWorkflowState,
  calculateProgress,
  getProcessingDelay
} from './agent-orchestration/workflow-logic'
import AgentCard from './agent-orchestration/agent-card'
import WorkflowStepComponent from './agent-orchestration/workflow-step'
import CompletionSummary from './agent-orchestration/completion-summary'

export default function AgentOrchestration({ industry = 'Technology' }: AgentOrchestrationProps) {
  const [isRunning, setIsRunning] = useState(false)
  const [, setCurrentStep] = useState(0)
  const [agents, setAgents] = useState(getInitialAgents())
  const [workflowSteps, setWorkflowSteps] = useState(getInitialWorkflowSteps())

  const processWorkflowStep = async (stepIndex: number) => {
    const agentId = workflowSteps[stepIndex].agent
    const prevAgentId = stepIndex > 0 ? workflowSteps[stepIndex - 1].agent : undefined
    
    setWorkflowSteps(prev => updateStepStatus(prev, stepIndex))
    setAgents(prev => updateAgentProcessing(prev, agentId, prevAgentId))
    
    await new Promise(resolve => setTimeout(resolve, getProcessingDelay()))
    
    setAgents(prev => completeAgentTask(prev, agentId))
    setWorkflowSteps(prev => updateStepOutput(prev, stepIndex, workflowSteps[stepIndex].name, industry))
  }

  const simulateWorkflow = async () => {
    setIsRunning(true)
    
    for (let i = 0; i < workflowSteps.length; i++) {
      setCurrentStep(i)
      await processWorkflowStep(i)
    }
    
    const { steps, agents: finalAgents } = finalizeWorkflow(workflowSteps, agents)
    setWorkflowSteps(steps)
    setAgents(finalAgents)
    setIsRunning(false)
  }

  const resetWorkflow = () => {
    setIsRunning(false)
    setCurrentStep(0)
    const { agents: resetAgents, steps: resetSteps } = resetWorkflowState(agents, workflowSteps)
    setAgents(resetAgents)
    setWorkflowSteps(resetSteps)
  }

  const { total: totalTasks, completed: completedTasks, progress } = calculateProgress(agents)

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Bot className="w-5 h-5" />
                Multi-Agent Orchestration
              </CardTitle>
              <CardDescription>
                Autonomous agents working together to optimize your AI workloads
              </CardDescription>
            </div>
            <div className="flex gap-2">
              {!isRunning ? (
                <Button onClick={simulateWorkflow} className="bg-gradient-to-r from-emerald-600 to-purple-600">
                  <Play className="w-4 h-4 mr-1" />
                  Start Workflow
                </Button>
              ) : (
                <Button variant="outline" disabled>
                  <Pause className="w-4 h-4 mr-1" />
                  Running...
                </Button>
              )}
              <Button variant="outline" onClick={resetWorkflow}>
                <RotateCcw className="w-4 h-4 mr-1" />
                Reset
              </Button>
            </div>
          </div>
        </CardHeader>
        {isRunning && (
          <CardContent>
            <Progress value={progress} className="h-2" />
            <p className="text-xs text-muted-foreground mt-2">
              Processing: {completedTasks}/{totalTasks} tasks completed
            </p>
          </CardContent>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Agents Status */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Agent Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {agents.map((agent) => (
                <AgentCard key={agent.id} agent={agent} />
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Workflow Steps */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Workflow Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {workflowSteps.map((step, idx) => (
                <WorkflowStepComponent 
                  key={step.id} 
                  step={step} 
                  index={idx} 
                  agents={agents} 
                  isLast={idx === workflowSteps.length - 1}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Decision Transparency */}
      <CompletionSummary 
        agents={agents}
        completedTasks={completedTasks}
        totalTasks={totalTasks}
        industry={industry}
      />
    </div>
  )
}