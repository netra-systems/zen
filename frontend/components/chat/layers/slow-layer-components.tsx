/**
 * UI Components for SlowLayer Enhanced
 * ULTRA DEEP THINK: Module-based architecture - Components extracted for 450-line compliance
 */

"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp, DollarSign, Zap, Target, ChevronDown, ChevronRight, Download,
  Share2, Shield, ArrowUpRight, ArrowDownRight, Gauge, Package, Brain, 
  Layers, Activity, FileText, Send
} from 'lucide-react';
import type {
  ReportData, RecommendationItem, ActionPlanItem, AgentTimelineItem
} from '@/types/report-data';
import type {
  MetricCardProps, SectionHeaderProps, CostSectionProps, PerformanceCardProps,
  RecommendationHeaderProps, StepButtonProps, TimelineBarProps
} from './slow-layer-types';

// Metric Card Component
export const MetricCard: React.FC<MetricCardProps> = ({ title, value, icon, colorClass }) => (
  <div className="bg-white/80 backdrop-blur rounded-lg p-3">
    <div className="flex items-center justify-between">
      <span className="text-xs text-gray-600">{title}</span>
      {icon}
    </div>
    <div className={`text-2xl font-bold mt-1 ${colorClass}`}>
      {value}
    </div>
  </div>
);

// Executive Summary Metrics Grid
export const SummaryMetrics: React.FC<{ data: ReportData }> = ({ data }) => {
  const savingsAmount = data.finalReport?.cost_analysis?.total_savings || 0;
  const optimizationPotential = data.finalReport?.performance_comparison?.improvement_percentage || 0;
  const confidenceScore = data.finalReport?.confidence_scores?.overall || 0.85 * 100;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <MetricCard
        title="Optimization Potential"
        value={`${optimizationPotential.toFixed(1)}%`}
        icon={<ArrowUpRight className="w-4 h-4 text-emerald-600" />}
        colorClass="text-emerald-600"
      />
      <MetricCard
        title="Monthly Savings"
        value={`$${savingsAmount.toLocaleString()}`}
        icon={<DollarSign className="w-4 h-4 text-green-600" />}
        colorClass="text-green-600"
      />
      <MetricCard
        title="Confidence Score"
        value={`${confidenceScore.toFixed(0)}%`}
        icon={<Shield className="w-4 h-4 text-blue-600" />}
        colorClass="text-blue-600"
      />
    </div>
  );
};

// Executive Summary Card
export const ExecutiveSummary: React.FC<{ data: ReportData }> = ({ data }) => {
  if (!data.finalReport?.executive_summary) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-r from-emerald-50 to-teal-50 rounded-xl p-6 border border-emerald-200 mb-6"
    >
      <h2 className="text-lg font-bold text-gray-900 mb-3 flex items-center">
        <Target className="w-5 h-5 mr-2 text-emerald-600" />
        Executive Summary
      </h2>
      
      <p className="text-sm text-gray-700 mb-4 leading-relaxed">
        {data.finalReport.executive_summary}
      </p>

      <SummaryMetrics data={data} />
    </motion.div>
  );
};

// Cost Entry Component
export const CostEntry: React.FC<{
  service: string;
  cost: number;
  colorClass: string;
  borderClass: string;
}> = ({ service, cost, colorClass, borderClass }) => (
  <div className={`flex justify-between items-center py-2 border-b ${borderClass} last:border-0`}>
    <span className={`text-sm ${colorClass}`}>{service}</span>
    <span className={`text-sm font-mono font-medium ${colorClass}`}>
      ${cost.toLocaleString()}
    </span>
  </div>
);

// Cost Section Component  
export const CostSection: React.FC<CostSectionProps> = ({ 
  title, costs, total, bgClass, titleClass, borderClass, colorClass 
}) => (
  <div className={`${bgClass} rounded-lg p-4`}>
    <h4 className={`text-xs font-semibold ${titleClass} mb-3`}>{title}</h4>
    {Object.entries(costs).map(([service, cost]) => (
      <CostEntry
        key={service}
        service={service}
        cost={cost as number}
        colorClass={colorClass}
        borderClass={borderClass}
      />
    ))}
    <div className={`mt-3 pt-3 border-t ${borderClass.replace('border-b', 'border-t')}`}>
      <div className="flex justify-between items-center">
        <span className={`text-sm font-semibold ${colorClass}`}>Total</span>
        <span className={`text-sm font-mono font-bold ${colorClass}`}>
          ${total.toLocaleString()}
        </span>
      </div>
    </div>
  </div>
);

