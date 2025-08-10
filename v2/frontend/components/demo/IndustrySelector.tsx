'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Building2, 
  Heart, 
  ShoppingCart, 
  Factory, 
  Cpu,
  TrendingUp,
  Shield,
  Users
} from 'lucide-react'

interface IndustrySelectorProps {
  onSelect: (industry: string) => void
}

interface Industry {
  id: string
  name: string
  icon: React.ReactNode
  description: string
  useCases: string[]
  avgSavings: string
  color: string
}

export default function IndustrySelector({ onSelect }: IndustrySelectorProps) {
  const industries: Industry[] = [
    {
      id: 'financial',
      name: 'Financial Services',
      icon: <TrendingUp className="w-8 h-8" />,
      description: 'Banks, insurance, fintech, and investment firms',
      useCases: ['Fraud Detection', 'Risk Analysis', 'Trading Algorithms', 'Customer Service'],
      avgSavings: '45-65%',
      color: 'from-green-500 to-emerald-600'
    },
    {
      id: 'healthcare',
      name: 'Healthcare',
      icon: <Heart className="w-8 h-8" />,
      description: 'Hospitals, biotech, pharmaceuticals, and medical devices',
      useCases: ['Diagnostic AI', 'Drug Discovery', 'Patient Care', 'Medical Imaging'],
      avgSavings: '40-55%',
      color: 'from-red-500 to-pink-600'
    },
    {
      id: 'ecommerce',
      name: 'E-commerce',
      icon: <ShoppingCart className="w-8 h-8" />,
      description: 'Online retail, marketplaces, and direct-to-consumer',
      useCases: ['Recommendations', 'Search', 'Inventory', 'Customer Support'],
      avgSavings: '35-50%',
      color: 'from-orange-500 to-amber-600'
    },
    {
      id: 'manufacturing',
      name: 'Manufacturing',
      icon: <Factory className="w-8 h-8" />,
      description: 'Industrial, automotive, aerospace, and electronics',
      useCases: ['Predictive Maintenance', 'Quality Control', 'Supply Chain', 'Automation'],
      avgSavings: '30-45%',
      color: 'from-gray-600 to-slate-700'
    },
    {
      id: 'technology',
      name: 'Technology',
      icon: <Cpu className="w-8 h-8" />,
      description: 'Software, SaaS, platforms, and tech services',
      useCases: ['Code Generation', 'DevOps AI', 'Product Analytics', 'Content Creation'],
      avgSavings: '50-70%',
      color: 'from-blue-500 to-purple-600'
    },
    {
      id: 'government',
      name: 'Government & Defense',
      icon: <Shield className="w-8 h-8" />,
      description: 'Federal, state, local agencies and defense contractors',
      useCases: ['Intelligence Analysis', 'Citizen Services', 'Security', 'Operations'],
      avgSavings: '35-50%',
      color: 'from-indigo-600 to-blue-700'
    }
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {industries.map((industry) => (
        <Card 
          key={industry.id}
          className="relative overflow-hidden hover:shadow-xl transition-all duration-300 cursor-pointer group"
          onClick={() => onSelect(industry.name)}
        >
          <div className={`absolute inset-0 bg-gradient-to-br ${industry.color} opacity-5 group-hover:opacity-10 transition-opacity`} />
          
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className={`p-3 rounded-lg bg-gradient-to-br ${industry.color} text-white`}>
                {industry.icon}
              </div>
              <Badge variant="secondary" className="text-xs">
                {industry.avgSavings} savings
              </Badge>
            </div>

            <h3 className="text-lg font-semibold mb-2">{industry.name}</h3>
            <p className="text-sm text-muted-foreground mb-4">
              {industry.description}
            </p>

            <div className="space-y-2 mb-4">
              <p className="text-xs font-medium text-muted-foreground">Common Use Cases:</p>
              <div className="flex flex-wrap gap-1">
                {industry.useCases.map((useCase, idx) => (
                  <Badge key={idx} variant="outline" className="text-xs">
                    {useCase}
                  </Badge>
                ))}
              </div>
            </div>

            <Button 
              className={`w-full bg-gradient-to-r ${industry.color} hover:opacity-90 text-white`}
              onClick={(e) => {
                e.stopPropagation()
                onSelect(industry.name)
              }}
            >
              Select {industry.name}
            </Button>
          </CardContent>
        </Card>
      ))}

      {/* Custom Industry Option */}
      <Card 
        className="relative overflow-hidden hover:shadow-xl transition-all duration-300 cursor-pointer group border-2 border-dashed"
        onClick={() => onSelect('Custom')}
      >
        <CardContent className="p-6 flex flex-col justify-center items-center h-full min-h-[280px]">
          <div className="p-3 rounded-lg bg-gray-100 dark:bg-gray-800 mb-4">
            <Users className="w-8 h-8 text-gray-600 dark:text-gray-400" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Other Industry</h3>
          <p className="text-sm text-muted-foreground text-center mb-4">
            Don&apos;t see your industry? We support all sectors
          </p>
          <Button variant="outline" className="w-full">
            Continue with Custom
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}