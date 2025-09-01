/**
 * Category handlers for Corpus Discovery Panel
 * All functions ≤8 lines, focused on category management logic
 */

import { generateUniqueId } from '../../../lib/utils';
import { DiscoveryCategory, ConfigOption, DiscoveryResponse } from './types';

export const createWorkloadCategory = (response: DiscoveryResponse): DiscoveryCategory => {
  const items = response.items || [];
  return {
    name: 'Workload Types',
    description: 'Choose the type of workload for your corpus',
    options: items.map(createWorkloadOption)
  };
};

const createWorkloadOption = (item: { name: string; id: string; description: string; recommended?: boolean }): ConfigOption => ({
  id: generateUniqueId('workload'),
  label: item.name,
  value: item.id,
  description: item.description,
  recommended: item.recommended
});

export const createDomainCategory = (): DiscoveryCategory => {
  const domains = ['ecommerce', 'fintech', 'healthcare', 'saas', 'iot'];
  return {
    name: 'Domain',
    description: 'Select your business domain',
    options: domains.map(createDomainOption)
  };
};

const createDomainOption = (domain: string): ConfigOption => ({
  id: generateUniqueId('domain'),
  label: domain.charAt(0).toUpperCase() + domain.slice(1),
  value: domain,
  description: `Optimized for ${domain} use cases`
});

export const createParameterCategory = (): DiscoveryCategory => ({
  name: 'Generation Parameters',
  description: 'Configure generation settings',
  options: [
    createPerformanceOption(),
    createQualityOption(),
    createBalancedOption()
  ]
});

const createPerformanceOption = (): ConfigOption => ({
  id: generateUniqueId('param'),
  label: 'Performance Optimized',
  value: 'performance',
  description: 'Fast generation with high throughput'
});

const createQualityOption = (): ConfigOption => ({
  id: generateUniqueId('param'),
  label: 'Quality Focused',
  value: 'quality',
  description: 'High accuracy and data integrity'
});

const createBalancedOption = (): ConfigOption => ({
  id: generateUniqueId('param'),
  label: 'Balanced',
  value: 'balanced',
  description: 'Balance between speed and quality',
  recommended: true
});

export const processDiscoveryResponse = (response: DiscoveryResponse): DiscoveryCategory[] => {
  return [
    createWorkloadCategory(response),
    createDomainCategory(),
    createParameterCategory()
  ];
};

export const extractSuggestions = (response: DiscoveryResponse): string[] => {
  return response.suggestions || [];
};