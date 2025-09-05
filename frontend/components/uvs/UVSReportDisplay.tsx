/**
 * UVS Report Display - Renders different report types
 * 
 * CRITICAL: Implements all 4 UVS report types per UVS_REQUIREMENTS.md
 * (full, partial, guidance, fallback)
 * 
 * Business Value: Always delivers value to users regardless of data availability
 */

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { 
  AlertCircle, 
  CheckCircle, 
  HelpCircle, 
  TrendingUp,
  DollarSign,
  Zap,
  FileText,
  ChevronRight,
  Sparkles
} from 'lucide-react';

export interface UVSReport {
  report_type: 'full' | 'partial' | 'guidance' | 'fallback';
  message: string;
  has_data?: boolean;
  has_optimizations?: boolean;
  triage_result?: any;
  data_result?: any;
  optimizations_result?: any;
  exploration_questions?: string[];
  next_steps?: string[];
  data_collection_guide?: any;
  error_handled?: string;
}

interface UVSReportDisplayProps {
  report: UVSReport;
  onQuestionClick?: (question: string) => void;
  onNextStepClick?: (step: string) => void;
  onRetry?: () => void;
}

/**
 * Get report type configuration
 */
function getReportConfig(type: UVSReport['report_type']) {
  switch (type) {
    case 'full':
      return {
        icon: CheckCircle,
        iconColor: 'text-green-600',
        bgColor: 'bg-green-50 dark:bg-green-900/10',
        borderColor: 'border-green-200 dark:border-green-800',
        title: 'Complete Analysis',
        description: 'Full optimization report with data and recommendations'
      };
    case 'partial':
      return {
        icon: TrendingUp,
        iconColor: 'text-blue-600',
        bgColor: 'bg-blue-50 dark:bg-blue-900/10',
        borderColor: 'border-blue-200 dark:border-blue-800',
        title: 'Partial Analysis',
        description: 'Working with available data to provide insights'
      };
    case 'guidance':
      return {
        icon: HelpCircle,
        iconColor: 'text-purple-600',
        bgColor: 'bg-purple-50 dark:bg-purple-900/10',
        borderColor: 'border-purple-200 dark:border-purple-800',
        title: 'Getting Started',
        description: 'Let\'s explore your AI optimization needs together'
      };
    case 'fallback':
      return {
        icon: AlertCircle,
        iconColor: 'text-orange-600',
        bgColor: 'bg-orange-50 dark:bg-orange-900/10',
        borderColor: 'border-orange-200 dark:border-orange-800',
        title: 'Alternative Approach',
        description: 'Here\'s how I can still help you'
      };
  }
}

/**
 * Full Report Component
 */
