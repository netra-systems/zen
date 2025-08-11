"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp, DollarSign,
  Zap, Target, ChevronDown, ChevronRight, Download,
  Share2, Shield, ArrowUpRight, ArrowDownRight, Gauge,
  Package, Brain, Layers, Activity, FileText, Send
} from 'lucide-react';
import type { SlowLayerProps } from '@/types/unified-chat';

interface ReportData {
  finalReport?: {
    executive_summary?: string;
    cost_analysis?: {
      total_savings?: number;
      current_costs?: Record<string, number>;
      projected_costs?: Record<string, number>;
      monthly_savings?: number;
      total_current?: number;
      total_projected?: number;
    };
    performance_comparison?: {
      improvement_percentage?: number;
      response_time_current?: string | number;
      response_time_projected?: string | number;
      response_time_improvement?: string | number;
      throughput_current?: string | number;
      throughput_projected?: string | number;
      throughput_improvement?: string | number;
      quality_score_current?: number;
      quality_score_projected?: number;
      quality_improvement?: number;
      quality_current?: string | number;
      quality_projected?: string | number;
    };
    confidence_scores?: {
      overall?: number;
    };
  };
}

// Executive Summary Card
const ExecutiveSummary: React.FC<{ data: ReportData }> = ({ data }) => {
  if (!data.finalReport?.executive_summary) return null;

  const savingsAmount = data.finalReport.cost_analysis?.total_savings || 0;
  const optimizationPotential = data.finalReport.performance_comparison?.improvement_percentage || 0;

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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white/80 backdrop-blur rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600">Optimization Potential</span>
            <ArrowUpRight className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-600 mt-1">
            {optimizationPotential.toFixed(1)}%
          </div>
        </div>

        <div className="bg-white/80 backdrop-blur rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600">Monthly Savings</span>
            <DollarSign className="w-4 h-4 text-green-600" />
          </div>
          <div className="text-2xl font-bold text-green-600 mt-1">
            ${savingsAmount.toLocaleString()}
          </div>
        </div>

        <div className="bg-white/80 backdrop-blur rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600">Confidence Score</span>
            <Shield className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-blue-600 mt-1">
            {(data.finalReport.confidence_scores?.overall || 0.85 * 100).toFixed(0)}%
          </div>
        </div>
      </div>
    </motion.div>
  );
};

