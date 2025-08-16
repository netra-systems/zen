/**
 * Recommendations and Action Plan Components for SlowLayer Enhanced
 * ULTRA DEEP THINK: Module-based architecture - Recommendations extracted for 300-line compliance
 */

"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Zap, TrendingUp, Activity, ChevronDown, ChevronRight, Package, Layers
} from 'lucide-react';
import type { RecommendationItem, ActionPlanItem, AgentTimelineItem } from './slow-layer-types';
import { StepButton, StepContent, TimelineBar } from './slow-layer-components';

// Utility Functions for Recommendations
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

// Recommendation Card Utilities
const toggleCardExpansion = (
  id: string,
  expandedCards: Set<string>,
  setExpandedCards: (cards: Set<string>) => void
) => {
  const newExpanded = new Set(expandedCards);
  if (newExpanded.has(id)) {
    newExpanded.delete(id);
  } else {
    newExpanded.add(id);
  }
  setExpandedCards(newExpanded);
};

// Recommendation Card Header
const RecommendationHeader: React.FC<{
  rec: RecommendationItem;
  expandedCards: Set<string>;
  onToggle: (id: string) => void;
}> = ({ rec, expandedCards, onToggle }) => (
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
      onClick={() => rec.id && onToggle(rec.id)}
      className="ml-2 p-1 hover:bg-gray-100 rounded"
    >
      {rec.id && expandedCards.has(rec.id) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
    </button>
  </div>
);

// Recommendation Metrics
const RecommendationMetrics: React.FC<{ metrics?: RecommendationItem['metrics'] }> = ({ metrics }) => (
  <div className="flex flex-wrap gap-2 mb-3">
    {metrics?.potential_savings && (
      <div className="bg-green-50 text-green-700 px-2 py-1 rounded-md text-xs font-medium">
        Save ${metrics.potential_savings.toLocaleString()}/mo
      </div>
    )}
    {metrics?.latency_reduction && (
      <div className="bg-blue-50 text-blue-700 px-2 py-1 rounded-md text-xs font-medium">
        {metrics.latency_reduction}ms faster
      </div>
    )}
    {metrics?.throughput_increase && (
      <div className="bg-purple-50 text-purple-700 px-2 py-1 rounded-md text-xs font-medium">
        +{metrics.throughput_increase}% throughput
      </div>
    )}
  </div>
);

// Implementation Steps
const ImplementationSteps: React.FC<{ steps: string[] }> = ({ steps }) => (
  <div className="space-y-2">
    <h5 className="text-xs font-semibold text-gray-700">Implementation Steps:</h5>
    <ol className="space-y-1">
      {steps.map((step: string, idx: number) => (
        <li key={idx} className="text-xs text-gray-600 flex">
          <span className="font-mono mr-2">{idx + 1}.</span>
          <span>{step}</span>
        </li>
      ))}
    </ol>
  </div>
);

// Recommendation Action Buttons
const RecommendationActions: React.FC = () => (
  <div className="mt-3 flex gap-2">
    <button className="flex-1 bg-indigo-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-indigo-700 transition-colors">
      Implement Now
    </button>
    <button className="flex-1 bg-gray-100 text-gray-700 px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-gray-200 transition-colors">
      Schedule Later
    </button>
  </div>
);

// Recommendation Expanded Content
const RecommendationExpandedContent: React.FC<{ rec: RecommendationItem }> = ({ rec }) => (
  <motion.div
    initial={{ height: 0, opacity: 0 }}
    animate={{ height: 'auto', opacity: 1 }}
    exit={{ height: 0, opacity: 0 }}
    className="pt-3 border-t border-gray-200"
  >
    {rec.implementation_steps && (
      <ImplementationSteps steps={rec.implementation_steps} />
    )}
    <RecommendationActions />
  </motion.div>
);

export const EnhancedRecommendations: React.FC<{ recommendations: RecommendationItem[] }> = ({ recommendations }) => {
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());

  const handleToggle = (id: string) => {
    toggleCardExpansion(id, expandedCards, setExpandedCards);
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
              <RecommendationHeader
                rec={rec}
                expandedCards={expandedCards}
                onToggle={handleToggle}
              />

              <p className="text-sm text-gray-600 mb-3">{rec.description}</p>

              <RecommendationMetrics metrics={rec.metrics} />

              <AnimatePresence>
                {rec.id && expandedCards.has(rec.id) && (
                  <RecommendationExpandedContent rec={rec} />
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export const ActionPlanStepper: React.FC<{ actionPlan: ActionPlanItem[] }> = ({ actionPlan }) => {
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
            <StepButton
              index={index}
              currentStep={currentStep}
              onClick={() => setCurrentStep(index)}
            />
            <StepContent step={step} />
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export const AgentTimeline: React.FC<{ agents: AgentTimelineItem[] }> = ({ agents }) => {
  if (!agents || agents.length === 0) return null;

  const maxDuration = Math.max(...agents.map(a => a.duration || 0));

  return (
    <div className="bg-gray-50 rounded-xl p-4">
      <h4 className="text-xs font-semibold text-gray-700 mb-3">Agent Execution Timeline</h4>
      <div className="space-y-2">
        {agents.map((agent, index) => (
          <TimelineBar
            key={`${agent.agentName}-${index}`}
            agent={agent}
            maxDuration={maxDuration}
            index={index}
          />
        ))}
      </div>
    </div>
  );
};