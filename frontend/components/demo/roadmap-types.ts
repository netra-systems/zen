// Implementation Roadmap Types
// Module: TypeScript interfaces and types for roadmap functionality
// Max 300 lines, all functions ≤8 lines

export interface ImplementationRoadmapProps {
  industry: string
  completedSteps: string[]
  onExport?: () => void
}

export interface Phase {
  id: string
  name: string
  duration: string
  status: 'current' | 'upcoming' | 'completed'
  tasks: Task[]
  milestone: string
  risk: 'low' | 'medium' | 'high'
}

export interface Task {
  id: string
  title: string
  owner: string
  priority: 'critical' | 'high' | 'medium' | 'low'
  effort: string
}

export interface SupportOption {
  title: string
  description: string
  icon: React.ReactNode
  available: boolean
}

export interface RiskMitigation {
  risk: string
  mitigation: string
  severity: 'low' | 'medium' | 'high'
}

export interface ExportData {
  industry: string
  completedSteps: string[]
  phases: Phase[]
  supportOptions: SupportOption[]
  riskMitigations: RiskMitigation[]
  exportDate: string
  estimatedSavings: string
  implementationCost: string
}

export type ExportFormat = 'pdf' | 'json' | 'csv'

export type TabValue = 'phases' | 'tasks' | 'risks' | 'support'

export type RiskLevel = 'low' | 'medium' | 'high'

export type TaskPriority = 'critical' | 'high' | 'medium' | 'low'

export type PhaseStatus = 'current' | 'upcoming' | 'completed'