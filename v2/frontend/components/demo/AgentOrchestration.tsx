'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Bot,
  Brain,
  Zap,
  Users,
  Activity,
  GitBranch,
  ArrowRight,
  Play,
  Pause,
  RotateCcw,
  CheckCircle,
  AlertCircle,
  Clock,
  Cpu
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface AgentOrchestrationProps {
  industry?: string
}

interface Agent {
  id: string
  name: string
  role: string
  status: 'idle' | 'active' | 'processing' | 'completed' | 'error'
  icon: React.ReactNode
  color: string
  tasks: number
  completedTasks: number
  processingTime?: number
  confidence?: number
}

interface WorkflowStep {
  id: string
  name: string
  agent: string
  status: 'pending' | 'active' | 'completed'
  duration?: number
  output?: string
}

export default function AgentOrchestration({ industry = 'Technology' }: AgentOrchestrationProps) {
  const [isRunning, setIsRunning] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [agents, setAgents] = useState<Agent[]>([
    {
      id: 'supervisor',
      name: 'Supervisor Agent',
      role: 'Orchestrates and coordinates all sub-agents',
      status: 'idle',
      icon: <Users className="w-5 h-5" />,
      color: 'text-purple-600',
      tasks: 0,
      completedTasks: 0
    },
    {
      id: 'triage',
      name: 'Triage Agent',
      role: 'Analyzes requests and routes to appropriate agents',
      status: 'idle',
      icon: <GitBranch className="w-5 h-5" />,
      color: 'text-blue-600',
      tasks: 0,
      completedTasks: 0
    },
    {
      id: 'analysis',
      name: 'Analysis Agent',
      role: 'Deep workload pattern analysis and insights',
      status: 'idle',
      icon: <Brain className="w-5 h-5" />,
      color: 'text-green-600',
      tasks: 0,
      completedTasks: 0
    },
    {
      id: 'optimization',
      name: 'Optimization Agent',
      role: 'Cost and performance optimization strategies',
      status: 'idle',
      icon: <Zap className="w-5 h-5" />,
      color: 'text-yellow-600',
      tasks: 0,
      completedTasks: 0
    },
    {
      id: 'reporting',
      name: 'Reporting Agent',
      role: 'Executive insights and report generation',
      status: 'idle',
      icon: <Activity className="w-5 h-5" />,
      color: 'text-red-600',
      tasks: 0,
      completedTasks: 0
    }
  ])

  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStep[]>([
    {
      id: '1',
      name: 'Request Reception',
      agent: 'supervisor',
      status: 'pending'
    },
    {
      id: '2',
      name: 'Request Triage',
      agent: 'triage',
      status: 'pending'
    },
    {
      id: '3',
      name: 'Workload Analysis',
      agent: 'analysis',
      status: 'pending'
    },
    {
      id: '4',
      name: 'Optimization Planning',
      agent: 'optimization',
      status: 'pending'
    },
    {
      id: '5',
      name: 'Report Generation',
      agent: 'reporting',
      status: 'pending'
    },
    {
      id: '6',
      name: 'Final Review',
      agent: 'supervisor',
      status: 'pending'
    }
  ])

  const simulateWorkflow = async () => {
    setIsRunning(true)
    
    for (let i = 0; i < workflowSteps.length; i++) {
      setCurrentStep(i)
      
      // Update step status
      setWorkflowSteps(prev => prev.map((step, idx) => ({
        ...step,
        status: idx < i ? 'completed' : idx === i ? 'active' : 'pending'
      })))
      
      // Update agent status
      const agentId = workflowSteps[i].agent
      setAgents(prev => prev.map(agent => ({
        ...agent,
        status: agent.id === agentId ? 'processing' : 
                i > 0 && agent.id === workflowSteps[i-1].agent ? 'completed' : 
                agent.status,
        tasks: agent.id === agentId ? agent.tasks + 1 : agent.tasks,
        processingTime: agent.id === agentId ? Math.floor(Math.random() * 2000) + 500 : agent.processingTime,
        confidence: agent.id === agentId ? 85 + Math.floor(Math.random() * 15) : agent.confidence
      })))
      
      // Simulate processing time
      await new Promise(resolve => setTimeout(resolve, 1500 + Math.random() * 1000))
      
      // Mark agent task as completed
      setAgents(prev => prev.map(agent => ({
        ...agent,
        completedTasks: agent.id === agentId ? agent.completedTasks + 1 : agent.completedTasks
      })))
      
      // Add output to step
      setWorkflowSteps(prev => prev.map((step, idx) => ({
        ...step,
        duration: idx === i ? Math.floor(Math.random() * 2000) + 500 : step.duration,
        output: idx === i ? generateStepOutput(step.name) : step.output
      })))
    }
    
    // Mark all as completed
    setWorkflowSteps(prev => prev.map(step => ({ ...step, status: 'completed' })))
    setAgents(prev => prev.map(agent => ({ ...agent, status: 'completed' })))
    setIsRunning(false)
  }

  const generateStepOutput = (stepName: string): string => {
    const outputs: Record<string, string> = {
      'Request Reception': 'Request validated and queued for processing',
      'Request Triage': `Identified as ${industry} optimization request, routing to specialized agents`,
      'Workload Analysis': 'Analyzed 10M+ data points, identified 3 optimization opportunities',
      'Optimization Planning': 'Generated optimization plan with 45% cost reduction potential',
      'Report Generation': 'Executive report created with actionable insights',
      'Final Review': 'All optimizations validated, ready for implementation'
    }
    return outputs[stepName] || 'Processing completed successfully'
  }

  const resetWorkflow = () => {
    setIsRunning(false)
    setCurrentStep(0)
    setAgents(prev => prev.map(agent => ({
      ...agent,
      status: 'idle',
      tasks: 0,
      completedTasks: 0,
      processingTime: undefined,
      confidence: undefined
    })))
    setWorkflowSteps(prev => prev.map(step => ({
      ...step,
      status: 'pending',
      duration: undefined,
      output: undefined
    })))
  }

  const totalTasks = agents.reduce((sum, agent) => sum + agent.tasks, 0)
  const completedTasks = agents.reduce((sum, agent) => sum + agent.completedTasks, 0)
  const progress = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0

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
                <Button onClick={simulateWorkflow} className="bg-gradient-to-r from-blue-600 to-purple-600">
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
                <Card key={agent.id} className={cn(
                  "transition-all",
                  agent.status === 'processing' && "border-primary shadow-md"
                )}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <div className={cn("p-2 rounded-lg", 
                          agent.status === 'processing' && "bg-primary/10 animate-pulse",
                          agent.status === 'completed' && "bg-green-100 dark:bg-green-900",
                          agent.status === 'idle' && "bg-gray-100 dark:bg-gray-800"
                        )}>
                          <span className={agent.color}>{agent.icon}</span>
                        </div>
                        <div>
                          <h4 className="font-medium text-sm">{agent.name}</h4>
                          <p className="text-xs text-muted-foreground">{agent.role}</p>
                        </div>
                      </div>
                      <Badge variant={
                        agent.status === 'processing' ? 'default' :
                        agent.status === 'completed' ? 'success' :
                        'outline'
                      }>
                        {agent.status}
                      </Badge>
                    </div>
                    
                    {agent.tasks > 0 && (
                      <div className="space-y-2 mt-3 pt-3 border-t">
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground">Tasks:</span>
                          <span>{agent.completedTasks}/{agent.tasks}</span>
                        </div>
                        {agent.processingTime && (
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">Processing:</span>
                            <span>{agent.processingTime}ms</span>
                          </div>
                        )}
                        {agent.confidence && (
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">Confidence:</span>
                            <span className="font-medium">{agent.confidence}%</span>
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
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
                <div key={step.id} className="flex items-start gap-3">
                  <div className="flex flex-col items-center">
                    <div className={cn(
                      "w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium",
                      step.status === 'completed' && "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
                      step.status === 'active' && "bg-primary text-primary-foreground animate-pulse",
                      step.status === 'pending' && "bg-gray-100 text-gray-500 dark:bg-gray-800"
                    )}>
                      {step.status === 'completed' ? <CheckCircle className="w-4 h-4" /> : idx + 1}
                    </div>
                    {idx < workflowSteps.length - 1 && (
                      <div className={cn(
                        "w-0.5 h-16 mt-1",
                        step.status === 'completed' ? "bg-green-500" : "bg-gray-300 dark:bg-gray-700"
                      )} />
                    )}
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
                      Agent: {agents.find(a => a.id === step.agent)?.name}
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
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Decision Transparency */}
      {completedTasks === totalTasks && totalTasks > 0 && (
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
                <p className="text-lg font-bold">
                  {agents.reduce((sum, a) => sum + (a.processingTime || 0), 0)}ms
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Agents Involved</p>
                <p className="text-lg font-bold">{agents.filter(a => a.tasks > 0).length}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Tasks Completed</p>
                <p className="text-lg font-bold">{completedTasks}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Avg Confidence</p>
                <p className="text-lg font-bold">
                  {Math.round(agents.reduce((sum, a) => sum + (a.confidence || 0), 0) / agents.filter(a => a.confidence).length)}%
                </p>
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
      )}
    </div>
  )
}