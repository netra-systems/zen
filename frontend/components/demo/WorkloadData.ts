import React from 'react';
import { 
  ShoppingCart, TrendingUp, Heart, Gamepad, Microscope
} from 'lucide-react';
import { WorkloadProfile } from './WorkloadTypes';

export const workloadProfiles: WorkloadProfile[] = [
  {
    id: 'ecommerce',
    name: 'E-Commerce Platform',
    industry: 'Retail',
    icon: React.createElement(ShoppingCart, { className: "w-6 h-6" }),
    description: 'Product recommendations, search, and customer support',
    metrics: {
      volume: '10K requests/day',
      models: ['GPT-4', 'Claude-2', 'Ada'],
      avgLatency: '200ms',
      costPerInference: '$0.002'
    },
    color: 'text-purple-600',
    gradient: 'from-purple-500 to-pink-500'
  },
  {
    id: 'financial',
    name: 'Financial Services',
    industry: 'Finance',
    icon: React.createElement(TrendingUp, { className: "w-6 h-6" }),
    description: 'Risk analysis, fraud detection, and compliance',
    metrics: {
      volume: '50K requests/day',
      models: ['GPT-4-Turbo', 'Claude-3-Opus'],
      avgLatency: '500ms',
      costPerInference: '$0.005'
    },
    color: 'text-emerald-600',
    gradient: 'from-emerald-500 to-cyan-500'
  },
  {
    id: 'healthcare',
    name: 'Healthcare AI',
    industry: 'Healthcare',
    icon: React.createElement(Heart, { className: "w-6 h-6" }),
    description: 'Diagnosis assistance, medical Q&A, report generation',
    metrics: {
      volume: '25K requests/day',
      models: ['Med-PaLM-2', 'GPT-4', 'Bio-GPT'],
      avgLatency: '800ms',
      costPerInference: '$0.008'
    },
    color: 'text-red-600',
    gradient: 'from-red-500 to-orange-500'
  },
  {
    id: 'gaming',
    name: 'Gaming Platform',
    industry: 'Entertainment',
    icon: React.createElement(Gamepad, { className: "w-6 h-6" }),
    description: 'NPC dialogue, story generation, player assistance',
    metrics: {
      volume: '100K requests/day',
      models: ['GPT-3.5-Turbo', 'Llama-2-7B'],
      avgLatency: '100ms',
      costPerInference: '$0.001'
    },
    color: 'text-green-600',
    gradient: 'from-green-500 to-emerald-500'
  },
  {
    id: 'research',
    name: 'Research Lab',
    industry: 'Science',
    icon: React.createElement(Microscope, { className: "w-6 h-6" }),
    description: 'Paper analysis, hypothesis generation, data synthesis',
    metrics: {
      volume: '5K requests/day',
      models: ['GPT-4', 'Claude-3-Opus', 'PaLM-2'],
      avgLatency: '2000ms',
      costPerInference: '$0.015'
    },
    color: 'text-indigo-600',
    gradient: 'from-indigo-500 to-purple-500'
  }
];

export const getWorkloadById = (id: string): WorkloadProfile | undefined => {
  return workloadProfiles.find(profile => profile.id === id);
};

export const getWorkloadsByIndustry = (industry: string): WorkloadProfile[] => {
  return workloadProfiles.filter(profile => profile.industry === industry);
};