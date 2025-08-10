'use client';

import { NextPage } from 'next';
import { authService } from '@/auth';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Database, Search, Filter, Download, Upload, Trash2, Edit, Eye, 
  FolderOpen, File, Hash, Calendar, HardDrive, Activity, 
  Shield, Lock, Unlock, RefreshCw, Settings, BarChart3,
  ChevronDown, ChevronRight, Copy, Share2, Archive
} from 'lucide-react';

interface CorpusItem {
  id: string;
  name: string;
  type: 'collection' | 'dataset' | 'model' | 'embedding';
  size: string;
  records: string;
  lastModified: string;
  status: 'active' | 'processing' | 'archived';
  owner: string;
  accessLevel: 'public' | 'private' | 'restricted';
  version: string;
  children?: CorpusItem[];
}

const CorpusPage: NextPage = () => {
  const { user, loading } = authService.useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('browse');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [expandedItems, setExpandedItems] = useState<string[]>(['1', '2']);
  const [filterType, setFilterType] = useState('all');
  const [storageUsed] = useState(68);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Loading...</p>
      </div>
    );
  }

  const corpusData: CorpusItem[] = [
    {
      id: '1',
      name: 'Production Models',
      type: 'collection',
      size: '12.4 GB',
      records: '45.2K',
      lastModified: '2 hours ago',
      status: 'active',
      owner: 'System',
      accessLevel: 'restricted',
      version: 'v3.2',
      children: [
        {
          id: '11',
          name: 'GPT-4 Fine-tuned',
          type: 'model',
          size: '4.8 GB',
          records: '12K',
          lastModified: '1 day ago',
          status: 'active',
          owner: 'ML Team',
          accessLevel: 'private',
          version: 'v2.1',
        },
        {
          id: '12',
          name: 'Claude-3 Optimized',
          type: 'model',
          size: '3.2 GB',
          records: '8.5K',
          lastModified: '3 days ago',
          status: 'active',
          owner: 'ML Team',
          accessLevel: 'private',
          version: 'v1.8',
        },
      ],
    },
    {
      id: '2',
      name: 'Training Datasets',
      type: 'collection',
      size: '28.7 GB',
      records: '2.1M',
      lastModified: '5 hours ago',
      status: 'active',
      owner: 'Data Team',
      accessLevel: 'public',
      version: 'v4.0',
      children: [
        {
          id: '21',
          name: 'Customer Interactions',
          type: 'dataset',
          size: '8.2 GB',
          records: '890K',
          lastModified: '6 hours ago',
          status: 'processing',
          owner: 'Analytics',
          accessLevel: 'restricted',
          version: 'v2.3',
        },
        {
          id: '22',
          name: 'Product Reviews',
          type: 'dataset',
          size: '5.6 GB',
          records: '450K',
          lastModified: '1 week ago',
          status: 'active',
          owner: 'Product Team',
          accessLevel: 'public',
          version: 'v1.5',
        },
        {
          id: '23',
          name: 'Support Tickets',
          type: 'dataset',
          size: '3.8 GB',
          records: '320K',
          lastModified: '2 days ago',
          status: 'active',
          owner: 'Support Team',
          accessLevel: 'restricted',
          version: 'v3.1',
        },
      ],
    },
    {
      id: '3',
      name: 'Vector Embeddings',
      type: 'embedding',
      size: '6.9 GB',
      records: '780K',
      lastModified: '12 hours ago',
      status: 'active',
      owner: 'ML Team',
      accessLevel: 'private',
      version: 'v2.0',
    },
    {
      id: '4',
      name: 'Archived Data',
      type: 'collection',
      size: '45.2 GB',
      records: '5.6M',
      lastModified: '1 month ago',
      status: 'archived',
      owner: 'Admin',
      accessLevel: 'private',
      version: 'v1.0',
    },
  ];

  const toggleExpand = (id: string) => {
    setExpandedItems(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const toggleSelect = (id: string) => {
    setSelectedItems(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'collection':
        return <FolderOpen className="h-4 w-4 text-blue-500" />;
      case 'dataset':
        return <Database className="h-4 w-4 text-green-500" />;
      case 'model':
        return <Activity className="h-4 w-4 text-purple-500" />;
      case 'embedding':
        return <Hash className="h-4 w-4 text-orange-500" />;
      default:
        return <File className="h-4 w-4 text-gray-500" />;
    }
  };

  const getAccessIcon = (level: string) => {
    switch (level) {
      case 'public':
        return <Unlock className="h-3 w-3 text-green-500" />;
      case 'private':
        return <Lock className="h-3 w-3 text-red-500" />;
      case 'restricted':
        return <Shield className="h-3 w-3 text-yellow-500" />;
      default:
        return null;
    }
  };

  const renderCorpusItem = (item: CorpusItem, depth = 0) => {
    const isExpanded = expandedItems.includes(item.id);
    const isSelected = selectedItems.includes(item.id);
    const hasChildren = item.children && item.children.length > 0;

    return (
      <div key={item.id}>
        <div
          className={`flex items-center gap-3 p-3 hover:bg-muted/50 rounded-lg cursor-pointer ${
            isSelected ? 'bg-muted' : ''
          }`}
          style={{ paddingLeft: `${depth * 24 + 12}px` }}
          onClick={() => toggleSelect(item.id)}
        >
          {hasChildren && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleExpand(item.id);
              }}
              className="p-0.5"
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </button>
          )}
          {!hasChildren && <div className="w-5" />}
          
          {getTypeIcon(item.type)}
          
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-medium">{item.name}</span>
              <Badge variant={item.status === 'active' ? 'default' : item.status === 'processing' ? 'secondary' : 'outline'}>
                {item.status}
              </Badge>
              {getAccessIcon(item.accessLevel)}
              <Badge variant="outline" className="text-xs">
                {item.version}
              </Badge>
            </div>
            <div className="flex gap-4 text-sm text-muted-foreground mt-1">
              <span>{item.records} items</span>
              <span>{item.size}</span>
              <span>{item.lastModified}</span>
              <span>by {item.owner}</span>
            </div>
          </div>
          
          <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
            <Button size="sm" variant="ghost">
              <Eye className="h-4 w-4" />
            </Button>
            <Button size="sm" variant="ghost">
              <Edit className="h-4 w-4" />
            </Button>
            <Button size="sm" variant="ghost">
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        {hasChildren && isExpanded && (
          <div>
            {item.children!.map(child => renderCorpusItem(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  const stats = [
    { label: 'Total Collections', value: '24', icon: <FolderOpen className="h-4 w-4" /> },
    { label: 'Active Datasets', value: '156', icon: <Database className="h-4 w-4" /> },
    { label: 'Models', value: '12', icon: <Activity className="h-4 w-4" /> },
    { label: 'Total Records', value: '8.4M', icon: <File className="h-4 w-4" /> },
  ];

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Corpus Management</h1>
          <p className="text-muted-foreground">Organize and manage your data collections</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline">
            <Upload className="mr-2 h-4 w-4" />
            Import
          </Button>
          <Button onClick={() => router.push('/ingestion')}>
            <Database className="mr-2 h-4 w-4" />
            New Ingestion
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {stats.map((stat, index) => (
          <Card key={index}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                  <p className="text-2xl font-bold">{stat.value}</p>
                </div>
                {stat.icon}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Storage Usage</CardTitle>
              <CardDescription>93.2 GB of 150 GB used</CardDescription>
            </div>
            <Button variant="outline" size="sm">
              <Settings className="mr-2 h-4 w-4" />
              Manage Storage
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Progress value={storageUsed} className="h-3" />
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>Models: 24.3 GB</span>
              <span>Datasets: 45.8 GB</span>
              <span>Embeddings: 15.2 GB</span>
              <span>Archives: 7.9 GB</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="browse">Browse</TabsTrigger>
          <TabsTrigger value="search">Search</TabsTrigger>
          <TabsTrigger value="versions">Versions</TabsTrigger>
          <TabsTrigger value="permissions">Permissions</TabsTrigger>
        </TabsList>

        <TabsContent value="browse" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Data Collections</CardTitle>
                <div className="flex gap-3">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search corpus..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-9 w-64"
                    />
                  </div>
                  <Select value={filterType} onValueChange={setFilterType}>
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      <SelectItem value="collection">Collections</SelectItem>
                      <SelectItem value="dataset">Datasets</SelectItem>
                      <SelectItem value="model">Models</SelectItem>
                      <SelectItem value="embedding">Embeddings</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button variant="outline" size="icon">
                    <Filter className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg">
                {corpusData
                  .filter(item => 
                    (filterType === 'all' || item.type === filterType) &&
                    (searchTerm === '' || item.name.toLowerCase().includes(searchTerm.toLowerCase()))
                  )
                  .map(item => renderCorpusItem(item))}
              </div>
              {selectedItems.length > 0 && (
                <div className="mt-4 p-4 bg-muted rounded-lg flex justify-between items-center">
                  <span className="text-sm">{selectedItems.length} items selected</span>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline">
                      <Copy className="mr-2 h-4 w-4" />
                      Duplicate
                    </Button>
                    <Button size="sm" variant="outline">
                      <Archive className="mr-2 h-4 w-4" />
                      Archive
                    </Button>
                    <Button size="sm" variant="outline">
                      <Share2 className="mr-2 h-4 w-4" />
                      Share
                    </Button>
                    <Button size="sm" variant="destructive">
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="search" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Advanced Search</CardTitle>
              <CardDescription>Search across all corpus data with advanced filters</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="search-query">Search Query</Label>
                  <Input id="search-query" placeholder="Enter search terms..." />
                </div>
                <div>
                  <Label htmlFor="search-type">Data Type</Label>
                  <Select>
                    <SelectTrigger id="search-type">
                      <SelectValue placeholder="All types" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      <SelectItem value="text">Text</SelectItem>
                      <SelectItem value="embeddings">Embeddings</SelectItem>
                      <SelectItem value="metadata">Metadata</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="date-range">Date Range</Label>
                  <Select>
                    <SelectTrigger id="date-range">
                      <SelectValue placeholder="Last 30 days" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="7">Last 7 days</SelectItem>
                      <SelectItem value="30">Last 30 days</SelectItem>
                      <SelectItem value="90">Last 90 days</SelectItem>
                      <SelectItem value="365">Last year</SelectItem>
                      <SelectItem value="all">All time</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="owner">Owner</Label>
                  <Select>
                    <SelectTrigger id="owner">
                      <SelectValue placeholder="All owners" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Owners</SelectItem>
                      <SelectItem value="me">My Data</SelectItem>
                      <SelectItem value="team">Team Data</SelectItem>
                      <SelectItem value="system">System Data</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex gap-4">
                <Button>
                  <Search className="mr-2 h-4 w-4" />
                  Search
                </Button>
                <Button variant="outline">Reset Filters</Button>
              </div>
              <Alert>
                <AlertDescription>
                  Use advanced operators: AND, OR, NOT, "exact phrase", wildcard*
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="versions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Version Control</CardTitle>
              <CardDescription>Track and manage different versions of your data</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="font-semibold">Production Models v3.2</h3>
                      <p className="text-sm text-muted-foreground">Current version</p>
                    </div>
                    <Badge>Active</Badge>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm">
                      <Calendar className="h-4 w-4 text-muted-foreground" />
                      <span>Created: March 15, 2024</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <HardDrive className="h-4 w-4 text-muted-foreground" />
                      <span>Size: 12.4 GB</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <BarChart3 className="h-4 w-4 text-muted-foreground" />
                      <span>45,231 records</span>
                    </div>
                  </div>
                </div>
                <div className="border rounded-lg p-4 opacity-75">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="font-semibold">Production Models v3.1</h3>
                      <p className="text-sm text-muted-foreground">Previous version</p>
                    </div>
                    <Badge variant="secondary">Archived</Badge>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline">
                      <RefreshCw className="mr-2 h-4 w-4" />
                      Restore
                    </Button>
                    <Button size="sm" variant="outline">
                      <Eye className="mr-2 h-4 w-4" />
                      Compare
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="permissions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Access Control</CardTitle>
              <CardDescription>Manage who can access your corpus data</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Default Access Level</Label>
                    <Select defaultValue="restricted">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="public">Public</SelectItem>
                        <SelectItem value="restricted">Restricted</SelectItem>
                        <SelectItem value="private">Private</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Sharing Policy</Label>
                    <Select defaultValue="team">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">No Sharing</SelectItem>
                        <SelectItem value="team">Team Only</SelectItem>
                        <SelectItem value="org">Organization</SelectItem>
                        <SelectItem value="external">Allow External</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="border rounded-lg">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-3">User/Group</th>
                        <th className="text-left p-3">Role</th>
                        <th className="text-left p-3">Access Level</th>
                        <th className="text-left p-3">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b">
                        <td className="p-3">ML Team</td>
                        <td className="p-3">Admin</td>
                        <td className="p-3">Full Access</td>
                        <td className="p-3">
                          <Button size="sm" variant="outline">Edit</Button>
                        </td>
                      </tr>
                      <tr className="border-b">
                        <td className="p-3">Data Scientists</td>
                        <td className="p-3">Editor</td>
                        <td className="p-3">Read/Write</td>
                        <td className="p-3">
                          <Button size="sm" variant="outline">Edit</Button>
                        </td>
                      </tr>
                      <tr>
                        <td className="p-3">Analytics Team</td>
                        <td className="p-3">Viewer</td>
                        <td className="p-3">Read Only</td>
                        <td className="p-3">
                          <Button size="sm" variant="outline">Edit</Button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <Button>
                  <Shield className="mr-2 h-4 w-4" />
                  Add Permission Rule
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default CorpusPage;