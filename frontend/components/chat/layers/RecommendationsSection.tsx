// Recommendations Section Component
// Business Value: AI optimization recommendations for Growth & Enterprise customers

import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp } from 'lucide-react';
import { getImpactColor } from './slow-layer-utils';

interface Recommendation {
  id: string;
  title: string;
  description: string;
  impact: string;
  effort: string;
  metrics?: {
    potential_savings?: number;
    latency_reduction?: number;
    throughput_increase?: number;
  };
}

interface RecommendationsSectionProps {
  recommendations: Recommendation[];
}

export const RecommendationsSection: React.FC<RecommendationsSectionProps> = ({ 
  recommendations 
}) => {
  if (!recommendations || recommendations.length === 0) {
    return null;
  }

  return (
    <div>
      <RecommendationsHeader />
      <RecommendationsList recommendations={recommendations} />
    </div>
  );
};

const RecommendationsHeader = () => (
  <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
    <TrendingUp className="w-4 h-4 mr-2 text-blue-600" />
    Optimization Recommendations
  </h3>
);

const RecommendationsList = ({ recommendations }: { recommendations: Recommendation[] }) => (
  <div className="space-y-3">
    {recommendations.map((rec) => (
      <RecommendationCard key={rec.id} recommendation={rec} />
    ))}
  </div>
);

const RecommendationCard = ({ recommendation }: { recommendation: Recommendation }) => (
  <motion.div
    className="rounded-lg p-4 border hover:shadow-md transition-all duration-200"
    style={{
      background: 'rgba(255, 255, 255, 0.95)',
      backdropFilter: 'blur(8px)',
      border: '1px solid rgba(255, 255, 255, 0.18)',
      boxShadow: '0 2px 6px 0 rgba(0, 0, 0, 0.05)'
    }}
    whileHover={{ scale: 1.01 }}
    whileTap={{ scale: 0.99 }}
    transition={{ duration: 0.2 }}
  >
    <RecommendationHeader recommendation={recommendation} />
    <RecommendationDescription description={recommendation.description} />
    {recommendation.metrics && (
      <RecommendationMetrics metrics={recommendation.metrics} />
    )}
  </motion.div>
);

const RecommendationHeader = ({ recommendation }: { recommendation: Recommendation }) => (
  <div className="flex items-start justify-between mb-2">
    <h4 className="font-medium text-gray-800">{recommendation.title}</h4>
    <RecommendationBadges 
      impact={recommendation.impact}
      effort={recommendation.effort}
    />
  </div>
);

const RecommendationBadges = ({ impact, effort }: { 
  impact: string; 
  effort: string; 
}) => (
  <div className="flex space-x-2">
    <span className={`text-xs px-2 py-1 rounded-full ${getImpactColor(impact)}`}>
      {impact} impact
    </span>
    <span className={`text-xs px-2 py-1 rounded-full ${getImpactColor(effort)}`}>
      {effort} effort
    </span>
  </div>
);

const RecommendationDescription = ({ description }: { description: string }) => (
  <p className="text-sm text-gray-600 mb-2">{description}</p>
);

const RecommendationMetrics = ({ metrics }: { 
  metrics: {
    potential_savings?: number;
    latency_reduction?: number;
    throughput_increase?: number;
  };
}) => (
  <div className="flex flex-wrap gap-3 text-xs">
    {metrics.potential_savings && (
      <span className="text-green-600 font-mono">
        ${metrics.potential_savings.toLocaleString()} savings
      </span>
    )}
    {metrics.latency_reduction && (
      <span className="text-blue-600 font-mono">
        {metrics.latency_reduction}ms faster
      </span>
    )}
    {metrics.throughput_increase && (
      <span className="text-purple-600 font-mono">
        {metrics.throughput_increase}% throughput ↑
      </span>
    )}
  </div>
);