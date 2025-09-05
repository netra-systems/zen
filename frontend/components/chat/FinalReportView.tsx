import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ReportHeader } from './components/ReportHeader';
import { ExecutiveSummary } from './components/ExecutiveSummary';
import { OverviewTab } from './components/tabs/OverviewTab';
import { DataAnalysisTab } from './components/tabs/DataAnalysisTab';
import { OptimizationsTab } from './components/tabs/OptimizationsTab';
import { ActionPlanTab } from './components/tabs/ActionPlanTab';
import { MetricsTab } from './components/tabs/MetricsTab';
import { RawDataViewer } from './components/RawDataViewer';
import type { FinalReportProps, ExpandedSections } from './types/FinalReportTypes';

// Initialize expanded sections state
const initializeExpandedSections = (): ExpandedSections => ({
  summary: true,
  data: false,
  optimizations: false,
  actions: false,
  metrics: false,
  raw: false
});

// Toggle section function
const createToggleSection = (
  setExpandedSections: React.Dispatch<React.SetStateAction<ExpandedSections>>
) => (section: string): void => {
  setExpandedSections(prev => ({
    ...prev,
    [section]: !prev[section]
  }));
};

export const FinalReportView: React.FC<FinalReportProps> = ({ reportData }) => {
  const [expandedSections, setExpandedSections] = useState<ExpandedSections>(
    initializeExpandedSections()
  );

  const toggleSection = createToggleSection(setExpandedSections);

  return (
    <div className="w-full max-w-6xl mx-auto p-3 space-y-3">
      <ReportHeader reportData={reportData} />
      
      <ExecutiveSummary finalReport={reportData.final_report} />

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="data">Data Analysis</TabsTrigger>
          <TabsTrigger value="optimizations">Optimizations</TabsTrigger>
          <TabsTrigger value="actions">Action Plan</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <OverviewTab executionMetrics={reportData.execution_metrics} />
        </TabsContent>

        <TabsContent value="data" className="space-y-4">
          <DataAnalysisTab dataResult={reportData.data_result} />
        </TabsContent>

        <TabsContent value="optimizations" className="space-y-4">
          <OptimizationsTab
            optimizationsResult={reportData.optimizations_result}
            expandedSections={expandedSections}
            toggleSection={toggleSection}
          />
        </TabsContent>

        <TabsContent value="actions" className="space-y-4">
          <ActionPlanTab actionPlanResult={reportData.action_plan_result} />
        </TabsContent>

        <TabsContent value="metrics" className="space-y-4">
          <MetricsTab executionMetrics={reportData.execution_metrics} />
        </TabsContent>
      </Tabs>

      <RawDataViewer
        reportData={reportData}
        isExpanded={expandedSections.raw}
        onToggle={() => toggleSection('raw')}
      />
    </div>
  );
};