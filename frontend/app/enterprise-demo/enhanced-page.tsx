'use client';

import { NextPage } from 'next';
import { authService } from '@/auth';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { useChatStore } from '@/store/chat';
import { useAgent } from '@/hooks/useAgent';
import AgentStatusPanel from '@/components/chat/AgentStatusPanel';
import DemoHeader from './DemoHeader';
import WelcomeScreen from './WelcomeScreen';
import WorkloadScreen from './WorkloadScreen';
import GeneratingScreen from './GeneratingScreen';
import AnalyzingScreen from './AnalyzingScreen';
import ResultsScreen from './ResultsScreen';
import { type DemoStep } from './demoConfig';

const EnhancedEnterpriseDemoPage: NextPage = () => {
  const { user, loading } = authService.useAuth();
  const router = useRouter();
  const [demoStep, setDemoStep] = useState<DemoStep>('welcome');
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
    triggerDataGeneration(workloadId);
  };

  const triggerDataGeneration = (workloadId: string) => {
    const message = `Generate synthetic ${workloadId} workload data for enterprise demo`;
    sendUserMessage(message);
    scheduleStepTransitions();
  };

  const scheduleStepTransitions = () => {
    setTimeout(() => {
      setSyntheticDataGenerated(true);
      setDemoStep('analyzing');
    }, 5000);
    
    setTimeout(() => {
      setDemoStep('results');
    }, 10000);
  };

  const handleStartDemo = () => {
    setDemoStep('workload');
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

      <DemoHeader demoStep={demoStep} />

      {/* Main Content */}
      <div className="container mx-auto p-6">
        <AnimatePresence mode="wait">
          {demoStep === 'welcome' && (
            <WelcomeScreen onStartDemo={handleStartDemo} />
          )}
          {demoStep === 'workload' && (
            <WorkloadScreen onWorkloadSelect={handleWorkloadSelect} />
          )}
          {demoStep === 'generating' && (
            <GeneratingScreen selectedWorkload={selectedWorkload} />
          )}
          {demoStep === 'analyzing' && (
            <AnalyzingScreen />
          )}
          {demoStep === 'results' && (
            <ResultsScreen selectedWorkload={selectedWorkload} />
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default EnhancedEnterpriseDemoPage;