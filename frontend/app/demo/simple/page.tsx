'use client'

import { useState, useEffect } from 'react'
import DemoChat from '@/components/demo/DemoChat'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Sparkles, Zap, TrendingUp, DollarSign } from 'lucide-react'

export default function SimpleDemoPage() {
  const [selectedIndustry, setSelectedIndustry] = useState<string>('general')

  const industries = [
    { id: 'healthcare', name: 'Healthcare', icon: '🏥' },
    { id: 'finance', name: 'Finance', icon: '💰' },
    { id: 'retail', name: 'Retail', icon: '🛍️' },
    { id: 'general', name: 'General', icon: '🚀' }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                <Sparkles className="w-8 h-8 text-blue-600" />
                Netra AI Demo
              </h1>
              <p className="text-gray-600 mt-1">Experience AI cost optimization in real-time</p>
            </div>
            <Badge className="bg-green-100 text-green-800 border-green-200 px-3 py-1">
              No Login Required
            </Badge>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column - Info */}
          <div className="lg:col-span-1 space-y-4">
            {/* Industry Selection */}
            <Card className="bg-white border-gray-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-gray-900">Select Industry</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2">
                  {industries.map((industry) => (
                    <button
                      key={industry.id}
                      onClick={() => setSelectedIndustry(industry.id)}
                      className={`p-3 rounded-lg border-2 transition-all ${
                        selectedIndustry === industry.id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300 bg-white'
                      }`}
                    >
                      <div className="text-2xl mb-1">{industry.icon}</div>
                      <div className="text-sm font-medium text-gray-900">{industry.name}</div>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Value Props */}
            <Card className="bg-white border-gray-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-gray-900">What Netra Does</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <DollarSign className="w-5 h-5 text-green-600 mt-0.5" />
                    <div>
                      <div className="font-medium text-gray-900">35% Cost Reduction</div>
                      <div className="text-sm text-gray-600">Optimize AI infrastructure spending</div>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <Zap className="w-5 h-5 text-blue-600 mt-0.5" />
                    <div>
                      <div className="font-medium text-gray-900">2.3x Faster</div>
                      <div className="text-sm text-gray-600">Accelerate AI response times</div>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <TrendingUp className="w-5 h-5 text-purple-600 mt-0.5" />
                    <div>
                      <div className="font-medium text-gray-900">80% Utilization</div>
                      <div className="text-sm text-gray-600">Maximize resource efficiency</div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick Tips */}
            <Card className="bg-blue-50 border-blue-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-gray-900">Try These Messages</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="p-2 bg-white rounded-lg text-gray-700">
                    "How can I reduce my OpenAI costs?"
                  </div>
                  <div className="p-2 bg-white rounded-lg text-gray-700">
                    "We spend $50K/month on AI"
                  </div>
                  <div className="p-2 bg-white rounded-lg text-gray-700">
                    "Show me optimization strategies"
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Chat */}
          <div className="lg:col-span-2">
            <Card className="bg-white border-gray-200 h-[600px] flex flex-col">
              <CardHeader className="border-b bg-gray-50">
                <CardTitle className="text-xl text-gray-900">Chat with Netra AI</CardTitle>
                <CardDescription>
                  Ask questions about AI optimization and see our agents in action
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-1 p-0">
                <DemoChat 
                  industry={selectedIndustry} 
                  onInteraction={() => {}}
                  useWebSocket={true}
                />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}