const FullReport: React.FC<{ report: UVSReport }> = ({ report }) => {
  const optimizations = report.optimizations_result?.optimizations || [];
  const metrics = report.data_result?.metrics || {};
  
  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      {Object.keys(metrics).length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600">
                <DollarSign className="w-4 h-4 inline mr-1" />
                Monthly Spend
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                ${metrics.monthly_spend || '0'}
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600">
                <Zap className="w-4 h-4 inline mr-1" />
                API Calls
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {metrics.api_calls?.toLocaleString() || '0'}
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600">
                <TrendingUp className="w-4 h-4 inline mr-1" />
                Potential Savings
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                ${metrics.potential_savings || '0'}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
      
      {/* Optimizations */}
      {optimizations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recommended Optimizations</CardTitle>
            <CardDescription>
              Actionable steps to improve your AI efficiency
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {optimizations.map((opt: any, index: number) => (
              <div 
                key={index}
                className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-900/50"
              >
                <Badge className="mt-1">{opt.priority || 'Medium'}</Badge>
                <div className="flex-1">
                  <h4 className="font-medium">{opt.title}</h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {opt.description}
                  </p>
                  {opt.impact && (
                    <p className="text-sm text-green-600 dark:text-green-400 mt-2">
                      Estimated impact: {opt.impact}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

/**
 * Partial Report Component
 */
const PartialReport: React.FC<{ report: UVSReport }> = ({ report }) => {
  const hasData = report.has_data;
  const hasOptimizations = report.has_optimizations;
  
  return (
    <div className="space-y-4">
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Partial Analysis Available</AlertTitle>
        <AlertDescription>
          {hasData && !hasOptimizations && 
            "I have your data but need more information to generate optimizations."}
          {!hasData && hasOptimizations && 
            "I have optimization strategies but need your usage data for specific recommendations."}
          {hasData && hasOptimizations && 
            "Working with partial information to provide the best insights possible."}
        </AlertDescription>
      </Alert>
      
      {report.data_result && (
        <Card>
          <CardHeader>
            <CardTitle>Available Data Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-sm bg-gray-100 dark:bg-gray-900 p-3 rounded">
              {JSON.stringify(report.data_result, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

/**
 * Guidance Report Component
 */
const GuidanceReport: React.FC<{ 
  report: UVSReport;
  onQuestionClick?: (question: string) => void;
}> = ({ report, onQuestionClick }) => {
  const questions = report.exploration_questions || [];
  const guide = report.data_collection_guide;
  
  return (
    <div className="space-y-6">
      {/* Exploration Questions */}
      {questions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-600" />
              Let's Explore Your Needs
            </CardTitle>
            <CardDescription>
              Click on any question to get started
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {questions.map((question, index) => (
              <Button
                key={index}
                variant="outline"
                className="w-full justify-start text-left"
                onClick={() => onQuestionClick?.(question)}
              >
                <ChevronRight className="w-4 h-4 mr-2" />
                {question}
              </Button>
            ))}
          </CardContent>
        </Card>
      )}
      
      {/* Data Collection Guide */}
      {guide && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              How to Collect Your Data
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm max-w-none dark:prose-invert">
              {typeof guide === 'string' ? (
                <p>{guide}</p>
              ) : (
                <div>
                  {guide.steps?.map((step: string, index: number) => (
                    <div key={index} className="flex items-start gap-2 mb-2">
                      <span className="font-semibold">{index + 1}.</span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

/**
 * Fallback Report Component
 */
const FallbackReport: React.FC<{ 
  report: UVSReport;
  onRetry?: () => void;
}> = ({ report, onRetry }) => {
  const errorMessage = report.error_handled;
  
  return (
    <div className="space-y-4">
      <Alert className="border-orange-200 bg-orange-50 dark:bg-orange-900/10">
        <AlertCircle className="h-4 w-4 text-orange-600" />
        <AlertTitle>Alternative Assistance</AlertTitle>
        <AlertDescription>
          I encountered an issue but can still help you in other ways.
          {errorMessage && (
            <details className="mt-2">
              <summary className="cursor-pointer text-sm">Technical details</summary>
              <pre className="mt-1 text-xs">{errorMessage}</pre>
            </details>
          )}
        </AlertDescription>
      </Alert>
      
      {onRetry && (
        <Button onClick={onRetry} variant="outline" className="w-full">
          Try Again
        </Button>
      )}
    </div>
  );
};

/**
 * Main UVS Report Display Component
 */
export const UVSReportDisplay: React.FC<UVSReportDisplayProps> = ({
  report,
  onQuestionClick,
  onNextStepClick,
  onRetry
}) => {
  const config = getReportConfig(report.report_type);
  const Icon = config.icon;
  
  return (
    <Card className={`${config.bgColor} border-2 ${config.borderColor}`}>
      <CardHeader>
        <div className="flex items-start gap-3">
          <Icon className={`w-6 h-6 ${config.iconColor} mt-1`} />
          <div className="flex-1">
            <CardTitle>{config.title}</CardTitle>
            <CardDescription>{config.description}</CardDescription>
          </div>
          <Badge variant="outline">{report.report_type}</Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Main Message */}
        {report.message && (
          <div className="mb-6 p-4 bg-white dark:bg-gray-900 rounded-lg">
            <p className="text-gray-700 dark:text-gray-300">{report.message}</p>
          </div>
        )}
        
        {/* Report Type Specific Content */}
        {report.report_type === 'full' && <FullReport report={report} />}
        {report.report_type === 'partial' && <PartialReport report={report} />}
        {report.report_type === 'guidance' && (
          <GuidanceReport report={report} onQuestionClick={onQuestionClick} />
        )}
        {report.report_type === 'fallback' && (
          <FallbackReport report={report} onRetry={onRetry} />
        )}
        
        {/* Next Steps */}
        {report.next_steps && report.next_steps.length > 0 && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="text-sm">Recommended Next Steps</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {report.next_steps.map((step, index) => (
                  <Button
                    key={index}
                    variant="ghost"
                    size="sm"
                    className="w-full justify-start"
                    onClick={() => onNextStepClick?.(step)}
                  >
                    <ChevronRight className="w-3 h-3 mr-1" />
                    {step}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </CardContent>
    </Card>
  );
};