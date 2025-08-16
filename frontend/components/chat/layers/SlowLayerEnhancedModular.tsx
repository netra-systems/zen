"use client";

import React from 'react';
import type { SlowLayerProps } from '@/types/unified-chat';
import {
  ExecutiveSummary,
  CostAnalysis,
  PerformanceMetrics,
  EnhancedRecommendations,
  ActionPlanStepper,
  AgentTimeline,
  TechnicalDetails,
  ExportControls,
  type ReportData
} from './slow-layer';

/**
 * Enhanced SlowLayer component with modular architecture
 * Each section is extracted into focused, reusable components
 */
export const SlowLayerEnhancedModular: React.FC<SlowLayerProps> = ({ data, isCollapsed }) => {
  if (!data || isCollapsed) return null;

  const reportData: ReportData = {
    finalReport: data.finalReport,
    completedAgents: data.completedAgents
  };

  return (
    <div className="bg-gradient-to-b from-gray-50 to-white">
      <div className="p-6 space-y-6">
        {/* Executive Summary */}
        <ExecutiveSummary data={reportData} />

        {/* Cost Analysis */}
        <CostAnalysis data={reportData} />

        {/* Performance Metrics */}
        <PerformanceMetrics data={reportData} />

        {/* Enhanced Recommendations */}
        {data.finalReport?.recommendations && (
          <EnhancedRecommendations recommendations={data.finalReport.recommendations} />
        )}

        {/* Action Plan Stepper */}
        {data.finalReport?.actionPlan && (
          <ActionPlanStepper actionPlan={data.finalReport.actionPlan} />
        )}

        {/* Agent Timeline */}
        {data.completedAgents && (
          <AgentTimeline agents={data.completedAgents} />
        )}

        {/* Technical Details */}
        <TechnicalDetails technicalDetails={data.finalReport?.technical_details} />

        {/* Export Controls */}
        <ExportControls />
      </div>
    </div>
  );
};