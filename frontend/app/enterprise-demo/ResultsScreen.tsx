'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Shield, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { getResultsData } from './demoConfig';

interface ResultsScreenProps {
  selectedWorkload: string | null;
}

const ResultsScreen = ({ selectedWorkload }: ResultsScreenProps) => {
  const router = useRouter();
  const resultsData = getResultsData();

  const renderMetricsGrid = () => (
    <div className="grid grid-cols-4 gap-6">
      <Card className="border-green-200 bg-green-50">
        <CardContent className="p-6 text-center">
          <div className="text-3xl font-bold text-green-600">{resultsData.costReduction}%</div>
          <div className="text-sm text-gray-600 mt-1">Cost Reduction</div>
          <div className="text-xs text-green-600 mt-2">{resultsData.monthlySavings}/month saved</div>
        </CardContent>
      </Card>
      
      <Card className="glass-card border-emerald-200">
        <CardContent className="p-6 text-center">
          <div className="text-3xl font-bold text-blue-600">{resultsData.responseTime}</div>
          <div className="text-sm text-gray-600 mt-1">Faster Response</div>
          <div className="text-xs text-blue-600 mt-2">{resultsData.latencyImprovement}</div>
        </CardContent>
      </Card>
      
      <Card className="border-purple-200 bg-purple-50">
        <CardContent className="p-6 text-center">
          <div className="text-3xl font-bold text-purple-600">{resultsData.reliability}</div>
          <div className="text-sm text-gray-600 mt-1">Reliability</div>
          <div className="text-xs text-purple-600 mt-2">{resultsData.reliabilityFrom}</div>
        </CardContent>
      </Card>
      
      <Card className="border-yellow-200 bg-yellow-50">
        <CardContent className="p-6 text-center">
          <div className="text-3xl font-bold text-yellow-600">{resultsData.gpuUtilization}</div>
          <div className="text-sm text-gray-600 mt-1">GPU Utilization</div>
          <div className="text-xs text-yellow-600 mt-2">{resultsData.gpuFrom}</div>
        </CardContent>
      </Card>
    </div>
  );

  const renderRecommendations = () => (
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
  );

  const renderCallToAction = () => (
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
  );

  return (
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

      {renderMetricsGrid()}
      {renderRecommendations()}
      {renderCallToAction()}
    </motion.div>
  );
};

export default ResultsScreen;