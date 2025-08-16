"use client";

// Integration test component for the modular three-layer response card system
// This tests the progressive disclosure: Fast (0-100ms) → Medium (100ms-1s) → Slow (1s+)

import React, { useState, useEffect } from 'react';
import { PersistentResponseCard } from './PersistentResponseCard';
import type { 
  FastLayerData, 
  MediumLayerData, 
  SlowLayerData 
} from '@/types/layer-types';

export const TestResponseCard: React.FC = () => {
  const [fastLayerData, setFastLayerData] = useState<FastLayerData | null>(null);
  const [mediumLayerData, setMediumLayerData] = useState<MediumLayerData | null>(null);
  const [slowLayerData, setSlowLayerData] = useState<SlowLayerData | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Simulate progressive layer updates with proper timing
  useEffect(() => {
    simulateThreeLayerProgression();
  }, []);

  const simulateThreeLayerProgression = (): void => {
    setIsProcessing(true);
    
    // Fast Layer (0-100ms): Immediate agent name and presence
    setTimeout(() => {
      setFastLayerData(createMockFastLayer());
    }, 50);
    
    // Medium Layer (100ms-1s): Thinking and partial content
    setTimeout(() => {
      setMediumLayerData(createMockMediumLayer());
    }, 300);
    
    // Simulate streaming content updates
    setTimeout(() => {
      simulateStreamingContent();
    }, 500);
    
    // Slow Layer (1s+): Final results and completion
    setTimeout(() => {
      setSlowLayerData(createMockSlowLayer());
      setIsProcessing(false);
    }, 1500);
  };

  const simulateStreamingContent = (): void => {
    const content = "Analyzing system performance... Found optimization opportunities...";
    let currentContent = "";
    
    const streamChars = (index: number): void => {
      if (index < content.length) {
        currentContent += content[index];
        setMediumLayerData(prev => prev ? {
          ...prev,
          partialContent: currentContent
        } : null);
        
        // 30 chars/sec streaming rate
        setTimeout(() => streamChars(index + 1), 1000 / 30);
      }
    };
    
    streamChars(0);
  };

  const createMockFastLayer = (): FastLayerData => ({
    agentName: "Performance Analyzer",
    activeTools: ["system_scanner", "metrics_collector"],
    timestamp: Date.now(),
    runId: "test-run-123"
  });

  const createMockMediumLayer = (): MediumLayerData => ({
    thought: "Scanning system components for performance bottlenecks...",
    partialContent: "",
    stepNumber: 2,
    totalSteps: 5,
    agentName: "Performance Analyzer"
  });

  const createMockSlowLayer = (): SlowLayerData => ({
    completedAgents: [{
      agentName: "Performance Analyzer",
      duration: 2500,
      result: {
        output: "Analysis complete",
        status: "success" as const,
        data: { optimizations: 3 }
      },
      metrics: {
        executionTime: 2500,
        memoryUsage: 128,
        apiCalls: 5
      }
    }],
    finalReport: {
      report: {
        summary: "Performance analysis completed successfully",
        findings: { bottlenecks: ["database_queries", "image_processing"] },
        data: { score: 85 },
        metadata: { generatedAt: new Date().toISOString(), version: "1.0" }
      },
      recommendations: [{
        id: "rec-1",
        title: "Optimize Database Queries",
        description: "Add indexes to frequently queried columns",
        impact: "high" as const,
        effort: "medium" as const,
        category: "database",
        metrics: { potential_savings: 500, latency_reduction: 200 }
      }],
      actionPlan: [{
        id: "step-1",
        step_number: 1,
        description: "Add database indexes",
        command: "CREATE INDEX idx_user_id ON users(id);",
        expected_outcome: "50% query performance improvement"
      }],
      agentMetrics: [{
        agent_id: "perf-analyzer",
        duration_ms: 2500,
        tokens_used: 150
      }]
    },
    totalDuration: 2500,
    metrics: {
      total_duration_ms: 2500,
      total_tokens: 150,
      total_cost: 0.05
    }
  });

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Three-Layer Response Card Test
          </h1>
          <p className="text-gray-600">
            Testing progressive disclosure: Fast (0-100ms) → Medium (100ms-1s) → Slow (1s+)
          </p>
        </div>
        
        <div className="space-y-4">
          <button
            onClick={simulateThreeLayerProgression}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            disabled={isProcessing}
          >
            {isProcessing ? 'Processing...' : 'Simulate Three-Layer Response'}
          </button>
          
          <div className="bg-white p-4 rounded-lg border">
            <h3 className="font-semibold mb-2">Layer Data Status:</h3>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className={`p-2 rounded ${fastLayerData ? 'bg-green-100' : 'bg-gray-100'}`}>
                Fast Layer: {fastLayerData ? '✓ Active' : '⏳ Waiting'}
              </div>
              <div className={`p-2 rounded ${mediumLayerData ? 'bg-blue-100' : 'bg-gray-100'}`}>
                Medium Layer: {mediumLayerData ? '✓ Active' : '⏳ Waiting'}
              </div>
              <div className={`p-2 rounded ${slowLayerData ? 'bg-purple-100' : 'bg-gray-100'}`}>
                Slow Layer: {slowLayerData ? '✓ Active' : '⏳ Waiting'}
              </div>
            </div>
          </div>
        </div>
        
        <PersistentResponseCard
          fastLayerData={fastLayerData}
          mediumLayerData={mediumLayerData}
          slowLayerData={slowLayerData}
          isProcessing={isProcessing}
          isCollapsed={isCollapsed}
          onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
        />
      </div>
    </div>
  );
};
