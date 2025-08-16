"use client";

import React from 'react';
import { Download, Share2, Send } from 'lucide-react';

interface ExportButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
}

const ExportButton: React.FC<ExportButtonProps> = ({ icon, label, onClick }) => (
  <button 
    onClick={onClick}
    className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
  >
    {icon}
    {label}
  </button>
);

export const ExportControls: React.FC = () => {
  const handleExportReport = () => {
    // TODO: Implement export functionality
    console.log('Export report clicked');
  };

  const handleShare = () => {
    // TODO: Implement share functionality
    console.log('Share clicked');
  };

  const handleEmailReport = () => {
    // TODO: Implement email functionality
    console.log('Email report clicked');
  };

  return (
    <div className="flex items-center gap-2 mt-6">
      <ExportButton
        icon={<Download className="w-4 h-4" />}
        label="Export Report"
        onClick={handleExportReport}
      />
      <ExportButton
        icon={<Share2 className="w-4 h-4" />}
        label="Share"
        onClick={handleShare}
      />
      <ExportButton
        icon={<Send className="w-4 h-4" />}
        label="Email Report"
        onClick={handleEmailReport}
      />
    </div>
  );
};