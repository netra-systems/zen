import { Agent, WorkflowStep } from './types'

const getStepOutputMap = (industry: string): Record<string, string> => ({
  'Request Reception': 'Request validated and queued for processing',
  'Request Triage': `Identified as ${industry} optimization request, routing to specialized agents`,
  'Workload Analysis': 'Analyzed 10M+ data points, identified 3 optimization opportunities',
  'Optimization Planning': 'Generated optimization plan with 45% cost reduction potential',
  'Report Generation': 'Executive report created with actionable insights',
  'Final Review': 'All optimizations validated, ready for implementation'
})

export const generateStepOutput = (stepName: string, industry: string): string => {
  const outputs = getStepOutputMap(industry)
  return outputs[stepName] || 'Processing completed successfully'
}

export const updateStepStatus = (
  steps: WorkflowStep[], 
  currentIndex: number
): WorkflowStep[] => {
  return steps.map((step, idx) => ({
    ...step,
    status: idx < currentIndex ? 'completed' : 
            idx === currentIndex ? 'active' : 'pending'
  }))
}

const getAgentStatus = (agentId: string, targetAgentId: string, prevAgentId?: string): string => {
  if (agentId === targetAgentId) return 'processing'
  if (prevAgentId && agentId === prevAgentId) return 'completed'
  return 'idle'
}

const generateRandomStats = () => ({
  processingTime: Math.floor(Math.random() * 2000) + 500,
  confidence: 85 + Math.floor(Math.random() * 15)
})

export const updateAgentProcessing = (
  agents: Agent[], 
  agentId: string, 
  prevAgentId?: string
): Agent[] => {
  return agents.map(agent => {
    const stats = agent.id === agentId ? generateRandomStats() : {}
    return {
      ...agent,
      status: getAgentStatus(agent.id, agentId, prevAgentId) as any,
      tasks: agent.id === agentId ? agent.tasks + 1 : agent.tasks,
      processingTime: agent.id === agentId ? stats.processingTime : agent.processingTime,
      confidence: agent.id === agentId ? stats.confidence : agent.confidence
    }
  })
}

export const completeAgentTask = (agents: Agent[], agentId: string): Agent[] => {
  return agents.map(agent => ({
    ...agent,
    completedTasks: agent.id === agentId ? agent.completedTasks + 1 : agent.completedTasks
  }))
}

const generateStepStats = () => ({
  duration: Math.floor(Math.random() * 2000) + 500
})

export const updateStepOutput = (
  steps: WorkflowStep[], 
  stepIndex: number, 
  stepName: string, 
  industry: string
): WorkflowStep[] => {
  return steps.map((step, idx) => {
    const stats = idx === stepIndex ? generateStepStats() : {}
    return {
      ...step,
      duration: idx === stepIndex ? stats.duration : step.duration,
      output: idx === stepIndex ? generateStepOutput(stepName, industry) : step.output
    }
  })
}

export const finalizeWorkflow = (
  steps: WorkflowStep[], 
  agents: Agent[]
): { steps: WorkflowStep[], agents: Agent[] } => {
  const finalSteps = steps.map(step => ({ ...step, status: 'completed' as const }))
  const finalAgents = agents.map(agent => ({ ...agent, status: 'completed' as const }))
  return { steps: finalSteps, agents: finalAgents }
}

const resetAgent = (agent: Agent): Agent => ({
  ...agent,
  status: 'idle' as const,
  tasks: 0,
  completedTasks: 0,
  processingTime: undefined,
  confidence: undefined
})

const resetStep = (step: WorkflowStep): WorkflowStep => ({
  ...step,
  status: 'pending' as const,
  duration: undefined,
  output: undefined
})

export const resetWorkflowState = (
  agents: Agent[], 
  steps: WorkflowStep[]
): { agents: Agent[], steps: WorkflowStep[] } => {
  const resetAgents = agents.map(resetAgent)
  const resetSteps = steps.map(resetStep)
  return { agents: resetAgents, steps: resetSteps }
}

export const calculateProgress = (agents: Agent[]): { total: number, completed: number, progress: number } => {
  const totalTasks = agents.reduce((sum, agent) => sum + agent.tasks, 0)
  const completedTasks = agents.reduce((sum, agent) => sum + agent.completedTasks, 0)
  const progress = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0
  return { total: totalTasks, completed: completedTasks, progress }
}

export const getProcessingDelay = (): number => {
  return 1500 + Math.random() * 1000
}