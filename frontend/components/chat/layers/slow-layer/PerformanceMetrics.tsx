"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity, ChevronDown, ChevronRight, Zap, Gauge, Brain,
  ArrowDownRight, ArrowUpRight
} from 'lucide-react';
import type { ReportData } from '@/types/report-data';

interface PerformanceMetricsProps {
  data: ReportData;
}

interface MetricCardProps {
  title: string;
  icon: React.ReactNode;
  current: string | number;
  projected: string | number;
  improvement: string | number;
  unit: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
  isIncrease?: boolean;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title, icon, current, projected, improvement, unit,
  bgColor, textColor, borderColor, isIncrease = true
}) => (
  <div className={`${bgColor} rounded-lg p-4`}>
    <div className="flex items-center justify-between mb-2">
      <span className={`text-xs font-semibold ${textColor}`}>{title}</span>
      {icon}
    </div>
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-xs text-gray-600">Current</span>
        <span className="text-sm font-mono">{current}{unit}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-xs text-gray-600">Projected</span>
        <span className={`text-sm font-mono ${textColor}`}>{projected}{unit}</span>
      </div>
      <div className={`pt-2 border-t ${borderColor}`}>
        <div className="flex items-center justify-center">
          {isIncrease ? 
            <ArrowUpRight className="w-4 h-4 text-green-600 mr-1" /> :
            <ArrowDownRight className="w-4 h-4 text-green-600 mr-1" />
          }
          <span className="text-sm font-bold text-green-600">
            {improvement}
          </span>
        </div>
      </div>
    </div>
  </div>
);

export const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({ data }) => {
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
              <MetricCard
                title="Response Time"
                icon={<Zap className="w-4 h-4 text-blue-600" />}
                current={perfData.response_time_current || '250'}
                projected={perfData.response_time_projected || '150'}
                improvement={`${perfData.response_time_improvement || '40'}% faster`}
                unit="ms"
                bgColor="bg-blue-50"
                textColor="text-blue-600"
                borderColor="border-blue-200"
                isIncrease={false}
              />

              {/* Throughput */}
              <MetricCard
                title="Throughput"
                icon={<Gauge className="w-4 h-4 text-purple-600" />}
                current={perfData.throughput_current || '1000'}
                projected={perfData.throughput_projected || '1500'}
                improvement={`${perfData.throughput_improvement || '50'}% increase`}
                unit=" req/s"
                bgColor="bg-purple-50"
                textColor="text-purple-600"
                borderColor="border-purple-200"
                isIncrease={true}
              />

              {/* Quality Score */}
              <MetricCard
                title="Quality Score"
                icon={<Brain className="w-4 h-4 text-orange-600" />}
                current={perfData.quality_current || '92'}
                projected={perfData.quality_projected || '96'}
                improvement={`${perfData.quality_improvement || '4'}% better`}
                unit="%"
                bgColor="bg-orange-50"
                textColor="text-orange-600"
                borderColor="border-orange-200"
                isIncrease={true}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};