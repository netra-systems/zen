import { Users, GitBranch, Brain, Zap, Activity } from 'lucide-react'
import { Agent, WorkflowStep } from './types'

export const getInitialAgents = (): Agent[] => [
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
]

export const getInitialWorkflowSteps = (): WorkflowStep[] => [
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
]