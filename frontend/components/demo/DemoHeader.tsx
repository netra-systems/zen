'use client'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Sparkles, TrendingUp, Zap, Shield } from 'lucide-react'

interface ValueProp {
  icon: React.ReactNode
  title: string
  description: string
}

interface DemoHeaderProps {
  selectedIndustry?: string
}

export default function DemoHeader({ selectedIndustry }: DemoHeaderProps) {
  const valueProps: ValueProp[] = [
    {
      icon: <TrendingUp className="w-5 h-5 text-green-500" />,
      title: '40-60% Cost Reduction',
      description: 'Optimize AI infrastructure spending'
    },
    {
      icon: <Zap className="w-5 h-5 text-yellow-500" />,
      title: '2-3x Performance Gain',
      description: 'Accelerate model inference and training'
    },
    {
      icon: <Shield className="w-5 h-5 text-blue-500" />,
      title: 'Enterprise Security',
      description: 'SOC2, HIPAA, GDPR compliant'
    }
  ]

  const renderTitle = () => (
    <h1 className="text-4xl font-bold bg-gradient-to-r from-emerald-600 to-purple-600 bg-clip-text text-transparent">
      Enterprise AI Optimization Platform
    </h1>
  )

  const renderSubtitle = () => (
    <p className="text-lg text-muted-foreground mt-2">
      Reduce costs by 40-60% while improving performance by 2-3x
    </p>
  )

  const renderLiveBadge = () => (
    <Badge variant="outline" className="px-4 py-2">
      <Sparkles className="w-4 h-4 mr-2" />
      Live Demo
    </Badge>
  )

  const renderValueProp = (prop: ValueProp, idx: number) => (
    <Card key={idx} className="border-2 hover:border-primary transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-center space-x-3">
          {prop.icon}
          <CardTitle className="text-lg">{prop.title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{prop.description}</p>
      </CardContent>
    </Card>
  )

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          {renderTitle()}
          {renderSubtitle()}
        </div>
        {renderLiveBadge()}
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {valueProps.map((prop, idx) => renderValueProp(prop, idx))}
      </div>
    </div>
  )
}