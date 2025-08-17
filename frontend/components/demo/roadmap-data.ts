// Implementation Roadmap Data
// Module: Static data and configuration for roadmap functionality
// Max 300 lines, all functions ≤8 lines

import { 
  Phase, 
  SupportOption, 
  RiskMitigation 
} from './roadmap-types'
import { 
  Phone,
  Users,
  MessageSquare,
  FileText
} from 'lucide-react'

// Create phases data (≤8 lines per function)
export const createPhasesData = (): Phase[] => {
  return [
    createImmediatePhase(),
    createPilotPhase(),
    createScalingPhase(),
    createProductionPhase()
  ]
}

// Create immediate phase data (≤8 lines)
const createImmediatePhase = (): Phase => {
  return {
    id: 'immediate',
    name: 'Immediate Actions',
    duration: 'Week 1',
    status: 'current',
    tasks: createImmediateTasks(),
    milestone: 'Stakeholder alignment achieved',
    risk: 'low'
  }
}

// Create immediate tasks (≤8 lines)
const createImmediateTasks = () => {
  return [
    createTask('t1', 'Share optimization report with stakeholders', 'Project Lead', 'critical', '2 hours'),
    createTask('t2', 'Schedule technical deep-dive with engineering', 'Tech Lead', 'high', '1 hour'),
    createTask('t3', 'Identify pilot workloads for testing', 'Engineering', 'high', '4 hours')
  ]
}

// Create pilot phase data (≤8 lines)
const createPilotPhase = (): Phase => {
  return {
    id: 'pilot',
    name: 'Pilot Implementation',
    duration: 'Weeks 2-3',
    status: 'upcoming',
    tasks: createPilotTasks(),
    milestone: 'Pilot validation complete',
    risk: 'medium'
  }
}

// Create pilot tasks (≤8 lines)
const createPilotTasks = () => {
  return [
    createTask('t4', 'Deploy Netra agents in dev environment', 'DevOps', 'critical', '2 days'),
    createTask('t5', 'Configure monitoring and observability', 'SRE Team', 'high', '1 day'),
    createTask('t6', 'Run A/B tests with 10% traffic', 'Engineering', 'high', '3 days'),
    createTask('t7', 'Collect performance metrics', 'Data Team', 'medium', '2 days')
  ]
}

// Create scaling phase data (≤8 lines)
const createScalingPhase = (): Phase => {
  return {
    id: 'scaling',
    name: 'Gradual Scaling',
    duration: 'Weeks 4-6',
    status: 'upcoming',
    tasks: createScalingTasks(),
    milestone: 'Quarter production deployment',
    risk: 'medium'
  }
}

// Create scaling tasks (≤8 lines)
const createScalingTasks = () => {
  return [
    createTask('t8', 'Scale to 25% of production traffic', 'Engineering', 'critical', '3 days'),
    createTask('t9', 'Implement auto-scaling policies', 'DevOps', 'high', '2 days'),
    createTask('t10', 'Train team on Netra platform', 'Training Team', 'medium', '1 week')
  ]
}

// Create production phase data (≤8 lines)
const createProductionPhase = (): Phase => {
  return {
    id: 'production',
    name: 'Full Production',
    duration: 'Weeks 7-12',
    status: 'upcoming',
    tasks: createProductionTasks(),
    milestone: 'Full production deployment',
    risk: 'high'
  }
}

// Create production tasks (≤8 lines)
const createProductionTasks = () => {
  return [
    createTask('t11', 'Complete production rollout', 'Engineering', 'critical', '1 week'),
    createTask('t12', 'Optimize based on real-world data', 'ML Team', 'high', '2 weeks'),
    createTask('t13', 'Document best practices', 'Tech Writers', 'low', '3 days')
  ]
}

// Create task helper (≤8 lines)
const createTask = (
  id: string, 
  title: string, 
  owner: string, 
  priority: 'critical' | 'high' | 'medium' | 'low', 
  effort: string
) => {
  return { id, title, owner, priority, effort }
}

// Create support options data (≤8 lines)
export const createSupportOptions = (): SupportOption[] => {
  return [
    createSupportOption('24/7 Enterprise Support', 'Round-the-clock support with 15-minute SLA', Phone, true),
    createSupportOption('Dedicated Success Manager', 'Personal point of contact for your implementation', Users, true),
    createSupportOption('Slack Connect Channel', 'Direct access to our engineering team', MessageSquare, true),
    createSupportOption('Training & Certification', 'Comprehensive training for your team', FileText, true)
  ]
}

// Create support option helper (≤8 lines)
const createSupportOption = (
  title: string,
  description: string,
  IconComponent: any,
  available: boolean
): SupportOption => {
  return {
    title,
    description,
    icon: <IconComponent className="w-5 h-5" />,
    available
  }
}

// Create risk mitigations data (≤8 lines)
export const createRiskMitigations = (): RiskMitigation[] => {
  return [
    createRiskMitigation('Performance degradation during rollout', 'Instant rollback capability with zero downtime', 'medium'),
    createRiskMitigation('Integration challenges with existing stack', 'Pre-built connectors and professional services support', 'low'),
    createRiskMitigation('Team adoption and learning curve', 'Comprehensive training program and documentation', 'low'),
    createRiskMitigation('Cost overruns during implementation', 'Fixed-price implementation package available', 'medium')
  ]
}

// Create risk mitigation helper (≤8 lines)
const createRiskMitigation = (
  risk: string,
  mitigation: string,
  severity: 'low' | 'medium' | 'high'
): RiskMitigation => {
  return { risk, mitigation, severity }
}

// Export default phases for convenience
export const defaultPhases = createPhasesData()
export const defaultSupportOptions = createSupportOptions()
export const defaultRiskMitigations = createRiskMitigations()