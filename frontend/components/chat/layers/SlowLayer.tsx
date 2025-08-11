"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, Clock, Cpu, TrendingUp, AlertCircle } from 'lucide-react';
import type { SlowLayerProps } from '@/types/unified-chat';

export const SlowLayer: React.FC<SlowLayerProps> = ({ data, isCollapsed }) => {
  if (!data) return null;

  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high': return 'text-red-600 bg-red-50';
      case 'medium': return 'text-yellow-600 bg-yellow-50';
      case 'low': return 'text-green-600 bg-green-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

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
        {/* Completed Agents Section */}
        {data.completedAgents && data.completedAgents.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
              <CheckCircle className="w-4 h-4 mr-2 text-green-600" />
              Completed Agents
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {data.completedAgents.map((agent, index) => (
                <motion.div
                  key={`${agent.agentName}-${index}`}
                  className="rounded-lg p-3 border hover:shadow-md transition-all duration-200"
                  style={{
                    background: 'rgba(255, 255, 255, 0.9)',
                    backdropFilter: 'blur(8px)',
                    border: '1px solid rgba(255, 255, 255, 0.18)',
                    boxShadow: '0 2px 4px 0 rgba(0, 0, 0, 0.05)'
                  }}
                  whileHover={{ scale: 1.02 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-sm text-gray-800">
                      {agent.agentName}
                    </span>
                    <span className="text-xs text-gray-500 flex items-center">
                      <Clock className="w-3 h-3 mr-1" />
                      {formatDuration(agent.duration)}
                    </span>
                  </div>
                  {agent.metrics && (
                    <div className="text-xs text-gray-600 space-y-1">
                      {Object.entries(agent.metrics).slice(0, 3).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span>{key.replace(/_/g, ' ')}:</span>
                          <span className="font-mono">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Final Report Section */}
        {data.finalReport && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="space-y-4"
          >
            {/* Recommendations */}
            {data.finalReport.recommendations && data.finalReport.recommendations.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  <TrendingUp className="w-4 h-4 mr-2 text-blue-600" />
                  Optimization Recommendations
                </h3>
                <div className="space-y-3">
                  {data.finalReport.recommendations.map((rec) => (
                    <motion.div
                      key={rec.id}
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
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-medium text-gray-800">{rec.title}</h4>
                        <div className="flex space-x-2">
                          <span className={`text-xs px-2 py-1 rounded-full ${getImpactColor(rec.impact)}`}>
                            {rec.impact} impact
                          </span>
                          <span className={`text-xs px-2 py-1 rounded-full ${getImpactColor(rec.effort)}`}>
                            {rec.effort} effort
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{rec.description}</p>
                      {rec.metrics && (
                        <div className="flex flex-wrap gap-3 text-xs">
                          {rec.metrics.potential_savings && (
                            <span className="text-green-600 font-mono">
                              ${rec.metrics.potential_savings.toLocaleString()} savings
                            </span>
                          )}
                          {rec.metrics.latency_reduction && (
                            <span className="text-blue-600 font-mono">
                              {rec.metrics.latency_reduction}ms faster
                            </span>
                          )}
                          {rec.metrics.throughput_increase && (
                            <span className="text-purple-600 font-mono">
                              {rec.metrics.throughput_increase}% throughput ↑
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Plan */}
            {data.finalReport.actionPlan && data.finalReport.actionPlan.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  <AlertCircle className="w-4 h-4 mr-2 text-orange-600" />
                  Implementation Action Plan
                </h3>
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <ol className="space-y-3">
                    {data.finalReport.actionPlan.map((step) => (
                      <li key={step.id} className="flex">
                        <span className="font-mono text-xs text-gray-500 mr-3 mt-0.5">
                          {String(step.step_number).padStart(2, '0')}
                        </span>
                        <div className="flex-1">
                          <p className="text-sm text-gray-800 mb-1">{step.description}</p>
                          {step.command && (
                            <code className="text-xs bg-gray-100 px-2 py-1 rounded font-mono block mb-1">
                              {step.command}
                            </code>
                          )}
                          <p className="text-xs text-gray-600 italic">{step.expected_outcome}</p>
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            )}

            {/* Execution Metrics */}
            {data.metrics && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  <Cpu className="w-4 h-4 mr-2 text-indigo-600" />
                  Execution Metrics
                </h3>
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Total Duration:</span>
                      <span className="font-mono ml-2 text-gray-800">
                        {formatDuration(data.metrics.total_duration_ms)}
                      </span>
                    </div>
                    {data.metrics.total_tokens && (
                      <div>
                        <span className="text-gray-600">Tokens Used:</span>
                        <span className="font-mono ml-2 text-gray-800">
                          {data.metrics.total_tokens.toLocaleString()}
                        </span>
                      </div>
                    )}
                    {data.metrics.total_cost !== undefined && (
                      <div>
                        <span className="text-gray-600">Cost:</span>
                        <span className="font-mono ml-2 text-gray-800">
                          ${data.metrics.total_cost.toFixed(4)}
                        </span>
                      </div>
                    )}
                    {data.metrics.cache_efficiency !== undefined && (
                      <div>
                        <span className="text-gray-600">Cache Hit Rate:</span>
                        <span className="font-mono ml-2 text-gray-800">
                          {(data.metrics.cache_efficiency * 100).toFixed(1)}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
};