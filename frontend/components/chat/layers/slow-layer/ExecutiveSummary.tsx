"use client";

import React from 'react';
import { motion } from 'framer-motion';
import {
  Target, DollarSign, ArrowUpRight, Shield
} from 'lucide-react';
import type { ReportData } from './types';

interface ExecutiveSummaryProps {
  data: ReportData;
}

export const ExecutiveSummary: React.FC<ExecutiveSummaryProps> = ({ data }) => {
  if (!data.finalReport?.executive_summary) return null;

  const savingsAmount = data.finalReport.cost_analysis?.total_savings || 0;
  const optimizationPotential = data.finalReport.performance_comparison?.improvement_percentage || 0;
  const confidenceScore = data.finalReport.confidence_scores?.overall || 0.85;

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
            {(confidenceScore * 100).toFixed(0)}%
          </div>
        </div>
      </div>
    </motion.div>
  );
};