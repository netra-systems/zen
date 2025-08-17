import React from 'react';
import { AlertCircle, RefreshCcw, Home, Bug } from 'lucide-react';
import { motion } from 'framer-motion';

interface ErrorHeaderProps {
  errorCount: number;
  maxRetries: number;
}

export const ErrorHeader: React.FC<ErrorHeaderProps> = ({ 
  errorCount, 
  maxRetries 
}) => (
  <div className="bg-gradient-to-r from-red-50 to-orange-50 p-6 border-b border-red-100">
    <div className="flex items-center space-x-3">
      <div className="p-3 bg-red-100 rounded-full">
        <AlertCircle className="w-6 h-6 text-red-600" />
      </div>
      <ErrorHeaderContent errorCount={errorCount} maxRetries={maxRetries} />
    </div>
  </div>
);

const ErrorHeaderContent: React.FC<ErrorHeaderProps> = ({ 
  errorCount, 
  maxRetries 
}) => (
  <div>
    <h1 className="text-xl font-bold text-gray-900">
      Oops! Something went wrong
    </h1>
    <ErrorSubtitle errorCount={errorCount} maxRetries={maxRetries} />
  </div>
);

const ErrorSubtitle: React.FC<ErrorHeaderProps> = ({ 
  errorCount, 
  maxRetries 
}) => (
  <p className="text-sm text-gray-600 mt-1">
    {errorCount > 1 && `Retry attempt ${errorCount} of ${maxRetries} • `}
    The application encountered an unexpected error
  </p>
);

interface ErrorDetailsProps {
  error: Error;
}

export const ErrorDetails: React.FC<ErrorDetailsProps> = ({ error }) => (
  <div className="p-6 space-y-4">
    <ErrorMessage error={error} />
    <TechnicalDetails error={error} />
  </div>
);

const ErrorMessage: React.FC<ErrorDetailsProps> = ({ error }) => (
  <div className="bg-red-50 rounded-lg p-4 border border-red-200">
    <h2 className="text-sm font-semibold text-red-900 mb-2">
      Error Message
    </h2>
    <p className="text-sm text-red-800 font-mono">{error.message}</p>
  </div>
);

const TechnicalDetails: React.FC<ErrorDetailsProps> = ({ error }) => {
  if (process.env.NODE_ENV !== 'development') return null;
  
  return (
    <details className="bg-gray-50 rounded-lg p-4 border border-gray-200">
      <summary className="cursor-pointer text-sm font-semibold text-gray-700 hover:text-gray-900">
        Technical Details (Development Only)
      </summary>
      <pre className="mt-3 text-xs text-gray-600 overflow-auto max-h-48">
        {error.stack}
      </pre>
    </details>
  );
};

interface ActionButtonsProps {
  onReset: () => void;
  onReload: () => void;
  onGoHome: () => void;
  onDownloadReport: () => void;
}

export const ActionButtons: React.FC<ActionButtonsProps> = ({
  onReset,
  onReload,
  onGoHome,
  onDownloadReport
}) => (
  <div className="flex flex-wrap gap-3 pt-2">
    <ResetButton onClick={onReset} />
    <ReloadButton onClick={onReload} />
    <HomeButton onClick={onGoHome} />
    <ReportButton onClick={onDownloadReport} />
  </div>
);

const ResetButton: React.FC<{ onClick: () => void }> = ({ onClick }) => (
  <button
    onClick={onClick}
    className="flex items-center space-x-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg transition-colors"
  >
    <RefreshCcw className="w-4 h-4" />
    <span>Try Again</span>
  </button>
);

const ReloadButton: React.FC<{ onClick: () => void }> = ({ onClick }) => (
  <button
    onClick={onClick}
    className="flex items-center space-x-2 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
  >
    <RefreshCcw className="w-4 h-4" />
    <span>Reload Page</span>
  </button>
);

const HomeButton: React.FC<{ onClick: () => void }> = ({ onClick }) => (
  <button
    onClick={onClick}
    className="flex items-center space-x-2 px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors"
  >
    <Home className="w-4 h-4" />
    <span>Go Home</span>
  </button>
);

const ReportButton: React.FC<{ onClick: () => void }> = ({ onClick }) => (
  <button
    onClick={onClick}
    className="flex items-center space-x-2 px-4 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg transition-colors"
  >
    <Bug className="w-4 h-4" />
    <span>Download Report</span>
  </button>
);

interface AutoRetryIndicatorProps {
  shouldShow: boolean;
}

export const AutoRetryIndicator: React.FC<AutoRetryIndicatorProps> = ({ 
  shouldShow 
}) => {
  if (!shouldShow) return null;
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex items-center space-x-2 text-sm text-amber-600 bg-amber-50 rounded-lg p-3"
    >
      <SpinningIcon />
      <span>Automatically retrying...</span>
    </motion.div>
  );
};

const SpinningIcon: React.FC = () => (
  <motion.div
    animate={{ rotate: 360 }}
    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
  >
    <RefreshCcw className="w-4 h-4" />
  </motion.div>
);

interface ErrorContainerProps {
  children: React.ReactNode;
}

export const ErrorContainer: React.FC<ErrorContainerProps> = ({ children }) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className="max-w-2xl w-full"
    >
      <div className="bg-white/95 backdrop-blur-lg rounded-2xl shadow-xl border border-red-100 overflow-hidden">
        {children}
      </div>
    </motion.div>
  </div>
);