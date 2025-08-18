'use client';

import { SyntheticDataGenerator } from '@/components/synthetic-data-generator';
import { logger } from '@/utils/debug-logger';

export default function SyntheticDataGeneratorPage() {
  const handleGenerationComplete = () => {
    // Handle completion - could navigate, show a toast, etc.
    logger.info('Synthetic data generation completed');
  };

  return <SyntheticDataGenerator onGenerationComplete={handleGenerationComplete} />;
}
