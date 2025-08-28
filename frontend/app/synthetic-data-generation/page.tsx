'use client';

import { SyntheticDataGenerator } from '@/components/synthetic-data-generator';
import { AuthGuard } from '@/components/AuthGuard';
import { logger } from '@/utils/debug-logger';

export default function SyntheticDataGeneratorPage() {
  const handleGenerationComplete = () => {
    // Handle completion - could navigate, show a toast, etc.
    logger.info('Synthetic data generation completed');
  };

  return (
    <AuthGuard>
      <SyntheticDataGenerator onGenerationComplete={handleGenerationComplete} />
    </AuthGuard>
  );
}
