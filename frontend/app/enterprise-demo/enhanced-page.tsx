'use client';

import { NextPage } from 'next';
import { authService } from '@/auth';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ArrowRight, BarChart3, Brain, Database, Rocket, Shield, Sparkles, ChevronRight, CheckCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import WorkloadSelector from '@/components/demo/WorkloadSelector';
import { useChatStore } from '@/store/chat';
import { useAgent } from '@/hooks/useAgent';
import AgentStatusPanel from '@/components/chat/AgentStatusPanel';

const EnhancedEnterpriseDemoPage: NextPage = () => {
  const { user, loading } = authService.useAuth();
  const router = useRouter();
  const [demoStep, setDemoStep] = useState<'welcome' | 'workload' | 'generating' | 'analyzing' | 'results'>('welcome');
  const [selectedWorkload, setSelectedWorkload] = useState<string | null>(null);
  const [, setSyntheticDataGenerated] = useState(false);
  const { sendUserMessage } = useAgent();
  const { isProcessing } = useChatStore();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [loading, user, router]);

  const handleWorkloadSelect = (workloadId: string) => {
    setSelectedWorkload(workloadId);
    setDemoStep('generating');
    
    // Send message to generate synthetic data
    const message = `Generate synthetic ${workloadId} workload data for enterprise demo`;
    sendUserMessage(message);
    
    // Simulate generation completion
    setTimeout(() => {
      setSyntheticDataGenerated(true);
      setDemoStep('analyzing');
    }, 5000);
    
    // Move to results after analysis
    setTimeout(() => {
      setDemoStep('results');
    }, 10000);
  };

  const demoSteps = [
    {
      id: 'workload',
      title: 'Select Workload',
      description: 'Choose your industry profile',
      icon: <Database className="w-5 h-5" />
    },
    {
      id: 'generate',
      title: 'Generate Data',
      description: 'Create synthetic workload data',
      icon: <Sparkles className="w-5 h-5" />
    },
    {
      id: 'analyze',
      title: 'Analyze & Optimize',
      description: 'AI-powered optimization',
      icon: <Brain className="w-5 h-5" />
    },
    {
      id: 'results',
      title: 'View Results',
      description: 'See optimization metrics',
      icon: <BarChart3 className="w-5 h-5" />
    }
  ];

  const getCurrentStepIndex = () => {
    switch(demoStep) {
      case 'welcome': return -1;
      case 'workload': return 0;
      case 'generating': return 1;
      case 'analyzing': return 2;
      case 'results': return 3;
      default: return 0;
    }
  };

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Enhanced Agent Status Panel */}
      <AnimatePresence>
        {isProcessing && <AgentStatusPanel />}
      </AnimatePresence>

      {/* Header */}
      <div className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-30">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Badge variant="secondary" className="glass-accent-purple text-purple-900">
                <Sparkles className="h-3 w-3 mr-1" />
                Enterprise Demo
              </Badge>
              <h1 className="text-xl font-bold text-gray-900">
                Netra AI Optimization Platform
              </h1>
            </div>
            
            {/* Progress Steps */}
            <div className="hidden lg:flex items-center space-x-2">
              {demoSteps.map((step, index) => {
                const isActive = index === getCurrentStepIndex();
                const isCompleted = index < getCurrentStepIndex();
                
                return (
                  <div key={step.id} className="flex items-center">
                    <div className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-all ${
                      isActive ? 'bg-purple-100 text-purple-700' : 
                      isCompleted ? 'bg-green-50 text-green-700' : 
                      'bg-gray-50 text-gray-400'
                    }`}>
                      {isCompleted ? (
                        <CheckCircle className="w-4 h-4" />
                      ) : (
                        step.icon
                      )}
                      <span className="text-sm font-medium">{step.title}</span>
                    </div>
                    {index < demoSteps.length - 1 && (
                      <ChevronRight className="w-4 h-4 mx-2 text-gray-300" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto p-6">
        <AnimatePresence mode="wait">
          {/* Welcome Screen */}
          {demoStep === 'welcome' && (
            <motion.div
              key="welcome"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="max-w-4xl mx-auto py-20 text-center"
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2 }}
                className="space-y-6"
              >
                <h1 className="text-5xl font-bold bg-gradient-to-r from-emerald-600 to-purple-600 bg-clip-text text-transparent">
                  Experience AI Optimization in Action
                </h1>
                <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                  See how Netra can reduce your AI costs by 40-60% while improving performance by 2-3x.
                  Start with your industry-specific workload profile.
                </p>
                
                <div className="flex items-center justify-center space-x-8 py-8">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-purple-600">$2.4M</div>
                    <div className="text-sm text-gray-500">Annual Savings</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-green-600">3.2x</div>
                    <div className="text-sm text-gray-500">Faster Response</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-blue-600">99.9%</div>
                    <div className="text-sm text-gray-500">Uptime SLA</div>
                  </div>
                </div>
                
                <Button
                  size="lg"
                  onClick={() => setDemoStep('workload')}
                  className="glass-button-primary hover:shadow-lg"
                >
                  <Rocket className="mr-2 h-5 w-5" />
                  Start Interactive Demo
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </motion.div>
            </motion.div>
          )}

          {/* Workload Selection */}
          {demoStep === 'workload' && (
            <motion.div
              key="workload"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <WorkloadSelector 
                onSelect={handleWorkloadSelect}
                showAdvancedOptions={true}
              />
            </motion.div>
          )}

          {/* Generating Data */}
          {demoStep === 'generating' && (
            <motion.div
              key="generating"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="max-w-4xl mx-auto py-20"
            >
              <Card className="border-2 border-purple-200">
                <CardContent className="p-12 text-center space-y-6">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    className="w-20 h-20 mx-auto"
                  >
                    <Sparkles className="w-20 h-20 text-purple-600" />
                  </motion.div>
                  
                  <h2 className="text-2xl font-bold text-gray-900">
                    Generating Synthetic Data
                  </h2>
                  <p className="text-gray-600 max-w-2xl mx-auto">
                    Creating realistic {selectedWorkload} workload patterns with temporal variations,
                    edge cases, and failure scenarios...
                  </p>
                  
                  <div className="space-y-2 max-w-md mx-auto">
                    <div className="flex justify-between text-sm">
                      <span>Data Generation</span>
                      <span className="font-mono">10,000 records</span>
                    </div>
                    <Progress value={75} className="h-2" />
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4 pt-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-600">10K</div>
                      <div className="text-xs text-gray-500">Records Generated</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">100%</div>
                      <div className="text-xs text-gray-500">GDPR Compliant</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">30</div>
                      <div className="text-xs text-gray-500">Days Simulated</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Analyzing */}
          {demoStep === 'analyzing' && (
            <motion.div
              key="analyzing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="max-w-4xl mx-auto py-20"
            >
              <Card className="border-2 border-blue-200">
                <CardContent className="p-12 text-center space-y-6">
                  <motion.div
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                    className="w-20 h-20 mx-auto"
                  >
                    <Brain className="w-20 h-20 text-blue-600" />
                  </motion.div>
                  
                  <h2 className="text-2xl font-bold text-gray-900">
                    Analyzing & Optimizing
                  </h2>
                  <p className="text-gray-600 max-w-2xl mx-auto">
                    Our AI agents are analyzing your workload patterns and identifying
                    optimization opportunities...
                  </p>
                  
                  <div className="grid grid-cols-4 gap-4 pt-4">
                    <div className="text-center">
                      <div className="text-lg font-bold text-purple-600">Triage</div>
                      <div className="text-xs text-gray-500">Complete</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-blue-600">Analysis</div>
                      <div className="text-xs text-gray-500">In Progress</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-gray-400">Optimize</div>
                      <div className="text-xs text-gray-400">Pending</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-gray-400">Report</div>
                      <div className="text-xs text-gray-400">Pending</div>
                    </div>
                  </div>
                  
                  <div className="bg-gray-50 rounded-lg p-4 font-mono text-xs text-left max-h-40 overflow-y-auto">
                    <div className="text-green-600">[TRIAGE] Request categorized: Cost Optimization</div>
                    <div className="text-blue-600">[DATA] Analyzing 10,000 workload events...</div>
                    <div className="text-purple-600">[PATTERN] Detected peak usage: 10AM-2PM, 7PM-9PM</div>
                    <div className="text-yellow-600">[INSIGHT] Opportunity: 42% cost reduction via model routing</div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Results */}
          {demoStep === 'results' && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-8"
            >
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-gray-900 mb-2">
                  Optimization Results
                </h2>
                <p className="text-gray-600">
                  Based on your {selectedWorkload} workload analysis
                </p>
              </div>

              {/* Key Metrics */}
              <div className="grid grid-cols-4 gap-6">
                <Card className="border-green-200 bg-green-50">
                  <CardContent className="p-6 text-center">
                    <div className="text-3xl font-bold text-green-600">42%</div>
                    <div className="text-sm text-gray-600 mt-1">Cost Reduction</div>
                    <div className="text-xs text-green-600 mt-2">$124K/month saved</div>
                  </CardContent>
                </Card>
                
                <Card className="glass-card border-emerald-200">
                  <CardContent className="p-6 text-center">
                    <div className="text-3xl font-bold text-blue-600">3.2x</div>
                    <div className="text-sm text-gray-600 mt-1">Faster Response</div>
                    <div className="text-xs text-blue-600 mt-2">62ms → 19ms p50</div>
                  </CardContent>
                </Card>
                
                <Card className="border-purple-200 bg-purple-50">
                  <CardContent className="p-6 text-center">
                    <div className="text-3xl font-bold text-purple-600">99.9%</div>
                    <div className="text-sm text-gray-600 mt-1">Reliability</div>
                    <div className="text-xs text-purple-600 mt-2">From 97.2%</div>
                  </CardContent>
                </Card>
                
                <Card className="border-yellow-200 bg-yellow-50">
                  <CardContent className="p-6 text-center">
                    <div className="text-3xl font-bold text-yellow-600">85%</div>
                    <div className="text-sm text-gray-600 mt-1">GPU Utilization</div>
                    <div className="text-xs text-yellow-600 mt-2">From 45%</div>
                  </CardContent>
                </Card>
              </div>

              {/* Recommendations */}
              <Card>
                <CardHeader>
                  <CardTitle>Optimization Recommendations</CardTitle>
                  <CardDescription>AI-powered insights based on your workload analysis</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-start space-x-3">
                    <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
                    <div>
                      <div className="font-semibold">Implement Intelligent Model Routing</div>
                      <div className="text-sm text-gray-600">
                        Route 65% of simple queries to GPT-3.5-Turbo, reducing costs by $89K/month
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-start space-x-3">
                    <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
                    <div>
                      <div className="font-semibold">Enable Request Batching</div>
                      <div className="text-sm text-gray-600">
                        Batch similar requests to improve throughput by 280% during peak hours
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-start space-x-3">
                    <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
                    <div>
                      <div className="font-semibold">Implement Semantic Caching</div>
                      <div className="text-sm text-gray-600">
                        Cache similar query results to reduce redundant API calls by 35%
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Call to Action */}
              <div className="text-center space-y-4 py-8">
                <h3 className="text-2xl font-bold">Ready to Deploy These Optimizations?</h3>
                <p className="text-gray-600 max-w-2xl mx-auto">
                  Start your pilot program today and see these results in your production environment
                </p>
                <div className="flex gap-4 justify-center">
                  <Button 
                    size="lg"
                    onClick={() => router.push('/chat')}
                    className="glass-button-primary"
                  >
                    <Shield className="mr-2 h-5 w-5" />
                    Access Admin Features
                  </Button>
                  <Button 
                    size="lg" 
                    variant="outline"
                    onClick={() => window.location.reload()}
                  >
                    Run Another Demo
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default EnhancedEnterpriseDemoPage;