"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Shield, Database, Sparkles, Users, Settings, FileText, CheckCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AdminFeatureProps } from '@/types/component-props';

const ADMIN_TYPE_CONFIG = {
  corpus: {
    icon: Database,
    color: 'purple',
    label: 'Corpus Management'
  },
  synthetic: {
    icon: Sparkles,
    color: 'indigo',
    label: 'Synthetic Data'
  },
  users: {
    icon: Users,
    color: 'blue',
    label: 'User Management'
  },
  config: {
    icon: Settings,
    color: 'gray',
    label: 'System Configuration'
  },
  logs: {
    icon: FileText,
    color: 'green',
    label: 'Log Analysis'
  }
};

export const AdminHeader: React.FC<AdminFeatureProps> = ({
  adminType,
  adminStatus = 'pending',
  adminMetadata
}) => {
  if (!adminType) return null;

  const adminConfig = ADMIN_TYPE_CONFIG[adminType];
  const AdminIcon = adminConfig?.icon || Shield;

  return (
    <div className="glass-accent-purple backdrop-blur-md text-purple-900 px-4 py-3 border-b border-purple-200">
      <div className="flex items-center justify-between">
        <AdminBadge adminConfig={adminConfig} AdminIcon={AdminIcon} />
        <AdminStatus adminStatus={adminStatus} />
      </div>
      {adminMetadata && (
        <AdminProgress adminMetadata={adminMetadata} />
      )}
    </div>
  );
};

const AdminBadge: React.FC<{
  adminConfig: typeof ADMIN_TYPE_CONFIG[keyof typeof ADMIN_TYPE_CONFIG];
  AdminIcon: React.ComponentType<{ className?: string }>;
}> = ({ adminConfig, AdminIcon }) => (
  <div className="flex items-center space-x-3">
    <div className="flex items-center space-x-2 px-3 py-1 bg-white/20 rounded-full">
      <AdminIcon className="w-4 h-4" />
      <span className="text-sm font-medium">{adminConfig.label}</span>
    </div>
    <Shield className="w-4 h-4 opacity-60" />
    <span className="text-xs opacity-80">Admin Operation</span>
  </div>
);

const AdminStatus: React.FC<{ adminStatus: string }> = ({ adminStatus }) => (
  <div className="flex items-center space-x-2">
    {adminStatus === 'in_progress' && (
      <>
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="text-sm">Processing...</span>
      </>
    )}
    {adminStatus === 'completed' && (
      <>
        <CheckCircle className="w-4 h-4" />
        <span className="text-sm">Completed</span>
      </>
    )}
  </div>
);

const AdminProgress: React.FC<{ adminMetadata: NonNullable<AdminFeatureProps['adminMetadata']> }> = ({ adminMetadata }) => {
  if (!adminMetadata.totalRecords || !adminMetadata.recordsProcessed) return null;

  return (
    <div className="mt-3">
      <ProgressBar 
        current={adminMetadata.recordsProcessed}
        total={adminMetadata.totalRecords}
      />
      {adminMetadata.estimatedTime && (
        <p className="text-xs mt-1 opacity-80">ETA: {adminMetadata.estimatedTime}</p>
      )}
    </div>
  );
};

const ProgressBar: React.FC<{ current: number; total: number }> = ({ current, total }) => {
  const percentage = (current / total) * 100;
  
  return (
    <>
      <div className="flex items-center justify-between text-xs mb-1">
        <span>Progress</span>
        <span>{current} / {total}</span>
      </div>
      <div className="w-full bg-white/20 rounded-full h-2">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5 }}
          className="bg-white rounded-full h-2"
        />
      </div>
    </>
  );
};

export const AdminResults: React.FC<AdminFeatureProps> = ({
  adminType,
  adminStatus,
  adminMetadata
}) => {
  if (!adminType || !adminMetadata || adminStatus !== 'completed') return null;

  return (
    <div className="p-4 bg-purple-50 border-t border-purple-200">
      <AdminAuditTrail adminMetadata={adminMetadata} />
      <AdminActionButtons adminMetadata={adminMetadata} />
      <AdminNextSteps adminType={adminType} />
    </div>
  );
};

const AdminAuditTrail: React.FC<{ adminMetadata: NonNullable<AdminFeatureProps['adminMetadata']> }> = ({ adminMetadata }) => {
  if (!adminMetadata.auditInfo) return null;

  return (
    <div className="text-xs text-purple-700 space-y-1 mb-3">
      <p>Performed by: {adminMetadata.auditInfo.user}</p>
      <p>At: {adminMetadata.auditInfo.timestamp}</p>
      <p>Action: {adminMetadata.auditInfo.action}</p>
    </div>
  );
};

const AdminActionButtons: React.FC<{ adminMetadata: NonNullable<AdminFeatureProps['adminMetadata']> }> = ({ adminMetadata }) => (
  <div className="flex items-center space-x-2 mb-3">
    {adminMetadata.rollbackAvailable && (
      <ActionButton>Rollback</ActionButton>
    )}
    <ActionButton>View Details</ActionButton>
    <ActionButton>Export Log</ActionButton>
  </div>
);

const ActionButton: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <button className="px-3 py-1 text-xs bg-white text-purple-600 border border-purple-300 rounded-md hover:bg-purple-50 transition-colors">
    {children}
  </button>
);

const AdminNextSteps: React.FC<{ adminType: string }> = ({ adminType }) => (
  <div className="pt-2 border-t border-purple-200">
    <p className="text-xs font-medium text-purple-900 mb-1">Suggested Next Steps:</p>
    <NextStepsList adminType={adminType} />
  </div>
);

const NextStepsList: React.FC<{ adminType: string }> = ({ adminType }) => {
  const steps = getNextSteps(adminType);
  
  return (
    <ul className="text-xs text-purple-700 space-y-1">
      {steps.map((step, index) => (
        <li key={index}>• {step}</li>
      ))}
    </ul>
  );
};

const getNextSteps = (adminType: string): string[] => {
  switch (adminType) {
    case 'corpus':
      return [
        'Validate corpus integrity',
        'Generate test queries',
        'Review corpus coverage'
      ];
    case 'synthetic':
      return [
        'Analyze generated patterns',
        'Run performance tests',
        'Export data for analysis'
      ];
    case 'users':
      return [
        'Send welcome emails',
        'Review permission assignments',
        'Generate access report'
      ];
    default:
      return [];
  }
};
