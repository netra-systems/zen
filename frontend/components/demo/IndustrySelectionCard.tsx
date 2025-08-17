'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import IndustrySelector from '@/components/demo/IndustrySelector'

interface IndustrySelectionCardProps {
  onIndustrySelect: (industry: string) => void
}

export default function IndustrySelectionCard({ onIndustrySelect }: IndustrySelectionCardProps) {
  
  const handleSelect = (industry: string) => {
    onIndustrySelect(industry)
  }

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>Select Your Industry</CardTitle>
        <CardDescription>
          Customize the demo experience for your specific sector
        </CardDescription>
      </CardHeader>
      <CardContent>
        <IndustrySelector onSelect={handleSelect} />
      </CardContent>
    </Card>
  )
}