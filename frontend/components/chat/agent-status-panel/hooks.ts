import { useState, useEffect, useMemo } from 'react';
import { Metrics, DataPreviewItem } from './types';

const PROCESSING_QUIPS = [
  "Optimizing the optimizers...",
  "Teaching AI to be more intelligent...",
  "Convincing the models to cooperate...",
  "Negotiating with the neural networks...",
  "Calibrating the crystal ball...",
  "Asking the magic 8-ball for advice...",
  "Consulting the optimization oracle...",
  "Bribing the algorithms with more compute..."
];

export const useHumorQuips = (isProcessing: boolean): string => {
  const processingQuips = useMemo(() => PROCESSING_QUIPS, []);
  const [currentQuip, setCurrentQuip] = useState(processingQuips[0]);

  const updateQuip = (): void => {
    const randomIndex = Math.floor(Math.random() * processingQuips.length);
    setCurrentQuip(processingQuips[randomIndex]);
  };

  useEffect(() => {
    if (!isProcessing) return;
    const interval = setInterval(updateQuip, 5000);
    return () => clearInterval(interval);
  }, [isProcessing, processingQuips]);

  return currentQuip;
};

const createInitialMetrics = (): Metrics => ({
  recordsProcessed: 0,
  processingRate: 0,
  estimatedTimeRemaining: 0,
  confidenceScore: 0
});

const updateMetricsStep = (prev: Metrics): Metrics => ({
  recordsProcessed: prev.recordsProcessed + Math.floor(Math.random() * 100),
  processingRate: 50 + Math.random() * 150,
  estimatedTimeRemaining: Math.max(0, prev.estimatedTimeRemaining - 1),
  confidenceScore: 0.7 + Math.random() * 0.3
});

export const useMetricsSimulation = (isProcessing: boolean): Metrics => {
  const [metrics, setMetrics] = useState<Metrics>(createInitialMetrics);

  const resetMetrics = (): void => setMetrics(createInitialMetrics());
  const updateMetrics = (): void => setMetrics(updateMetricsStep);

  useEffect(() => {
    if (isProcessing) {
      const interval = setInterval(updateMetrics, 1000);
      return () => clearInterval(interval);
    } else {
      resetMetrics();
    }
  }, [isProcessing]);

  return metrics;
};

const generateSampleDataItem = (index: number): DataPreviewItem => ({
  id: `record-${Date.now()}-${index}`,
  model: ['gpt-4', 'claude-2', 'llama-2'][Math.floor(Math.random() * 3)],
  latency: Math.floor(50 + Math.random() * 200),
  tokens: Math.floor(100 + Math.random() * 2000),
  cost: (Math.random() * 0.5).toFixed(4)
});

const generateSampleData = (): DataPreviewItem[] => (
  Array.from({ length: 5 }, (_, i) => generateSampleDataItem(i))
);

export const useDataPreview = (isProcessing: boolean, workflowStep: number): DataPreviewItem[] => {
  const [dataPreview, setDataPreview] = useState<DataPreviewItem[]>([]);

  const shouldUpdatePreview = (): boolean => isProcessing && Math.random() > 0.7;

  useEffect(() => {
    if (shouldUpdatePreview()) {
      setDataPreview(generateSampleData());
    }
  }, [isProcessing, workflowStep]);

  return dataPreview;
};