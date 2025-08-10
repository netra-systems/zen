import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  CheckCircle2, 
  ChevronDown, 
  ChevronRight, 
  Clock, 
  Code, 
  Database, 
  FileText, 
  LineChart, 
  Package, 
  Zap, 
  TrendingUp,
  AlertCircle,
  Download,
  Copy
} from 'lucide-react';

interface FinalReportProps {
  reportData: {
    data_result?: Record<string, unknown>;
    optimizations_result?: Record<string, unknown>;
    action_plan_result?: Array<Record<string, unknown>> | Record<string, unknown>;
    report_result?: Record<string, unknown>;
    final_report?: string;
    execution_metrics?: {
      total_duration: number;
      agent_timings: {
        agent_name: string;
        duration: number;
        start_time: string;
        end_time: string;
      }[];
      tool_calls: {
        tool_name: string;
        count: number;
        avg_duration: number;
      }[];
    };
  };
}

export const FinalReportView: React.FC<FinalReportProps> = ({ reportData }) => {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    summary: true,
    data: false,
    optimizations: false,
    actions: false,
    metrics: false,
    raw: false
  });

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const downloadReport = () => {
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `netra-report-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  return (
    <div className="w-full max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200">
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <CardTitle className="text-2xl font-bold text-gray-900">
                Optimization Analysis Report
              </CardTitle>
              <p className="text-sm text-gray-600 mt-2">
                Generated at {new Date().toLocaleString()}
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={downloadReport}>
                <Download className="w-4 h-4 mr-1" />
                Download
              </Button>
              <Button variant="outline" size="sm" onClick={() => copyToClipboard(JSON.stringify(reportData))}>
                <Copy className="w-4 h-4 mr-1" />
                Copy
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Executive Summary */}
      {reportData.final_report && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              Executive Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose max-w-none">
              <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                {reportData.final_report}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="data">Data Analysis</TabsTrigger>
          <TabsTrigger value="optimizations">Optimizations</TabsTrigger>
          <TabsTrigger value="actions">Action Plan</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Key Metrics Cards */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Total Duration</p>
                    <p className="text-2xl font-bold">
                      {formatDuration(reportData.execution_metrics?.total_duration || 0)}
                    </p>
                  </div>
                  <Clock className="w-8 h-8 text-blue-500" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Agents Used</p>
                    <p className="text-2xl font-bold">
                      {reportData.execution_metrics?.agent_timings?.length || 0}
                    </p>
                  </div>
                  <Package className="w-8 h-8 text-green-500" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Tool Calls</p>
                    <p className="text-2xl font-bold">
                      {reportData.execution_metrics?.tool_calls?.reduce((sum, t) => sum + t.count, 0) || 0}
                    </p>
                  </div>
                  <Zap className="w-8 h-8 text-purple-500" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Agent Timeline */}
          {reportData.execution_metrics?.agent_timings && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Agent Execution Timeline</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {reportData.execution_metrics.agent_timings.map((timing, idx) => (
                  <div key={idx} className="flex items-center gap-4">
                    <Badge variant="outline" className="min-w-[140px]">
                      {timing.agent_name}
                    </Badge>
                    <div className="flex-1">
                      <Progress 
                        value={(timing.duration / reportData.execution_metrics!.total_duration) * 100} 
                        className="h-2"
                      />
                    </div>
                    <span className="text-sm text-gray-600 min-w-[60px] text-right">
                      {formatDuration(timing.duration)}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Data Analysis Tab */}
        <TabsContent value="data" className="space-y-4">
          {reportData.data_result && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="w-5 h-5 text-blue-600" />
                  Data Analysis Results
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-50 rounded-lg p-4">
                  <pre className="text-sm overflow-x-auto">
                    {JSON.stringify(reportData.data_result, null, 2)}
                  </pre>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Optimizations Tab */}
        <TabsContent value="optimizations" className="space-y-4">
          {reportData.optimizations_result && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-green-600" />
                  Optimization Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {typeof reportData.optimizations_result === 'object' && 
                   Object.entries(reportData.optimizations_result).map(([key, value]) => (
                    <Collapsible key={key} open={expandedSections[key]} onOpenChange={() => toggleSection(key)}>
                      <CollapsibleTrigger className="flex items-center gap-2 w-full p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                        {expandedSections[key] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        <span className="font-medium capitalize">{key.replace(/_/g, ' ')}</span>
                      </CollapsibleTrigger>
                      <CollapsibleContent className="mt-2 p-3 bg-white border rounded-lg">
                        <pre className="text-sm overflow-x-auto">
                          {JSON.stringify(value, null, 2)}
                        </pre>
                      </CollapsibleContent>
                    </Collapsible>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Action Plan Tab */}
        <TabsContent value="actions" className="space-y-4">
          {reportData.action_plan_result && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-green-600" />
                  Implementation Action Plan
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Array.isArray(reportData.action_plan_result) ? (
                    reportData.action_plan_result.map((action, idx) => (
                      <Alert key={idx} className="border-l-4 border-l-blue-500">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>
                          <div className="font-medium mb-1">Step {idx + 1}</div>
                          <div className="text-sm text-gray-600">{JSON.stringify(action)}</div>
                        </AlertDescription>
                      </Alert>
                    ))
                  ) : (
                    <div className="bg-gray-50 rounded-lg p-4">
                      <pre className="text-sm overflow-x-auto">
                        {JSON.stringify(reportData.action_plan_result, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Metrics Tab */}
        <TabsContent value="metrics" className="space-y-4">
          {reportData.execution_metrics && (
            <>
              {/* Tool Usage Stats */}
              {reportData.execution_metrics.tool_calls && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <LineChart className="w-5 h-5 text-purple-600" />
                      Tool Usage Statistics
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {reportData.execution_metrics.tool_calls.map((tool, idx) => (
                        <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div className="flex items-center gap-3">
                            <Code className="w-4 h-4 text-gray-600" />
                            <span className="font-medium">{tool.tool_name}</span>
                          </div>
                          <div className="flex items-center gap-4">
                            <Badge variant="secondary">{tool.count} calls</Badge>
                            <Badge variant="outline">avg {formatDuration(tool.avg_duration)}</Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>

      {/* Raw Data Viewer */}
      <Collapsible open={expandedSections.raw} onOpenChange={() => toggleSection('raw')}>
        <Card>
          <CollapsibleTrigger className="w-full">
            <CardHeader className="cursor-pointer hover:bg-gray-50 transition-colors">
              <CardTitle className="flex items-center gap-2 text-base">
                {expandedSections.raw ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <Code className="w-4 h-4" />
                Raw Report Data
              </CardTitle>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent>
              <div className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto">
                <pre className="text-xs">
                  {JSON.stringify(reportData, null, 2)}
                </pre>
              </div>
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>
    </div>
  );
};