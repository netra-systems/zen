'use client'

import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CheckCircle } from 'lucide-react'

interface DemoCompletionProps {
  demoProgress: number
}

export default function DemoCompletion({ demoProgress }: DemoCompletionProps) {
  const router = useRouter()

  const handleTryLiveSystem = () => {
    router.push('/chat')
  }

  const handleScheduleDeepDive = () => {
    // Implementation for scheduling deep dive
    // Could integrate with calendly or similar
  }

  if (demoProgress !== 100) return null

  return (
    <Card className="mt-6 border-green-500 bg-green-50 dark:bg-green-950">
      <CardHeader>
        <CardTitle className="text-green-700 dark:text-green-300">
          <CheckCircle className="w-5 h-5 inline mr-2" />
          Demo Complete!
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-4">
          Congratulations! You&apos;ve experienced the full power of our AI Optimization Platform.
        </p>
        <div className="flex space-x-4">
          <Button onClick={handleTryLiveSystem}>
            Try Live System
          </Button>
          <Button variant="outline" onClick={handleScheduleDeepDive}>
            Schedule Deep Dive
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}