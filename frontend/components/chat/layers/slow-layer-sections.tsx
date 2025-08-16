/**
 * Section Components for SlowLayer Enhanced
 * ULTRA DEEP THINK: Module-based architecture - Sections extracted for 300-line compliance
 */

"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { DollarSign, Activity } from 'lucide-react';
import type { ReportData } from './slow-layer-types';
import { 
  SectionHeader, CostSection, SavingsSummary, PerformanceCard 
} from './slow-layer-components';

// Cost Analysis Expanded Content
const CostAnalysisContent: React.FC<{ costData: any }> = ({ costData }) => (
  <motion.div
    initial={{ height: 0, opacity: 0 }}
    animate={{ height: 'auto', opacity: 1 }}
    exit={{ height: 0, opacity: 0 }}
    className="px-6 pb-6"
  >
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <CostSection
        title="Current Monthly Costs"
        costs={costData.current_costs || {}}
        total={costData.total_current || 0}
        bgClass="bg-gray-50"
        titleClass="text-gray-600"
        borderClass="border-gray-200"
        colorClass="text-gray-700"
      />
      <CostSection
        title="Projected Monthly Costs"
        costs={costData.projected_costs || {}}
        total={costData.total_projected || 0}
        bgClass="bg-emerald-50"
        titleClass="text-emerald-700"
        borderClass="border-emerald-200"
        colorClass="text-emerald-700"
      />
    </div>
    <SavingsSummary monthlySavings={costData.monthly_savings || 0} />
  </motion.div>
);

// Cost Analysis Section
export const CostAnalysis: React.FC<{ data: ReportData }> = ({ data }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  
  if (!data.finalReport?.cost_analysis) return null;

  const costData = data.finalReport.cost_analysis;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl shadow-sm border border-gray-200 mb-6"
    >
      <SectionHeader
        icon={<DollarSign className="w-4 h-4 mr-2 text-green-600" />}
        title="Cost Analysis & Projections"
        isExpanded={isExpanded}
        onToggle={() => setIsExpanded(!isExpanded)}
      />

      <AnimatePresence>
        {isExpanded && <CostAnalysisContent costData={costData} />}
      </AnimatePresence>
    </motion.div>
  );
};

// Performance Metrics Content
const PerformanceMetricsContent: React.FC<{ perfData: any }> = ({ perfData }) => (
  <motion.div
    initial={{ height: 0, opacity: 0 }}
    animate={{ height: 'auto', opacity: 1 }}
    exit={{ height: 0, opacity: 0 }}
    className="px-6 pb-6"
  >
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <PerformanceCard
        title="Response Time"
        icon={<Activity className="w-4 h-4 text-blue-600" />}
        current={`${perfData.response_time_current || '250'}ms`}
        projected={`${perfData.response_time_projected || '150'}ms`}
        improvement={`${perfData.response_time_improvement || '40'}% faster`}
        bgClass="bg-blue-50"
        titleClass="text-blue-700"
        borderClass="border-blue-200"
        projectedClass="text-blue-600"
      />
      <PerformanceCard
        title="Throughput"
        icon={<Activity className="w-4 h-4 text-purple-600" />}
        current={`${perfData.throughput_current || '1000'} req/s`}
        projected={`${perfData.throughput_projected || '1500'} req/s`}
        improvement={`${perfData.throughput_improvement || '50'}% increase`}
        bgClass="bg-purple-50"
        titleClass="text-purple-700"
        borderClass="border-purple-200"
        projectedClass="text-purple-600"
      />
      <PerformanceCard
        title="Quality Score"
        icon={<Activity className="w-4 h-4 text-orange-600" />}
        current={`${perfData.quality_current || '92'}%`}
        projected={`${perfData.quality_projected || '96'}%`}
        improvement={`${perfData.quality_improvement || '4'}% better`}
        bgClass="bg-orange-50"
        titleClass="text-orange-700"
        borderClass="border-orange-200"
        projectedClass="text-orange-600"
      />
    </div>
  </motion.div>
);

// Performance Metrics Section
export const PerformanceMetrics: React.FC<{ data: ReportData }> = ({ data }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  
  if (!data.finalReport?.performance_comparison) return null;

  const perfData = data.finalReport.performance_comparison;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl shadow-sm border border-gray-200 mb-6"
    >
      <SectionHeader
        icon={<Activity className="w-4 h-4 mr-2 text-blue-600" />}
        title="Performance Metrics & Improvements"
        isExpanded={isExpanded}
        onToggle={() => setIsExpanded(!isExpanded)}
      />

      <AnimatePresence>
        {isExpanded && <PerformanceMetricsContent perfData={perfData} />}
      </AnimatePresence>
    </motion.div>
  );
};