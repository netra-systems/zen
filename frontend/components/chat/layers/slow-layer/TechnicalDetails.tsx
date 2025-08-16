"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { FileText } from 'lucide-react';

interface TechnicalDetailsProps {
  technicalDetails: any;
}

export const TechnicalDetails: React.FC<TechnicalDetailsProps> = ({ technicalDetails }) => {
  if (!technicalDetails) return null;

  return (
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
};