// Savings Summary Component
export const SavingsSummary: React.FC<{ monthlySavings: number }> = ({ monthlySavings }) => (
  <div className="mt-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-4 border border-green-200">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-gray-600">Estimated Monthly Savings</p>
        <p className="text-2xl font-bold text-green-700">
          ${monthlySavings.toLocaleString()}
        </p>
      </div>
      <div className="text-right">
        <p className="text-sm text-gray-600">Annual Savings</p>
        <p className="text-2xl font-bold text-green-700">
          ${(monthlySavings * 12).toLocaleString()}
        </p>
      </div>
    </div>
  </div>
);

// Collapsible Section Header
export const SectionHeader: React.FC<SectionHeaderProps> = ({ 
  icon, title, isExpanded, onToggle 
}) => (
  <button
    onClick={onToggle}
    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
  >
    <h3 className="text-sm font-semibold text-gray-800 flex items-center">
      {icon}
      {title}
    </h3>
    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
  </button>
);

// Performance Metric Card
export const PerformanceCard: React.FC<PerformanceCardProps> = ({ 
  title, icon, current, projected, improvement, bgClass, titleClass, borderClass, projectedClass 
}) => (
  <div className={`${bgClass} rounded-lg p-4`}>
    <div className="flex items-center justify-between mb-2">
      <span className={`text-xs font-semibold ${titleClass}`}>{title}</span>
      {icon}
    </div>
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-xs text-gray-600">Current</span>
        <span className="text-sm font-mono">{current}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-xs text-gray-600">Projected</span>
        <span className={`text-sm font-mono ${projectedClass}`}>{projected}</span>
      </div>
      <div className={`pt-2 border-t ${borderClass}`}>
        <div className="flex items-center justify-center">
          <ArrowUpRight className="w-4 h-4 text-green-600 mr-1" />
          <span className="text-sm font-bold text-green-600">
            {improvement}
          </span>
        </div>
      </div>
    </div>
  </div>
);

// Step Button Component
export const StepButton: React.FC<StepButtonProps> = ({ 
  index, currentStep, onClick 
}) => (
  <button
    onClick={onClick}
    className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
      index <= currentStep
        ? 'bg-indigo-600 text-white'
        : 'bg-gray-200 text-gray-500'
    }`}
  >
    {index < currentStep ? '✓' : index + 1}
  </button>
);

// Step Content Component
export const StepContent: React.FC<{ step: ActionPlanItem }> = ({ step }) => (
  <div className="ml-4 flex-1 pb-8 border-l-2 border-gray-200 pl-4 -ml-0 last:border-0">
    <h4 className="font-medium text-sm text-gray-900 mb-1">{step.title || step.description}</h4>
    {step.effort_estimate && (
      <p className="text-xs text-gray-500 mb-2">
        Estimated effort: {step.effort_estimate}
      </p>
    )}
    {step.command && (
      <code className="block bg-gray-100 rounded px-3 py-2 text-xs font-mono mb-2">
        {step.command}
      </code>
    )}
    {step.expected_outcome && (
      <p className="text-xs text-gray-600 italic">
        Expected: {step.expected_outcome}
      </p>
    )}
  </div>
);

// Timeline Bar Component
export const TimelineBar: React.FC<TimelineBarProps> = ({ 
  agent, maxDuration, index 
}) => (
  <div key={`${agent.agentName}-${index}`} className="flex items-center">
    <span className="text-xs text-gray-600 w-32 truncate">{agent.agentName}</span>
    <div className="flex-1 mx-2">
      <div className="bg-gray-200 rounded-full h-4 relative overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${((agent.duration || 0) / maxDuration) * 100}%` }}
          transition={{ duration: 0.5, delay: index * 0.1 }}
          className="absolute left-0 top-0 h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
        />
      </div>
    </div>
    <span className="text-xs font-mono text-gray-700 w-16 text-right">
      {(agent.duration || 0) < 1000 ? `${agent.duration || 0}ms` : `${((agent.duration || 0) / 1000).toFixed(1)}s`}
    </span>
  </div>
);

// Export and Share Controls
export const ExportControls: React.FC = () => {
  return (
    <div className="flex items-center gap-2 mt-6">
      <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
        <Download className="w-4 h-4" />
        Export Report
      </button>
      <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
        <Share2 className="w-4 h-4" />
        Share
      </button>
      <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
        <Send className="w-4 h-4" />
        Email Report
      </button>
    </div>
  );
};

// Technical Details Component
export const TechnicalDetails: React.FC<{ technicalDetails: any }> = ({ technicalDetails }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    className="bg-gray-900 text-gray-100 rounded-xl p-6"
  >
    <h3 className="text-sm font-semibold mb-4 flex items-center">
      <FileText className="w-4 h-4 mr-2 text-gray-400" />
      Technical Deep Dive
    </h3>
    <pre className="text-xs font-mono overflow-x-auto">
      {JSON.stringify(technicalDetails, null, 2)}
    </pre>
  </motion.div>
);