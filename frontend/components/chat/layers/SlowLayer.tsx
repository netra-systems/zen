"use client";

import React from 'react';
import { motion } from 'framer-motion';
import type { SlowLayerProps } from '@/types/component-props';
import { CompletedAgentsSection } from './CompletedAgentsSection';
import { RecommendationsSection } from './RecommendationsSection';
import { ActionPlanSection } from './ActionPlanSection';
import { ExecutionMetricsSection } from './ExecutionMetricsSection';

export const SlowLayer: React.FC<SlowLayerProps> = ({ data, isCollapsed }) => {
  if (!data) {
    return <EmptyState />;
  }

  // Don't render detailed content if collapsed
  if (isCollapsed) return null;

  return (
    <div 
      className="border-t"
      style={{
        background: 'linear-gradient(180deg, rgba(250, 250, 250, 0.98) 0%, rgba(255, 255, 255, 0.95) 100%)',
        borderTop: '1px solid rgba(228, 228, 231, 0.5)',
        backdropFilter: 'blur(4px)'
      }}
    >
      <div className="p-5 space-y-6">
        {/* Enhanced Completed Agents Section */}
        {data.completedAgents && data.completedAgents.length > 0 && (
          <CompletedAgentsSection completedAgents={data.completedAgents} />
        )}

        {/* Final Report Section */}
        {data.finalReport && (
          <FinalReportSection 
            finalReport={data.finalReport}
            metrics={data.metrics}
            completedAgents={data.completedAgents}
            totalDuration={data.totalDuration}
          />
        )}
      </div>
    </div>
  );
};

const EmptyState = () => (
  <div 
    className="border-t flex items-center justify-center"
    style={{
      minHeight: '100px',
      background: 'linear-gradient(180deg, rgba(250, 250, 250, 0.98) 0%, rgba(255, 255, 255, 0.95) 100%)',
      borderTop: '1px solid rgba(228, 228, 231, 0.5)',
      backdropFilter: 'blur(4px)'
    }}
  >
    <div className="text-center">
      <div className="text-sm text-zinc-500 italic mb-2">Awaiting final results...</div>
      <EmptyStateAnimation />
    </div>
  </div>
);

const EmptyStateAnimation = () => (
  <div className="flex justify-center space-x-1">
    {[0, 1, 2].map((i) => (
      <motion.div
        key={i}
        className="w-2 h-2 bg-gray-400 rounded-full"
        animate={{ opacity: [0.3, 1, 0.3] }}
        transition={{ 
          duration: 1.5, 
          repeat: Infinity, 
          delay: i * 0.3 
        }}
      />
    ))}
  </div>
);

interface FinalReportSectionProps {
  finalReport: {
    recommendations?: any[];
    actionPlan?: any[];
  };
  metrics?: any;
  completedAgents?: any[];
  totalDuration?: number;
}

const FinalReportSection = ({ 
  finalReport, 
  metrics, 
  completedAgents, 
  totalDuration 
}: FinalReportSectionProps) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.4, delay: 0.1 }}
    className="space-y-4"
  >
    {/* Recommendations */}
    {finalReport.recommendations && finalReport.recommendations.length > 0 && (
      <RecommendationsSection recommendations={finalReport.recommendations} />
    )}

    {/* Action Plan */}
    {finalReport.actionPlan && finalReport.actionPlan.length > 0 && (
      <ActionPlanSection actionPlan={finalReport.actionPlan} />
    )}

    {/* Enhanced Execution Metrics */}
    {metrics && (
      <ExecutionMetricsSection 
        metrics={metrics}
        completedAgents={completedAgents}
        totalDuration={totalDuration}
      />
    )}
  </motion.div>
);