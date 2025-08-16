/**
 * SlowLayer Enhanced Component - Main Component
 * ULTRA DEEP THINK: Module-based architecture - Main component ≤300 lines
 */

"use client";

import React from 'react';
import type { SlowLayerProps } from '@/types/unified-chat';
import type { ReportData } from './slow-layer-types';
import { ExecutiveSummary, ExportControls, TechnicalDetails } from './slow-layer-components';
import { CostAnalysis, PerformanceMetrics } from './slow-layer-sections';
import { EnhancedRecommendations, ActionPlanStepper, AgentTimeline } from './slow-layer-recommendations';

// Main Enhanced SlowLayer Component
export const SlowLayerEnhanced: React.FC<SlowLayerProps> = ({ data, isCollapsed }) => {
  if (!data) return null;
  if (isCollapsed) return null;

  const reportData = data as ReportData;

  return (
    <div className="bg-gradient-to-b from-gray-50 to-white">
      <div className="p-6 space-y-6">
        <ExecutiveSummary data={reportData} />
        <CostAnalysis data={reportData} />
        <PerformanceMetrics data={reportData} />

        {reportData.finalReport?.recommendations && (
          <EnhancedRecommendations recommendations={reportData.finalReport.recommendations} />
        )}

        {reportData.finalReport?.actionPlan && (
          <ActionPlanStepper actionPlan={reportData.finalReport.actionPlan} />
        )}

        {reportData.completedAgents && (
          <AgentTimeline agents={reportData.completedAgents} />
        )}

        {reportData.finalReport?.technical_details && (
          <TechnicalDetails technicalDetails={reportData.finalReport.technical_details} />
        )}

        <ExportControls />
      </div>
    </div>
  );
};