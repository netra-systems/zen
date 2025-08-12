'use client';

import { NextPage } from 'next';
import { authService } from '@/auth';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ArrowRight, Brain, Code2, Database, Layers, LineChart, Rocket, Shield, Sparkles, Zap } from 'lucide-react';

const EnterpriseDemoPage: NextPage = () => {
  const { user, loading } = authService.useAuth();
  const router = useRouter();
  const [activeDemo, setActiveDemo] = useState('optimization');
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [loading, user, router]);

  useEffect(() => {
    const timer = setTimeout(() => setProgress(85), 500);
    return () => clearTimeout(timer);
  }, []);

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Loading...</p>
      </div>
    );
  }

  const demos = [
    {
      id: 'optimization',
      title: 'AI Workload Optimization',
      description: 'Real-time optimization of AI models and agents',
      metrics: [
        { label: 'Cost Reduction', value: '62%', trend: 'up' },
        { label: 'Performance Gain', value: '3.4x', trend: 'up' },
        { label: 'Latency Reduction', value: '78ms', trend: 'down' },
      ],
    },
    {
      id: 'multiagent',
      title: 'Multi-Agent Orchestration',
      description: 'Intelligent routing and coordination of agent workflows',
      metrics: [
        { label: 'Agent Efficiency', value: '94%', trend: 'up' },
        { label: 'Task Completion', value: '99.7%', trend: 'up' },
        { label: 'Error Rate', value: '0.02%', trend: 'down' },
      ],
    },
    {
      id: 'analytics',
      title: 'Advanced Analytics',
      description: 'Deep insights into AI system performance',
      metrics: [
        { label: 'Data Points/sec', value: '1.2M', trend: 'up' },
        { label: 'Anomaly Detection', value: '99.9%', trend: 'up' },
        { label: 'Response Time', value: '12ms', trend: 'down' },
      ],
    },
  ];

  const features = [
    {
      icon: <Brain className="h-8 w-8 text-blue-500" />,
      title: 'Intelligent Optimization',
      description: 'ML-driven optimization algorithms that continuously learn and adapt to your workloads',
    },
    {
      icon: <Shield className="h-8 w-8 text-green-500" />,
      title: 'Enterprise Security',
      description: 'SOC2 Type II certified with end-to-end encryption and comprehensive audit logging',
    },
    {
      icon: <Layers className="h-8 w-8 text-purple-500" />,
      title: 'Hybrid Architecture',
      description: 'Seamlessly operate across cloud, on-premise, and edge environments',
    },
    {
      icon: <Zap className="h-8 w-8 text-yellow-500" />,
      title: 'Real-time Processing',
      description: 'Sub-millisecond decision making for time-critical AI operations',
    },
    {
      icon: <Database className="h-8 w-8 text-red-500" />,
      title: 'Data Sovereignty',
      description: 'Complete control over data residency and compliance requirements',
    },
    {
      icon: <LineChart className="h-8 w-8 text-indigo-500" />,
      title: 'Predictive Analytics',
      description: 'Forecast resource needs and prevent bottlenecks before they occur',
    },
  ];

  const customers = [
    { name: 'OpenAI', industry: 'AI Research' },
    { name: 'Anthropic', industry: 'AI Safety' },
    { name: 'Fortune 100 Bank', industry: 'Financial Services' },
    { name: 'Global Retailer', industry: 'E-commerce' },
    { name: 'Healthcare Leader', industry: 'Healthcare' },
    { name: 'Tech Unicorn', industry: 'SaaS' },
  ];

  return (
    <div className="container mx-auto p-6 space-y-8">
      <div className="text-center space-y-4 py-8">
        <Badge variant="secondary" className="mb-4">
          <Sparkles className="h-3 w-3 mr-1" />
          Enterprise Platform
        </Badge>
        <h1 className="text-5xl font-bold bg-gradient-to-r from-emerald-600 to-purple-600 bg-clip-text text-transparent">
          Netra AI Optimization Platform
        </h1>
        <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
          The world&apos;s most advanced AI optimization platform, trusted by industry leaders including OpenAI and Anthropic
        </p>
        <div className="flex gap-4 justify-center pt-4">
          <Button size="lg" onClick={() => router.push('/chat')}>
            <Rocket className="mr-2 h-5 w-5" />
            Start Demo
          </Button>
          <Button size="lg" variant="outline" onClick={() => router.push('/ingestion')}>
            <Database className="mr-2 h-5 w-5" />
            Explore Data
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Live Performance Metrics</CardTitle>
          <CardDescription>Real-time optimization results from production deployments</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeDemo} onValueChange={setActiveDemo}>
            <TabsList className="grid w-full grid-cols-3">
              {demos.map((demo) => (
                <TabsTrigger key={demo.id} value={demo.id}>
                  {demo.title}
                </TabsTrigger>
              ))}
            </TabsList>
            {demos.map((demo) => (
              <TabsContent key={demo.id} value={demo.id} className="space-y-6">
                <div className="text-center py-4">
                  <h3 className="text-2xl font-semibold">{demo.title}</h3>
                  <p className="text-muted-foreground">{demo.description}</p>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  {demo.metrics.map((metric) => (
                    <Card key={metric.label}>
                      <CardContent className="pt-6">
                        <div className="text-center space-y-2">
                          <p className="text-sm text-muted-foreground">{metric.label}</p>
                          <p className="text-3xl font-bold">{metric.value}</p>
                          <Badge variant={metric.trend === 'up' ? 'default' : 'secondary'}>
                            {metric.trend === 'up' ? '↑' : '↓'} Optimized
                          </Badge>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Optimization Progress</span>
                    <span>{progress}%</span>
                  </div>
                  <Progress value={progress} className="h-2" />
                </div>
              </TabsContent>
            ))}
          </Tabs>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((feature, index) => (
          <Card key={index} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center gap-4">
                {feature.icon}
                <CardTitle className="text-lg">{feature.title}</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">{feature.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Trusted by Industry Leaders</CardTitle>
          <CardDescription>Powering AI optimization for the world&apos;s most innovative companies</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
            {customers.map((customer, index) => (
              <div key={index} className="text-center space-y-2 p-4 border rounded-lg">
                <p className="font-semibold">{customer.name}</p>
                <Badge variant="outline">{customer.industry}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="text-center space-y-4 py-8">
        <h2 className="text-3xl font-bold">Ready to Transform Your AI Operations?</h2>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          Join the leaders in AI optimization and experience the power of Netra&apos;s enterprise platform
        </p>
        <div className="flex gap-4 justify-center">
          <Button size="lg" onClick={() => router.push('/ingestion')}>
            <ArrowRight className="mr-2 h-5 w-5" />
            Explore Data Ingestion
          </Button>
          <Button size="lg" variant="outline" onClick={() => router.push('/corpus')}>
            <Code2 className="mr-2 h-5 w-5" />
            Manage Corpus
          </Button>
        </div>
      </div>
    </div>
  );
};

export default EnterpriseDemoPage;