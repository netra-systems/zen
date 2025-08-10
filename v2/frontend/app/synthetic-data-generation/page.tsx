'use client';

import { SyntheticDataGenerator } from '@/components/synthetic-data-generator';

export default function SyntheticDataGeneratorPage() {
  const handleGenerationComplete = () => {
    // Handle completion - could navigate, show a toast, etc.
    console.log('Synthetic data generation completed');
  };

  return <SyntheticDataGenerator onGenerationComplete={handleGenerationComplete} />;
}
