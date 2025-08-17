export interface AgentOrchestrationProps {
  industry?: string
}

export interface Agent {
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

export interface WorkflowStep {
  id: string
  name: string
  agent: string
  status: 'pending' | 'active' | 'completed'
  duration?: number
  output?: string
}

export interface WorkflowState {
  isRunning: boolean
  currentStep: number
  agents: Agent[]
  workflowSteps: WorkflowStep[]
}