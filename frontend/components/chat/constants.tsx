import { Database, Sparkles, Users, Settings, FileText } from 'lucide-react';
import { AdminCommand, AdminTemplate } from './types';

export const ADMIN_COMMANDS: AdminCommand[] = [
  {
    command: '/corpus',
    description: 'Corpus management commands',
    icon: <Database className="w-4 h-4" />,
    category: 'corpus',
    template: 'Create a corpus for '
  },
  {
    command: '/synthetic',
    description: 'Synthetic data generation',
    icon: <Sparkles className="w-4 h-4" />,
    category: 'synthetic',
    template: 'Generate synthetic data with '
  },
  {
    command: '/users',
    description: 'User management commands',
    icon: <Users className="w-4 h-4" />,
    category: 'users',
    template: 'List all users with role '
  },
  {
    command: '/config',
    description: 'System configuration',
    icon: <Settings className="w-4 h-4" />,
    category: 'config',
    template: 'Update system setting '
  },
  {
    command: '/logs',
    description: 'Log analysis commands',
    icon: <FileText className="w-4 h-4" />,
    category: 'logs',
    template: 'Show logs from the last '
  }
];

export const ADMIN_TEMPLATES: AdminTemplate[] = [
  {
    name: 'Create Financial Corpus',
    category: 'corpus',
    icon: <Database className="w-3 h-3" />,
    template: `Create a corpus for financial services with examples for:
- Market data analysis
- Risk assessment
- Portfolio optimization
- Compliance checking`
  },
  {
    name: 'Generate Test Data',
    category: 'synthetic',
    icon: <Sparkles className="w-3 h-3" />,
    template: `Generate 10,000 synthetic optimization requests with:
- 70% successful optimizations
- 20% partial optimizations
- 10% failed requests
- Realistic latency distribution`
  },
  {
    name: 'User Access Audit',
    category: 'users',
    icon: <Users className="w-3 h-3" />,
    template: `Show me all admin actions performed in the last 7 days, 
grouped by user and sorted by frequency`
  },
  {
    name: 'E-Commerce Load Test',
    category: 'synthetic',
    icon: <Sparkles className="w-3 h-3" />,
    template: `Generate Black Friday e-commerce workload pattern:
- 500,000 requests over 24 hours
- Peak traffic between 6 AM and 2 PM
- 30% cart abandonment rate
- Realistic geographic distribution`
  }
];

export const MESSAGE_INPUT_CONSTANTS = {
  MAX_ROWS: 5,
  CHAR_LIMIT: 10000,
  LINE_HEIGHT: 24
} as const;