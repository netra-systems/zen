'use client'

import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  ImplementationRoadmapProps, 
  ExportFormat, 
  TabValue 
} from './roadmap-types'
import { 
  defaultPhases, 
  defaultSupportOptions, 
  defaultRiskMitigations 
} from './roadmap-data'
import { 
  createExportData, 
  handleExportData 
} from './roadmap-utils'
import { 
  RoadmapHeader, 
  MetricsGrid, 
  PhaseRecommendationAlert, 
  PhaseCard 
} from './roadmap-components'
import { 
  TaskBreakdownCard, 
  RiskManagementCard, 
  SupportPackageCard, 
  CallToActionCard 
} from './roadmap-components-extended'

export default function ImplementationRoadmap({ 
  industry, 
  completedSteps,
  onExport 
}: ImplementationRoadmapProps) {
  const [activeTab, setActiveTab] = useState<TabValue>('phases')
  const [exportFormat] = useState<ExportFormat>('pdf')

  // Use data from modules
  const phases = defaultPhases
  const supportOptions = defaultSupportOptions
  const riskMitigations = defaultRiskMitigations

  // Handle export using utils module (≤8 lines)
  const handleExport = () => {
    const exportData = createExportData(
      industry,
      completedSteps,
      phases,
      supportOptions,
      riskMitigations
    )
    handleExportData(exportData, exportFormat, onExport)
  }

  return (
    <div className="space-y-6">
      <RoadmapHeader industry={industry} onExport={handleExport} />
      <MetricsGrid />
      <RoadmapTabs 
        activeTab={activeTab} 
        setActiveTab={setActiveTab}
        industry={industry}
        phases={phases}
        supportOptions={supportOptions}
        riskMitigations={riskMitigations}
      />
      <CallToActionCard />
    </div>
  )
}

// Roadmap tabs component (≤8 lines)
const RoadmapTabs = ({ 
  activeTab, 
  setActiveTab, 
  industry, 
  phases, 
  supportOptions, 
  riskMitigations 
}: {
  activeTab: TabValue
  setActiveTab: (tab: TabValue) => void
  industry: string
  phases: any[]
  supportOptions: any[]
  riskMitigations: any[]
}) => (
  <Tabs value={activeTab} onValueChange={setActiveTab}>
    <TabsList className="grid w-full grid-cols-4">
      <TabsTrigger value="phases">Implementation Phases</TabsTrigger>
      <TabsTrigger value="tasks">Task Breakdown</TabsTrigger>
      <TabsTrigger value="risks">Risk Management</TabsTrigger>
      <TabsTrigger value="support">Support & Resources</TabsTrigger>
    </TabsList>
    <RoadmapTabsContent 
      industry={industry}
      phases={phases}
      supportOptions={supportOptions}
      riskMitigations={riskMitigations}
    />
  </Tabs>
)

// Roadmap tabs content (≤8 lines)
const RoadmapTabsContent = ({ 
  industry, 
  phases, 
  supportOptions, 
  riskMitigations 
}: {
  industry: string
  phases: any[]
  supportOptions: any[]
  riskMitigations: any[]
}) => (
  <>
    <TabsContent value="phases" className="space-y-4">
      <PhaseRecommendationAlert industry={industry} />
      <PhasesGrid phases={phases} />
    </TabsContent>
    <TabsContent value="tasks" className="space-y-4">
      <TaskBreakdownCard phases={phases} />
    </TabsContent>
    <TabsContent value="risks" className="space-y-4">
      <RiskManagementCard riskMitigations={riskMitigations} />
    </TabsContent>
    <TabsContent value="support" className="space-y-4">
      <SupportPackageCard supportOptions={supportOptions} />
    </TabsContent>
  </>
)

// Phases grid component (≤8 lines)
const PhasesGrid = ({ phases }: { phases: any[] }) => (
  <div className="space-y-4">
    {phases.map((phase, idx) => (
      <PhaseCard key={phase.id} phase={phase} index={idx} />
    ))}
  </div>
)