"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { DollarSign, ChevronDown, ChevronRight } from 'lucide-react';
import type { ReportData } from './types';

interface CostAnalysisProps {
  data: ReportData;
}

const CostItem: React.FC<{
  service: string;
  cost: number;
  className?: string;
  borderClassName?: string;
}> = ({ service, cost, className = "text-gray-700", borderClassName = "border-gray-200" }) => (
  <div className={`flex justify-between items-center py-2 border-b ${borderClassName} last:border-0`}>
    <span className={`text-sm ${className}`}>{service}</span>
    <span className={`text-sm font-mono font-medium ${className.replace('text-gray-700', 'text-gray-900')}`}>
      ${cost.toLocaleString()}
    </span>
  </div>
);

const CostTotal: React.FC<{
  total: number;
  className?: string;
  borderClassName?: string;
}> = ({ total, className = "text-gray-700", borderClassName = "border-gray-300" }) => (
  <div className={`mt-3 pt-3 border-t ${borderClassName}`}>
    <div className="flex justify-between items-center">
      <span className={`text-sm font-semibold ${className}`}>Total</span>
      <span className={`text-sm font-mono font-bold ${className.replace('text-gray-700', 'text-gray-900')}`}>
        ${total.toLocaleString()}
      </span>
    </div>
  </div>
);

export const CostAnalysis: React.FC<CostAnalysisProps> = ({ data }) => {
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
                  <CostItem key={service} service={service} cost={cost as number} />
                ))}
                <CostTotal total={costData.total_current || 0} />
              </div>

              {/* Projected Costs */}
              <div className="bg-emerald-50 rounded-lg p-4">
                <h4 className="text-xs font-semibold text-emerald-700 mb-3">Projected Monthly Costs</h4>
                {Object.entries(costData.projected_costs || {}).map(([service, cost]) => (
                  <CostItem
                    key={service}
                    service={service}
                    cost={cost as number}
                    className="text-emerald-700"
                    borderClassName="border-emerald-200"
                  />
                ))}
                <CostTotal
                  total={costData.total_projected || 0}
                  className="text-emerald-700"
                  borderClassName="border-emerald-300"
                />
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