// Cost Analysis Section
const CostAnalysis: React.FC<{ data: ReportData }> = ({ data }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  
  if (!data.finalReport?.cost_analysis) return null;

  const costData = data.finalReport.cost_analysis;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl shadow-sm border border-gray-200 mb-6"
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <h3 className="text-sm font-semibold text-gray-800 flex items-center">
          <DollarSign className="w-4 h-4 mr-2 text-green-600" />
          Cost Analysis & Projections
        </h3>
        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-6 pb-6"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Current Costs */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-xs font-semibold text-gray-600 mb-3">Current Monthly Costs</h4>
                {Object.entries(costData.current_costs || {}).map(([service, cost]) => (
                  <div key={service} className="flex justify-between items-center py-2 border-b border-gray-200 last:border-0">
                    <span className="text-sm text-gray-700">{service}</span>
                    <span className="text-sm font-mono font-medium text-gray-900">
                      ${(cost as number).toLocaleString()}
                    </span>
                  </div>
                ))}
                <div className="mt-3 pt-3 border-t border-gray-300">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-semibold text-gray-700">Total</span>
                    <span className="text-sm font-mono font-bold text-gray-900">
                      ${(costData.total_current || 0).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Projected Costs */}
              <div className="bg-emerald-50 rounded-lg p-4">
                <h4 className="text-xs font-semibold text-emerald-700 mb-3">Projected Monthly Costs</h4>
                {Object.entries(costData.projected_costs || {}).map(([service, cost]) => (
                  <div key={service} className="flex justify-between items-center py-2 border-b border-emerald-200 last:border-0">
                    <span className="text-sm text-emerald-700">{service}</span>
                    <span className="text-sm font-mono font-medium text-emerald-900">
                      ${(cost as number).toLocaleString()}
                    </span>
                  </div>
                ))}
                <div className="mt-3 pt-3 border-t border-emerald-300">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-semibold text-emerald-700">Total</span>
                    <span className="text-sm font-mono font-bold text-emerald-900">
                      ${(costData.total_projected || 0).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Savings Summary */}
            <div className="mt-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-4 border border-green-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Estimated Monthly Savings</p>
                  <p className="text-2xl font-bold text-green-700">
                    ${(costData.monthly_savings || 0).toLocaleString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-600">Annual Savings</p>
                  <p className="text-2xl font-bold text-green-700">
                    ${((costData.monthly_savings || 0) * 12).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Performance Metrics Section
const PerformanceMetrics: React.FC<{ data: ReportData }> = ({ data }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  
  if (!data.finalReport?.performance_comparison) return null;

  const perfData = data.finalReport.performance_comparison;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl shadow-sm border border-gray-200 mb-6"
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <h3 className="text-sm font-semibold text-gray-800 flex items-center">
          <Activity className="w-4 h-4 mr-2 text-blue-600" />
          Performance Metrics & Improvements
        </h3>
        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-6 pb-6"
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Response Time */}
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-blue-700">Response Time</span>
                  <Zap className="w-4 h-4 text-blue-600" />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-600">Current</span>
                    <span className="text-sm font-mono">{perfData.response_time_current || '250'}ms</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-600">Projected</span>
                    <span className="text-sm font-mono text-blue-600">{perfData.response_time_projected || '150'}ms</span>
                  </div>
                  <div className="pt-2 border-t border-blue-200">
                    <div className="flex items-center justify-center">
                      <ArrowDownRight className="w-4 h-4 text-green-600 mr-1" />
                      <span className="text-sm font-bold text-green-600">
                        {perfData.response_time_improvement || '40'}% faster
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Throughput */}
              <div className="bg-purple-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-purple-700">Throughput</span>
                  <Gauge className="w-4 h-4 text-purple-600" />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-600">Current</span>
                    <span className="text-sm font-mono">{perfData.throughput_current || '1000'} req/s</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-600">Projected</span>
                    <span className="text-sm font-mono text-purple-600">{perfData.throughput_projected || '1500'} req/s</span>
                  </div>
                  <div className="pt-2 border-t border-purple-200">
                    <div className="flex items-center justify-center">
                      <ArrowUpRight className="w-4 h-4 text-green-600 mr-1" />
                      <span className="text-sm font-bold text-green-600">
                        {perfData.throughput_improvement || '50'}% increase
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Quality Score */}
              <div className="bg-orange-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-orange-700">Quality Score</span>
                  <Brain className="w-4 h-4 text-orange-600" />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-600">Current</span>
                    <span className="text-sm font-mono">{perfData.quality_current || '92'}%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-600">Projected</span>
                    <span className="text-sm font-mono text-orange-600">{perfData.quality_projected || '96'}%</span>
                  </div>
                  <div className="pt-2 border-t border-orange-200">
                    <div className="flex items-center justify-center">
                      <ArrowUpRight className="w-4 h-4 text-green-600 mr-1" />
                      <span className="text-sm font-bold text-green-600">
                        {perfData.quality_improvement || '4'}% better
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Enhanced Recommendations with Cards
interface RecommendationItem {
  id?: string;
  title?: string;
  description?: string;
  impact?: 'high' | 'medium' | 'low';
  effort?: 'high' | 'medium' | 'low';
  category?: string;
  confidence_score?: number;
  implementation_steps?: string[];
  metrics?: {
    potential_savings?: number;
    latency_reduction?: number;
    throughput_increase?: number;
  };
}

const EnhancedRecommendations: React.FC<{ recommendations: RecommendationItem[] }> = ({ recommendations }) => {
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());

  const toggleCard = (id: string) => {
    const newExpanded = new Set(expandedCards);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedCards(newExpanded);
  };

  const getImpactIcon = (impact: string) => {
    switch (impact) {
      case 'high': return <Zap className="w-4 h-4 text-red-600" />;
      case 'medium': return <TrendingUp className="w-4 h-4 text-yellow-600" />;
      case 'low': return <Activity className="w-4 h-4 text-green-600" />;
      default: return null;
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800';
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-orange-100 text-orange-800';
  };

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-800 flex items-center mb-4">
        <Package className="w-4 h-4 mr-2 text-indigo-600" />
        Optimization Recommendations
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {recommendations.map((rec) => (
          <motion.div
            key={rec.id}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
          >
            <div className="p-4">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-900 flex items-center">
                    {rec.impact && getImpactIcon(rec.impact)}
                    <span className="ml-2">{rec.title}</span>
                  </h4>
                  {rec.confidence_score && (
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium mt-2 ${getConfidenceColor(rec.confidence_score)}`}>
                      {(rec.confidence_score * 100).toFixed(0)}% confidence
                    </span>
                  )}
                </div>
                <button
                  onClick={() => rec.id && toggleCard(rec.id)}
                  className="ml-2 p-1 hover:bg-gray-100 rounded"
                >
                  {rec.id && expandedCards.has(rec.id) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </button>
              </div>

              <p className="text-sm text-gray-600 mb-3">{rec.description}</p>

              {/* Key Metrics */}
              <div className="flex flex-wrap gap-2 mb-3">
                {rec.metrics?.potential_savings && (
                  <div className="bg-green-50 text-green-700 px-2 py-1 rounded-md text-xs font-medium">
                    Save ${rec.metrics.potential_savings.toLocaleString()}/mo
                  </div>
                )}
                {rec.metrics?.latency_reduction && (
                  <div className="bg-blue-50 text-blue-700 px-2 py-1 rounded-md text-xs font-medium">
                    {rec.metrics.latency_reduction}ms faster
                  </div>
                )}
                {rec.metrics?.throughput_increase && (
                  <div className="bg-purple-50 text-purple-700 px-2 py-1 rounded-md text-xs font-medium">
                    +{rec.metrics.throughput_increase}% throughput
                  </div>
                )}
              </div>

              <AnimatePresence>
                {expandedCards.has(rec.id) && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="pt-3 border-t border-gray-200"
                  >
                    {rec.implementation_steps && (
                      <div className="space-y-2">
                        <h5 className="text-xs font-semibold text-gray-700">Implementation Steps:</h5>
                        <ol className="space-y-1">
                          {rec.implementation_steps.map((step: string, idx: number) => (
                            <li key={idx} className="text-xs text-gray-600 flex">
                              <span className="font-mono mr-2">{idx + 1}.</span>
                              <span>{step}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}
                    
                    <div className="mt-3 flex gap-2">
                      <button className="flex-1 bg-indigo-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-indigo-700 transition-colors">
                        Implement Now
                      </button>
                      <button className="flex-1 bg-gray-100 text-gray-700 px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-gray-200 transition-colors">
                        Schedule Later
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

// Action Plan Stepper
interface ActionPlanItem {
  id?: string;
  step_number?: number;
  description?: string;
  command?: string;
  expected_outcome?: string;
  dependencies?: string[];
  estimated_duration?: string;
}

const ActionPlanStepper: React.FC<{ actionPlan: ActionPlanItem[] }> = ({ actionPlan }) => {
  const [currentStep, setCurrentStep] = useState(0);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-sm font-semibold text-gray-800 flex items-center mb-4">
        <Layers className="w-4 h-4 mr-2 text-orange-600" />
        Implementation Roadmap
      </h3>

      <div className="space-y-4">
        {actionPlan.map((step, index) => (
          <motion.div
            key={step.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`flex items-start ${index <= currentStep ? 'opacity-100' : 'opacity-50'}`}
          >
            <button
              onClick={() => setCurrentStep(index)}
              className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                index <= currentStep
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-200 text-gray-500'
              }`}
            >
              {index < currentStep ? '✓' : index + 1}
            </button>

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
          </motion.div>
        ))}
      </div>
    </div>
  );
};

// Agent Timeline Visualization
interface AgentTimelineItem {
  agentName?: string;
  duration?: number;
  metrics?: {
    tokens_used?: number;
    tools_executed?: number;
    cache_hits?: number;
    cache_misses?: number;
  };
}

const AgentTimeline: React.FC<{ agents: AgentTimelineItem[] }> = ({ agents }) => {
  if (!agents || agents.length === 0) return null;

  const maxDuration = Math.max(...agents.map(a => a.duration || 0));

  return (
    <div className="bg-gray-50 rounded-xl p-4">
      <h4 className="text-xs font-semibold text-gray-700 mb-3">Agent Execution Timeline</h4>
      <div className="space-y-2">
        {agents.map((agent, index) => (
          <div key={`${agent.agentName}-${index}`} className="flex items-center">
            <span className="text-xs text-gray-600 w-32 truncate">{agent.agentName}</span>
            <div className="flex-1 mx-2">
              <div className="bg-gray-200 rounded-full h-4 relative overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(agent.duration / maxDuration) * 100}%` }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  className="absolute left-0 top-0 h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                />
              </div>
            </div>
            <span className="text-xs font-mono text-gray-700 w-16 text-right">
              {agent.duration < 1000 ? `${agent.duration}ms` : `${(agent.duration / 1000).toFixed(1)}s`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

// Export and Share Controls
const ExportControls: React.FC = () => {
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

// Main Enhanced SlowLayer Component
export const SlowLayerEnhanced: React.FC<SlowLayerProps> = ({ data, isCollapsed }) => {
  if (!data) return null;
  if (isCollapsed) return null;

  return (
    <div className="bg-gradient-to-b from-gray-50 to-white">
      <div className="p-6 space-y-6">
        {/* Executive Summary */}
        <ExecutiveSummary data={data} />

        {/* Cost Analysis */}
        <CostAnalysis data={data} />

        {/* Performance Metrics */}
        <PerformanceMetrics data={data} />

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

        {/* Technical Details (Collapsible) */}
        {data.finalReport?.technical_details && (
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
              {JSON.stringify(data.finalReport.technical_details, null, 2)}
            </pre>
          </motion.div>
        )}

        {/* Export Controls */}
        <ExportControls />
      </div>
    </div>
  );
};