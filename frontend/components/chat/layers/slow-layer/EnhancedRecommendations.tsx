"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Package, ChevronDown, ChevronRight, Zap, TrendingUp, Activity
} from 'lucide-react';
import type { RecommendationItem } from './types';

interface EnhancedRecommendationsProps {
  recommendations: RecommendationItem[];
}

const getImpactIcon = (impact?: string) => {
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

interface MetricBadgeProps {
  label: string;
  value: string;
  bgColor: string;
  textColor: string;
}

const MetricBadge: React.FC<MetricBadgeProps> = ({ label, value, bgColor, textColor }) => (
  <div className={`${bgColor} ${textColor} px-2 py-1 rounded-md text-xs font-medium`}>
    {label} {value}
  </div>
);

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

const ActionButtons: React.FC = () => (
  <div className="mt-3 flex gap-2">
    <button className="flex-1 bg-indigo-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-indigo-700 transition-colors">
      Implement Now
    </button>
    <button className="flex-1 bg-gray-100 text-gray-700 px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-gray-200 transition-colors">
      Schedule Later
    </button>
  </div>
);

interface RecommendationCardProps {
  recommendation: RecommendationItem;
  isExpanded: boolean;
  onToggle: () => void;
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendation,
  isExpanded,
  onToggle
}) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.95 }}
    animate={{ opacity: 1, scale: 1 }}
    className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
  >
    <div className="p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h4 className="font-semibold text-gray-900 flex items-center">
            {recommendation.impact && getImpactIcon(recommendation.impact)}
            <span className="ml-2">{recommendation.title}</span>
          </h4>
          {recommendation.confidence_score && (
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium mt-2 ${getConfidenceColor(recommendation.confidence_score)}`}>
              {(recommendation.confidence_score * 100).toFixed(0)}% confidence
            </span>
          )}
        </div>
        <button
          onClick={onToggle}
          className="ml-2 p-1 hover:bg-gray-100 rounded"
        >
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>

      <p className="text-sm text-gray-600 mb-3">{recommendation.description}</p>

      {/* Key Metrics */}
      <div className="flex flex-wrap gap-2 mb-3">
        {recommendation.metrics?.potential_savings && (
          <MetricBadge
            label="Save"
            value={`$${recommendation.metrics.potential_savings.toLocaleString()}/mo`}
            bgColor="bg-green-50"
            textColor="text-green-700"
          />
        )}
        {recommendation.metrics?.latency_reduction && (
          <MetricBadge
            label=""
            value={`${recommendation.metrics.latency_reduction}ms faster`}
            bgColor="bg-blue-50"
            textColor="text-blue-700"
          />
        )}
        {recommendation.metrics?.throughput_increase && (
          <MetricBadge
            label=""
            value={`+${recommendation.metrics.throughput_increase}% throughput`}
            bgColor="bg-purple-50"
            textColor="text-purple-700"
          />
        )}
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="pt-3 border-t border-gray-200"
          >
            {recommendation.implementation_steps && (
              <ImplementationSteps steps={recommendation.implementation_steps} />
            )}
            <ActionButtons />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  </motion.div>
);

export const EnhancedRecommendations: React.FC<EnhancedRecommendationsProps> = ({ recommendations }) => {
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

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-800 flex items-center mb-4">
        <Package className="w-4 h-4 mr-2 text-indigo-600" />
        Optimization Recommendations
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {recommendations.map((rec) => (
          <RecommendationCard
            key={rec.id}
            recommendation={rec}
            isExpanded={rec.id ? expandedCards.has(rec.id) : false}
            onToggle={() => rec.id && toggleCard(rec.id)}
          />
        ))}
      </div>
    </div>
  );
};