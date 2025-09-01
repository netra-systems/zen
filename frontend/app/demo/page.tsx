'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'
import DemoHeader from '@/components/demo/DemoHeader'
import DemoProgress from '@/components/demo/DemoProgress'
import DemoTabs from '@/components/demo/DemoTabs'
import IndustrySelectionCard from '@/components/demo/IndustrySelectionCard'
import DemoCompletion from '@/components/demo/DemoCompletion'

export default function EnterpriseDemo() {
  const { } = useAuthStore()
  const [activeTab, setActiveTab] = useState('overview')
  const [selectedIndustry, setSelectedIndustry] = useState<string>('')
  const [demoProgress, setDemoProgress] = useState(0)
  const [demoStarted, setDemoStarted] = useState(false)
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set())

  const calculateProgress = useCallback(() => {
    const totalSteps = 5 // industry, roi, chat, metrics, export
    const progress = (completedSteps.size / totalSteps) * 100
    setDemoProgress(progress)
  }, [completedSteps])

  const navigateToNextTab = (stepId: string) => {
    if (stepId === 'roi') setActiveTab('roi')
    if (stepId === 'chat') setActiveTab('optimization')
    if (stepId === 'metrics') setActiveTab('performance')
    if (stepId === 'export') setActiveTab('roadmap')
  }

  const handleStepComplete = (stepId: string) => {
    setCompletedSteps(prev => new Set(prev).add(stepId))
    navigateToNextTab(stepId)
  }

  const handleIndustrySelect = (industry: string) => {
    setSelectedIndustry(industry)
    handleStepComplete('industry')
    setDemoStarted(true)
  }

  useEffect(() => {
    calculateProgress()
  }, [completedSteps, calculateProgress])

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-black">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <DemoHeader selectedIndustry={selectedIndustry} />
        
        <DemoProgress 
          demoProgress={demoProgress}
          completedSteps={completedSteps}
          selectedIndustry={selectedIndustry}
          demoStarted={demoStarted}
        />

        {!selectedIndustry && (
          <IndustrySelectionCard onIndustrySelect={handleIndustrySelect} />
        )}

        {selectedIndustry && (
          <DemoTabs
            activeTab={activeTab}
            selectedIndustry={selectedIndustry}
            completedSteps={completedSteps}
            onTabChange={setActiveTab}
            onStepComplete={handleStepComplete}
          />
        )}

        <DemoCompletion demoProgress={demoProgress} />
      </div>
    </div>
  )
}