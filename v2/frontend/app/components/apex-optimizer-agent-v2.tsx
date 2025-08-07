'use client';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useState } from 'react';
import { MessageFactory } from '../services/agent/MessageFactory';
import { useAgentContext } from '../providers/AgentProvider';
import { MessageOrchestrator } from './chat/MessageOrchestrator';

const examplePrompts = [
  'Analyze the latency of the `get_user_data` tool and suggest optimizations.',
    'Find the most expensive tool in my project and explain why it is so costly.',
  'Simulate the cost impact of a 50% increase in traffic to the `process_payment` tool.',
  'Generate a report on the quality of the `generate_report` tool.',
];

function truncatePrompt(prompt: string, words: number) {
  return prompt.split(' ').slice(0, words).join(' ') + '...';
}

function ApexOptimizerAgentV2() {